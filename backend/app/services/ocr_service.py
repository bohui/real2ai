"""
OCR Service - DEPRECATED
This basic OCR service has been superseded by GeminiOCRService which provides:
- Advanced semantic analysis capabilities
- PromptManager integration for better context awareness
- Performance optimization with OCRPerformanceService
- Enhanced property document intelligence

Please use GeminiOCRService instead:
    from app.services.gemini_ocr_service import GeminiOCRService

This module will be removed in a future version.
"""

import logging
import asyncio
import warnings
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, UTC
from pathlib import Path
import mimetypes

from app.core.config import get_settings
from app.clients import get_gemini_client
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)
from app.core.langsmith_config import langsmith_trace, log_trace_info

logger = logging.getLogger(__name__)


class OCRCapabilities:
    """OCR service capabilities and configuration"""

    def __init__(self):
        self.supported_formats = [
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
            "tiff",
            "webp",
        ]
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.confidence_threshold = 0.6
        self.retry_attempts = 2

    def is_supported_format(self, file_type: str) -> bool:
        """Check if file format is supported for OCR"""
        return file_type.lower() in self.supported_formats

    def estimate_processing_time(self, file_size: int, file_type: str) -> int:
        """Estimate processing time in seconds"""
        base_time = 10  # Base 10 seconds
        size_factor = file_size / (1024 * 1024)  # Size in MB

        # Different file types have different processing complexities
        type_multipliers = {
            "pdf": 1.5,
            "png": 1.0,
            "jpg": 0.8,
            "jpeg": 0.8,
            "tiff": 1.3,
            "bmp": 1.2,
            "webp": 1.0,
            "gif": 1.1,
        }

        multiplier = type_multipliers.get(file_type.lower(), 1.0)
        return int(base_time + (size_factor * 2 * multiplier))


class OCRService:
    """Service for Optical Character Recognition with multiple provider support

    DEPRECATED: This service has been superseded by GeminiOCRService.
    Please use GeminiOCRService for enhanced semantic analysis and property intelligence.
    """

    def __init__(self):
        warnings.warn(
            "OCRService is deprecated and will be removed in a future version. "
            "Please use GeminiOCRService instead for advanced OCR capabilities.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.settings = get_settings()
        self.gemini_client = None
        self.capabilities = OCRCapabilities()
        self._initialized = False

    async def initialize(self):
        """Initialize OCR service with available providers"""
        try:
            # Initialize Gemini client for OCR
            self.gemini_client = await get_gemini_client()
            self._initialized = True

            logger.info("OCR service initialized successfully")

        except ClientConnectionError as e:
            logger.error(f"Failed to initialize OCR providers: {e}")
            # OCR service can still work with degraded functionality
            self._initialized = False
        except Exception as e:
            logger.error(f"OCR service initialization error: {str(e)}")
            self._initialized = False

    async def get_capabilities(self) -> Dict[str, Any]:
        """Get OCR service capabilities and status"""

        gemini_status = "available"
        if not self.gemini_client:
            try:
                await self.initialize()
                gemini_status = "available" if self.gemini_client else "unavailable"
            except Exception:
                gemini_status = "error"

        return {
            "service_available": self._initialized and bool(self.gemini_client),
            "providers": {
                "gemini": {
                    "status": gemini_status,
                    "model": (
                        self.settings.gemini_model
                        if hasattr(self.settings, "gemini_model")
                        else "gemini-2.5-flash"
                    ),
                    "supported_formats": self.capabilities.supported_formats,
                    "max_file_size_mb": self.capabilities.max_file_size / (1024 * 1024),
                }
            },
            "supported_formats": self.capabilities.supported_formats,
            "confidence_threshold": self.capabilities.confidence_threshold,
            "max_file_size_mb": self.capabilities.max_file_size / (1024 * 1024),
        }

    @langsmith_trace(name="ocr_service_extract_text", run_type="chain")
    async def extract_text(
        self,
        content: bytes,
        content_type: str,
        filename: Optional[str] = None,
        contract_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document using OCR

        Args:
            content: Document content as bytes
            content_type: MIME type of the content
            filename: Original filename (optional)
            contract_context: Context about the contract type and requirements
            options: Additional processing options

        Returns:
            Dictionary containing extracted text and metadata
        """

        if not self._initialized:
            await self.initialize()

        if not self.gemini_client:
            raise ClientConnectionError("OCR service not available")

        log_trace_info(
            "ocr_service_extract_text",
            content_size=len(content),
            content_type=content_type,
            filename=filename,
            has_context=bool(contract_context),
        )

        # Validate input
        self._validate_ocr_input(content, content_type, filename)

        # Prepare options
        processing_options = options or {}
        enhancement_level = processing_options.get("enhancement_level", "standard")
        priority = processing_options.get("priority", False)

        try:
            # Use Gemini client for OCR extraction
            start_time = datetime.now(UTC)

            ocr_result = await self.gemini_client.extract_text(
                content=content,
                content_type=content_type,
                contract_context=contract_context,
                enhancement_options={
                    "quality_enhancement": enhancement_level
                    in ["premium", "enterprise"],
                    "contract_specific": bool(contract_context),
                    "priority_processing": priority,
                },
            )

            processing_time = (datetime.now(UTC) - start_time).total_seconds()

            # Enhance result with OCR-specific metadata
            enhanced_result = {
                **ocr_result,
                "service": "OCRService",
                "provider": "gemini",
                "processing_time_seconds": processing_time,
                "ocr_used": True,
                "content_type": content_type,
                "file_size_bytes": len(content),
                "processing_options": processing_options,
                "extraction_timestamp": datetime.now(UTC).isoformat(),
            }

            # Add quality assessment
            quality_score = self._assess_extraction_quality(
                enhanced_result.get("extracted_text", ""), contract_context
            )
            enhanced_result["extraction_quality"] = quality_score

            # Add processing details
            enhanced_result["processing_details"] = {
                "provider_used": "gemini",
                "enhancement_level": enhancement_level,
                "priority_processing": priority,
                "contract_context_applied": bool(contract_context),
                "quality_score": quality_score,
                "confidence_above_threshold": enhanced_result.get(
                    "extraction_confidence", 0
                )
                >= self.capabilities.confidence_threshold,
            }

            return enhanced_result

        except ClientQuotaExceededError as e:
            logger.warning(f"OCR quota exceeded: {e}")
            raise ClientError(f"OCR quota exceeded: {str(e)}")

        except ClientError as e:
            logger.error(f"OCR extraction failed: {e}")
            raise ClientError(f"OCR extraction failed: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected OCR error: {str(e)}")
            raise ClientError(f"OCR processing failed: {str(e)}")

    async def batch_extract_text(
        self,
        documents: List[Dict[str, Any]],
        contract_context: Optional[Dict[str, Any]] = None,
        batch_options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract text from multiple documents using OCR

        Args:
            documents: List of document dictionaries with content and metadata
            contract_context: Shared context for all documents
            batch_options: Batch processing options

        Returns:
            List of extraction results
        """

        batch_options = batch_options or {}
        parallel_processing = batch_options.get(
            "parallel_processing", len(documents) > 1
        )
        max_concurrent = batch_options.get("max_concurrent", 3)

        results = []

        if parallel_processing and len(documents) > 1:
            # Parallel processing with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_single_document(doc: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    try:
                        return await self.extract_text(
                            content=doc["content"],
                            content_type=doc["content_type"],
                            filename=doc.get("filename"),
                            contract_context=contract_context,
                            options=doc.get("options", {}),
                        )
                    except Exception as e:
                        logger.error(
                            f"Batch OCR failed for document {doc.get('filename', 'unknown')}: {str(e)}"
                        )
                        return {
                            "extracted_text": "",
                            "extraction_confidence": 0.0,
                            "error": str(e),
                            "service": "OCRService",
                            "provider": "failed",
                            "filename": doc.get("filename"),
                        }

            # Execute parallel processing
            tasks = [process_single_document(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions from gather
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    results[i] = {
                        "extracted_text": "",
                        "extraction_confidence": 0.0,
                        "error": str(result),
                        "service": "OCRService",
                        "provider": "failed",
                        "filename": documents[i].get("filename"),
                    }
        else:
            # Sequential processing
            for doc in documents:
                try:
                    result = await self.extract_text(
                        content=doc["content"],
                        content_type=doc["content_type"],
                        filename=doc.get("filename"),
                        contract_context=contract_context,
                        options=doc.get("options", {}),
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Sequential OCR failed for document {doc.get('filename', 'unknown')}: {str(e)}"
                    )
                    results.append(
                        {
                            "extracted_text": "",
                            "extraction_confidence": 0.0,
                            "error": str(e),
                            "service": "OCRService",
                            "provider": "failed",
                            "filename": doc.get("filename"),
                        }
                    )

        return results

    def _validate_ocr_input(
        self,
        content: bytes,
        content_type: str,
        filename: Optional[str] = None,
    ):
        """Validate OCR input parameters"""

        if not content:
            raise ValueError("Content cannot be empty")

        if len(content) > self.capabilities.max_file_size:
            raise ValueError(
                f"File too large for OCR. Maximum size: {self.capabilities.max_file_size / (1024 * 1024)}MB"
            )

        # Extract file type from content type or filename
        file_type = None
        if content_type:
            if content_type == "application/pdf":
                file_type = "pdf"
            elif content_type.startswith("image/"):
                file_type = content_type.split("/")[1]
        elif filename:
            file_type = Path(filename).suffix.lower().lstrip(".")

        if not file_type or not self.capabilities.is_supported_format(file_type):
            raise ValueError(
                f"Unsupported file type for OCR: {file_type}. "
                f"Supported formats: {', '.join(self.capabilities.supported_formats)}"
            )

    def _assess_extraction_quality(
        self,
        extracted_text: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assess the quality of extracted text"""

        if not extracted_text:
            return {
                "score": 0.0,
                "issues": ["No text extracted"],
                "recommendations": [
                    "Check if document contains readable text",
                    "Try different OCR settings",
                ],
            }

        issues = []
        recommendations = []
        score = 0.5  # Base score

        # Text length assessment
        text_length = len(extracted_text.strip())
        if text_length < 100:
            issues.append("Very short text extracted")
            recommendations.append("Document may be mostly images or low quality")
        elif text_length > 500:
            score += 0.2

        # Word quality assessment
        words = extracted_text.split()
        if words:
            # Check for single character "words" (OCR artifacts)
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            if single_char_ratio > 0.3:
                issues.append("High ratio of single character artifacts")
                recommendations.append(
                    "Document quality may be poor, consider rescanning"
                )
                score -= 0.2
            else:
                score += 0.1

        # Contract-specific quality checks
        if contract_context:
            contract_keywords = [
                "purchase",
                "sale",
                "agreement",
                "contract",
                "property",
                "vendor",
                "purchaser",
                "settlement",
                "deposit",
                "price",
            ]

            text_lower = extracted_text.lower()
            keyword_matches = sum(
                1 for keyword in contract_keywords if keyword in text_lower
            )

            if keyword_matches >= 3:
                score += 0.2
            elif keyword_matches == 0:
                issues.append("No contract-related keywords found")
                recommendations.append("Verify this is a contract document")

        # Character encoding quality
        try:
            extracted_text.encode("utf-8")
            score += 0.1
        except UnicodeEncodeError:
            issues.append("Text contains encoding issues")
            recommendations.append("OCR may have misinterpreted characters")
            score -= 0.1

        return {
            "score": max(0.0, min(1.0, score)),
            "text_length": text_length,
            "word_count": len(words) if words else 0,
            "single_char_ratio": single_char_ratio if words else 0,
            "contract_keywords_found": keyword_matches if contract_context else None,
            "issues": issues,
            "recommendations": recommendations,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of OCR service and providers"""

        health_status = {
            "service": "OCRService",
            "status": "healthy",
            "providers": {},
            "capabilities": await self.get_capabilities(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Check Gemini client
        if self.gemini_client:
            try:
                gemini_health = await self.gemini_client.health_check()
                health_status["providers"]["gemini"] = {
                    "status": gemini_health.get("status", "unknown"),
                    "model": gemini_health.get("model", "unknown"),
                    "authentication": gemini_health.get("authentication", {}),
                }
            except Exception as e:
                health_status["providers"]["gemini"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_status["status"] = "degraded"
        else:
            health_status["providers"]["gemini"] = {
                "status": "not_initialized",
            }
            health_status["status"] = "degraded"

        # Overall status assessment
        provider_statuses = [
            provider.get("status") for provider in health_status["providers"].values()
        ]

        if all(status == "healthy" for status in provider_statuses):
            health_status["status"] = "healthy"
        elif any(status == "error" for status in provider_statuses):
            health_status["status"] = "unhealthy"
        else:
            health_status["status"] = "degraded"

        return health_status


# Global OCR service instance
_ocr_service = None


async def get_ocr_service() -> OCRService:
    """Get the global OCR service instance

    DEPRECATED: Use get_ocr_service from app.services instead, which returns GeminiOCRService.
    """
    warnings.warn(
        "get_ocr_service from ocr_service module is deprecated. "
        "Use 'from app.services import get_ocr_service' for GeminiOCRService instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    global _ocr_service

    if _ocr_service is None:
        _ocr_service = OCRService()
        await _ocr_service.initialize()

    return _ocr_service
