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
from .config import OpenAIClientConfig, DEFAULT_MODEL
from ...core.langsmith_config import langsmith_trace, log_trace_info
from .task_queue import OpenAILLMQueueManager

logger = logging.getLogger(__name__)


class OpenAIClient(BaseClient):
    """OpenAI client for connection and API management."""

    def __init__(self, config: OpenAIClientConfig):
        super().__init__(config, "OpenAIClient")
        self.config: OpenAIClientConfig = config
        self._openai_client: Optional[OpenAI] = None
        self._langchain_client: Optional[ChatOpenAI] = None

        # Round-robin API key pool
        self._api_keys: List[str] = []
        self._rr_index: int = 0
        self._rr_lock: asyncio.Lock = asyncio.Lock()
        # Per-key client caches
        self._openai_clients_by_key: Dict[str, OpenAI] = {}
        # Cache LangChain clients by (api_key, model)
        self._langchain_clients_by_key_model: Dict[str, ChatOpenAI] = {}

    async def _select_next_key(self) -> str:
        """Select the next API key using round-robin."""
        async with self._rr_lock:
            if not self._api_keys:
                return self.config.api_key
            key = self._api_keys[self._rr_index % len(self._api_keys)]
            self._rr_index = (self._rr_index + 1) % len(self._api_keys)
            return key

    def _get_or_create_openai_client_for(self, api_key: str) -> OpenAI:
        """Return an OpenAI client for a specific API key, creating it if missing."""
        if api_key in self._openai_clients_by_key:
            return self._openai_clients_by_key[api_key]

        client_kwargs: Dict[str, Any] = {
            "api_key": api_key,
            "timeout": self.config.request_timeout,
            "max_retries": self.config.max_retries,
        }
        if self.config.api_base:
            client_kwargs["base_url"] = self.config.api_base
        if self.config.organization:
            client_kwargs["organization"] = self.config.organization
        try:
            default_headers = self.config.extra_config.get("default_headers")  # type: ignore[attr-defined]
            if default_headers:
                client_kwargs["default_headers"] = default_headers
        except Exception:
            pass

        client = OpenAI(**client_kwargs)
        self._openai_clients_by_key[api_key] = client
        return client

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
        """Initialize OpenAI client."""
        try:
            self.logger.info("Initializing OpenAI client...")

            # Build API key pool from extra_config if provided
            api_keys_cfg = None
            try:
                api_keys_cfg = self.config.extra_config.get("api_keys")  # type: ignore[attr-defined]
            except Exception:
                api_keys_cfg = None

            api_keys: List[str] = []
            if isinstance(api_keys_cfg, list):
                api_keys = [k for k in api_keys_cfg if isinstance(k, str) and k.strip()]
            elif isinstance(api_keys_cfg, str):
                # Support comma-separated keys in a single string
                api_keys = [k.strip() for k in api_keys_cfg.split(",") if k.strip()]

            if not api_keys and self.config.api_key:
                api_keys = [self.config.api_key]

            # Filter out any empty strings defensively
            api_keys = [k for k in api_keys if isinstance(k, str) and k.strip()]

            if not api_keys:
                raise ClientAuthenticationError(
                    "No OpenAI API keys configured. Set OPENAI_API_KEYS (comma-separated or JSON) or OPENAI_API_KEY.",
                    client_name=self.client_name,
                )

            self._api_keys = api_keys
            pool_size = len(self._api_keys)
            self.logger.info(f"Configured OpenAI API key pool size: {pool_size}")

            # Create OpenAI client
            client_kwargs = {
                # Use first key for initial client; others are created lazily
                "api_key": self._api_keys[0],
                "timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            }

            if self.config.api_base:
                client_kwargs["base_url"] = self.config.api_base

            if self.config.organization:
                client_kwargs["organization"] = self.config.organization

            # If configured, attach default headers (e.g., for OpenRouter)
            try:
                default_headers = self.config.extra_config.get("default_headers")  # type: ignore[attr-defined]
                if default_headers:
                    client_kwargs["default_headers"] = default_headers
            except Exception:
                pass

            self._openai_client = OpenAI(**client_kwargs)
            self._openai_clients_by_key[self._api_keys[0]] = self._openai_client

            # Initialize LangChain ChatOpenAI client for LangSmith tracing
            langchain_kwargs = {
                "openai_api_key": self._api_keys[0],
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "request_timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            }

            if self.config.api_base:
                langchain_kwargs["openai_api_base"] = self.config.api_base

            if self.config.organization:
                langchain_kwargs["openai_organization"] = self.config.organization

            # Remove None values
            langchain_kwargs = {
                k: v for k, v in langchain_kwargs.items() if v is not None
            }

            self._langchain_client = ChatOpenAI(**langchain_kwargs)
            self._langchain_clients_by_key_model[
                f"{self._api_keys[0]}|{self.config.model_name}"
            ] = self._langchain_client

            # Test the connection (optionally, and with timeout)
            should_test = bool(
                self.config.extra_config.get("init_connection_test", True)
            )
            if should_test:
                test_timeout = int(
                    self.config.extra_config.get("init_test_timeout", 12)
                )

                async def _run_test_with_timeout():
                    await self._test_connection()

                try:
                    await asyncio.wait_for(
                        _run_test_with_timeout(), timeout=test_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"OpenAI connection test exceeded {test_timeout}s. Proceeding without blocking startup."
                    )

            self._initialized = True
            self.logger.info(
                "OpenAI client and LangChain ChatOpenAI initialized successfully"
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
            # Simple test with a minimal completion
            # Prefer chat.completions for modern providers and OpenRouter
            test_messages = [{"role": "user", "content": "ping"}]

            # Use queue even for connection tests to respect global backoff
            async def _run_test(model_to_use: str, messages: list) -> Any:
                queue = OpenAILLMQueueManager.get_queue(model_to_use)
                # Use the first key's client for initialization test
                key_for_test = (
                    self._api_keys[0] if self._api_keys else self.config.api_key
                )
                openai_client = self._get_or_create_openai_client_for(key_for_test)
                return await queue.run_in_executor(
                    lambda: openai_client.chat.completions.create(
                        model=model_to_use,
                        messages=messages,
                        max_tokens=1,
                        temperature=0,
                    )
                )

            response = await _run_test(self.config.model_name, test_messages)

            if not getattr(response, "choices", None):
                # Retry once quickly with a slightly different prompt
                self.logger.warning(
                    "OpenAI API test returned no choices. Retrying once immediately..."
                )
                retry_messages = [{"role": "user", "content": "healthcheck"}]
                response = await _run_test(self.config.model_name, retry_messages)

            if not getattr(response, "choices", None):
                # As a last resort, try a known working default model (useful with OpenRouter)
                if self.config.model_name != DEFAULT_MODEL:
                    self.logger.warning(
                        f"Connection test still empty. Trying fallback model: {DEFAULT_MODEL}"
                    )
                    response = await _run_test(DEFAULT_MODEL, test_messages)

            # Determine success
            if getattr(response, "choices", None):
                self.logger.debug("OpenAI API connection test successful")
                return
            # Some providers return id/usage but empty choices on test prompts; treat as success if id present
            if hasattr(response, "id"):
                self.logger.warning(
                    "OpenAI API test returned empty choices but had an id; treating as success"
                )
                return

            raise ClientConnectionError(
                "OpenAI API test failed: No response received",
                client_name=self.client_name,
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
            # If the configured model is invalid for the provider, try the fallback once
            if any(
                term in message_lower
                for term in ["model", "not found", "does not exist", "invalid"]
            ):
                try:
                    self.logger.warning(
                        f"Model error during connection test: {e}. Trying fallback model: {DEFAULT_MODEL}"
                    )
                    queue = OpenAILLMQueueManager.get_queue(DEFAULT_MODEL)
                    key_for_test = (
                        self._api_keys[0] if self._api_keys else self.config.api_key
                    )
                    openai_client = self._get_or_create_openai_client_for(key_for_test)
                    _ = await queue.run_in_executor(
                        lambda: openai_client.chat.completions.create(
                            model=DEFAULT_MODEL,
                            messages=[{"role": "user", "content": "ping"}],
                            max_tokens=1,
                            temperature=0,
                        )
                    )
                    self.logger.debug("Fallback model connection test successful")
                    return
                except Exception as inner_e:
                    raise ClientConnectionError(
                        f"OpenAI API connection test failed after fallback: {str(inner_e)}",
                        client_name=self.client_name,
                        original_error=inner_e,
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

            # Resolve model and select API key via round-robin
            model_to_use = kwargs.get("model", self.config.model_name)
            selected_key = await self._select_next_key()

            # Get or create a per-key, per-model LangChain client
            langchain_client = self._get_or_create_langchain_client_for(
                selected_key,
                model_to_use,
                temperature=kwargs.get("temperature"),
                max_tokens=kwargs.get("max_tokens"),
                top_p=kwargs.get("top_p"),
                frequency_penalty=kwargs.get("frequency_penalty"),
                presence_penalty=kwargs.get("presence_penalty"),
            )

            # Call LangChain ChatOpenAI through queue system for rate limiting
            # Use a per-(model,key) queue to isolate 429 backoffs across keys
            queue_key = f"{model_to_use}|{selected_key[:6]}"
            queue = OpenAILLMQueueManager.get_queue(queue_key)
            if hasattr(langchain_client, "ainvoke"):
                response = await queue.run_async(
                    lambda: langchain_client.ainvoke(langchain_messages)
                )
            else:
                response = await queue.run_in_executor(
                    lambda: langchain_client.invoke(langchain_messages)
                )

            if not response.content:
                raise ClientError(
                    "No content generated from OpenAI", client_name=self.client_name
                )

            return response.content

        except Exception as langchain_error:
            # raise error to trigger retry
            self.logger.warning(f"LangChain call failed, retrying: {langchain_error}")
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
