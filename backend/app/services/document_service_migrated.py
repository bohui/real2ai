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
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.base.user_aware_service import UserAwareService, ServiceInitializationMixin
from app.clients import get_gemini_client
from app.core.config import get_settings
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


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
        enable_advanced_ocr: bool = True,
        enable_gemini_ocr: bool = True,
        max_file_size_mb: int = 50,
        user_client=None,  # For dependency injection
    ):
        super().__init__(user_client=user_client)
        self.settings = get_settings()
        self.storage_base_path = Path(storage_base_path)
        self.enable_advanced_ocr = enable_advanced_ocr
        self.enable_gemini_ocr = enable_gemini_ocr
        self.max_file_size_mb = max_file_size_mb

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
            self.logger.info(f"Gemini client initialized: {self.gemini_client is not None}")

            # Initialize OCR services
            if self.enable_gemini_ocr:
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
            raise HTTPException(status_code=503, detail="Required services unavailable")
        except Exception as e:
            self.logger.error(f"Failed to initialize document service: {str(e)}")
            self.enable_gemini_ocr = False  # Fallback mode

    async def _ensure_bucket_exists(self):
        """Ensure Supabase storage bucket exists - SYSTEM OPERATION"""
        try:
            # This is a legitimate system operation - bucket creation requires admin privileges
            system_client = await self.get_system_client()
            result = await system_client.execute_rpc(
                "ensure_bucket_exists", {"bucket_name": self.storage_bucket}
            )

            # Parse the JSON string result
            result_data = json.loads(result)

            if result_data.get("created"):
                self.logger.info(f"Created storage bucket: {self.storage_bucket}")
                
            self.log_operation("system_bucket_ensure", "storage_bucket", self.storage_bucket)

        except Exception as e:
            self.logger.warning(f"Could not verify/create bucket: {str(e)}")

    @langsmith_trace(name="process_document")
    async def process_document(
        self,
        file: UploadFile,
        user_id: str,
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main document processing pipeline - USER OPERATION
        
        This is a user-scoped operation that processes documents with proper RLS enforcement.
        """
        processing_start = datetime.now(UTC)
        document_id = None
        temp_file_path = None

        try:
            # Log user operation
            self.log_operation("process_document", "document", None)
            
            # Step 1: Validate file
            validation_result = await self._validate_uploaded_file(file)
            if not validation_result["valid"]:
                return self._create_error_response(
                    f"File validation failed: {validation_result['error']}",
                    processing_start,
                )

            # Step 2: Upload to Supabase storage and create document record (USER OPERATION)
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
            
            # Log successful upload
            self.log_operation("create", "document", document_id)

            # Step 3: Update processing status (USER OPERATION)
            await self._update_document_status(
                document_id, ProcessingStatus.PROCESSING.value
            )

            # All subsequent operations are user-scoped and use RLS
            # Step 4: Extract text with comprehensive analysis
            text_extraction_result = (
                await self._extract_text_with_comprehensive_analysis(
                    document_id,
                    storage_path,
                    validation_result["file_info"]["file_type"],
                )
            )

            # Continue with other processing steps...
            # All operations automatically use user context

            processing_time = (datetime.now(UTC) - processing_start).total_seconds()

            return self._create_success_response(
                document_id,
                processing_time,
                text_extraction_result,
                {},  # page_processing_result
                {},  # entity_extraction_result  
                {},  # diagram_processing_result
                {},  # document_analysis_result
                {},  # semantic_result
            )

        except Exception as e:
            processing_time = (datetime.now(UTC) - processing_start).total_seconds()
            self.logger.error(f"Document processing failed: {str(e)}", exc_info=True)

            # Update document status if it exists (USER OPERATION)
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
                    self.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

    async def _upload_and_create_document_record(
        self,
        file: UploadFile,
        user_id: str,
        file_info: Dict[str, Any],
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Supabase storage and create document record - USER OPERATION"""
        try:
            document_id = str(uuid.uuid4())
            file_extension = Path(file_info["original_filename"]).suffix.lower()
            storage_filename = f"{document_id}{file_extension}"
            storage_path = f"documents/{user_id}/{storage_filename}"

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
                return {"success": False, "error": "Failed to upload file to storage"}

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

            insert_result = await user_client.insert(
                "documents", document_data
            )

            if not insert_result.get("success"):
                return {"success": False, "error": "Failed to create document record"}

            self.logger.info(f"Created document record: {document_id}")
            return {
                "success": True,
                "document_id": document_id,
                "storage_path": storage_path,
            }

        except Exception as e:
            self.logger.error(f"Upload and record creation failed: {str(e)}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    async def _extract_text_with_comprehensive_analysis(
        self, document_id: str, storage_path: str, file_type: str
    ) -> Dict[str, Any]:
        """Extract text using multiple methods - USER OPERATION"""

        try:
            # Download file from storage (user context)
            user_client = await self.get_user_client()
            file_content = await user_client.download_file(
                bucket=self.storage_bucket, path=storage_path
            )

            if not file_content:
                raise ValueError("Failed to download file from storage")

            # Log the access
            self.log_operation("read", "document_content", storage_path)

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
            self.logger.error(f"Text extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "pages": [],
                "extraction_method": "failed",
                "confidence": 0.0,
            }

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

            await user_client.update(
                "documents", {"id": document_id}, update_data
            )

        except Exception as e:
            self.logger.error(f"Failed to update document status: {str(e)}")

    async def get_user_documents(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's documents - USER OPERATION with explicit user context"""
        try:
            user_client = await self.get_user_client()
            
            # RLS will automatically filter to user's documents
            # user_id parameter is for application logic validation
            current_user = self.get_current_user_id()
            if current_user != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            self.log_operation("list", "documents", user_id)
            
            result = await user_client.database.select(
                "documents",
                columns=["id", "original_filename", "file_type", "created_at", "processing_status"],
                limit=limit,
                order_by="created_at DESC"
            )
            
            return result.get("data", [])
            
        except Exception as e:
            self.logger.error(f"Failed to get user documents: {str(e)}")
            raise

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide document statistics - SYSTEM OPERATION"""
        try:
            # This is a legitimate system operation for admin dashboards
            system_client = await self.get_system_client()
            
            self.log_system_operation(
                "system_stats", 
                "documents", 
                None, 
                self.get_current_user_id()
            )
            
            # These queries bypass RLS to get system-wide stats
            result = await system_client.database.execute_rpc(
                "get_document_statistics",
                {}
            )
            
            return result.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {str(e)}")
            raise

    # Health check implementation
    async def health_check(self) -> Dict[str, Any]:
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
        return health_status

    # Utility methods remain largely the same but now operate in proper context
    async def _validate_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """Enhanced file validation with security checks"""
        # Implementation remains the same - no database access
        pass

    def _create_success_response(self, *args) -> Dict[str, Any]:
        """Create comprehensive success response"""
        # Implementation remains the same - no database access
        pass

    def _create_error_response(self, error_message: str, processing_start: datetime) -> Dict[str, Any]:
        """Create standardized error response"""
        # Implementation remains the same - no database access  
        pass

    # Additional methods would follow the same pattern:
    # - User operations use self.get_user_client()
    # - System operations use self.get_system_client() 
    # - Clear logging of operation types
    # - Proper error handling and context management