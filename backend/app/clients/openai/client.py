"""
Main OpenAI client implementation.
"""

import logging
from typing import Any, Dict, Optional, List
from openai import OpenAI
from openai import RateLimitError, APIError, AuthenticationError

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

    @property
    def openai_client(self) -> OpenAI:
        """Get the underlying OpenAI client."""
        if not self._openai_client:
            raise ClientError("OpenAI client not initialized", self.client_name)
        return self._openai_client

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            self.logger.info("Initializing OpenAI client...")

            # Create OpenAI client
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            }

            if self.config.api_base:
                client_kwargs["base_url"] = self.config.api_base

            if self.config.organization:
                client_kwargs["organization"] = self.config.organization

            self._openai_client = OpenAI(**client_kwargs)

            # Test the connection
            await self._test_connection()

            self._initialized = True
            self.logger.info("OpenAI client initialized successfully")

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
                return await queue.run_in_executor(
                    lambda: self._openai_client.chat.completions.create(
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
                    _ = await queue.run_in_executor(
                        lambda: self._openai_client.chat.completions.create(
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

            self._initialized = False
            self.logger.info("OpenAI client closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing OpenAI client: {e}")
            raise ClientError(
                f"Error closing OpenAI client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # Core API Methods - Connection Layer Only

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Call OpenAI API to generate content."""
        try:
            # Handle both single prompt and messages format
            if "messages" in kwargs:
                messages = kwargs["messages"]
            else:
                messages = [{"role": "user", "content": prompt}]

            # Prepare parameters
            params = {
                "model": kwargs.get("model", self.config.model_name),
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty", self.config.frequency_penalty
                ),
                "presence_penalty": kwargs.get(
                    "presence_penalty", self.config.presence_penalty
                ),
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            # Execute via task queue for rate limiting
            queue = OpenAILLMQueueManager.get_queue(params.get("model"))
            response = await queue.run_in_executor(
                lambda: self.openai_client.chat.completions.create(**params)
            )

            if not response.choices or not response.choices[0].message.content:
                raise ClientError(
                    "No content generated from OpenAI", client_name=self.client_name
                )

            return response.choices[0].message.content

        except (RateLimitError, APIError) as e:
            if isinstance(e, RateLimitError):
                raise ClientRateLimitError(
                    f"OpenAI rate limit exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            elif "quota" in str(e).lower():
                raise ClientQuotaExceededError(
                    f"OpenAI quota exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            else:
                raise ClientError(
                    f"OpenAI API error: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
        except Exception as e:
            raise ClientError(
                f"Content generation failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

