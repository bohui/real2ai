"""
Main Google Gemini client implementation.
"""

import logging
import os
from typing import Any, Dict, Optional
from google import genai
from google.genai.types import HarmCategory, HarmBlockThreshold
from google.auth import default
from google.auth.credentials import Credentials

from ..base.client import BaseClient, with_retry
from ..base.interfaces import AIOperations
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientQuotaExceededError,
)
from .config import GeminiClientConfig
from .ocr_client import GeminiOCRClient
from ...core.langsmith_config import langsmith_trace, log_trace_info

logger = logging.getLogger(__name__)


class GeminiClient(BaseClient, AIOperations):
    """Google Gemini client wrapper providing AI operations."""

    def __init__(self, config: GeminiClientConfig):
        super().__init__(config, "GeminiClient")
        self.config: GeminiClientConfig = config
        self._model: Optional[Any] = None
        self._ocr_client: Optional[GeminiOCRClient] = None

    @property
    def model(self):
        """Get the underlying Gemini model."""
        if not self._model:
            raise ClientError("Gemini model not initialized", self.client_name)
        return self._model

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

            # Set up safety settings
            safety_settings = self._get_safety_settings()

            # Create the generative model
            self._model = genai.GenerativeModel(
                model_name=self.config.model_name, safety_settings=safety_settings
            )

            # Test the connection
            await self._test_connection()

            # Initialize OCR client
            self._ocr_client = GeminiOCRClient(self._model, self.config)
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

            # Configure genai with credentials
            genai.configure(credentials=credentials)

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

    def _get_safety_settings(self) -> Dict:
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

        return {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
            HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        }

    async def _test_connection(self) -> None:
        """Test Gemini API connection."""
        try:
            # Simple test prompt
            test_prompt = "Test connection. Respond with 'OK'."
            response = self._model.generate_content(test_prompt)

            if not response.text:
                raise ClientConnectionError(
                    "Gemini API test failed: No response received",
                    client_name=self.client_name,
                )

            self.logger.debug(
                f"Gemini API connection test successful. Response: {response.text[:50]}..."
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
                    "max_file_size_mb": self.config.max_file_size / (1024 * 1024),
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

            if self._model:
                # Gemini model doesn't require explicit closing
                self._model = None

            self._initialized = False
            self.logger.info("Gemini client closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing Gemini client: {e}")
            raise ClientError(
                f"Error closing Gemini client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # AIOperations interface implementation

    @with_retry(max_retries=3, backoff_factor=2.0)
    @langsmith_trace(name="gemini_generate_content", run_type="llm")
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content based on a prompt."""
        try:
            log_trace_info("gemini_generate_content", prompt_length=len(prompt), model=self.config.model_name)
            self.logger.debug(f"Generating content for prompt: {prompt[:100]}...")

            # Execute in thread pool to avoid blocking
            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(prompt)
            )

            if not response.text:
                raise ClientError(
                    "No content generated from Gemini", client_name=self.client_name
                )

            self.logger.debug(f"Successfully generated {len(response.text)} characters")
            return response.text

        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
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

    @langsmith_trace(name="gemini_analyze_document", run_type="tool")
    async def analyze_document(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Analyze a document and extract information."""
        try:
            log_trace_info("gemini_analyze_document", content_type=content_type, content_size=len(content))
            self.logger.debug(f"Analyzing document of type: {content_type}")

            # Delegate to OCR client for document analysis
            result = await self.ocr.analyze_document(content, content_type, **kwargs)

            self.logger.debug("Document analysis completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="gemini_extract_text", run_type="tool")
    async def extract_text(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Extract text from a document using OCR."""
        try:
            log_trace_info("gemini_extract_text", content_type=content_type, content_size=len(content))
            self.logger.debug(f"Extracting text from document of type: {content_type}")

            # Delegate to OCR client
            result = await self.ocr.extract_text(content, content_type, **kwargs)

            self.logger.debug("Text extraction completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="gemini_classify_content", run_type="llm")
    async def classify_content(
        self, content: str, categories: list, **kwargs
    ) -> Dict[str, Any]:
        """Classify content into predefined categories."""
        try:
            log_trace_info("gemini_classify_content", content_length=len(content), categories_count=len(categories))
            self.logger.debug(f"Classifying content into {len(categories)} categories")

            # Create classification prompt
            categories_text = ", ".join(categories)
            prompt = f"""
            Classify the following content into one of these categories: {categories_text}
            
            Content:
            {content[:2000]}...
            
            Respond with only the category name that best fits this content.
            """

            classification = await self.generate_content(prompt)

            # Clean up the response
            classification = classification.strip()

            # Validate that the classification is in the provided categories
            if classification not in categories:
                # Try to find partial match
                classification_lower = classification.lower()
                for category in categories:
                    if (
                        category.lower() in classification_lower
                        or classification_lower in category.lower()
                    ):
                        classification = category
                        break
                else:
                    # If no match found, use the first category as default
                    classification = categories[0]

            result = {
                "classification": classification,
                "confidence": 0.8,  # Default confidence for now
                "categories": categories,
                "content_length": len(content),
            }

            self.logger.debug(f"Content classified as: {classification}")
            return result

        except Exception as e:
            self.logger.error(f"Content classification failed: {e}")
            raise ClientError(
                f"Content classification failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
