"""Comprehensive document analysis task for contract processing."""

import asyncio
import logging
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.core.celery import celery_app
from app.core.task_context import user_aware_task
from app.core.auth_context import AuthContext
from app.core.langsmith_config import langsmith_session
from app.core.async_utils import langgraph_safe_task
from app.services.contract_analysis_service import ContractAnalysisService
from app.services.document_service import DocumentService
from app.services.communication.websocket_singleton import websocket_manager
from app.services.communication.redis_pubsub import publish_progress_sync
from app.services.communication.websocket_service import WebSocketEvents
from app.core.task_recovery import CheckpointData
from app.services.repositories.analyses_repository import AnalysesRepository
from app.services.repositories.analysis_progress_repository import (
    AnalysisProgressRepository,
)
from app.services.repositories.documents_repository import DocumentsRepository
from .utils import (
    update_analysis_progress,
    _extract_root_cause,
    _format_exception_chain,
    _validate_analysis_results,
    PROGRESS_STAGES,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=2)
@langgraph_safe_task
async def comprehensive_document_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str,
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
):
    """
    Comprehensive document processing and analysis with detailed progress tracking.

    This task combines:
    1. Document processing (text extraction, OCR, page analysis)
    2. Contract analysis (AI workflow)
    3. Real-time progress updates
    4. Result caching
    """
    try:
        # User ID is passed explicitly as parameter - no need for context validation
        # in the per-loop registry design with isolated execution

        logger.info(
            f"Starting comprehensive analysis for user {user_id}, document {document_id}, analysis {analysis_id}"
        )

        async with langsmith_session(
            "comprehensive_document_analysis",
            document_id=document_id,
            analysis_id=analysis_id,
            contract_id=contract_id,
            user_id=user_id,
        ):

            # Initialize services
            document_service = DocumentService(use_llm_document_processing=True)
            await document_service.initialize()
            # Note: No user client needed - repositories use explicit user_id parameters

            # Get document record with explicit user_id for safety
            docs_repo = DocumentsRepository(user_id=UUID(user_id))
            document = await docs_repo.get_document(UUID(document_id), user_id=UUID(user_id))
            if not document:
                raise Exception("Document not found or access denied")
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
                raise Exception(
                    "Content hash not found in document or analysis options"
                )

            # Determine resume point from latest analysis_progress (if any)
            try:
                progress_repo = AnalysisProgressRepository(user_id=user_id)
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
                logger.warning(
                    f"Unable to fetch latest progress for resume: {resume_err}"
                )

            # Prefer explicit task checkpoint (if available) to determine precise resume step
            try:
                if hasattr(recovery_ctx, "registry") and hasattr(
                    recovery_ctx, "task_id"
                ):
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
                logger.info("New analysis: starting from queued at 5%")

            # Keep the task context fresh for long-running operations
            await recovery_ctx.refresh_context_ttl()

            # =============================================
            # PHASE 2: CONTRACT ANALYSIS (75-100%)
            # =============================================

            # Step: Contract Analysis Start (coarse milestone)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=10,
                current_step="contract_analysis",
                step_description="Starting AI contract analysis...",
                estimated_completion_minutes=1,
            )

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
                enable_websocket_progress=True,  # Let service handle progress updates
            )

            # Execute contract analysis using the service layer
            logger.info(f"Starting contract analysis with document data")

            async def persist_progress(step: str, percent: int, description: str):
                # Persist to Supabase, update recovery registry, create checkpoint, then refresh task TTL
                try:
                    # 1) Persist user-facing progress (DB + WS/Redis)
                    await update_analysis_progress(
                        user_id,
                        content_hash,
                        progress_percent=percent,
                        current_step=step,
                        step_description=description,
                        estimated_completion_minutes=None,
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

            # Execute contract analysis with automatic isolation via @langgraph_safe_task
            logger.info(f"Starting contract analysis for analysis {analysis_id}")
            
            analysis_response = await contract_service.start_analysis(
                user_id=user_id,
                session_id=content_hash,
                document_data=document_data,
                australian_state=state_to_use,
                user_preferences=analysis_options,
                user_type="buyer",
                progress_callback=persist_progress,
            )

            # Handle None response
            if analysis_response is None:
                error_msg = "Contract analysis service returned None"
                logger.error(error_msg)
                raise ValueError(f"Contract analysis failed: {error_msg}")

            # Extract analysis results from service response
            # StartAnalysisResponse object - access attributes directly
            if not analysis_response.success:
                # Ensure we have a non-empty error message even if the field exists but is None/empty
                error_msg = (
                    getattr(analysis_response, "error", None)
                    or "Contract analysis failed"
                )
                logger.error(f"Contract analysis failed: {error_msg}")
                raise ValueError(f"Contract analysis failed: {error_msg}")

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
                    completed_at=datetime.now(timezone.utc),
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
                    completed_at=datetime.now(timezone.utc),
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
                    progress_repo = AnalysisProgressRepository(user_id=user_id)
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
                completed_at=datetime.now(timezone.utc),
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