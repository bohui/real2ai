"""Background tasks for document processing and contract analysis.

MIGRATED VERSION: Now uses user-aware architecture with proper context propagation.
All tasks use @user_aware_task decorator to maintain user authentication context.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
import datetime as dt

from app.core.celery import celery_app
from app.core.task_context import user_aware_task
from app.core.auth_context import AuthContext
from app.services.contract_analysis_service import ContractAnalysisService
from app.services.document_service import DocumentService
from app.services.communication.websocket_service import WebSocketEvents
from app.services.communication.websocket_singleton import websocket_manager
from app.services.communication.redis_pubsub import publish_progress_sync
from app.core.task_recovery import CheckpointData
from app.services.repositories.analyses_repository import AnalysesRepository
from app.services.repositories.analysis_progress_repository import (
    AnalysisProgressRepository,
)
from app.services.repositories.documents_repository import DocumentsRepository
from app.services.backend_token_service import BackendTokenService

logger = logging.getLogger(__name__)


def _extract_root_cause(exception: Exception) -> Exception:
    """
    Extract the root cause from an exception chain.

    Args:
        exception: The exception to analyze

    Returns:
        The root cause exception (the original exception that started the chain)
    """
    current = exception
    while hasattr(current, "__cause__") and current.__cause__ is not None:
        current = current.__cause__

    # Also check for __context__ which is used for implicit exception chaining
    while hasattr(current, "__context__") and current.__context__ is not None:
        if not hasattr(current, "__cause__") or current.__cause__ is None:
            # Only follow __context__ if there's no explicit __cause__
            current = current.__context__
        else:
            break

    return current


def _format_exception_chain(exception: Exception) -> List[str]:
    """
    Format the full exception chain as a list of strings for logging.

    Args:
        exception: The exception to format

    Returns:
        List of formatted exception strings showing the full chain
    """
    chain = []
    current = exception
    seen = set()  # Prevent infinite loops in circular references

    while current is not None:
        # Prevent infinite loops
        exception_id = id(current)
        if exception_id in seen:
            break
        seen.add(exception_id)

        # Format current exception
        exc_info = {
            "type": type(current).__name__,
            "message": str(current),
            "module": getattr(type(current), "__module__", "unknown"),
        }

        # Add file and line info if available
        if hasattr(current, "__traceback__") and current.__traceback__:
            tb = current.__traceback__
            while tb.tb_next:
                tb = tb.tb_next  # Get the deepest traceback
            exc_info["file"] = tb.tb_frame.f_code.co_filename
            exc_info["line"] = tb.tb_lineno
            exc_info["function"] = tb.tb_frame.f_code.co_name

        chain.append(
            f"{exc_info['type']}: {exc_info['message']} (in {exc_info.get('function', 'unknown')} at {exc_info.get('file', 'unknown')}:{exc_info.get('line', 'unknown')})"
        )

        # Move to the next exception in the chain
        if hasattr(current, "__cause__") and current.__cause__ is not None:
            current = current.__cause__
        elif hasattr(current, "__context__") and current.__context__ is not None:
            current = current.__context__
        else:
            break

    return chain


# Progress tracking constants
PROGRESS_STAGES = {
    "document_processing": {
        "text_extraction": 25,
        "page_analysis": 50,
        "diagram_detection": 60,
        "entity_extraction": 70,
        "document_complete": 75,
    },
    "contract_analysis": {
        "analysis_start": 80,
        "workflow_processing": 90,
        "results_caching": 95,
        "analysis_complete": 100,
    },
}


async def update_analysis_progress(
    user_id: str,
    content_hash: str,
    progress_percent: int,
    current_step: str,
    step_description: str,
    estimated_completion_minutes: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Update analysis progress with detailed tracking"""
    try:
        # Get user-authenticated client
        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        # user_client = await AuthContext.get_authenticated_client(isolated=True)

        # Update or create progress record
        # Determine status based on step and progress
        # Only mark as completed if we have confirmation of successful processing
        if current_step.endswith("_failed") or current_step == "failed":
            status = "failed"
        elif progress_percent >= 100 and current_step == "analysis_complete":
            # Additional validation: only mark as completed for analysis_complete step
            # This prevents premature completion marking
            status = "completed"
        else:
            status = "in_progress"

        progress_data = {
            "content_hash": content_hash,
            "user_id": user_id,
            "current_step": current_step,
            "progress_percent": progress_percent,
            "step_description": step_description,
            # Pass a datetime object for DB insertion (asyncpg expects datetime, not string)
            "step_started_at": dt.datetime.now(dt.timezone.utc),
            "estimated_completion_minutes": estimated_completion_minutes,
            "status": status,
            "error_message": error_message,
        }

        # Upsert progress record using repository
        logger.debug(
            "[update_analysis_progress] Prepared progress_data",
            extra={
                "content_hash": content_hash,
                "user_id": user_id,
                "current_step": current_step,
                "progress_percent": progress_percent,
                "status": status,
                "step_started_at_type": type(progress_data["step_started_at"]).__name__,
            },
        )
        progress_repo = AnalysisProgressRepository()
        result = await progress_repo.upsert_progress(
            content_hash, user_id, progress_data
        )
        logger.debug(
            "[update_analysis_progress] Upsert result",
            extra={"content_hash": content_hash, "user_id": user_id, "result": result},
        )

        # IMPORTANT: Do not emit per-step analysis_progress over the document WebSocket channel.
        # The unified ContractAnalysisService already emits ordered progress over the contract/session channel.
        # Emitting here causes duplicate, out-of-order updates interleaving across channels which regresses the UI.
        # We still persist to DB and publish to Redis below for internal consumers.
        try:
            # We intentionally skip WebSocket fan-out on the document channel to prevent UI regressions.
            docs_repo = DocumentsRepository()
            documents = await docs_repo.get_documents_by_content_hash(
                content_hash, user_id, columns="id"
            )
            logger.debug(
                "[update_analysis_progress] Skipping WS broadcast on document channel",
                extra={
                    "content_hash": content_hash,
                    "user_id": user_id,
                    "doc_count": len(documents) if documents is not None else 0,
                    "broadcast_skipped": True,
                },
            )
        except Exception as ws_error:
            logger.warning(f"WS progress routing introspection failed: {ws_error}")

        # Do not publish progress to Redis here to avoid duplicate/out-of-order UI updates.
        # The ContractAnalysisService is the single source of truth for real-time progress
        # and will publish progress via Redis/WebSocket. We only persist to DB in this path.

        logger.info(
            f"Progress updated: {current_step} ({progress_percent}%) for content_hash {content_hash}"
        )

    except Exception as e:
        logger.error(
            f"Failed to update progress for content_hash {content_hash}: {str(e)}"
        )


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=2)
async def comprehensive_document_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str,
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Comprehensive document analysis with enhanced token management.

    This task performs comprehensive analysis of uploaded documents with proactive
    token refresh to prevent JWT expiration issues during long-running operations.

    Args:
        recovery_ctx: Recovery context for checkpointing
        document_id: Document ID to analyze
        analysis_id: Analysis ID for tracking
        contract_id: Contract ID for context
        user_id: User ID for authentication
        analysis_options: Analysis configuration options

    Returns:
        Analysis results dictionary
    """
    task_start = dt.datetime.now(dt.timezone.utc)
    logger.info(
        f"Starting comprehensive document analysis",
        extra={
            "task_id": (
                recovery_ctx.task_id if hasattr(recovery_ctx, "task_id") else "unknown"
            ),
            "document_id": document_id,
            "analysis_id": analysis_id,
            "contract_id": contract_id,
            "user_id": user_id,
            "analysis_options": analysis_options,
        },
    )

    # Proactive token refresh check at task start
    try:

        current_token = AuthContext.get_user_token()
        if current_token and BackendTokenService.is_backend_token(current_token):
            # Check if token needs refresh
            claims = BackendTokenService.verify_backend_token(current_token)
            backend_exp = claims.get("exp")
            if backend_exp:
                now = int(time.time())
                time_to_expiry = backend_exp - now

                logger.info(
                    f"Token expiry check at task start",
                    extra={
                        "task_id": (
                            recovery_ctx.task_id
                            if hasattr(recovery_ctx, "task_id")
                            else "unknown"
                        ),
                        "user_id": user_id,
                        "time_to_expiry_seconds": time_to_expiry,
                        "time_to_expiry_minutes": (
                            time_to_expiry / 60 if time_to_expiry > 0 else 0
                        ),
                    },
                )

                # If token expires in less than 15 minutes, refresh proactively
                if time_to_expiry <= 900:  # 15 minutes
                    logger.info(
                        f"Proactively refreshing token before task execution",
                        extra={
                            "task_id": (
                                recovery_ctx.task_id
                                if hasattr(recovery_ctx, "task_id")
                                else "unknown"
                            ),
                            "user_id": user_id,
                            "time_to_expiry_seconds": time_to_expiry,
                            "reason": "Token expires soon, refreshing proactively",
                        },
                    )

                    try:
                        refreshed_token = (
                            await BackendTokenService.refresh_coordinated_tokens(
                                current_token
                            )
                        )
                        if refreshed_token:
                            # Update auth context with new token
                            AuthContext.set_auth_context(
                                token=refreshed_token,
                                user_id=user_id,
                                user_email=AuthContext.get_user_email(),
                                metadata=AuthContext.get_auth_metadata(),
                                refresh_token=AuthContext.get_refresh_token(),
                            )
                            logger.info(
                                f"Successfully refreshed token before task execution",
                                extra={
                                    "task_id": (
                                        recovery_ctx.task_id
                                        if hasattr(recovery_ctx, "task_id")
                                        else "unknown"
                                    ),
                                    "user_id": user_id,
                                    "old_token_length": len(current_token),
                                    "new_token_length": len(refreshed_token),
                                },
                            )
                        else:
                            logger.warning(
                                f"Failed to refresh token before task execution",
                                extra={
                                    "task_id": (
                                        recovery_ctx.task_id
                                        if hasattr(recovery_ctx, "task_id")
                                        else "unknown"
                                    ),
                                    "user_id": user_id,
                                },
                            )
                    except Exception as refresh_error:
                        logger.error(
                            f"Error during proactive token refresh",
                            extra={
                                "task_id": (
                                    recovery_ctx.task_id
                                    if hasattr(recovery_ctx, "task_id")
                                    else "unknown"
                                ),
                                "user_id": user_id,
                                "error": str(refresh_error),
                            },
                            exc_info=True,
                        )
                        # Continue with original token - let the database layer handle refresh if needed

    except Exception as token_check_error:
        logger.warning(
            f"Could not perform proactive token refresh check",
            extra={
                "task_id": (
                    recovery_ctx.task_id
                    if hasattr(recovery_ctx, "task_id")
                    else "unknown"
                ),
                "user_id": user_id,
                "error": str(token_check_error),
            },
        )
        # Continue with task execution - token refresh will happen at database layer if needed

    try:
        # Initialize services
        document_service = DocumentService(use_llm_document_processing=True)
        await document_service.initialize()
        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        user_client = await document_service.get_user_client(isolated=True)

        # Get document record
        docs_repo = DocumentsRepository()
        document = await docs_repo.get_document(UUID(document_id))
        if not document:
            raise Exception(f"Document not found or access denied: {document_id}")
        # Convert to dict for backward compatibility
        document = {
            "id": str(document.id),
            "user_id": str(document.user_id),
            "original_filename": document.original_filename,
            "storage_path": document.storage_path,
            "file_type": document.file_type,
            "content_hash": document.content_hash,
            "processing_status": document.processing_status,
        }

        # Get content_hash for progress tracking
        content_hash = analysis_options.get("content_hash") or document.get(
            "content_hash"
        )
        if not content_hash:
            raise Exception("Content hash not found in document or analysis options")

        # Determine resume point from latest analysis_progress (if any)
        try:
            progress_repo = AnalysisProgressRepository()
            latest_progress = await progress_repo.get_latest_progress(
                content_hash,
                user_id,
                columns="current_step, progress_percent, updated_at",
            )
            if latest_progress:
                last_step = latest_progress.get("current_step")
                # Inject resume info into analysis options
                if last_step:
                    analysis_options["resume_from_step"] = last_step
                    logger.info(
                        f"Resuming analysis for {content_hash} from step: {last_step}"
                    )
        except Exception as resume_err:
            logger.warning(f"Unable to fetch latest progress for resume: {resume_err}")

        # Prefer explicit task checkpoint (if available) to determine precise resume step
        try:
            if hasattr(recovery_ctx, "registry") and hasattr(recovery_ctx, "task_id"):
                ckpt = await recovery_ctx.registry.get_latest_checkpoint(
                    recovery_ctx.task_id
                )
                if ckpt and getattr(ckpt, "checkpoint_name", None):
                    analysis_options["resume_from_step"] = ckpt.checkpoint_name
                    logger.info(
                        f"Using checkpoint-based resume step: {ckpt.checkpoint_name}"
                    )
        except Exception as ckpt_err:
            logger.debug(f"No checkpoint-based resume available: {ckpt_err}")

        # =============================================
        # PHASE 1: COARSE PROGRESS ONLY (skip pre-processing)
        # =============================================

        # Record a minimal DB-backed milestone to indicate the job is queued/starting
        # Check if this is a retry operation to preserve progress continuity
        is_retry = analysis_options.get("is_retry", False)
        resume_from_step = analysis_options.get("resume_from_step")

        if is_retry and resume_from_step:
            # For retry operations, preserve the previous progress and show resumption
            previous_progress = (
                latest_progress.get("progress_percent", 5) if latest_progress else 5
            )
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=previous_progress,
                current_step="retrying",
                step_description=f"Resuming analysis from {resume_from_step}...",
                estimated_completion_minutes=2,
            )
            logger.info(
                f"Retry operation: maintaining progress at {previous_progress}% for step {resume_from_step}"
            )
        else:
            # Normal startup: new analysis
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=5,
                current_step="queued",
                step_description="Queued for AI contract analysis...",
                estimated_completion_minutes=3,
            )
            # Emit initial WS/Redis notification for 5%
            try:
                message = {
                    "event_type": "analysis_progress",
                    "timestamp": dt.datetime.now().isoformat(),
                    "data": {
                        "contract_id": contract_id,
                        "current_step": "queued",
                        "progress_percent": 5,
                        "step_description": "Queued for AI contract analysis...",
                    },
                }
                publish_progress_sync(content_hash, message)
                if contract_id and contract_id != content_hash:
                    publish_progress_sync(contract_id, message)
            except Exception:
                pass
            logger.info("New analysis: starting from queued at 5%")

            # Keep the task context fresh for long-running operations
            await recovery_ctx.refresh_context_ttl()

            # =============================================
            # PHASE 2: CONTRACT ANALYSIS (75-100%)
            # =============================================

            # Step: Contract Analysis Start (coarse milestone)
            # Fixed: Use 7% to match PRD validate_input step percentage
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=7,
                current_step="contract_analysis",
                step_description="Starting AI contract analysis...",
                estimated_completion_minutes=1,
            )
            # Emit initial WS/Redis notification for 7%
            try:

                message = {
                    "event_type": "analysis_progress",
                    "timestamp": dt.datetime.now().isoformat(),
                    "data": {
                        "contract_id": contract_id,
                        "current_step": "contract_analysis",
                        "progress_percent": 7,
                        "step_description": "Starting AI contract analysis...",
                    },
                }
                publish_progress_sync(content_hash, message)
                if contract_id and contract_id != content_hash:
                    publish_progress_sync(contract_id, message)
            except Exception:
                pass

            # Prepare minimal document_data for ContractAnalysisService
            # Validation requires either content or file_path; provide file_path to avoid pre-processing duplication
            document_data = {
                "document_id": document_id,
                "filename": document.get(
                    "original_filename", document.get("filename", "unknown")
                ),
                "file_type": document.get("file_type", "pdf"),
                "storage_path": document.get("storage_path", ""),
                "content_hash": content_hash,
                "file_path": document.get("storage_path", ""),
            }

            # Resolve Australian state from document metadata or options (default to NSW)
            state_to_use = (
                document.get("australian_state")
                or analysis_options.get("australian_state")
                or "NSW"
            )

            # Initialize ContractAnalysisService with WebSocket progress tracking

            contract_service = ContractAnalysisService(
                websocket_manager=websocket_manager,
                enable_websocket_progress=False,  # Progress will be emitted from persist_progress callback
            )

            # Execute contract analysis using the service layer
            logger.info(f"Starting contract analysis with document data")

            async def persist_progress(step: str, percent: int, description: str):
                # Persist to Supabase, then emit WS/Redis notification with monotonic guard.
                # Also update recovery registry, create checkpoint, and refresh task TTL.
                try:
                    # Monotonic gating using latest persisted progress
                    try:
                        progress_repo = AnalysisProgressRepository()
                        latest = await progress_repo.get_latest_progress(
                            content_hash,
                            user_id,
                            columns="progress_percent,current_step",
                        )
                        last_percent = (
                            int(latest.get("progress_percent", 0)) if latest else 0
                        )
                    except Exception as _lp_err:
                        last_percent = 0
                        logger.debug(
                            f"Monotonic lookup failed, defaulting last_percent=0: {_lp_err}"
                        )

                    if percent <= last_percent:
                        # this shouldn't happen
                        logger.warning(
                            "Skipping non-increasing progress update",
                            extra={
                                "content_hash": content_hash,
                                "requested_percent": percent,
                                "last_percent": last_percent,
                                "step": step,
                            },
                        )
                        return

                    # 1) Persist user-facing progress (DB only; this function intentionally avoids duplicate WS in update_analysis_progress)
                    await update_analysis_progress(
                        user_id,
                        content_hash,
                        progress_percent=percent,
                        current_step=step,
                        step_description=description,
                        estimated_completion_minutes=None,
                    )

                    # 1b) Emit WS/Redis notification here as the single source of truth for real-time UI updates
                    try:

                        message = {
                            "event_type": "analysis_progress",
                            "timestamp": dt.datetime.now().isoformat(),
                            "data": {
                                "contract_id": contract_id,  # actual contract UUID expected by UI
                                "current_step": step,
                                "progress_percent": percent,
                                "step_description": description,
                            },
                        }

                        # Primary channel: session_id (we use content_hash as session/session-like id)
                        publish_progress_sync(content_hash, message)
                        # Secondary channel: contract_id for contract-specific subscriptions
                        if contract_id and contract_id != content_hash:
                            publish_progress_sync(contract_id, message)
                    except Exception as _ws_err:
                        logger.warning(
                            f"Progress WS/Redis publish failed for {content_hash}: {_ws_err}"
                        )

                    # 2) Update recovery registry progress (idempotent)
                    try:
                        await recovery_ctx.update_progress(
                            progress_percent=percent,
                            current_step=step,
                            step_description=description,
                        )
                    except Exception as _reg_err:
                        logger.debug(
                            f"Recovery registry progress update skipped: {_reg_err}"
                        )

                    # 3) Create a lightweight checkpoint for step-level resume (idempotent)
                    try:
                        checkpoint = CheckpointData(
                            checkpoint_name=step,
                            progress_percent=percent,
                            step_description=description,
                            recoverable_data={
                                "content_hash": content_hash,
                                "step": step,
                            },
                            database_state={},
                            file_state={},
                        )
                        await recovery_ctx.create_checkpoint(checkpoint)
                    except Exception as _cp_err:
                        logger.debug(f"Checkpoint creation skipped: {_cp_err}")
                finally:
                    # 4) Keep the task context alive for long-running analyses
                    try:
                        await recovery_ctx.refresh_context_ttl()
                    except Exception:
                        pass

            analysis_response = await contract_service.start_analysis(
                user_id=user_id,
                session_id=content_hash,  # Use content_hash as session_id
                document_data=document_data,
                australian_state=state_to_use,
                user_preferences=analysis_options,
                user_type="buyer",  # Default user type
                progress_callback=persist_progress,
            )

            # Unified error handling for None or unsuccessful responses
            unified_error_msg = None
            if analysis_response is None:
                unified_error_msg = "Contract analysis service returned None"
            elif not getattr(analysis_response, "success", False):
                unified_error_msg = (
                    getattr(analysis_response, "error", None)
                    or "Contract analysis failed"
                )

            if unified_error_msg:
                # Enriched diagnostics for tracing root cause (single code path)
                latest_snapshot = None
                try:
                    progress_repo = AnalysisProgressRepository()
                    latest_snapshot = await progress_repo.get_latest_progress(
                        content_hash,
                        user_id,
                        columns="current_step, progress_percent, updated_at",
                    )
                except Exception as _snap_err:
                    latest_snapshot = {"error": str(_snap_err)}

                logger.error(
                    unified_error_msg,
                    extra={
                        "document_id": document_id,
                        "analysis_id": analysis_id,
                        "contract_id": contract_id,
                        "user_id": user_id,
                        "content_hash": content_hash,
                        "analysis_options_keys": sorted(list(analysis_options.keys())),
                        "workflow_initialized": getattr(
                            contract_service, "_workflow_initialized", None
                        ),
                        "latest_progress": latest_snapshot,
                        "service_enable_ws": getattr(
                            contract_service, "enable_websocket_progress", None
                        ),
                        "response_type": (
                            None
                            if analysis_response is None
                            else type(analysis_response).__name__
                        ),
                        "response_success": (
                            None
                            if analysis_response is None
                            else getattr(analysis_response, "success", None)
                        ),
                        "response_error": (
                            None
                            if analysis_response is None
                            else getattr(analysis_response, "error", None)
                        ),
                        "response_warnings": (
                            None
                            if analysis_response is None
                            else getattr(analysis_response, "warnings", None)
                        ),
                    },
                )
                raise ValueError(f"Contract analysis failed: {unified_error_msg}")

            # Get analysis results from the service response
            analysis_result = getattr(analysis_response, "analysis_results", {})
            final_state = getattr(analysis_response, "final_state", {})

            # Merge in missing keys from final_state to avoid false negatives during validation
            # Some nodes populate root-level state keys that may not be copied into analysis_results
            if isinstance(analysis_result, dict):
                merged_result = dict(analysis_result)
            else:
                merged_result = {}
            if isinstance(final_state, dict):
                for key in [
                    "contract_terms",
                    "risk_assessment",
                    "compliance_check",
                    "compliance_analysis",
                    "recommendations",
                    "final_validation_result",
                    "overall_confidence",
                    "final_workflow_confidence",
                ]:
                    if key not in merged_result or not merged_result.get(key):
                        value = final_state.get(key)
                        if value is not None:
                            merged_result[key] = value
            # Use merged result for downstream ops
            analysis_result = merged_result

            logger.info(f"Contract analysis completed successfully")

            # Coarse milestone after analysis to indicate we are persisting results
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=95,
                current_step="results_caching",
                step_description="Caching results for future use...",
                estimated_completion_minutes=0,
            )

            # (Already updated results_caching above with coarse milestone)

            # Save analysis results using AnalysesRepository
            analyses_repo = AnalysesRepository(use_service_role=True)

            # Validate analysis results before marking as completed
            has_meaningful_results = _validate_analysis_results(analysis_result)

            if has_meaningful_results:
                # Update analysis with results
                await analyses_repo.update_analysis_status(
                    analysis_id,
                    status="completed",
                    result=analysis_result,
                    completed_at=dt.datetime.now(dt.timezone.utc),
                )
            else:
                # Mark as failed if no meaningful results
                logger.warning(f"Analysis {analysis_id} produced no meaningful results")
                await analyses_repo.update_analysis_status(
                    analysis_id,
                    status="failed",
                    error_details={
                        "error_message": "Analysis produced no meaningful results - document processing may have failed"
                    },
                    completed_at=dt.datetime.now(dt.timezone.utc),
                )
                raise ValueError(
                    "Analysis produced no meaningful results - document processing failed"
                )

            # Step 9: Complete (95-100%) - only if we have meaningful results
            if has_meaningful_results:
                await update_analysis_progress(
                    user_id,
                    content_hash,
                    progress_percent=PROGRESS_STAGES["contract_analysis"][
                        "analysis_complete"
                    ],
                    current_step="analysis_complete",
                    step_description="Analysis completed successfully! Results are ready to view.",
                    estimated_completion_minutes=0,
                )
            else:
                # Mark as failed in progress tracking
                await update_analysis_progress(
                    user_id,
                    content_hash,
                    progress_percent=90,  # Keep at 90% to indicate processing issue
                    current_step="processing_failed",
                    step_description="Document processing failed - no meaningful content extracted.",
                    error_message="Document processing did not extract sufficient content for analysis",
                )

            # Send completion notification only if we have meaningful results
            if has_meaningful_results:
                # Normalize recommendations to a list for summary metrics
                _recs = analysis_result.get("recommendations")
                if isinstance(_recs, dict):
                    _rec_list = _recs.get("recommendations", [])
                elif isinstance(_recs, list):
                    _rec_list = _recs
                else:
                    _rec_list = []

                analysis_summary = {
                    "analysis_id": analysis_id,
                    "risk_score": analysis_result.get("risk_assessment", {}).get(
                        "overall_risk_score", 0.0
                    ),
                    "processing_time": getattr(analysis_response, "processing_time", 0)
                    or 0,
                    "recommendations_count": len(_rec_list),
                    "compliance_status": analysis_result.get(
                        "compliance_check",
                        analysis_result.get("compliance_analysis", {}),
                    ).get("state_compliance", False),
                }
                publish_progress_sync(
                    contract_id,
                    WebSocketEvents.analysis_completed(contract_id, analysis_summary),
                )
            else:
                # Send failure notification
                publish_progress_sync(
                    contract_id,
                    {
                        "event_type": "analysis_failed",
                        "data": {
                            "contract_id": contract_id,
                            "analysis_id": analysis_id,
                            "error_message": "Document processing failed - insufficient content extracted",
                        },
                    },
                )

            if has_meaningful_results:
                logger.info(
                    f"Comprehensive analysis completed successfully for contract {contract_id}"
                )
            else:
                logger.warning(
                    f"Comprehensive analysis failed for contract {contract_id} - no meaningful results"
                )

    except Exception as e:
        # Enhanced exception logging with full context chain
        root_cause = _extract_root_cause(e)
        context_info = {
            "document_id": document_id,
            "analysis_id": analysis_id,
            "contract_id": contract_id,
            "user_id": user_id,
            "exception_type": type(e).__name__,
            "root_cause_type": type(root_cause).__name__,
            "root_cause_message": str(root_cause),
            "full_exception_chain": _format_exception_chain(e),
        }

        logger.error(
            f"Comprehensive analysis failed: {str(e)}\nRoot cause: {str(root_cause)}",
            exc_info=True,
            extra=context_info,
        )

        # Update progress with error
        try:
            # Only attempt progress update if we have a content_hash
            if "content_hash" not in locals() or not content_hash:
                # Try to recover from analysis_options as last resort
                content_hash = analysis_options.get("content_hash")
            if content_hash:
                # Fetch the last progress to preserve resume information
                last_progress_percent = 0
                last_step = "unknown"
                try:
                    progress_repo = AnalysisProgressRepository()
                    latest_progress = await progress_repo.get_latest_progress(
                        content_hash, user_id, columns="current_step, progress_percent"
                    )
                    if latest_progress:
                        last_step = latest_progress.get("current_step", "unknown")
                        last_progress_percent = latest_progress.get(
                            "progress_percent", 0
                        )
                except Exception as fetch_err:
                    logger.warning(f"Could not fetch last progress: {fetch_err}")

                # Include root cause in error message for better debugging
                detailed_error_message = f"{str(e)} | Root cause: {str(root_cause)}"

                # Update progress preserving the last step and percentage for resume capability
                await update_analysis_progress(
                    user_id,
                    content_hash,
                    progress_percent=last_progress_percent,  # Preserve last progress
                    current_step=f"{last_step}_failed",  # Keep step info with failed suffix
                    step_description=f"Analysis failed at {last_step}. Ready to resume from this point.",
                    error_message=detailed_error_message,
                )

            # Update analysis record with enhanced error details
            analyses_repo = AnalysesRepository(use_service_role=True)
            await analyses_repo.update_analysis_status(
                analysis_id,
                status="failed",
                error_details={
                    "error_message": str(e),
                    "root_cause": str(root_cause),
                    "exception_type": type(e).__name__,
                    "root_cause_type": type(root_cause).__name__,
                    "failed_at_step": (
                        last_step if "last_step" in locals() else "unknown"
                    ),
                    "context": context_info,
                },
                completed_at=dt.datetime.now(dt.timezone.utc),
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update error status: {str(update_error)}",
                exc_info=True,
                extra={
                    "original_error": str(e),
                    "root_cause": (
                        str(root_cause) if "root_cause" in locals() else "unknown"
                    ),
                },
            )

        # Re-raise for Celery retry logic with preserved context
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
@user_aware_task
async def enhanced_reprocess_document_with_ocr_background(
    self,
    document_id: str,
    user_id: str,
    document: Dict[str, Any],
    contract_context: Dict[str, Any],
    processing_options: Dict[str, Any],
):
    """Background task for OCR reprocessing - USER AWARE VERSION

    This task maintains user authentication context throughout execution,
    ensuring all database operations respect RLS policies.
    """

    try:
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        # Initialize user-aware document service
        document_service = DocumentService()
        await document_service.initialize()

        # Get user-authenticated client (respects RLS)
        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        user_client = await document_service.get_user_client(isolated=True)

        # Update document status
        docs_repo = DocumentsRepository()
        await docs_repo.update_document_status(UUID(document_id), "reprocessing_ocr")

        # Send WebSocket notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_started",
                "data": {"document_id": document_id},
            },
        )

        # Enhanced OCR extraction with priority handling
        start_time = time.time()

        # Send progress update
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_progress",
                "data": {
                    "document_id": document_id,
                    "progress_percent": 10,
                    "current_step": "initializing_gemini_ocr",
                    "step_description": "Initializing Gemini 2.5 Pro OCR service",
                },
            },
        )

        # Enhanced OCR with contract-specific optimizations
        extraction_result = await document_service.extract_text_with_ocr(
            document["storage_path"],
            document["file_type"],
            contract_context=contract_context,
        )

        processing_time = time.time() - start_time

        # Enhanced result with performance metrics
        extraction_result["processing_details"] = {
            **extraction_result.get("processing_details", {}),
            "processing_time_seconds": processing_time,
            "priority_processing": processing_options.get("priority", False),
            "enhancement_level": (
                "premium" if processing_options.get("detailed_analysis") else "standard"
            ),
            "contract_context_applied": bool(contract_context),
            "gemini_model_used": "gemini-2.5-flash",
        }

        # Update document with OCR results
        await docs_repo.update_processing_status_and_results(
            UUID(document_id), "processed", extraction_result
        )

        # Send enhanced completion notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_completed",
                "data": {
                    "document_id": document_id,
                    "extraction_confidence": extraction_result.get(
                        "extraction_confidence", 0.0
                    ),
                    "character_count": extraction_result.get("character_count", 0),
                    "word_count": extraction_result.get("word_count", 0),
                    "extraction_method": extraction_result.get(
                        "extraction_method", "unknown"
                    ),
                    "processing_time_seconds": processing_time,
                    "contract_terms_detected": extraction_result.get(
                        "processing_details", {}
                    ).get("contract_terms_found", 0),
                    "enhancement_applied": extraction_result.get(
                        "processing_details", {}
                    ).get("enhancement_applied", []),
                    "quality_score": extraction_result.get(
                        "extraction_confidence", 0.0
                    ),
                },
            },
        )

        logger.info(f"OCR reprocessing completed for document {document_id}")

    except Exception as e:
        logger.error(f"OCR reprocessing failed for {document_id}: {str(e)}")

        # Update status to failed
        await docs_repo.update_processing_status_and_results(
            UUID(document_id), "ocr_failed", {"error": str(e)}
        )

        # Send error notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_failed",
                "data": {"document_id": document_id, "error_message": str(e)},
            },
        )


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
@user_aware_task
async def batch_ocr_processing_background(
    self,
    document_ids: List[str],
    user_id: str,
    batch_context: Dict[str, Any],
    processing_options: Dict[str, Any],
):
    """Background task for batch OCR processing with intelligent optimization - USER AWARE VERSION

    This task maintains user authentication context throughout execution,
    ensuring all database operations respect RLS policies.
    """

    batch_id = batch_context["batch_id"]
    total_docs = len(document_ids)
    processed_docs = 0
    start_time = time.time()

    try:
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        # Initialize user-aware document service
        document_service = DocumentService()
        await document_service.initialize()

        # Get user-authenticated client (respects RLS)
        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        user_client = await document_service.get_user_client(isolated=True)

        logger.info(f"Starting batch OCR processing for {total_docs} documents")

        # Initialize batch processing
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_started",
                "data": {
                    "batch_id": batch_id,
                    "total_documents": total_docs,
                    "processing_mode": (
                        "parallel"
                        if processing_options["parallel_processing"]
                        else "sequential"
                    ),
                },
            },
        )

        # Process documents with intelligent batching
        if processing_options["parallel_processing"] and total_docs > 1:
            # Parallel processing for multiple documents
            semaphore = asyncio.Semaphore(3)  # Limit concurrent processing

            async def process_single_doc(doc_id: str, index: int):
                nonlocal processed_docs
                async with semaphore:
                    try:
                        # Get document details
                        docs_repo = DocumentsRepository()
                        document = await docs_repo.get_document(UUID(doc_id))

                        if not document:
                            logger.warning(
                                f"Document {doc_id} not found in batch processing"
                            )
                            return

                        # Convert to dict for backward compatibility
                        document_dict = {
                            "storage_path": document.storage_path,
                            "file_type": document.file_type,
                        }

                        # Update document status
                        await docs_repo.update_document_status(
                            UUID(doc_id), "processing_ocr"
                        )

                        # Process with OCR
                        extraction_result = (
                            await document_service.extract_text_with_ocr(
                                document_dict["storage_path"],
                                document_dict["file_type"],
                                contract_context=batch_context,
                            )
                        )

                        # Update document with results
                        await docs_repo.update_processing_status_and_results(
                            UUID(doc_id), "processed", extraction_result
                        )

                        processed_docs += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to process document {doc_id} in batch: {str(e)}"
                        )

                        # Update document status to failed
                        await docs_repo.update_processing_status_and_results(
                            UUID(doc_id), "ocr_failed", {"error": str(e)}
                        )

            # Execute parallel processing
            tasks = [
                process_single_doc(doc_id, i) for i, doc_id in enumerate(document_ids)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        else:
            # Sequential processing
            for i, doc_id in enumerate(document_ids):
                try:
                    # Get document details
                    docs_repo = DocumentsRepository()
                    document = await docs_repo.get_document(UUID(doc_id))

                    if not document:
                        continue

                    # Update document status
                    await docs_repo.update_document_status(
                        UUID(doc_id), "processing_ocr"
                    )

                    # Process with OCR
                    extraction_result = await document_service.extract_text_with_ocr(
                        document.storage_path,
                        document.file_type,
                        contract_context=batch_context,
                    )

                    # Update document with results
                    await docs_repo.update_processing_status_and_results(
                        UUID(doc_id), "processed", extraction_result
                    )

                    processed_docs += 1

                    # Send progress update
                    await websocket_manager.send_message(
                        batch_id,
                        {
                            "event_type": "batch_progress",
                            "data": {
                                "batch_id": batch_id,
                                "processed_count": processed_docs,
                                "total_documents": total_docs,
                                "progress_percent": int(
                                    (processed_docs / total_docs) * 100
                                ),
                            },
                        },
                    )

                except Exception as e:
                    logger.error(f"Failed to process document {doc_id}: {str(e)}")
                    continue

        processing_time = time.time() - start_time

        # Send batch completion notification
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_completed",
                "data": {
                    "batch_id": batch_id,
                    "processed_documents": processed_docs,
                    "total_documents": total_docs,
                    "processing_time_seconds": processing_time,
                    "success_rate": (
                        (processed_docs / total_docs) * 100 if total_docs > 0 else 0
                    ),
                },
            },
        )

        logger.info(
            f"Batch OCR processing completed: {processed_docs}/{total_docs} documents"
        )

    except Exception as e:
        logger.error(f"Batch OCR processing failed: {str(e)}")

        # Send batch error notification
        await websocket_manager.send_message(
            batch_id,
            {
                "event_type": "batch_ocr_failed",
                "data": {
                    "batch_id": batch_id,
                    "error_message": str(e),
                    "processed_documents": processed_docs,
                    "total_documents": total_docs,
                },
            },
        )


@celery_app.task(bind=True)
@user_aware_task
async def generate_pdf_report(self, analysis_data: Dict[str, Any]) -> bytes:
    """Generate PDF report from analysis data - USER AWARE VERSION

    This task generates a PDF report from contract analysis results,
    maintaining user authentication context throughout execution.
    """
    try:
        logger.info("Starting PDF report generation")

        # Verify user context if user_id is provided in analysis_data
        if "user_id" in analysis_data:
            context_user_id = AuthContext.get_user_id()
            if context_user_id != analysis_data["user_id"]:
                raise ValueError(
                    f"User context mismatch: expected {analysis_data['user_id']}, got {context_user_id}"
                )

        # For now, return a structured text report until reportlab is added
        report_content = f"""
CONTRACT ANALYSIS REPORT
========================

Document: {analysis_data.get('filename', 'Unknown')}
Analysis Date: {analysis_data.get('analysis_date', 'Unknown')}
Risk Score: {analysis_data.get('risk_score', 'N/A')}

Executive Summary:
{analysis_data.get('executive_summary', 'No summary available')}

Recommendations:
{chr(10).join(f'- {rec}' for rec in analysis_data.get('recommendations', []))}

Generated by Real2.AI Contract Analysis Platform
        """.strip()

        logger.info("PDF report generation completed")
        return report_content.encode("utf-8")

    except Exception as e:
        logger.error(f"PDF report generation failed: {str(e)}")
        raise Exception(f"Report generation failed: {str(e)}")


def _validate_analysis_results(analysis_result: Dict[str, Any]) -> bool:
    """
    Validate that analysis results contain meaningful data indicating successful processing.

    Args:
        analysis_result: The analysis result dictionary

    Returns:
        bool: True if analysis contains meaningful results, False otherwise
    """
    try:
        if not analysis_result or not isinstance(analysis_result, dict):
            return False

        # 1) Contract terms present with any meaningful content
        contract_terms = analysis_result.get("contract_terms")
        if isinstance(contract_terms, dict) and contract_terms:
            meaningful_fields = [
                "purchase_price",
                "settlement_date",
                "property_address",
                "vendor_name",
                "purchaser_name",
                # Accept alternate/common keys as well
                "address",
                "price",
                "buyer_name",
                "seller_name",
            ]
            extracted_fields = 0
            for field in meaningful_fields:
                value = contract_terms.get(field)
                if (
                    value
                    and str(value).strip()
                    and str(value).strip() != "Not specified"
                ):
                    extracted_fields += 1
            if extracted_fields >= 1:
                return True

        # 2) Risk assessment present with score or level
        risk_assessment = analysis_result.get("risk_assessment")
        if isinstance(risk_assessment, dict) and risk_assessment:
            overall_risk_level = risk_assessment.get("overall_risk_level")
            overall_risk_score = risk_assessment.get("overall_risk_score")
            if (overall_risk_level and overall_risk_level != "unknown") or (
                isinstance(overall_risk_score, (int, float)) and overall_risk_score > 0
            ):
                return True

        # 3) Compliance present under either key used by the service
        compliance = analysis_result.get("compliance_check") or analysis_result.get(
            "compliance_analysis"
        )
        if isinstance(compliance, dict) and compliance:
            if compliance.get("state_compliance") is not None:
                return True
            # Also accept presence of specific checks/issues
            if compliance.get("issues") or compliance.get("warnings"):
                return True

        # 4) Recommendations present (list or object with list)
        recommendations = analysis_result.get("recommendations")
        if isinstance(recommendations, list) and len(recommendations) > 0:
            return True
        if isinstance(recommendations, dict):
            rec_list = recommendations.get("recommendations", [])
            if isinstance(rec_list, list) and len(rec_list) > 0:
                return True

        # 5) Final validation status indicates a good result
        final_validation = analysis_result.get("final_validation_result")
        if isinstance(final_validation, dict) and final_validation.get(
            "validation_passed"
        ):
            return True

        # 6) Confidence signals
        overall_confidence = analysis_result.get("overall_confidence")
        final_workflow_confidence = analysis_result.get("final_workflow_confidence")
        if (
            isinstance(overall_confidence, (int, float)) and overall_confidence >= 0.5
        ) or (
            isinstance(final_workflow_confidence, (int, float))
            and final_workflow_confidence >= 0.5
        ):
            return True

        return False

    except Exception as e:
        logger.warning(f"Error validating analysis results: {e}")
        return False
