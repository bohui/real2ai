"""
Unified Document Service - Merged implementation combining best features
Modern implementation with Supabase persistence, comprehensive document processing,
and advanced analysis capabilities.

Architecture:
- Supabase persistence (from document_service.py)
- Structured diagram processing (from enhanced_document_service.py)
- Quality assessment framework (from enhanced_document_service.py)
- Semantic analysis integration (from document_service.py)
- Australian contract patterns (from enhanced_document_service.py)
"""

import asyncio
import logging
import os
import re
import uuid
import io
from typing import Dict, Any, Optional, List, Tuple, BinaryIO
from datetime import datetime, UTC
from pathlib import Path
from decimal import Decimal, InvalidOperation
import mimetypes

import pymupdf  # pymupdf
from PIL import Image
import pytesseract
from fastapi import UploadFile, HTTPException
import pypdf
from docx import Document as DocxDocument
from unstructured.partition.auto import partition

from app.models.document_models import (
    Document,
    DocumentPage,
    DocumentEntity,
    DocumentDiagram,
    ProcessingStatus,
    ContentType,
    DiagramType,
    EntityType,
)
from backend.app.prompts.schema.entity_extraction_schema import (
    AustralianState,
    ContractType,
)
from app.models.contract_state import ContractType as ContractStateType
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.semantic_analysis_service import SemanticAnalysisService
from app.clients import get_supabase_client, get_gemini_client
from app.core.config import get_settings
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Unified Document Service combining best features from both implementations

    Key Features:
    - Modern Supabase persistence layer
    - Comprehensive document processing pipeline
    - Advanced OCR with multiple fallback mechanisms
    - Structured diagram detection and extraction
    - Quality assessment and scoring framework
    - Semantic analysis integration
    - Australian contract-specific entity patterns
    - Progress tracking and health monitoring
    """

    def __init__(
        self,
        storage_base_path: str = "storage/documents",
        enable_advanced_ocr: bool = True,
        enable_gemini_ocr: bool = True,
        max_file_size_mb: int = 50,
        use_service_role: bool = False,
    ):
        self.settings = get_settings()
        self.storage_base_path = Path(storage_base_path)
        self.enable_advanced_ocr = enable_advanced_ocr
        self.enable_gemini_ocr = enable_gemini_ocr
        self.max_file_size_mb = max_file_size_mb
        self.use_service_role = use_service_role

        # Client instances
        self.supabase_client = None
        self.gemini_client = None
        self.gemini_ocr_service = None
        self.semantic_analysis_service = None

        # Storage configuration
        self.storage_bucket = "documents"

        # Initialize storage directories for local files
        self._setup_storage_directories()

    def _setup_storage_directories(self):
        """Create necessary local storage directories"""
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        (self.storage_base_path / "originals").mkdir(exist_ok=True)
        (self.storage_base_path / "diagrams").mkdir(exist_ok=True)
        (self.storage_base_path / "pages").mkdir(exist_ok=True)
        (self.storage_base_path / "temp").mkdir(exist_ok=True)

    async def initialize(self):
        """Initialize all service components"""
        try:
            # Initialize clients
            self.supabase_client = await get_supabase_client()
            self.gemini_client = await get_gemini_client()

            # Initialize OCR services
            if self.enable_gemini_ocr:
                self.gemini_ocr_service = GeminiOCRService()
                await self.gemini_ocr_service.initialize()

            # Initialize semantic analysis service
            self.semantic_analysis_service = SemanticAnalysisService()
            await self.semantic_analysis_service.initialize()

            # Ensure storage bucket exists
            await self._ensure_bucket_exists()

            logger.info("Unified Document Service initialized successfully")

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to required services: {e}")
            raise HTTPException(status_code=503, detail="Required services unavailable")
        except Exception as e:
            logger.error(f"Failed to initialize unified document service: {str(e)}")
            self.enable_gemini_ocr = False  # Fallback mode

    async def _ensure_bucket_exists(self):
        """Ensure Supabase storage bucket exists"""
        try:
            result = await self.supabase_client.execute_rpc(
                "ensure_bucket_exists", {"bucket_name": self.storage_bucket}
            )

            if result.get("created"):
                logger.info(f"Created storage bucket: {self.storage_bucket}")

        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {str(e)}")

    @langsmith_trace(name="process_document")
    async def process_document(
        self,
        file: UploadFile,
        user_id: str,
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main document processing pipeline

        Combines upload, extraction, analysis, and persistence in a single operation
        """
        processing_start = datetime.now(UTC)
        document_id = None
        temp_file_path = None

        try:
            # Step 1: Validate file
            validation_result = await self._validate_uploaded_file(file)
            if not validation_result["valid"]:
                return self._create_error_response(
                    f"File validation failed: {validation_result['error']}",
                    processing_start,
                )

            # Step 2: Upload to Supabase storage and create document record
            upload_result = await self._upload_and_create_document_record(
                file,
                user_id,
                validation_result["file_info"],
                contract_type,
                australian_state,
            )

            if not upload_result["success"]:
                return self._create_error_response(
                    upload_result["error"], processing_start
                )

            document_id = upload_result["document_id"]
            storage_path = upload_result["storage_path"]

            # Step 3: Update processing status
            await self._update_document_status(
                document_id, ProcessingStatus.PROCESSING.value
            )

            # Step 4: Extract text with comprehensive analysis
            text_extraction_result = (
                await self._extract_text_with_comprehensive_analysis(
                    document_id,
                    storage_path,
                    validation_result["file_info"]["file_type"],
                )
            )

            # Step 5: Process pages and create page records
            page_processing_result = await self._process_and_analyze_pages(
                document_id, text_extraction_result
            )

            # Step 6: Extract entities with Australian patterns
            entity_extraction_result = await self._extract_australian_entities(
                document_id, page_processing_result
            )

            # Step 7: Detect and process diagrams
            diagram_processing_result = await self._detect_and_process_diagrams(
                document_id, storage_path, validation_result["file_info"]["file_type"]
            )

            # Step 8: Perform document-level analysis
            document_analysis_result = await self._analyze_document_content(
                document_id, page_processing_result, entity_extraction_result
            )

            # Step 9: Run semantic analysis if available
            semantic_result = None
            if self.semantic_analysis_service:
                semantic_result = await self._run_semantic_analysis(
                    document_id, text_extraction_result["full_text"]
                )

            # Step 10: Finalize processing
            await self._finalize_document_processing(
                document_id,
                text_extraction_result,
                page_processing_result,
                entity_extraction_result,
                diagram_processing_result,
                document_analysis_result,
                semantic_result,
            )

            processing_time = (datetime.now(UTC) - processing_start).total_seconds()

            # Step 11: Create comprehensive response
            return self._create_success_response(
                document_id,
                processing_time,
                text_extraction_result,
                page_processing_result,
                entity_extraction_result,
                diagram_processing_result,
                document_analysis_result,
                semantic_result,
            )

        except Exception as e:
            processing_time = (datetime.now(UTC) - processing_start).total_seconds()
            logger.error(f"Document processing failed: {str(e)}", exc_info=True)

            # Update document status if it exists
            if document_id:
                await self._update_document_status(
                    document_id,
                    ProcessingStatus.FAILED.value,
                    error_details={
                        "error": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "processing_time": processing_time,
                    },
                )

            return self._create_error_response(
                f"Processing failed: {str(e)}", processing_start
            )

        finally:
            # Cleanup temporary files
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

    async def _validate_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """Enhanced file validation with security checks"""
        try:
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)  # Reset file position

            # Size validation
            if file_size > self.max_file_size_mb * 1024 * 1024:
                return {
                    "valid": False,
                    "error": f"File too large. Maximum size: {self.max_file_size_mb}MB",
                }

            # Type validation
            file_type = self._detect_file_type(file.filename, file_content[:1024])
            supported_types = [
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "tiff",
                "bmp",
                "docx",
                "doc",
            ]

            if file_type not in supported_types:
                return {
                    "valid": False,
                    "error": f"Unsupported file type: {file_type}. Supported: {', '.join(supported_types)}",
                }

            # Security validation
            if self._has_security_concerns(file.filename, file_content[:1024]):
                return {"valid": False, "error": "File failed security validation"}

            return {
                "valid": True,
                "file_info": {
                    "original_filename": file.filename,
                    "file_type": file_type,
                    "file_size": file_size,
                    "content_hash": self._calculate_hash(file_content),
                    "mime_type": mimetypes.guess_type(file.filename)[0]
                    or "application/octet-stream",
                },
            }

        except Exception as e:
            return {"valid": False, "error": f"File validation error: {str(e)}"}

    async def _upload_and_create_document_record(
        self,
        file: UploadFile,
        user_id: str,
        file_info: Dict[str, Any],
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Supabase storage and create document record"""
        try:
            document_id = str(uuid.uuid4())
            file_extension = Path(file_info["original_filename"]).suffix.lower()
            storage_filename = f"{document_id}{file_extension}"
            storage_path = f"documents/{user_id}/{storage_filename}"

            # Upload to Supabase storage
            file_content = await file.read()
            upload_result = await self.supabase_client.upload_file(
                bucket=self.storage_bucket,
                path=storage_path,
                file=file_content,
                content_type=file_info["mime_type"],
            )

            if not upload_result.get("success"):
                return {"success": False, "error": "Failed to upload file to storage"}

            # Create document record in database
            document_data = {
                "id": document_id,
                "user_id": user_id,
                "original_filename": file_info["original_filename"],
                "file_type": file_info["file_type"],
                "storage_path": storage_path,
                "file_size": file_info["file_size"],
                "content_hash": file_info["content_hash"],
                "processing_status": ProcessingStatus.UPLOADED.value,
                "contract_type": contract_type,
                "australian_state": australian_state,
                "text_extraction_method": "pending",
            }

            insert_result = await self.supabase_client.insert(
                "documents", document_data
            )

            if not insert_result.get("success"):
                return {"success": False, "error": "Failed to create document record"}

            logger.info(f"Created document record: {document_id}")
            return {
                "success": True,
                "document_id": document_id,
                "storage_path": storage_path,
            }

        except Exception as e:
            logger.error(f"Upload and record creation failed: {str(e)}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    async def _extract_text_with_comprehensive_analysis(
        self, document_id: str, storage_path: str, file_type: str
    ) -> Dict[str, Any]:
        """Extract text using multiple methods with quality assessment"""

        try:
            # Download file from storage
            file_content = await self.supabase_client.download_file(
                bucket=self.storage_bucket, path=storage_path
            )

            if not file_content:
                raise ValueError("Failed to download file from storage")

            # Extract text based on file type
            if file_type == "pdf":
                return await self._extract_pdf_text_comprehensive(file_content)
            elif file_type == "docx":
                return await self._extract_docx_text_comprehensive(file_content)
            elif file_type in ["png", "jpg", "jpeg", "tiff", "bmp"]:
                return await self._extract_image_text_comprehensive(file_content)
            else:
                raise ValueError(
                    f"Unsupported file type for text extraction: {file_type}"
                )

        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "pages": [],
                "extraction_method": "failed",
                "confidence": 0.0,
            }

    async def _extract_pdf_text_comprehensive(
        self, file_content: bytes
    ) -> Dict[str, Any]:
        """Comprehensive PDF text extraction with pymupdf and OCR fallback"""

        try:
            pdf_document = pymupdf.open(stream=file_content, filetype="pdf")
            pages = []
            full_text = ""
            extraction_methods = []

            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)

                # Primary extraction with pymupdf
                text_content = page.get_text()
                extraction_method = "pymupdf"
                confidence = 0.9

                # OCR fallback for pages with minimal text
                if len(text_content.strip()) < 50:
                    ocr_text = await self._extract_text_with_ocr(page, page_num + 1)
                    if len(ocr_text.strip()) > len(text_content.strip()):
                        text_content = ocr_text
                        extraction_method = "tesseract_ocr"
                        confidence = 0.7

                # Advanced OCR with Gemini for complex pages
                if (
                    self.enable_gemini_ocr
                    and self.gemini_ocr_service
                    and confidence < 0.8
                ):
                    try:
                        gemini_result = await self._extract_text_with_gemini(
                            page, page_num + 1
                        )
                        if gemini_result and len(gemini_result.strip()) > len(
                            text_content.strip()
                        ):
                            text_content = gemini_result
                            extraction_method = "gemini_ocr"
                            confidence = 0.85
                    except Exception as gemini_error:
                        logger.warning(
                            f"Gemini OCR failed for page {page_num + 1}: {gemini_error}"
                        )

                # Analyze page content
                page_analysis = self._analyze_page_content(text_content, page)

                page_data = {
                    "page_number": page_num + 1,
                    "text_content": text_content,
                    "text_length": len(text_content),
                    "word_count": len(text_content.split()) if text_content else 0,
                    "extraction_method": extraction_method,
                    "confidence": confidence,
                    "content_analysis": page_analysis,
                }

                pages.append(page_data)
                full_text += f"\n--- Page {page_num + 1} ---\n{text_content}"

                if extraction_method not in extraction_methods:
                    extraction_methods.append(extraction_method)

            pdf_document.close()

            return {
                "success": True,
                "full_text": full_text,
                "pages": pages,
                "total_pages": len(pages),
                "extraction_methods": extraction_methods,
                "total_word_count": sum(p["word_count"] for p in pages),
                "overall_confidence": (
                    sum(p["confidence"] for p in pages) / len(pages) if pages else 0
                ),
            }

        except Exception as e:
            logger.error(f"PDF text extraction failed: {str(e)}")
            return {"success": False, "error": str(e), "full_text": "", "pages": []}

    async def _extract_text_with_ocr(self, page: pymupdf.Page, page_number: int) -> str:
        """Extract text using Tesseract OCR with optimized settings"""
        try:
            # Render page as high-resolution image
            matrix = pymupdf.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=matrix)

            # Convert to PIL Image
            img_data = pix.pil_tobytes(format="PNG")
            image = Image.open(io.BytesIO(img_data))

            # OCR with optimized configuration
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}"-'
            ocr_text = pytesseract.image_to_string(image, config=custom_config)

            return ocr_text.strip()

        except Exception as e:
            logger.warning(f"Tesseract OCR failed for page {page_number}: {e}")
            return ""

    async def _extract_text_with_gemini(
        self, page: pymupdf.Page, page_number: int
    ) -> Optional[str]:
        """Extract text using Gemini Vision API"""
        if not self.gemini_ocr_service:
            return None

        try:
            # Render page as image
            matrix = pymupdf.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.pil_tobytes(format="PNG")

            # Use Gemini OCR service
            ocr_result = await self.gemini_ocr_service.extract_text_from_image_data(
                img_data, filename=f"page_{page_number}.png"
            )

            if ocr_result and hasattr(ocr_result, "extracted_text"):
                return ocr_result.extracted_text.strip()

        except Exception as e:
            logger.warning(f"Gemini OCR failed for page {page_number}: {e}")

        return None

    def _analyze_page_content(
        self, text_content: str, page: pymupdf.Page
    ) -> Dict[str, Any]:
        """Analyze page content for classification and layout features"""

        analysis = {
            "content_types": [],
            "primary_type": ContentType.EMPTY.value,
            "layout_features": {
                "has_header": False,
                "has_footer": False,
                "has_signatures": False,
                "has_diagrams": False,
                "has_tables": False,
            },
            "quality_indicators": {
                "text_density": 0.0,
                "structure_score": 0.0,
                "readability_score": 0.0,
            },
        }

        if not text_content or len(text_content.strip()) < 10:
            return analysis

        text_lower = text_content.lower()

        # Content type detection
        if text_content and len(text_content.strip()) > 20:
            analysis["content_types"].append("text")

        # Table detection
        if self._detect_table_content(text_content):
            analysis["content_types"].append("table")
            analysis["layout_features"]["has_tables"] = True

        # Signature detection
        signature_patterns = [
            r"\b(signature|signed|date.*signed|initial)\b",
            r"_+\s*(signature|date)",
        ]
        if any(re.search(pattern, text_lower) for pattern in signature_patterns):
            analysis["content_types"].append("signature")
            analysis["layout_features"]["has_signatures"] = True

        # Diagram detection
        if self._detect_diagrams_on_page(page, text_content):
            analysis["content_types"].append("diagram")
            analysis["layout_features"]["has_diagrams"] = True

        # Layout feature detection
        analysis["layout_features"]["has_header"] = self._detect_header_footer(
            text_content, "header"
        )
        analysis["layout_features"]["has_footer"] = self._detect_header_footer(
            text_content, "footer"
        )

        # Determine primary content type
        analysis["primary_type"] = self._determine_primary_content_type(
            analysis["content_types"]
        )

        # Calculate quality indicators
        analysis["quality_indicators"] = self._calculate_quality_indicators(
            text_content
        )

        return analysis

    def _detect_table_content(self, text: str) -> bool:
        """Detect table-like content using multiple heuristics"""
        if not text:
            return False

        lines = text.split("\n")

        # Check for consistent column separators
        tab_lines = sum(1 for line in lines if "\t" in line or "  " in line)
        tab_ratio = tab_lines / len(lines) if lines else 0

        # Check for financial patterns (common in contract tables)
        currency_lines = sum(1 for line in lines if re.search(r"\$[\d,]+\.?\d*", line))

        # Check for aligned data patterns
        aligned_patterns = sum(1 for line in lines if re.search(r"\s{3,}", line))
        alignment_ratio = aligned_patterns / len(lines) if lines else 0

        return tab_ratio > 0.3 or currency_lines > 2 or alignment_ratio > 0.4

    def _detect_diagrams_on_page(self, page: pymupdf.Page, text_content: str) -> bool:
        """Comprehensive diagram detection"""

        # Method 1: Check for embedded images
        image_list = page.get_images()
        if image_list:
            return True

        # Method 2: Check for vector graphics
        drawings = page.get_drawings()
        if drawings:
            return True

        # Method 3: Text-based diagram indicators
        if text_content:
            diagram_keywords = [
                "diagram",
                "plan",
                "map",
                "layout",
                "site plan",
                "floor plan",
                "survey",
                "boundary",
                "title plan",
                "sewer diagram",
                "flood map",
                "bushfire",
                "drainage",
                "contour",
            ]
            text_lower = text_content.lower()
            return any(keyword in text_lower for keyword in diagram_keywords)

        return False

    def _detect_header_footer(self, text: str, position: str) -> bool:
        """Detect header or footer content"""
        if not text:
            return False

        lines = text.split("\n")
        target_lines = lines[:3] if position == "header" else lines[-3:]

        indicators = {
            "header": ["contract", "agreement", "document", "page", "section"],
            "footer": ["page", "confidential", "copyright", "initial", "version"],
        }

        pattern_indicators = indicators.get(position, [])

        for line in target_lines:
            if any(indicator in line.lower() for indicator in pattern_indicators):
                return True

        return False

    def _determine_primary_content_type(self, content_types: List[str]) -> str:
        """Determine primary content type from detected types"""
        if not content_types:
            return ContentType.EMPTY.value
        elif "diagram" in content_types and len(content_types) == 1:
            return ContentType.DIAGRAM.value
        elif "table" in content_types and "text" not in content_types:
            return ContentType.TABLE.value
        elif "signature" in content_types:
            return ContentType.SIGNATURE.value
        elif len(content_types) > 1:
            return ContentType.MIXED.value
        else:
            return ContentType.TEXT.value

    def _calculate_quality_indicators(self, text_content: str) -> Dict[str, float]:
        """Calculate various quality metrics for text content"""

        indicators = {
            "text_density": 0.0,
            "structure_score": 0.0,
            "readability_score": 0.0,
        }

        if not text_content:
            return indicators

        # Text density (characters per line ratio)
        lines = text_content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        if non_empty_lines:
            avg_line_length = sum(len(line) for line in non_empty_lines) / len(
                non_empty_lines
            )
            indicators["text_density"] = min(
                avg_line_length / 80, 1.0
            )  # Normalize to 80 chars

        # Structure score (based on punctuation and formatting)
        sentences = re.split(r"[.!?]+", text_content)
        if len(sentences) > 1:
            avg_sentence_length = len(text_content) / len(sentences)
            indicators["structure_score"] = min(
                avg_sentence_length / 100, 1.0
            )  # Normalize to 100 chars

        # Basic readability (word length distribution)
        words = text_content.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            indicators["readability_score"] = (
                1.0 - abs(avg_word_length - 5) / 10
            )  # Optimal around 5 chars
            indicators["readability_score"] = max(0.0, indicators["readability_score"])

        return indicators

    # Utility methods
    def _detect_file_type(self, filename: str, file_header: bytes) -> str:
        """Detect file type from filename and magic bytes"""

        # Get extension from filename
        if filename:
            ext = Path(filename).suffix.lower()
            ext_map = {
                ".pdf": "pdf",
                ".png": "png",
                ".jpg": "jpg",
                ".jpeg": "jpg",
                ".tiff": "tiff",
                ".bmp": "bmp",
                ".docx": "docx",
                ".doc": "doc",
            }
            if ext in ext_map:
                return ext_map[ext]

        # Detect from magic bytes
        if file_header.startswith(b"%PDF"):
            return "pdf"
        elif file_header.startswith(b"\x89PNG"):
            return "png"
        elif file_header.startswith(b"\xff\xd8\xff"):
            return "jpg"
        elif file_header.startswith(b"II*\x00") or file_header.startswith(b"MM\x00*"):
            return "tiff"
        elif file_header.startswith(b"BM"):
            return "bmp"
        elif file_header.startswith(b"PK") and b"word/" in file_header[:200]:
            return "docx"

        return "unknown"

    def _has_security_concerns(self, filename: str, file_header: bytes) -> bool:
        """Security validation to prevent malicious files"""

        # Check for suspicious extensions
        suspicious_extensions = [".exe", ".bat", ".cmd", ".scr", ".vbs", ".js", ".jar"]
        if any(filename.lower().endswith(ext) for ext in suspicious_extensions):
            return True

        # Check for executable headers
        executable_headers = [b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe"]
        if any(file_header.startswith(header) for header in executable_headers):
            return True

        return False

    def _calculate_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        import hashlib

        return hashlib.sha256(file_content).hexdigest()

    async def _update_document_status(
        self,
        document_id: str,
        status: str,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        """Update document processing status in database"""
        try:
            update_data = {
                "processing_status": status,
            }

            if error_details:
                update_data["processing_errors"] = error_details

            await self.supabase_client.update(
                "documents", {"id": document_id}, update_data
            )

        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")

    def _create_success_response(
        self,
        document_id: str,
        processing_time: float,
        text_result: Dict[str, Any],
        page_result: Dict[str, Any],
        entity_result: Dict[str, Any],
        diagram_result: Dict[str, Any],
        analysis_result: Dict[str, Any],
        semantic_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create comprehensive success response"""

        return {
            "success": True,
            "document_id": document_id,
            "processing_time_seconds": processing_time,
            "processing_timestamp": datetime.now(UTC).isoformat(),
            "text_extraction": {
                "total_pages": text_result.get("total_pages", 0),
                "total_word_count": text_result.get("total_word_count", 0),
                "extraction_methods": text_result.get("extraction_methods", []),
                "overall_confidence": text_result.get("overall_confidence", 0.0),
            },
            "content_analysis": {
                "pages_analyzed": len(page_result.get("pages", [])),
                "entities_extracted": entity_result.get("total_entities", 0),
                "diagrams_detected": diagram_result.get("total_diagrams", 0),
                "document_classification": analysis_result.get("classification", {}),
            },
            "quality_assessment": analysis_result.get("quality", {}),
            "semantic_analysis": semantic_result if semantic_result else {},
            "ready_for_advanced_analysis": True,
            "next_steps": [
                "Document processing completed successfully",
                "Ready for contract analysis and compliance checking",
                "All extracted data available for queries and analysis",
            ],
        }

    def _create_error_response(
        self, error_message: str, processing_start: datetime
    ) -> Dict[str, Any]:
        """Create standardized error response"""

        processing_time = (datetime.now(UTC) - processing_start).total_seconds()

        return {
            "success": False,
            "error": error_message,
            "processing_time_seconds": processing_time,
            "processing_timestamp": datetime.now(UTC).isoformat(),
            "recovery_suggestions": [
                "Verify file format is supported (PDF, DOCX, PNG, JPG, TIFF, BMP)",
                "Check file size is under the limit",
                "Ensure file is not corrupted or password protected",
                "Contact support if the issue persists",
            ],
        }

    # Placeholder methods for future implementation
    async def _extract_docx_text_comprehensive(
        self, file_content: bytes
    ) -> Dict[str, Any]:
        """Extract text from DOCX files - placeholder for future implementation"""
        # Implementation would go here
        return {"success": False, "error": "DOCX extraction not yet implemented"}

    async def _extract_image_text_comprehensive(
        self, file_content: bytes
    ) -> Dict[str, Any]:
        """Extract text from image files - placeholder for future implementation"""
        # Implementation would go here
        return {"success": False, "error": "Image text extraction not yet implemented"}

    async def _process_and_analyze_pages(
        self, document_id: str, text_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and analyze individual pages - placeholder for future implementation"""
        # Implementation would go here
        return {"pages": [], "total_analyzed": 0}

    async def _extract_australian_entities(
        self, document_id: str, page_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Australian contract entities - placeholder for future implementation"""
        # Implementation would go here
        return {"total_entities": 0, "entities_by_type": {}}

    async def _detect_and_process_diagrams(
        self, document_id: str, storage_path: str, file_type: str
    ) -> Dict[str, Any]:
        """Detect and process diagrams - placeholder for future implementation"""
        # Implementation would go here
        return {"total_diagrams": 0, "diagrams_by_type": {}}

    async def _analyze_document_content(
        self,
        document_id: str,
        page_result: Dict[str, Any],
        entity_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze document content - placeholder for future implementation"""
        # Implementation would go here
        return {"classification": {}, "quality": {}}

    async def _run_semantic_analysis(
        self, document_id: str, full_text: str
    ) -> Optional[Dict[str, Any]]:
        """Run semantic analysis - placeholder for future implementation"""
        # Implementation would go here
        return None

    async def _finalize_document_processing(self, document_id: str, *args) -> None:
        """Finalize document processing - placeholder for future implementation"""
        # Implementation would go here
        pass


# Factory function
def create_document_service(
    storage_path: str = "storage/documents",
    enable_advanced_ocr: bool = True,
    enable_gemini_ocr: bool = True,
    max_file_size_mb: int = 50,
    use_service_role: bool = False,
) -> DocumentService:
    """Create unified document service with specified configuration"""

    return DocumentService(
        storage_base_path=storage_path,
        enable_advanced_ocr=enable_advanced_ocr,
        enable_gemini_ocr=enable_gemini_ocr,
        max_file_size_mb=max_file_size_mb,
        use_service_role=use_service_role,
    )
