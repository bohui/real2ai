"""
Gemini OCR client implementation.
"""

import asyncio
import base64
import io
import logging
from typing import Any, Dict, Optional, BinaryIO
from datetime import datetime
from PIL import Image
import fitz  # PyMuPDF

from ..base.client import with_retry
from ..base.exceptions import (
    ClientError,
    ClientValidationError,
    ClientQuotaExceededError,
)
from .config import GeminiClientConfig

logger = logging.getLogger(__name__)


class GeminiOCRClient:
    """Gemini OCR operations client."""
    
    def __init__(self, gemini_model, config: GeminiClientConfig):
        self.model = gemini_model
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
                original_error=e
            )
    
    async def _test_ocr_capability(self) -> None:
        """Test OCR capability with a simple test."""
        try:
            # Create a simple test image programmatically
            test_image = Image.new('RGB', (100, 50), color='white')
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            test_image.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            
            # Test OCR on the simple image
            # This is a minimal test to verify the API works
            prompt = "What text is visible in this image? If no text, respond with 'No text found'."
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(img_bytes).decode('utf-8')
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content([prompt, image_part])
            )
            
            if not response.text:
                raise ClientError("OCR test failed: No response received")
            
            self.logger.debug("OCR capability test successful")
            
        except Exception as e:
            raise ClientError(
                f"OCR capability test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    def _validate_file(self, content: bytes, content_type: str) -> None:
        """Validate file for OCR processing."""
        # Check file size
        if len(content) > self.config.max_file_size:
            raise ClientValidationError(
                f"File too large for OCR. Maximum size: {self.config.max_file_size / 1024 / 1024}MB",
                client_name=self.client_name
            )
        
        # Check file format
        file_extension = content_type.lower().replace('image/', '').replace('application/', '')
        if file_extension not in self.config.supported_formats:
            raise ClientValidationError(
                f"Unsupported file format for OCR: {content_type}. Supported: {self.config.supported_formats}",
                client_name=self.client_name
            )
    
    @with_retry(max_retries=3, backoff_factor=2.0)
    async def extract_text(self, content: bytes, content_type: str, **kwargs) -> Dict[str, Any]:
        """Extract text from document using Gemini OCR."""
        try:
            self.logger.debug(f"Extracting text from {content_type} document")
            
            # Validate input
            self._validate_file(content, content_type)
            
            # Determine processing method based on content type
            if content_type == "application/pdf":
                return await self._extract_from_pdf(content, **kwargs)
            else:
                return await self._extract_from_image(content, content_type, **kwargs)
                
        except (ClientValidationError, ClientError):
            raise
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def analyze_document(self, content: bytes, content_type: str, **kwargs) -> Dict[str, Any]:
        """Analyze document and extract structured information."""
        try:
            self.logger.debug(f"Analyzing {content_type} document")
            
            # First extract text
            extraction_result = await self.extract_text(content, content_type, **kwargs)
            
            # Add additional analysis
            extracted_text = extraction_result.get("extracted_text", "")
            
            if extracted_text and len(extracted_text.strip()) > 0:
                # Analyze the extracted text for document structure
                analysis_result = await self._analyze_text_content(extracted_text, **kwargs)
                
                # Combine extraction and analysis results
                result = {
                    **extraction_result,
                    "analysis": analysis_result,
                    "analysis_timestamp": datetime.utcnow().isoformat(),
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
                client_name=self.client_name,
                original_error=e
            )
    
    async def _extract_from_pdf(self, pdf_content: bytes, **kwargs) -> Dict[str, Any]:
        """Extract text from PDF using Gemini OCR."""
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            extracted_pages = []
            total_confidence = 0.0
            processing_details = {
                "total_pages": pdf_document.page_count,
                "pages_processed": 0,
                "processing_method": "gemini_ocr"
            }
            
            # Process each page (limit for performance)
            max_pages = min(pdf_document.page_count, 50)  # Limit to 50 pages
            
            for page_num in range(max_pages):
                page = pdf_document[page_num]
                
                # Check if page has native text first
                native_text = page.get_text().strip()
                
                if native_text and len(native_text) > 50:
                    # Use native text extraction
                    page_result = {
                        "page_number": page_num + 1,
                        "text": native_text,
                        "extraction_method": "native_pdf",
                        "confidence": 0.95
                    }
                else:
                    # Use OCR for this page
                    page_result = await self._ocr_pdf_page(page, page_num + 1, **kwargs)
                
                extracted_pages.append(page_result)
                total_confidence += page_result["confidence"]
                processing_details["pages_processed"] += 1
            
            pdf_document.close()
            
            # Combine all extracted text
            combined_text = "\n\n".join([page["text"] for page in extracted_pages if page["text"]])
            average_confidence = total_confidence / len(extracted_pages) if extracted_pages else 0.0
            
            # Apply text enhancement if enabled
            if self.config.enable_text_enhancement and combined_text:
                enhanced_text = await self._enhance_extracted_text(combined_text, **kwargs)
                combined_text = enhanced_text.get("text", combined_text)
            
            return {
                "extracted_text": combined_text,
                "extraction_method": "gemini_ocr_pdf",
                "extraction_confidence": average_confidence,
                "character_count": len(combined_text),
                "word_count": len(combined_text.split()) if combined_text else 0,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "processing_details": {
                    **processing_details,
                    "pages_data": extracted_pages,
                }
            }
            
        except Exception as e:
            self.logger.error(f"PDF OCR processing failed: {e}")
            raise ClientError(
                f"PDF OCR processing failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def _ocr_pdf_page(self, page, page_number: int, **kwargs) -> Dict[str, Any]:
        """OCR a single PDF page using Gemini."""
        try:
            # Convert page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x scale for better OCR
            img_data = pix.tobytes("png")
            
            # Create OCR prompt
            prompt = self._create_ocr_prompt(page_number, **kwargs)
            
            # Send to Gemini for OCR
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(img_data).decode('utf-8')
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content([prompt, image_part])
            )
            
            extracted_text = response.text if response.text else ""
            confidence = self._calculate_confidence(extracted_text)
            
            return {
                "page_number": page_number,
                "text": extracted_text,
                "extraction_method": "gemini_ocr",
                "confidence": confidence
            }
            
        except Exception as e:
            self.logger.error(f"OCR failed for page {page_number}: {e}")
            return {
                "page_number": page_number,
                "text": "",
                "extraction_method": "gemini_ocr_failed",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _extract_from_image(self, image_content: bytes, content_type: str, **kwargs) -> Dict[str, Any]:
        """Extract text from image using Gemini OCR."""
        try:
            # Enhance image if enabled
            if self.config.enable_image_enhancement:
                enhanced_image = await self._enhance_image(image_content, content_type)
            else:
                enhanced_image = image_content
            
            # Create OCR prompt
            prompt = self._create_ocr_prompt(1, is_single_image=True, **kwargs)
            
            # Prepare image for Gemini
            mime_type = f"image/{content_type.replace('image/', '')}"
            image_part = {
                "mime_type": mime_type,
                "data": base64.b64encode(enhanced_image).decode('utf-8')
            }
            
            # Send to Gemini for OCR
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content([prompt, image_part])
            )
            
            extracted_text = response.text if response.text else ""
            confidence = self._calculate_confidence(extracted_text)
            
            # Apply text enhancement if enabled
            if self.config.enable_text_enhancement and extracted_text:
                enhanced_text = await self._enhance_extracted_text(extracted_text, **kwargs)
                extracted_text = enhanced_text.get("text", extracted_text)
            
            return {
                "extracted_text": extracted_text,
                "extraction_method": "gemini_ocr_image",
                "extraction_confidence": confidence,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()) if extracted_text else 0,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "processing_details": {
                    "image_enhanced": self.config.enable_image_enhancement,
                    "content_type": content_type
                }
            }
            
        except Exception as e:
            self.logger.error(f"Image OCR processing failed: {e}")
            raise ClientError(
                f"Image OCR processing failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    def _create_ocr_prompt(self, page_number: int, is_single_image: bool = False, **kwargs) -> str:
        """Create optimized OCR prompt."""
        base_prompt = """
        You are an expert OCR system. Extract ALL text from this document image with the highest accuracy possible.
        
        Instructions:
        - Extract every word, number, and symbol visible in the image
        - Maintain the original document structure and formatting where possible
        - If text is unclear, provide your best interpretation
        - Include all headers, subheadings, and section numbers
        - Preserve tables and lists with appropriate formatting
        - Don't add any explanations or comments - just the extracted text
        
        Focus on accuracy and completeness. Extract all visible text content.
        """
        
        # Add context-specific instructions
        contract_context = kwargs.get("contract_context", {})
        if contract_context:
            if contract_context.get("australian_state"):
                base_prompt += f"\nNote: This appears to be an Australian document from {contract_context['australian_state']}."
            if contract_context.get("contract_type"):
                base_prompt += f"\nDocument type: {contract_context['contract_type']}"
        
        if not is_single_image:
            base_prompt += f"\nThis is page {page_number} of a multi-page document."
        
        base_prompt += "\n\nExtracted text:"
        return base_prompt
    
    def _calculate_confidence(self, extracted_text: str) -> float:
        """Calculate confidence score for extracted text."""
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
        
        # Quality indicators
        words = extracted_text.split()
        if words:
            # Reduce confidence for high ratio of single characters (poor OCR)
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            confidence -= single_char_ratio * 0.3
            
            # Boost confidence for reasonable word lengths
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 3 <= avg_word_length <= 8:
                confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    async def _enhance_image(self, image_content: bytes, content_type: str) -> bytes:
        """Enhance image quality for better OCR results."""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance image quality for OCR
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save enhanced image
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG', optimize=True)
            return output_buffer.getvalue()
            
        except Exception as e:
            self.logger.warning(f"Image enhancement failed, using original: {e}")
            return image_content
    
    async def _enhance_extracted_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """Enhance extracted text with post-processing."""
        try:
            enhanced_text = text
            enhancements_applied = []
            
            # Apply basic text cleaning
            import re
            
            # Fix common OCR errors
            ocr_corrections = {
                r'\$\s*(\d)': r'$\1',  # Fix spacing in currency
                r'(\d),(\d{3})': r'\1,\2',  # Fix comma in numbers
                r'(\d{1,2})/(\d{1,2})/(\d{4})': r'\1/\2/\3',  # Standardize dates
            }
            
            for pattern, replacement in ocr_corrections.items():
                if re.search(pattern, enhanced_text):
                    enhanced_text = re.sub(pattern, replacement, enhanced_text)
                    enhancements_applied.append(f"corrected_pattern_{pattern[:20]}")
            
            return {
                "text": enhanced_text,
                "enhancements_applied": enhancements_applied,
                "enhancement_factor": 1.0 + len(enhancements_applied) * 0.02
            }
            
        except Exception as e:
            self.logger.warning(f"Text enhancement failed: {e}")
            return {"text": text, "enhancements_applied": [], "enhancement_factor": 1.0}
    
    async def _analyze_text_content(self, text: str, **kwargs) -> Dict[str, Any]:
        """Analyze extracted text for document structure and content."""
        try:
            # Basic content analysis
            word_count = len(text.split())
            char_count = len(text)
            
            # Detect potential document type based on keywords
            document_indicators = {
                "contract": ["agreement", "contract", "party", "vendor", "purchaser"],
                "legal": ["whereas", "therefore", "clause", "section", "subsection"],
                "financial": ["amount", "payment", "price", "$", "total", "balance"],
                "real_estate": ["property", "premises", "settlement", "title", "lease"]
            }
            
            detected_types = []
            for doc_type, keywords in document_indicators.items():
                matches = sum(1 for keyword in keywords if keyword.lower() in text.lower())
                if matches >= 2:  # Require at least 2 keyword matches
                    detected_types.append(doc_type)
            
            return {
                "word_count": word_count,
                "character_count": char_count,
                "detected_document_types": detected_types,
                "content_quality": "good" if word_count > 100 else "limited",
                "analysis_method": "keyword_detection"
            }
            
        except Exception as e:
            self.logger.warning(f"Content analysis failed: {e}")
            return {
                "error": str(e),
                "analysis_method": "failed"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OCR client health."""
        try:
            await self._test_ocr_capability()
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "model_available": self.model is not None,
                "max_file_size_mb": self.config.max_file_size / (1024 * 1024),
                "supported_formats": list(self.config.supported_formats),
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