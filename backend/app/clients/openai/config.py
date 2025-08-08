"""
Configuration for OpenAI client.
"""

from dataclasses import dataclass
from typing import Optional
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

    openai_api_key: str
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

    class Config:
        env_file = [".env", ".env.local"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

    def to_client_config(self) -> OpenAIClientConfig:
        """Convert to OpenAIClientConfig."""
        return OpenAIClientConfig(
            # API settings
            api_key=self.openai_api_key,
            api_base=self.openai_api_base,
            model_name=self.openai_model_name,
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
        )
