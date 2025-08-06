"""OCR processing router."""

from fastapi import APIRouter, HTTPException, Depends
import logging

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.schema.ocr import OCRCapabilitiesResponse, EnhancedOCRCapabilities, OCRQueueStatus
from app.core.error_handler import (
    handle_api_error, 
    create_error_context, 
    ErrorCategory
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ocr", tags=["ocr"])


# Dependency function to get initialized document service
async def get_document_service(
    user: User = Depends(get_current_user),
) -> DocumentService:
    """Get initialized document service with user-aware architecture"""
    user_client = await AuthContext.get_authenticated_client(require_auth=True)
    service = DocumentService(user_client=user_client)
    await service.initialize()
    return service


@router.get("/capabilities")
async def get_ocr_capabilities(
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get comprehensive OCR service capabilities and status"""
    
    context = create_error_context(
        user_id=str(user.id),
        operation="get_ocr_capabilities"
    )
    
    try:
        capabilities = await document_service.get_ocr_capabilities()
        
        # Enhanced capabilities with Gemini 2.5 Pro features
        enhanced_capabilities = {
            **capabilities,
            "gemini_features": {
                "multimodal_processing": True,
                "contract_analysis": True,
                "australian_specific": True,
                "structured_output": True,
                "batch_processing": True,
                "priority_queue": True
            },
            "processing_tiers": {
                "standard": {
                    "queue_time": "1-3 minutes",
                    "processing_time": "2-5 minutes",
                    "features": ["basic_ocr", "contract_detection"]
                },
                "priority": {
                    "queue_time": "< 30 seconds", 
                    "processing_time": "1-3 minutes",
                    "features": ["enhanced_ocr", "detailed_analysis", "quality_boost"]
                }
            },
            "api_health": await document_service.gemini_ocr.health_check() if hasattr(document_service, 'gemini_ocr') and document_service.gemini_ocr else {"status": "unavailable"}
        }
        
        return enhanced_capabilities
        
    except Exception as e:
        # Use enhanced error handling
        raise handle_api_error(e, context, ErrorCategory.EXTERNAL_API)


@router.get("/queue-status")
async def get_ocr_queue_status(
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get current OCR processing queue status"""
    
    context = create_error_context(
        user_id=str(user.id),
        operation="get_ocr_queue_status"
    )
    
    try:
        # This would integrate with Celery to get real queue status
        # For now, return estimated status
        
        queue_status = {
            "queue_position": 0,  # Would be calculated from Celery
            "estimated_wait_time_minutes": 2,
            "active_workers": 3,  # Would be from Celery inspect
            "queue_length": 5,    # Would be from Celery
            "user_priority": "standard" if user.subscription_status == "free" else "priority",
            "processing_capacity": {
                "documents_per_hour": 20,
                "average_processing_time_minutes": 3
            }
        }
        
        return queue_status
        
    except Exception as e:
        # Use enhanced error handling
        raise handle_api_error(e, context, ErrorCategory.SYSTEM)