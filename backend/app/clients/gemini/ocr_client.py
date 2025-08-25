"""
Gemini OCR client - Thin client for connection management only.
"""

import asyncio
import io
import logging
from typing import Any, Dict, Optional
from PIL import Image
from google.genai.types import Content, Part, GenerateContentConfig

from ..base.client import with_retry
from ..base.exceptions import ClientError
from .config import GeminiClientConfig

logger = logging.getLogger(__name__)

# Constants for testing
TEST_IMAGE_WIDTH = 100
TEST_IMAGE_HEIGHT = 50


class GeminiOCRClient:
    """Gemini OCR operations client."""

    def __init__(self, gemini_client, config: GeminiClientConfig):
        """
        Initialize thin OCR client.

        Args:
            gemini_client: The underlying Gemini API client
            config: Client configuration
        """
        self.client = gemini_client
        self.config = config
        self.client_name = "GeminiOCRClient"
        self.logger = logging.getLogger(f"{__name__}.{self.client_name}")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize OCR client."""
        try:
            # Test OCR capability with a simple operation
            await self._test_ocr_capability()
            self._initialized = True
            self.logger.info("OCR client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OCR client: {e}")
            raise ClientError(
                f"Failed to initialize OCR client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def _test_ocr_capability(self) -> None:
        """Test OCR capability with a simple test."""
        try:
            # Create a simple test image programmatically
            test_image = Image.new(
                "RGB", (TEST_IMAGE_WIDTH, TEST_IMAGE_HEIGHT), color="white"
            )

            # Convert to bytes
            img_buffer = io.BytesIO()
            test_image.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

            # Test OCR on the simple image
            prompt = "What text is visible in this image? If no text, respond with 'No text found'."

            # Create content with image
            content = Content(
                role="user",
                parts=[
                    Part.from_text(text=prompt),
                    Part.from_bytes(data=img_bytes, mime_type="image/png"),
                ],
            )

            # Call the API
            await self.generate_content(content)
            self.logger.debug("OCR capability test successful")

        except Exception as e:
            raise ClientError(
                f"OCR capability test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def generate_content(
        self, content: Content, config: Optional[GenerateContentConfig] = None
    ) -> Dict[str, Any]:
        """
        Send content to Gemini API for processing.

        This is the ONLY method that should interact with the Gemini API.
        All business logic should be in the service layer.

        Args:
            content: The content to send to Gemini
            config: Optional generation configuration

        Returns:
            Response from Gemini API
        """
        try:
            if config is None:
                config = GenerateContentConfig(temperature=0.1)

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.config.model_name, contents=[content], config=config
                ),
            )

            if not getattr(response, "candidates", None):
                raise ClientError(
                    "No response candidates received from Gemini",
                    client_name=self.client_name,
                )

            # Extract text from response safely
            text = self._extract_text_from_response(response)

            return {
                "text": text,
                "raw_response": response,
                "model": self.config.model_name,
            }

        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise ClientError(
                f"Gemini API call failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def _extract_text_from_response(self, response: Any) -> str:
        """Safely extract text from a Gemini response for OCR flows."""
        try:
            # Fast path if SDK provides a text attribute
            text_attr = getattr(response, "text", None)
            if isinstance(text_attr, str) and text_attr.strip():
                return text_attr

            candidates = getattr(response, "candidates", None) or []
            for candidate in candidates:
                content_obj = getattr(candidate, "content", None)
                if not content_obj:
                    continue
                parts = getattr(content_obj, "parts", None) or []
                texts: list[str] = []
                for part in parts:
                    t = getattr(part, "text", None)
                    if isinstance(t, str) and t:
                        texts.append(t)
                if texts:
                    return "\n".join(texts)

            # As a last resort, attempt str() preview for diagnostics
            preview = str(response)
            self.logger.error(
                "OCR: Failed to extract text from Gemini response",
                extra={
                    "candidates_count": len(candidates),
                    "response_preview": preview[:1000],
                },
            )
            return ""
        except Exception as e:
            # Do not raise here — OCR service may still proceed with empty text fallback
            self.logger.error(f"OCR: Exception while extracting text: {e}")
            return ""

    async def health_check(self) -> Dict[str, Any]:
        """Check OCR client health."""
        try:
            await self._test_ocr_capability()
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "model_available": self.client is not None,
                "model_name": self.config.model_name,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """Close OCR client."""
        self._initialized = False
        self.logger.info("OCR client closed successfully")
