"""
User-Aware Background Tasks

Example implementation of background tasks that maintain user authentication
context using the secure task context store.

This demonstrates how to migrate existing background tasks to properly
maintain user context and RLS enforcement.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from app.core.task_context import user_aware_task, task_manager
from app.core.auth_context import AuthContext
from app.core.async_utils import celery_async_task
from app.services.document_service import DocumentService
from app.agents.contract_workflow import ContractAnalysisWorkflow

logger = logging.getLogger(__name__)

# Assume celery app is configured elsewhere
from app.core.celery import celery_app


# @celery_app.task(bind=True)
# @user_aware_task
# async def process_user_document_background(
#     self, document_id: str, user_id: str
# ) -> Dict[str, Any]:
#     """
#     Process document in background with maintained user context.

#     This task maintains the user authentication context throughout execution,
#     ensuring all database operations respect RLS policies.

#     Args:
#         document_id: ID of document to process
#         user_id: User ID (for validation against context)

#     Returns:
#         Processing result dictionary
#     """
#     task_start = datetime.now(UTC)

#     try:
#         # Verify user context matches expected user
#         context_user_id = AuthContext.get_user_id()
#         if context_user_id != user_id:
#             raise ValueError(
#                 f"User context mismatch: expected {user_id}, got {context_user_id}"
#             )

#         logger.info(
#             f"Starting document processing for user {user_id}, document {document_id}"
#         )

#         # Initialize document service (will use restored user context)
#         document_service = DocumentService(use_llm_document_processing=True)
#         await document_service.initialize()

#         # Update task progress
#         self.update_state(
#             state="PROCESSING",
#             meta={
#                 "status": "Document processing started",
#                 "progress": 10,
#                 "user_id": user_id,
#                 "document_id": document_id,
#             },
#         )

#         # Process document using new subflow (for backward compatibility)
#         # Note: This will be migrated to use the subflow directly
#         processing_result = await document_service.process_document_by_id(
#             document_id=document_id
#         )

#         # Update progress
#         self.update_state(
#             state="PROCESSING",
#             meta={
#                 "status": "Text extraction completed",
#                 "progress": 50,
#                 "extraction_confidence": processing_result.get("confidence", 0),
#             },
#         )

#         # Perform additional analysis if needed
#         if processing_result.get("success"):
#             analysis_result = await document_service.analyze_extracted_content(
#                 document_id=document_id,
#                 extracted_text=processing_result.get("text", ""),
#             )

#             # Update progress
#             self.update_state(
#                 state="PROCESSING",
#                 meta={
#                     "status": "Analysis completed",
#                     "progress": 90,
#                     "entities_found": analysis_result.get("entity_count", 0),
#                 },
#             )

#         # Finalize processing
#         processing_time = (datetime.now(UTC) - task_start).total_seconds()

#         final_result = {
#             "success": True,
#             "document_id": document_id,
#             "user_id": user_id,
#             "processing_time": processing_time,
#             "task_id": self.request.id,
#             "completed_at": datetime.now(UTC).isoformat(),
#             **processing_result,
#         }

#         logger.info(
#             f"Document processing completed for user {user_id}, "
#             f"document {document_id} in {processing_time:.2f}s"
#         )

#         return final_result

#     except Exception as e:
#         processing_time = (datetime.now(UTC) - task_start).total_seconds()

#         logger.error(
#             f"Document processing failed for user {user_id}, document {document_id}: {e}",
#             exc_info=True,
#         )

#         # Update document status to failed (user context maintained)
#         try:
#             document_service = DocumentService(use_llm_document_processing=True)
#             await document_service.initialize()
#             await document_service.mark_document_failed(
#                 document_id=document_id,
#                 error_details={
#                     "error": str(e),
#                     "task_id": self.request.id,
#                     "processing_time": processing_time,
#                     "failed_at": datetime.now(UTC).isoformat(),
#                 },
#             )
#         except Exception as update_error:
#             logger.error(f"Failed to update document status: {update_error}")

#         # Return error result
#         raise Exception(f"Document processing failed: {str(e)}")


@celery_app.task(bind=True)
@user_aware_task
@celery_async_task
async def run_document_processing_subflow(
    self,
    document_id: str,
    user_id: str,
    use_llm: bool = True,
    content_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run unified contract workflow's document processing with user context.

    This task uses the single ContractAnalysisWorkflow and executes the
    document processing node while maintaining user authentication context
    for RLS enforcement and progress tracking.

    Args:
        document_id: ID of document to process
        user_id: User ID (for validation against context)
        use_llm: Whether to use LLM for enhanced OCR/analysis
        content_hash: Content hash override (optional)

    Returns:
        Processing result dictionary with ProcessedDocumentSummary or error
    """
    task_start = datetime.now(UTC)

    try:
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        logger.info(
            f"Starting document processing subflow for user {user_id}, document {document_id}"
        )

        # Update task progress
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Initializing document processing subflow",
                "progress": 5,
                "user_id": user_id,
                "document_id": document_id,
                "use_llm": use_llm,
            },
        )

        # Initialize unified contract workflow
        workflow = ContractAnalysisWorkflow()

        # Update progress
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Document processing workflow started",
                "progress": 10,
            },
        )

        # Build minimal state expected by ContractAnalysisWorkflow
        state = {
            "user_id": user_id,
            "document_data": {"document_id": document_id, "content_hash": content_hash},
            "australian_state": (
                AuthContext.get_user_state()
                if hasattr(AuthContext, "get_user_state")
                else "NSW"
            ),
            "contract_type": "purchase_agreement",
            "document_type": "contract",
            # Optional progress callback can be injected by caller if needed
        }

        # Run just the document processing node
        result = workflow.process_document(state)

        # Update progress based on updated state
        parsing_completed = (
            result.get("parsing_status") == ProcessingStatus.COMPLETED
            if isinstance(result, dict)
            else False
        )
        if parsing_completed:
            self.update_state(
                state="PROCESSING",
                meta={
                    "status": "Document processing completed successfully",
                    "progress": 90,
                    "extraction_method": result.get("document_metadata", {}).get(
                        "extraction_method", "unknown"
                    ),
                    "total_pages": result.get("document_metadata", {}).get(
                        "total_pages", 0
                    ),
                    "character_count": result.get("document_metadata", {}).get(
                        "character_count", 0
                    ),
                },
            )
        else:
            self.update_state(
                state="PROCESSING",
                meta={
                    "status": "Document processing failed",
                    "progress": 50,
                    "error": (
                        result.get("error", "Unknown error")
                        if isinstance(result, dict)
                        else "Unknown error"
                    ),
                },
            )

        # Finalize processing
        processing_time = (datetime.now(UTC) - task_start).total_seconds()

        final_result = {
            "success": parsing_completed,
            "document_id": document_id,
            "user_id": user_id,
            "processing_time": processing_time,
            "task_id": self.request.id,
            "completed_at": datetime.now(UTC).isoformat(),
            "workflow_type": "contract_workflow_document_processing",
            "use_llm": use_llm,
            "result": result,
        }

        logger.info(
            f"Document processing subflow completed for user {user_id}, "
            f"document {document_id} in {processing_time:.2f}s"
        )

        return final_result

    except Exception as e:
        processing_time = (datetime.now(UTC) - task_start).total_seconds()

        logger.error(
            f"Document processing subflow failed for user {user_id}, document {document_id}: {e}",
            exc_info=True,
        )

        # Try to mark document as failed (if we can get user context)
        try:
            document_service = DocumentService()
            await document_service.initialize()

            # Import here to avoid circular import
            from app.models.supabase_models import ProcessingStatus

            # Update document status using repository
            from app.services.repositories.documents_repository import (
                DocumentsRepository,
            )
            from uuid import UUID

            docs_repo = DocumentsRepository()
            await docs_repo.update_processing_status_and_results(
                UUID(document_id),
                ProcessingStatus.FAILED.value,
                {
                    "error": str(e),
                    "task_id": self.request.id,
                    "processing_time": processing_time,
                    "failed_at": datetime.now(UTC).isoformat(),
                    "workflow_type": "document_processing_subflow",
                    "processing_completed_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update document status after subflow error: {update_error}"
            )

        # Return error result
        raise Exception(f"Document processing subflow failed: {str(e)}")


# @celery_app.task(bind=True)
# @user_aware_task
# async def batch_process_documents_background(
#     self,
#     document_ids: list[str],
#     user_id: str,
#     batch_options: Optional[Dict[str, Any]] = None,
# ) -> Dict[str, Any]:
#     """
#     Process multiple documents in batch with user context.

#     Demonstrates how to handle batch operations while maintaining
#     user authentication context throughout.
#     """
#     batch_start = datetime.now(UTC)
#     batch_options = batch_options or {}

#     try:
#         # Verify user context
#         context_user_id = AuthContext.get_user_id()
#         if context_user_id != user_id:
#             raise ValueError(
#                 f"User context mismatch: expected {user_id}, got {context_user_id}"
#             )

#         logger.info(
#             f"Starting batch processing for user {user_id}, "
#             f"{len(document_ids)} documents"
#         )

#         # Initialize services
#         document_service = DocumentService(use_llm_document_processing=True)
#         await document_service.initialize()

#         results = []
#         completed_count = 0

#         for i, document_id in enumerate(document_ids):
#             try:
#                 # Update batch progress
#                 progress = int((i / len(document_ids)) * 100)
#                 self.update_state(
#                     state="PROCESSING",
#                     meta={
#                         "status": f"Processing document {i+1} of {len(document_ids)}",
#                         "progress": progress,
#                         "current_document": document_id,
#                         "completed_count": completed_count,
#                     },
#                 )

#                 # Process individual document
#                 doc_result = await document_service.process_document_internal(
#                     document_id=document_id,
#                     user_id=user_id,
#                     processing_options=batch_options,
#                 )

#                 results.append(
#                     {
#                         "document_id": document_id,
#                         "success": doc_result.get("success", False),
#                         "result": doc_result,
#                     }
#                 )

#                 if doc_result.get("success"):
#                     completed_count += 1

#             except Exception as doc_error:
#                 logger.error(f"Failed to process document {document_id}: {doc_error}")
#                 results.append(
#                     {
#                         "document_id": document_id,
#                         "success": False,
#                         "error": str(doc_error),
#                     }
#                 )

#         # Calculate batch statistics
#         batch_time = (datetime.now(UTC) - batch_start).total_seconds()
#         success_rate = completed_count / len(document_ids) if document_ids else 0

#         batch_result = {
#             "success": True,
#             "batch_id": f"batch_{user_id}_{int(time.time())}",
#             "user_id": user_id,
#             "total_documents": len(document_ids),
#             "completed_documents": completed_count,
#             "success_rate": success_rate,
#             "batch_time": batch_time,
#             "results": results,
#             "completed_at": datetime.now(UTC).isoformat(),
#         }

#         logger.info(
#             f"Batch processing completed for user {user_id}: "
#             f"{completed_count}/{len(document_ids)} documents processed "
#             f"({success_rate:.1%} success rate) in {batch_time:.2f}s"
#         )

#         return batch_result

#     except Exception as e:
#         logger.error(f"Batch processing failed for user {user_id}: {e}", exc_info=True)
#         raise Exception(f"Batch processing failed: {str(e)}")


@celery_app.task(bind=True)
@user_aware_task
async def generate_user_report_background(
    self, report_type: str, user_id: str, report_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate user-specific report with maintained authentication context.

    This demonstrates how to generate reports that are properly scoped
    to the authenticated user while running in background.
    """
    try:
        # Verify user context
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        logger.info(f"Starting report generation: {report_type} for user {user_id}")

        # Initialize services
        document_service = DocumentService(use_llm_document_processing=True)
        await document_service.initialize()

        # Update progress
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Gathering user data",
                "progress": 10,
                "report_type": report_type,
            },
        )

        # Get user's documents (RLS enforced)
        user_documents = await document_service.get_user_documents(
            user_id=user_id, filters=report_params.get("filters", {})
        )

        # Update progress
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Analyzing documents",
                "progress": 50,
                "documents_found": len(user_documents),
            },
        )

        # Generate report based on user's data only
        report_data = await document_service.generate_analysis_report(
            documents=user_documents, report_type=report_type, parameters=report_params
        )

        # Update progress
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Finalizing report",
                "progress": 90,
            },
        )

        # Store report (user context maintained)
        report_id = await document_service.store_user_report(
            user_id=user_id, report_type=report_type, report_data=report_data
        )

        result = {
            "success": True,
            "report_id": report_id,
            "report_type": report_type,
            "user_id": user_id,
            "documents_analyzed": len(user_documents),
            "generated_at": datetime.now(UTC).isoformat(),
            "task_id": self.request.id,
        }

        logger.info(f"Report {report_type} generated for user {user_id}: {report_id}")
        return result

    except Exception as e:
        logger.error(f"Report generation failed for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Report generation failed: {str(e)}")


# Example of launching user-aware tasks from API endpoints


async def launch_document_processing(
    document_id: str, user_id: str, background_tasks=None
) -> str:
    """
    Launch document processing task with user context.

    This is how you would call the task from an API endpoint.
    """
    try:
        # Create task ID
        task_id = f"process_{document_id}_{int(time.time())}"

        # Launch task with user context
        task_result = await task_manager.launch_user_task(
            run_document_processing_subflow, task_id, document_id, user_id
        )

        logger.info(
            f"Launched document processing task {task_result.id} for user {user_id}"
        )
        return task_result.id

    except Exception as e:
        logger.error(f"Failed to launch document processing task: {e}")
        raise


# async def launch_batch_processing(
#     document_ids: list[str],
#     user_id: str,
#     batch_options: Optional[Dict[str, Any]] = None,
# ) -> str:
#     """Launch batch processing task with user context."""
#     try:
#         task_id = f"batch_{user_id}_{int(time.time())}"
##         Note: batch task is currently not implemented; keeping example disabled.
#         # task_result = await task_manager.launch_user_task(
#         #     batch_process_documents_background,
#         #     task_id,
#         #     document_ids,
#         #     user_id,
#         #     batch_options,
#         # )
#
#         # logger.info(
#         #     f"Launched batch processing task {task_result.id} for user {user_id}, "
#         #     f"{len(document_ids)} documents"
#         # )
#         # return task_result.id
#         raise NotImplementedError("Batch processing task is not available")
#
#     except Exception as e:
#         logger.error(f"Failed to launch batch processing task: {e}")
#         raise


# System-level tasks (no user context needed)


@celery_app.task
async def cleanup_expired_documents():
    """
    System maintenance task - runs with service role.

    This type of task doesn't use @user_aware_task because it's
    a legitimate system operation that needs to access all users' data.
    """
    from app.clients import get_supabase_client

    try:
        logger.info("Starting expired documents cleanup")

        # Use service role for system operations
        system_client = await get_supabase_client(use_service_role=True)

        # This bypasses RLS to clean up across all users
        cleanup_result = await system_client.execute_rpc(
            "cleanup_expired_documents", {"days_old": 30}
        )

        logger.info(
            f"Cleaned up {cleanup_result.get('deleted_count', 0)} expired documents"
        )

        return {
            "success": True,
            "deleted_count": cleanup_result.get("deleted_count", 0),
            "cleanup_time": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Document cleanup failed: {e}")
        raise


@celery_app.task
async def generate_system_analytics():
    """
    Generate system-wide analytics - legitimate system operation.

    This runs with service role to generate admin dashboards
    and system monitoring reports.
    """
    from app.clients import get_supabase_client

    try:
        logger.info("Generating system analytics")

        # Use service role for cross-user analytics
        system_client = await get_supabase_client(use_service_role=True)

        # Generate system-wide statistics
        analytics_result = await system_client.execute_rpc(
            "generate_system_analytics", {}
        )

        return {
            "success": True,
            "analytics": analytics_result.get("data", {}),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"System analytics generation failed: {e}")
        raise
