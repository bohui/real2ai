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

import asyncio
import json
import warnings
import logging
import os
import re
import uuid
import io
from typing import Dict, Any, Optional, List, Tuple, BinaryIO
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal, InvalidOperation
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
    DocumentPage,
    DocumentEntity,
    DocumentDiagram,
    DocumentStatus as ProcessingStatus,
    ContentType,
    DiagramType,
    EntityType,
)
from app.prompts.schema.entity_extraction_schema import (
    AustralianState,
    ContractType,
)
from app.models.contract_state import ContractType as ContractStateType
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.services.base.user_aware_service import (
    UserAwareService,
    ServiceInitializationMixin,
)
from app.clients import get_gemini_client
from app.core.config import get_settings
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)
from app.schema.document import (
    FastUploadResult,
    UploadRecordResult,
    FileValidationResult,
    UploadedFileInfo,
    TextExtractionResult,
    PageExtraction,
    ProcessedDocumentSummary,
    ProcessingErrorResponse,
    DocumentDetails,
    SystemStatsResponse,
    ServiceHealthStatus,
    ContentAnalysis as ContentAnalysisSchema,
    QualityIndicators as QualityIndicatorsSchema,
    PageProcessingSummary,
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
                import re

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

    # @langsmith_trace(name="process_document")
    # async def process_document(
    #     self,
    #     file: UploadFile,
    #     user_id: str,
    #     contract_type: Optional[str] = None,
    #     australian_state: Optional[str] = None,
    # ) -> Dict[str, Any]:
    #     """
    #     DEPRECATED: Use `upload_document_fast` followed by
    #     `process_document_by_id`/`process_existing_document`.

    #     This legacy method combines upload + processing in one step and is kept
    #     for backward compatibility. It will be removed in a future release.
    #     """
    #     warnings.warn(
    #         (
    #             "DocumentService.process_document is deprecated. "
    #             "Use upload_document_fast + process_document_by_id instead."
    #         ),
    #         DeprecationWarning,
    #         stacklevel=2,
    #     )
    #     processing_start = datetime.now(timezone.utc)
    #     document_id = None
    #     temp_file_path = None

    #     try:
    #         # Log user operation
    #         self.log_operation("process_document", "document", None)

    #         # Step 1: Validate file
    #         validation_result = await self._validate_uploaded_file(file)
    #         if not validation_result["valid"]:
    #             return self._create_error_response(
    #                 f"File validation failed: {validation_result['error']}",
    #                 processing_start,
    #             )

    #         # Step 2: Upload to Supabase storage and create document record (USER OPERATION)
    #         upload_result = await self._upload_and_create_document_record(
    #             file,
    #             user_id,
    #             validation_result["file_info"],
    #             contract_type,
    #             australian_state,
    #         )

    #         if not upload_result["success"]:
    #             return self._create_error_response(
    #                 upload_result["error"], processing_start
    #             )

    #         document_id = upload_result["document_id"]
    #         storage_path = upload_result["storage_path"]

    #         # Log successful upload
    #         self.log_operation("create", "document", document_id)

    #         # Step 3: Update processing status and start timestamp (USER OPERATION)
    #         await self._update_document_status(
    #             document_id, ProcessingStatus.PROCESSING.value
    #         )

    #         # Set processing started timestamp
    #         await self._set_processing_started(document_id)

    #         # All subsequent operations are user-scoped and use RLS
    #         # Step 4: Extract text with comprehensive analysis
    #         text_extraction_result = (
    #             await self._extract_text_with_comprehensive_analysis(
    #                 document_id,
    #                 storage_path,
    #                 validation_result["file_info"]["file_type"],
    #             )
    #         )

    #         # Step 5: Persist analysis results to database with transaction-like behavior
    #         try:
    #             # Save page data to database
    #             content_hash = validation_result["file_info"]["content_hash"]
    #             await self._save_document_pages(
    #                 document_id, text_extraction_result, content_hash
    #             )

    #             # Aggregate diagram detection results from pages
    #             diagram_processing_result = self._aggregate_diagram_detections(
    #                 text_extraction_result
    #             )

    #             # Save diagram data to database
    #             await self._save_document_diagrams(document_id, text_extraction_result)

    #             # Update main document with aggregated metrics
    #             await self._update_document_metrics(
    #                 document_id, text_extraction_result, diagram_processing_result
    #             )

    #             # Create page processing summary
    #             page_processing_result = self._create_page_processing_summary(
    #                 text_extraction_result
    #             )

    #             # Mark document as completed
    #             await self._update_document_status(
    #                 document_id, ProcessingStatus.BASIC_COMPLETE.value
    #             )

    #             self.logger.info(
    #                 f"Successfully completed document processing for {document_id}"
    #             )

    #         except Exception as db_error:
    #             self.logger.error(
    #                 f"Database persistence failed for document {document_id}: {str(db_error)}"
    #             )

    #             # Attempt to rollback by marking document as failed with detailed error info
    #             try:
    #                 await self._update_document_status(
    #                     document_id,
    #                     ProcessingStatus.FAILED.value,
    #                     error_details={
    #                         "error": "Database persistence failed",
    #                         "details": str(db_error),
    #                         "stage": "database_persistence",
    #                         "timestamp": datetime.now(timezone.utc).isoformat(),
    #                         "text_extraction_successful": text_extraction_result.get(
    #                             "success", False
    #                         ),
    #                     },
    #                 )
    #             except Exception as rollback_error:
    #                 self.logger.error(
    #                     f"Rollback failed for document {document_id}: {str(rollback_error)}"
    #                 )

    #             # Re-raise the original database error
    #             raise db_error

    #         processing_time = (datetime.now(timezone.utc) - processing_start).total_seconds()

    #         return self._create_success_response(
    #             document_id,
    #             processing_time,
    #             text_extraction_result,
    #             page_processing_result,
    #             {},  # entity_extraction_result
    #             diagram_processing_result,
    #             {},  # document_analysis_result
    #             {},  # semantic_result
    #         )

    #     except Exception as e:
    #         processing_time = (datetime.now(timezone.utc) - processing_start).total_seconds()
    #         self.logger.error(f"Document processing failed: {str(e)}", exc_info=True)

    #         # Update document status if it exists (USER OPERATION)
    #         if document_id:
    #             await self._update_document_status(
    #                 document_id,
    #                 ProcessingStatus.FAILED.value,
    #                 error_details={
    #                     "error": str(e),
    #                     "timestamp": datetime.now(timezone.utc).isoformat(),
    #                     "processing_time": processing_time,
    #                 },
    #             )

    #         return self._create_error_response(
    #             f"Processing failed: {str(e)}", processing_start
    #         )

    #     finally:
    #         # Cleanup temporary files
    #         if temp_file_path and os.path.exists(temp_file_path):
    #             try:
    #                 os.unlink(temp_file_path)
    #             except Exception as cleanup_error:
    #                 self.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

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

    # Complete PDF processing implementation
    # async def _extract_pdf_text_comprehensive(
    #     self, file_content: bytes
    # ) -> TextExtractionResult:
    #     """Comprehensive PDF text extraction with pymupdf and OCR fallback"""

    #     try:
    #         pdf_document = pymupdf.open(stream=file_content, filetype="pdf")
    #         pages = []
    #         full_text = ""
    #         extraction_methods = []

    #         for page_num in range(len(pdf_document)):
    #             page = pdf_document.load_page(page_num)

    #             # Primary extraction with pymupdf
    #             text_content = page.get_text()
    #             extraction_method = "pymupdf"
    #             confidence = DocumentServiceConstants.OCR_CONFIDENCE_HIGH

    #             # OCR fallback for pages with minimal text
    #             if (
    #                 len(text_content.strip())
    #                 < DocumentServiceConstants.MIN_TEXT_LENGTH_FOR_OCR
    #             ):
    #                 ocr_text = await self._extract_text_with_ocr(
    #                     page,
    #                     page_num + 1,
    #                 )
    #                 if len(ocr_text.strip()) > len(text_content.strip()):
    #                     text_content = ocr_text
    #                     extraction_method = "tesseract_ocr"
    #                     confidence = DocumentServiceConstants.OCR_CONFIDENCE_LOW

    #             # Advanced OCR with Gemini for complex pages when LLM is enabled
    #             if (
    #                 self.use_llm_document_processing
    #                 and self.gemini_ocr_service
    #                 and confidence < DocumentServiceConstants.OCR_CONFIDENCE_THRESHOLD
    #             ):
    #                 try:
    #                     gemini_result = await self._extract_text_with_gemini(
    #                         page,
    #                         page_num + 1,
    #                     )
    #                     llm_insights = None
    #                     if gemini_result:
    #                         # Prefer Gemini text if it improves length
    #                         gemini_text = gemini_result.get("text") or ""
    #                         if len(gemini_text.strip()) > len(text_content.strip()):
    #                             text_content = gemini_text
    #                             extraction_method = "gemini_ocr"
    #                             confidence = (
    #                                 gemini_result.get("confidence")
    #                                 or DocumentServiceConstants.OCR_CONFIDENCE_MEDIUM
    #                             )

    #                         # Capture diagram hints/semantics for downstream analysis
    #                         llm_insights = {
    #                             "diagram_hint": gemini_result.get("diagram_hint"),
    #                             "semantic_analysis": gemini_result.get(
    #                                 "semantic_analysis"
    #                             ),
    #                         }
    #                 except Exception as gemini_error:
    #                     self.logger.warning(
    #                         f"Gemini OCR failed for page {page_num + 1}: {gemini_error}"
    #                     )

    #             # Analyze page content (use LLM insights if available)
    #             page_analysis = self._analyze_page_content(
    #                 text_content, page, llm_insights=locals().get("llm_insights")
    #             )

    #             page_data = {
    #                 "page_number": page_num + 1,
    #                 "text_content": text_content,
    #                 "text_length": len(text_content),
    #                 "word_count": (
    #                     len(text_content.split())
    #                     if text_content
    #                     else DocumentServiceConstants.DEFAULT_PAGE_NUMBER
    #                 ),
    #                 "extraction_method": extraction_method,
    #                 "confidence": confidence,
    #                 "content_analysis": page_analysis,
    #             }

    #             # Attach LLM-derived diagram hints for later persistence
    #             if locals().get("llm_insights") and locals()["llm_insights"].get(
    #                 "diagram_hint"
    #             ):
    #                 page_data["diagram_hint"] = locals()["llm_insights"]["diagram_hint"]

    #             pages.append(page_data)
    #             full_text += f"\n--- Page {page_num + 1} ---\n{text_content}"

    #             if extraction_method not in extraction_methods:
    #                 extraction_methods.append(extraction_method)

    #         pdf_document.close()

    #         return TextExtractionResult(
    #             success=True,
    #             full_text=full_text,
    #             pages=[
    #                 PageExtraction(
    #                     page_number=p.get("page_number", 0),
    #                     text_content=p.get("text_content", ""),
    #                     text_length=p.get("text_length", 0),
    #                     word_count=p.get("word_count", 0),
    #                     extraction_method=p.get("extraction_method"),
    #                     confidence=p.get("confidence", 0.0),
    #                     content_analysis=ContentAnalysisSchema(
    #                         **p.get("content_analysis", {})
    #                     ),
    #                 )
    #                 for p in pages
    #             ],
    #             total_pages=len(pages),
    #             extraction_methods=extraction_methods,
    #             total_word_count=sum(p["word_count"] for p in pages),
    #             overall_confidence=(
    #                 sum(p["confidence"] for p in pages) / len(pages)
    #                 if pages
    #                 else DocumentServiceConstants.DEFAULT_CONFIDENCE
    #             ),
    #         )

    #     except Exception as e:
    #         self.logger.error(f"PDF text extraction failed: {str(e)}")
    #         return TextExtractionResult(
    #             success=False, error=str(e), full_text="", pages=[]
    #         )

    # async def _extract_text_with_ocr(self, page: pymupdf.Page, page_number: int) -> str:
    #     """Extract text using Tesseract OCR with optimized settings"""
    #     try:
    #         # Render page as high-resolution image
    #         matrix = pymupdf.Matrix(
    #             DocumentServiceConstants.OCR_ZOOM_FACTOR,
    #             DocumentServiceConstants.OCR_ZOOM_FACTOR,
    #         )  # 2x zoom for better OCR
    #         pix = page.get_pixmap(matrix=matrix)

    #         # Convert to PIL Image
    #         img_data = pix.pil_tobytes(format="PNG")
    #         image = Image.open(io.BytesIO(img_data))

    #         # OCR with optimized configuration
    #         custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}"-'
    #         ocr_text = pytesseract.image_to_string(image, config=custom_config)

    #         return ocr_text.strip()

    #     except Exception as e:
    #         self.logger.warning(f"Tesseract OCR failed for page {page_number}: {e}")
    #         return ""

    # async def _extract_text_with_gemini(
    #     self, page: pymupdf.Page, page_number: int
    # ) -> Optional[Dict[str, Any]]:
    #     """Extract text and diagram insights using Gemini.

    #     Returns a dict with keys:
    #     - text: extracted OCR text (str)
    #     - confidence: float confidence estimate if available
    #     - diagram_hint: { is_diagram: bool, diagram_type: str | None }
    #     - semantic_analysis: optional structured semantics payload
    #     """
    #     if not (self.gemini_client and self.gemini_ocr_service):
    #         return None

    #     try:
    #         # Render page as image
    #         matrix = pymupdf.Matrix(
    #             DocumentServiceConstants.OCR_ZOOM_FACTOR,
    #             DocumentServiceConstants.OCR_ZOOM_FACTOR,
    #         )
    #         pix = page.get_pixmap(matrix=matrix)
    #         img_data = pix.pil_tobytes(format="PNG")

    #         filename = f"page_{page_number}.png"

    #         # Single combined lightweight call to OCR service
    #         combined = await self.gemini_ocr_service.extract_text_diagram_insight(
    #             file_content=img_data,
    #             file_type="png",
    #             filename=filename,
    #             analysis_focus="diagram_detection",
    #         )

    #         if not isinstance(combined, dict):
    #             return None

    #         return {
    #             "text": combined.get("text", ""),
    #             "confidence": combined.get("confidence", 0.0),
    #             "diagram_hint": combined.get("diagram_hint"),
    #         }

    #     except Exception as e:
    #         self.logger.warning(
    #             f"Gemini OCR/semantics failed for page {page_number}: {e}"
    #         )
    #         return None

    # def _analyze_page_content(
    #     self,
    #     text_content: str,
    #     page: pymupdf.Page,
    #     llm_insights: Optional[Dict[str, Any]] = None,
    # ) -> TextExtractionResult:
    #     """Analyze page content for classification and layout features"""

    #     analysis = {
    #         "content_types": [],
    #         "primary_type": ContentType.EMPTY.value,
    #         "layout_features": {
    #             "has_header": False,
    #             "has_footer": False,
    #             "has_signatures": False,
    #             "has_diagrams": False,
    #             "has_tables": False,
    #         },
    #         "quality_indicators": {
    #             "text_density": DocumentServiceConstants.DEFAULT_CONFIDENCE,
    #             "structure_score": DocumentServiceConstants.DEFAULT_CONFIDENCE,
    #             "readability_score": DocumentServiceConstants.DEFAULT_CONFIDENCE,
    #         },
    #     }

    #     if (
    #         not text_content
    #         or len(text_content.strip())
    #         < DocumentServiceConstants.MIN_TEXT_CONTENT_LENGTH
    #     ):
    #         return analysis

    #     text_lower = text_content.lower()

    #     # Content type detection
    #     if (
    #         text_content
    #         and len(text_content.strip())
    #         > DocumentServiceConstants.MIN_TEXT_CONTENT_FOR_ANALYSIS
    #     ):
    #         analysis["content_types"].append("text")

    #     # Table detection
    #     if self._detect_table_content(text_content):
    #         analysis["content_types"].append("table")
    #         analysis["layout_features"]["has_tables"] = True

    #     # Signature detection
    #     signature_patterns = [
    #         r"\b(signature|signed|date.*signed|initial)\b",
    #         r"_+\s*(signature|date)",
    #     ]
    #     if any(re.search(pattern, text_lower) for pattern in signature_patterns):
    #         analysis["content_types"].append("signature")
    #         analysis["layout_features"]["has_signatures"] = True

    #     # Diagram detection (prefer LLM hint if available)
    #     if self._detect_diagrams_on_page(page, text_content, llm_insights=llm_insights):
    #         analysis["content_types"].append("diagram")
    #         analysis["layout_features"]["has_diagrams"] = True

    #         # Carry through diagram type if provided by LLM semantics
    #         if llm_insights and llm_insights.get("diagram_hint"):
    #             diagram_type = llm_insights["diagram_hint"].get("diagram_type")
    #             if diagram_type:
    #                 analysis["diagram_type"] = diagram_type

    #     # Layout feature detection
    #     analysis["layout_features"]["has_header"] = self._detect_header_footer(
    #         text_content, "header"
    #     )
    #     analysis["layout_features"]["has_footer"] = self._detect_header_footer(
    #         text_content, "footer"
    #     )

    #     # Determine primary content type
    #     analysis["primary_type"] = self._determine_primary_content_type(
    #         analysis["content_types"]
    #     )

    #     # Calculate quality indicators
    #     analysis["quality_indicators"] = self._calculate_quality_indicators(
    #         text_content
    #     )

    #     return analysis

    # def _detect_table_content(self, text: str) -> bool:
    #     """Detect table-like content using multiple heuristics"""
    #     if not text:
    #         return False

    #     lines = text.split("\n")

    #     # Check for consistent column separators
    #     tab_lines = sum(
    #         DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
    #         for line in lines
    #         if "\t" in line or "  " in line
    #     )
    #     tab_ratio = (
    #         tab_lines / len(lines)
    #         if lines
    #         else DocumentServiceConstants.DEFAULT_PAGE_NUMBER
    #     )

    #     # Check for financial patterns (common in contract tables)
    #     currency_lines = sum(
    #         DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
    #         for line in lines
    #         if re.search(r"\$[\d,]+\.?\d*", line)
    #     )

    #     # Check for aligned data patterns
    #     aligned_patterns = sum(
    #         DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
    #         for line in lines
    #         if re.search(
    #             r"\s{" + str(DocumentServiceConstants.MIN_SPACES_FOR_ALIGNMENT) + r",}",
    #             line,
    #         )
    #     )
    #     alignment_ratio = (
    #         aligned_patterns / len(lines)
    #         if lines
    #         else DocumentServiceConstants.DEFAULT_PAGE_NUMBER
    #     )

    #     return (
    #         tab_ratio > DocumentServiceConstants.TAB_RATIO_FOR_TABLE
    #         or currency_lines > DocumentServiceConstants.CURRENCY_LINES_FOR_TABLE
    #         or alignment_ratio > DocumentServiceConstants.ALIGNMENT_RATIO_FOR_TABLE
    #     )

    # def _detect_diagrams_on_page(
    #     self,
    #     page: pymupdf.Page,
    #     text_content: str,
    #     llm_insights: Optional[Dict[str, Any]] = None,
    # ) -> bool:
    #     """Optimized diagram detection with text length preconditions"""

    #     # Prefer explicit LLM hint if available
    #     if llm_insights and llm_insights.get("diagram_hint"):
    #         hint = llm_insights["diagram_hint"]
    #         if isinstance(hint, dict) and hint.get("is_diagram"):
    #             return True

    #     # OPTIMIZATION 1: Text length precondition
    #     text_length = (
    #         len(text_content)
    #         if text_content
    #         else DocumentServiceConstants.DEFAULT_PAGE_NUMBER
    #     )

    #     # Log performance optimization decisions for monitoring
    #     if self.logger.isEnabledFor(logging.DEBUG):
    #         self.logger.debug(
    #             f"Diagram detection: text_length={text_length}, threshold={self.text_heavy_threshold}"
    #         )

    #     # Skip vector analysis for text-heavy pages (likely tables)
    #     if text_length > self.text_heavy_threshold:
    #         # For long text pages, only check images and keywords
    #         image_list = page.get_images()
    #         if image_list:
    #             return True

    #         # Enhanced keyword check for text-heavy pages
    #         if text_content:
    #             return self._has_diagram_keywords(text_content, strict_mode=True)
    #         return False

    #     # Method 1: Check for embedded images (always check)
    #     image_list = page.get_images()
    #     if image_list:
    #         return True

    #     # OPTIMIZATION 2: Smart vector analysis (only for low-text pages)
    #     if text_length < self.low_text_threshold:
    #         drawings = page.get_drawings()
    #         if drawings:
    #             # Filter out table-like vector patterns
    #             if self._is_likely_diagram_vectors(drawings, text_content):
    #                 return True
    #     elif (
    #         text_length <= self.text_heavy_threshold
    #     ):  # Medium text pages - limited vector check
    #         drawings = page.get_drawings()
    #         if drawings and len(drawings) <= self.max_vector_count:
    #             if self._is_likely_diagram_vectors(drawings, text_content):
    #                 return True

    #     # Method 3: Enhanced keyword detection
    #     if text_content:
    #         return self._has_diagram_keywords(text_content, strict_mode=True)

    #     return False

    # def _is_likely_diagram_vectors(self, drawings: list, text_content: str) -> bool:
    #     """Distinguish diagram vectors from table vectors"""
    #     if not drawings:
    #         return False

    #     # High vector count suggests tables, not diagrams
    #     if len(drawings) > self.table_vector_threshold:
    #         return False

    #     # Check for drawing complexity patterns (sample first 20 for performance)
    #     sample_size = min(DocumentServiceConstants.VECTOR_SAMPLE_SIZE, len(drawings))
    #     complex_shapes = DocumentServiceConstants.DEFAULT_PAGE_NUMBER

    #     for drawing in drawings[:sample_size]:
    #         # Check for complex drawing items (curves, paths, etc.)
    #         items = drawing.get("items", []) if hasattr(drawing, "get") else []
    #         if (
    #             len(items) > DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
    #         ):  # Complex shape indicator
    #             complex_shapes += DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS

    #     # If 30%+ of sampled drawings are complex, likely diagrams
    #     complexity_ratio = (
    #         complex_shapes / sample_size
    #         if sample_size > DocumentServiceConstants.DEFAULT_PAGE_NUMBER
    #         else DocumentServiceConstants.DEFAULT_CONFIDENCE
    #     )

    #     # Additional heuristic: check for geometric patterns vs table patterns
    #     if (
    #         text_content
    #         and complexity_ratio > DocumentServiceConstants.DEFAULT_CONFIDENCE
    #     ):
    #         # If we have both complex vectors and minimal text, likely a diagram
    #         text_to_vector_ratio = len(text_content) / len(drawings)
    #         if (
    #             text_to_vector_ratio
    #             < DocumentServiceConstants.TEXT_TO_VECTOR_RATIO_THRESHOLD
    #         ):  # Low text-to-vector ratio
    #             return True

    #     return complexity_ratio > self.complexity_ratio_threshold

    def _has_diagram_keywords(
        self, text_content: str, strict_mode: bool = False
    ) -> bool:
        """Enhanced keyword detection with configurable strictness"""
        if not text_content:
            return False

        text_lower = text_content.lower()

        if strict_mode:
            # Stricter keywords for text-heavy pages to reduce false positives
            strict_keywords = [
                "site plan",
                "floor plan",
                "survey plan",
                "title plan",
                "sewer diagram",
                "sewerage diagram",
                "utilities diagram",
                "service diagram",
                "flood map",
                "zoning map",
                "cadastral",
                "boundary survey",
                "drainage plan",
                "contour map",
            ]
            return any(keyword in text_lower for keyword in strict_keywords)

        # Standard keyword list for regular detection
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
            "sewerage diagram",
            "service diagram",
            "utilities diagram",
            "flood map",
            "bushfire",
            "drainage",
            "contour",
            "easement",
            "zoning map",
            "cadastral",
        ]
        return any(keyword in text_lower for keyword in diagram_keywords)

    def _detect_header_footer(self, text: str, position: str) -> bool:
        """Detect header or footer content"""
        if not text:
            return False

        lines = text.split("\n")
        target_lines = (
            lines[: DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS]
            if position == "header"
            else lines[-DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS :]
        )

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
        elif (
            "diagram" in content_types
            and len(content_types) == DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
        ):
            return ContentType.DIAGRAM.value
        elif "table" in content_types and "text" not in content_types:
            return ContentType.TABLE.value
        elif "signature" in content_types:
            return ContentType.SIGNATURE.value
        elif len(content_types) > DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS:
            return ContentType.MIXED.value
        else:
            return ContentType.TEXT.value

    def _calculate_quality_indicators(
        self, text_content: str
    ) -> QualityIndicatorsSchema:
        """Calculate various quality metrics for text content"""

        indicators = {
            "text_density": DocumentServiceConstants.DEFAULT_CONFIDENCE,
            "structure_score": DocumentServiceConstants.DEFAULT_CONFIDENCE,
            "readability_score": DocumentServiceConstants.DEFAULT_CONFIDENCE,
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
            # Calculate normalized density and clamp to [0.0, 1.0]
            normalized_density = (
                avg_line_length / DocumentServiceConstants.MAX_LINE_LENGTH_NORMALIZATION
            )
            indicators["text_density"] = min(1.0, max(0.0, normalized_density))

        # Structure score (based on punctuation and formatting)
        sentences = re.split(r"[.!?]+", text_content)
        if len(sentences) > DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS:
            avg_sentence_length = len(text_content) / len(sentences)
            # Calculate normalized structure score and clamp to [0.0, 1.0]
            normalized_structure = (
                avg_sentence_length
                / DocumentServiceConstants.MAX_SENTENCE_LENGTH_NORMALIZATION
            )
            indicators["structure_score"] = min(1.0, max(0.0, normalized_structure))

        # Basic readability (word length distribution)
        words = text_content.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            # Calculate readability based on deviation from optimal word length
            # Start with max score (1.0) and subtract penalty for deviation
            word_length_penalty = (
                abs(avg_word_length - DocumentServiceConstants.OPTIMAL_WORD_LENGTH)
                / DocumentServiceConstants.WORD_LENGTH_NORMALIZATION_FACTOR
            )
            readability_raw = 1.0 - word_length_penalty
            # Clamp to [0.0, 1.0] range
            indicators["readability_score"] = min(1.0, max(0.0, readability_raw))

        return QualityIndicatorsSchema(**indicators)

    def _aggregate_diagram_detections(
        self, text_extraction_result: TextExtractionResult
    ) -> Dict[str, Any]:
        """Aggregate diagram detection results from page-level analysis"""
        if not text_extraction_result.success or not text_extraction_result.pages:
            return {
                "total_diagrams": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                "diagram_pages": [],
                "diagram_types": {},
                "detection_summary": {
                    "embedded_images": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                    "vector_graphics": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                    "text_indicators": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                    "mixed_content": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                },
            }

        diagram_pages = []
        diagram_types = {}
        detection_summary = {
            "embedded_images": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
            "vector_graphics": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
            "text_indicators": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
            "mixed_content": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
        }

        for page in text_extraction_result.pages:
            page_analysis = page.content_analysis
            layout_features = page_analysis.layout_features

            if layout_features.has_diagrams:
                page_num = page.page_number
                diagram_pages.append(
                    {
                        "page_number": page_num,
                        "content_types": page_analysis.content_types,
                        "primary_type": page_analysis.primary_type,
                        "confidence": page.confidence,
                    }
                )

                # Count diagram types based on content analysis
                primary_type = page_analysis.primary_type
                if primary_type == "diagram":
                    diagram_types["diagram"] = (
                        diagram_types.get(
                            "diagram", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                        )
                        + DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
                    )
                elif primary_type == "mixed" and "diagram" in page_analysis.get(
                    "content_types", []
                ):
                    diagram_types["mixed"] = (
                        diagram_types.get(
                            "mixed", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                        )
                        + DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
                    )
                    detection_summary[
                        "mixed_content"
                    ] += DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
                else:
                    diagram_types["other"] = (
                        diagram_types.get(
                            "other", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                        )
                        + DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
                    )

                # Increment detection summary (this is a simplified heuristic)
                # In a full implementation, we'd track detection method per page
                detection_summary[
                    "text_indicators"
                ] += DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS

        total_diagrams = len(diagram_pages)

        return {
            "total_diagrams": total_diagrams,
            "diagram_pages": diagram_pages,
            "diagram_types": diagram_types,
            "detection_summary": detection_summary,
            "processing_notes": [
                f"Detected diagrams on {total_diagrams} pages",
                f"Primary detection method: text-based indicators",
                (
                    f"Diagram types found: {list(diagram_types.keys())}"
                    if diagram_types
                    else "No specific diagram types classified"
                ),
            ],
        }

    def _create_page_processing_summary(
        self, text_extraction_result: TextExtractionResult
    ) -> Dict[str, Any]:
        """Create summary of page processing results"""
        if not text_extraction_result.success or not text_extraction_result.pages:
            return {
                "pages": [],
                "total_pages_processed": DocumentServiceConstants.DEFAULT_PAGE_NUMBER,
                "content_type_distribution": {},
                "average_confidence": DocumentServiceConstants.DEFAULT_CONFIDENCE,
            }

        pages = text_extraction_result.pages
        content_type_distribution = {}
        total_confidence = DocumentServiceConstants.DEFAULT_CONFIDENCE

        for page in pages:
            page_analysis = page.content_analysis
            primary_type = page_analysis.primary_type

            content_type_distribution[primary_type] = (
                content_type_distribution.get(
                    primary_type, DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                )
                + DocumentServiceConstants.MIN_COMPLEX_SHAPE_ITEMS
            )
            total_confidence += page.confidence

        average_confidence = (
            total_confidence / len(pages)
            if pages
            else DocumentServiceConstants.DEFAULT_CONFIDENCE
        )

        return {
            "pages": pages,
            "total_pages_processed": len(pages),
            "content_type_distribution": content_type_distribution,
            "average_confidence": average_confidence,
            "processing_summary": {
                "text_pages": content_type_distribution.get(
                    "text", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "diagram_pages": content_type_distribution.get(
                    "diagram", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "mixed_pages": content_type_distribution.get(
                    "mixed", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "table_pages": content_type_distribution.get(
                    "table", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "signature_pages": content_type_distribution.get(
                    "signature", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
                "empty_pages": content_type_distribution.get(
                    "empty", DocumentServiceConstants.DEFAULT_PAGE_NUMBER
                ),
            },
        }

    async def _save_document_pages(
        self,
        document_id: str,
        text_extraction_result: TextExtractionResult,
        content_hash: str = None,
    ) -> None:
        """Save page analysis data to document_pages table - USER OPERATION"""
        try:
            if not text_extraction_result.success or not text_extraction_result.pages:
                self.logger.info(f"No pages to save for document {document_id}")
                return

            user_client = await self.get_user_client()
            pages = text_extraction_result.pages

            for page in pages:
                page_analysis = page.content_analysis
                layout_features = page_analysis.layout_features
                quality_indicators = page_analysis.quality_indicators

                page_data = {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "content_hash": content_hash,
                    "page_number": page.page_number,
                    # Content analysis
                    "text_content": page.text_content,
                    "text_length": page.text_length,
                    "word_count": page.word_count,
                    # Content classification
                    "content_types": page_analysis.content_types,
                    "primary_content_type": page_analysis.primary_type,
                    # Quality metrics
                    "extraction_confidence": page.confidence,
                    "content_quality_score": quality_indicators.structure_score,
                    # Layout analysis
                    "has_header": layout_features.has_header,
                    "has_footer": layout_features.has_footer,
                    "has_signatures": layout_features.has_signatures,
                    "has_diagrams": layout_features.has_diagrams,
                    "has_tables": layout_features.has_tables,
                    # Processing metadata
                    "processed_at": datetime.now(timezone.utc),
                    "processing_method": page.extraction_method or "unknown",
                }

                # Save page record
                await user_client.database.create("document_pages", page_data)

            self.logger.info(f"Saved {len(pages)} pages for document {document_id}")
            self.log_operation("create", "document_pages", document_id)

        except Exception as e:
            self.logger.error(f"Failed to save document pages: {str(e)}")
            raise

    async def _save_document_diagrams(
        self, document_id: str, text_extraction_result: TextExtractionResult
    ) -> None:
        """Save diagram detection data to document_diagrams table - USER OPERATION"""
        try:
            if not text_extraction_result.success or not text_extraction_result.pages:
                return

            user_client = await self.get_user_client()
            diagrams_saved = 0

            for page in text_extraction_result.pages:
                page_analysis = page.content_analysis
                layout_features = page_analysis.layout_features

                # Only save if diagrams were detected on this page
                if layout_features.has_diagrams:
                    # Use diagram type from content analysis
                    resolved_type = page_analysis.diagram_type or "unknown"

                    diagram_data = {
                        # Intentionally omit "id" to let DB assign or keep existing on conflict
                        "document_id": document_id,
                        "page_number": page.page_number,
                        # Classification from content analysis
                        "diagram_type": resolved_type,
                        "classification_confidence": page.confidence,
                        # Analysis status
                        "basic_analysis_completed": True,
                        "detailed_analysis_completed": False,
                        # Basic analysis results
                        "basic_analysis": {
                            "content_types": page_analysis.get("content_types", []),
                            "primary_type": page_analysis.get("primary_type"),
                            "detection_method": "text_analysis",
                            "quality_indicators": page_analysis.get(
                                "quality_indicators", {}
                            ),
                        },
                        # Quality metrics
                        "image_quality_score": page_analysis.get(
                            "quality_indicators", {}
                        ).get("structure_score", 0.0),
                        "clarity_score": page_analysis.get(
                            "quality_indicators", {}
                        ).get("readability_score", 0.0),
                        # Metadata
                        "detected_at": datetime.now(timezone.utc),
                        "basic_analysis_at": datetime.now(timezone.utc),
                    }

                    # Upsert to avoid duplicates on retry: requires unique index on (document_id, page_number, diagram_type)
                    await user_client.database.upsert(
                        "document_diagrams",
                        diagram_data,
                        conflict_columns=["document_id", "page_number", "diagram_type"],
                    )
                    diagrams_saved += 1

            if diagrams_saved > 0:
                self.logger.info(
                    f"Saved {diagrams_saved} diagrams for document {document_id}"
                )
                self.log_operation("create", "document_diagrams", document_id)

        except Exception as e:
            self.logger.error(f"Failed to save document diagrams: {str(e)}")
            raise

    async def _update_document_metrics(
        self,
        document_id: str,
        text_extraction_result: TextExtractionResult,
        diagram_processing_result: Dict[str, Any],
    ) -> None:
        """Update main document with aggregated metrics - USER OPERATION"""
        try:
            user_client = await self.get_user_client()

            # Calculate aggregated metrics
            pages = text_extraction_result.pages
            total_pages = len(pages)
            total_word_count = sum(p.word_count for p in pages)
            total_text_length = sum(p.text_length for p in pages)

            # Calculate average confidence
            confidences = [p.confidence for p in pages if p.confidence > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Diagram information
            total_diagrams = diagram_processing_result.get("total_diagrams", 0)
            has_diagrams = total_diagrams > 0

            # Determine text extraction method
            extraction_methods = text_extraction_result.extraction_methods or []
            primary_method = extraction_methods[0] if extraction_methods else "unknown"

            update_data = {
                "full_text": text_extraction_result.full_text,
                "total_pages": total_pages,
                "total_word_count": total_word_count,
                "total_text_length": total_text_length,
                "has_diagrams": has_diagrams,
                "diagram_count": total_diagrams,
                "extraction_confidence": avg_confidence,
                "overall_quality_score": avg_confidence,  # Use confidence as quality proxy for now
                "text_extraction_method": primary_method,
                "processing_completed_at": datetime.now(timezone.utc),
                "processing_results": {
                    "text_extraction": text_extraction_result,
                    "diagram_processing": diagram_processing_result,
                },
            }

            await user_client.database.update("documents", document_id, update_data)
            self.logger.info(f"Updated document {document_id} with processing metrics")
            self.log_operation("update", "document_metrics", document_id)

        except Exception as e:
            self.logger.error(f"Failed to update document metrics: {str(e)}")
            raise

    # Placeholder implementations
    async def _extract_docx_text_comprehensive(
        self, file_content: bytes
    ) -> TextExtractionResult:
        """Extract text from DOCX files - placeholder for future implementation"""
        return TextExtractionResult(
            success=False, error="DOCX extraction not yet implemented"
        )

    async def _extract_image_text_comprehensive(
        self, file_content: bytes
    ) -> TextExtractionResult:
        """Extract text from image files - placeholder for future implementation"""
        return TextExtractionResult(
            success=False, error="Image text extraction not yet implemented"
        )


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
