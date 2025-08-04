"""
Real2.AI FastAPI Backend
Australian Real Estate AI Assistant
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Optional, Dict, Any, List
import asyncio
import logging
import time
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import application modules
from app.models.contract_state import (
    RealEstateAgentState,
    AustralianState,
    ContractType,
    create_initial_state,
)
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.core.config import get_settings
from app.core.auth import get_current_user, User
from app.core.database import get_database_client
from app.services.document_service import DocumentService
from app.services.websocket_service import WebSocketManager
from app.api.models import (
    ContractAnalysisRequest,
    ContractAnalysisResponse,
    DocumentUploadResponse,
    UserRegistrationRequest,
    UserLoginRequest,
    OnboardingStatusResponse,
    OnboardingPreferencesRequest,
    OnboardingCompleteRequest,
)

# Initialize FastAPI app
app = FastAPI(
    title="Real2.AI API",
    description="Australian Real Estate AI Assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://real2.ai", "https://*.real2.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
settings = get_settings()
security = HTTPBearer()
db_client = get_database_client()
document_service = DocumentService()
websocket_manager = WebSocketManager()

# Initialize LangGraph workflow
contract_workflow = ContractAnalysisWorkflow(
    openai_api_key=settings.openai_api_key,
    model_name="gpt-4",
    openai_api_base=settings.openai_api_base,
)

# Global state storage (in production, use Redis/database)
analysis_sessions: Dict[str, RealEstateAgentState] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Real2.AI API...")

    # Initialize database connection
    await db_client.initialize()

    # Initialize document service
    await document_service.initialize()

    logger.info("Real2.AI API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Real2.AI API...")

    # Close database connections
    await db_client.close()

    # Close websocket connections
    await websocket_manager.disconnect_all()

    logger.info("Real2.AI API shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
    }


# Authentication Endpoints


@app.post("/api/auth/register")
async def register_user(user_data: UserRegistrationRequest, db_client=Depends(get_database_client)):
    """Register a new user"""
    try:
        # Create user in Supabase
        user_result = db_client.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "australian_state": user_data.australian_state,
                        "user_type": user_data.user_type,
                    }
                },
            }
        )

        if user_result.user:
            # Create user profile
            profile_data = {
                "id": user_result.user.id,
                "email": user_data.email,
                "australian_state": user_data.australian_state,
                "user_type": user_data.user_type,
                "subscription_status": "free",
                "credits_remaining": 1,  # First contract free
                "onboarding_completed": False,
                "onboarding_preferences": {}
            }

            db_client.table("profiles").insert(profile_data).execute()

            return {
                "user_id": user_result.user.id,
                "email": user_data.email,
                "message": "User registered successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail="Registration failed")


@app.post("/api/auth/login")
async def login_user(login_data: UserLoginRequest, db_client=Depends(get_database_client)):
    """Authenticate user"""
    try:
        auth_result = db_client.auth.sign_in_with_password(
            {"email": login_data.email, "password": login_data.password}
        )

        if auth_result.user and auth_result.session:
            # Get user profile
            profile_result = (
                db_client.table("profiles")
                .select("*")
                .eq("id", auth_result.user.id)
                .execute()
            )

            return {
                "access_token": auth_result.session.access_token,
                "refresh_token": auth_result.session.refresh_token,
                "user_profile": profile_result.data[0] if profile_result.data else None,
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


# Document Management Endpoints


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
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

        # Upload to Supabase Storage
        upload_result = await document_service.upload_file(
            file=file, user_id=user.id, contract_type=contract_type
        )

        # Store document metadata in database
        document_data = {
            "id": upload_result["document_id"],
            "user_id": user.id,
            "filename": file.filename,
            "storage_path": upload_result["storage_path"],
            "file_type": file_extension,
            "file_size": file.size,
            "status": "uploaded",
        }

        db_client.table("documents").insert(document_data).execute()

        # Start background processing
        background_tasks.add_task(
            process_document_background,
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


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str, user: User = Depends(get_current_user), db_client=Depends(get_database_client)):
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


# Contract Analysis Endpoints


@app.post("/api/contracts/analyze", response_model=ContractAnalysisResponse)
async def start_contract_analysis(
    request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client),
):
    """Start contract analysis"""

    try:
        # Check user credits
        if user.credits_remaining <= 0 and user.subscription_status == "free":
            raise HTTPException(
                status_code=402,
                detail="No credits remaining. Please upgrade your subscription.",
            )

        # Get document
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", request.document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]

        # Create contract record
        contract_data = {
            "document_id": request.document_id,
            "contract_type": document.get("contract_type", "purchase_agreement"),
            "australian_state": user.australian_state,
            "user_id": user.id,
        }

        contract_result = (
            db_client.table("contracts").insert(contract_data).execute()
        )
        contract_id = contract_result.data[0]["id"]

        # Create analysis record
        analysis_data = {
            "contract_id": contract_id,
            "agent_version": "1.0",
            "status": "pending",
        }

        analysis_result = (
            db_client.table("contract_analyses").insert(analysis_data).execute()
        )
        analysis_id = analysis_result.data[0]["id"]

        # Start background analysis
        background_tasks.add_task(
            analyze_contract_background,
            contract_id,
            analysis_id,
            user.id,
            document,
            request.analysis_options,
        )

        return ContractAnalysisResponse(
            contract_id=contract_id,
            analysis_id=analysis_id,
            status="pending",
            estimated_completion_minutes=2,
        )

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Contract analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/contracts/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str, user: User = Depends(get_current_user), db_client=Depends(get_database_client)
):
    """Get contract analysis results"""

    try:
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
            db_client.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
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


@app.get("/api/contracts/{contract_id}/report")
async def download_analysis_report(
    contract_id: str, format: str = "pdf", user: User = Depends(get_current_user), db_client=Depends(get_database_client)
):
    """Download analysis report"""

    try:
        # Get analysis data
        analysis_data = await get_contract_analysis(contract_id, user, db_client)

        if format == "pdf":
            # Generate PDF report (would implement with reportlab or similar)
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


# User Management Endpoints


@app.get("/api/users/profile")
async def get_user_profile(user: User = Depends(get_current_user)):
    """Get user profile"""
    return user.model_dump()


# Onboarding Management Endpoints


@app.get("/api/users/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: User = Depends(get_current_user), db_client=Depends(get_database_client)):
    """Get user onboarding status"""
    try:
        profile_result = (
            db_client.table("profiles")
            .select("onboarding_completed", "onboarding_completed_at", "onboarding_preferences")
            .eq("id", user.id)
            .execute()
        )
        
        if not profile_result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
            
        profile = profile_result.data[0]
        return OnboardingStatusResponse(
            onboarding_completed=profile.get("onboarding_completed", False),
            onboarding_completed_at=profile.get("onboarding_completed_at"),
            onboarding_preferences=profile.get("onboarding_preferences", {})
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get onboarding status error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/users/onboarding/complete")
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client)
):
    """Complete user onboarding and save preferences"""
    try:
        # Check if already completed
        profile_result = (
            db_client.table("profiles")
            .select("onboarding_completed")
            .eq("id", user.id)
            .execute()
        )
        
        if profile_result.data and profile_result.data[0].get("onboarding_completed", False):
            return {"message": "Onboarding already completed", "skip_onboarding": True}
        
        # Update profile with onboarding completion
        update_data = {
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_preferences": request.onboarding_preferences.model_dump(exclude_unset=True),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        db_client.table("profiles").update(update_data).eq("id", user.id).execute()
        
        # Log onboarding completion
        db_client.table("usage_logs").insert({
            "user_id": user.id,
            "action_type": "onboarding_completed",
            "credits_used": 0,
            "credits_remaining": user.credits_remaining,
            "resource_used": "onboarding",
            "metadata": {"preferences": request.onboarding_preferences.model_dump(exclude_unset=True)}
        }).execute()
        
        return {
            "message": "Onboarding completed successfully",
            "skip_onboarding": False,
            "preferences_saved": True
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Complete onboarding error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/users/onboarding/preferences")
async def update_onboarding_preferences(
    preferences: OnboardingPreferencesRequest,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client)
):
    """Update user onboarding preferences"""
    try:
        update_data = {
            "onboarding_preferences": preferences.model_dump(exclude_unset=True),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        db_client.table("profiles").update(update_data).eq("id", user.id).execute()
        
        return {"message": "Onboarding preferences updated successfully"}
        
    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Update onboarding preferences error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/users/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any], user: User = Depends(get_current_user), db_client=Depends(get_database_client)
):
    """Update user preferences"""
    try:
        db_client.table("profiles").update({"preferences": preferences}).eq(
            "id", user.id
        ).execute()
        return {"message": "Preferences updated successfully"}

    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users/usage-stats")
async def get_usage_stats(user: User = Depends(get_current_user), db_client=Depends(get_database_client)):
    """Get user usage statistics"""

    try:
        # Get usage logs
        usage_result = (
            db_client.table("usage_logs")
            .select("*")
            .eq("user_id", user.id)
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

        # Get contract count
        contracts_result = (
            db_client.from_("documents")
            .select("count", count="exact")
            .eq("user_id", user.id)
            .execute()
        )

        return {
            "credits_remaining": user.credits_remaining,
            "subscription_status": user.subscription_status,
            "total_contracts_analyzed": contracts_result.count,
            "recent_usage": usage_result.data,
        }

    except Exception as e:
        logger.error(f"Usage stats error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws/contracts/{contract_id}/progress")
async def websocket_endpoint(websocket, contract_id: str):
    """WebSocket for real-time analysis progress"""
    await websocket_manager.connect(websocket, contract_id)

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket_manager.disconnect(websocket, contract_id)


@app.post("/api/documents/{document_id}/reprocess-ocr")
async def reprocess_document_with_ocr(
    document_id: str,
    background_tasks: BackgroundTasks,
    processing_options: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client)
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
            raise HTTPException(
                status_code=503, 
                detail="OCR service not available"
            )
        
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
            "filename": document["filename"]
        }
        
        # Enhanced processing options
        enhanced_options = {
            "priority": user_profile.get("subscription_status") in ["premium", "enterprise"],
            "enhanced_quality": True,
            "detailed_analysis": processing_options and processing_options.get("detailed_analysis", False) if processing_options else False,
            "contract_specific": True
        }
        
        # Use enhanced background processing
        background_tasks.add_task(
            enhanced_reprocess_document_with_ocr_background,
            document_id,
            user.id,
            document,
            contract_context,
            enhanced_options
        )
        
        return {
            "message": "Enhanced OCR processing started",
            "document_id": document_id,
            "estimated_completion_minutes": 3 if enhanced_options["priority"] else 5,
            "processing_features": [
                "gemini_2.5_pro_ocr",
                "contract_analysis",
                "australian_context",
                "quality_enhancement"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced OCR reprocessing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/ocr/capabilities")
async def get_ocr_capabilities():
    """Get comprehensive OCR service capabilities and status"""
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
        logger.error(f"OCR capabilities error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/batch-ocr")
async def batch_process_ocr(
    document_ids: List[str],
    background_tasks: BackgroundTasks,
    batch_options: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client)
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
            raise HTTPException(
                status_code=503,
                detail="OCR service not available"
            )
        
        # Get user profile
        user_result = (
            db_client.table("profiles").select("*").eq("id", user.id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}
        
        # Create batch context
        batch_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": batch_options.get("contract_type", "purchase_agreement") if batch_options else "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer"),
            "batch_id": f"batch_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Enhanced batch processing options
        processing_options = {
            "priority": user_profile.get("subscription_status") in ["premium", "enterprise"],
            "parallel_processing": len(verified_docs) > 1,
            "contract_analysis": batch_options.get("include_analysis", True) if batch_options else True,
            "quality_enhancement": True
        }
        
        # Start batch processing
        batch_id = batch_context["batch_id"]
        
        background_tasks.add_task(
            batch_ocr_processing_background,
            [doc["id"] for doc in verified_docs],
            user.id,
            batch_context,
            processing_options
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
                "parallel_processing" if processing_options["parallel_processing"] else "sequential_processing"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/documents/{document_id}/ocr-status")
async def get_ocr_status(
    document_id: str,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client)
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
            "extraction_confidence": processing_results.get("extraction_confidence", 0.0),
            "character_count": processing_results.get("character_count", 0),
            "word_count": processing_results.get("word_count", 0),
            "extraction_method": processing_results.get("extraction_method", "unknown"),
            "processing_time": processing_results.get("processing_time", 0)
        }
        
        return {
            "document_id": document_id,
            "filename": document["filename"],
            "status": status,
            "processing_metrics": metrics,
            "ocr_features_used": processing_results.get("processing_details", {}).get("enhancement_applied", []),
            "last_updated": document.get("updated_at"),
            "supports_reprocessing": status in ["processed", "failed", "ocr_failed"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR status check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/ocr/queue-status")
async def get_ocr_queue_status(user: User = Depends(get_current_user)):
    """Get current OCR processing queue status"""
    
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
        logger.error(f"Queue status error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Background Tasks


async def enhanced_reprocess_document_with_ocr_background(
    document_id: str,
    user_id: str,
    document: Dict[str, Any],
    contract_context: Dict[str, Any],
    processing_options: Dict[str, Any]
):
    """Background task for OCR reprocessing"""
    
    try:
        # Update document status
        db_client.table("documents").update({
            "status": "reprocessing_ocr"
        }).eq("id", document_id).execute()
        
        # Send WebSocket notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_started",
                "data": {"document_id": document_id}
            }
        )
        
        # Get user profile for context
        user_result = (
            db_client.table("profiles").select("*").eq("id", user_id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}
        
        # Create contract context
        contract_context = {
            "australian_state": user_profile.get("australian_state", "NSW"),
            "contract_type": "purchase_agreement",
            "user_type": user_profile.get("user_type", "buyer")
        }
        
        # Enhanced OCR extraction with priority handling
        start_time = time.time()
        
        # Send progress update
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_progress",
                "data": {
                    "document_id": document_id,
                    "progress_percent": 10,
                    "current_step": "initializing_gemini_ocr",
                    "step_description": "Initializing Gemini 2.5 Pro OCR service"
                }
            }
        )
        
        # Enhanced OCR with contract-specific optimizations
        extraction_result = await document_service.extract_text_with_ocr(
            document["storage_path"],
            document["file_type"],
            contract_context=contract_context
        )
        
        processing_time = time.time() - start_time
        
        # Enhanced result with performance metrics
        extraction_result["processing_details"] = {
            **extraction_result.get("processing_details", {}),
            "processing_time_seconds": processing_time,
            "priority_processing": processing_options.get("priority", False),
            "enhancement_level": "premium" if processing_options.get("detailed_analysis") else "standard",
            "contract_context_applied": bool(contract_context),
            "gemini_model_used": "gemini-2.5-pro"
        }
        
        # Update document with OCR results
        db_client.table("documents").update({
            "status": "processed",
            "processing_results": extraction_result
        }).eq("id", document_id).execute()
        
        # Send enhanced completion notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_completed",
                "data": {
                    "document_id": document_id,
                    "extraction_confidence": extraction_result.get("extraction_confidence", 0.0),
                    "character_count": extraction_result.get("character_count", 0),
                    "word_count": extraction_result.get("word_count", 0),
                    "extraction_method": extraction_result.get("extraction_method", "unknown"),
                    "processing_time_seconds": processing_time,
                    "contract_terms_detected": extraction_result.get("processing_details", {}).get("contract_terms_found", 0),
                    "enhancement_applied": extraction_result.get("processing_details", {}).get("enhancement_applied", []),
                    "quality_score": extraction_result.get("extraction_confidence", 0.0)
                }
            }
        )
        
        logger.info(f"OCR reprocessing completed for document {document_id}")
        
    except Exception as e:
        logger.error(f"OCR reprocessing failed for {document_id}: {str(e)}")
        
        # Update status to failed
        db_client.table("documents").update({
            "status": "ocr_failed",
            "processing_results": {"error": str(e)}
        }).eq("id", document_id).execute()
        
        # Send error notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_failed",
                "data": {"document_id": document_id, "error_message": str(e)}
            }
        )


async def process_document_background(
    document_id: str,
    user_id: str,
    australian_state: AustralianState,
    contract_type: ContractType,
):
    """Background task for document processing"""

    try:
        # Update document status
        db_client.table("documents").update({"status": "processing"}).eq(
            "id", document_id
        ).execute()

        # Get document metadata
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )
        if not doc_result.data:
            raise Exception("Document not found")

        document = doc_result.data[0]

        # Extract text from document with contract context
        contract_context = {
            "australian_state": australian_state.value,
            "contract_type": contract_type.value,
            "user_type": "buyer"  # Could be derived from user profile
        }
        
        extraction_result = await document_service.extract_text(
            document["storage_path"], 
            document["file_type"],
            contract_context=contract_context
        )

        # Update document with extraction results
        db_client.table("documents").update(
            {"status": "processed", "processing_results": extraction_result}
        ).eq("id", document_id).execute()

        # Send WebSocket notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "document_processed",
                "data": {
                    "document_id": document_id,
                    "extraction_confidence": extraction_result.get(
                        "extraction_confidence", 0.0
                    ),
                    "character_count": extraction_result.get("character_count", 0),
                    "word_count": extraction_result.get("word_count", 0),
                },
            },
        )

        logger.info(f"Document {document_id} processed successfully")

    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {str(e)}")
        db_client.table("documents").update(
            {"status": "failed", "processing_results": {"error": str(e)}}
        ).eq("id", document_id).execute()

        # Send error WebSocket notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "document_processing_failed",
                "data": {"document_id": document_id, "error_message": str(e)},
            },
        )


async def analyze_contract_background(
    contract_id: str,
    analysis_id: str,
    user_id: str,
    document: Dict[str, Any],
    analysis_options: Dict[str, Any],
):
    """Background task for contract analysis"""

    try:
        # Update analysis status
        db_client.table("contract_analyses").update({"status": "processing"}).eq(
            "id", analysis_id
        ).execute()

        # Send WebSocket update
        await websocket_manager.send_message(
            contract_id,
            {
                "event_type": "analysis_started",
                "data": {"contract_id": contract_id, "status": "processing"},
            },
        )

        # Send progress updates during analysis
        progress_steps = [
            ("validating_input", 10, "Validating document and user input"),
            ("processing_document", 25, "Extracting text from document"),
            ("extracting_terms", 45, "Extracting contract terms"),
            ("analyzing_compliance", 65, "Analyzing Australian compliance"),
            ("assessing_risks", 80, "Assessing contract risks"),
            ("generating_recommendations", 90, "Generating recommendations"),
            ("compiling_report", 95, "Compiling final report"),
        ]

        # Function to send progress updates
        async def send_progress_update(step: str, progress: int, description: str):
            await websocket_manager.send_message(
                contract_id,
                {
                    "event_type": "analysis_progress",
                    "data": {
                        "contract_id": contract_id,
                        "current_step": step,
                        "progress_percent": progress,
                        "step_description": description,
                    },
                },
            )

        # Get user profile for context
        user_result = (
            db_client.table("profiles").select("*").eq("id", user_id).execute()
        )
        user_profile = user_result.data[0] if user_result.data else {}

        # Create initial state
        initial_state = create_initial_state(
            user_id=user_id,
            australian_state=AustralianState(
                user_profile.get("australian_state", "NSW")
            ),
            user_type=user_profile.get("user_type", "buyer"),
            user_preferences=user_profile.get("preferences", {}),
        )

        # Get processed document content
        processing_results = document.get("processing_results", {})
        extracted_text = processing_results.get("extracted_text", "")
        extraction_confidence = processing_results.get("extraction_confidence", 0.0)

        if not extracted_text or extraction_confidence < 0.5:
            # If no extracted text or low confidence, try enhanced extraction
            contract_context = {
                "australian_state": user_profile.get("australian_state", "NSW"),
                "contract_type": "purchase_agreement",
                "user_type": user_profile.get("user_type", "buyer")
            }
            
            # Use OCR if confidence is low or text is missing
            force_ocr = extraction_confidence < 0.5
            extraction_result = await document_service.extract_text(
                document["storage_path"], 
                document["file_type"],
                contract_context=contract_context,
                force_ocr=force_ocr
            )
            extracted_text = extraction_result.get("extracted_text", "")
            
            # Update document with improved extraction results
            if extraction_result.get("extraction_confidence", 0) > extraction_confidence:
                db_client.table("documents").update({
                    "processing_results": extraction_result
                }).eq("id", document["id"]).execute()

        # Add document data to state
        initial_state["document_data"] = {
            "document_id": document["id"],
            "filename": document["filename"],
            "content": extracted_text,
            "storage_path": document["storage_path"],
            "file_type": document["file_type"],
        }

        # Run analysis workflow
        final_state = await contract_workflow.analyze_contract(initial_state)

        # Update analysis results
        analysis_result = final_state.get("analysis_results", {})

        db_client.table("contract_analyses").update(
            {
                "status": "completed",
                "analysis_result": analysis_result,
                "risk_score": analysis_result.get("risk_assessment", {}).get(
                    "overall_risk_score", 0
                ),
                "processing_time": final_state.get("processing_time", 0),
            }
        ).eq("id", analysis_id).execute()

        # Deduct user credit
        if user_profile.get("subscription_status") == "free":
            new_credits = max(0, user_profile.get("credits_remaining", 0) - 1)
            db_client.table("profiles").update(
                {"credits_remaining": new_credits}
            ).eq("id", user_id).execute()

        # Log usage
        db_client.table("usage_logs").insert(
            {
                "user_id": user_id,
                "action_type": "contract_analysis",
                "credits_used": 1,
                "remaining_credits": user_profile.get("credits_remaining", 0) - 1,
            }
        ).execute()

        # Send completion WebSocket update
        await websocket_manager.send_message(
            contract_id,
            {
                "event_type": "analysis_completed",
                "data": {
                    "contract_id": contract_id,
                    "analysis_summary": {
                        "overall_risk_score": analysis_result.get(
                            "risk_assessment", {}
                        ).get("overall_risk_score", 0),
                        "total_recommendations": len(
                            analysis_result.get("recommendations", [])
                        ),
                        "compliance_status": (
                            "compliant"
                            if analysis_result.get("compliance_check", {}).get(
                                "state_compliance", False
                            )
                            else "non-compliant"
                        ),
                        "processing_time_seconds": final_state.get(
                            "processing_time", 0
                        ),
                    },
                },
            },
        )

        logger.info(f"Contract analysis {analysis_id} completed successfully")

    except Exception as e:
        logger.error(f"Contract analysis failed for {analysis_id}: {str(e)}")

        # Update analysis status to failed
        db_client.table("contract_analyses").update({"status": "failed"}).eq(
            "id", analysis_id
        ).execute()

        # Send error WebSocket update
        await websocket_manager.send_message(
            contract_id,
            {
                "event_type": "analysis_failed",
                "data": {"contract_id": contract_id, "error_message": str(e)},
            },
        )


async def batch_ocr_processing_background(
    document_ids: List[str],
    user_id: str,
    batch_context: Dict[str, Any],
    processing_options: Dict[str, Any]
):
    """Background task for batch OCR processing with intelligent optimization"""
    
    batch_id = batch_context["batch_id"]
    total_docs = len(document_ids)
    processed_docs = 0
    start_time = time.time()
    
    try:
        logger.info(f"Starting batch OCR processing for {total_docs} documents")
        
        # Initialize batch processing
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_started",
                "data": {
                    "batch_id": batch_id,
                    "total_documents": total_docs,
                    "processing_mode": "parallel" if processing_options["parallel_processing"] else "sequential"
                }
            }
        )
        
        # Process documents with intelligent batching
        if processing_options["parallel_processing"] and total_docs > 1:
            # Parallel processing for multiple documents
            semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
            
            async def process_single_doc(doc_id: str, index: int):
                nonlocal processed_docs
                async with semaphore:
                    try:
                        # Get document details
                        doc_result = (
                            db_client.table("documents")
                            .select("*")
                            .eq("id", doc_id)
                            .execute()
                        )
                        
                        if not doc_result.data:
                            logger.warning(f"Document {doc_id} not found in batch processing")
                            return
                        
                        document = doc_result.data[0]
                        
                        # Update document status
                        db_client.table("documents").update({
                            "status": "processing_ocr"
                        }).eq("id", doc_id).execute()
                        
                        # Send progress update
                        await websocket_manager.send_message(
                            batch_id,
                            {
                                "event_type": "batch_document_progress",
                                "data": {
                                    "batch_id": batch_id,
                                    "document_id": doc_id,
                                    "document_index": index + 1,
                                    "total_documents": total_docs,
                                    "status": "processing"
                                }
                            }
                        )
                        
                        # Process with OCR
                        extraction_result = await document_service.extract_text_with_ocr(
                            document["storage_path"],
                            document["file_type"],
                            contract_context=batch_context
                        )
                        
                        # Update document with results
                        db_client.table("documents").update({
                            "status": "processed",
                            "processing_results": extraction_result
                        }).eq("id", doc_id).execute()
                        
                        processed_docs += 1
                        
                        # Send document completion update
                        await websocket_manager.send_message(
                            batch_id,
                            {
                                "event_type": "batch_document_completed",
                                "data": {
                                    "batch_id": batch_id,
                                    "document_id": doc_id,
                                    "document_index": index + 1,
                                    "processed_count": processed_docs,
                                    "total_documents": total_docs,
                                    "extraction_confidence": extraction_result.get("extraction_confidence", 0.0),
                                    "character_count": extraction_result.get("character_count", 0)
                                }
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to process document {doc_id} in batch: {str(e)}")
                        
                        # Update document status to failed
                        db_client.table("documents").update({
                            "status": "ocr_failed",
                            "processing_results": {"error": str(e)}
                        }).eq("id", doc_id).execute()
                        
                        # Send error notification
                        await websocket_manager.send_message(
                            batch_id,
                            {
                                "event_type": "batch_document_failed",
                                "data": {
                                    "batch_id": batch_id,
                                    "document_id": doc_id,
                                    "error_message": str(e)
                                }
                            }
                        )
            
            # Execute parallel processing
            tasks = [process_single_doc(doc_id, i) for i, doc_id in enumerate(document_ids)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        else:
            # Sequential processing
            for i, doc_id in enumerate(document_ids):
                try:
                    # Get document details
                    doc_result = (
                        db_client.table("documents")
                        .select("*")
                        .eq("id", doc_id)
                        .execute()
                    )
                    
                    if not doc_result.data:
                        continue
                    
                    document = doc_result.data[0]
                    
                    # Update document status
                    db_client.table("documents").update({
                        "status": "processing_ocr"
                    }).eq("id", doc_id).execute()
                    
                    # Process with OCR
                    extraction_result = await document_service.extract_text_with_ocr(
                        document["storage_path"],
                        document["file_type"],
                        contract_context=batch_context
                    )
                    
                    # Update document with results
                    db_client.table("documents").update({
                        "status": "processed",
                        "processing_results": extraction_result
                    }).eq("id", doc_id).execute()
                    
                    processed_docs += 1
                    
                    # Send progress update
                    await websocket_manager.send_message(
                        batch_id,
                        {
                            "event_type": "batch_progress",
                            "data": {
                                "batch_id": batch_id,
                                "processed_count": processed_docs,
                                "total_documents": total_docs,
                                "progress_percent": int((processed_docs / total_docs) * 100)
                            }
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process document {doc_id}: {str(e)}")
                    continue
        
        processing_time = time.time() - start_time
        
        # Send batch completion notification
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_completed",
                "data": {
                    "batch_id": batch_id,
                    "processed_documents": processed_docs,
                    "total_documents": total_docs,
                    "processing_time_seconds": processing_time,
                    "success_rate": (processed_docs / total_docs) * 100 if total_docs > 0 else 0
                }
            }
        )
        
        logger.info(f"Batch OCR processing completed: {processed_docs}/{total_docs} documents")
        
    except Exception as e:
        logger.error(f"Batch OCR processing failed: {str(e)}")
        
        # Send batch error notification
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_failed",
                "data": {
                    "batch_id": batch_id,
                    "error_message": str(e),
                    "processed_documents": processed_docs,
                    "total_documents": total_docs
                }
            }
        )


async def generate_pdf_report(analysis_data: Dict[str, Any]) -> bytes:
    """Generate PDF report from analysis data"""
    # Placeholder - would implement with reportlab or similar
    return b"PDF report content"


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
