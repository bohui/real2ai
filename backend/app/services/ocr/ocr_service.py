"""
OCR Service - Orchestrates OCR operations with specialized processors.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from app.clients.base.client import with_retry
from app.clients.base.exceptions import ClientError, ClientValidationError
from .file_validator import FileValidator
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .document_analyzer import DocumentAnalyzer

logger = logging.getLogger(__name__)


class OCRService:
    """
    Service layer for OCR operations.
    Orchestrates the interaction between the thin Gemini client and specialized processors.
    """
    
    def __init__(self, gemini_client, config):
        self.client = gemini_client
        self.config = config
        
        # Initialize processors
        self.file_validator = FileValidator(
            max_file_size=config.max_file_size,
            supported_formats=config.supported_formats
        )
        self.pdf_processor = PDFProcessor(gemini_client)
        self.image_processor = ImageProcessor(gemini_client)
        self.document_analyzer = DocumentAnalyzer()
        
        self.logger = logger
        
    @with_retry(max_retries=3, backoff_factor=2.0)
    async def extract_text(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Extract text from document using appropriate processor."""
        try:
            self.logger.debug(f"Extracting text from {content_type} document")

            # Validate input
            self.file_validator.validate_file(content, content_type)

            # Pass config to processors
            kwargs['config'] = self.config

            # Determine processing method based on content type
            if content_type == "application/pdf":
                return await self.pdf_processor.extract_from_pdf(content, **kwargs)
            else:
                return await self.image_processor.extract_from_image(
                    content, content_type, **kwargs
                )

        except (ClientValidationError, ClientError):
            raise
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name="OCRService",
                original_error=e,
            )

    async def analyze_document(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Analyze document and extract structured information."""
        try:
            self.logger.debug(f"Analyzing {content_type} document")

            # First extract text
            extraction_result = await self.extract_text(content, content_type, **kwargs)

            # Add additional analysis
            extracted_text = extraction_result.get("extracted_text", "")

            if extracted_text and len(extracted_text.strip()) > 0:
                # Analyze the extracted text for document structure
                analysis_result = await self.document_analyzer.analyze_text_content(
                    extracted_text, **kwargs
                )

                # Combine extraction and analysis results
                result = {
                    **extraction_result,
                    "analysis": analysis_result,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                result = extraction_result
                result["analysis"] = {"error": "No text found to analyze"}

            self.logger.debug("Document analysis completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name="OCRService",
                original_error=e,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check OCR service health."""
        try:
            # Delegate to client for connectivity check
            client_health = await self.client.health_check()
            
            return {
                "status": "healthy",
                "service_name": "OCRService",
                "client_health": client_health,
                "processors_initialized": True,
                "max_file_size_mb": self.config.max_file_size / (1024 * 1024),
                "supported_formats": list(self.config.supported_formats),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service_name": "OCRService",
                "error": str(e),
                "processors_initialized": True,
            }