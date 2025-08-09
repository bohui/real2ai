"""Document management router."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import Optional, Dict, Any, List
import logging

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.core.config import get_settings
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.schema.enums import ContractType, AustralianState
from app.services.document_service import DocumentService
from app.services.websocket_singleton import websocket_manager
from app.services.websocket_service import WebSocketEvents
from app.schema.document import (
    DocumentUploadResponse,
    ReportGenerationRequest,
    ReportResponse,
)
from app.schema.ocr import (
    OCRProcessingRequest,
    OCRProcessingResponse,
    BatchOCRRequest,
    BatchOCRResponse,
    OCRStatusResponse,
    OCRCapabilitiesResponse,
    EnhancedOCRCapabilities,
    OCRQueueStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# Initialize services (these would typically be dependency injected)
settings = get_settings()


# Dependency function to get initialized document service
async def get_document_service(
    user: User = Depends(get_current_user),
) -> DocumentService:
    """Get initialized document service with user-aware architecture"""
    logger.info(f"Creating DocumentService instance for user {user.id}...")

    # Get user-authenticated client for dependency injection
    user_client = await AuthContext.get_authenticated_client(require_auth=True)

    # Initialize service with user client injection
    service = DocumentService(user_client=user_client, use_llm_document_processing=True)
    await service.initialize()
    logger.info("DocumentService initialized with user-aware authentication")
    return service


@router.get("/test-document-service")
async def test_document_service(
    user: User = Depends(get_current_user),
):
    """Test endpoint to check DocumentService initialization with auth context"""
    try:
        # Create a document service instance with user client injection
        user_client = await AuthContext.get_authenticated_client(require_auth=True)
        service = DocumentService(
            user_client=user_client, use_llm_document_processing=True
        )
        await service.initialize()

        # Test auth context
        from app.core.auth_context import AuthContext

        return {
            "status": "success",
            "message": "DocumentService initialized successfully",
            "auth_context": {
                "is_authenticated": AuthContext.is_authenticated(),
                "user_id": AuthContext.get_user_id() or user.id,
            },
            "service_initialized": True,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    contract_type: ContractType = ContractType.PURCHASE_AGREEMENT,
    australian_state: AustralianState = AustralianState.NSW,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Fast document upload - stores file and creates record only.

    This endpoint now focuses solely on file storage and basic validation.
    For document processing and analysis, use /api/contracts/analyze endpoint.
    """

    context = create_error_context(
        user_id=str(user.id),
        operation="upload_document",
        metadata={
            "filename": file.filename,
            "contract_type": contract_type.value,
            "australian_state": australian_state.value,
        },
    )

    try:
        # Log upload attempt
        logger.info(
            f"Fast upload attempt: filename={file.filename}, size={file.size}, content_type={file.content_type}"
        )

        # Basic file validation
        if file.size == 0:
            logger.warning(f"Empty file upload attempted: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded. Please select a valid document with content.",
            )

        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size / 1024 / 1024}MB",
            )

        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in settings.allowed_file_types_list:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_file_types_list)}",
            )

        # Fast upload - just store file and create record
        logger.info("Starting fast document upload...")
        try:
            upload_result = await document_service.upload_document_fast(
                file=file,
                user_id=str(user.id),
                contract_type=contract_type.value if contract_type else None,
                australian_state=australian_state.value if australian_state else None,
            )
            logger.info(f"Fast upload result: {upload_result}")
        except Exception as upload_error:
            logger.error(f"Fast upload failed: {str(upload_error)}", exc_info=True)
            raise

        # Check if upload was successful
        if not upload_result.success:
            logger.error(
                f"Document upload failed: {upload_result.error or 'Unknown error'}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Document upload failed: {upload_result.error or 'Unknown error'}",
            )

        logger.info("Fast document upload completed successfully")

        response = DocumentUploadResponse(
            document_id=upload_result.document_id,
            filename=file.filename,
            file_size=file.size,
            upload_status="uploaded",  # Status is now "uploaded" not "processed"
            processing_time=upload_result.processing_time,
        )
        logger.info(
            f"Document uploaded successfully - document_id: {upload_result.document_id}"
        )
        return response

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        # Log the full exception details before handling
        logger.error(f"Unhandled exception in upload_document: {str(e)}", exc_info=True)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        # Use enhanced error handling
        raise handle_api_error(e, context, ErrorCategory.FILE_PROCESSING)


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
):
    """Get document details"""

    context = create_error_context(
        user_id=str(user.id),
        operation="get_document",
        metadata={"document_id": document_id},
    )

    try:
        # Get authenticated client through context
        supabase_client = await AuthContext.get_authenticated_client()

        # RLS will automatically filter by authenticated user
        result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        return result.data[0]

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        # Use enhanced error handling
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.post("/{document_id}/reprocess-ocr")
async def reprocess_document_with_ocr(
    document_id: str,
    background_tasks: BackgroundTasks,
    processing_options: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Reprocess document using enhanced OCR for better text extraction"""

    try:
        # Verify document ownership - RLS will handle access control
        supabase_client = await AuthContext.get_authenticated_client()
        doc_result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]

        # Check if OCR is available
        ocr_capabilities = await document_service.get_ocr_capabilities()
        if not ocr_capabilities["service_available"]:
            raise HTTPException(status_code=503, detail="OCR service not available")

        # Get user profile for context - RLS ensures we only get our own profile
        user_result = supabase_client.table("profiles").select("*").execute()
        user_profile = user_result.data[0] if user_result.data else {}

        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
            "document_id": document_id,
            "filename": document["original_filename"],
        }

        # Enhanced processing options
        enhanced_options = {
            "priority": user_profile.get("subscription_status")
            in ["premium", "enterprise"],
            "enhanced_quality": True,
            "detailed_analysis": (
                processing_options
                and processing_options.get("detailed_analysis", False)
                if processing_options
                else False
            ),
            "contract_specific": True,
        }

        # Use enhanced background processing via Celery
        from app.tasks.background_tasks import (
            enhanced_reprocess_document_with_ocr_background,
        )

        task = enhanced_reprocess_document_with_ocr_background.delay(
            document_id, user.id, document, contract_context, enhanced_options
        )

        return {
            "message": "Enhanced OCR processing started",
            "document_id": document_id,
            "estimated_completion_minutes": 3 if enhanced_options["priority"] else 5,
            "processing_features": [
                "gemini_2.5_pro_ocr",
                "contract_analysis",
                "australian_context",
                "quality_enhancement",
                "progress_tracking",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced OCR reprocessing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch-ocr")
async def batch_process_ocr(
    document_ids: List[str],
    background_tasks: BackgroundTasks,
    batch_options: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Batch process multiple documents with OCR"""

    try:
        # Validate document ownership - RLS handles access control
        supabase_client = await AuthContext.get_authenticated_client()
        verified_docs = []
        for doc_id in document_ids:
            doc_result = (
                supabase_client.table("documents")
                .select("id, original_filename, file_type")
                .eq("id", doc_id)
                .execute()
            )

            if doc_result.data:
                verified_docs.append(doc_result.data[0])

        if not verified_docs:
            raise HTTPException(status_code=404, detail="No valid documents found")

        # Check OCR availability
        ocr_capabilities = await document_service.get_ocr_capabilities()
        if not ocr_capabilities["service_available"]:
            raise HTTPException(status_code=503, detail="OCR service not available")

        # Get user profile - RLS ensures we only get our own profile
        user_result = supabase_client.table("profiles").select("*").execute()
        user_profile = user_result.data[0] if user_result.data else {}

        # Create batch context
        from datetime import datetime

        batch_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": (
                batch_options.get("contract_type", "purchase_agreement")
                if batch_options
                else "purchase_agreement"
            ),
            "user_type": user_profile.get("user_type", "buyer"),
            "batch_id": f"batch_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        }

        # Enhanced batch processing options
        processing_options = {
            "priority": user_profile.get("subscription_status")
            in ["premium", "enterprise"],
            "parallel_processing": len(verified_docs) > 1,
            "contract_analysis": (
                batch_options.get("include_analysis", True) if batch_options else True
            ),
            "quality_enhancement": True,
        }

        # Start batch processing
        batch_id = batch_context["batch_id"]

        from app.tasks.background_tasks import batch_ocr_processing_background

        task = batch_ocr_processing_background.delay(
            [doc["id"] for doc in verified_docs],
            user.id,
            batch_context,
            processing_options,
        )

        return {
            "message": "Batch OCR processing started",
            "batch_id": batch_id,
            "documents_queued": len(verified_docs),
            "estimated_completion_minutes": min(30, len(verified_docs) * 3),
            "processing_features": [
                "gemini_2.5_pro_ocr",
                "batch_optimization",
                "contract_analysis",
                (
                    "parallel_processing"
                    if processing_options["parallel_processing"]
                    else "sequential_processing"
                ),
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/ocr-status")
async def get_ocr_status(
    document_id: str,
    user: User = Depends(get_current_user),
):
    """Get detailed OCR processing status for a document"""

    try:
        # Verify document ownership - RLS will handle access control
        supabase_client = await AuthContext.get_authenticated_client()
        doc_result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]
        processing_results = document.get("processing_results", {})

        # Determine processing status
        status = document.get("processing_status", "unknown")

        if status in ["queued_for_ocr", "processing_ocr", "reprocessing_ocr"]:
            # Check if we have task ID for detailed status
            task_id = processing_results.get("task_id")
            task_status = "unknown"

            if task_id:
                # Here you could check Celery task status
                # For now, provide estimated status
                task_status = "processing"

        # Calculate processing metrics
        metrics = {
            "extraction_confidence": processing_results.get(
                "extraction_confidence", 0.0
            ),
            "character_count": processing_results.get("character_count", 0),
            "word_count": processing_results.get("word_count", 0),
            "extraction_method": processing_results.get("extraction_method", "unknown"),
            "processing_time": processing_results.get("processing_time", 0),
        }

        return {
            "document_id": document_id,
            "filename": document["original_filename"],
            "status": status,
            "processing_metrics": metrics,
            "ocr_features_used": processing_results.get("processing_details", {}).get(
                "enhancement_applied", []
            ),
            "last_updated": document.get("updated_at"),
            "supports_reprocessing": status in ["processed", "failed", "ocr_failed"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR status check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/progress")
async def get_document_processing_progress(
    document_id: str,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get real-time processing progress for a document"""

    try:
        # Verify document ownership - RLS will handle access control
        supabase_client = await AuthContext.get_authenticated_client()
        doc_result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get processing progress
        progress = await document_service.get_processing_progress(document_id)

        return progress

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Progress retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{document_id}/validate-contract")
async def validate_contract_document(
    document_id: str,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Validate document specifically for contract processing"""

    try:
        # Verify document ownership - RLS will handle access control
        supabase_client = await AuthContext.get_authenticated_client()
        doc_result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]

        # Get user profile for context - RLS ensures we only get our own profile
        user_result = supabase_client.table("profiles").select("*").execute()
        user_profile = user_result.data[0] if user_result.data else {}

        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
        }

        # Validate contract document
        validation_result = await document_service.validate_contract_document(
            document["storage_path"],
            document["file_type"],
            contract_context,
        )

        return {
            "document_id": document_id,
            "filename": document["original_filename"],
            "validation_result": validation_result,
            "contract_context": contract_context,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contract validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ocr/capabilities")
async def get_ocr_capabilities(
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get OCR service capabilities and status"""

    try:
        # Get OCR capabilities
        capabilities = await document_service.get_ocr_capabilities()

        return capabilities

    except Exception as e:
        logger.error(f"OCR capabilities error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{document_id}/assess-quality")
async def assess_document_quality(
    document_id: str,
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Assess document processing quality and provide recommendations"""

    try:
        # Verify document ownership - RLS will handle access control
        supabase_client = await AuthContext.get_authenticated_client()
        doc_result = (
            supabase_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]
        processing_results = document.get("processing_results", {})

        # Get user profile for context - RLS ensures we only get our own profile
        user_result = supabase_client.table("profiles").select("*").execute()
        user_profile = user_result.data[0] if user_result.data else {}

        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
        }

        # Assess document quality
        quality_assessment = document_service.assess_document_quality(
            processing_results.get("extracted_text", ""),
            document["file_type"],
            document["file_size"],
            processing_results.get("extraction_method", "unknown"),
            processing_results.get("extraction_confidence", 0.0),
            contract_context,
        )

        return {
            "document_id": document_id,
            "filename": document["original_filename"],
            "quality_assessment": quality_assessment,
            "processing_results_summary": {
                "extraction_method": processing_results.get(
                    "extraction_method", "unknown"
                ),
                "extraction_confidence": processing_results.get(
                    "extraction_confidence", 0.0
                ),
                "character_count": processing_results.get("character_count", 0),
                "word_count": processing_results.get("word_count", 0),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
