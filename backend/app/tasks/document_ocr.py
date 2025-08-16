"""Document OCR processing tasks for enhanced text extraction."""

import asyncio
import time
import logging
from typing import Dict, Any, List
from uuid import UUID

from app.core.celery import celery_app
from app.core.task_context import user_aware_task
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.services.communication.websocket_singleton import websocket_manager
from app.services.repositories.documents_repository import DocumentsRepository

logger = logging.getLogger(__name__)


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