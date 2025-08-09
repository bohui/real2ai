"""
Configuration for OpenAI client.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings

from ..base.client import ClientConfig


AVAILABLE_MODELS = {
    "deepseek-chat": "deepseek/deepseek-chat-v3-0324:free",
    "deepseek-reasoner": "deepseek/deepseek-r1-0528:free",
    "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
    "llama-3-1-405b": "meta-llama/llama-3.1-405b-instruct",
    "llama-3-1-8b": "meta-llama/llama-3.1-8b-instruct",
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
    # Default to a model known to work on OpenRouter; can be overridden via env
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

    # Base client settings
    openai_backoff_factor: float = 2.0
    openai_circuit_breaker_enabled: bool = True
    openai_failure_threshold: int = 5
    openai_circuit_timeout: int = 300  # 5 minutes for AI services

    # OpenRouter-compatible envs (optional). If present, they will be used.
    # This makes configuration resilient when users export OPENROUTER_* vars.
    openrouter_api_key: Optional[str] = None
    openrouter_api_base: Optional[str] = None  # If not set, we will default below
    openrouter_model_name: Optional[str] = None
    openrouter_http_referer: Optional[str] = None
    openrouter_x_title: Optional[str] = None

    class Config:
        env_file = [".env", ".env.local"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

    def to_client_config(self) -> OpenAIClientConfig:
        """Convert to OpenAIClientConfig.

        This method intelligently supports both standard OpenAI and OpenRouter
        environment variables. If any OPENROUTER_* variables are present, or the
        configured base URL refers to OpenRouter, we will prefer the OpenRouter
        API key and defaults.
        """
        # Determine if we should use OpenRouter specific defaults
        base_env = (self.openai_api_base or "").lower()
        model_env = self.openai_model_name or ""
        openrouter_env_present = bool(
            self.openrouter_api_key or ("openrouter.ai" in base_env)
        )

        use_openrouter = openrouter_env_present or ("/" in model_env)

        # Resolve effective API key and base URL
        if use_openrouter:
            effective_api_key = self.openrouter_api_key or self.openai_api_key
            # Prefer OpenRouter base when using OpenRouter models/keys
            effective_api_base = (
                self.openrouter_api_base
                or "https://openrouter.ai/api/v1"
            )
            effective_model = (
                self.openrouter_model_name
                or self.openai_model_name
                or DEFAULT_MODEL
            )
        else:
            effective_api_key = self.openai_api_key
            effective_api_base = self.openai_api_base
            effective_model = self.openai_model_name or DEFAULT_MODEL

        # Prepare optional default headers for OpenRouter
        default_headers: Dict[str, Any] = {}
        if use_openrouter:
            if self.openrouter_http_referer:
                default_headers["HTTP-Referer"] = self.openrouter_http_referer
            if self.openrouter_x_title:
                default_headers["X-Title"] = self.openrouter_x_title

        extra_config: Dict[str, Any] = {}
        if default_headers:
            extra_config["default_headers"] = default_headers
        extra_config["is_openrouter"] = use_openrouter

        return OpenAIClientConfig(
            # API settings
            api_key=effective_api_key or "",
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
