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
from datetime import datetime

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
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
    }


# Authentication Endpoints


@app.post("/api/auth/register")
async def register_user(user_data: UserRegistrationRequest):
    """Register a new user"""
    try:
        # Create user in Supabase
        user_result = await db_client.auth.sign_up(
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
            }

            await db_client.table("profiles").insert(profile_data).execute()

            return {
                "user_id": user_result.user.id,
                "email": user_data.email,
                "message": "User registered successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login_user(login_data: UserLoginRequest):
    """Authenticate user"""
    try:
        auth_result = await db_client.auth.sign_in_with_password(
            {"email": login_data.email, "password": login_data.password}
        )

        if auth_result.user and auth_result.session:
            # Get user profile
            profile_result = (
                await db_client.table("profiles")
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

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


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
        if file_extension not in settings.allowed_file_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_file_types)}",
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

        await db_client.table("documents").insert(document_data).execute()

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

    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str, user: User = Depends(get_current_user)):
    """Get document details"""

    try:
        result = (
            await db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        return result.data[0]

    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Contract Analysis Endpoints


@app.post("/api/contracts/analyze", response_model=ContractAnalysisResponse)
async def start_contract_analysis(
    request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
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
            await db_client.table("documents")
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
            await db_client.table("contracts").insert(contract_data).execute()
        )
        contract_id = contract_result.data[0]["id"]

        # Create analysis record
        analysis_data = {
            "contract_id": contract_id,
            "agent_version": "1.0",
            "status": "pending",
        }

        analysis_result = (
            await db_client.table("contract_analyses").insert(analysis_data).execute()
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

    except Exception as e:
        logger.error(f"Contract analysis error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/contracts/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str, user: User = Depends(get_current_user)
):
    """Get contract analysis results"""

    try:
        # Get analysis results
        result = (
            await db_client.table("contract_analyses")
            .select("*")
            .eq("contract_id", contract_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Analysis not found")

        analysis = result.data[0]

        # Verify user owns this contract
        contract_result = (
            await db_client.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )
        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = contract_result.data[0]
        doc_result = (
            await db_client.table("documents")
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

    except Exception as e:
        logger.error(f"Get analysis error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/contracts/{contract_id}/report")
async def download_analysis_report(
    contract_id: str, format: str = "pdf", user: User = Depends(get_current_user)
):
    """Download analysis report"""

    try:
        # Get analysis data
        analysis_data = await get_contract_analysis(contract_id, user)

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
    return user.dict()


@app.put("/api/users/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any], user: User = Depends(get_current_user)
):
    """Update user preferences"""

    try:
        await db_client.table("profiles").update({"preferences": preferences}).eq(
            "id", user.id
        ).execute()
        return {"message": "Preferences updated successfully"}

    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users/usage-stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    """Get user usage statistics"""

    try:
        # Get usage logs
        usage_result = (
            await db_client.table("usage_logs")
            .select("*")
            .eq("user_id", user.id)
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

        # Get contract count
        contracts_result = (
            await db_client.from_("documents")
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


# Background Tasks


async def process_document_background(
    document_id: str,
    user_id: str,
    australian_state: AustralianState,
    contract_type: ContractType,
):
    """Background task for document processing"""

    try:
        # Update document status
        await db_client.table("documents").update({"status": "processing"}).eq(
            "id", document_id
        ).execute()

        # Get document metadata
        doc_result = (
            await db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )
        if not doc_result.data:
            raise Exception("Document not found")

        document = doc_result.data[0]

        # Extract text from document
        extraction_result = await document_service.extract_text(
            document["storage_path"], document["file_type"]
        )

        # Update document with extraction results
        await db_client.table("documents").update(
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
        await db_client.table("documents").update(
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
        await db_client.table("contract_analyses").update({"status": "processing"}).eq(
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
            await db_client.table("profiles").select("*").eq("id", user_id).execute()
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

        if not extracted_text:
            # If no extracted text, try to extract it now
            extraction_result = await document_service.extract_text(
                document["storage_path"], document["file_type"]
            )
            extracted_text = extraction_result.get("extracted_text", "")

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

        await db_client.table("contract_analyses").update(
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
            await db_client.table("profiles").update(
                {"credits_remaining": new_credits}
            ).eq("id", user_id).execute()

        # Log usage
        await db_client.table("usage_logs").insert(
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
        await db_client.table("contract_analyses").update({"status": "failed"}).eq(
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
