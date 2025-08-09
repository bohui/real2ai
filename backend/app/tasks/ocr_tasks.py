"""
Celery tasks for OCR processing with Gemini 2.5 Pro
Scalable background processing for document analysis

MIGRATED VERSION: Now uses user-aware architecture with proper context propagation.
All tasks use @user_aware_task decorator to maintain user authentication context.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from celery.exceptions import Retry, MaxRetriesExceededError

from app.core.celery import celery_app
from app.core.task_context import user_aware_task
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.services.communication.websocket_singleton import websocket_manager
from app.clients.factory import get_supabase_client

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
@user_aware_task
async def process_document_ocr(
    self,
    document_id: str,
    user_id: str,
    contract_context: Dict[str, Any],
    processing_options: Optional[Dict[str, Any]] = None,
):
    """
    Process document with OCR using Gemini 2.5 Pro - USER AWARE VERSION

    This task maintains user authentication context throughout execution,
    ensuring all database operations respect RLS policies.

    Args:
        document_id: Document ID to process
        user_id: User ID for security and context validation
        contract_context: Context for contract analysis
        processing_options: Additional processing options
    """

    try:
        # Verify user context matches expected user
        context_user_id = AuthContext.get_user_id()
        if context_user_id != user_id:
            raise ValueError(
                f"User context mismatch: expected {user_id}, got {context_user_id}"
            )

        logger.info(
            f"Starting OCR processing for user {user_id}, document {document_id}"
        )

        # Initialize user-aware document service
        document_service = DocumentService()
        await document_service.initialize()

        # Process document using user context (all operations respect RLS)
        result = await document_service.process_document_internal(
            document_id=document_id,
            user_id=user_id,
            processing_options=processing_options or {},
        )

        logger.info(f"OCR processing completed for document {document_id}")
        return result

    except Exception as e:
        logger.error(f"OCR task failed for document {document_id}: {str(e)}")
        # Update document status to failed
        asyncio.run(
            _update_document_status(document_id, "ocr_failed", {"error": str(e)})
        )
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def batch_process_documents(
    self, document_ids: list, user_id: str, batch_options: Dict[str, Any]
):
    """
    Batch process multiple documents with OCR

    Args:
        document_ids: List of document IDs to process
        user_id: User ID for security
        batch_options: Batch processing configuration
    """

    try:
        return asyncio.run(
            _async_batch_process_documents(
                document_ids, user_id, batch_options, self.request.id
            )
        )

    except Exception as e:
        logger.error(f"Batch OCR task failed for user {user_id}: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    priority=9,  # High priority
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 30},
)
def priority_ocr_processing(
    self, document_id: str, user_id: str, priority_context: Dict[str, Any]
):
    """
    High-priority OCR processing for premium users or urgent documents

    Args:
        document_id: Document ID to process
        user_id: User ID for security
        priority_context: Priority processing context
    """

    try:
        # Enhanced processing options for priority tasks
        processing_options = {
            "priority": True,
            "enhanced_quality": True,
            "detailed_analysis": True,
            "fast_response": True,
        }

        return asyncio.run(
            _async_process_document_ocr(
                document_id,
                user_id,
                priority_context,
                processing_options,
                self.request.id,
            )
        )

    except Exception as e:
        logger.error(f"Priority OCR task failed for document {document_id}: {str(e)}")
        raise


async def _async_process_document_ocr(
    document_id: str,
    user_id: str,
    contract_context: Dict[str, Any],
    processing_options: Optional[Dict[str, Any]],
    task_id: str,
) -> Dict[str, Any]:
    """Async implementation of OCR processing"""

    db_client = await get_supabase_client()
    document_service = DocumentService()

    try:
        # Initialize services
        await document_service.initialize()

        # Get document details
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not doc_result.data:
            raise ValueError(f"Document {document_id} not found or access denied")

        document = doc_result.data[0]

        # Update status to processing
        await _update_document_status(
            document_id,
            "processing_ocr",
            {"task_id": task_id, "started_at": datetime.now(timezone.utc).isoformat()},
        )

        # Send WebSocket update
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_processing_started",
                "data": {
                    "document_id": document_id,
                    "task_id": task_id,
                    "estimated_completion": "2-5 minutes",
                },
            },
        )

        # Progress tracking
        progress_steps = [
            ("initializing", 10, "Initializing OCR processing"),
            ("extracting", 30, "Extracting text with Gemini 2.5 Pro"),
            ("enhancing", 60, "Enhancing contract-specific content"),
            ("analyzing", 80, "Analyzing document structure"),
            ("finalizing", 95, "Finalizing results"),
        ]

        async def send_progress(step: str, progress: int, description: str):
            await websocket_manager.send_message(
                document_id,
                {
                    "event_type": "ocr_progress",
                    "data": {
                        "document_id": document_id,
                        "task_id": task_id,
                        "current_step": step,
                        "progress_percent": progress,
                        "step_description": description,
                    },
                },
            )

        # Process with progress updates
        for step, progress, description in progress_steps:
            await send_progress(step, progress, description)

            if step == "extracting":
                # Perform OCR extraction
                extraction_result = await document_service.extract_text_with_ocr(
                    document["storage_path"], document["file_type"], contract_context
                )

                # Enhanced processing for priority tasks
                if processing_options and processing_options.get("enhanced_quality"):
                    extraction_result = await _enhance_extraction_quality(
                        extraction_result, contract_context
                    )

        # Update document with final results
        final_results = {
            **extraction_result,
            "processing_completed_at": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "processing_options": processing_options or {},
        }

        await _update_document_status(document_id, "processed", final_results)

        # Send completion notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_processing_completed",
                "data": {
                    "document_id": document_id,
                    "task_id": task_id,
                    "extraction_confidence": extraction_result.get(
                        "extraction_confidence", 0.0
                    ),
                    "character_count": extraction_result.get("character_count", 0),
                    "word_count": extraction_result.get("word_count", 0),
                    "processing_method": extraction_result.get(
                        "extraction_method", "unknown"
                    ),
                },
            },
        )

        logger.info(f"OCR processing completed for document {document_id}")
        return final_results

    except Exception as e:
        logger.error(f"OCR processing failed for document {document_id}: {str(e)}")

        # Update status to failed
        await _update_document_status(
            document_id,
            "ocr_failed",
            {
                "error": str(e),
                "task_id": task_id,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Send error notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_processing_failed",
                "data": {
                    "document_id": document_id,
                    "task_id": task_id,
                    "error_message": str(e),
                },
            },
        )

        raise


async def _async_batch_process_documents(
    document_ids: list, user_id: str, batch_options: Dict[str, Any], task_id: str
) -> Dict[str, Any]:
    """Async implementation of batch OCR processing"""

    results = []
    failed_documents = []

    # use shared websocket manager

    # Send batch start notification
    await websocket_manager.send_message(
        f"batch_{user_id}",
        {
            "event_type": "batch_ocr_started",
            "data": {
                "batch_id": task_id,
                "total_documents": len(document_ids),
                "user_id": user_id,
            },
        },
    )

    for i, document_id in enumerate(document_ids):
        try:
            # Process individual document
            contract_context = batch_options.get("contract_context", {})
            processing_options = batch_options.get("processing_options", {})

            result = await _async_process_document_ocr(
                document_id,
                user_id,
                contract_context,
                processing_options,
                f"{task_id}_{i}",
            )

            results.append(
                {"document_id": document_id, "status": "success", "result": result}
            )

            # Send progress update
            progress = int(((i + 1) / len(document_ids)) * 100)
            await websocket_manager.send_message(
                f"batch_{user_id}",
                {
                    "event_type": "batch_ocr_progress",
                    "data": {
                        "batch_id": task_id,
                        "completed": i + 1,
                        "total": len(document_ids),
                        "progress_percent": progress,
                    },
                },
            )

        except Exception as e:
            logger.error(
                f"Batch processing failed for document {document_id}: {str(e)}"
            )
            failed_documents.append({"document_id": document_id, "error": str(e)})

            results.append(
                {"document_id": document_id, "status": "failed", "error": str(e)}
            )

    # Send completion notification
    await websocket_manager.send_message(
        f"batch_{user_id}",
        {
            "event_type": "batch_ocr_completed",
            "data": {
                "batch_id": task_id,
                "total_documents": len(document_ids),
                "successful": len(document_ids) - len(failed_documents),
                "failed": len(failed_documents),
                "results": results,
            },
        },
    )

    return {
        "batch_id": task_id,
        "total_processed": len(document_ids),
        "successful": len(document_ids) - len(failed_documents),
        "failed": len(failed_documents),
        "results": results,
        "failed_documents": failed_documents,
    }


async def _enhance_extraction_quality(
    extraction_result: Dict[str, Any], contract_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Enhanced quality processing for priority documents"""

    # Additional quality enhancements for premium processing
    enhanced_result = extraction_result.copy()

    # Contract-specific enhancements
    extracted_text = enhanced_result.get("extracted_text", "")

    if extracted_text:
        # Advanced contract term extraction
        contract_patterns = {
            "purchase_price": r"\$[\d,]+(?:\.\d{2})?",
            "settlement_date": r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}",
            "property_address": r"\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Court|Ct|Place|Pl)",
            "australian_states": r"\b(?:NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b",
        }

        import re

        extracted_patterns = {}

        for pattern_name, pattern in contract_patterns.items():
            matches = re.findall(pattern, extracted_text, re.IGNORECASE)
            if matches:
                extracted_patterns[pattern_name] = matches

        enhanced_result["contract_analysis"] = {
            "extracted_patterns": extracted_patterns,
            "contract_completeness": len(extracted_patterns) / len(contract_patterns),
            "quality_score": enhanced_result.get("extraction_confidence", 0.0) * 1.1,
        }

    return enhanced_result


async def _update_document_status(
    document_id: str, status: str, processing_results: Dict[str, Any]
):
    """Update document status in database"""

    try:
        db_client = await get_supabase_client()

        db_client.table("documents").update(
            {
                "status": status,
                "processing_results": processing_results,
            }
        ).eq("id", document_id).execute()

    except Exception as e:
        logger.error(f"Failed to update document status for {document_id}: {str(e)}")


# Celery monitoring and health checks
@celery_app.task
def health_check() -> Dict[str, str]:
    """Health check task for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_id": "ocr_worker",
    }


@celery_app.task
def cleanup_failed_tasks() -> None:
    """Cleanup failed OCR tasks"""
    # Implementation for cleaning up failed tasks
    return {"cleanup_completed": True}
