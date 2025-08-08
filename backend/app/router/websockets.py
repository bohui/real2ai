"""WebSocket router with proper ASGI compliance and user-aware architecture"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, UTC, timedelta

from app.core.auth import get_current_user_ws, verify_ws_token, get_user_by_id_service
from app.core.auth_context import AuthContext
from app.services.websocket_service import WebSocketEvents
from app.services.websocket_singleton import websocket_manager
from app.services.redis_pubsub import redis_pubsub_service
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.clients.factory import get_service_supabase_client
from enum import Enum


class CacheStatus(str, Enum):
    COMPLETE = "complete"  # ✅ Analysis results ready
    IN_PROGRESS = "in_progress"  # 🔄 Currently analyzing
    FAILED = "failed"  # ❌ Previous attempt failed
    MISS = "miss"  # 🆕 First time seeing this document


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websockets"])

# Use global singleton manager to ensure background tasks and router share sessions
# See app/services/websocket_singleton.py


async def check_document_cache_status(document_id: str, user_id: str) -> Dict[str, Any]:
    """
    Check cache status for a document and return comprehensive status info.

    Returns:
    - cache_status: COMPLETE | IN_PROGRESS | FAILED | MISS
    - document_id: Original document ID
    - content_hash: Document content hash for caching
    - contract_id: Associated contract ID (if exists)
    - analysis_result: Full analysis (if COMPLETE)
    - progress: Current progress info (if IN_PROGRESS)
    - error_message: Error details (if FAILED)
    - retry_available: Whether retry is possible
    """

    try:
        # Get authenticated client
        user_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get document with user context (RLS enforced)
        doc_result = await user_client.database.select(
            "documents", columns="*", filters={"id": document_id, "user_id": user_id}
        )

        if not doc_result.get("data"):
            raise ValueError(f"Document {document_id} not found or access denied")

        document = doc_result["data"][0]
        content_hash = document.get(
            "content_hash"
        ) or _generate_content_hash_from_document(document)

        logger.info(
            f"Checking cache for document {document_id} with content_hash: {content_hash}"
        )

        # Check existing contract with this content_hash using service role (shared resource)
        service_client = await get_service_supabase_client()
        contract_result = await service_client.database.select(
            "contracts",
            columns="*",
            filters={"content_hash": content_hash},
            order_by="created_at DESC",
            limit=1,
        )

        if not contract_result.get("data"):
            # CACHE MISS - First time seeing this document
            logger.info(
                f"Cache MISS: No existing contract found for content_hash {content_hash}"
            )
            return {
                "cache_status": CacheStatus.MISS,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": None,
                "retry_available": False,
                "message": "New document - analysis will start shortly",
            }

        contract = contract_result["data"][0]
        contract_id = contract["id"]

        # Check analysis status using service role (shared resource)
        analysis_result = await service_client.database.select(
            "contract_analyses",
            columns="*",
            filters={"content_hash": content_hash},
            order_by="created_at DESC",
            limit=1,
        )

        if not analysis_result.get("data"):
            # Contract exists but no analysis - should not happen but handle gracefully
            logger.warning(
                f"Contract {contract_id} exists but no analysis found - treating as MISS"
            )
            return {
                "cache_status": CacheStatus.MISS,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "retry_available": False,
                "message": "Existing contract found but no analysis - will start analysis",
            }

        analysis = analysis_result["data"][0]
        analysis_status = analysis["status"]

        if analysis_status == "completed":
            # CACHE HIT COMPLETE - Results ready!
            logger.info(
                f"Cache HIT COMPLETE: Analysis ready for contract {contract_id}"
            )
            return {
                "cache_status": CacheStatus.COMPLETE,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "analysis_id": analysis["id"],
                "analysis_result": analysis.get("analysis_result", {}),
                "processing_time": analysis.get("processing_time"),
                "retry_available": False,
                "message": "Analysis complete - results available instantly!",
            }

        elif analysis_status in ["pending", "queued", "processing"]:
            # CACHE HIT IN PROGRESS - Join existing analysis
            logger.info(
                f"Cache HIT IN_PROGRESS: Analysis ongoing for contract {contract_id}"
            )

            # Get detailed progress if available
            progress_result = await user_client.database.select(
                "analysis_progress",
                columns="*",
                filters={"content_hash": content_hash, "user_id": user_id},
                order_by="updated_at DESC",
                limit=1,
            )

            progress_info = None
            if progress_result.get("data"):
                progress = progress_result["data"][0]
                progress_info = {
                    "current_step": progress["current_step"],
                    "progress_percent": progress["progress_percent"],
                    "step_description": progress["step_description"],
                    "estimated_completion_minutes": progress.get(
                        "estimated_completion_minutes"
                    ),
                }

            return {
                "cache_status": CacheStatus.IN_PROGRESS,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "analysis_id": analysis["id"],
                "progress": progress_info,
                "retry_available": False,
                "message": "Analysis in progress - joining existing process",
            }

        elif analysis_status in ["failed", "cancelled"]:
            # CACHE HIT FAILED - Previous attempt failed
            logger.info(
                f"Cache HIT FAILED: Previous analysis failed for contract {contract_id}"
            )
            return {
                "cache_status": CacheStatus.FAILED,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "analysis_id": analysis["id"],
                "error_message": analysis.get("error_message", "Analysis failed"),
                "retry_available": True,
                "message": "Previous analysis failed - retry available",
            }

        else:
            # Unknown status - treat as failed
            logger.warning(
                f"Unknown analysis status '{analysis_status}' for contract {contract_id}"
            )
            return {
                "cache_status": CacheStatus.FAILED,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "analysis_id": analysis["id"],
                "error_message": f"Unknown status: {analysis_status}",
                "retry_available": True,
                "message": "Analysis in unknown state - retry recommended",
            }

    except Exception as e:
        logger.error(
            f"Error checking cache status for document {document_id}: {str(e)}"
        )
        return {
            "cache_status": CacheStatus.MISS,
            "document_id": document_id,
            "content_hash": None,
            "contract_id": None,
            "error_message": f"Cache check failed: {str(e)}",
            "retry_available": False,
            "message": "Cache check failed - will attempt new analysis",
        }


def _generate_content_hash_from_document(document: Dict[str, Any]) -> str:
    """
    Generate content hash from document metadata if not present.
    """
    import hashlib

    # Try to get hash from document record first
    if document.get("content_hash"):
        return document["content_hash"]

    # If document has processing results with text, hash that
    processing_results = document.get("processing_results", {})
    text_extraction = processing_results.get("text_extraction", {})
    full_text = text_extraction.get("full_text", "")

    if full_text:
        content_bytes = full_text.encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    # Fallback: create hash from document metadata
    metadata = f"{document.get('original_filename', '')}{document.get('file_size', 0)}{document.get('created_at', '')}"
    return hashlib.sha256(metadata.encode("utf-8")).hexdigest()


@router.websocket("/documents/{document_id}")
async def document_analysis_websocket(
    websocket: WebSocket,
    document_id: str,
    token: str = Query(..., description="Short-lived server-signed WS token"),
):
    """
    ASGI-Compliant WebSocket endpoint for real-time document analysis updates.

    This endpoint provides intelligent cache-aware analysis:
    1. ALWAYS accept() first (required by ASGI protocol)
    2. Authenticate after accepting
    3. Check cache status for document content_hash
    4. Handle different cache states: complete, in_progress, failed, miss
    5. Stream real-time updates or provide instant results
    """

    user = None
    subscription_created = False

    try:
        # STEP 1: ALWAYS accept the WebSocket connection first (ASGI requirement)
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for document {document_id}")

        # STEP 2: Authenticate AFTER accepting (security check)
        # Prefer hardened short-lived token; fall back to legacy if needed
        ws_user_id = verify_ws_token(token)
        if ws_user_id:
            user = await get_user_by_id_service(ws_user_id)
        else:
            user = await get_current_user_ws(token)
        if not user:
            logger.error(f"WebSocket authentication failed for document {document_id}")

            # Send error message before closing (now we can send because it's accepted)
            await websocket.send_text(
                json.dumps(
                    {
                        "event_type": "authentication_error",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": {
                            "error": "Authentication failed",
                            "code": 4001,
                            "message": "Invalid or missing authentication token",
                        },
                    }
                )
            )

            # Now we can safely close (WebSocket is in CONNECTED state)
            await websocket.close(code=4001, reason="Authentication failed")
            return

        logger.info(
            f"Authentication successful for document {document_id} by user {user.id}"
        )

        # STEP 2.5: Set authentication context for the WebSocket connection
        # Do not store the WS token as Supabase token in context
        AuthContext.set_auth_context(
            token="",
            user_id=str(user.id),
            user_email=user.email,
            metadata={
                "websocket_document_id": document_id,
                "connection_type": "websocket",
                "connected_at": datetime.now(UTC).isoformat(),
            },
        )
        logger.debug(f"Auth context set for WebSocket user: {user.id}")

        # STEP 3: Check cache status and get document info
        cache_status_result = await check_document_cache_status(
            document_id, str(user.id)
        )
        logger.info(
            f"Cache status for document {document_id}: {cache_status_result['cache_status']}"
        )

        # STEP 4: Register with connection manager (connection is accepted and authenticated)
        await websocket_manager.connect(
            websocket,
            document_id,  # Use document_id as session key
            metadata={
                "user_id": str(user.id),
                "document_id": document_id,
                "contract_id": cache_status_result.get("contract_id"),
                "cache_status": cache_status_result["cache_status"],
                "connected_at": datetime.now(UTC).isoformat(),
            },
        )

        # Bridge Redis pub/sub updates to this session if not already subscribed
        if document_id not in getattr(redis_pubsub_service, "subscriptions", {}):

            async def _forward_pubsub_message(message: Dict[str, Any]):
                try:
                    await websocket_manager.send_message(document_id, message)
                except Exception as forward_error:
                    logger.error(f"Failed to forward pub/sub message: {forward_error}")

            try:
                await redis_pubsub_service.initialize()
                await redis_pubsub_service.subscribe_to_progress(
                    document_id, _forward_pubsub_message
                )
                subscription_created = True
                logger.info(
                    f"Redis subscription created for document session {document_id}"
                )
            except Exception as sub_error:
                logger.warning(
                    f"Could not subscribe to Redis channel for {document_id}: {sub_error}"
                )

        # Also subscribe to contract_id and content_hash channels to bridge legacy publishers
        try:
            contract_id = cache_status_result.get("contract_id")
            if contract_id and contract_id not in redis_pubsub_service.subscriptions:

                async def _forward_from_contract(message: Dict[str, Any]):
                    try:
                        await websocket_manager.send_message(document_id, message)
                    except Exception as forward_error:
                        logger.error(
                            f"Failed to forward contract pub/sub message: {forward_error}"
                        )

                await redis_pubsub_service.subscribe_to_progress(
                    contract_id, _forward_from_contract
                )

            content_hash = cache_status_result.get("content_hash")
            if content_hash and content_hash not in redis_pubsub_service.subscriptions:

                async def _forward_from_hash(message: Dict[str, Any]):
                    try:
                        await websocket_manager.send_message(document_id, message)
                    except Exception as forward_error:
                        logger.error(
                            f"Failed to forward hash pub/sub message: {forward_error}"
                        )

                await redis_pubsub_service.subscribe_to_progress(
                    content_hash, _forward_from_hash
                )
        except Exception as extra_sub_error:
            logger.warning(
                f"Failed to subscribe to additional channels: {extra_sub_error}"
            )

        # Send cache status and connection confirmation
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "cache_status",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": cache_status_result,
            },
        )

        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "connection_established",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "document_id": document_id,
                    "contract_id": cache_status_result.get("contract_id"),
                    "user_id": str(user.id),
                    "cache_status": cache_status_result["cache_status"],
                    "message": "Connected to document analysis updates",
                },
            },
        )

        # Send document_uploaded notification if this is a recent upload
        try:
            # Check if document was recently uploaded (within last 5 minutes)
            from app.services.websocket_service import WebSocketEvents

            # Get document details to check upload time
            user_client = await AuthContext.get_authenticated_client()
            doc_result = await user_client.database.select(
                "documents",
                columns="*",
                filters={"id": document_id, "user_id": str(user.id)},
            )

            if doc_result.get("data"):
                document = doc_result["data"][0]
                created_at = document.get("created_at")

                if created_at:
                    # Check if document was created within last 5 minutes
                    created_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)

                    if created_time > five_minutes_ago:
                        # Send document_uploaded notification
                        await websocket_manager.send_personal_message(
                            document_id,
                            websocket,
                            WebSocketEvents.document_uploaded(
                                document_id=document_id,
                                filename=document.get("filename", "Unknown"),
                                processing_status=document.get("status", "uploaded"),
                            ),
                        )
                        logger.info(
                            f"Sent document_uploaded notification for document {document_id}"
                        )

        except Exception as upload_notification_error:
            logger.warning(
                f"Failed to send document_uploaded notification: {str(upload_notification_error)}"
            )
            # Don't fail the connection if notification fails

        # STEP 5: Handle client messages in message loop
        await handle_websocket_messages(
            websocket, document_id, cache_status_result.get("contract_id"), user.id
        )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for document {document_id}")
    except Exception as e:
        # Create error context for WebSocket errors
        context = create_error_context(
            user_id=user.id if user else None,
            operation="websocket_connection",
            metadata={"document_id": document_id},
        )

        # Log enhanced error (but don't raise since this is WebSocket)
        try:
            handle_api_error(e, context, ErrorCategory.NETWORK)
        except Exception:
            # Just log the enhanced error, don't re-raise for WebSocket
            pass

        logger.error(f"WebSocket error for document {document_id}: {str(e)}")
        try:
            # Safe error handling - only close if not already closed
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=4000, reason="Internal server error")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket: {str(close_error)}")
    finally:
        # Cleanup - disconnect from manager and clear auth context
        if user:  # Only cleanup if we had a successful authentication
            websocket_manager.disconnect(websocket, document_id)
            logger.info(f"WebSocket cleanup completed for document {document_id}")

        # Note: We intentionally do not unsubscribe the Redis channel here to avoid
        # tearing down the shared subscription while other sockets for the same
        # document may still be connected. The subscription is maintained per
        # session id by redis_pubsub_service.

        # Always clear authentication context for WebSocket connections
        AuthContext.clear_auth_context()
        logger.debug("WebSocket authentication context cleared")


async def handle_websocket_messages(
    websocket: WebSocket, document_id: str, contract_id: Optional[str], user_id: str
):
    """
    Handle WebSocket messages for document-based analysis.
    Supports both document-level commands and contract-specific commands when available.
    """
    try:
        while True:
            # Wait for client messages (heartbeat, commands, etc.)
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
                await handle_client_message(
                    websocket, document_id, contract_id, user_id, data
                )
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client: {message}")
                await websocket_manager.send_personal_message(
                    document_id,
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
    websocket: WebSocket,
    document_id: str,
    contract_id: Optional[str],
    user_id: str,
    data: Dict[str, Any],
):
    """Handle messages received from WebSocket clients for document-based analysis."""

    message_type = data.get("type")

    logger.info(
        f"📨 Received WebSocket message: {message_type} for document {document_id}"
    )

    if message_type == "heartbeat":
        # Respond to heartbeat
        await websocket_manager.send_personal_message(
            document_id, websocket, WebSocketEvents.heartbeat()
        )

    elif message_type == "get_status":
        # Request current analysis status
        await handle_status_request(websocket, document_id, contract_id, user_id)

    elif message_type == "start_analysis":
        # Client wants to start analysis (for cache miss or retry scenarios)
        await handle_start_analysis_request(
            websocket, document_id, contract_id, user_id, data
        )

    elif message_type == "retry_analysis":
        # Client wants to retry failed analysis
        await handle_retry_analysis_request(
            websocket, document_id, contract_id, user_id, data
        )

    elif message_type == "cancel_analysis":
        # Handle analysis cancellation request
        await handle_cancellation_request(websocket, document_id, contract_id, user_id)

    else:
        logger.warning(f"Unknown message type received: {message_type}")
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "message": f"Unknown message type: {message_type}",
                    "supported_types": [
                        "heartbeat",
                        "get_status",
                        "start_analysis",
                        "retry_analysis",
                        "cancel_analysis",
                    ],
                },
            },
        )


async def handle_start_analysis_request(
    websocket: WebSocket,
    document_id: str,
    contract_id: Optional[str],
    user_id: str,
    data: Dict[str, Any],
):
    """Handle request to start new analysis and actually dispatch the task."""

    logger.info(f"🎆 Starting new analysis for document {document_id}")

    try:
        # Import here to avoid circular imports
        from app.tasks.background_tasks import comprehensive_document_analysis

        # Get analysis options from client
        analysis_options = data.get(
            "analysis_options",
            {
                "include_financial_analysis": True,
                "include_risk_assessment": True,
                "include_compliance_check": True,
                "include_recommendations": True,
            },
        )

        # Send initial acknowledgment
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "analysis_starting",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "document_id": document_id,
                    "contract_id": contract_id,
                    "message": "Analysis starting...",
                    "estimated_completion_minutes": 3,
                },
            },
        )

        # Actually dispatch the analysis task
        task_result = await _dispatch_analysis_task(
            document_id=document_id,
            contract_id=contract_id,
            user_id=user_id,
            analysis_options=analysis_options,
        )

        # Send success confirmation
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "analysis_dispatched",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "document_id": document_id,
                    "contract_id": task_result["contract_id"],
                    "analysis_id": task_result["analysis_id"],
                    "task_id": task_result["task_id"],
                    "message": "Analysis task dispatched successfully",
                },
            },
        )

        logger.info(
            f"Analysis task dispatched for document {document_id}, task ID: {task_result['task_id']}"
        )

    except Exception as e:
        logger.error(f"Error starting analysis for document {document_id}: {str(e)}")
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "message": "Failed to start analysis",
                    "error": str(e),
                },
            },
        )


async def handle_retry_analysis_request(
    websocket: WebSocket,
    document_id: str,
    contract_id: Optional[str],
    user_id: str,
    data: Dict[str, Any],
):
    """Handle request to retry failed analysis and actually dispatch the task."""

    logger.info(
        f"🔄 Retrying analysis for document {document_id}, contract {contract_id}"
    )

    try:
        if not contract_id:
            raise ValueError("Contract ID required for retry")

        # Get analysis options from client
        analysis_options = data.get(
            "analysis_options",
            {
                "include_financial_analysis": True,
                "include_risk_assessment": True,
                "include_compliance_check": True,
                "include_recommendations": True,
            },
        )

        # Send acknowledgment
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "analysis_retrying",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "document_id": document_id,
                    "contract_id": contract_id,
                    "message": "Retrying analysis...",
                    "retry_attempt": data.get("retry_attempt", 1),
                },
            },
        )

        # Get the content_hash for the contract to use in retry
        user_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get contract to find content_hash
        contract_result = await user_client.database.select(
            "contracts", columns="content_hash", filters={"id": contract_id}
        )

        if not contract_result.get("data"):
            raise ValueError("Contract not found")

        content_hash = contract_result["data"][0]["content_hash"]

        # Use the new retry function to safely handle existing analysis records
        retry_analysis_id = await user_client.database.execute_rpc(
            "retry_contract_analysis",
            {"p_content_hash": content_hash, "p_user_id": user_id},
        )

        if not retry_analysis_id:
            raise ValueError("Failed to retry analysis via database function")

        # Actually dispatch the retry task
        task_result = await _dispatch_analysis_task(
            document_id=document_id,
            contract_id=contract_id,
            user_id=user_id,
            analysis_options=analysis_options,
        )

        # Send success confirmation
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "analysis_retry_dispatched",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "document_id": document_id,
                    "contract_id": task_result["contract_id"],
                    "analysis_id": task_result["analysis_id"],
                    "task_id": task_result["task_id"],
                    "message": "Retry analysis task dispatched successfully",
                },
            },
        )

        logger.info(
            f"Retry analysis task dispatched for document {document_id}, task ID: {task_result['task_id']}"
        )

    except Exception as e:
        logger.error(f"Error retrying analysis for document {document_id}: {str(e)}")
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "message": "Failed to retry analysis",
                    "error": str(e),
                },
            },
        )


async def handle_status_request(
    websocket: WebSocket, document_id: str, contract_id: Optional[str], user_id: str
):
    """Handle status request with user context (RLS enforced)."""
    from app.core.auth_context import AuthContext

    try:
        # Check if contract_id is provided
        if not contract_id or contract_id == "None":
            # No contract_id means no analysis has been started yet
            status_message = {
                "event_type": "status_update",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": None,
                    "status": "not_started",
                    "message": "No analysis has been started for this document",
                    "progress_percent": 0,
                },
            }
            await websocket_manager.send_personal_message(
                document_id, websocket, status_message
            )
            return

        # Get user-authenticated client (respects RLS)
        user_client = await AuthContext.get_authenticated_client(require_auth=True)

        # First get the content_hash from the document
        doc_result = await user_client.database.select(
            "documents",
            columns="content_hash",
            filters={"id": document_id, "user_id": user_id},
        )

        if not doc_result.get("data"):
            raise ValueError(f"Document {document_id} not found or access denied")

        content_hash = doc_result["data"][0].get("content_hash")
        if not content_hash:
            raise ValueError(f"Document {document_id} has no content hash")

        # Get detailed progress from analysis_progress table (user context - RLS enforced)
        progress_result = await user_client.database.select(
            "analysis_progress",
            columns="*",
            filters={"content_hash": content_hash, "user_id": user_id},
            order_by="updated_at DESC",
            limit=1,
        )

        if progress_result.get("data"):
            progress = progress_result["data"][0]
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
            # Fallback to contract_analyses table (shared resource - no user filter)
            analysis_result = await user_client.database.select(
                "contract_analyses",
                columns="*",
                filters={"content_hash": content_hash},
                order_by="created_at DESC",
                limit=1,
            )

            if analysis_result.get("data"):
                analysis = analysis_result["data"][0]
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
            document_id, websocket, status_message
        )

    except Exception as e:
        logger.error(f"Error getting analysis status: {str(e)}")
        await websocket_manager.send_personal_message(
            document_id,
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


async def handle_cancellation_request(
    websocket: WebSocket, document_id: str, contract_id: Optional[str], user_id: str
):
    """Handle analysis cancellation request."""
    logger.info(
        f"Analysis cancellation requested for document {document_id}, contract {contract_id} by user {user_id}"
    )

    try:
        # Get authenticated client
        user_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get the content_hash from the document
        doc_result = await user_client.database.select(
            "documents",
            columns="content_hash",
            filters={"id": document_id, "user_id": user_id},
        )

        if not doc_result.get("data"):
            raise ValueError(f"Document {document_id} not found or access denied")

        content_hash = doc_result["data"][0].get("content_hash")

        # Find and update analysis_progress records that match the filters
        progress_records = await user_client.database.read(
            "analysis_progress",
            filters={
                "content_hash": content_hash,
                "user_id": user_id,
                "status": "in_progress",
            },
        )

        # Update each matching progress record
        for record in progress_records:
            await user_client.database.update(
                "analysis_progress",
                record["id"],
                {"status": "cancelled", "error_message": "Analysis cancelled by user"},
            )

        # Find and update contract_analyses records that match the filters
        analysis_records = await user_client.database.read(
            "contract_analyses",
            filters={"content_hash": content_hash, "status": "pending"},
        )

        # Update each matching analysis record
        for record in analysis_records:
            await user_client.database.update(
                "contract_analyses",
                record["id"],
                {"status": "cancelled", "error_details": {"cancelled_by_user": True}},
            )

        # Try to cancel the Celery task if we can find it
        try:
            from app.tasks.background_tasks import comprehensive_document_analysis
            from celery import Celery

            # Get all active tasks and try to revoke matching ones
            app = comprehensive_document_analysis.app
            active_tasks = app.control.inspect().active()

            cancelled_tasks = []
            if active_tasks:
                for worker, tasks in active_tasks.items():
                    for task in tasks:
                        if task.get(
                            "name"
                        ) == "app.tasks.background_tasks.comprehensive_document_analysis" and document_id in str(
                            task.get("args", [])
                        ):
                            # Revoke the task
                            app.control.revoke(task["id"], terminate=True)
                            cancelled_tasks.append(task["id"])
                            logger.info(
                                f"Cancelled Celery task {task['id']} for document {document_id}"
                            )

        except Exception as task_cancel_error:
            logger.warning(
                f"Could not cancel background task: {str(task_cancel_error)}"
            )
            # Continue with user notification even if task cancellation fails

        # Send success confirmation
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "analysis_cancelled",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "document_id": document_id,
                    "message": "Analysis successfully cancelled",
                    "status": "cancelled",
                    "cancelled_tasks": (
                        len(cancelled_tasks) if "cancelled_tasks" in locals() else 0
                    ),
                },
            },
        )

        logger.info(f"Successfully cancelled analysis for document {document_id}")

    except Exception as e:
        logger.error(f"Error cancelling analysis for document {document_id}: {str(e)}")

        # Send error response
        await websocket_manager.send_personal_message(
            document_id,
            websocket,
            {
                "event_type": "cancellation_failed",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "message": "Failed to cancel analysis",
                    "error": str(e),
                },
            },
        )


async def _dispatch_analysis_task(
    document_id: str,
    contract_id: Optional[str],
    user_id: str,
    analysis_options: Dict[str, Any],
) -> Dict[str, str]:
    """Helper function to dispatch analysis task with proper contract/analysis creation."""
    try:
        # Get authenticated client
        user_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get document record
        doc_result = await user_client.database.select(
            "documents", columns="*", filters={"id": document_id, "user_id": user_id}
        )

        if not doc_result.get("data"):
            raise ValueError(f"Document {document_id} not found or access denied")

        document = doc_result["data"][0]

        # Generate content hash for caching
        content_hash = await _generate_document_content_hash(document)

        # Create contract record if not provided
        if not contract_id:
            # Create new contract record
            contract_data = {
                "content_hash": content_hash,
                "contract_type": document.get("contract_type", "purchase_agreement"),
                "australian_state": document.get("australian_state", "NSW"),
            }

            contract_result = await user_client.database.insert(
                "contracts", contract_data
            )
            if not contract_result.get("success") or not contract_result.get("data"):
                raise ValueError("Failed to create contract record")

            contract_id = contract_result["data"]["id"]
            logger.info(f"Created new contract record: {contract_id}")

        # Create analysis record using upsert to handle duplicates
        try:
            # Use the new upsert function to handle duplicate content_hash gracefully
            analysis_id = await user_client.database.execute_rpc(
                "upsert_contract_analysis",
                {
                    "p_content_hash": content_hash,
                    "p_agent_version": "1.0",
                    "p_status": "pending",
                    "p_analysis_result": {},
                    "p_error_message": None,
                },
            )

            if not analysis_id:
                raise ValueError("Failed to create analysis record via upsert")

        except Exception as e:
            logger.error(f"Upsert failed for content_hash {content_hash}: {str(e)}")
            # Fallback to direct upsert with conflict handling
            analysis_data = {
                "content_hash": content_hash,
                "agent_version": "1.0",
                "status": "pending",
            }

            analysis_result = await user_client.database.upsert(
                "contract_analyses", analysis_data, conflict_columns=["content_hash"]
            )

            if not analysis_result:
                raise ValueError("Failed to create analysis record via upsert fallback")

            analysis_id = analysis_result["id"]
        logger.info(f"Created new analysis record: {analysis_id}")

        # Import and dispatch the comprehensive analysis task
        from app.tasks.background_tasks import comprehensive_document_analysis

        # Enhanced task parameters with comprehensive processing
        task_params = {
            "document_id": document_id,
            "analysis_id": analysis_id,
            "contract_id": contract_id,
            "user_id": user_id,
            "analysis_options": {
                **analysis_options,
                "content_hash": content_hash,
                "enable_caching": True,
                "progress_tracking": True,
                "comprehensive_processing": True,
            },
        }

        logger.info(
            f"Dispatching comprehensive analysis task for contract {contract_id} with progress tracking"
        )

        # Use task manager to properly launch the task with context
        from app.core.task_context import task_manager

        await task_manager.initialize()
        # Extract the task parameters that should be passed to the task
        task_args = (
            task_params["document_id"],
            task_params["analysis_id"],
            task_params["contract_id"],
            task_params["user_id"],
            task_params["analysis_options"],
        )
        task = await task_manager.launch_user_task(
            comprehensive_document_analysis, task_params["analysis_id"], *task_args
        )

        if not task or not task.id:
            raise ValueError("Failed to queue comprehensive analysis task")

        logger.info(f"Comprehensive analysis task queued with ID: {task.id}")

        return {
            "contract_id": contract_id,
            "analysis_id": analysis_id,
            "task_id": task.id,
        }

    except Exception as e:
        logger.error(f"Failed to dispatch analysis task: {str(e)}")
        raise ValueError(f"Analysis dispatch failed: {str(e)}")


async def _generate_document_content_hash(document: Dict[str, Any]) -> Optional[str]:
    """Generate content hash for document."""
    try:
        import hashlib

        # Try to get hash from document record first
        if document.get("content_hash"):
            return document["content_hash"]

        # If document has processing results with text, hash that
        processing_results = document.get("processing_results", {})
        text_extraction = processing_results.get("text_extraction", {})
        full_text = text_extraction.get("full_text", "")

        if full_text:
            # Hash the extracted text content
            content_bytes = full_text.encode("utf-8")
            return hashlib.sha256(content_bytes).hexdigest()

        # Fallback: create hash from document metadata
        metadata = f"{document.get('original_filename', '')}{document.get('file_size', 0)}{document.get('created_at', '')}"
        return hashlib.sha256(metadata.encode("utf-8")).hexdigest()

    except Exception as e:
        logger.error(f"Error generating content hash: {str(e)}")
        return None


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
