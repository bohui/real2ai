"""
PDF processing for OCR operations.
"""

import asyncio
import pymupdf
from typing import Dict, Any, List
from datetime import datetime, timezone
from google.genai.types import Content, Part

from app.clients.base.exceptions import ClientError
from .prompt_generator import PromptGenerator
from .confidence_calculator import ConfidenceCalculator
from .text_enhancer import TextEnhancer

# Constants
MAX_PDF_PAGES = 50
MIN_NATIVE_TEXT_LENGTH = 50
NATIVE_TEXT_CONFIDENCE = 0.95


class PDFProcessor:
    """Processes PDF documents for OCR operations."""
    
    def __init__(self, gemini_client):
        self.client = gemini_client
        self.prompt_generator = PromptGenerator()
        self.confidence_calculator = ConfidenceCalculator()
        self.text_enhancer = TextEnhancer()
        
    async def extract_from_pdf(self, pdf_content: bytes, **kwargs) -> Dict[str, Any]:
        """Extract text from PDF using Gemini OCR."""
        try:
            # Open PDF with pymupdf
            pdf_document = pymupdf.open(stream=pdf_content, filetype="pdf")

            extracted_pages = []
            total_confidence = 0.0
            processing_details = {
                "total_pages": pdf_document.page_count,
                "pages_processed": 0,
                "processing_method": "gemini_ocr",
            }

            # Process each page (limit for performance)
            max_pages = min(pdf_document.page_count, MAX_PDF_PAGES)

            for page_num in range(max_pages):
                page = pdf_document[page_num]

                # Check if page has native text first
                native_text = page.get_text().strip()

                if native_text and len(native_text) > MIN_NATIVE_TEXT_LENGTH:
                    # Use native text extraction
                    page_result = {
                        "page_number": page_num + 1,
                        "text": native_text,
                        "extraction_method": "native_pdf",
                        "confidence": NATIVE_TEXT_CONFIDENCE,
                    }
                else:
                    # Use OCR for this page
                    page_result = await self.ocr_pdf_page(page, page_num + 1, **kwargs)

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

            # Apply text enhancement if enabled
            config = kwargs.get('config', {})
            if config.get('enable_text_enhancement', False) and combined_text:
                enhanced_text = await self.text_enhancer.enhance_extracted_text(
                    combined_text, **kwargs
                )
                combined_text = enhanced_text.get("text", combined_text)

            return {
                "extracted_text": combined_text,
                "extraction_method": "gemini_ocr_pdf",
                "extraction_confidence": average_confidence,
                "character_count": len(combined_text),
                "word_count": len(combined_text.split()) if combined_text else 0,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_details": {
                    **processing_details,
                    "pages_data": extracted_pages,
                },
            }

        except Exception as e:
            raise ClientError(
                f"PDF OCR processing failed: {str(e)}",
                client_name="PDFProcessor",
                original_error=e,
            )

    async def ocr_pdf_page(self, page, page_number: int, **kwargs) -> Dict[str, Any]:
        """OCR a single PDF page using Gemini."""
        try:
            # Convert page to image
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2.0, 2.0)  # 2x scale for better OCR
            )
            img_data = pix.tobytes("png")

            # Create OCR prompt
            prompt = self.prompt_generator.create_ocr_prompt(page_number, **kwargs)

            # Create content with image
            content = Content(
                parts=[
                    Part.from_text(text=prompt),
                    Part.from_data(data=img_data, mime_type="image/png"),
                ]
            )

            # Send to Gemini for OCR
            response = await self.client.generate_content(content)

            extracted_text = response.get('text', '') if response else ''
            confidence = self.confidence_calculator.calculate_confidence(extracted_text)

            return {
                "page_number": page_number,
                "text": extracted_text,
                "extraction_method": "gemini_ocr",
                "confidence": confidence,
            }

        except Exception as e:
            return {
                "page_number": page_number,
                "text": "",
                "extraction_method": "gemini_ocr_failed",
                "confidence": 0.0,
                "error": str(e),
            }