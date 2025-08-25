"""
Main OpenAI client implementation.
"""

import logging
import asyncio
from typing import Any, Dict, Optional, List
from openai import OpenAI
from openai import RateLimitError, APIError, AuthenticationError
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..base.client import BaseClient, with_retry
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientQuotaExceededError,
    ClientRateLimitError,
)
from .config import OpenAIClientConfig
from ...core.langsmith_config import langsmith_trace, log_trace_info
import time
import hashlib
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class OpenAIClient(BaseClient):
    """OpenAI client for connection and API management."""

    def __init__(self, config: OpenAIClientConfig):
        super().__init__(config, "OpenAIClient")
        self.config: OpenAIClientConfig = config
        self._openai_client: Optional[OpenAI] = None
        self._langchain_client: Optional[ChatOpenAI] = None

        # Round-robin API key pool and health-aware state
        self._api_keys: List[str] = []
        self._rr_index: int = 0
        self._pool_lock: asyncio.Lock = asyncio.Lock()
        # Per-key health state
        # key -> {"status": "HEALTHY"|"COOLDOWN", "cooldown_until": float, "backoff": float}
        self._key_state: Dict[str, Dict[str, Any]] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}

        # Per-key client caches
        self._openai_clients_by_key: Dict[str, OpenAI] = {}
        # Cache LangChain clients by (api_key, model)
        self._langchain_clients_by_key_model: Dict[str, ChatOpenAI] = {}

        # Pool backoff configuration (no magic numbers; can be overridden via extra_config)
        ec = self.config.extra_config if hasattr(self.config, "extra_config") else {}
        self._short_backoff_seconds: float = float(
            ec.get("pool_short_backoff_seconds", 20)
        )
        self._long_backoff_seconds: float = float(
            ec.get("pool_long_backoff_seconds", 600)
        )
        self._backoff_multiplier: float = float(ec.get("pool_backoff_multiplier", 2.0))
        self._backoff_jitter_seconds: float = float(
            ec.get("pool_backoff_jitter_seconds", 5)
        )
        self._max_attempts_per_call: int = int(ec.get("pool_max_attempts_per_call", 8))

    def _now(self) -> float:
        return time.monotonic()

    def _key_hash(self, key: str) -> str:
        try:
            return hashlib.sha256(key.encode()).hexdigest()[:10]
        except Exception:
            return "unknown"

    def _openrouter_key_url(self) -> str:
        base = self.config.api_base or "https://openrouter.ai/api/v1"
        return base.rstrip("/") + "/key"

    def _parse_interval_seconds(self, interval: Any) -> float:
        try:
            if isinstance(interval, (int, float)):
                return float(interval)
            s = str(interval).strip().lower()
            if s.endswith("ms"):
                return max(0.0, float(s[:-2]) / 1000.0)
            if s.endswith("s"):
                return max(0.0, float(s[:-1]))
            if s.endswith("m"):
                return max(0.0, float(s[:-1]) * 60.0)
            return max(0.0, float(s))
        except Exception:
            return 10.0

    async def _fetch_key_status(self, api_key: str) -> Dict[str, Any]:
        url = self._openrouter_key_url()
        timeout = float(self.config.request_timeout or 60)
        try:
            default_headers = self.config.extra_config.get("default_headers")  # type: ignore[attr-defined]
        except Exception:
            default_headers = {}

        def _do_request() -> Dict[str, Any]:
            req = Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {api_key}")
            for hk, hv in (default_headers or {}).items():
                try:
                    req.add_header(str(hk), str(hv))
                except Exception:
                    continue
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _do_request)

    async def _next_healthy_key(self) -> Optional[str]:
        """Return next healthy API key using round-robin, skipping cooldown keys."""
        async with self._pool_lock:
            if not self._api_keys:
                return None
            start_index = self._rr_index
            total = len(self._api_keys)
            for _ in range(total):
                key = self._api_keys[self._rr_index]
                self._rr_index = (self._rr_index + 1) % total
                state = self._key_state.get(
                    key, {"status": "HEALTHY", "cooldown_until": 0.0}
                )
                if state.get("status") != "COOLDOWN" or self._now() >= float(
                    state.get("cooldown_until", 0.0)
                ):
                    # If cooldown elapsed, mark healthy
                    if state.get("status") == "COOLDOWN" and self._now() >= float(
                        state.get("cooldown_until", 0.0)
                    ):
                        self._key_state[key] = {
                            "status": "HEALTHY",
                            "cooldown_until": 0.0,
                            "backoff": self._short_backoff_seconds,
                        }
                    self.logger.debug(
                        f"Selected API key hash={self._key_hash(key)} via RR; rr_index={self._rr_index}"
                    )
                    return key
            # No healthy key
            return None

    async def _snapshot_pool_state(self) -> Dict[str, Any]:
        """Return a lightweight snapshot of pool states for logging."""
        async with self._pool_lock:
            now = self._now()
            states: List[Dict[str, Any]] = []
            healthy = 0
            cooldown = 0
            for key in self._api_keys:
                st = self._key_state.get(
                    key, {"status": "HEALTHY", "cooldown_until": 0.0}
                )
                status = st.get("status")
                if status == "COOLDOWN":
                    cooldown += 1
                else:
                    healthy += 1
                remaining = 0.0
                if status == "COOLDOWN":
                    remaining = max(0.0, float(st.get("cooldown_until", 0.0)) - now)
                states.append(
                    {
                        "hash": self._key_hash(key),
                        "status": status,
                        "cooldown_remaining_s": round(remaining, 1),
                    }
                )
            return {
                "keys_total": len(self._api_keys),
                "healthy": healthy,
                "cooldown": cooldown,
                "states": states,
            }

    async def _mark_unhealthy(
        self, key: str, *, reason: str, long_cooldown: bool = False
    ) -> None:
        """Mark key unhealthy and schedule background healthcheck."""
        backoff_base = (
            self._long_backoff_seconds if long_cooldown else self._short_backoff_seconds
        )
        async with self._pool_lock:
            prev = self._key_state.get(key) or {"backoff": backoff_base}
            prev_backoff = float(prev.get("backoff", backoff_base))
            # Exponential backoff with cap depending on long/short mode
            max_backoff = (
                self._long_backoff_seconds
                if long_cooldown
                else max(self._short_backoff_seconds * 8, self._short_backoff_seconds)
            )
            next_backoff = min(
                prev_backoff * (self._backoff_multiplier if prev_backoff > 0 else 1.0),
                max_backoff,
            )
            # Add small jitter
            jitter = min(
                self._backoff_jitter_seconds, max(0.0, self._backoff_jitter_seconds)
            )
            cooldown_for = next_backoff + (jitter if jitter > 0 else 0)
            cooldown_until = self._now() + cooldown_for
            self._key_state[key] = {
                "status": "COOLDOWN",
                "cooldown_until": cooldown_until,
                "backoff": next_backoff,
            }
            self.logger.warning(
                f"Marking API key unhealthy: hash={self._key_hash(key)} reason={reason} cooldown_for={cooldown_for:.1f}s"
            )
            self.logger.debug(
                f"Unhealthy details: backoff_base={'long' if long_cooldown else 'short'} next_backoff={next_backoff:.1f}s cooldown_until_in={cooldown_for:.1f}s"
            )
            # Schedule single-flight healthcheck task if not already scheduled
            if key not in self._health_tasks or self._health_tasks[key].done():
                self._health_tasks[key] = asyncio.create_task(
                    self._healthcheck_worker(key)
                )

    async def _set_healthy(self, key: str) -> None:
        async with self._pool_lock:
            self._key_state[key] = {
                "status": "HEALTHY",
                "cooldown_until": 0.0,
                "backoff": self._short_backoff_seconds,
            }
            # Clear any finished task record
            if key in self._health_tasks and self._health_tasks[key].done():
                del self._health_tasks[key]
            self.logger.info(
                f"API key recovered to HEALTHY: hash={self._key_hash(key)}"
            )

    async def _healthcheck_worker(self, key: str) -> None:
        """Background probe loop for an unhealthy key."""
        while True:
            async with self._pool_lock:
                state = self._key_state.get(key)
                if not state:
                    return
                status = state.get("status")
                cooldown_until = float(state.get("cooldown_until", 0.0))
            if status != "COOLDOWN":
                return
            now = self._now()
            if cooldown_until > now:
                await asyncio.sleep(max(0.0, cooldown_until - now))

            # Probe via OpenRouter key status endpoint (does not consume gen limits)
            try:
                info = await self._fetch_key_status(key)
                data = info.get("data") if isinstance(info, dict) else None
                rate = (
                    (data or {}).get("rate_limit") if isinstance(data, dict) else None
                )
                interval = (
                    (rate or {}).get("interval") if isinstance(rate, dict) else None
                )
                limit_remaining = (
                    (data or {}).get("limit_remaining")
                    if isinstance(data, dict)
                    else None
                )
                if interval is not None:
                    # If unlimited (null), consider healthy immediately
                    if limit_remaining is None:
                        self.logger.debug(
                            f"Healthcheck: limit remaining = null (unlimited) for key hash={self._key_hash(key)}; marking healthy"
                        )
                        await self._set_healthy(key)
                        return
                    try:
                        if float(limit_remaining) > 0:
                            self.logger.debug(
                                f"Healthcheck: limit remaining = {limit_remaining} within interval {interval} for key hash={self._key_hash(key)}; marking healthy"
                            )
                            await self._set_healthy(key)
                            return
                        # No remaining credits in this interval; wait interval then retry
                        wait_secs = self._parse_interval_seconds(interval)
                        await self._mark_unhealthy(
                            key, reason="healthcheck-rl-window", long_cooldown=False
                        )
                        self.logger.debug(
                            f"Healthcheck: limit remaining = 0; waiting {wait_secs:.1f}s per interval before retry for key hash={self._key_hash(key)}"
                        )
                        await asyncio.sleep(max(0.0, wait_secs))
                        continue
                    except Exception:
                        # On parsing issues, keep short cooldown
                        await self._mark_unhealthy(
                            key, reason="healthcheck-parse", long_cooldown=False
                        )
                        continue
                # If no rate info but endpoint reachable, treat as healthy
                await self._set_healthy(key)
                return
            except RateLimitError:
                await self._mark_unhealthy(
                    key, reason="healthcheck-429", long_cooldown=False
                )
                continue
            except APIError as e:
                sc = getattr(e, "status_code", None)
                if sc in (401, 402):
                    await self._mark_unhealthy(
                        key, reason=f"healthcheck-{sc}", long_cooldown=True
                    )
                    continue
                if sc and sc >= 500:
                    await self._mark_unhealthy(
                        key, reason=f"healthcheck-5xx-{sc}", long_cooldown=False
                    )
                    continue
                if sc == 403:
                    # Treat as request/content related; keep long cooldown
                    await self._mark_unhealthy(
                        key, reason="healthcheck-403", long_cooldown=True
                    )
                    continue
                # Other 4xx -> keep cooldown and stop to avoid churn
                await self._mark_unhealthy(
                    key, reason=f"healthcheck-4xx-{sc}", long_cooldown=True
                )
                return
            except HTTPError as e:
                code = getattr(e, "code", None)
                if code in (401, 402):
                    await self._mark_unhealthy(
                        key, reason=f"healthcheck-http-{code}", long_cooldown=True
                    )
                    continue
                if code and code >= 500:
                    await self._mark_unhealthy(
                        key, reason=f"healthcheck-http-5xx-{code}", long_cooldown=False
                    )
                    continue
                await self._mark_unhealthy(
                    key, reason=f"healthcheck-http-{code}", long_cooldown=False
                )
                continue
            except URLError as e:
                await self._mark_unhealthy(
                    key, reason="healthcheck-network", long_cooldown=False
                )
                continue
            except Exception as e:  # pragma: no cover - defensive
                await self._mark_unhealthy(
                    key, reason=f"healthcheck-exc:{e}", long_cooldown=False
                )
                continue

    # Deprecated: direct per-key OpenAI client creation removed; we use
    # ChatOpenAI for generation and the /key endpoint for health checks.

    def _get_or_create_langchain_client_for(
        self,
        api_key: str,
        model: str,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
    ) -> ChatOpenAI:
        """Return a LangChain ChatOpenAI client for a specific (api_key, model)."""
        cache_key = f"{api_key}|{model}"
        if cache_key in self._langchain_clients_by_key_model:
            return self._langchain_clients_by_key_model[cache_key]

        langchain_kwargs: Dict[str, Any] = {
            "openai_api_key": api_key,
            "model": model,
            "temperature": (
                temperature if temperature is not None else self.config.temperature
            ),
            "max_tokens": (
                max_tokens if max_tokens is not None else self.config.max_tokens
            ),
            "top_p": top_p if top_p is not None else self.config.top_p,
            "frequency_penalty": (
                frequency_penalty
                if frequency_penalty is not None
                else self.config.frequency_penalty
            ),
            "presence_penalty": (
                presence_penalty
                if presence_penalty is not None
                else self.config.presence_penalty
            ),
            "request_timeout": self.config.request_timeout,
            "max_retries": self.config.max_retries,
        }
        if self.config.api_base:
            langchain_kwargs["openai_api_base"] = self.config.api_base
        if self.config.organization:
            langchain_kwargs["openai_organization"] = self.config.organization
        langchain_kwargs = {k: v for k, v in langchain_kwargs.items() if v is not None}

        lc_client = ChatOpenAI(**langchain_kwargs)
        self._langchain_clients_by_key_model[cache_key] = lc_client
        return lc_client

    @property
    def openai_client(self) -> OpenAI:
        """Get the underlying OpenAI client."""
        if not self._openai_client:
            raise ClientError("OpenAI client not initialized", self.client_name)
        return self._openai_client

    @property
    def langchain_client(self) -> ChatOpenAI:
        """Get the LangChain ChatOpenAI client for LangSmith tracing."""
        if not self._langchain_client:
            raise ClientError("LangChain client not initialized", self.client_name)
        return self._langchain_client

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def initialize(self) -> None:
        """Initialize OpenAI client.

        - Populate API key pool from config
        - Optionally run a lightweight connection test
        - Mark client as initialized
        """
        try:
            self.logger.info("Initializing OpenAI client (lazy mode enabled)...")

            # Build API key pool
            extra: Dict[str, Any] = {}
            try:
                extra = self.config.extra_config or {}
            except Exception:
                extra = {}

            keys = []
            try:
                raw_keys = extra.get("api_keys")
                if isinstance(raw_keys, list):
                    keys = [str(k).strip() for k in raw_keys if str(k).strip()]
            except Exception:
                keys = []

            # Ensure primary key is present if configured
            if self.config.api_key and self.config.api_key.strip():
                if self.config.api_key.strip() not in keys:
                    keys = [self.config.api_key.strip()] + keys

            # Store pool and initialize per-key state
            async with self._pool_lock:
                self._api_keys = keys
                self._rr_index = 0
                for key in self._api_keys:
                    self._key_state[key] = {
                        "status": "HEALTHY",
                        "cooldown_until": 0.0,
                        "backoff": self._short_backoff_seconds,
                    }

            # Optionally pre-warm a LangChain client for the default model
            if self._api_keys:
                try:
                    _ = self._get_or_create_langchain_client_for(
                        self._api_keys[0],
                        self.config.model_name,
                    )
                except Exception:
                    # Pre-warm failures should not block initialization; connection test handles health
                    pass

            # Optionally run a connection test
            run_test = bool(extra.get("init_connection_test", True))
            if run_test:
                await self._test_connection()

            self._initialized = True
            self.logger.info(
                f"OpenAI client initialized. keys_total={len(self._api_keys)} model={self.config.model_name}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize OpenAI client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def _test_connection(self) -> None:
        """Test OpenAI API connection."""
        try:
            # Use OpenRouter key status endpoint; does not consume chat/gen limits
            key_for_test = self._api_keys[0] if self._api_keys else self.config.api_key
            if not key_for_test:
                raise ClientAuthenticationError(
                    "No OpenAI API key configured",
                    client_name=self.client_name,
                )
            try:
                info = await self._fetch_key_status(key_for_test)
                data = info.get("data") if isinstance(info, dict) else None
                if data is None:
                    raise ClientConnectionError(
                        "Key status payload missing 'data'",
                        client_name=self.client_name,
                    )
                self.logger.debug("OpenAI key status reachable; connection ok")
                return
            except HTTPError as e:
                if e.code == 401:
                    raise ClientAuthenticationError(
                        "Authentication failed on key status endpoint",
                        client_name=self.client_name,
                        original_error=e,
                    )
                if e.code == 402:
                    raise ClientQuotaExceededError(
                        "Credits exhausted on key status endpoint",
                        client_name=self.client_name,
                        original_error=e,
                    )
                if 500 <= e.code <= 599:
                    raise ClientConnectionError(
                        f"Key status endpoint 5xx: {e.code}",
                        client_name=self.client_name,
                        original_error=e,
                    )
                raise ClientConnectionError(
                    f"Key status endpoint error: {e.code}",
                    client_name=self.client_name,
                    original_error=e,
                )
            except URLError as e:
                raise ClientConnectionError(
                    f"Key status endpoint network error: {e}",
                    client_name=self.client_name,
                    original_error=e,
                )

        except AuthenticationError as e:
            raise ClientAuthenticationError(
                f"OpenAI API authentication failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except RateLimitError as e:
            raise ClientRateLimitError(
                f"OpenAI API rate limit exceeded: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except APIError as e:
            message_lower = str(e).lower()
            if "quota" in message_lower:
                raise ClientQuotaExceededError(
                    f"OpenAI API quota exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            # If the configured model is invalid for the provider, surface clearly
            if any(
                term in message_lower
                for term in ["model", "not found", "does not exist", "invalid"]
            ):
                raise ClientConnectionError(
                    f"Model configuration invalid during connection test: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            raise ClientConnectionError(
                f"OpenAI API connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            raise ClientConnectionError(
                f"OpenAI API connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on OpenAI client."""
        try:
            # Test API connection
            await self._test_connection()

            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "model_name": self.config.model_name,
                "connection": "ok",
                "config": {
                    "model_name": self.config.model_name,
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                    "temperature": self.config.temperature,
                    "api_base": self.config.api_base or "https://api.openai.com/v1",
                },
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """Close OpenAI client and clean up resources."""
        try:
            if self._openai_client:
                # OpenAI client doesn't require explicit closing
                self._openai_client = None

            if self._langchain_client:
                # LangChain client doesn't require explicit closing
                self._langchain_client = None

            # Clear per-key caches
            self._openai_clients_by_key.clear()
            self._langchain_clients_by_key_model.clear()

            self._initialized = False
            self.logger.info(
                "OpenAI client and LangChain ChatOpenAI closed successfully"
            )

        except Exception as e:
            self.logger.error(f"Error closing OpenAI client: {e}")
            raise ClientError(
                f"Error closing OpenAI client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # Core API Methods - Connection Layer Only

    @langsmith_trace(name="openai_client_generate_content", run_type="chain")
    @with_retry(max_retries=3, backoff_factor=2.0)
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Call OpenAI API to generate content using LangChain for LangSmith tracing.

        Accepted kwargs include:
        - model: Optional[str]
        - temperature: Optional[float]
        - max_tokens: Optional[int]
        - top_p: Optional[float]
        - frequency_penalty: Optional[float]
        - presence_penalty: Optional[float]
        - messages: Optional[List[Dict[str, Any]]] - if provided, used as-is
        - system_prompt: Optional[str] - if provided and messages not supplied,
          will be prepended as a system message before the user prompt.
        """
        try:
            # Handle both single prompt and messages format
            if "messages" in kwargs:
                messages = kwargs["messages"]
            else:
                system_prompt: Optional[str] = kwargs.get("system_prompt")
                if system_prompt:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ]
                else:
                    messages = [{"role": "user", "content": prompt}]

            # Convert to LangChain message format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                # Add other message types as needed

            # Log trace info for debugging
            log_trace_info(
                "generate_content_with_langchain",
                model=kwargs.get("model", self.config.model_name),
                message_count=len(langchain_messages),
                temperature=kwargs.get("temperature", self.config.temperature),
            )

            # Resolve model
            model_to_use = kwargs.get("model", self.config.model_name)

            # Attempt across healthy keys within a single call
            attempts = 0
            tried_hashes: List[str] = []
            last_error: Optional[Exception] = None
            while attempts < max(
                1, min(self._max_attempts_per_call, max(1, len(self._api_keys)))
            ):
                key = await self._next_healthy_key()
                if not key:
                    # No healthy key available
                    self.logger.error("No healthy API keys available; pool depleted")
                    raise ClientConnectionError(
                        "No healthy API keys available for OpenAI request",
                        client_name=self.client_name,
                    )
                attempts += 1
                key_hash = self._key_hash(key)
                tried_hashes.append(key_hash)
                self.logger.info(
                    f"Attempt {attempts}: using key_hash={key_hash} model={model_to_use}"
                )
                try:
                    langchain_client = self._get_or_create_langchain_client_for(
                        key,
                        model_to_use,
                        temperature=kwargs.get("temperature"),
                        max_tokens=kwargs.get("max_tokens"),
                        top_p=kwargs.get("top_p"),
                        frequency_penalty=kwargs.get("frequency_penalty"),
                        presence_penalty=kwargs.get("presence_penalty"),
                    )

                    if hasattr(langchain_client, "ainvoke"):
                        response = await langchain_client.ainvoke(langchain_messages)
                    else:
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(
                            None, lambda: langchain_client.invoke(langchain_messages)
                        )

                    if not response or not getattr(response, "content", None):
                        raise ClientError(
                            "No content generated from OpenAI",
                            client_name=self.client_name,
                        )
                    self.logger.info(f"OpenAI response succeeded with key {key_hash}")
                    return response.content
                except RateLimitError as e:
                    self.logger.warning(
                        f"429 RateLimitError on key hash={self._key_hash(key)} attempt={attempts}; failing over"
                    )
                    await self._mark_unhealthy(key, reason="429", long_cooldown=False)
                    last_error = e
                    continue
                except APIError as e:
                    sc = getattr(e, "status_code", None)
                    # Timeout sometimes surfaced as 408 in APIError
                    if sc == 408:
                        self.logger.warning(
                            f"408 timeout on key hash={self._key_hash(key)} attempt={attempts}; failing over"
                        )
                        await self._mark_unhealthy(
                            key, reason="408-timeout", long_cooldown=False
                        )
                        last_error = e
                        continue
                    if sc == 429:
                        self.logger.warning(
                            f"429 APIError on key hash={self._key_hash(key)} attempt={attempts}; failing over"
                        )
                        await self._mark_unhealthy(
                            key, reason="429", long_cooldown=False
                        )
                        last_error = e
                        continue
                    if sc in (401, 402):
                        self.logger.warning(
                            f"{sc} auth/quota on key hash={self._key_hash(key)}; long cooldown and failover"
                        )
                        await self._mark_unhealthy(
                            key, reason=f"{sc}", long_cooldown=True
                        )
                        last_error = e
                        continue
                    if sc == 403:
                        # Moderation/blocked content -> raise immediately
                        self.logger.info(
                            f"403 moderation/content block; raising without failover"
                        )
                        raise e
                    if sc and 400 <= sc < 500:
                        # Other request errors -> raise
                        self.logger.info(
                            f"4xx={sc} request error; raising without failover"
                        )
                        raise e
                    if sc and sc >= 500:
                        self.logger.warning(
                            f"5xx={sc} on key hash={self._key_hash(key)}; short cooldown and failover"
                        )
                        await self._mark_unhealthy(
                            key, reason=f"5xx-{sc}", long_cooldown=False
                        )
                        last_error = e
                        continue
                    # Unknown APIError shape -> treat as transient
                    self.logger.warning(
                        f"Unknown APIError (status={sc}); treating as transient and failing over"
                    )
                    await self._mark_unhealthy(
                        key, reason="apierror-unknown", long_cooldown=False
                    )
                    last_error = e
                    continue
                except asyncio.TimeoutError as e:
                    self.logger.warning(
                        f"asyncio.TimeoutError on key hash={self._key_hash(key)} attempt={attempts}; failing over"
                    )
                    await self._mark_unhealthy(
                        key, reason="timeout", long_cooldown=False
                    )
                    last_error = e
                    continue
                except Exception as e:
                    # Non-HTTP exceptions: bubble up so outer retry policy can apply
                    self.logger.warning(
                        f"OpenAI call error on key hash={self._key_hash(key)} attempts={attempts} tried={tried_hashes}: {e}"
                    )
                    raise

            # Exhausted attempts across keys
            if last_error:
                raise last_error
            raise ClientError(
                "OpenAI request failed with no specific error captured",
                client_name=self.client_name,
            )

        except Exception as langchain_error:
            # raise error to trigger retry (handled by decorator or caller)
            self.logger.warning(f"LangChain call failed: {langchain_error}")
            raise langchain_error
            # Fallback to direct OpenAI client if LangChain fails
            # self.logger.warning(
            #     f"LangChain call failed, falling back to direct OpenAI: {langchain_error}"
            # )

            # # Prepare parameters for direct OpenAI call
            # params = {
            #     "model": kwargs.get("model", self.config.model_name),
            #     "messages": messages,  # Use original messages format
            #     "temperature": kwargs.get("temperature", self.config.temperature),
            #     "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            #     "top_p": kwargs.get("top_p", self.config.top_p),
            #     "frequency_penalty": kwargs.get(
            #         "frequency_penalty", self.config.frequency_penalty
            #     ),
            #     "presence_penalty": kwargs.get(
            #         "presence_penalty", self.config.presence_penalty
            #     ),
            # }

            # # Remove None values
            # params = {k: v for k, v in params.items() if v is not None}

            # # Execute via task queue for rate limiting (original approach)
            # queue = OpenAILLMQueueManager.get_queue(params.get("model"))
            # try:
            #     response = await queue.run_in_executor(
            #         lambda: self.openai_client.chat.completions.create(**params)
            #     )

            #     if not response.choices or not response.choices[0].message.content:
            #         raise ClientError(
            #             "No content generated from OpenAI", client_name=self.client_name
            #         )

            #     return response.choices[0].message.content

            # except (RateLimitError, APIError) as e:
            #     if isinstance(e, RateLimitError):
            #         raise ClientRateLimitError(
            #             f"OpenAI rate limit exceeded: {str(e)}",
            #             client_name=self.client_name,
            #             original_error=e,
            #         )
            #     elif "quota" in str(e).lower():
            #         raise ClientQuotaExceededError(
            #             f"OpenAI quota exceeded: {str(e)}",
            #             client_name=self.client_name,
            #             original_error=e,
            #         )
            #     else:
            #         raise ClientError(
            #             f"OpenAI API error: {str(e)}",
            #             client_name=self.client_name,
            #             original_error=e,
            #         )
