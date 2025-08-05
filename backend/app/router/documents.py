"""Document management router."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import Optional, Dict, Any, List
import logging

from app.core.auth import get_current_user, User
from app.core.database import get_database_client
from app.core.config import get_settings
from app.model.enums import ContractType, AustralianState
from app.services.document_service import DocumentService
from app.services.websocket_service import WebSocketManager
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
document_service = DocumentService()
websocket_manager = WebSocketManager()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    contract_type: ContractType = ContractType.PURCHASE_AGREEMENT,
    australian_state: AustralianState = AustralianState.NSW,
    user: User = Depends(get_current_user),
):
    """Upload contract document for analysis"""

    try:
        # Validate file
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

        # Get database client first
        db_client = get_database_client()

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        # Upload to Supabase Storage (this includes validation)
        upload_result = await document_service.upload_file(
            file=file, user_id=user.id, contract_type=contract_type
        )

        # Verify file was actually uploaded successfully
        try:
            # Try to get file content to verify upload worked
            await document_service.get_file_content(upload_result["storage_path"])
        except Exception as verification_error:
            logger.error(f"File upload verification failed: {str(verification_error)}")
            raise HTTPException(
                status_code=500, detail="File upload failed - please try again"
            )

        # Store document metadata in database only after successful upload verification
        document_data = {
            "id": upload_result["document_id"],
            "user_id": user.id,
            "filename": file.filename,
            "storage_path": upload_result["storage_path"],
            "file_type": file_extension,
            "file_size": file.size,
            "status": "uploaded",
        }

        # Insert to database with error handling
        try:
            db_client.table("documents").insert(document_data).execute()
        except Exception as db_error:
            # If database insert fails, try to clean up the uploaded file
            logger.error(f"Database insert failed: {str(db_error)}")
            try:
                storage = db_client.storage()
                storage.from_(document_service.storage_bucket).remove(
                    [upload_result["storage_path"]]
                )
                logger.info(
                    f"Cleaned up orphaned file: {upload_result['storage_path']}"
                )
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup orphaned file: {str(cleanup_error)}")

            raise HTTPException(
                status_code=500, detail="Failed to save document metadata"
            )

        # Start background processing via Celery
        from app.tasks.background_tasks import process_document_background

        task = process_document_background.delay(
            upload_result["document_id"],
            user.id,
            australian_state,
            contract_type,
        )

        return DocumentUploadResponse(
            document_id=upload_result["document_id"],
            filename=file.filename,
            file_size=file.size,
            upload_status="uploaded",
            processing_time=0.0,
        )

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client),
):
    """Get document details"""

    try:
        result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        return result.data[0]

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{document_id}/reprocess-ocr")
async def reprocess_document_with_ocr(
    document_id: str,
    background_tasks: BackgroundTasks,
    processing_options: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client),
):
    """Reprocess document using enhanced OCR for better text extraction"""

    try:
        # Verify document ownership
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]

        # Check if OCR is available
        ocr_capabilities = await document_service.get_ocr_capabilities()
        if not ocr_capabilities["service_available"]:
            raise HTTPException(status_code=503, detail="OCR service not available")

        # Get user profile for context
        user_result = (
            db_client.table("profiles").select("*").eq("id", user.id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}

        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
            "document_id": document_id,
            "filename": document["filename"],
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
    db_client=Depends(get_database_client),
):
    """Batch process multiple documents with OCR"""

    try:
        # Validate document ownership
        verified_docs = []
        for doc_id in document_ids:
            doc_result = (
                db_client.table("documents")
                .select("id, filename, file_type")
                .eq("id", doc_id)
                .eq("user_id", user.id)
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

        # Get user profile
        user_result = (
            db_client.table("profiles").select("*").eq("id", user.id).execute()
        )
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
    db_client=Depends(get_database_client),
):
    """Get detailed OCR processing status for a document"""

    try:
        # Verify document ownership
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]
        processing_results = document.get("processing_results", {})

        # Determine processing status
        status = document.get("status", "unknown")

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
            "filename": document["filename"],
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
    db_client=Depends(get_database_client),
):
    """Get real-time processing progress for a document"""
    
    try:
        # Verify document ownership
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Initialize document service
        await document_service.initialize()
        
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
    db_client=Depends(get_database_client),
):
    """Validate document specifically for contract processing"""
    
    try:
        # Verify document ownership
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = doc_result.data[0]
        
        # Get user profile for context
        user_result = (
            db_client.table("profiles").select("*").eq("id", user.id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}
        
        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
        }
        
        # Initialize document service
        await document_service.initialize()
        
        # Validate contract document
        validation_result = await document_service.validate_contract_document(
            document["storage_path"],
            document["file_type"],
            contract_context,
        )
        
        return {
            "document_id": document_id,
            "filename": document["filename"],
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
):
    """Get OCR service capabilities and status"""
    
    try:
        # Initialize document service
        await document_service.initialize()
        
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
    db_client=Depends(get_database_client),
):
    """Assess document processing quality and provide recommendations"""
    
    try:
        # Verify document ownership
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = doc_result.data[0]
        processing_results = document.get("processing_results", {})
        
        # Get user profile for context
        user_result = (
            db_client.table("profiles").select("*").eq("id", user.id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}
        
        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
        }
        
        # Initialize document service
        await document_service.initialize()
        
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
            "filename": document["filename"],
            "quality_assessment": quality_assessment,
            "processing_results_summary": {
                "extraction_method": processing_results.get("extraction_method", "unknown"),
                "extraction_confidence": processing_results.get("extraction_confidence", 0.0),
                "character_count": processing_results.get("character_count", 0),
                "word_count": processing_results.get("word_count", 0),
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
