"""Health check and WebSocket router."""

from fastapi import APIRouter
from datetime import datetime, timezone
import logging

from app.core.config import get_settings

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
