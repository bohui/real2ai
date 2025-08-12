"""WebSocket router with proper ASGI compliance and user-aware architecture"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, UTC, timedelta

from app.core.auth import get_current_user_ws, verify_ws_token, get_user_by_id_service
from app.core.auth_context import AuthContext
from app.services.communication.websocket_service import WebSocketEvents
from app.services.communication.websocket_singleton import websocket_manager
from app.services.communication.redis_pubsub import redis_pubsub_service
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.clients.factory import get_service_supabase_client
from enum import Enum
from app.services.backend_token_service import BackendTokenService
from app.services.repositories.analyses_repository import AnalysesRepository
from app.services.repositories.analysis_progress_repository import (
    AnalysisProgressRepository,
)
from app.services.repositories.documents_repository import DocumentsRepository
from app.services.repositories.contracts_repository import ContractsRepository


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
        # Get document with user context (RLS enforced)
        docs_repo = DocumentsRepository()
        document = await docs_repo.get_document(UUID(document_id))

        if not document:
            raise ValueError(f"Document {document_id} not found or access denied")

        # Convert to dict for backward compatibility
        document = {
            "id": str(document.id),
            "user_id": str(document.user_id),
            "content_hash": document.content_hash,
            "original_filename": document.original_filename,
            "processing_status": document.processing_status,
        }
        content_hash = document.get("content_hash")
        if not content_hash:
            logger.info("Document has no content_hash; treating as cache MISS")
            return {
                "cache_status": CacheStatus.MISS,
                "document_id": document_id,
                "content_hash": None,
                "contract_id": None,
                "retry_available": False,
                "message": "Document has no content_hash yet; analysis will start shortly",
            }

        logger.info(
            f"Checking cache for document {document_id} with content_hash: {content_hash}"
        )

        # Check if user has access to documents with this content_hash using repository
        docs_repo = DocumentsRepository()
        user_documents = await docs_repo.get_documents_by_content_hash(
            content_hash, user_id
        )

        if not user_documents:
            # CACHE MISS - User doesn't have access to any documents with this content_hash
            logger.info(
                f"Cache MISS: User doesn't have access to documents with content_hash {content_hash}"
            )
            return {
                "cache_status": CacheStatus.MISS,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": None,
                "retry_available": False,
                "message": "New document - analysis will start shortly",
            }

        # User has access to documents with this content_hash, now check for contracts
        # Since the user has access to documents with this content_hash, they should be able to access contracts
        # But we need to ensure the RLS policy is satisfied by checking user_contract_views first
        user_contract_views = await docs_repo.get_user_contract_views(
            content_hash, user_id, limit=1
        )

        # If no user_contract_views entry exists, create one to ensure access
        if not user_contract_views:
            # Create a user_contract_views entry to ensure access to contracts and analyses
            try:
                await docs_repo.create_user_contract_view(
                    user_id=UUID(user_id),
                    content_hash=content_hash,
                    property_address=document.get("property_address"),
                    source="upload",
                )
                logger.info(
                    f"Created user_contract_views entry for user {user_id} and content_hash {content_hash}"
                )
            except Exception as e:
                logger.warning(f"Failed to create user_contract_views entry: {e}")
                # Continue anyway - the user should still have access through documents

        # Now check for contracts - the RLS policy should allow access since user has documents with this content_hash
        contracts_repo = ContractsRepository()
        contract = await contracts_repo.get_contract_by_content_hash(content_hash)

        if not contract:
            # CACHE MISS - No contract found for this content_hash
            logger.info(
                f"Cache MISS: No contract found for content_hash {content_hash}"
            )
            return {
                "cache_status": CacheStatus.MISS,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": None,
                "retry_available": False,
                "message": "New document - analysis will start shortly",
            }

        contract_id = str(contract.id)

        # Check analysis status using AnalysesRepository
        analyses_repo = AnalysesRepository(use_service_role=True)
        analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

        if not analysis:
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

        analysis_status = analysis.status

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
                "analysis_id": str(analysis.id),
                "analysis_result": analysis.result or {},
                "processing_time": None,  # Field not available in analyses table
                "retry_available": False,
                "message": "Analysis complete - results available instantly!",
            }

        elif analysis_status in ["pending", "queued", "processing"]:
            # CACHE HIT IN PROGRESS - Join existing analysis
            logger.info(
                f"Cache HIT IN_PROGRESS: Analysis ongoing for contract {contract_id}"
            )

            # Get detailed progress if available
            progress_repo = AnalysisProgressRepository()
            progress = await progress_repo.get_latest_progress(content_hash, user_id)

            progress_info = None
            if progress:
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
                "analysis_id": str(analysis.id),
                "progress": progress_info,
                "retry_available": False,
                "message": "Analysis in progress - joining existing process",
            }

        elif analysis_status in ["failed", "cancelled"]:
            # CACHE HIT FAILED - Previous attempt failed
            logger.info(
                f"Cache HIT FAILED: Previous analysis failed for contract {contract_id}"
            )
            # Normalize error_details that may be stored as text
            error_details = analysis.error_details
            if not isinstance(error_details, dict):
                error_details = {
                    "message": str(error_details) if error_details else None
                }
            return {
                "cache_status": CacheStatus.FAILED,
                "document_id": document_id,
                "content_hash": content_hash,
                "contract_id": contract_id,
                "analysis_id": str(analysis.id),
                "error_message": error_details.get("message")
                or error_details.get("error_message")
                or "Analysis failed",
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
        # Exchange backend token for Supabase access token if needed
        auth_token = token
        if BackendTokenService.is_backend_token(token):
            logger.info(
                f"Backend token detected for WebSocket, attempting exchange for user: {user.id}"
            )
            exchanged = await BackendTokenService.ensure_supabase_access_token(token)
            if exchanged:
                auth_token = exchanged
                logger.info(
                    f"Successfully exchanged backend token for Supabase token for WebSocket user: {user.id}"
                )
            else:
                logger.warning(
                    f"Failed to exchange backend token for Supabase token for WebSocket user: {user.id}"
                )

        # Store the actual token for authenticated operations
        # Also carry refresh token if the backend token store has one
        refresh_token: Optional[str] = None
        try:
            if BackendTokenService.is_backend_token(token):
                mapping = BackendTokenService.get_mapping(token)
                if mapping:
                    refresh_token = mapping.get("supabase_refresh_token")
        except Exception:
            refresh_token = None

        AuthContext.set_auth_context(
            token=auth_token,  # Use exchanged token if available
            user_id=str(user.id),
            user_email=user.email,
            metadata={
                "websocket_document_id": document_id,
                "connection_type": "websocket",
                "connected_at": datetime.now(UTC).isoformat(),
            },
            refresh_token=refresh_token,
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
        if document_id not in redis_pubsub_service.subscriptions:

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
                logger.info(
                    f"Redis subscription created for document session {document_id}"
                )
            except Exception as sub_error:
                logger.warning(
                    f"Could not subscribe to Redis channel for {document_id}: {sub_error}"
                )

        # Also subscribe to contract_id and content_hash channels for legacy compatibility
        # Legacy bridging: contract_id subscription exists for compatibility and can be removed
        # once all publishers emit on content_hash channels
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
                        logger.info(
                            f"📨 Forwarding hash pub/sub message to document {document_id}: {message}"
                        )
                        await websocket_manager.send_message(document_id, message)
                        logger.info(
                            f"✅ Successfully forwarded hash message to WebSocket"
                        )
                    except Exception as forward_error:
                        logger.error(
                            f"Failed to forward hash pub/sub message: {forward_error}"
                        )

                await redis_pubsub_service.subscribe_to_progress(
                    content_hash, _forward_from_hash
                )
                logger.info(
                    f"🔗 Subscribed to content_hash channel: {content_hash} for document {document_id}"
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
            # Get document details to check upload time
            docs_repo = DocumentsRepository()
            document_obj = await docs_repo.get_document(UUID(document_id))

            if document_obj:
                document = {
                    "id": str(document_obj.id),
                    "created_at": document_obj.created_at,
                    "original_filename": document_obj.original_filename,
                    "file_size": document_obj.file_size,
                    "processing_status": getattr(
                        document_obj, "processing_status", None
                    ),
                }
                created_at = document.get("created_at")

                if created_at:
                    # Convert created_at to aware datetime safely
                    try:
                        if isinstance(created_at, str):
                            created_time = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        elif isinstance(created_at, datetime):
                            created_time = created_at
                        else:
                            created_time = None
                    except Exception as dt_err:
                        logger.warning(
                            "Failed to parse created_at for document %s: %s",
                            document_id,
                            dt_err,
                        )
                        created_time = None
                    five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)

                    if created_time is not None:
                        # Ensure timezone-aware (assume UTC if naive)
                        if created_time.tzinfo is None:
                            created_time = created_time.replace(tzinfo=UTC)
                    if created_time and created_time > five_minutes_ago:
                        # Send document_uploaded notification
                        filename_to_send = document.get("original_filename", "Unknown")
                        status_to_send = document.get("processing_status", "uploaded")
                        await websocket_manager.send_personal_message(
                            document_id,
                            websocket,
                            WebSocketEvents.document_uploaded(
                                document_id=document_id,
                                filename=filename_to_send,
                                processing_status=status_to_send,
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

        # Ensure Redis subscription to newly created contract_id so progress events are forwarded
        try:
            new_contract_id = task_result.get("contract_id")
            if (
                new_contract_id
                and new_contract_id not in redis_pubsub_service.subscriptions
            ):

                async def _forward_from_new_contract(message: Dict[str, Any]):
                    try:
                        await websocket_manager.send_message(document_id, message)
                    except Exception as forward_error:
                        logger.error(
                            f"Failed to forward contract pub/sub message (post-dispatch): {forward_error}"
                        )

                await redis_pubsub_service.subscribe_to_progress(
                    new_contract_id, _forward_from_new_contract
                )
                logger.info(
                    f"🔗 Subscribed to contract_id channel post-dispatch: {new_contract_id} for document {document_id}"
                )
        except Exception as sub_error:
            logger.warning(
                f"Could not subscribe to new contract_id channel after dispatch: {sub_error}"
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
        # Mark this as a retry operation
        analysis_options["is_retry"] = True

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
        contracts_repo = ContractsRepository()
        contract = await contracts_repo.get_contract_by_id(UUID(contract_id))

        if not contract:
            raise ValueError("Contract not found")

        content_hash = contract.content_hash

        # Check current analysis status before attempting retry
        analyses_repo = AnalysesRepository(use_service_role=True)
        analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

        if analysis:
            current_status = analysis.status
            if current_status == "completed":
                # Analysis already completed successfully, no retry needed
                await websocket_manager.send_personal_message(
                    document_id,
                    websocket,
                    {
                        "event_type": "retry_not_needed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": {
                            "document_id": document_id,
                            "contract_id": contract_id,
                            "message": "Analysis already completed successfully. No retry needed.",
                            "current_status": current_status,
                        },
                    },
                )
                return

        # Use the new retry function to safely handle existing analysis records
        analyses_repo = AnalysesRepository(use_service_role=True)
        retry_analysis_id = await analyses_repo.retry_contract_analysis(
            content_hash, user_id
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
    try:
        # First get the content_hash from the document
        docs_repo = DocumentsRepository()
        document = await docs_repo.get_document(UUID(document_id))

        if not document:
            raise ValueError(f"Document {document_id} not found or access denied")

        content_hash = document.content_hash
        if not content_hash:
            raise ValueError(f"Document {document_id} has no content hash")

        # If client didn't provide a contract_id, try to resolve it by content_hash
        if not contract_id or contract_id == "None":
            try:
                contracts_repo = ContractsRepository()
                contracts = await contracts_repo.get_contracts_by_content_hash(
                    content_hash, limit=1
                )
                if contracts:
                    contract_id = str(contracts[0].id)
            except Exception:
                # If this lookup fails, continue; we'll still report status by content_hash
                pass

        # Check if user has access to this content_hash through user_contract_views
        user_contract_views = await docs_repo.get_user_contract_views(
            content_hash, user_id, limit=1
        )

        # If no user_contract_views entry exists, create one to ensure access
        if not user_contract_views:
            # Create a user_contract_views entry to ensure access to contracts and analyses
            try:
                # Create user_contract_views entry using repository
                from app.services.repositories.user_contract_views_repository import (
                    UserContractViewsRepository,
                )

                contract_views_repo = UserContractViewsRepository()
                await contract_views_repo.create_contract_view(
                    user_id=user_id,
                    content_hash=content_hash,
                    property_address=getattr(document, "property_address", None),
                    source="upload",
                )
                logger.info(
                    f"Created user_contract_views entry for user {user_id} and content_hash {content_hash}"
                )
            except Exception as e:
                logger.warning(f"Failed to create user_contract_views entry: {e}")
                # Continue anyway - the user should still have access through documents

        # Get detailed progress from analysis_progress table (user context - RLS enforced)
        progress_repo = AnalysisProgressRepository()
        # Request all fields needed by the frontend to avoid KeyErrors
        progress_data = await progress_repo.get_latest_progress(
            content_hash,
            user_id,
            columns=(
                "current_step, progress_percent, step_description, status, "
                "estimated_completion_minutes, updated_at, total_elapsed_seconds"
            ),
        )

        if progress_data:
            progress = progress_data
            status_message = {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": progress.get("current_step", ""),
                    "progress_percent": progress.get("progress_percent", 0),
                    "step_description": progress.get("step_description", ""),
                    "status": progress.get("status", "in_progress"),
                    "estimated_completion_minutes": progress.get(
                        "estimated_completion_minutes"
                    ),
                    "last_updated": progress.get("updated_at"),
                    "total_elapsed_seconds": progress.get("total_elapsed_seconds", 0),
                },
            }
        else:
            # Fallback to analyses repository (shared resource - RLS enforced)
            # Since the user has access to documents with this content_hash, they should be able to access analyses
            analyses_repo = AnalysesRepository(use_service_role=True)
            analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

            if analysis:
                status_message = {
                    "event_type": "status_update",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "contract_id": contract_id,
                        "status": analysis.status,
                        "progress_percent": get_progress_from_status(analysis.status),
                        "last_updated": (
                            analysis.updated_at.isoformat()
                            if analysis.updated_at
                            else None
                        ),
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
        # Get the content_hash from the document
        docs_repo = DocumentsRepository()
        document = await docs_repo.get_document(UUID(document_id))

        if not document:
            raise ValueError(f"Document {document_id} not found or access denied")

        content_hash = document.content_hash

        # Find and update analysis_progress records that match the filters
        progress_repo = AnalysisProgressRepository()
        progress_records = await progress_repo.get_progress_records(
            filters={
                "content_hash": content_hash,
                "user_id": user_id,
                "status": "in_progress",
            }
        )

        # Update each matching progress record
        for record in progress_records:
            await progress_repo.update_progress_by_id(
                record["id"],
                {"status": "cancelled", "error_message": "Analysis cancelled by user"},
            )

        # Update analysis records using AnalysesRepository
        try:
            analyses_repo = AnalysesRepository(use_service_role=True)
            analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

            if analysis:
                await analyses_repo.update_analysis_status(
                    analysis.id,
                    status="cancelled",
                    error_details={"cancelled_by_user": user_id},
                )
                logger.info(f"Cancelled analysis {analysis.id} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to update analysis status during cancel: {e}")
            logger.info("Skip direct update to shared analyses rows during cancel")

        # Try to cancel the Celery task if we can find it
        try:
            from app.tasks.background_tasks import comprehensive_document_analysis

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
        # Get document record
        docs_repo = DocumentsRepository()
        document_obj = await docs_repo.get_document(UUID(document_id))

        if not document_obj:
            raise ValueError(f"Document {document_id} not found or access denied")

        # Convert to dict for backward compatibility
        document = {
            "id": str(document_obj.id),
            "user_id": str(document_obj.user_id),
            "original_filename": document_obj.original_filename,
            "storage_path": document_obj.storage_path,
            "file_type": document_obj.file_type,
            "file_size": document_obj.file_size,
            "content_hash": document_obj.content_hash,
            "processing_status": document_obj.processing_status,
        }
        content_hash = document.get("content_hash")
        if not content_hash:
            raise ValueError("Document has no content_hash; cannot dispatch analysis")

        # Create or get contract record if not provided
        if not contract_id:
            # Use service role client (shared resource) and delegate to central service
            from app.services.contract_analysis_service import ensure_contract

            service_client = await get_service_supabase_client()
            contract_id = await ensure_contract(
                service_client,
                content_hash=content_hash,
                contract_type=document.get("contract_type", "purchase_agreement"),
                australian_state=document.get("australian_state", "NSW"),
            )

        # Create analysis record using AnalysesRepository
        analyses_repo = AnalysesRepository(use_service_role=True)

        analysis = await analyses_repo.upsert_analysis(
            content_hash=content_hash, agent_version="1.0", status="pending", result={}
        )
        analysis_id = str(analysis.id)
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
