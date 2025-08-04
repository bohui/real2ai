"""
Gemini 2.5 Pro OCR Service for Real2.AI
Advanced OCR capabilities for contract document processing
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List, BinaryIO
from datetime import datetime
from pathlib import Path
import base64
import tempfile

from google import genai
from google.genai.types import HarmCategory, HarmBlockThreshold
from fastapi import HTTPException
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import io

from app.core.config import get_settings
from app.models.contract_state import ProcessingStatus
from app.services.ocr_performance_service import (
    OCRPerformanceService,
    ProcessingPriority,
)

logger = logging.getLogger(__name__)


class GeminiOCRService:
    """Advanced OCR service using Gemini 2.5 Pro for contract document processing"""

    def __init__(self):
        self.settings = get_settings()
        self.model_name = "gemini-2.5-pro"
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit for Gemini
        self.supported_formats = {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "bmp",
            "tiff",
        }

        # Performance optimization service
        self.performance_service = OCRPerformanceService()

        # Advanced processing options
        self.processing_profiles = {
            "fast": {
                "max_resolution": 1500,
                "enhancement_level": 1,
                "timeout_seconds": 30,
            },
            "balanced": {
                "max_resolution": 2000,
                "enhancement_level": 2,
                "timeout_seconds": 60,
            },
            "quality": {
                "max_resolution": 3000,
                "enhancement_level": 3,
                "timeout_seconds": 120,
            },
        }

        # Initialize Gemini API
        if hasattr(self.settings, "gemini_api_key") and self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
            )
        else:
            logger.warning(
                "Gemini API key not configured - OCR service will be disabled"
            )
            self.model = None

    async def initialize(self):
        """Initialize Gemini OCR service with performance optimization"""
        try:
            if self.model:
                # Test API connection
                test_response = await self._test_api_connection()
                if test_response:
                    logger.info("Gemini OCR service initialized successfully")

                    # Initialize performance service
                    await self.performance_service.initialize()
                    logger.info("OCR Performance optimization enabled")
                else:
                    logger.warning("Gemini API connection test failed")
            else:
                logger.warning("Gemini OCR service not available - API key missing")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini OCR service: {str(e)}")
            raise

    async def _test_api_connection(self) -> bool:
        """Test Gemini API connection"""
        try:
            response = self.model.generate_content("Test connection")
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {str(e)}")
            return False

    async def extract_text_from_document(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text from document using Gemini 2.5 Pro OCR with AI optimization

        Args:
            file_content: Raw file bytes
            file_type: File extension (pdf, jpg, png, etc.)
            filename: Original filename
            contract_context: Additional context for better extraction
            user_id: User ID for cost tracking and optimization
            priority: Processing priority level
            enable_optimization: Enable AI performance optimization

        Returns:
            Dict containing extracted text, confidence, and metadata
        """
        if not self.model:
            raise HTTPException(
                status_code=503,
                detail="Gemini OCR service not available - API key not configured",
            )

        try:
            # Validate file size
            if len(file_content) > self.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large for OCR. Maximum size: {self.max_file_size / 1024 / 1024}MB",
                )

            # Validate file format
            if file_type.lower() not in self.supported_formats:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format for OCR: {file_type}",
                )

            # Process based on file type
            if file_type.lower() == "pdf":
                return await self._extract_from_pdf(
                    file_content, filename, contract_context
                )
            else:
                return await self._extract_from_image(
                    file_content, file_type, filename, contract_context
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini OCR extraction failed for {filename}: {str(e)}")
            return {
                "extracted_text": "",
                "extraction_method": "gemini_ocr_failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "file_processed": filename,
                "processing_details": {
                    "file_size": len(file_content),
                    "file_type": file_type,
                    "error_type": type(e).__name__,
                },
            }

    async def _extract_from_pdf(
        self,
        pdf_content: bytes,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text from PDF using Gemini OCR"""

        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

            # Check if PDF has extractable text first
            has_text = False
            for page_num in range(
                min(3, pdf_document.page_count)
            ):  # Check first 3 pages
                page = pdf_document[page_num]
                if page.get_text().strip():
                    has_text = True
                    break

            extracted_pages = []
            total_confidence = 0.0
            processing_details = {
                "total_pages": pdf_document.page_count,
                "pages_processed": 0,
                "has_native_text": has_text,
                "processing_method": "hybrid" if has_text else "ocr_only",
            }

            # Process each page
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]

                # Try extracting native text first
                native_text = page.get_text().strip()

                if native_text and len(native_text) > 50:  # Good native text extraction
                    page_result = {
                        "page_number": page_num + 1,
                        "text": native_text,
                        "extraction_method": "native_pdf",
                        "confidence": 0.95,
                    }
                else:
                    # Use OCR for this page
                    page_result = await self._ocr_pdf_page(
                        page, page_num + 1, contract_context
                    )

                extracted_pages.append(page_result)
                total_confidence += page_result["confidence"]
                processing_details["pages_processed"] += 1

            pdf_document.close()

            # Combine all extracted text
            combined_text = "\n\n".join(
                [page["text"] for page in extracted_pages if page["text"]]
            )
            average_confidence = (
                total_confidence / len(extracted_pages) if extracted_pages else 0.0
            )

            # Enhance with contract-specific post-processing
            enhanced_result = await self._enhance_contract_text(
                combined_text, contract_context
            )

            return {
                "extracted_text": enhanced_result["text"],
                "extraction_method": "gemini_ocr_hybrid",
                "extraction_confidence": min(
                    0.95, average_confidence * enhanced_result["enhancement_factor"]
                ),
                "character_count": len(enhanced_result["text"]),
                "word_count": len(enhanced_result["text"].split()),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "file_processed": filename,
                "processing_details": {
                    **processing_details,
                    "pages_data": extracted_pages,
                    "enhancement_applied": enhanced_result["enhancements_applied"],
                    "contract_terms_found": enhanced_result["contract_terms_count"],
                },
            }

        except Exception as e:
            logger.error(f"PDF OCR processing failed for {filename}: {str(e)}")
            raise

    async def _ocr_pdf_page(
        self, page, page_number: int, contract_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """OCR a single PDF page using Gemini"""

        try:
            # Convert page to image
            pix = page.get_pixmap(
                matrix=fitz.Matrix(2.0, 2.0)
            )  # 2x scale for better OCR
            img_data = pix.tobytes("png")

            # Create contract-specific OCR prompt
            prompt = self._create_ocr_prompt(contract_context, page_number)

            # Send to Gemini for OCR
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(img_data).decode("utf-8"),
            }

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content([prompt, image_part])
            )

            extracted_text = response.text if response.text else ""

            # Calculate confidence based on text quality
            confidence = self._calculate_ocr_confidence(extracted_text, page_number)

            return {
                "page_number": page_number,
                "text": extracted_text,
                "extraction_method": "gemini_ocr",
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"OCR failed for page {page_number}: {str(e)}")
            return {
                "page_number": page_number,
                "text": "",
                "extraction_method": "gemini_ocr_failed",
                "confidence": 0.0,
                "error": str(e),
            }

    async def _extract_from_image(
        self,
        image_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text from image using Gemini OCR"""

        try:
            # Validate and potentially enhance image
            enhanced_image = await self._preprocess_image(image_content, file_type)

            # Create contract-specific OCR prompt
            prompt = self._create_ocr_prompt(contract_context, 1, is_single_image=True)

            # Prepare image for Gemini
            image_part = {
                "mime_type": f"image/{file_type.lower()}",
                "data": base64.b64encode(enhanced_image).decode("utf-8"),
            }

            # Send to Gemini for OCR
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content([prompt, image_part])
            )

            extracted_text = response.text if response.text else ""

            # Enhance with contract-specific post-processing
            enhanced_result = await self._enhance_contract_text(
                extracted_text, contract_context
            )

            # Calculate confidence
            confidence = self._calculate_ocr_confidence(
                enhanced_result["text"], 1, is_single_image=True
            )

            return {
                "extracted_text": enhanced_result["text"],
                "extraction_method": "gemini_ocr_image",
                "extraction_confidence": confidence
                * enhanced_result["enhancement_factor"],
                "character_count": len(enhanced_result["text"]),
                "word_count": len(enhanced_result["text"].split()),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "file_processed": filename,
                "processing_details": {
                    "image_enhanced": True,
                    "enhancement_applied": enhanced_result["enhancements_applied"],
                    "contract_terms_found": enhanced_result["contract_terms_count"],
                    "file_type": file_type,
                },
            }

        except Exception as e:
            logger.error(f"Image OCR processing failed for {filename}: {str(e)}")
            raise

    async def _preprocess_image(self, image_content: bytes, file_type: str) -> bytes:
        """Preprocess image for better OCR results"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Enhance image quality for OCR
            # Resize if too small (OCR works better on larger images)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save enhanced image
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="PNG", optimize=True)
            return output_buffer.getvalue()

        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {str(e)}")
            return image_content

    def _create_ocr_prompt(
        self,
        contract_context: Optional[Dict[str, Any]],
        page_number: int,
        is_single_image: bool = False,
    ) -> str:
        """Create optimized OCR prompt for contract documents"""

        base_prompt = """
You are an expert OCR system specialized in extracting text from Australian real estate contracts and legal documents.

Please extract ALL text from this document image with the highest accuracy possible. Pay special attention to:

1. **Contract Details**: Purchase price, settlement dates, deposit amounts, property addresses
2. **Party Information**: Vendor and purchaser names, contact details
3. **Legal Terms**: Cooling-off periods, special conditions, finance clauses
4. **Fine Print**: Small text, footnotes, and signature blocks
5. **Formatting**: Preserve spacing, line breaks, and paragraph structure where possible

**Instructions:**
- Extract every word, number, and symbol visible in the image
- Maintain the original document structure and formatting
- If text is unclear, provide your best interpretation in [brackets]
- Include all headers, subheadings, and section numbers
- Preserve tables and lists with appropriate formatting
- Don't add any explanations or comments - just the extracted text

**Australian Context:** This is likely an Australian real estate contract, so pay attention to:
- Australian state abbreviations (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
- Australian currency ($AUD)
- Legal terminology specific to Australian property law
- Australian address formats and postcodes
"""

        if contract_context:
            if contract_context.get("australian_state"):
                base_prompt += f"\n- This contract is from {contract_context['australian_state']}, Australia"

            if contract_context.get("contract_type"):
                base_prompt += (
                    f"\n- Expected contract type: {contract_context['contract_type']}"
                )

        if not is_single_image:
            base_prompt += f"\n\n**Page Context:** This is page {page_number} of a multi-page document."

        base_prompt += "\n\nExtracted text:"

        return base_prompt

    async def _enhance_contract_text(
        self, raw_text: str, contract_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Post-process OCR text with contract-specific enhancements"""

        if not raw_text.strip():
            return {
                "text": raw_text,
                "enhancement_factor": 1.0,
                "enhancements_applied": [],
                "contract_terms_count": 0,
            }

        enhanced_text = raw_text
        enhancements_applied = []

        # Common OCR corrections for contract documents
        ocr_corrections = {
            # Currency corrections
            r"\$\s*(\d)": r"$\1",  # Fix spacing in currency
            r"(\d),(\d{3})": r"\1,\2",  # Fix comma in numbers
            # Date corrections
            r"(\d{1,2})/(\d{1,2})/(\d{4})": r"\1/\2/\3",  # Standardize dates
            # Australian state corrections
            r"\bN\.?S\.?W\.?\b": "NSW",
            r"\bV\.?I\.?C\.?\b": "VIC",
            r"\bQ\.?L\.?D\.?\b": "QLD",
            r"\bS\.?A\.?\b": "SA",
            r"\bW\.?A\.?\b": "WA",
            r"\bT\.?A\.?S\.?\b": "TAS",
            r"\bN\.?T\.?\b": "NT",
            r"\bA\.?C\.?T\.?\b": "ACT",
        }

        import re

        for pattern, replacement in ocr_corrections.items():
            if re.search(pattern, enhanced_text):
                enhanced_text = re.sub(pattern, replacement, enhanced_text)
                enhancements_applied.append(f"corrected_pattern_{pattern[:20]}")

        # Count contract-specific terms
        contract_terms = [
            "purchase price",
            "settlement",
            "deposit",
            "vendor",
            "purchaser",
            "cooling-off",
            "finance clause",
            "building inspection",
            "pest inspection",
            "strata",
            "title",
            "contract",
            "agreement",
            "property",
        ]

        text_lower = enhanced_text.lower()
        contract_terms_count = sum(1 for term in contract_terms if term in text_lower)

        # Enhancement factor based on improvements made
        enhancement_factor = 1.0
        if enhancements_applied:
            enhancement_factor += len(enhancements_applied) * 0.02
        if contract_terms_count > 5:
            enhancement_factor += 0.05

        return {
            "text": enhanced_text,
            "enhancement_factor": min(
                1.2, enhancement_factor
            ),  # Cap at 20% improvement
            "enhancements_applied": enhancements_applied,
            "contract_terms_count": contract_terms_count,
        }

    def _calculate_ocr_confidence(
        self, extracted_text: str, page_number: int, is_single_image: bool = False
    ) -> float:
        """Calculate confidence score for OCR extraction"""

        if not extracted_text:
            return 0.0

        confidence = 0.5  # Base confidence

        # Text length factor
        text_length = len(extracted_text.strip())
        if text_length > 100:
            confidence += 0.1
        if text_length > 500:
            confidence += 0.1
        if text_length > 1000:
            confidence += 0.1

        # Contract keyword factor
        contract_keywords = [
            "contract",
            "agreement",
            "purchase",
            "sale",
            "property",
            "vendor",
            "purchaser",
            "settlement",
            "deposit",
            "price",
            "australia",
            "nsw",
            "vic",
            "qld",
            "sa",
            "wa",
            "tas",
            "nt",
            "act",
        ]

        text_lower = extracted_text.lower()
        keyword_matches = sum(
            1 for keyword in contract_keywords if keyword in text_lower
        )
        confidence += min(0.2, keyword_matches * 0.02)

        # Text quality indicators
        words = extracted_text.split()
        if words:
            # Reduce confidence for high ratio of single characters (poor OCR)
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            confidence -= single_char_ratio * 0.3

            # Boost confidence for reasonable word lengths
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 3 <= avg_word_length <= 8:  # Reasonable average word length
                confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _select_processing_profile(
        self, priority: ProcessingPriority, file_size: int
    ) -> str:
        """Select optimal processing profile based on priority and file characteristics"""

        # Base profile selection
        if priority in [ProcessingPriority.CRITICAL, ProcessingPriority.HIGH]:
            base_profile = "quality"
        elif priority == ProcessingPriority.STANDARD:
            base_profile = "balanced"
        else:
            base_profile = "fast"

        # Adjust based on file size
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > 20:  # Large files need quality processing
            if base_profile == "fast":
                base_profile = "balanced"
        elif file_size_mb < 1:  # Small files can use fast processing
            if base_profile == "quality":
                base_profile = "balanced"

        return base_profile

    async def _extract_from_pdf_optimized(
        self,
        pdf_content: bytes,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        processing_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Extract text from PDF with optimization enhancements"""

        # Use the existing method but with profile-based enhancements
        result = await self._extract_from_pdf(pdf_content, filename, contract_context)

        # Apply profile-specific enhancements
        profile_config = self.processing_profiles.get(
            processing_profile, self.processing_profiles["balanced"]
        )

        # Enhance result with profile metadata
        result["processing_details"] = {
            **result.get("processing_details", {}),
            "processing_profile": processing_profile,
            "profile_config": profile_config,
            "optimization_applied": True,
        }

        return result

    async def _extract_from_image_optimized(
        self,
        image_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        processing_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Extract text from image with optimization enhancements"""

        # Use the existing method but with profile-based enhancements
        result = await self._extract_from_image(
            image_content, file_type, filename, contract_context
        )

        # Apply profile-specific enhancements
        profile_config = self.processing_profiles.get(
            processing_profile, self.processing_profiles["balanced"]
        )

        # Enhance result with profile metadata
        result["processing_details"] = {
            **result.get("processing_details", {}),
            "processing_profile": processing_profile,
            "profile_config": profile_config,
            "optimization_applied": True,
        }

        return result

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with performance metrics"""
        try:
            # Basic service check
            service_available = self.model is not None

            # API connectivity check
            api_responsive = False
            if service_available:
                api_responsive = await self._test_api_connection()

            # Performance service health
            performance_health = {"status": "disabled"}
            if hasattr(self, "performance_service"):
                performance_health = await self.performance_service.health_check()

            # Current load and capacity metrics
            capacity_metrics = {
                "max_file_size_mb": self.max_file_size / (1024 * 1024),
                "supported_formats": len(self.supported_formats),
                "processing_profiles": len(self.processing_profiles),
            }

            return {
                "service_status": (
                    "healthy" if (service_available and api_responsive) else "unhealthy"
                ),
                "gemini_api_status": "connected" if api_responsive else "disconnected",
                "performance_optimization": performance_health.get(
                    "service_status", "unknown"
                ),
                "capacity_metrics": capacity_metrics,
                "features": [
                    "multi_page_pdf_processing",
                    "image_enhancement",
                    "contract_specific_ocr",
                    "confidence_scoring",
                    "hybrid_extraction",
                    "australian_context_awareness",
                    "ai_performance_optimization",
                    "intelligent_caching",
                    "quality_assessment",
                    "cost_optimization",
                ],
                "last_health_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "service_status": "error",
                "error_message": str(e),
                "last_health_check": datetime.utcnow().isoformat(),
            }

    async def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive OCR service capabilities and status"""
        base_capabilities = {
            "service_available": self.model is not None,
            "model_name": self.model_name,
            "supported_formats": list(self.supported_formats),
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
            "processing_profiles": list(self.processing_profiles.keys()),
            "features": [
                "multi_page_pdf_processing",
                "image_enhancement",
                "contract_specific_ocr",
                "confidence_scoring",
                "hybrid_extraction",
                "australian_context_awareness",
                "ai_performance_optimization",
                "intelligent_caching",
                "quality_assessment",
                "cost_optimization",
            ],
        }

        # Add performance optimization capabilities if available
        if hasattr(self, "performance_service"):
            try:
                perf_analytics = (
                    await self.performance_service.get_performance_analytics(24)
                )
                base_capabilities["performance_metrics"] = {
                    "cache_hit_rate": perf_analytics.get("cache_hit_rate", 0.0),
                    "average_processing_time_ms": perf_analytics.get(
                        "average_processing_time_ms", 0
                    ),
                    "average_confidence_score": perf_analytics.get(
                        "average_confidence_score", 0.0
                    ),
                    "cost_efficiency": perf_analytics.get("cost_efficiency", {}),
                }
            except Exception as e:
                logger.warning(f"Could not fetch performance metrics: {str(e)}")

        return base_capabilities
