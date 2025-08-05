"""WebSocket router for real-time contract analysis updates."""

import json
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security import HTTPBearer
from datetime import datetime, UTC

from app.core.auth import get_current_user_ws
from app.services.websocket_service import WebSocketManager, WebSocketEvents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websockets"])

# Global WebSocket manager instance
websocket_manager = WebSocketManager()


@router.websocket("/contracts/{contract_id}")
async def contract_analysis_websocket(
    websocket: WebSocket,
    contract_id: str,
    token: str = Query(..., description="Authentication token"),
):
    """
    WebSocket endpoint for real-time contract analysis updates.

    ASGI-compliant WebSocket lifecycle: accept → authenticate → connect → handle messages
    This prevents ASGI protocol violations by accepting before any close operations.
    """
    
    user = None
    connection_established = False
    authenticated = False

    try:
        # Step 1: Log connection attempt
        logger.info(f"WebSocket connection requested for contract {contract_id} by user token")
        
        # Step 2: ACCEPT FIRST (required by ASGI protocol)
        # Must accept before any other operations to establish proper ASGI state
        await websocket.accept()
        logger.info("WebSocket connection accepted, proceeding with authentication")
        connection_established = True

        # Step 3: Authenticate AFTER accepting (ASGI compliant)
        try:
            user = await get_current_user_ws(token)
            if not user:
                logger.error(f"WebSocket authentication failed for contract {contract_id}")
                await websocket.close(code=4001, reason="Authentication failed")
                return
            
            authenticated = True
            logger.info(
                f"WebSocket authentication successful for contract {contract_id} by user {user.id}"
            )
        except Exception as auth_error:
            logger.error(f"WebSocket authentication error for contract {contract_id}: {str(auth_error)}")
            await websocket.close(code=4001, reason="Authentication failed")
            return

        # Step 4: Register with connection manager (websocket accepted and authenticated)
        await websocket_manager.connect(
            websocket,
            contract_id,
            metadata={
                "user_id": str(user.id),
                "contract_id": contract_id,
                "connected_at": datetime.now(UTC).isoformat(),
                "authenticated": True,
            },
        )

        # Send initial connection confirmation
        await websocket_manager.send_personal_message(
            contract_id,
            websocket,
            {
                "event_type": "connection_established",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "user_id": str(user.id),
                    "message": "Connected to contract analysis updates",
                },
            },
        )

        # Keep connection alive and handle client messages
        try:
            while True:
                # Wait for client messages (heartbeat, commands, etc.)
                message = await websocket.receive_text()

                try:
                    data = json.loads(message)
                    await handle_client_message(websocket, contract_id, user.id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from client: {message}")
                    await websocket_manager.send_personal_message(
                        contract_id,
                        websocket,
                        {
                            "event_type": "error",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "data": {
                                "message": "Invalid message format",
                                "expected": "JSON",
                            },
                        },
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for contract {contract_id}")

    except Exception as e:
        logger.error(f"WebSocket error for contract {contract_id}: {str(e)}")
        # Only attempt to close if connection was properly established and authenticated
        if connection_established and authenticated:
            try:
                await websocket.close(code=4000, reason="Internal server error")
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
        elif connection_established:
            # Connection accepted but not authenticated - close with auth error
            try:
                await websocket.close(code=4001, reason="Authentication required")
            except Exception as close_error:
                logger.error(f"Error closing unauthenticated WebSocket: {str(close_error)}")

    finally:
        # Cleanup - only register/disconnect if properly authenticated
        if connection_established and authenticated and user:
            websocket_manager.disconnect(websocket, contract_id)
            logger.info(f"WebSocket cleanup completed for contract {contract_id}")
        else:
            logger.info(f"WebSocket cleanup skipped - connection not fully established for contract {contract_id}")


async def handle_client_message(
    websocket: WebSocket, contract_id: str, user_id: str, data: Dict[str, Any]
):
    """Handle messages received from WebSocket clients."""

    message_type = data.get("type")

    if message_type == "heartbeat":
        # Respond to heartbeat
        await websocket_manager.send_personal_message(
            contract_id, websocket, WebSocketEvents.heartbeat()
        )

    elif message_type == "get_status":
        # Request current analysis status
        from app.core.database import get_service_database_client

        try:
            db_client = get_service_database_client()
            await db_client.initialize()

            # First try to get detailed progress from analysis_progress table
            progress_result = (
                db_client.table("analysis_progress")
                .select("*")
                .eq("contract_id", contract_id)
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

            if progress_result.data:
                progress = progress_result.data[0]
                status_message = {
                    "event_type": "analysis_progress",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "contract_id": contract_id,
                        "current_step": progress["current_step"],
                        "progress_percent": progress["progress_percent"],
                        "step_description": progress["step_description"],
                        "status": progress["status"],
                        "estimated_completion_minutes": progress[
                            "estimated_completion_minutes"
                        ],
                        "last_updated": progress["updated_at"],
                        "total_elapsed_seconds": progress["total_elapsed_seconds"],
                    },
                }
            else:
                # Fallback to contract_analyses table
                analysis_result = (
                    db_client.table("contract_analyses")
                    .select("*")
                    .eq("contract_id", contract_id)
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if analysis_result.data:
                    analysis = analysis_result.data[0]
                    status_message = {
                        "event_type": "status_update",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": {
                            "contract_id": contract_id,
                            "status": analysis["status"],
                            "progress_percent": get_progress_from_status(
                                analysis["status"]
                            ),
                            "last_updated": analysis["updated_at"],
                        },
                    }
                else:
                    status_message = {
                        "event_type": "status_update",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": {
                            "contract_id": contract_id,
                            "status": "not_found",
                            "message": "No analysis found for this contract",
                        },
                    }

            await websocket_manager.send_personal_message(
                contract_id, websocket, status_message
            )

        except Exception as e:
            logger.error(f"Error getting analysis status: {str(e)}")
            await websocket_manager.send_personal_message(
                contract_id,
                websocket,
                {
                    "event_type": "error",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "message": "Failed to get analysis status",
                        "error": str(e),
                    },
                },
            )

    elif message_type == "cancel_analysis":
        # Handle analysis cancellation request
        logger.info(
            f"Analysis cancellation requested for contract {contract_id} by user {user_id}"
        )

        # TODO: Implement cancellation logic
        await websocket_manager.send_personal_message(
            contract_id,
            websocket,
            {
                "event_type": "cancellation_received",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "message": "Cancellation request received",
                    "note": "Analysis will stop at the next checkpoint",
                },
            },
        )

    else:
        logger.warning(f"Unknown message type received: {message_type}")
        await websocket_manager.send_personal_message(
            contract_id,
            websocket,
            {
                "event_type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "message": f"Unknown message type: {message_type}",
                    "supported_types": ["heartbeat", "get_status", "cancel_analysis"],
                },
            },
        )


def get_progress_from_status(status: str) -> int:
    """Convert analysis status to progress percentage."""
    status_progress_map = {
        "pending": 0,
        "processing": 50,
        "completed": 100,
        "failed": 0,
        "cancelled": 0,
    }
    return status_progress_map.get(status, 0)


# Health check endpoint for WebSocket connections
@router.get("/health")
async def websocket_health():
    """Get WebSocket service health information."""
    return {
        "status": "healthy",
        "active_sessions": websocket_manager.get_session_count(),
        "total_connections": websocket_manager.get_total_connections(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Get connection info for a specific contract
@router.get("/contracts/{contract_id}/info")
async def get_contract_connection_info(
    contract_id: str, user=Depends(get_current_user_ws)
):
    """Get WebSocket connection information for a contract."""
    if not user:
        return {"error": "Authentication required"}

    info = websocket_manager.get_session_info(contract_id)
    return {
        "contract_id": contract_id,
        "connection_info": info,
        "timestamp": datetime.now(UTC).isoformat(),
    }
