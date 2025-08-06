"""
Real2.AI FastAPI Backend - Refactored
Australian Real Estate AI Assistant
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
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
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status

# Import routers
from app.router.auth import router as auth_router
from app.router.documents import router as documents_router
from app.router.contracts import router as contracts_router
from app.router.users import router as users_router
from app.router.onboarding import router as onboarding_router
from app.router.ocr import router as ocr_router
from app.router.health import router as health_router
from app.router.websockets import router as websockets_router
from app.router.property_profile import router as property_profile_router

# Initialize services
settings = get_settings()
security = HTTPBearer()
db_client = get_database_client()
document_service = DocumentService()
websocket_manager = WebSocketManager()

# Initialize LangGraph workflow (will be initialized in lifespan)
contract_workflow = ContractAnalysisWorkflow(
    model_name="gpt-4",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Real2.AI API...")

    # Initialize LangSmith tracing
    langsmith_enabled = initialize_langsmith()
    if langsmith_enabled:
        status = get_langsmith_status()
        logger.info(f"LangSmith tracing enabled for project: {status['project_name']}")
    else:
        logger.info("LangSmith tracing disabled")

    # Initialize database connection
    await db_client.initialize()

    # Initialize document service
    await document_service.initialize()

    # Initialize contract workflow
    await contract_workflow.initialize()

    logger.info("Real2.AI API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Real2.AI API...")

    # Close database connections
    await db_client.close()

    # Close websocket connections
    await websocket_manager.disconnect_all()

    logger.info("Real2.AI API shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Real2.AI API",
    description="Australian Real Estate AI Assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
# Get allowed origins from environment variable or use defaults
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3100,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:3100,http://127.0.0.1:5173",
).split(",")

# Add production origins if configured
if os.getenv("ENVIRONMENT") == "production":
    production_origins = [
        "https://real2.ai",
        "https://www.real2.ai",
        "https://app.real2.ai",
    ]
    allowed_origins.extend(production_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
    ],
    expose_headers=["Content-Length", "Content-Type", "Authorization"],
    max_age=3600,  # Cache preflight responses for 1 hour
)


# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(contracts_router)
app.include_router(users_router)
app.include_router(onboarding_router)
app.include_router(ocr_router)
app.include_router(websockets_router)
app.include_router(property_profile_router)


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
