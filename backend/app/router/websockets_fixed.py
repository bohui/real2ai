"""WebSocket router with proper ASGI compliance - ARCHITECTURAL REFERENCE"""

import json
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, UTC

from app.core.auth import get_current_user_ws
from app.services.websocket_service import WebSocketManager, WebSocketEvents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websockets"])

websocket_manager = WebSocketManager()


@router.websocket("/contracts/{contract_id}")
async def contract_analysis_websocket(
    websocket: WebSocket,
    contract_id: str,
    token: str = Query(..., description="Authentication token"),
):
    """
    ASGI-Compliant WebSocket endpoint for real-time contract analysis updates.
    
    Proper ASGI WebSocket lifecycle:
    1. ALWAYS accept() first (required by ASGI protocol)
    2. Authenticate after accepting
    3. Close with proper error codes if auth fails
    4. Handle messages in connected state
    """
    
    user = None
    
    try:
        # STEP 1: ALWAYS accept the WebSocket connection first (ASGI requirement)
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for contract {contract_id}")
        
        # STEP 2: Authenticate AFTER accepting (security check)
        user = await get_current_user_ws(token)
        if not user:
            logger.error(f"WebSocket authentication failed for contract {contract_id}")
            
            # Send error message before closing (now we can send because it's accepted)
            await websocket.send_text(json.dumps({
                "event_type": "authentication_error",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "error": "Authentication failed",
                    "code": 4001,
                    "message": "Invalid or missing authentication token"
                }
            }))
            
            # Now we can safely close (WebSocket is in CONNECTED state)
            await websocket.close(code=4001, reason="Authentication failed")
            return

        logger.info(f"Authentication successful for contract {contract_id} by user {user.id}")

        # STEP 3: Register with connection manager (connection is accepted and authenticated)
        await websocket_manager.connect(
            websocket,
            contract_id,
            metadata={
                "user_id": str(user.id),
                "contract_id": contract_id,
                "connected_at": datetime.now(UTC).isoformat(),
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

        # STEP 4: Handle client messages in message loop
        await handle_websocket_messages(websocket, contract_id, user.id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for contract {contract_id}")
    except Exception as e:
        logger.error(f"WebSocket error for contract {contract_id}: {str(e)}")
        try:
            # Safe error handling - only close if not already closed
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=4000, reason="Internal server error")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket: {str(close_error)}")
    finally:
        # Cleanup - disconnect from manager
        if user:  # Only cleanup if we had a successful authentication
            websocket_manager.disconnect(websocket, contract_id)
            logger.info(f"WebSocket cleanup completed for contract {contract_id}")


async def handle_websocket_messages(websocket: WebSocket, contract_id: str, user_id: str):
    """
    Handle WebSocket messages in a separate function for better separation of concerns.
    This ensures the main WebSocket handler focuses on connection lifecycle.
    """
    try:
        while True:
            # Wait for client messages (heartbeat, commands, etc.)
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
                await handle_client_message(websocket, contract_id, user_id, data)
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
        # Normal disconnection - let it bubble up
        raise
    except Exception as e:
        logger.error(f"Error handling WebSocket messages: {str(e)}")
        raise


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
        await handle_status_request(websocket, contract_id, user_id)

    elif message_type == "cancel_analysis":
        # Handle analysis cancellation request
        await handle_cancellation_request(websocket, contract_id, user_id)

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


async def handle_status_request(websocket: WebSocket, contract_id: str, user_id: str):
    """Handle status request with proper error handling."""
    from app.core.database import get_service_database_client

    try:
        db_client = get_service_database_client()
        await db_client.initialize()

        # Get detailed progress from analysis_progress table
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
                    "estimated_completion_minutes": progress["estimated_completion_minutes"],
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
                        "progress_percent": get_progress_from_status(analysis["status"]),
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

        await websocket_manager.send_personal_message(contract_id, websocket, status_message)

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


async def handle_cancellation_request(websocket: WebSocket, contract_id: str, user_id: str):
    """Handle analysis cancellation request."""
    logger.info(f"Analysis cancellation requested for contract {contract_id} by user {user_id}")

    # TODO: Implement actual cancellation logic
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
async def get_contract_connection_info(contract_id: str, user=None):
    """Get WebSocket connection information for a contract."""
    if not user:
        return {"error": "Authentication required"}

    info = websocket_manager.get_session_info(contract_id)
    return {
        "contract_id": contract_id,
        "connection_info": info,
        "timestamp": datetime.now(UTC).isoformat(),
    }