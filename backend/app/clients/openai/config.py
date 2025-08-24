"""
Configuration for OpenAI client.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import os
import json
from pydantic_settings import BaseSettings

from ..base.client import ClientConfig


AVAILABLE_MODELS = {
    "deepseek-chat": "deepseek/deepseek-chat-v3-0324:free",
    "deepseek-reasoner": "deepseek/deepseek-r1-0528:free",
    "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
    "llama-3-1-405b": "meta-llama/llama-3.1-405b-instruct",
    "llama-3-1-8b": "meta-llama/llama-3.1-8b-instruct",
    "qwen3-coder": "qwen/qwen3-coder:free",
}
DEFAULT_MODEL = AVAILABLE_MODELS["deepseek-chat"]
DEFAULT_REASON_MODEL = AVAILABLE_MODELS["deepseek-reasoner"]


@dataclass(kw_only=True)
class OpenAIClientConfig(ClientConfig):
    """Configuration for OpenAI client."""

    # OpenAI API settings
    api_key: str
    api_base: Optional[str] = None
    model_name: str = DEFAULT_MODEL

    # Model parameters
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # Request settings
    request_timeout: int = 60
    max_retries: int = 3

    # Organization settings
    organization: Optional[str] = None


class OpenAISettings(BaseSettings):
    """Pydantic settings for OpenAI configuration from environment."""

    # Standard OpenAI-style envs
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    # Default model; can be overridden via env
    openai_model_name: str = DEFAULT_MODEL
    openai_organization: Optional[str] = None

    # Model parameters
    openai_temperature: float = 0.1
    openai_max_tokens: Optional[int] = None
    openai_top_p: float = 1.0
    openai_frequency_penalty: float = 0.0
    openai_presence_penalty: float = 0.0

    # Request settings
    openai_request_timeout: int = 60
    openai_max_retries: int = 3

    # Initialization behavior
    openai_init_connection_test: bool = True
    openai_init_test_timeout: int = 12

    # Base client settings
    openai_backoff_factor: float = 2.0
    openai_circuit_breaker_enabled: bool = True
    openai_failure_threshold: int = 5
    openai_circuit_timeout: int = 300  # 5 minutes for AI services

    # API key pool support (comma-separated string or JSON array)
    openai_api_keys: Optional[str] = None

    model_config = {
        "env_file": [".env", ".env.local"],
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }

    def to_client_config(self) -> OpenAIClientConfig:
        """Convert to OpenAIClientConfig using standard OpenAI environment variables."""
        # Resolve effective API key and base URL from OPENAI_* env vars
        effective_api_key = self.openai_api_key or ""
        effective_api_base = self.openai_api_base or "https://api.openai.com/v1"
        effective_model = self.openai_model_name or DEFAULT_MODEL

        # Parse API key pool from env (supports comma-separated or JSON array)
        def _parse_api_keys(raw: Optional[str]) -> List[str]:
            if not raw:
                return []
            raw = raw.strip()
            if not raw:
                return []
            # Try JSON first
            if (raw.startswith("[") and raw.endswith("]")) or (
                raw.startswith("\n[") and raw.rstrip().endswith("]")
            ):
                try:
                    data = json.loads(raw)
                    if isinstance(data, list):
                        return [str(x).strip() for x in data if str(x).strip()]
                except Exception:
                    pass
            # Fallback: comma-separated
            return [part.strip() for part in raw.split(",") if part.strip()]

        pool_keys = _parse_api_keys(self.openai_api_keys)

        # If not explicitly provided, auto-assemble from numbered env vars
        if not pool_keys:
            prefix = "OPENAI_API_KEY"

            def _suffix_num(name: str) -> Tuple[int, str]:
                # Return (sort_key, name) where base var (no number) sorts first as 0
                suffix = name[len(prefix) :]
                if suffix == "":
                    return (0, name)
                try:
                    return (int(suffix), name)
                except Exception:
                    return (999999, name)

            candidates: List[Tuple[int, str]] = []
            for env_name, env_val in os.environ.items():
                if not env_val or not isinstance(env_val, str):
                    continue
                env_upper = env_name.upper()
                if env_upper == prefix or env_upper.startswith(prefix):
                    candidates.append(_suffix_num(env_upper))

            candidates.sort(key=lambda x: x[0])
            resolved: List[str] = []
            for _, name in candidates:
                val = os.environ.get(name) or os.environ.get(name.lower())
                if val and val.strip():
                    resolved.append(val.strip())
            pool_keys = resolved
        # Ensure the effective key is present if defined
        if effective_api_key and effective_api_key not in pool_keys:
            pool_keys = [effective_api_key] + pool_keys

        extra_config: Dict[str, Any] = {}
        # Initialization behavior controls
        extra_config["init_connection_test"] = self.openai_init_connection_test
        extra_config["init_test_timeout"] = self.openai_init_test_timeout
        # Inject API key pool if provided
        if pool_keys:
            extra_config["api_keys"] = pool_keys

        return OpenAIClientConfig(
            # API settings
            api_key=effective_api_key,
            api_base=effective_api_base,
            model_name=effective_model,
            organization=self.openai_organization,
            # Model parameters
            temperature=self.openai_temperature,
            max_tokens=self.openai_max_tokens,
            top_p=self.openai_top_p,
            frequency_penalty=self.openai_frequency_penalty,
            presence_penalty=self.openai_presence_penalty,
            # Request settings
            request_timeout=self.openai_request_timeout,
            # Base client settings
            timeout=self.openai_request_timeout,
            max_retries=self.openai_max_retries,
            backoff_factor=self.openai_backoff_factor,
            circuit_breaker_enabled=self.openai_circuit_breaker_enabled,
            failure_threshold=self.openai_failure_threshold,
            circuit_timeout=self.openai_circuit_timeout,
            # Extras
            extra_config=extra_config,
        )
