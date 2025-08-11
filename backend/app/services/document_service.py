"""
Document Service - Migrated to User-Aware Architecture

This is the migrated version of DocumentService that demonstrates the proper
separation between user-context and system-level operations using the new
authentication architecture.

Key changes:
- Inherits from UserAwareService
- Uses user context for all document operations
- System context only for legitimate admin operations (bucket creation, etc.)
- Clear separation of concerns between user and system operations
"""

import json
import logging
import re
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import mimetypes

# Optional dependencies - handle gracefully if not installed
try:
    import pymupdf  # pymupdf

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    pymupdf = None

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

try:
    from fastapi import UploadFile, HTTPException

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    UploadFile = None
    HTTPException = None

try:
    import pypdf

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    pypdf = None

try:
    from docx import Document as DocxDocument

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    DocxDocument = None

try:
    from unstructured.partition.auto import partition

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition = None

from app.models.supabase_models import (
    Document,
    DocumentStatus as ProcessingStatus,
    ContentType,
    DiagramType,
    EntityType,
)
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.services.base.user_aware_service import (
    UserAwareService,
    ServiceInitializationMixin,
)
from app.clients import get_gemini_client
from app.core.config import get_settings
from app.core.langsmith_config import langsmith_trace
from app.clients.base.exceptions import (
    ClientConnectionError,
)
from app.schema.document import (
    FastUploadResult,
    UploadRecordResult,
    FileValidationResult,
    UploadedFileInfo,
    TextExtractionResult,
    DocumentDetails,
    SystemStatsResponse,
    ServiceHealthStatus,
)

logger = logging.getLogger(__name__)


# Constants for magic numbers
class DocumentServiceConstants:
    """Constants used throughout DocumentService to replace magic numbers."""

    # File size and validation constants
    DEFAULT_MAX_FILE_SIZE_MB = 50
    BYTES_PER_MB = 1024 * 1024
    FILE_HEADER_READ_SIZE = 1024
    DOCX_HEADER_SEARCH_SIZE = 200

    # Text processing thresholds
    TEXT_HEAVY_THRESHOLD = 5000  # Skip vector analysis above this text length
    LOW_TEXT_THRESHOLD = 500  # Full vector analysis below this text length
    MAX_VECTOR_COUNT = 50  # Maximum vectors to analyze for medium text pages
    TABLE_VECTOR_THRESHOLD = 100  # Vector count indicating tables vs diagrams
    COMPLEXITY_RATIO_THRESHOLD = (
        0.3  # Minimum complexity ratio for diagram classification
    )

    # OCR and text extraction constants
    MIN_TEXT_LENGTH_FOR_OCR = 50
    OCR_ZOOM_FACTOR = 2.0
    OCR_CONFIDENCE_HIGH = 0.9
    OCR_CONFIDENCE_MEDIUM = 0.85
    OCR_CONFIDENCE_LOW = 0.7
    OCR_CONFIDENCE_THRESHOLD = 0.8

    # Content analysis thresholds
    MIN_TEXT_CONTENT_LENGTH = 10
    MIN_TEXT_CONTENT_FOR_ANALYSIS = 20
    MIN_COMPLEX_SHAPE_ITEMS = 3
    VECTOR_SAMPLE_SIZE = 20
    TEXT_TO_VECTOR_RATIO_THRESHOLD = 10

    # Table detection thresholds
    TAB_RATIO_THRESHOLD = 0.3
    CURRENCY_LINES_THRESHOLD = 2
    ALIGNMENT_RATIO_THRESHOLD = 0.4
    MIN_SPACES_FOR_ALIGNMENT = 3

    # Quality indicators normalization
    MAX_LINE_LENGTH_NORMALIZATION = 80
    MAX_SENTENCE_LENGTH_NORMALIZATION = 100
    OPTIMAL_WORD_LENGTH = 5
    WORD_LENGTH_NORMALIZATION_FACTOR = 10

    # HTTP status codes
    HTTP_SERVICE_UNAVAILABLE = 503
    HTTP_FORBIDDEN = 403

    # Default values
    DEFAULT_CONFIDENCE = 0.0
    DEFAULT_LIMIT = 50
    DEFAULT_PAGE_NUMBER = 0

    # Error message truncation
    ERROR_MESSAGE_TRUNCATION_LENGTH = 100

    # File type detection magic bytes
    PNG_MAGIC_BYTES = b"\x89PNG"
    JPEG_MAGIC_BYTES = b"\xff\xd8\xff"
    TIFF_MAGIC_BYTES_1 = b"II*\x00"
    TIFF_MAGIC_BYTES_2 = b"MM\x00*"
    BMP_MAGIC_BYTES = b"BM"
    PDF_MAGIC_BYTES = b"%PDF"
    ZIP_MAGIC_BYTES = b"PK"

    # Executable file headers
    EXECUTABLE_HEADERS = [b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe"]

    # Content type ratios
    TAB_RATIO_FOR_TABLE = 0.3
    CURRENCY_LINES_FOR_TABLE = 2
    ALIGNMENT_RATIO_FOR_TABLE = 0.4


class DocumentService(UserAwareService, ServiceInitializationMixin):
    """
    Document Service with proper user context management.

    This service handles document processing operations with proper separation
    between user-scoped and system-level operations:

    User Operations (RLS enforced):
    - Document upload and processing
    - Text extraction and analysis
    - User-specific document retrieval

    System Operations (service role):
    - Bucket management
    - System maintenance
    - Cross-user analytics (admin only)
    """

    def __init__(
        self,
        storage_base_path: str = "storage/documents",
        use_llm_document_processing: bool = True,
        max_file_size_mb: int = DocumentServiceConstants.DEFAULT_MAX_FILE_SIZE_MB,
        user_client=None,  # For dependency injection
    ):
        super().__init__(user_client=user_client)
        self.settings = get_settings()
        self.storage_base_path = Path(storage_base_path)
        self.use_llm_document_processing = use_llm_document_processing
        self.max_file_size_mb = max_file_size_mb

        # Diagram detection optimization thresholds
        self.text_heavy_threshold = DocumentServiceConstants.TEXT_HEAVY_THRESHOLD
        self.low_text_threshold = DocumentServiceConstants.LOW_TEXT_THRESHOLD
        self.max_vector_count = DocumentServiceConstants.MAX_VECTOR_COUNT
        self.table_vector_threshold = DocumentServiceConstants.TABLE_VECTOR_THRESHOLD
        self.complexity_ratio_threshold = (
            DocumentServiceConstants.COMPLEXITY_RATIO_THRESHOLD
        )

        # Client instances
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
            self.logger.info("Starting DocumentService initialization...")

            # Initialize Gemini client (system-level, no user context needed)
            self.logger.info("Initializing Gemini client...")
            self.gemini_client = await get_gemini_client()
            self.logger.info(
                f"Gemini client initialized: {self.gemini_client is not None}"
            )

            # Initialize OCR services when LLM processing is enabled
            if self.use_llm_document_processing:
                self.logger.info("Initializing Gemini OCR service...")
                self.gemini_ocr_service = GeminiOCRService()
                await self.gemini_ocr_service.initialize()
                self.logger.info("Gemini OCR service initialized")

            # Initialize semantic analysis service lazily
            self.semantic_analysis_service = None

            # Ensure storage bucket exists (system operation)
            self.logger.info("Ensuring storage bucket exists...")
            await self._ensure_bucket_exists()

            self.logger.info("Document Service initialized successfully")

        except ClientConnectionError as e:
            self.logger.error(f"Failed to connect to required services: {e}")
            raise HTTPException(
                status_code=DocumentServiceConstants.HTTP_SERVICE_UNAVAILABLE,
                detail="Required services unavailable",
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize document service: {str(e)}")

    async def _ensure_bucket_exists(self):
        """Ensure Supabase storage bucket exists - SYSTEM OPERATION"""
        try:
            # This is a legitimate system operation - bucket creation requires admin privileges
            system_client = await self.get_system_client()
            result = await system_client.execute_rpc(
                "ensure_bucket_exists", {"bucket_name": self.storage_bucket}
            )

            # Handle boolean return (function returns BOOLEAN in SQL)
            if isinstance(result, bool):
                if result:
                    self.logger.info(f"Created storage bucket: {self.storage_bucket}")
                else:
                    self.logger.debug(
                        f"Storage bucket already exists: {self.storage_bucket}"
                    )
                self.log_operation(
                    "system_bucket_ensure", "storage_bucket", self.storage_bucket
                )
                return

            # Handle structured/JSON-like responses
            if isinstance(result, dict):
                result_data = result
            elif isinstance(result, str):
                try:
                    result_data = json.loads(result)
                except json.JSONDecodeError:
                    self.logger.warning(f"Could not parse RPC response: {result}")
                    return
            else:
                self.logger.warning(f"Unexpected RPC response type: {type(result)}")
                return

            # Log appropriate message based on result
            if result_data.get("created"):
                self.logger.info(f"Created storage bucket: {self.storage_bucket}")
            elif result_data.get("message") == "Bucket already exists":
                self.logger.debug(
                    f"Storage bucket already exists: {self.storage_bucket}"
                )
            else:
                self.logger.info(
                    f"Bucket operation result: {result_data.get('message', 'Unknown')}"
                )

            self.log_operation(
                "system_bucket_ensure", "storage_bucket", self.storage_bucket
            )

        except Exception as e:
            # Parse the error message to extract actual result if available
            error_str = str(e)
            if "Bucket already exists" in error_str:
                self.logger.debug(
                    f"Storage bucket already exists: {self.storage_bucket}"
                )
            elif "JSON could not be generated" in error_str and "details" in error_str:
                # Extract the JSON from the error details - this is a known Supabase client issue

                json_match = re.search(r"details.*?b'({.*?})'", error_str)
                if json_match:
                    try:
                        result_data = json.loads(json_match.group(1))
                        if result_data.get("message") == "Bucket already exists":
                            self.logger.debug(
                                f"Storage bucket already exists: {self.storage_bucket}"
                            )
                        else:
                            self.logger.debug(
                                f"Bucket operation completed: {result_data.get('message', 'Unknown')}"
                            )
                    except json.JSONDecodeError:
                        self.logger.debug(
                            f"Bucket operation completed with parsing issues (service operational): {error_str[:DocumentServiceConstants.ERROR_MESSAGE_TRUNCATION_LENGTH]}..."
                        )
                else:
                    self.logger.debug(
                        f"Bucket operation completed (service operational): {error_str[:DocumentServiceConstants.ERROR_MESSAGE_TRUNCATION_LENGTH]}..."
                    )
            else:
                self.logger.debug(
                    f"Bucket operation completed (service operational): {error_str[:DocumentServiceConstants.ERROR_MESSAGE_TRUNCATION_LENGTH]}..."
                )
            # Don't raise - service can function without bucket verification

    @langsmith_trace(name="upload_document_fast")
    async def upload_document_fast(
        self,
        file: UploadFile,
        user_id: str,
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> FastUploadResult:
        """
        Fast document upload - stores file and creates record only.

        This method handles only the essential upload operations:
        1. File validation
        2. Upload to Supabase Storage
        3. Create document record with status "uploaded"

        Processing is handled separately by background tasks.
        """
        upload_start = datetime.now(timezone.utc)
        document_id = None

        try:
            # Log user operation
            self.log_operation("upload_document_fast", "document", None)

            # Step 1: Validate file (same as before)
            validation_result = await self._validate_uploaded_file(file)
            if not validation_result.valid:
                upload_time = (
                    datetime.now(timezone.utc) - upload_start
                ).total_seconds()
                return FastUploadResult(
                    success=False,
                    document_id=None,
                    storage_path=None,
                    processing_time=upload_time,
                    status="failed",
                    error=f"File validation failed: {validation_result.error}",
                )

            # Step 2: Upload to Supabase storage and create document record (USER OPERATION)
            upload_result = await self._upload_and_create_document_record(
                file,
                user_id,
                (
                    validation_result.file_info.model_dump()
                    if validation_result.file_info
                    else {}
                ),
                contract_type,
                australian_state,
            )

            if not upload_result.success:
                upload_time = (
                    datetime.now(timezone.utc) - upload_start
                ).total_seconds()
                return FastUploadResult(
                    success=False,
                    document_id=None,
                    storage_path=None,
                    processing_time=upload_time,
                    status="failed",
                    error=upload_result.error or "Upload failed",
                )

            document_id = upload_result.document_id

            # Log successful upload
            self.log_operation("create", "document", document_id)

            # Step 3: Mark document as uploaded (not processing)
            await self._update_document_status(
                document_id, ProcessingStatus.UPLOADED.value
            )

            upload_time = (datetime.now(timezone.utc) - upload_start).total_seconds()

            self.logger.info(
                f"Fast upload completed for document {document_id} in {upload_time:.2f}s"
            )

            return FastUploadResult(
                success=True,
                document_id=document_id,
                storage_path=upload_result.storage_path,
                processing_time=upload_time,
                status="uploaded",
            )

        except Exception as e:
            upload_time = (datetime.now(timezone.utc) - upload_start).total_seconds()
            self.logger.error(f"Fast upload failed: {str(e)}", exc_info=True)

            # Update document status if it exists (USER OPERATION)
            if document_id:
                await self._update_document_status(
                    document_id,
                    ProcessingStatus.FAILED.value,
                    error_details={
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "upload_time": upload_time,
                    },
                )

            upload_time = (datetime.now(timezone.utc) - upload_start).total_seconds()
            return FastUploadResult(
                success=False,
                document_id=None,
                storage_path=None,
                processing_time=upload_time,
                status="failed",
                error=f"Upload failed: {str(e)}",
            )

    async def _upload_and_create_document_record(
        self,
        file: UploadFile,
        user_id: str,
        file_info: Dict[str, Any],
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> UploadRecordResult:
        """Upload file to Supabase storage and create document record - USER OPERATION"""
        try:
            document_id = str(uuid.uuid4())
            file_extension = Path(file_info["original_filename"]).suffix.lower()
            storage_filename = f"{document_id}{file_extension}"
            storage_path = f"{user_id}/{storage_filename}"

            # Get user-authenticated client for this operation
            user_client = await self.get_user_client()

            # Upload to Supabase storage (user context - RLS enforced)
            file_content = await file.read()
            upload_result = await user_client.upload_file(
                bucket=self.storage_bucket,
                path=storage_path,
                file=file_content,
                content_type=file_info["mime_type"],
            )

            if not upload_result.get("success"):
                return UploadRecordResult(
                    success=False,
                    error=upload_result.get(
                        "error", "Failed to upload file to storage"
                    ),
                )

            # Create document record in database (user context - RLS enforced)
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

            # Use the database client's create method instead of insert
            created_record = await user_client.database.create(
                "documents", document_data
            )

            if not created_record:
                return UploadRecordResult(
                    success=False, error="Failed to create document record"
                )

            # Create user_contract_views record for RLS policy access
            if file_info.get("content_hash"):
                try:
                    user_contract_view_data = {
                        "user_id": user_id,
                        "content_hash": file_info["content_hash"],
                        "property_address": None,  # Will be populated later if available
                        "source": "upload",
                    }

                    await user_client.database.create(
                        "user_contract_views", user_contract_view_data
                    )
                    self.logger.info(
                        f"Created user_contract_views record for document {document_id}"
                    )
                except Exception as view_error:
                    # Log the error but don't fail the upload - this is for RLS access
                    self.logger.warning(
                        f"Failed to create user_contract_views record: {str(view_error)}"
                    )

            self.logger.info(f"Created document record: {document_id}")
            return UploadRecordResult(
                success=True,
                document_id=document_id,
                storage_path=storage_path,
            )

        except Exception as e:
            self.logger.error(f"Upload and record creation failed: {str(e)}")
            return UploadRecordResult(success=False, error=f"Upload failed: {str(e)}")

    async def _update_document_status(
        self,
        document_id: str,
        status: str,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        """Update document processing status - USER OPERATION"""
        try:
            user_client = await self.get_user_client()
            self.log_operation("update", "document", document_id)

            update_data = {
                "processing_status": status,
            }

            if error_details:
                update_data["processing_errors"] = error_details

            await user_client.database.update("documents", document_id, update_data)

        except Exception as e:
            self.logger.error(f"Failed to update document status: {str(e)}")

    async def get_user_documents(
        self, user_id: str, limit: int = DocumentServiceConstants.DEFAULT_LIMIT
    ) -> List[DocumentDetails]:
        """Get user's documents - USER OPERATION with explicit user context"""
        try:
            user_client = await self.get_user_client()

            # RLS will automatically filter to user's documents
            # user_id parameter is for application logic validation
            current_user = self.get_current_user_id()
            if current_user != user_id:
                raise HTTPException(
                    status_code=DocumentServiceConstants.HTTP_FORBIDDEN,
                    detail="Access denied",
                )

            self.log_operation("list", "documents", user_id)

            # Use the read method with empty filters to get all user documents
            # RLS will automatically filter to user's documents
            result = await user_client.database.read(
                "documents", filters={}, limit=limit
            )
            documents: List[DocumentDetails] = []
            for rec in result:
                try:
                    documents.append(
                        DocumentDetails(
                            id=str(rec.get("id")),
                            user_id=str(rec.get("user_id")),
                            filename=rec.get("original_filename")
                            or rec.get("filename", "unknown"),
                            file_type=rec.get("file_type", "unknown"),
                            file_size=int(rec.get("file_size", 0)),
                            status=rec.get("processing_status")
                            or rec.get("status", "unknown"),
                            storage_path=rec.get("storage_path", ""),
                            created_at=rec.get("created_at"),
                            processing_results=rec.get("processing_results"),
                        )
                    )
                except Exception:
                    continue
            return documents

        except Exception as e:
            self.logger.error(f"Failed to get user documents: {str(e)}")
            raise

    async def get_system_stats(self) -> SystemStatsResponse:
        """Get system-wide document statistics - SYSTEM OPERATION"""
        try:
            # This is a legitimate system operation for admin dashboards
            system_client = await self.get_system_client()

            self.log_system_operation(
                "system_stats", "documents", None, self.get_current_user_id()
            )

            # These queries bypass RLS to get system-wide stats
            result = await system_client.database.execute_rpc(
                "get_document_statistics", {}
            )
            return SystemStatsResponse(data=result.get("data", {}))

        except Exception as e:
            self.logger.error(f"Failed to get system stats: {str(e)}")
            raise

    async def get_file_content(self, storage_path: str) -> bytes:
        """
        Get file content from storage - can be used for system operations.

        This method will use system client if no user authentication is available,
        making it suitable for background tasks like cleanup.

        Args:
            storage_path: Path to file in storage

        Returns:
            bytes: File content

        Raises:
            Exception: If file not found or access denied
        """
        try:
            # Try user client first if authenticated
            if self.is_user_authenticated():
                user_client = await self.get_user_client()
                self.log_operation("read", "document_content", storage_path)
            else:
                # Fall back to system client for background tasks
                user_client = await self.get_system_client()
                self.log_system_operation(
                    "read", "document_content", storage_path, None
                )

            file_content = await user_client.download_file(
                bucket=self.storage_bucket, path=storage_path
            )

            if not file_content:
                raise ValueError(f"File not found or empty: {storage_path}")

            return file_content

        except Exception as e:
            self.logger.error(
                f"Failed to get file content for {storage_path}: {str(e)}"
            )
            raise

    # Health check implementation
    async def health_check(self) -> ServiceHealthStatus:
        """Health check for DocumentService"""
        base_health = await super().health_check()

        health_status = {
            **base_health,
            "dependencies": {},
            "capabilities": [
                "document_upload",
                "text_extraction",
                "user_context_aware",
                "rls_enforced",
            ],
        }

        # Check user client
        try:
            if self.is_user_authenticated():
                user_client = await self.get_user_client()
                test_result = await user_client.execute_rpc("health_check", {})
                health_status["dependencies"]["user_client"] = {
                    "status": "healthy",
                    "connection": "ok",
                }
            else:
                health_status["dependencies"]["user_client"] = {
                    "status": "no_auth_context",
                }
        except Exception as e:
            health_status["dependencies"]["user_client"] = {
                "status": "error",
                "error": str(e),
            }

        # Check system client
        try:
            system_client = await self.get_system_client()
            test_result = await system_client.execute_rpc("health_check", {})
            health_status["dependencies"]["system_client"] = {
                "status": "healthy",
                "connection": "ok",
            }
        except Exception as e:
            health_status["dependencies"]["system_client"] = {
                "status": "error",
                "error": str(e),
            }

        # Check other dependencies...
        return ServiceHealthStatus(
            service=health_status.get("service", self.__class__.__name__),
            status=str(health_status.get("status", "healthy")),
            authenticated=bool(health_status.get("authenticated", False)),
            dependencies=health_status.get("dependencies", {}),
            capabilities=health_status.get("capabilities", []),
        )

    # Utility methods remain largely the same but now operate in proper context
    async def _validate_uploaded_file(self, file: UploadFile) -> FileValidationResult:
        """Enhanced file validation with security checks"""
        try:
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)  # Reset file position

            # Size validation
            if (
                file_size
                > self.max_file_size_mb * DocumentServiceConstants.BYTES_PER_MB
            ):
                return FileValidationResult(
                    valid=False,
                    error=f"File too large. Maximum size: {self.max_file_size_mb}MB",
                )

            # Type validation
            file_type = self._detect_file_type(
                file.filename,
                file_content[: DocumentServiceConstants.FILE_HEADER_READ_SIZE],
            )
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
                return FileValidationResult(
                    valid=False,
                    error=f"Unsupported file type: {file_type}. Supported: {', '.join(supported_types)}",
                )

            # Security validation
            if self._has_security_concerns(
                file.filename,
                file_content[: DocumentServiceConstants.FILE_HEADER_READ_SIZE],
            ):
                return FileValidationResult(
                    valid=False, error="File failed security validation"
                )

            return FileValidationResult(
                valid=True,
                file_info=UploadedFileInfo(
                    original_filename=file.filename,
                    file_type=file_type,
                    file_size=file_size,
                    content_hash=self._calculate_hash(file_content),
                    mime_type=mimetypes.guess_type(file.filename)[0]
                    or "application/octet-stream",
                ),
            )
        except Exception as e:
            return FileValidationResult(
                valid=False, error=f"File validation error: {str(e)}"
            )

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
        if file_header.startswith(DocumentServiceConstants.PDF_MAGIC_BYTES):
            return "pdf"
        elif file_header.startswith(DocumentServiceConstants.PNG_MAGIC_BYTES):
            return "png"
        elif file_header.startswith(DocumentServiceConstants.JPEG_MAGIC_BYTES):
            return "jpg"
        elif file_header.startswith(
            DocumentServiceConstants.TIFF_MAGIC_BYTES_1
        ) or file_header.startswith(DocumentServiceConstants.TIFF_MAGIC_BYTES_2):
            return "tiff"
        elif file_header.startswith(DocumentServiceConstants.BMP_MAGIC_BYTES):
            return "bmp"
        elif (
            file_header.startswith(DocumentServiceConstants.ZIP_MAGIC_BYTES)
            and b"word/"
            in file_header[: DocumentServiceConstants.DOCX_HEADER_SEARCH_SIZE]
        ):
            return "docx"

        return "unknown"

    def _has_security_concerns(self, filename: str, file_header: bytes) -> bool:
        """Security validation to prevent malicious files"""
        # Check for suspicious extensions
        suspicious_extensions = [".exe", ".bat", ".cmd", ".scr", ".vbs", ".js", ".jar"]
        if any(filename.lower().endswith(ext) for ext in suspicious_extensions):
            return True

        # Check for executable headers
        if any(
            file_header.startswith(header)
            for header in DocumentServiceConstants.EXECUTABLE_HEADERS
        ):
            return True

        return False

    def _calculate_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        import hashlib
        return hashlib.sha256(file_content).hexdigest()

    def _create_success_response(
        self,
        document_id: str,
        processing_time: float,
        text_result: Dict[str, Any] = None,
        page_result: Dict[str, Any] = None,
        entity_result: Dict[str, Any] = None,
        diagram_result: Dict[str, Any] = None,
        analysis_result: Dict[str, Any] = None,
        semantic_result: Optional[Dict[str, Any]] = None,
    ) -> TextExtractionResult:
        """Create comprehensive success response"""

        # Provide default values for optional results
        text_result = text_result or {}
        page_result = page_result or {}
        entity_result = entity_result or {}
        diagram_result = diagram_result or {}
        analysis_result = analysis_result or {}

        return {
            "success": True,
            "document_id": document_id,
            "processing_time": processing_time,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "text_extraction": {
                "total_pages": text_result.get(
                    "total_pages", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "total_word_count": text_result.get(
                    "total_word_count", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "extraction_methods": text_result.get("extraction_methods", []),
                "overall_confidence": text_result.get(
                    "overall_confidence", DocumentServiceConstants.DEFAULT_CONFIDENCE
                ),
            },
            "content_analysis": {
                "pages_analyzed": len(page_result.get("pages", [])),
                "entities_extracted": entity_result.get(
                    "total_entities", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "diagrams_detected": diagram_result.get(
                    "total_diagrams", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "document_classification": analysis_result.get("classification", {}),
            },
        }

    def _create_error_response(
        self, error_message: str, processing_start: datetime
    ) -> TextExtractionResult:
        """Create standardized error response"""
        processing_time = (
            datetime.now(timezone.utc) - processing_start
        ).total_seconds()
        return {
            "success": False,
            "error": error_message,
            "processing_time": processing_time,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "recovery_suggestions": [
                "Verify file format is supported (PDF, DOCX, PNG, JPG, TIFF, BMP)",
                "Check file size is under the limit",
                "Ensure file is not corrupted or password protected",
                "Try uploading a different file",
                "Contact support if the problem persists",
            ],
        }


# Factory function for backward compatibility
def create_document_service(
    storage_path: str = "storage/documents",
    use_llm_document_processing: bool = True,
    max_file_size_mb: int = DocumentServiceConstants.DEFAULT_MAX_FILE_SIZE_MB,
) -> DocumentService:
    """Create unified document service with specified configuration"""

    return DocumentService(
        storage_base_path=storage_path,
        use_llm_document_processing=use_llm_document_processing,
        max_file_size_mb=max_file_size_mb,
    )
