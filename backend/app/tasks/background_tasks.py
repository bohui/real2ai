"""Background tasks for document processing and contract analysis.

MIGRATED VERSION: Now uses user-aware architecture with proper context propagation.
All tasks use @user_aware_task decorator to maintain user authentication context.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.celery import celery_app
from app.core.task_context import user_aware_task, task_manager
from app.core.auth_context import AuthContext
from app.models.contract_state import (
    RealEstateAgentState,
    AustralianState,
    ContractType,
    create_initial_state,
)
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.services.document_service import DocumentService
from app.services.websocket_service import WebSocketEvents
from app.services.websocket_singleton import websocket_manager
from app.services.redis_pubsub import publish_progress_sync
from app.core.langsmith_config import langsmith_session, log_trace_info

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
        user_client = await AuthContext.get_authenticated_client()

        # Update or create progress record
        progress_data = {
            "content_hash": content_hash,
            "user_id": user_id,
            "current_step": current_step,
            "progress_percent": progress_percent,
            "step_description": step_description,
            "step_started_at": datetime.now(timezone.utc).isoformat(),
            "estimated_completion_minutes": estimated_completion_minutes,
            "status": "in_progress" if progress_percent < 100 else "completed",
            "error_message": error_message,
        }

        # Upsert progress record using content_hash + user_id unique constraint
        result = await user_client.database.upsert(
            "analysis_progress",
            progress_data,
            conflict_columns=["content_hash", "user_id"],
        )

        # Resolve a session id (document_id) for WS delivery and send progress
        try:
            # Find the latest document for this user/content_hash to route messages
            doc_result = await user_client.database.select(
                "documents",
                columns="id",
                filters={"user_id": user_id, "content_hash": content_hash},
                order_by="created_at DESC",
                limit=1,
            )
            if doc_result.get("data"):
                session_id = doc_result["data"][0]["id"]
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
                "type": "analysis_progress",
                "content_hash": content_hash,
                "progress": progress_percent,
                "current_step": current_step,
                "step_description": step_description,
                "estimated_completion_minutes": estimated_completion_minutes,
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
            document_service = DocumentService()
            await document_service.initialize()
            user_client = await document_service.get_user_client()

            # Get document record
            doc_result = await user_client.database.select(
                "documents", columns="*", filters={"id": document_id}
            )
            if not doc_result.get("data"):
                raise Exception("Document not found or access denied")
            document = doc_result["data"][0]

            # Get content_hash for progress tracking
            content_hash = analysis_options.get("content_hash") or document.get(
                "content_hash"
            )
            if not content_hash:
                raise Exception(
                    "Content hash not found in document or analysis options"
                )

            # =============================================
            # PHASE 1: DOCUMENT PROCESSING (0-75%)
            # =============================================

            # Step 1: Text Extraction (0-25%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=5,
                current_step="text_extraction",
                step_description="Extracting text from document...",
                estimated_completion_minutes=3,
            )

            # Extract text with comprehensive analysis
            extraction_result = (
                await document_service._extract_text_with_comprehensive_analysis(
                    document_id=document_id,
                    storage_path=document["storage_path"],
                    file_type=document["file_type"],
                )
            )

            if not extraction_result.get("success"):
                error_msg = f"Text extraction failed: {extraction_result.get('error', 'Unknown error')}"
                await update_analysis_progress(
                    user_id,
                    content_hash,
                    progress_percent=0,
                    current_step="text_extraction",
                    step_description="Text extraction failed",
                    error_message=error_msg,
                )
                raise Exception(error_msg)

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["document_processing"][
                    "text_extraction"
                ],
                current_step="text_extraction",
                step_description="Text extraction completed successfully",
                estimated_completion_minutes=2,
            )

            # Step 2: Page Analysis (25-50%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=30,
                current_step="page_analysis",
                step_description="Analyzing document pages and content...",
                estimated_completion_minutes=2,
            )

            # Save page data to database
            await document_service._save_document_pages(
                document_id, extraction_result, content_hash
            )

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["document_processing"][
                    "page_analysis"
                ],
                current_step="page_analysis",
                step_description="Page analysis completed successfully",
                estimated_completion_minutes=2,
            )

            # Step 3: Diagram Detection (50-60%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=55,
                current_step="diagram_detection",
                step_description="Detecting and analyzing diagrams...",
                estimated_completion_minutes=1,
            )

            # Process diagrams
            await document_service._save_document_diagrams(
                document_id, extraction_result
            )

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["document_processing"][
                    "diagram_detection"
                ],
                current_step="diagram_detection",
                step_description="Diagram detection completed",
                estimated_completion_minutes=1,
            )

            # Step 4: Entity Extraction (60-70%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=65,
                current_step="entity_extraction",
                step_description="Extracting key entities and terms...",
                estimated_completion_minutes=1,
            )

            # Update document metrics
            diagram_result = document_service._aggregate_diagram_detections(
                extraction_result
            )
            await document_service._update_document_metrics(
                document_id, extraction_result, diagram_result
            )

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["document_processing"][
                    "entity_extraction"
                ],
                current_step="entity_extraction",
                step_description="Entity extraction completed",
                estimated_completion_minutes=1,
            )

            # Step 5: Document Processing Complete (70-75%)
            await user_client.database.update(
                "documents",
                document_id,
                {"processing_status": "basic_complete"},
            )

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["document_processing"][
                    "document_complete"
                ],
                current_step="document_complete",
                step_description="Document processing completed successfully",
                estimated_completion_minutes=1,
            )

            # =============================================
            # PHASE 2: CONTRACT ANALYSIS (75-100%)
            # =============================================

            # Step 6: Contract Analysis Start (75-80%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["contract_analysis"]["analysis_start"],
                current_step="contract_analysis",
                step_description="Starting AI contract analysis...",
                estimated_completion_minutes=1,
            )

            # Initialize contract workflow
            from app.core.config import get_settings

            settings = get_settings()
            contract_workflow = ContractAnalysisWorkflow(
                openai_api_key=settings.openai_api_key,
                model_name="gpt-4",
                openai_api_base=settings.openai_api_base,
            )

            # Update analysis status
            await user_client.database.update(
                "contract_analyses", analysis_id, {"status": "processing"}
            )

            # Step 7: Workflow Processing (80-90%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=85,
                current_step="workflow_processing",
                step_description="AI is analyzing your contract for risks and compliance...",
                estimated_completion_minutes=1,
            )

            # Get contract details
            contract_result = await user_client.database.select(
                "contracts", columns="*", filters={"id": contract_id}
            )
            contract_data = (
                contract_result["data"][0] if contract_result.get("data") else {}
            )

            # Create contract analysis state
            contract_state = create_initial_state(
                user_id=user_id,
                australian_state=AustralianState(
                    contract_data.get("australian_state", "NSW")
                ),
                user_type="buyer",  # Default user type
                user_preferences=analysis_options,  # Pass analysis options as user preferences
            )

            # Execute contract analysis workflow
            analysis_result = await contract_workflow.analyze_contract(contract_state)

            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["contract_analysis"][
                    "workflow_processing"
                ],
                current_step="workflow_processing",
                step_description="Contract analysis completed, preparing results...",
                estimated_completion_minutes=0,
            )

            # Step 8: Results Caching (90-95%)
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=PROGRESS_STAGES["contract_analysis"][
                    "results_caching"
                ],
                current_step="results_caching",
                step_description="Caching results for future use...",
                estimated_completion_minutes=0,
            )

            # Save analysis results
            analysis_update = {
                "status": "completed",
                "analysis_result": analysis_result.get("analysis", {}),
                "risk_score": analysis_result.get("risk_score", 0.0),
                "processing_time": (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(
                        doc_result["data"][0]["created_at"].replace("Z", "+00:00")
                    )
                ).total_seconds(),
                "processing_completed_at": datetime.now(timezone.utc).isoformat(),
            }

            await user_client.database.update(
                "contract_analyses", analysis_id, analysis_update
            )

            # Step 9: Complete (95-100%)
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

            # Send completion notification
            analysis_summary = {
                "analysis_id": analysis_id,
                "risk_score": analysis_result.get("risk_score", 0.0),
                "processing_time": analysis_update["processing_time"],
            }
            publish_progress_sync(
                contract_id,
                WebSocketEvents.analysis_completed(contract_id, analysis_summary),
            )

            logger.info(
                f"Comprehensive analysis completed successfully for contract {contract_id}"
            )

    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {str(e)}", exc_info=True)

        # Update progress with error
        try:
            await update_analysis_progress(
                user_id,
                content_hash,
                progress_percent=0,
                current_step="failed",
                step_description="Analysis failed. Please try again or contact support.",
                error_message=str(e),
            )

            # Update analysis record with error
            user_client = await AuthContext.get_authenticated_client()
            await user_client.database.update(
                "contract_analyses",
                analysis_id,
                {
                    "status": "failed",
                    "error_message": str(e),
                    "processing_completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as update_error:
            logger.error(f"Failed to update error status: {str(update_error)}")

        # Re-raise for Celery retry logic
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
@user_aware_task
async def process_document_background(
    self,
    document_id: str,
    user_id: str,
    australian_state: str,
    contract_type: str,
):
    """Background task for document processing - USER AWARE VERSION

    This task maintains user authentication context throughout execution,
    ensuring all database operations respect RLS policies.
    """
    task_start = datetime.now(timezone.utc)

    try:
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        logger.info(
            f"Starting document processing for user {user_id}, document {document_id}"
        )
        async with langsmith_session(
            "background_document_processing",
            document_id=document_id,
            user_id=user_id,
            australian_state=australian_state,
            contract_type=contract_type,
        ):
            try:
                log_trace_info(
                    "background_document_processing",
                    document_id=document_id,
                    user_id=user_id,
                    australian_state=australian_state,
                    contract_type=contract_type,
                )
                # Initialize user-aware document service
                document_service = DocumentService()
                await document_service.initialize()

                # Get user-authenticated client (respects RLS)
                user_client = await document_service.get_user_client()

                # Update document status (user context - RLS enforced)
                await user_client.update(
                    "documents",
                    {"id": document_id},
                    {"processing_status": "processing"},
                )

                # Get document metadata (user context - RLS enforced)
                doc_result = await user_client.database.select(
                    "documents", columns="*", filters={"id": document_id}
                )
                if not doc_result.get("data"):
                    raise Exception("Document not found or access denied")

                document = doc_result["data"][0]

                # Log the operation for audit trail
                document_service.log_operation("process", "document", document_id)

                # Verify file exists in storage before processing (user context)
                try:
                    file_content = await user_client.download_file(
                        bucket="documents", path=document["storage_path"]
                    )
                    if not file_content:
                        raise Exception("Empty file content")
                except Exception as storage_error:
                    # If file doesn't exist, mark document as failed and clean up
                    logger.error(
                        f"File not found in storage for document {document_id}: {document['storage_path']}"
                    )

                    # Mark document as failed with specific error (user context - RLS enforced)
                    await user_client.update(
                        "documents",
                        {"id": document_id},
                        {
                            "status": "failed",
                            "processing_results": {
                                "error": "File not found in storage - orphaned record",
                                "storage_path": document["storage_path"],
                                "cleanup_required": True,
                            },
                        },
                    )

                    raise Exception(
                        f"File not found in storage: {document['storage_path']}"
                    )

                # Extract text from document with contract context (user context preserved)
                contract_context = {
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                    "user_type": "buyer",  # Could be derived from user profile
                }

                # Use the migrated DocumentService method (preserves user context)
                extraction_result = (
                    await document_service._extract_text_with_comprehensive_analysis(
                        document_id=document_id,
                        storage_path=document["storage_path"],
                        file_type=document["file_type"],
                    )
                )

                # Update document with extraction results (user context - RLS enforced)
                await user_client.update(
                    "documents",
                    {"id": document_id},
                    {"status": "processed", "processing_results": extraction_result},
                )

                # Send WebSocket notification via Redis Pub/Sub
                publish_progress_sync(
                    document_id,
                    {
                        "event_type": "document_processed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "document_id": document_id,
                            "extraction_confidence": extraction_result.get(
                                "extraction_confidence", 0.0
                            ),
                            "character_count": extraction_result.get(
                                "character_count", 0
                            ),
                            "word_count": extraction_result.get("word_count", 0),
                        },
                    },
                )

                # Also send via WebSocket manager for immediate delivery (if connected)
                await websocket_manager.send_message(
                    document_id,
                    {
                        "event_type": "document_processed",
                        "data": {
                            "document_id": document_id,
                            "extraction_confidence": extraction_result.get(
                                "extraction_confidence", 0.0
                            ),
                            "character_count": extraction_result.get(
                                "character_count", 0
                            ),
                            "word_count": extraction_result.get("word_count", 0),
                        },
                    },
                )

                logger.info(f"Document {document_id} processed successfully")

            except Exception as e:
                logger.error(f"Document processing failed for {document_id}: {str(e)}")

                # Update document status to failed (user context - RLS enforced)
                try:
                    await user_client.update(
                        "documents",
                        {"id": document_id},
                        {"status": "failed", "processing_results": {"error": str(e)}},
                    )
                except Exception as update_error:
                    logger.error(f"Failed to update document status: {update_error}")

                # Send error notification via Redis Pub/Sub
                publish_progress_sync(
                    document_id,
                    {
                        "event_type": "document_processing_failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {"document_id": document_id, "error_message": str(e)},
                    },
                )

                # Also send via WebSocket manager for immediate delivery (if connected)
                await websocket_manager.send_message(
                    document_id,
                    {
                        "event_type": "document_processing_failed",
                        "data": {"document_id": document_id, "error_message": str(e)},
                    },
                )

                # Re-raise the exception to trigger task retry
                raise Exception(f"Document processing failed: {str(e)}")

    except Exception as e:
        processing_time = (datetime.now(timezone.utc) - task_start).total_seconds()

        logger.error(
            f"Document processing failed for user {user_id}, document {document_id}: {e}",
            exc_info=True,
        )

        # Return error result for task status
        raise Exception(f"Document processing failed: {str(e)}")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
@user_aware_task
async def analyze_contract_background(
    self,
    contract_id: str,
    analysis_id: str,
    user_id: str,
    document: Dict[str, Any],
    analysis_options: Dict[str, Any],
):
    """Background task for contract analysis - USER AWARE VERSION

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

        logger.info(
            f"Starting contract analysis for user {user_id}, contract {contract_id}"
        )
        from app.core.config import get_settings

        settings = get_settings()
        contract_workflow = ContractAnalysisWorkflow(
            openai_api_key=settings.openai_api_key,
            model_name="gpt-4",
            openai_api_base=settings.openai_api_base,
        )

        # Initialize user-aware document service
        document_service = DocumentService()
        await document_service.initialize()

        # Get user-authenticated client (respects RLS)
        user_client = await document_service.get_user_client()

        # Update analysis status (user context - RLS enforced)
        await user_client.update(
            "contract_analyses", {"id": analysis_id}, {"status": "processing"}
        )

        # Log the operation for audit trail
        document_service.log_operation("analyze", "contract", contract_id)

        # Derive session id for WebSocket/Redis routing (standardize on document_id)
        session_id = document.get("id") if isinstance(document, dict) else contract_id

        # Send analysis_started event via Redis Pub/Sub (route via document session id)
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "estimated_time_minutes": 5,
                    "message": "Analysis started",
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_started(contract_id, estimated_time=5),
        )

        # Get user profile for context
        user_result = await user_client.database.select(
            "profiles", columns="*", filters={"id": user_id}
        )
        user_profile = (
            user_result.get("data", [{}])[0] if user_result.get("data") else {}
        )

        # Check user credits before processing
        if user_profile.get("subscription_status") == "free":
            credits_remaining = user_profile.get("credits_remaining", 0)
            if credits_remaining <= 0:
                raise Exception("quota_error - Insufficient credits or quota exceeded.")

        # Progress update: Initial validation complete via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "validating_input",
                    "progress_percent": 10,
                    "step_description": "Validating user credentials and document access",
                    "estimated_completion_minutes": 5,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "validating_input",
                10,
                "Validating user credentials and document access",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "validating_input",
                    "p_progress_percent": 10,
                    "p_step_description": "Validating user credentials and document access",
                    "p_estimated_completion_minutes": 5,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Verify document file exists in storage before processing
        try:
            await document_service.get_file_content(document["storage_path"])
        except Exception as storage_error:
            logger.error(
                f"Document file not found in storage: {document['storage_path']}"
            )
            # Continue with analysis if we have extracted text, otherwise fail
            if not document.get("processing_results", {}).get("extracted_text"):
                raise Exception(
                    f"File not found and no extracted text available: {document['storage_path']}"
                )

        # Progress update: Setting up analysis context via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "processing_document",
                    "progress_percent": 20,
                    "step_description": "Setting up analysis context and extracting document content",
                    "estimated_completion_minutes": 4,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "processing_document",
                20,
                "Setting up analysis context and extracting document content",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "processing_document",
                    "p_progress_percent": 20,
                    "p_step_description": "Setting up analysis context and extracting document content",
                    "p_estimated_completion_minutes": 4,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Create initial state
        initial_state = create_initial_state(
            user_id=user_id,
            australian_state=AustralianState(
                user_profile.get("australian_state", "NSW")
            ),
            user_type=user_profile.get("user_type", "buyer"),
            user_preferences=user_profile.get("preferences", {}),
        )

        # Get processed document content
        processing_results = document.get("processing_results", {})
        extracted_text = processing_results.get("extracted_text", "")
        extraction_confidence = processing_results.get("extraction_confidence", 0.0)

        if not extracted_text or extraction_confidence < 0.5:
            # If no extracted text or low confidence, try enhanced extraction
            contract_context = {
                "australian_state": user_profile.get("australian_state", "NSW"),
                "contract_type": "purchase_agreement",
                "user_type": user_profile.get("user_type", "buyer"),
            }

            # Use OCR if confidence is low or text is missing
            force_ocr = extraction_confidence < 0.5
            extraction_result = await document_service.extract_text(
                document["storage_path"],
                document["file_type"],
                contract_context=contract_context,
                force_ocr=force_ocr,
            )
            extracted_text = extraction_result.get("extracted_text", "")

            # Update document with improved extraction results
            if (
                extraction_result.get("extraction_confidence", 0)
                > extraction_confidence
            ):
                await user_client.update(
                    "documents",
                    {"id": document["id"]},
                    {"processing_results": extraction_result},
                )

        # Progress update: Preparing document for analysis via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "extracting_terms",
                    "progress_percent": 40,
                    "step_description": "Preparing document content for AI analysis",
                    "estimated_completion_minutes": 3,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "extracting_terms",
                40,
                "Preparing document content for AI analysis",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "extracting_terms",
                    "p_progress_percent": 40,
                    "p_step_description": "Preparing document content for AI analysis",
                    "p_estimated_completion_minutes": 3,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Add document data to state
        initial_state["document_data"] = {
            "document_id": document["id"],
            "filename": document["filename"],
            "content": extracted_text,
            "storage_path": document["storage_path"],
            "file_type": document["file_type"],
        }

        # Progress update: Starting AI analysis via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "analyzing_compliance",
                    "progress_percent": 60,
                    "step_description": "AI is analyzing contract terms and compliance requirements",
                    "estimated_completion_minutes": 2,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "analyzing_compliance",
                60,
                "AI is analyzing contract terms and compliance requirements",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "analyzing_compliance",
                    "p_progress_percent": 60,
                    "p_step_description": "AI is analyzing contract terms and compliance requirements",
                    "p_estimated_completion_minutes": 2,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Run analysis workflow
        final_state = await contract_workflow.analyze_contract(initial_state)

        # Progress update: Generating risk assessment via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "assessing_risks",
                    "progress_percent": 80,
                    "step_description": "Evaluating potential risks and generating insights",
                    "estimated_completion_minutes": 1,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "assessing_risks",
                80,
                "Evaluating potential risks and generating insights",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "assessing_risks",
                    "p_progress_percent": 80,
                    "p_step_description": "Evaluating potential risks and generating insights",
                    "p_estimated_completion_minutes": 1,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Progress update: Compiling final report via Redis Pub/Sub
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "current_step": "compiling_report",
                    "progress_percent": 95,
                    "step_description": "Finalizing analysis report and recommendations",
                    "estimated_completion_minutes": 0,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_progress(
                contract_id,
                "compiling_report",
                95,
                "Finalizing analysis report and recommendations",
            ),
        )

        # Save progress to database
        try:
            await user_client.execute_rpc(
                "update_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_user_id": user_id,
                    "p_current_step": "compiling_report",
                    "p_progress_percent": 95,
                    "p_step_description": "Finalizing analysis report and recommendations",
                    "p_estimated_completion_minutes": 0,
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to save progress to database: {str(progress_error)}"
            )

        # Update analysis results
        analysis_result = final_state.get("analysis_results", {})

        # Update with both old and new column names for compatibility
        await user_client.update(
            "contract_analyses",
            {"id": analysis_id},
            {
                "status": "completed",
                "analysis_result": analysis_result,
                "executive_summary": analysis_result.get("executive_summary", {}),
                "risk_assessment": analysis_result.get("risk_assessment", {}),
                "compliance_check": analysis_result.get("compliance_check", {}),
                "recommendations": analysis_result.get("recommendations", []),
                "risk_score": analysis_result.get("risk_assessment", {}).get(
                    "overall_risk_score", 0
                ),
                "overall_risk_score": analysis_result.get("risk_assessment", {}).get(
                    "overall_risk_score", 0
                ),
                "confidence_score": analysis_result.get("executive_summary", {}).get(
                    "confidence_level", 0
                ),
                "confidence_level": analysis_result.get("executive_summary", {}).get(
                    "confidence_level", 0
                ),
                "processing_time": final_state.get("processing_time", 0),
                "processing_time_seconds": final_state.get("processing_time", 0),
            },
        )

        # Deduct user credit only if analysis was successful
        if user_profile.get("subscription_status") == "free":
            new_credits = max(0, user_profile.get("credits_remaining", 0) - 1)
            await user_client.update(
                "profiles", {"id": user_id}, {"credits_remaining": new_credits}
            )

            # Log usage only if deduction was successful
            try:
                await user_client.insert(
                    "usage_logs",
                    {
                        "user_id": user_id,
                        "action_type": "contract_analysis",
                        "credits_used": 1,
                        "credits_remaining": new_credits,
                    },
                )
            except Exception as log_error:
                logger.warning(
                    f"Failed to log usage for user {user_id}: {str(log_error)}"
                )

        # Send completion update via Redis Pub/Sub
        analysis_summary = {
            "overall_risk_score": analysis_result.get("risk_assessment", {}).get(
                "overall_risk_score", 0
            ),
            "total_recommendations": len(analysis_result.get("recommendations", [])),
            "compliance_status": (
                "compliant"
                if analysis_result.get("compliance_check", {}).get(
                    "state_compliance", False
                )
                else "non-compliant"
            ),
            "processing_time_seconds": final_state.get("processing_time", 0),
        }

        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "status": "completed",
                    "analysis_summary": analysis_summary,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_completed(contract_id, analysis_summary),
        )

        # Mark analysis as completed in database
        try:
            await user_client.execute_rpc(
                "complete_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_final_status": "completed",
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to mark analysis as completed in database: {str(progress_error)}"
            )

        logger.info(f"Contract analysis {analysis_id} completed successfully")

    except Exception as e:
        error_message = str(e)
        error_type = "general_error"

        # Classify error types for better handling
        if "openrouter" in error_message.lower() or "api" in error_message.lower():
            error_type = "llm_api_error"
            error_message = "LLM service temporarily unavailable. Please try again."
        elif "timeout" in error_message.lower():
            error_type = "timeout_error"
            error_message = "Analysis timed out. Document may be too complex."
        elif "rate limit" in error_message.lower():
            error_type = "rate_limit_error"
            error_message = "API rate limit reached. Please try again in a few minutes."
        elif "quota" in error_message.lower() or "credit" in error_message.lower():
            error_type = "quota_error"
            error_message = "Insufficient credits or quota exceeded."

        logger.error(
            f"Contract analysis failed for {analysis_id}: {error_type} - {error_message}"
        )

        # Update analysis status to failed with error details
        await user_client.update(
            "contract_analyses",
            {"id": analysis_id},
            {
                "status": "failed",
                "analysis_result": {
                    "error": {
                        "type": error_type,
                        "message": error_message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                },
            },
        )

        # Send detailed error update via Redis Pub/Sub
        retry_available = error_type in [
            "llm_api_error",
            "timeout_error",
            "rate_limit_error",
        ]
        publish_progress_sync(
            session_id,
            {
                "event_type": "analysis_failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "contract_id": contract_id,
                    "status": "failed",
                    "error_message": error_message,
                    "error_type": error_type,
                    "retry_available": retry_available,
                },
            },
        )

        # Also send via WebSocket manager for immediate delivery (if connected)
        await websocket_manager.send_message(
            session_id,
            WebSocketEvents.analysis_failed(
                contract_id, error_message, retry_available
            ),
        )

        # Mark analysis as failed in database
        try:
            await user_client.execute_rpc(
                "complete_analysis_progress",
                {
                    "p_contract_id": contract_id,
                    "p_analysis_id": analysis_id,
                    "p_final_status": "failed",
                },
            )
        except Exception as progress_error:
            logger.warning(
                f"Failed to mark analysis as failed in database: {str(progress_error)}"
            )


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
        user_client = await document_service.get_user_client()

        # Update document status
        await user_client.update(
            "documents", {"id": document_id}, {"processing_status": "reprocessing_ocr"}
        )

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
        await user_client.update(
            "documents",
            {"id": document_id},
            {"status": "processed", "processing_results": extraction_result},
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
        await user_client.update(
            "documents",
            {"id": document_id},
            {"status": "ocr_failed", "processing_results": {"error": str(e)}},
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
        user_client = await document_service.get_user_client()

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
                        doc_result = await user_client.database.select(
                            "documents", columns="*", filters={"id": doc_id}
                        )

                        if not doc_result.get("data"):
                            logger.warning(
                                f"Document {doc_id} not found in batch processing"
                            )
                            return

                        document = doc_result["data"][0]

                        # Update document status
                        await user_client.update(
                            "documents",
                            {"id": doc_id},
                            {"processing_status": "processing_ocr"},
                        )

                        # Process with OCR
                        extraction_result = (
                            await document_service.extract_text_with_ocr(
                                document["storage_path"],
                                document["file_type"],
                                contract_context=batch_context,
                            )
                        )

                        # Update document with results
                        await user_client.update(
                            "documents",
                            {"id": doc_id},
                            {
                                "processing_status": "processed",
                                "processing_results": extraction_result,
                            },
                        )

                        processed_docs += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to process document {doc_id} in batch: {str(e)}"
                        )

                        # Update document status to failed
                        await user_client.update(
                            "documents",
                            {"id": doc_id},
                            {
                                "processing_status": "ocr_failed",
                                "processing_results": {"error": str(e)},
                            },
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
                    doc_result = await user_client.database.select(
                        "documents", columns="*", filters={"id": doc_id}
                    )

                    if not doc_result.get("data"):
                        continue

                    document = doc_result["data"][0]

                    # Update document status
                    await user_client.update(
                        "documents",
                        {"id": doc_id},
                        {"processing_status": "processing_ocr"},
                    )

                    # Process with OCR
                    extraction_result = await document_service.extract_text_with_ocr(
                        document["storage_path"],
                        document["file_type"],
                        contract_context=batch_context,
                    )

                    # Update document with results
                    await user_client.update(
                        "documents",
                        {"id": doc_id},
                        {
                            "processing_status": "processed",
                            "processing_results": extraction_result,
                        },
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
