"""Background tasks for document processing and contract analysis.

MIGRATED VERSION: Now uses user-aware architecture with proper context propagation.
All tasks use @user_aware_task decorator to maintain user authentication context.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.core.celery import celery_app
from app.core.task_context import user_aware_task, task_manager
from app.core.auth_context import AuthContext
from app.core.langsmith_config import langsmith_session, log_trace_info
from app.core.config import get_settings
from app.clients.factory import get_service_supabase_client
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.models.contract_state import (
    AustralianState,
    create_initial_state,
)
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

logger = logging.getLogger(__name__)


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
            "step_started_at": datetime.now(timezone.utc),
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

        # Resolve session ids (document_ids) for WS delivery and send progress
        # Send to ALL documents with this content_hash since multiple uploads may exist
        try:
            # Find ALL documents for this user/content_hash to route messages
            docs_repo = DocumentsRepository()
            documents = await docs_repo.get_documents_by_content_hash(
                content_hash, user_id, columns="id"
            )
            logger.debug(
                "[update_analysis_progress] Documents for WS routing",
                extra={
                    "content_hash": content_hash,
                    "user_id": user_id,
                    "doc_count": len(documents) if documents is not None else 0,
                },
            )
            if documents:
                # Send to all documents with this content_hash
                for doc in documents:
                    session_id = (
                        str(doc["id"]) if isinstance(doc, dict) else str(doc.id)
                    )
                    logger.info(
                        f"Sending progress to document {session_id} for content_hash {content_hash}"
                    )
                    await websocket_manager.send_message(
                        session_id,
                        {
                            "event_type": "analysis_progress",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": {
                                "content_hash": content_hash,
                                "progress_percent": progress_percent,
                                "current_step": current_step,
                                "step_description": step_description,
                                "estimated_completion_minutes": estimated_completion_minutes,
                                "status": status,  # Include status in WebSocket message
                                "error_message": error_message,
                            },
                        },
                    )
        except Exception as ws_error:
            logger.warning(f"WS progress routing failed: {ws_error}")

        # Send Redis pub/sub update using content_hash as channel identifier
        publish_progress_sync(
            content_hash,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "content_hash": content_hash,
                    "progress_percent": progress_percent,
                    "current_step": current_step,
                    "step_description": step_description,
                    "estimated_completion_minutes": estimated_completion_minutes,
                    "status": status,  # Use the same status determined above
                },
            },
        )

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
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

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
            # Use isolated client to prevent JWT token race conditions in concurrent tasks
            user_client = await document_service.get_user_client(isolated=True)

            # Get document record
            docs_repo = DocumentsRepository()
            document = await docs_repo.get_document(UUID(document_id))
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

            analysis_response = await contract_service.start_analysis(
                user_id=user_id,
                session_id=content_hash,  # Use content_hash as session_id
                document_data=document_data,
                australian_state=state_to_use,
                user_preferences=analysis_options,
                user_type="buyer",  # Default user type
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
                    error_details={"error_message": "Analysis produced no meaningful results - document processing may have failed"},
                    completed_at=datetime.now(timezone.utc),
                )
                raise ValueError("Analysis produced no meaningful results - document processing failed")

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
                analysis_summary = {
                    "analysis_id": analysis_id,
                    "risk_score": analysis_result.get("risk_assessment", {}).get(
                        "overall_risk_score", 0.0
                    ),
                    "processing_time": getattr(analysis_response, "processing_time", 0)
                    or 0,
                    "recommendations_count": len(
                        analysis_result.get("recommendations", [])
                    ),
                    "compliance_status": analysis_result.get("compliance_check", {}).get(
                        "state_compliance", False
                    ),
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
                            "error_message": "Document processing failed - insufficient content extracted"
                        }
                    }
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
        logger.error(f"Comprehensive analysis failed: {str(e)}", exc_info=True)

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

                # Update progress preserving the last step and percentage for resume capability
                await update_analysis_progress(
                    user_id,
                    content_hash,
                    progress_percent=last_progress_percent,  # Preserve last progress
                    current_step=f"{last_step}_failed",  # Keep step info with failed suffix
                    step_description=f"Analysis failed at {last_step}. Ready to resume from this point.",
                    error_message=str(e),
                )

            # Update analysis record with error using AnalysesRepository
            analyses_repo = AnalysesRepository(use_service_role=True)
            await analyses_repo.update_analysis_status(
                analysis_id,
                status="failed",
                error_details={"error_message": str(e)},
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as update_error:
            logger.error(f"Failed to update error status: {str(update_error)}")

        # Re-raise for Celery retry logic
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
        
        # Check for contract terms with meaningful content
        contract_terms = analysis_result.get("contract_terms", {})
        if contract_terms and isinstance(contract_terms, dict):
            # Look for at least some extracted contract data
            meaningful_fields = [
                "purchase_price",
                "settlement_date",
                "property_address", 
                "vendor_name",
                "purchaser_name"
            ]
            
            extracted_fields = 0
            for field in meaningful_fields:
                value = contract_terms.get(field)
                if value and str(value).strip() and str(value).strip() != "Not specified":
                    extracted_fields += 1
            
            # Require at least 2 meaningful contract terms
            if extracted_fields >= 2:
                return True
        
        # Check for risk assessment results
        risk_assessment = analysis_result.get("risk_assessment", {})
        if risk_assessment and isinstance(risk_assessment, dict):
            overall_risk = risk_assessment.get("overall_risk_level")
            if overall_risk and overall_risk != "unknown":
                return True
        
        # Check for compliance analysis
        compliance = analysis_result.get("compliance_analysis", {})
        if compliance and isinstance(compliance, dict):
            state_compliance = compliance.get("state_compliance")
            if state_compliance is not None:  # Can be True or False
                return True
        
        # Check for any recommendations
        recommendations = analysis_result.get("recommendations", {})
        if recommendations and isinstance(recommendations, dict):
            rec_list = recommendations.get("recommendations", [])
            if rec_list and len(rec_list) > 0:
                return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Error validating analysis results: {e}")
        return False
