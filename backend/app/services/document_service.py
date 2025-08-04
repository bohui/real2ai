"""
Document processing service for Real2.AI
"""

import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime
from pathlib import Path
import mimetypes

from fastapi import UploadFile, HTTPException
import PyPDF2
from docx import Document
from unstructured.partition.auto import partition

from app.core.config import get_settings
from app.core.database import get_database_client
from app.models.contract_state import ContractType
from app.services.gemini_ocr_service import GeminiOCRService

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for handling document upload and processing"""

    def __init__(self):
        self.settings = get_settings()
        self.db_client = get_database_client()
        self.storage_bucket = "documents"
        self.gemini_ocr = GeminiOCRService()
        self.ocr_enabled = True  # Can be configured via settings

    async def initialize(self):
        """Initialize document service"""
        try:
            # Ensure storage bucket exists
            await self._ensure_bucket_exists()

            # Initialize Gemini OCR service
            if self.ocr_enabled:
                ocr_success = await self.gemini_ocr.initialize()
                if not ocr_success:
                    logger.warning(
                        "Gemini OCR initialization failed, falling back to traditional methods"
                    )
                    self.ocr_enabled = False

            logger.info("Document service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize document service: {str(e)}")
            raise

    async def _ensure_bucket_exists(self):
        """Ensure storage bucket exists"""
        try:
            # Check if bucket exists, create if not
            storage = self.db_client.storage()
            buckets = storage.list_buckets()

            bucket_names = [bucket.name for bucket in buckets]
            if self.storage_bucket not in bucket_names:
                storage.create_bucket(self.storage_bucket)
                logger.info(f"Created storage bucket: {self.storage_bucket}")

        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {str(e)}")

    async def upload_file(
        self, file: UploadFile, user_id: str, contract_type: ContractType
    ) -> Dict[str, Any]:
        """Upload file to storage and return metadata"""

        try:
            # Generate unique document ID and storage path
            document_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix.lower()
            storage_path = f"{user_id}/{document_id}{file_extension}"

            # Read file content
            file_content = await file.read()

            # Validate file
            self._validate_file(file_content, file.filename)

            # Upload to Supabase storage
            storage = self.db_client.storage()
            result = storage.from_(self.storage_bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": file.content_type
                    or mimetypes.guess_type(file.filename)[0]
                },
            )

            if result.get("error"):
                raise HTTPException(
                    status_code=500, detail=f"File upload failed: {result['error']}"
                )

            return {
                "document_id": document_id,
                "storage_path": storage_path,
                "original_filename": file.filename,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "upload_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def _validate_file(self, file_content: bytes, filename: str):
        """Validate uploaded file"""

        # Check file size
        if len(file_content) > self.settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.settings.max_file_size / 1024 / 1024}MB",
            )

        # Check file extension
        file_extension = Path(filename).suffix.lower().lstrip(".")
        if file_extension not in self.settings.allowed_file_types_list:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(self.settings.allowed_file_types_list)}",
            )

        # Basic content validation
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

    async def get_file_content(self, storage_path: str) -> bytes:
        """Get file content from storage"""
        try:
            storage = self.db_client.storage()
            result = storage.from_(self.storage_bucket).download(storage_path)

            if isinstance(result, bytes):
                return result
            else:
                raise HTTPException(status_code=404, detail="File not found")

        except Exception as e:
            logger.error(f"Error retrieving file: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not retrieve file")

    async def extract_text(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
        force_ocr: bool = False,
    ) -> Dict[str, Any]:
        """Extract text from document with intelligent OCR fallback"""

        try:
            # Get file content
            file_content = await self.get_file_content(storage_path)
            filename = Path(storage_path).name

            # Determine extraction strategy with enhanced logic
            use_gemini_ocr = (
                self.ocr_enabled
                and hasattr(self.gemini_ocr, "model")
                and self.gemini_ocr.model
                and (
                    force_ocr or file_type.lower() in self.gemini_ocr.supported_formats
                )
            )

            # Smart OCR decision based on file characteristics
            if not force_ocr and file_type.lower() == "pdf":
                # Quick scan to determine if OCR is needed
                try:
                    from io import BytesIO
                    import PyPDF2

                    pdf_file = BytesIO(file_content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)

                    # Check if PDF has extractable text
                    sample_text = ""
                    for i, page in enumerate(
                        pdf_reader.pages[:3]
                    ):  # Check first 3 pages
                        sample_text += page.extract_text()
                        if len(sample_text) > 100:  # Has reasonable text
                            break

                    # If very little text extracted, prefer OCR
                    if len(sample_text.strip()) < 50:
                        use_gemini_ocr = (
                            self.ocr_enabled
                            and hasattr(self.gemini_ocr, "model")
                            and self.gemini_ocr.model
                        )
                        logger.info(
                            f"PDF appears to be scanned, preferring OCR for {filename}"
                        )

                except Exception as e:
                    logger.debug(
                        f"PDF text check failed, proceeding with extraction strategy: {e}"
                    )

            primary_result = None
            fallback_result = None

            # Try primary extraction method
            if use_gemini_ocr and (
                force_ocr
                or file_type.lower() in ["pdf"]
                or file_type.lower()
                in ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]
            ):
                # Use Gemini OCR for PDFs (especially scanned) and images
                try:
                    primary_result = await self.gemini_ocr.extract_text_from_document(
                        file_content, file_type, filename, contract_context
                    )
                    logger.info(f"Gemini OCR extraction successful for {filename}")
                except Exception as ocr_error:
                    logger.warning(
                        f"Gemini OCR failed for {filename}: {str(ocr_error)}"
                    )
                    primary_result = None

            # Fallback to traditional methods if OCR failed or not applicable
            if (
                not primary_result
                or primary_result.get("extraction_confidence", 0) < 0.3
            ):
                if file_type == "pdf":
                    extracted_text = await self._extract_pdf_text(file_content)
                    extraction_method = "pypdf2"
                elif file_type in ["doc", "docx"]:
                    extracted_text = await self._extract_word_text(file_content)
                    extraction_method = "python_docx"
                else:
                    extracted_text = await self._extract_with_unstructured(file_content)
                    extraction_method = "unstructured"

                fallback_result = {
                    "extracted_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": self._estimate_extraction_confidence(
                        extracted_text
                    ),
                    "character_count": len(extracted_text),
                    "word_count": len(extracted_text.split()),
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                }

            # Choose best result
            if primary_result and fallback_result:
                # Compare results and choose the better one
                if primary_result.get(
                    "extraction_confidence", 0
                ) >= fallback_result.get("extraction_confidence", 0):
                    final_result = primary_result
                    final_result["fallback_available"] = True
                    final_result["fallback_method"] = fallback_result[
                        "extraction_method"
                    ]
                else:
                    final_result = fallback_result
                    final_result["ocr_attempted"] = True
                    final_result["ocr_confidence"] = primary_result.get(
                        "extraction_confidence", 0
                    )
            elif primary_result:
                final_result = primary_result
            elif fallback_result:
                final_result = fallback_result
            else:
                # Both methods failed
                final_result = {
                    "extracted_text": "",
                    "extraction_method": "all_methods_failed",
                    "extraction_confidence": 0.0,
                    "character_count": 0,
                    "word_count": 0,
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "error": "All extraction methods failed",
                }

            return final_result

        except Exception as e:
            logger.error(f"Text extraction error for {storage_path}: {str(e)}")
            return {
                "extracted_text": "",
                "extraction_method": "failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.utcnow().isoformat(),
            }

    async def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            from io import BytesIO

            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return ""

    async def _extract_word_text(self, file_content: bytes) -> str:
        """Extract text from Word document"""
        try:
            from io import BytesIO

            doc_file = BytesIO(file_content)
            doc = Document(doc_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Word extraction error: {str(e)}")
            return ""

    async def _extract_with_unstructured(self, file_content: bytes) -> str:
        """Extract text using unstructured library"""
        try:
            # Save to temporary file for unstructured processing
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()

                elements = partition(temp_file.name)
                text_parts = [
                    element.text for element in elements if hasattr(element, "text")
                ]

                # Clean up temp file
                os.unlink(temp_file.name)

                return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Unstructured extraction error: {str(e)}")
            return ""

    def _estimate_extraction_confidence(self, text: str) -> float:
        """Estimate confidence in text extraction quality"""
        if not text:
            return 0.0

        # Simple heuristics for confidence estimation
        confidence = 0.5  # Base confidence

        # Check for common contract keywords
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
        ]

        text_lower = text.lower()
        keyword_matches = sum(
            1 for keyword in contract_keywords if keyword in text_lower
        )

        # Boost confidence based on keyword presence
        confidence += min(0.4, keyword_matches * 0.05)

        # Check text quality indicators
        if len(text) > 500:  # Reasonable length
            confidence += 0.1

        # Check for garbled text (many single characters or numbers)
        words = text.split()
        if words:
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            if single_char_ratio < 0.3:  # Less than 30% single characters
                confidence += 0.1

        return min(1.0, confidence)

    async def extract_text_with_ocr(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Force OCR extraction for better quality on scanned documents"""
        return await self.extract_text(
            storage_path, file_type, contract_context, force_ocr=True
        )

    async def get_ocr_capabilities(self) -> Dict[str, Any]:
        """Get OCR service capabilities"""
        if self.ocr_enabled and self.gemini_ocr.model:
            return await self.gemini_ocr.get_processing_capabilities()
        else:
            return {
                "service_available": False,
                "reason": "Gemini OCR not configured or disabled",
            }

    def requires_ocr(self, file_type: str, extraction_confidence: float) -> bool:
        """Determine if document would benefit from OCR processing"""
        # Recommend OCR for low confidence PDF extractions or image files
        if file_type.lower() in ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]:
            return True
        if file_type.lower() == "pdf" and extraction_confidence < 0.6:
            return True
        return False

    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage"""
        try:
            storage = self.db_client.storage()
            result = storage.from_(self.storage_bucket).remove([storage_path])

            return not result.get("error")

        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return False

    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get temporary signed URL for file access"""
        try:
            storage = self.db_client.storage()
            result = storage.from_(self.storage_bucket).create_signed_url(
                storage_path, expires_in
            )

            if result.get("error"):
                raise HTTPException(
                    status_code=500, detail="Could not generate file URL"
                )

            return result["signedURL"]

        except Exception as e:
            logger.error(f"URL generation error: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not generate file URL")
