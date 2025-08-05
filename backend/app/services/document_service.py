"""
Document Service V2 - Refactored to use client architecture
Handles document upload, storage, and processing with proper client integration
"""

import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime, UTC
from pathlib import Path
import mimetypes

from fastapi import UploadFile, HTTPException
import pypdf
from docx import Document
from unstructured.partition.auto import partition

from app.core.config import get_settings
from app.models.contract_state import ContractType
from app.clients import get_supabase_client, get_gemini_client
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for handling document upload and processing using client architecture"""

    def __init__(self):
        self.settings = get_settings()
        self.supabase_client = None
        self.gemini_client = None
        self.storage_bucket = "documents"

    async def initialize(self):
        """Initialize document service with proper clients"""
        try:
            # Get clients from factory
            self.supabase_client = await get_supabase_client()
            self.gemini_client = await get_gemini_client()

            # Ensure storage bucket exists
            await self._ensure_bucket_exists()

            logger.info("Document service V2 initialized with client architecture")

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to required services: {e}")
            raise HTTPException(status_code=503, detail="Required services unavailable")
        except Exception as e:
            logger.error(f"Failed to initialize document service: {str(e)}")
            raise

    async def _ensure_bucket_exists(self):
        """Ensure storage bucket exists using Supabase client"""
        try:
            # Use Supabase client's storage operations
            # Note: This would need to be implemented in SupabaseClient
            # For now, we'll use a direct approach
            result = await self.supabase_client.execute_rpc(
                "ensure_bucket_exists", {"bucket_name": self.storage_bucket}
            )

            if result.get("created"):
                logger.info(f"Created storage bucket: {self.storage_bucket}")

        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {str(e)}")

    async def upload_file(
        self, file: UploadFile, user_id: str, contract_type: ContractType
    ) -> Dict[str, Any]:
        """Upload file to storage and return metadata"""

        if not self.supabase_client:
            raise HTTPException(
                status_code=503, detail="Storage service not initialized"
            )

        try:
            # Generate unique document ID and storage path
            document_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix.lower()
            storage_path = f"{user_id}/{document_id}{file_extension}"

            # Read file content
            file_content = await file.read()

            # Validate file
            self._validate_file(file_content, file.filename)

            # Upload using Supabase client's storage operations
            upload_result = await self.supabase_client.upload_file(
                bucket=self.storage_bucket,
                file_path=storage_path,
                content=file_content,
                content_type=file.content_type
                or mimetypes.guess_type(file.filename)[0],
            )

            return {
                "document_id": document_id,
                "storage_path": storage_path,
                "original_filename": file.filename,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "upload_timestamp": datetime.now(UTC).isoformat(),
                "storage_url": upload_result.get("url"),
            }

        except ClientError as e:
            logger.error(f"File upload error: {e}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected file upload error: {str(e)}")
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
        """Get file content from storage using Supabase client"""

        if not self.supabase_client:
            raise HTTPException(
                status_code=503, detail="Storage service not initialized"
            )

        try:
            # Download using Supabase client
            file_content = await self.supabase_client.download_file(
                bucket=self.storage_bucket, file_path=storage_path
            )

            return file_content

        except ClientError as e:
            logger.error(f"Error retrieving file: {e}")
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail="File not found")
            raise HTTPException(status_code=500, detail="Could not retrieve file")

    @langsmith_trace(name="document_service_extract_text", run_type="chain")
    async def extract_text(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
        force_ocr: bool = False,
    ) -> Dict[str, Any]:
        """Extract text from document using intelligent OCR fallback"""

        try:
            log_trace_info(
                "document_service_extract_text",
                storage_path=storage_path,
                file_type=file_type,
                force_ocr=force_ocr,
            )
            # Get file content
            file_content = await self.get_file_content(storage_path)
            filename = Path(storage_path).name

            # Determine if we should use OCR
            use_ocr = self._should_use_ocr(file_content, file_type, force_ocr)

            # Try OCR extraction if appropriate
            if use_ocr and self.gemini_client:
                try:
                    # Determine content type
                    if file_type.lower() == "pdf":
                        content_type = "application/pdf"
                    elif file_type.lower() in ["jpg", "jpeg"]:
                        content_type = "image/jpeg"
                    elif file_type.lower() == "png":
                        content_type = "image/png"
                    else:
                        content_type = f"image/{file_type.lower()}"

                    # Use Gemini client for OCR
                    ocr_result = await self.gemini_client.extract_text(
                        content=file_content,
                        content_type=content_type,
                        contract_context=contract_context,
                    )

                    # Add service metadata
                    ocr_result.update(
                        {
                            "service": "DocumentService",
                            "storage_path": storage_path,
                            "ocr_used": True,
                        }
                    )

                    # If OCR was successful and has good confidence, return it
                    if ocr_result.get("extraction_confidence", 0) >= 0.6:
                        return ocr_result

                except ClientQuotaExceededError as e:
                    logger.warning(
                        f"OCR quota exceeded, falling back to traditional extraction: {e}"
                    )
                except ClientError as e:
                    logger.warning(
                        f"OCR failed, falling back to traditional extraction: {e}"
                    )

            # Fallback to traditional extraction methods
            return await self._extract_text_traditional(
                file_content, file_type, filename
            )

        except Exception as e:
            logger.error(f"Text extraction error for {storage_path}: {str(e)}")
            return {
                "extracted_text": "",
                "extraction_method": "failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
            }

    def _should_use_ocr(
        self, file_content: bytes, file_type: str, force_ocr: bool
    ) -> bool:
        """Determine if OCR should be used for extraction"""

        if force_ocr:
            return True

        # Always use OCR for image files
        if file_type.lower() in ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]:
            return True

        # For PDFs, check if it's likely scanned
        if file_type.lower() == "pdf":
            try:
                from io import BytesIO

                pdf_file = BytesIO(file_content)
                pdf_reader = pypdf.PdfReader(pdf_file)

                # Check first few pages for text
                sample_text = ""
                for i, page in enumerate(pdf_reader.pages[:3]):
                    sample_text += page.extract_text()
                    if len(sample_text) > 100:
                        break

                # If very little text, likely scanned
                return len(sample_text.strip()) < 50

            except Exception as e:
                logger.debug(f"PDF text check failed: {e}")
                return True  # Default to OCR on error

        return False

    async def _extract_text_traditional(
        self, file_content: bytes, file_type: str, filename: str
    ) -> Dict[str, Any]:
        """Traditional text extraction methods"""

        extracted_text = ""
        extraction_method = "unknown"

        try:
            if file_type == "pdf":
                extracted_text = await self._extract_pdf_text(file_content)
                extraction_method = "pypdf"
            elif file_type in ["doc", "docx"]:
                extracted_text = await self._extract_word_text(file_content)
                extraction_method = "python_docx"
            else:
                extracted_text = await self._extract_with_unstructured(file_content)
                extraction_method = "unstructured"

        except Exception as e:
            logger.error(f"Traditional extraction failed: {e}")
            extraction_method = "failed"

        return {
            "extracted_text": extracted_text,
            "extraction_method": extraction_method,
            "extraction_confidence": self._estimate_extraction_confidence(
                extracted_text
            ),
            "character_count": len(extracted_text),
            "word_count": len(extracted_text.split()),
            "extraction_timestamp": datetime.now(UTC).isoformat(),
            "service": "DocumentService",
            "ocr_used": False,
        }

    async def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            from io import BytesIO

            pdf_file = BytesIO(file_content)
            pdf_reader = pypdf.PdfReader(pdf_file)

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
        if len(text) > 500:
            confidence += 0.1

        # Check for garbled text
        words = text.split()
        if words:
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            if single_char_ratio < 0.3:
                confidence += 0.1

        return min(1.0, confidence)

    async def analyze_document(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze document using Gemini client"""

        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="Analysis service not available"
            )

        try:
            # Get file content
            file_content = await self.get_file_content(storage_path)

            # Determine content type
            if file_type.lower() == "pdf":
                content_type = "application/pdf"
            elif file_type.lower() in ["jpg", "jpeg"]:
                content_type = "image/jpeg"
            elif file_type.lower() == "png":
                content_type = "image/png"
            else:
                content_type = f"application/{file_type.lower()}"

            # Use Gemini client for analysis
            analysis_result = await self.gemini_client.analyze_document(
                content=file_content,
                content_type=content_type,
                contract_context=contract_context,
                analysis_options=analysis_options,
            )

            # Add service metadata
            analysis_result.update(
                {
                    "service": "DocumentService",
                    "storage_path": storage_path,
                    "file_type": file_type,
                }
            )

            return analysis_result

        except ClientError as e:
            logger.error(f"Document analysis failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Document analysis failed: {str(e)}"
            )

    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage"""

        if not self.supabase_client:
            raise HTTPException(
                status_code=503, detail="Storage service not initialized"
            )

        try:
            # Delete using Supabase client
            result = await self.supabase_client.delete_file(
                bucket=self.storage_bucket, file_path=storage_path
            )

            return result

        except ClientError as e:
            logger.error(f"File deletion error: {e}")
            return False

    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get temporary signed URL for file access"""

        if not self.supabase_client:
            raise HTTPException(
                status_code=503, detail="Storage service not initialized"
            )

        try:
            # Generate signed URL using Supabase client
            signed_url = await self.supabase_client.generate_signed_url(
                bucket=self.storage_bucket,
                file_path=storage_path,
                expires_in=expires_in,
            )

            return signed_url

        except ClientError as e:
            logger.error(f"URL generation error: {e}")
            raise HTTPException(status_code=500, detail="Could not generate file URL")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of document service and its dependencies"""

        health_status = {
            "service": "DocumentService",
            "status": "healthy",
            "dependencies": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Check Supabase client
        if self.supabase_client:
            try:
                supabase_health = await self.supabase_client.health_check()
                health_status["dependencies"]["supabase"] = supabase_health.get(
                    "status", "unknown"
                )
            except Exception as e:
                health_status["dependencies"]["supabase"] = "error"
                health_status["status"] = "degraded"

        else:
            health_status["dependencies"]["supabase"] = "not_initialized"
            health_status["status"] = "degraded"

        # Check Gemini client
        if self.gemini_client:
            try:
                gemini_health = await self.gemini_client.health_check()
                health_status["dependencies"]["gemini"] = gemini_health.get(
                    "status", "unknown"
                )
                health_status["dependencies"]["gemini_auth"] = gemini_health.get(
                    "authentication", {}
                ).get("method", "unknown")
            except Exception as e:
                health_status["dependencies"]["gemini"] = "error"

        else:
            health_status["dependencies"]["gemini"] = "not_initialized"

        # Overall status
        if all(
            status == "healthy"
            for status in health_status["dependencies"].values()
            if status != "unknown"
        ):
            health_status["status"] = "healthy"
        elif any(
            status == "error" for status in health_status["dependencies"].values()
        ):
            health_status["status"] = "unhealthy"
        else:
            health_status["status"] = "degraded"

        return health_status
