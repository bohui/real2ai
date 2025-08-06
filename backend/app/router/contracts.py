"""Contract analysis router with enhanced error handling."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.core.auth import get_current_user, User
from app.clients.factory import get_supabase_client
from app.core.error_handler import (
    handle_api_error, 
    create_error_context, 
    ErrorCategory
)
from app.core.retry_manager import retry_database_operation, retry_api_call
from app.core.notification_system import notification_system, notify_user_error, notify_user_success
from app.schema.contract import ContractAnalysisRequest, ContractAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/analyze", response_model=ContractAnalysisResponse)
async def start_contract_analysis(
    request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db_client=Depends(get_supabase_client),
):
    """Start contract analysis with enhanced error handling and validation"""

    # Create error context for better error reporting
    context = create_error_context(
        user_id=str(user.id),
        operation="start_contract_analysis",
        document_id=request.document_id
    )

    try:
        # Validate request parameters
        if not request.document_id:
            raise ValueError("Document ID is required")
        
        if not user.australian_state:
            raise ValueError("Australian state is required for accurate contract analysis")

        # Ensure database client is initialized with retry
        await _initialize_database_client(db_client)

        # Check user credits with user-friendly messaging
        if user.credits_remaining <= 0 and user.subscription_status == "free":
            raise ValueError("You don't have enough credits to analyze this contract")

        # Get document with retry mechanism
        document = await _get_user_document(db_client, request.document_id, user.id)
        
        # Validate document is suitable for analysis
        if not _is_valid_contract_document(document):
            raise ValueError("This file doesn't appear to be a property contract")

        # Create contract record with retry
        contract_id = await _create_contract_record(
            db_client, request.document_id, document, user
        )

        # Create analysis record with retry
        analysis_id = await _create_analysis_record(db_client, contract_id, user.id)

        # Start background analysis with proper error handling
        task_id = await _start_background_analysis(
            contract_id, analysis_id, user.id, document, request.analysis_options
        )

        # Send success notification to user
        await notification_system.send_notification(
            template_name="analysis_started",
            user_id=str(user.id),
            contract_id=contract_id,
            session_id=context.session_id or f"contract_{contract_id}"
        )

        return ContractAnalysisResponse(
            contract_id=contract_id,
            analysis_id=analysis_id,
            status="queued",
            task_id=task_id,
            estimated_completion_minutes=2,
        )

    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except Exception as e:
        # Send error notification to user
        await notify_user_error(
            user_id=str(user.id),
            title="Analysis Failed",
            message=str(e),
            session_id=context.session_id or f"contract_error_{user.id}",
            contract_id=context.contract_id
        )
        
        # Use enhanced error handler
        raise handle_api_error(e, context, ErrorCategory.CONTRACT_ANALYSIS)


@retry_database_operation(max_attempts=3)
async def _initialize_database_client(db_client):
    """Initialize database client with retry logic"""
    if not hasattr(db_client, "_client") or db_client._client is None:
        await db_client.initialize()


@retry_database_operation(max_attempts=3)
async def _get_user_document(db_client, document_id: str, user_id: str):
    """Get user document with retry logic"""
    doc_result = (
        db_client.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not doc_result.data:
        raise ValueError(f"Document not found or you don't have access to it")

    return doc_result.data[0]


def _is_valid_contract_document(document) -> bool:
    """Validate that document is suitable for contract analysis"""
    # Check file size (basic validation)
    if document.get("file_size", 0) > 10 * 1024 * 1024:  # 10MB limit
        raise ValueError("File is too large. Please use a file smaller than 10MB")
    
    # Check file type
    allowed_types = [
        "application/pdf", 
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    file_type = document.get("file_type", "").lower()
    if file_type and file_type not in allowed_types:
        raise ValueError("This file format isn't supported. Please upload a PDF, DOC, or DOCX file")
    
    # Check if document has content
    if not document.get("content") and not document.get("file_path"):
        raise ValueError("The document appears to be empty or corrupted")
    
    return True


@retry_database_operation(max_attempts=3)
async def _create_contract_record(db_client, document_id: str, document: dict, user: User) -> str:
    """Create contract record with retry logic"""
    contract_data = {
        "document_id": document_id,
        "contract_type": document.get("contract_type", "purchase_agreement"),
        "australian_state": user.australian_state,
        "user_id": user.id,
    }

    contract_result = db_client.table("contracts").insert(contract_data).execute()
    
    if not contract_result.data:
        raise ValueError("Failed to create contract record")
    
    return contract_result.data[0]["id"]


@retry_database_operation(max_attempts=3)
async def _create_analysis_record(db_client, contract_id: str, user_id: str) -> str:
    """Create analysis record with retry logic"""
    analysis_data = {
        "contract_id": contract_id,
        "user_id": user_id,
        "agent_version": "1.0",
        "status": "pending",
    }

    analysis_result = (
        db_client.table("contract_analyses").insert(analysis_data).execute()
    )
    
    if not analysis_result.data:
        raise ValueError("Failed to create analysis record")
    
    return analysis_result.data[0]["id"]


@retry_api_call(max_attempts=2)
async def _start_background_analysis(
    contract_id: str, 
    analysis_id: str, 
    user_id: str, 
    document: dict, 
    analysis_options
) -> str:
    """Start background analysis with retry logic"""
    try:
        from app.tasks.background_tasks import analyze_contract_background

        task = analyze_contract_background.delay(
            contract_id,
            analysis_id,
            user_id,
            document,
            analysis_options.model_dump(),
        )
        
        if not task or not task.id:
            raise ValueError("Failed to queue contract analysis")
        
        return task.id
        
    except Exception as e:
        # Log the specific error for debugging
        logger.error(f"Background task creation failed: {str(e)}")
        raise ValueError("Our AI service is temporarily busy. Please try again in a few minutes")


@router.get("/{contract_id}/status")
async def get_analysis_status(
    contract_id: str,
    user: User = Depends(get_current_user),
    db_client=Depends(get_supabase_client),
):
    """Get contract analysis status and progress with enhanced error handling"""
    
    context = create_error_context(
        user_id=str(user.id),
        contract_id=contract_id,
        operation="get_analysis_status"
    )
    
    try:
        # Validate contract ID format
        if not contract_id or not contract_id.strip():
            raise ValueError("Contract ID is required")

        # Initialize database client with retry
        await _initialize_database_client(db_client)

        # Get analysis status with retry and validation
        analysis = await _get_analysis_status_with_validation(
            db_client, contract_id, user.id
        )

        # Calculate progress with enhanced information
        progress_info = _calculate_analysis_progress(analysis)

        return {
            "contract_id": contract_id,
            "analysis_id": analysis["id"],
            "status": analysis["status"],
            "progress": progress_info["progress"],
            "processing_time": analysis.get("processing_time", 0),
            "created_at": analysis["created_at"],
            "updated_at": analysis["updated_at"],
            "estimated_completion": progress_info["estimated_completion"],
            "status_message": progress_info["status_message"],
            "next_update_in_seconds": progress_info.get("next_update_in_seconds")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@retry_database_operation(max_attempts=3)
async def _get_analysis_status_with_validation(db_client, contract_id: str, user_id: str):
    """Get analysis status with validation and retry logic"""
    
    # First verify the contract belongs to the user
    contract_result = (
        db_client.table("contracts")
        .select("id, user_id")
        .eq("id", contract_id)
        .execute()
    )
    
    if not contract_result.data:
        raise ValueError("Contract not found")
    
    contract = contract_result.data[0]
    if contract["user_id"] != user_id:
        raise ValueError("You don't have access to this contract")

    # Get analysis status
    result = (
        db_client.table("contract_analyses")
        .select("id, status, created_at, updated_at, processing_time, error_message")
        .eq("contract_id", contract_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise ValueError("Analysis not found for this contract")

    return result.data[0]


def _calculate_analysis_progress(analysis: dict) -> dict:
    """Calculate detailed progress information"""
    
    status = analysis["status"]
    
    # Enhanced progress mapping with more granular updates
    progress_mapping = {
        "pending": {
            "progress": 0,
            "status_message": "Your contract analysis is queued and will start shortly",
            "estimated_completion": "2-5 minutes",
            "next_update_in_seconds": 30
        },
        "queued": {
            "progress": 5,
            "status_message": "Analysis has been queued and will begin processing soon",
            "estimated_completion": "2-5 minutes", 
            "next_update_in_seconds": 15
        },
        "processing": {
            "progress": 50,
            "status_message": "Our AI is analyzing your contract - this may take a few minutes",
            "estimated_completion": "1-3 minutes",
            "next_update_in_seconds": 10
        },
        "completed": {
            "progress": 100,
            "status_message": "Analysis complete! You can now view your results",
            "estimated_completion": None,
            "next_update_in_seconds": None
        },
        "failed": {
            "progress": 0,
            "status_message": "Analysis failed. Please try again or contact support",
            "estimated_completion": None,
            "next_update_in_seconds": None
        },
        "cancelled": {
            "progress": 0,
            "status_message": "Analysis was cancelled", 
            "estimated_completion": None,
            "next_update_in_seconds": None
        }
    }
    
    return progress_mapping.get(status, {
        "progress": 0,
        "status_message": "Analysis status unknown",
        "estimated_completion": None,
        "next_update_in_seconds": 30
    })


@router.get("/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str,
    user: User = Depends(get_current_user),
    db_client=Depends(get_supabase_client),
):
    """Get contract analysis results"""

    try:
        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        # Get analysis results
        result = (
            db_client.table("contract_analyses")
            .select("*")
            .eq("contract_id", contract_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Analysis not found")

        analysis = result.data[0]

        # Verify user owns this contract
        contract_result = (
            db_client.table("contracts").select("*").eq("id", contract_id).execute()
        )
        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = contract_result.data[0]
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", contract["document_id"])
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "contract_id": contract_id,
            "analysis_status": analysis["status"],
            "analysis_result": analysis.get("analysis_result", {}),
            "risk_score": analysis.get("risk_score"),
            "processing_time": analysis.get("processing_time"),
            "created_at": analysis["created_at"],
        }

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/report")
async def download_analysis_report(
    contract_id: str,
    format: str = "pdf",
    user: User = Depends(get_current_user),
    db_client=Depends(get_supabase_client),
):
    """Download analysis report"""

    try:
        # Get analysis data
        analysis_data = await get_contract_analysis(contract_id, user, db_client)

        if format == "pdf":
            # Generate PDF report (would implement with reportlab or similar)
            from app.tasks.background_tasks import generate_pdf_report

            pdf_content = await generate_pdf_report(analysis_data)
            return JSONResponse(
                content={"download_url": f"/api/contracts/{contract_id}/report.pdf"},
                headers={"Content-Type": "application/json"},
            )
        else:
            return analysis_data

    except Exception as e:
        logger.error(f"Report download error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{contract_id}")
async def delete_contract_analysis(
    contract_id: str,
    user: User = Depends(get_current_user),
    db_client=Depends(get_supabase_client),
):
    """Delete contract analysis and related data"""
    
    try:
        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        # Verify user owns this contract
        contract_result = (
            db_client.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )
        
        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")
            
        contract = contract_result.data[0]
        
        # Verify ownership through document
        doc_result = (
            db_client.table("documents")
            .select("user_id")
            .eq("id", contract["document_id"])
            .execute()
        )
        
        if not doc_result.data or doc_result.data[0]["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete contract analyses first (foreign key constraint)
        analyses_result = (
            db_client.table("contract_analyses")
            .delete()
            .eq("contract_id", contract_id)
            .execute()
        )
        
        # Delete the contract
        contract_delete_result = (
            db_client.table("contracts")
            .delete()
            .eq("id", contract_id)
            .execute()
        )
        
        if not contract_delete_result.data:
            raise HTTPException(status_code=404, detail="Contract not found or already deleted")
        
        return {
            "message": "Contract analysis deleted successfully",
            "contract_id": contract_id,
            "analyses_deleted": len(analyses_result.data) if analyses_result.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete contract error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notifications")
async def get_user_notifications(
    user: User = Depends(get_current_user),
    include_acknowledged: bool = False
):
    """Get user notifications with enhanced feedback"""
    
    try:
        notifications = await notification_system.get_user_notifications(
            user_id=str(user.id),
            include_acknowledged=include_acknowledged
        )
        
        return {
            "notifications": [n.to_dict() for n in notifications],
            "total_count": len(notifications),
            "unread_count": len([n for n in notifications if not n.acknowledged])
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    user: User = Depends(get_current_user)
):
    """Dismiss a user notification"""
    
    try:
        await notification_system.dismiss_notification(
            user_id=str(user.id),
            notification_id=notification_id
        )
        
        return {"message": "Notification dismissed successfully"}
        
    except Exception as e:
        logger.error(f"Error dismissing notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to dismiss notification")
