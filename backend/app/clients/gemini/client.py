"""
Main Google Gemini client implementation.
"""

import logging
import os
from typing import Any, Dict, Optional
from google import genai
from google.genai.types import (
    Part,
    Content,
    HarmCategory,
    HarmBlockThreshold,
    SafetySetting,
    GenerateContentConfig,
)
from google.auth import default

from ..base.client import BaseClient, with_retry
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientQuotaExceededError,
)
from .config import GeminiClientConfig
from .ocr_client import GeminiOCRClient
from ...core.langsmith_config import langsmith_trace

logger = logging.getLogger(__name__)

# Constants to replace magic numbers
BYTES_PER_MB = 1024 * 1024
RESPONSE_PREVIEW_LENGTH = 50
PROMPT_PREVIEW_LENGTH = 100
CONTENT_PREVIEW_LENGTH = 2000


class GeminiClient(BaseClient):
    """Google Gemini client for connection and API management."""

    def __init__(self, config: GeminiClientConfig):
        super().__init__(config, "GeminiClient")
        self.config: GeminiClientConfig = config
        self._client: Optional[genai.Client] = None
        self._ocr_client: Optional[GeminiOCRClient] = None

    @property
    def client(self):
        """Get the underlying Gemini client."""
        if not self._client:
            raise ClientError("Gemini client not initialized", self.client_name)
        return self._client

    @property
    def ocr(self) -> GeminiOCRClient:
        """Get the OCR client."""
        if not self._ocr_client:
            raise ClientError("OCR client not initialized", self.client_name)
        return self._ocr_client

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def initialize(self) -> None:
        """Initialize Gemini client with service role authentication."""
        try:
            self.logger.info(
                "Initializing Gemini client with service role authentication..."
            )

            # Configure Gemini API with service role authentication
            self.logger.info(
                "Using service role authentication via Application Default Credentials"
            )
            await self._configure_service_role_auth()

            # Test the connection
            await self._test_connection()

            # Initialize OCR client
            self._ocr_client = GeminiOCRClient(self._client, self.config)
            await self._ocr_client.initialize()

            self._initialized = True
            self.logger.info(
                "Gemini client initialized successfully with service role authentication"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize Gemini client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def _configure_service_role_auth(self) -> None:
        """Configure Gemini API with service role authentication using Application Default Credentials."""
        try:
            # Determine credentials path
            credentials_path = self.config.credentials_path or os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS"
            )

            if credentials_path:
                self.logger.info(
                    f"Using service account credentials from: {credentials_path}"
                )
                if not os.path.exists(credentials_path):
                    raise ClientAuthenticationError(
                        f"Service account credentials file not found: {credentials_path}",
                        client_name=self.client_name,
                    )
                # Set environment variable if provided via config
                if self.config.credentials_path:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            else:
                self.logger.info(
                    "Using Application Default Credentials (metadata server or gcloud auth)"
                )

            # Get default credentials with required scopes
            credentials, project_id = default(
                scopes=["https://www.googleapis.com/auth/generative-language"]
            )

            if not credentials:
                raise ClientAuthenticationError(
                    "Unable to obtain Application Default Credentials. "
                    "Please ensure service account is properly configured or run 'gcloud auth application-default login'",
                    client_name=self.client_name,
                )

            # Use configured project ID if available
            if self.config.project_id:
                project_id = self.config.project_id
                self.logger.info(f"Using configured project ID: {project_id}")

            # Create the client with vertexai parameters
            self._client = genai.Client(
                vertexai=True,
                project=project_id,
                location=self.config.location,
            )

            self.logger.info(
                f"Service role authentication configured successfully"
                + (f" for project: {project_id}" if project_id else "")
            )

        except Exception as e:
            if isinstance(e, ClientAuthenticationError):
                raise

            self.logger.error(f"Service role authentication configuration failed: {e}")
            raise ClientAuthenticationError(
                f"Failed to configure service role authentication: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def _get_safety_settings(self) -> list[SafetySetting]:
        """Get safety settings for Gemini model."""
        threshold_map = {
            "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
            "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        }

        threshold = threshold_map.get(
            self.config.harm_block_threshold, HarmBlockThreshold.BLOCK_NONE
        )

        return [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=threshold
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=threshold
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=threshold,
            ),
        ]

    async def _test_connection(self) -> None:
        """Test Gemini API connection."""
        try:
            # Simple test prompt
            test_prompt = "Test connection. Respond with 'OK'."

            # Create content for the test
            content = Content(role="user", parts=[Part.from_text(text=test_prompt)])

            # Generate content
            response = self._client.models.generate_content(
                model=self.config.model_name,
                contents=[content],
                config=GenerateContentConfig(
                    safety_settings=self._get_safety_settings()
                ),
            )

            if not getattr(response, "candidates", None):
                raise ClientConnectionError(
                    "Gemini API test failed: No response candidates",
                    client_name=self.client_name,
                )

            response_text = self._extract_text_from_response(response)
            self.logger.debug(
                f"Gemini API connection test successful. Response: {response_text[:RESPONSE_PREVIEW_LENGTH]}..."
            )

        except Exception as e:
            error_message = str(e).upper()

            # Enhanced error categorization for service account authentication
            if any(
                keyword in error_message
                for keyword in [
                    "API_KEY",
                    "AUTHENTICATION",
                    "UNAUTHORIZED",
                    "FORBIDDEN",
                ]
            ):
                auth_method = "service account"
                raise ClientAuthenticationError(
                    f"Gemini API authentication failed using {auth_method}: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            elif any(
                keyword in error_message
                for keyword in ["QUOTA", "LIMIT", "EXCEEDED", "RATE"]
            ):
                raise ClientQuotaExceededError(
                    f"Gemini API quota/rate limit exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            elif any(
                keyword in error_message
                for keyword in ["PERMISSION", "ACCESS", "SCOPE"]
            ):
                raise ClientAuthenticationError(
                    f"Gemini API permission/scope error: {str(e)}. "
                    f"Check if service account has required permissions for Generative Language API",
                    client_name=self.client_name,
                    original_error=e,
                )
            elif any(
                keyword in error_message
                for keyword in ["NETWORK", "CONNECTION", "TIMEOUT"]
            ):
                raise ClientConnectionError(
                    f"Gemini API network/connection error: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            else:
                raise ClientConnectionError(
                    f"Gemini API connection test failed: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Gemini client."""
        try:
            # Test API connection
            await self._test_connection()

            # Check OCR client
            ocr_health = (
                await self._ocr_client.health_check()
                if self._ocr_client
                else {"status": "not_initialized"}
            )

            # Authentication method is always service account
            auth_method = "service_account"

            # Get service account credentials info
            credentials_path = self.config.credentials_path or os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS"
            )
            credentials_info = {
                "credentials_path": credentials_path,
                "project_id": self.config.project_id,
                "env_var_set": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            }

            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "model_name": self.config.model_name,
                "connection": "ok",
                "authentication": {
                    "method": auth_method,
                    "service_account_enabled": True,
                    **credentials_info,
                },
                "ocr_status": ocr_health.get("status", "unknown"),
                "config": {
                    "model_name": self.config.model_name,
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                    "max_file_size_mb": self.config.max_file_size / BYTES_PER_MB,
                    "service_account_only": True,
                },
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            error_type = type(e).__name__
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "error_type": error_type,
                "initialized": self._initialized,
                "authentication": {
                    "method": "service_account",
                    "service_account_enabled": True,
                },
            }

    async def close(self) -> None:
        """Close Gemini client and clean up resources."""
        try:
            if self._ocr_client:
                await self._ocr_client.close()
                self._ocr_client = None

            if self._client:
                # Client doesn't require explicit closing
                self._client = None

            self._initialized = False
            self.logger.info("Gemini client closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing Gemini client: {e}")
            raise ClientError(
                f"Error closing Gemini client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # Core API Methods - Connection Layer Only

    @langsmith_trace(name="gemini_client_generate_content", run_type="llm")
    @with_retry(max_retries=3, backoff_factor=2.0)
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Call Gemini API to generate content.

        Accepted kwargs include:
        - temperature: Optional[float]
        - top_p: Optional[float]
        - max_tokens: Optional[int]
        - system_prompt: Optional[str] - if provided, will be passed as
          system_instruction to guide the model.
        - model: Optional[str] - override configured model name.
        """
        try:
            # Create content for the prompt
            content = genai.types.Content(
                role="user", parts=[genai.types.Part(text=prompt)]
            )

            # Create generation config
            generation_config = GenerateContentConfig(
                safety_settings=self._get_safety_settings(),
                temperature=kwargs.get("temperature", 0.1),
                top_p=kwargs.get("top_p", 1.0),
                max_output_tokens=kwargs.get("max_tokens"),
                system_instruction=kwargs.get("system_prompt"),
                response_mime_type="application/json",
                response_schema=kwargs.get("response_schema"),
            )

            # Execute in thread pool to avoid blocking
            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=kwargs.get("model", self.config.model_name),
                    contents=[content],
                    config=generation_config,
                ),
            )

            if not getattr(response, "candidates", None):
                # Add more diagnostics to logs to help root-cause
                self.logger.error(
                    "Gemini returned no candidates",
                    extra={
                        "operation": "generate_content",
                        "model": kwargs.get("model", self.config.model_name),
                    },
                )
                raise ClientError(
                    "No content generated from Gemini (no candidates)",
                    client_name=self.client_name,
                )

            response_text = self._extract_text_from_response(response)
            return response_text

        except Exception as e:
            if "QUOTA" in str(e).upper() or "LIMIT" in str(e).upper():
                raise ClientQuotaExceededError(
                    f"Gemini quota exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            else:
                raise ClientError(
                    f"Content generation failed: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

    async def analyze_document(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Delegate document analysis to OCR client."""
        try:
            # Delegate to OCR client for document analysis
            result = await self.ocr.analyze_document(content, content_type, **kwargs)
            return result

        except Exception as e:
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def extract_text(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Delegate text extraction to OCR client."""
        try:
            # Delegate to OCR client
            result = await self.ocr.extract_text(content, content_type, **kwargs)
            return result

        except Exception as e:
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="gemini_analyze_image_semantics", run_type="llm")
    async def analyze_image_semantics(
        self, content: bytes, content_type: str, analysis_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze image semantics using multimodal capabilities."""
        try:
            # Create multimodal content
            parts = [
                Part.from_text(
                    text=analysis_context.get("prompt", "Analyze this image")
                ),
                Part.from_bytes(data=content, mime_type=content_type),
            ]
            content_obj = Content(role="user", parts=parts)

            # Create generation config with optional system instruction
            config_kwargs = {"safety_settings": self._get_safety_settings()}

            # Add system instruction if provided
            if (
                "system_prompt" in analysis_context
                and analysis_context["system_prompt"]
            ):
                config_kwargs["system_instruction"] = analysis_context["system_prompt"]

            generate_config = GenerateContentConfig(**config_kwargs)

            # Generate analysis
            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.config.model_name,
                    contents=[content_obj],
                    config=generate_config,
                ),
            )

            if not getattr(response, "candidates", None):
                raise ClientError(
                    "No analysis candidates returned", client_name=self.client_name
                )

            return {
                "content": self._extract_text_from_response(response),
                "analysis_type": "image_semantics",
            }

        except Exception as e:
            raise ClientError(
                f"Image analysis failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="gemini_analyze_image_semantics_batch", run_type="llm")
    async def analyze_image_semantics_batch(
        self, *, contents: list[dict[str, Any]], analysis_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze semantics for multiple images in a single request.

        contents: list of {"content": bytes, "content_type": str, "filename": Optional[str]}
        """
        try:
            # Build a single multimodal content: prompt + multiple images
            parts: list[Part] = [
                Part.from_text(
                    text=analysis_context.get("prompt", "Analyze these images")
                )
            ]
            for item in contents or []:
                if not isinstance(item, dict):
                    continue
                data = item.get("content")
                mime = item.get("content_type") or "image/jpeg"
                if not data:
                    continue
                parts.append(Part.from_bytes(data=data, mime_type=mime))

            content_obj = Content(role="user", parts=parts)

            # Create generation config with optional system instruction
            config_kwargs = {"safety_settings": self._get_safety_settings()}
            if analysis_context.get("system_prompt"):
                config_kwargs["system_instruction"] = analysis_context["system_prompt"]

            generate_config = GenerateContentConfig(**config_kwargs)

            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.config.model_name,
                    contents=[content_obj],
                    config=generate_config,
                ),
            )

            if not getattr(response, "candidates", None):
                raise ClientError(
                    "No analysis candidates returned (batch)",
                    client_name=self.client_name,
                )

            return {
                "content": self._extract_text_from_response(response),
                "analysis_type": "image_semantics_batch",
            }

        except Exception as e:
            raise ClientError(
                f"Image analysis batch failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # ------------------------
    # Internal helpers
    # ------------------------
    def _extract_text_from_response(self, response: Any) -> str:
        """Safely extract text from a Gemini response.

        This handles cases where content/parts may be None or the first part does not
        contain text. It attempts sensible fallbacks and raises a ClientError with
        helpful diagnostics if no text can be found.
        """
        try:
            # Some SDK versions expose a convenient text field
            text_attr = getattr(response, "text", None)
            if isinstance(text_attr, str) and text_attr.strip():
                return text_attr

            candidates = getattr(response, "candidates", None) or []
            for idx, candidate in enumerate(candidates):
                content_obj = getattr(candidate, "content", None)
                if not content_obj:
                    continue
                parts = getattr(content_obj, "parts", None) or []
                texts: list[str] = []
                for p in parts:
                    # Parts can be text or other modalities
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t:
                        texts.append(t)
                if texts:
                    return "\n".join(texts)

            # If we reach here, we couldn't extract any text. Log diagnostics.
            preview = str(response)
            if len(preview) > CONTENT_PREVIEW_LENGTH:
                preview = preview[:CONTENT_PREVIEW_LENGTH] + "…"
            self.logger.error(
                "Failed to extract text from Gemini response",
                extra={
                    "operation": "_extract_text_from_response",
                    "candidates_count": len(getattr(response, "candidates", []) or []),
                    "response_preview": preview,
                },
            )
            raise ClientError(
                "Gemini returned candidates but no textual parts were found",
                client_name=self.client_name,
            )
        except ClientError:
            raise
        except Exception as e:
            # Wrap any unexpected errors
            raise ClientError(
                f"Failed to parse Gemini response: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
