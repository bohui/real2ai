"""
Real2.AI FastAPI Backend - Refactored
Australian Real Estate AI Assistant
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
import os
import logging
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import application modules
from app.models.contract_state import RealEstateAgentState, create_initial_state
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.core.config import get_settings
from app.core.database import get_database_client
from app.services.document_service import DocumentService
from app.services.websocket_service import WebSocketManager

# Import routers
from app.router.auth import router as auth_router
from app.router.documents import router as documents_router
from app.router.contracts import router as contracts_router
from app.router.users import router as users_router
from app.router.onboarding import router as onboarding_router
from app.router.ocr import router as ocr_router
from app.router.health import router as health_router

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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3100",
        "https://real2.ai",
        "https://*.real2.ai",
    ],
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

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(contracts_router)
app.include_router(users_router)
app.include_router(onboarding_router)
app.include_router(ocr_router)


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


# Import background tasks
from app.tasks.background_tasks import (
    process_document_background,
    analyze_contract_background,
    enhanced_reprocess_document_with_ocr_background,
    batch_ocr_processing_background,
    generate_pdf_report,
)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
