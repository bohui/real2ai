"""
Document Service V2 - Refactored to use client architecture
Handles document upload, storage, and processing with proper client integration
"""

import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, BinaryIO, List
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
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.semantic_analysis_service import SemanticAnalysisService
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for handling document upload and processing using client architecture"""

    def __init__(self, use_service_role: bool = False):
        self.settings = get_settings()
        self.supabase_client = None
        self.gemini_client = None
        self.ocr_service = None
        self.semantic_analysis_service = None
        self.storage_bucket = "documents"
        self.use_service_role = use_service_role

    async def initialize(self):
        """Initialize document service with proper clients"""
        try:
            # Get clients from factory
            self.supabase_client = await get_supabase_client()
            self.gemini_client = await get_gemini_client()
            # Initialize GeminiOCRService for advanced OCR and semantic analysis
            self.ocr_service = GeminiOCRService()
            await self.ocr_service.initialize()
            
            # Initialize semantic analysis service
            self.semantic_analysis_service = SemanticAnalysisService()
            await self.semantic_analysis_service.initialize()

            # Ensure storage bucket exists
            await self._ensure_bucket_exists()

            logger.info("Document service V2 initialized with client architecture, OCR, and semantic analysis services")

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
        """Enhanced file validation with content type checking"""

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
        
        # Enhanced content validation based on file type
        validation_result = self._validate_file_content(file_content, file_extension)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {validation_result['reason']}"
            )
    
    def _validate_file_content(self, file_content: bytes, file_extension: str) -> Dict[str, Any]:
        """Validate file content matches expected format"""
        
        validation_result = {
            "valid": True,
            "reason": "File content valid",
            "detected_type": file_extension,
            "confidence": 1.0,
        }
        
        try:
            # PDF validation
            if file_extension == "pdf":
                if not file_content.startswith(b"%PDF"):
                    validation_result.update({
                        "valid": False,
                        "reason": "File does not appear to be a valid PDF",
                        "detected_type": "unknown",
                    })
                else:
                    # Check if PDF is readable
                    try:
                        from io import BytesIO
                        import pypdf
                        pdf_file = BytesIO(file_content)
                        pdf_reader = pypdf.PdfReader(pdf_file)
                        page_count = len(pdf_reader.pages)
                        validation_result["metadata"] = {
                            "page_count": page_count,
                            "encrypted": pdf_reader.is_encrypted,
                        }
                        if pdf_reader.is_encrypted:
                            validation_result.update({
                                "valid": False,
                                "reason": "PDF is encrypted and cannot be processed",
                            })
                    except Exception as e:
                        validation_result.update({
                            "valid": False,
                            "reason": f"PDF appears corrupted: {str(e)}",
                        })
            
            # Word document validation
            elif file_extension in ["doc", "docx"]:
                if file_extension == "docx":
                    # DOCX files are ZIP archives
                    if not (file_content.startswith(b"PK") or file_content.startswith(b"\x50\x4b")):
                        validation_result.update({
                            "valid": False,
                            "reason": "File does not appear to be a valid DOCX document",
                            "detected_type": "unknown",
                        })
                    else:
                        # Try to validate DOCX structure
                        try:
                            from io import BytesIO
                            from docx import Document
                            doc_file = BytesIO(file_content)
                            doc = Document(doc_file)
                            paragraph_count = len(doc.paragraphs)
                            validation_result["metadata"] = {
                                "paragraph_count": paragraph_count,
                            }
                        except Exception as e:
                            validation_result.update({
                                "valid": False,
                                "reason": f"DOCX appears corrupted: {str(e)}",
                            })
                elif file_extension == "doc":
                    # Legacy DOC format validation (basic)
                    if not file_content.startswith((b"\xd0\xcf\x11\xe0", b"\x0e\x11\xfc\x0d")):
                        validation_result.update({
                            "valid": False,
                            "reason": "File does not appear to be a valid DOC document",
                            "detected_type": "unknown",
                        })
            
            # Image file validation
            elif file_extension in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                image_signatures = {
                    "png": b"\x89PNG\r\n\x1a\n",
                    "jpg": b"\xff\xd8\xff",
                    "jpeg": b"\xff\xd8\xff",
                    "gif": (b"GIF87a", b"GIF89a"),
                    "bmp": b"BM",
                    "tiff": (b"II*\x00", b"MM\x00*"),
                    "webp": b"RIFF",
                }
                
                expected_signatures = image_signatures.get(file_extension)
                if expected_signatures:
                    if isinstance(expected_signatures, tuple):
                        signature_match = any(
                            file_content.startswith(sig) for sig in expected_signatures
                        )
                    else:
                        signature_match = file_content.startswith(expected_signatures)
                    
                    if not signature_match:
                        # Try to detect actual image type
                        detected_type = self._detect_image_type(file_content)
                        validation_result.update({
                            "valid": False,
                            "reason": f"File appears to be {detected_type} but has {file_extension} extension",
                            "detected_type": detected_type,
                        })
                    else:
                        validation_result["metadata"] = {
                            "format_verified": True,
                        }
                        
                        # Additional validation for WebP
                        if file_extension == "webp":
                            if b"WEBP" not in file_content[:20]:
                                validation_result.update({
                                    "valid": False,
                                    "reason": "File has RIFF signature but is not a valid WebP",
                                })
            
            # File size validation for specific types
            file_size_mb = len(file_content) / (1024 * 1024)
            if file_extension == "pdf" and file_size_mb > 50:
                validation_result["reason"] += " (Large PDF may slow processing)"
            elif file_extension in ["tiff", "bmp"] and file_size_mb > 20:
                validation_result["reason"] += " (Large image file may slow processing)"
                
        except Exception as e:
            logger.warning(f"File content validation error: {str(e)}")
            # Don't fail validation for unexpected errors, just log them
            validation_result["reason"] += f" (Warning: {str(e)})"
        
        return validation_result
    
    def _detect_image_type(self, file_content: bytes) -> str:
        """Detect actual image type from content"""
        
        image_signatures = {
            b"\x89PNG\r\n\x1a\n": "png",
            b"\xff\xd8\xff": "jpeg", 
            b"GIF87a": "gif",
            b"GIF89a": "gif",
            b"BM": "bmp",
            b"II*\x00": "tiff",
            b"MM\x00*": "tiff",
            b"RIFF": "webp_or_other",
        }
        
        for signature, image_type in image_signatures.items():
            if file_content.startswith(signature):
                if image_type == "webp_or_other":
                    if b"WEBP" in file_content[:20]:
                        return "webp"
                    else:
                        return "riff_format"
                return image_type
        
        return "unknown"

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

        # Check OCR service
        if self.ocr_service:
            try:
                ocr_health = await self.ocr_service.health_check()
                health_status["dependencies"]["ocr_service"] = ocr_health.get(
                    "status", "unknown"
                )
            except Exception as e:
                health_status["dependencies"]["ocr_service"] = "error"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["ocr_service"] = "not_initialized"
            health_status["status"] = "degraded"

        # Check semantic analysis service
        if self.semantic_analysis_service:
            try:
                semantic_health = await self.semantic_analysis_service.health_check()
                health_status["dependencies"]["semantic_analysis_service"] = semantic_health.get(
                    "status", "unknown"
                )
            except Exception as e:
                health_status["dependencies"]["semantic_analysis_service"] = "error"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["semantic_analysis_service"] = "not_initialized"
            health_status["status"] = "degraded"

        return health_status

    async def extract_text_with_ocr(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text using dedicated OCR service"""
        
        if not self.ocr_service:
            raise HTTPException(
                status_code=503, detail="OCR service not available"
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
            elif file_type.lower() == "gif":
                content_type = "image/gif"
            elif file_type.lower() == "bmp":
                content_type = "image/bmp"
            elif file_type.lower() in ["tiff", "tif"]:
                content_type = "image/tiff"
            elif file_type.lower() == "webp":
                content_type = "image/webp"
            else:
                content_type = f"image/{file_type.lower()}"
            
            # Extract text using OCR service
            ocr_result = await self.ocr_service.extract_text(
                content=file_content,
                content_type=content_type,
                filename=Path(storage_path).name,
                contract_context=contract_context,
                options=options or {},
            )
            
            # Add document service metadata
            ocr_result.update({
                "service": "DocumentService",
                "storage_path": storage_path,
                "file_type": file_type,
            })
            
            return ocr_result
            
        except ClientError as e:
            logger.error(f"OCR extraction failed for {storage_path}: {e}")
            raise HTTPException(
                status_code=500, detail=f"OCR extraction failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected OCR error for {storage_path}: {str(e)}")
            return {
                "extracted_text": "",
                "extraction_method": "ocr_failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
                "service": "DocumentService",
                "storage_path": storage_path,
                "ocr_used": True,
            }
    
    async def get_ocr_capabilities(self) -> Dict[str, Any]:
        """Get OCR service capabilities"""
        
        if not self.ocr_service:
            return {
                "service_available": False,
                "reason": "OCR service not initialized",
                "supported_formats": [],
            }
        
        try:
            return await self.ocr_service.get_capabilities()
        except Exception as e:
            logger.error(f"Failed to get OCR capabilities: {str(e)}")
            return {
                "service_available": False,
                "reason": str(e),
                "supported_formats": [],
            }
    
    def assess_document_quality(
        self,
        extracted_text: str,
        file_type: str,
        file_size: int,
        extraction_method: str,
        extraction_confidence: float,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assess overall document processing quality"""
        
        quality_assessment = {
            "overall_score": 0.0,
            "text_quality": {},
            "extraction_quality": {},
            "document_characteristics": {},
            "recommendations": [],
            "issues": [],
        }
        
        # Text quality assessment
        if extracted_text:
            text_length = len(extracted_text.strip())
            word_count = len(extracted_text.split())
            
            quality_assessment["text_quality"] = {
                "length": text_length,
                "word_count": word_count,
                "avg_word_length": sum(len(word) for word in extracted_text.split()) / word_count if word_count > 0 else 0,
                "has_content": text_length > 100,
            }
            
            # Contract-specific assessment
            if contract_context:
                contract_keywords = [
                    "purchase", "sale", "agreement", "contract", "property",
                    "vendor", "purchaser", "settlement", "deposit", "price",
                    "terms", "conditions", "clause", "section", "party"
                ]
                
                text_lower = extracted_text.lower()
                keyword_matches = sum(1 for keyword in contract_keywords if keyword in text_lower)
                
                quality_assessment["text_quality"]["contract_keywords_found"] = keyword_matches
                quality_assessment["text_quality"]["appears_to_be_contract"] = keyword_matches >= 3
        
        # Extraction quality assessment
        quality_assessment["extraction_quality"] = {
            "method": extraction_method,
            "confidence": extraction_confidence,
            "confidence_adequate": extraction_confidence >= 0.6,
        }
        
        # Document characteristics
        quality_assessment["document_characteristics"] = {
            "file_type": file_type,
            "file_size_mb": file_size / (1024 * 1024),
            "size_category": self._categorize_file_size(file_size),
            "ocr_recommended": file_type.lower() in ["pdf", "png", "jpg", "jpeg", "tiff"],
        }
        
        # Calculate overall score
        score_components = []
        
        # Text content score (40%)
        if extracted_text and len(extracted_text.strip()) > 100:
            score_components.append(0.4)
        elif extracted_text:
            score_components.append(0.2)
        else:
            score_components.append(0.0)
        
        # Extraction confidence score (30%)
        confidence_score = min(1.0, extraction_confidence) * 0.3
        score_components.append(confidence_score)
        
        # Contract relevance score (30%)
        if contract_context and quality_assessment["text_quality"].get("appears_to_be_contract", False):
            score_components.append(0.3)
        elif contract_context:
            score_components.append(0.1)
        else:
            score_components.append(0.15)  # Neutral score when no contract context
        
        quality_assessment["overall_score"] = sum(score_components)
        
        # Generate recommendations and identify issues
        if extraction_confidence < 0.5:
            quality_assessment["issues"].append("Low extraction confidence")
            quality_assessment["recommendations"].append("Consider using OCR for better text extraction")
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            quality_assessment["issues"].append("Very little text extracted")
            quality_assessment["recommendations"].append("Check document quality and format")
        
        if contract_context and not quality_assessment["text_quality"].get("appears_to_be_contract", False):
            quality_assessment["issues"].append("Document may not be a contract")
            quality_assessment["recommendations"].append("Verify document type and content")
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            quality_assessment["recommendations"].append("Large file size may slow processing")
        
        return quality_assessment
    
    def _categorize_file_size(self, file_size: int) -> str:
        """Categorize file size for quality assessment"""
        
        size_mb = file_size / (1024 * 1024)
        
        if size_mb < 1:
            return "small"
        elif size_mb < 5:
            return "medium"
        elif size_mb < 20:
            return "large"
        else:
            return "very_large"
    
    async def validate_contract_document(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate document specifically for contract processing"""
        
        validation_result = {
            "is_valid_contract_document": False,
            "validation_score": 0.0,
            "issues": [],
            "recommendations": [],
            "document_characteristics": {},
        }
        
        try:
            # Get file content for analysis
            file_content = await self.get_file_content(storage_path)
            file_size = len(file_content)
            
            # Basic file validation
            content_validation = self._validate_file_content(file_content, file_type)
            if not content_validation["valid"]:
                validation_result["issues"].append(content_validation["reason"])
                validation_result["recommendations"].append("Check file integrity and format")
                return validation_result
            
            # Extract text for content analysis
            extraction_result = await self.extract_text(
                storage_path, file_type, contract_context
            )
            
            extracted_text = extraction_result.get("extracted_text", "")
            extraction_confidence = extraction_result.get("extraction_confidence", 0.0)
            
            # Assess document quality
            quality_assessment = self.assess_document_quality(
                extracted_text,
                file_type,
                file_size,
                extraction_result.get("extraction_method", "unknown"),
                extraction_confidence,
                contract_context,
            )
            
            # Contract-specific validation
            contract_indicators = self._analyze_contract_indicators(extracted_text)
            
            validation_result.update({
                "document_characteristics": {
                    "file_type": file_type,
                    "file_size_mb": file_size / (1024 * 1024),
                    "text_length": len(extracted_text),
                    "extraction_confidence": extraction_confidence,
                    "quality_score": quality_assessment["overall_score"],
                },
                "contract_analysis": contract_indicators,
                "extraction_quality": quality_assessment["extraction_quality"],
            })
            
            # Calculate overall validation score
            score_factors = [
                extraction_confidence * 0.3,  # 30% extraction quality
                quality_assessment["overall_score"] * 0.3,  # 30% overall quality
                contract_indicators["contract_likelihood"] * 0.4,  # 40% contract indicators
            ]
            
            validation_result["validation_score"] = sum(score_factors)
            validation_result["is_valid_contract_document"] = validation_result["validation_score"] >= 0.6
            
            # Generate issues and recommendations
            if extraction_confidence < 0.5:
                validation_result["issues"].append("Poor text extraction quality")
                validation_result["recommendations"].append("Consider using OCR or higher quality scan")
            
            if contract_indicators["contract_likelihood"] < 0.3:
                validation_result["issues"].append("Document may not be a contract")
                validation_result["recommendations"].append("Verify document type and content")
            
            if len(extracted_text) < 200:
                validation_result["issues"].append("Very short document content")
                validation_result["recommendations"].append("Check if document is complete")
            
            if file_size > 20 * 1024 * 1024:  # 20MB
                validation_result["recommendations"].append("Large file may slow processing")
            
        except Exception as e:
            logger.error(f"Contract document validation failed: {str(e)}")
            validation_result["issues"].append(f"Validation error: {str(e)}")
            validation_result["recommendations"].append("Check file format and integrity")
        
        return validation_result
    
    def _analyze_contract_indicators(self, text: str) -> Dict[str, Any]:
        """Analyze text for contract-specific indicators"""
        
        if not text:
            return {
                "contract_likelihood": 0.0,
                "indicators_found": [],
                "missing_indicators": [],
                "confidence": 0.0,
            }
        
        text_lower = text.lower()
        
        # Define contract indicators with weights
        contract_indicators = {
            # Core contract terms (high weight)
            "agreement": 0.2,
            "contract": 0.2,
            "purchase": 0.15,
            "sale": 0.15,
            
            # Property-specific terms (medium-high weight)
            "property": 0.1,
            "vendor": 0.1,
            "purchaser": 0.1,
            "settlement": 0.1,
            
            # Legal terms (medium weight)
            "terms and conditions": 0.08,
            "clause": 0.08,
            "party": 0.08,
            "hereby": 0.08,
            
            # Financial terms (medium weight)
            "deposit": 0.07,
            "price": 0.07,
            "payment": 0.07,
            
            # Australian-specific terms (medium weight)
            "cooling off": 0.06,
            "stamp duty": 0.06,
            "conveyancer": 0.06,
            "solicitor": 0.06,
            
            # Date/time indicators (low weight)
            "settlement date": 0.05,
            "completion date": 0.05,
            "due date": 0.05,
        }
        
        found_indicators = []
        total_score = 0.0
        
        for indicator, weight in contract_indicators.items():
            if indicator in text_lower:
                found_indicators.append(indicator)
                total_score += weight
        
        # Normalize score to 0-1 range
        max_possible_score = sum(contract_indicators.values())
        contract_likelihood = min(1.0, total_score / max_possible_score * 2)  # Scale up for easier thresholds
        
        # Identify missing critical indicators
        critical_indicators = ["agreement", "contract", "purchase", "sale"]
        missing_critical = [ind for ind in critical_indicators if ind not in text_lower]
        
        return {
            "contract_likelihood": contract_likelihood,
            "indicators_found": found_indicators,
            "missing_critical_indicators": missing_critical,
            "total_indicators": len(found_indicators),
            "confidence": min(1.0, len(found_indicators) / 10),  # Based on number of indicators
        }
    
    async def track_processing_progress(
        self,
        document_id: str,
        stage: str,
        progress_percent: int,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track document processing progress"""
        
        progress_data = {
            "document_id": document_id,
            "stage": stage,
            "progress_percent": min(100, max(0, progress_percent)),
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        
        try:
            # Update database if available
            if self.supabase_client:
                # Try to update document progress in database
                await self.supabase_client.execute_rpc(
                    "update_document_progress",
                    {
                        "p_document_id": document_id,
                        "p_stage": stage,
                        "p_progress_percent": progress_percent,
                        "p_message": message,
                        "p_metadata": metadata or {},
                    },
                )
            
            # Send progress via WebSocket if available
            from app.services.websocket_singleton import websocket_manager
            await websocket_manager.send_message(
                document_id,
                {
                    "event_type": "document_processing_progress",
                    "data": progress_data,
                },
            )
            
            # Also publish via Redis for persistence
            from app.services.redis_pubsub import publish_progress_sync
            publish_progress_sync(document_id, {
                "event_type": "document_processing_progress",
                "timestamp": progress_data["timestamp"],
                "data": progress_data,
            })
            
        except Exception as e:
            logger.warning(f"Failed to track progress for document {document_id}: {str(e)}")
    
    async def get_processing_progress(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        """Get current processing progress for a document"""
        
        try:
            if not self.supabase_client:
                return {
                    "document_id": document_id,
                    "stage": "unknown",
                    "progress_percent": 0,
                    "message": "Progress tracking not available",
                    "error": "Database not available",
                }
            
            # Get latest progress from database
            result = await self.supabase_client.execute_rpc(
                "get_document_progress",
                {"p_document_id": document_id},
            )
            
            if result and result.get("data"):
                return result["data"][0]
            else:
                return {
                    "document_id": document_id,
                    "stage": "not_started",
                    "progress_percent": 0,
                    "message": "Processing not started",
                }
                
        except Exception as e:
            logger.error(f"Failed to get progress for document {document_id}: {str(e)}")
            return {
                "document_id": document_id,
                "stage": "error",
                "progress_percent": 0,
                "message": "Error retrieving progress",
                "error": str(e),
            }

    async def analyze_document_semantics(
        self,
        storage_path: str,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_options: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document for semantic meaning using SemanticAnalysisService
        
        This method provides a comprehensive semantic analysis of property documents,
        identifying infrastructure, boundaries, environmental factors, and potential risks.
        
        Args:
            storage_path: Path to document in storage
            file_type: File extension (pdf, jpg, png, etc.)
            filename: Original filename
            contract_context: Contract context for analysis
            analysis_options: Analysis configuration options
            document_id: Document ID for progress tracking
            
        Returns:
            Comprehensive semantic analysis results
            
        Example Usage:
            # Analyze a sewer service diagram
            result = await document_service.analyze_document_semantics(
                storage_path="user123/doc456.jpg",
                file_type="jpg",
                filename="sewer_service_plan.jpg",
                contract_context={
                    "australian_state": AustralianState.NSW,
                    "contract_type": ContractType.PURCHASE_AGREEMENT,
                    "user_type": "buyer"
                },
                analysis_options={
                    "analysis_focus": "infrastructure",
                    "risk_categories": ["infrastructure", "construction"]
                }
            )
        """
        if not self.semantic_analysis_service:
            raise HTTPException(
                status_code=503, detail="Semantic analysis service not available"
            )
        
        try:
            return await self.semantic_analysis_service.analyze_document_semantics(
                storage_path=storage_path,
                file_type=file_type,
                filename=filename,
                contract_context=contract_context,
                analysis_options=analysis_options,
                document_id=document_id
            )
            
        except Exception as e:
            logger.error(f"Semantic analysis failed for {storage_path}: {str(e)}")
            return {
                "document_metadata": {
                    "storage_path": storage_path,
                    "filename": filename,
                    "file_type": file_type,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "document_id": document_id
                },
                "semantic_analysis": None,
                "error": str(e),
                "service": "DocumentService",
                "analysis_failed": True
            }

    async def analyze_contract_diagrams(
        self,
        diagram_storage_paths: List[str],
        contract_context: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple diagrams from a contract document
        
        This method orchestrates semantic analysis across multiple property diagrams,
        consolidating risks and providing comprehensive property insights.
        
        Args:
            diagram_storage_paths: List of storage paths to diagram images
            contract_context: Contract context including state, type, user info
            document_id: Document ID for progress tracking
            
        Returns:
            Consolidated analysis of all contract diagrams
            
        Example Usage:
            # Analyze all diagrams in a property contract
            result = await document_service.analyze_contract_diagrams(
                diagram_storage_paths=[
                    "user123/sewer_plan.jpg",
                    "user123/site_plan.pdf", 
                    "user123/flood_map.png"
                ],
                contract_context={
                    "australian_state": AustralianState.NSW,
                    "contract_type": ContractType.PURCHASE_AGREEMENT,
                    "property_address": "123 Main St, Sydney NSW 2000",
                    "user_type": "buyer",
                    "user_experience_level": "novice"
                }
            )
        """
        if not self.semantic_analysis_service:
            raise HTTPException(
                status_code=503, detail="Semantic analysis service not available"
            )
        
        if not diagram_storage_paths:
            raise HTTPException(
                status_code=400, detail="No diagram paths provided for analysis"
            )
        
        try:
            return await self.semantic_analysis_service.analyze_contract_diagrams(
                storage_paths=diagram_storage_paths,
                contract_context=contract_context,
                document_id=document_id
            )
            
        except Exception as e:
            logger.error(f"Contract diagram analysis failed: {str(e)}")
            return {
                "contract_context": contract_context,
                "total_diagrams": len(diagram_storage_paths),
                "error": str(e),
                "service": "DocumentService",
                "analysis_failed": True,
                "analysis_timestamp": datetime.now(UTC).isoformat()
            }

    async def process_contract_with_semantic_analysis(
        self,
        main_document_path: str,
        diagram_paths: List[str],
        contract_context: Dict[str, Any],
        document_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete contract processing including text extraction and semantic analysis
        
        This method provides end-to-end processing of property contracts:
        1. Text extraction from main document
        2. Semantic analysis of all diagrams
        3. Risk consolidation and assessment
        4. Professional consultation recommendations
        
        Args:
            main_document_path: Path to main contract document
            diagram_paths: List of paths to property diagrams
            contract_context: Contract context for analysis
            document_id: Document ID for progress tracking
            processing_options: Processing configuration options
            
        Returns:
            Complete contract analysis including text and semantic analysis
        """
        if not self.semantic_analysis_service:
            raise HTTPException(
                status_code=503, detail="Semantic analysis service not available"
            )
        
        processing_results = {
            "document_id": document_id,
            "contract_context": contract_context,
            "processing_timestamp": datetime.now(UTC).isoformat(),
            "text_extraction": None,
            "semantic_analysis": None,
            "consolidated_assessment": None,
            "processing_stages": [],
            "errors": []
        }
        
        try:
            # Stage 1: Process main contract document (10-50%)
            await self.track_processing_progress(
                document_id, "processing_main_document", 10,
                "Processing main contract document"
            )
            
            main_filename = Path(main_document_path).name
            main_file_type = Path(main_document_path).suffix.lower().lstrip('.')
            
            # Extract text from main document
            text_extraction = await self.process_document_with_progress(
                storage_path=main_document_path,
                file_type=main_file_type,
                document_id=document_id,
                contract_context=contract_context,
                processing_options=processing_options
            )
            
            processing_results["text_extraction"] = text_extraction
            processing_results["processing_stages"].append({
                "stage": "text_extraction",
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "confidence": text_extraction.get("extraction_confidence", 0.0)
            })
            
            # Stage 2: Analyze contract diagrams (50-90%)
            if diagram_paths:
                await self.track_processing_progress(
                    document_id, "analyzing_diagrams", 50,
                    f"Analyzing {len(diagram_paths)} property diagrams"
                )
                
                semantic_analysis = await self.analyze_contract_diagrams(
                    diagram_storage_paths=diagram_paths,
                    contract_context=contract_context,
                    document_id=document_id
                )
                
                processing_results["semantic_analysis"] = semantic_analysis
                processing_results["processing_stages"].append({
                    "stage": "semantic_analysis",
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "diagrams_analyzed": len(diagram_paths),
                    "risks_identified": semantic_analysis.get("consolidated_risks", [])
                })
            
            # Stage 3: Consolidate results (90-100%)
            await self.track_processing_progress(
                document_id, "consolidating_results", 90,
                "Consolidating contract analysis results"
            )
            
            consolidated_assessment = self._consolidate_contract_analysis(
                text_extraction,
                processing_results.get("semantic_analysis"),
                contract_context
            )
            
            processing_results["consolidated_assessment"] = consolidated_assessment
            processing_results["processing_stages"].append({
                "stage": "consolidation",
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "overall_confidence": consolidated_assessment.get("overall_confidence", 0.0)
            })
            
            # Final progress update
            await self.track_processing_progress(
                document_id, "completed", 100,
                "Complete contract analysis finished successfully"
            )
            
            return processing_results
            
        except Exception as e:
            logger.error(f"Complete contract processing failed for {document_id}: {str(e)}")
            
            await self.track_processing_progress(
                document_id, "failed", 0,
                f"Contract processing failed: {str(e)}"
            )
            
            processing_results["errors"].append({
                "error": str(e),
                "stage": "contract_processing",
                "timestamp": datetime.now(UTC).isoformat()
            })
            
            return processing_results

    def _consolidate_contract_analysis(
        self,
        text_extraction: Optional[Dict[str, Any]],
        semantic_analysis: Optional[Dict[str, Any]],
        contract_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consolidate text extraction and semantic analysis results"""
        
        consolidation = {
            "overall_confidence": 0.0,
            "analysis_completeness": {
                "text_extracted": bool(text_extraction and text_extraction.get("extracted_text")),
                "semantic_analysis_completed": bool(semantic_analysis and not semantic_analysis.get("analysis_failed")),
                "diagrams_analyzed": len(semantic_analysis.get("diagram_analyses", [])) if semantic_analysis else 0
            },
            "key_insights": {
                "contract_summary": {},
                "property_risks": [],
                "critical_actions": [],
                "professional_consultations": []
            },
            "integrated_recommendations": []
        }
        
        # Process text extraction results
        if text_extraction and text_extraction.get("extracted_text"):
            contract_analysis = text_extraction.get("contract_validation", {}).get("contract_analysis", {})
            consolidation["key_insights"]["contract_summary"] = {
                "appears_to_be_contract": contract_analysis.get("appears_to_be_contract", False),
                "contract_likelihood": contract_analysis.get("contract_likelihood", 0.0),
                "key_terms_found": contract_analysis.get("indicators_found", [])
            }
            text_confidence = text_extraction.get("extraction_confidence", 0.0)
        else:
            text_confidence = 0.0
        
        # Process semantic analysis results
        if semantic_analysis and not semantic_analysis.get("analysis_failed"):
            overall_assessment = semantic_analysis.get("overall_assessment", {})
            consolidated_risks = semantic_analysis.get("consolidated_risks", [])
            recommendations = semantic_analysis.get("recommendations", [])
            
            consolidation["key_insights"]["property_risks"] = [
                {
                    "risk_type": risk.get("risk_type", "Unknown"),
                    "severity": risk.get("severity", "unknown"),
                    "category": risk.get("category", "general"),
                    "source_diagrams": risk.get("source_diagrams", [])
                }
                for risk in consolidated_risks
            ]
            
            consolidation["key_insights"]["critical_actions"] = [
                rec.get("recommendation", "") for rec in recommendations
                if rec.get("priority") in ["critical", "high"]
            ]
            
            consolidation["key_insights"]["professional_consultations"] = list(set([
                rec.get("professional_required", "") for rec in recommendations
                if rec.get("professional_required")
            ]))
            
            semantic_confidence = overall_assessment.get("confidence_level", 0.0)
        else:
            semantic_confidence = 0.0
        
        # Calculate overall confidence
        if text_confidence > 0 and semantic_confidence > 0:
            consolidation["overall_confidence"] = (text_confidence + semantic_confidence) / 2
        elif text_confidence > 0:
            consolidation["overall_confidence"] = text_confidence * 0.7  # Penalty for missing semantic analysis
        elif semantic_confidence > 0:
            consolidation["overall_confidence"] = semantic_confidence * 0.8  # Penalty for missing text analysis
        else:
            consolidation["overall_confidence"] = 0.0
        
        # Generate integrated recommendations
        consolidation["integrated_recommendations"] = self._generate_integrated_recommendations(
            consolidation["key_insights"],
            contract_context,
            consolidation["overall_confidence"]
        )
        
        return consolidation

    def _generate_integrated_recommendations(
        self,
        key_insights: Dict[str, Any],
        contract_context: Dict[str, Any],
        overall_confidence: float
    ) -> List[Dict[str, Any]]:
        """Generate integrated recommendations from both text and semantic analysis"""
        
        recommendations = []
        
        # Contract-specific recommendations
        contract_summary = key_insights.get("contract_summary", {})
        if not contract_summary.get("appears_to_be_contract", False):
            recommendations.append({
                "type": "document_verification", 
                "priority": "high",
                "recommendation": "Verify that this document is the complete contract - low contract likelihood detected",
                "source": "text_analysis"
            })
        
        # Risk-based recommendations
        property_risks = key_insights.get("property_risks", [])
        high_risk_count = len([r for r in property_risks if r.get("severity") in ["high", "critical"]])
        
        if high_risk_count > 0:
            recommendations.append({
                "type": "risk_mitigation",
                "priority": "critical" if high_risk_count > 2 else "high",
                "recommendation": f"Address {high_risk_count} high-priority property risks before proceeding",
                "source": "semantic_analysis"
            })
        
        # Professional consultation recommendations
        consultations = key_insights.get("professional_consultations", [])
        if consultations:
            recommendations.append({
                "type": "professional_advice",
                "priority": "high",
                "recommendation": f"Engage the following professionals: {', '.join(consultations)}",
                "source": "integrated_analysis"
            })
        
        # Confidence-based recommendations
        if overall_confidence < 0.5:
            recommendations.append({
                "type": "analysis_quality",
                "priority": "medium",
                "recommendation": "Consider providing additional documents or higher quality images for more comprehensive analysis",
                "source": "quality_assessment"
            })
        
        # User experience recommendations
        user_experience = contract_context.get("user_experience_level", "novice")
        if user_experience == "novice" and (high_risk_count > 0 or overall_confidence < 0.6):
            recommendations.append({
                "type": "experience_support",
                "priority": "high", 
                "recommendation": "Given your experience level and the complexity identified, strongly recommend comprehensive legal review",
                "source": "user_context"
            })
        
        return recommendations

    async def get_semantic_analysis_capabilities(self) -> Dict[str, Any]:
        """Get semantic analysis capabilities"""
        
        if not self.semantic_analysis_service:
            return {
                "semantic_analysis_available": False,
                "reason": "Semantic analysis service not initialized"
            }
        
        try:
            return await self.semantic_analysis_service.get_analysis_capabilities()
        except Exception as e:
            logger.error(f"Failed to get semantic analysis capabilities: {str(e)}")
            return {
                "semantic_analysis_available": False,
                "reason": str(e)
            }
    
    async def process_document_with_progress(
        self,
        storage_path: str,
        file_type: str,
        document_id: str,
        contract_context: Optional[Dict[str, Any]] = None,
        processing_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process document with detailed progress tracking"""
        
        processing_options = processing_options or {}
        
        try:
            # Stage 1: Initialization (0-10%)
            await self.track_processing_progress(
                document_id,
                "initializing",
                5,
                "Starting document processing",
                {"storage_path": storage_path, "file_type": file_type},
            )
            
            # Stage 2: File validation (10-20%)
            await self.track_processing_progress(
                document_id,
                "validating",
                15,
                "Validating document format and integrity",
            )
            
            # Validate document
            file_content = await self.get_file_content(storage_path)
            filename = Path(storage_path).name
            self._validate_file(file_content, filename)
            
            # Stage 3: Text extraction decision (20-30%)
            await self.track_processing_progress(
                document_id,
                "preparing_extraction",
                25,
                "Determining optimal text extraction method",
            )
            
            # Determine extraction method
            use_ocr = self._should_use_ocr(
                file_content, file_type, processing_options.get("force_ocr", False)
            )
            
            extraction_method = "OCR" if use_ocr else "Traditional"
            
            # Stage 4: Text extraction (30-70%)
            await self.track_processing_progress(
                document_id,
                "extracting_text",
                40,
                f"Extracting text using {extraction_method} method",
                {"extraction_method": extraction_method},
            )
            
            # Extract text
            if use_ocr and self.ocr_service:
                extraction_result = await self.extract_text_with_ocr(
                    storage_path, file_type, contract_context, processing_options
                )
            else:
                extraction_result = await self.extract_text(
                    storage_path, file_type, contract_context
                )
            
            # Stage 5: Quality assessment (70-85%)
            await self.track_processing_progress(
                document_id,
                "assessing_quality",
                75,
                "Analyzing document quality and content",
            )
            
            # Assess quality
            quality_assessment = self.assess_document_quality(
                extraction_result.get("extracted_text", ""),
                file_type,
                len(file_content),
                extraction_result.get("extraction_method", "unknown"),
                extraction_result.get("extraction_confidence", 0.0),
                contract_context,
            )
            
            # Stage 6: Contract validation (85-95%)
            if contract_context:
                await self.track_processing_progress(
                    document_id,
                    "validating_contract",
                    90,
                    "Validating contract-specific content",
                )
                
                contract_validation = await self.validate_contract_document(
                    storage_path, file_type, contract_context
                )
            else:
                contract_validation = {}
            
            # Stage 7: Finalization (95-100%)
            await self.track_processing_progress(
                document_id,
                "finalizing",
                95,
                "Finalizing processing results",
            )
            
            # Combine all results
            final_result = {
                **extraction_result,
                "document_id": document_id,
                "processing_stages_completed": 7,
                "quality_assessment": quality_assessment,
                "contract_validation": contract_validation,
                "processing_options": processing_options,
                "final_timestamp": datetime.now(UTC).isoformat(),
            }
            
            # Final progress update
            await self.track_processing_progress(
                document_id,
                "completed",
                100,
                "Document processing completed successfully",
                {
                    "extraction_confidence": extraction_result.get("extraction_confidence", 0.0),
                    "quality_score": quality_assessment.get("overall_score", 0.0),
                    "contract_likelihood": contract_validation.get("contract_analysis", {}).get("contract_likelihood", 0.0) if contract_validation else None,
                },
            )
            
            return final_result
            
        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {str(e)}")
            
            # Error progress update
            await self.track_processing_progress(
                document_id,
                "failed",
                0,
                f"Processing failed: {str(e)}",
                {"error": str(e)},
            )
            
            return {
                "document_id": document_id,
                "extracted_text": "",
                "extraction_method": "failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
                "processing_failed": True,
            }
