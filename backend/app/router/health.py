"""Health check and WebSocket router."""

from fastapi import APIRouter
from datetime import datetime, timezone
import logging

from app.core.config import get_settings
from app.core.langsmith_init import get_langsmith_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Initialize services
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
    }


@router.get("/health/langsmith")
async def langsmith_health_check():
    """LangSmith health check endpoint"""
    langsmith_status = get_langsmith_status()
    
    return {
        "status": "healthy" if langsmith_status.get("enabled", False) else "disabled",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "langsmith": langsmith_status,
    }
