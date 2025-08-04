"""Health check and WebSocket router."""

from fastapi import APIRouter, WebSocket
from datetime import datetime, timezone
import asyncio
import logging

from app.core.config import get_settings
from app.services.websocket_service import WebSocketManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Initialize services
settings = get_settings()
websocket_manager = WebSocketManager()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
    }


@router.websocket("/ws/contracts/{contract_id}/progress")
async def websocket_endpoint(websocket: WebSocket, contract_id: str):
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