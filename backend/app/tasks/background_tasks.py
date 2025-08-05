"""Background tasks for document processing and contract analysis."""

import asyncio
import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.core.celery import celery_app
from app.models.contract_state import (
    RealEstateAgentState,
    AustralianState,
    ContractType,
    create_initial_state,
)
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.core.database import get_database_client
from app.services.document_service import DocumentService
from app.services.websocket_service import WebSocketManager

logger = logging.getLogger(__name__)

# Initialize services
document_service = DocumentService()
websocket_manager = WebSocketManager()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def process_document_background(
    self,
    document_id: str,
    user_id: str,
    australian_state: str,
    contract_type: str,
):
    """Background task for document processing"""

    async def _async_process_document():
        try:
            # Get database client
            db_client = get_database_client()
            if not hasattr(db_client, "_client") or db_client._client is None:
                await db_client.initialize()

            # Update document status
            db_client.table("documents").update({"status": "processing"}).eq(
                "id", document_id
            ).execute()

            # Get document metadata
            doc_result = (
                db_client.table("documents").select("*").eq("id", document_id).execute()
            )
            if not doc_result.data:
                raise Exception("Document not found")

            document = doc_result.data[0]

            # Extract text from document with contract context
            contract_context = {
                "australian_state": australian_state,
                "contract_type": contract_type,
                "user_type": "buyer",  # Could be derived from user profile
            }

            extraction_result = await document_service.extract_text(
                document["storage_path"],
                document["file_type"],
                contract_context=contract_context,
            )

            # Update document with extraction results
            db_client.table("documents").update(
                {"status": "processed", "processing_results": extraction_result}
            ).eq("id", document_id).execute()

            # Send WebSocket notification
            await websocket_manager.send_message(
                document_id,
                {
                    "event_type": "document_processed",
                    "data": {
                        "document_id": document_id,
                        "extraction_confidence": extraction_result.get(
                            "extraction_confidence", 0.0
                        ),
                        "character_count": extraction_result.get("character_count", 0),
                        "word_count": extraction_result.get("word_count", 0),
                    },
                },
            )

            logger.info(f"Document {document_id} processed successfully")

        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {str(e)}")
            db_client.table("documents").update(
                {"status": "failed", "processing_results": {"error": str(e)}}
            ).eq("id", document_id).execute()

            # Send error WebSocket notification
            await websocket_manager.send_message(
                document_id,
                {
                    "event_type": "document_processing_failed",
                    "data": {"document_id": document_id, "error_message": str(e)},
                },
            )

    # Run the async function
    return asyncio.run(_async_process_document())


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def analyze_contract_background(
    self,
    contract_id: str,
    analysis_id: str,
    user_id: str,
    document: Dict[str, Any],
    analysis_options: Dict[str, Any],
):
    """Background task for contract analysis"""

    async def _async_analyze_contract():
        from app.core.config import get_settings

        settings = get_settings()
        contract_workflow = ContractAnalysisWorkflow(
            openai_api_key=settings.openai_api_key,
            model_name="gpt-4",
            openai_api_base=settings.openai_api_base,
        )

        try:
            # Get database client
            db_client = get_database_client()
            if not hasattr(db_client, "_client") or db_client._client is None:
                await db_client.initialize()

            # Update analysis status
            db_client.table("contract_analyses").update({"status": "processing"}).eq(
                "id", analysis_id
            ).execute()

            # Send WebSocket update
            await websocket_manager.send_message(
                contract_id,
                {
                    "event_type": "analysis_started",
                    "data": {"contract_id": contract_id, "status": "processing"},
                },
            )

            # Get user profile for context
            user_result = (
                db_client.table("profiles").select("*").eq("id", user_id).execute()
            )
            user_profile = user_result.data[0] if user_result.data else {}

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
                    db_client.table("documents").update(
                        {"processing_results": extraction_result}
                    ).eq("id", document["id"]).execute()

            # Add document data to state
            initial_state["document_data"] = {
                "document_id": document["id"],
                "filename": document["filename"],
                "content": extracted_text,
                "storage_path": document["storage_path"],
                "file_type": document["file_type"],
            }

            # Run analysis workflow
            final_state = await contract_workflow.analyze_contract(initial_state)

            # Update analysis results
            analysis_result = final_state.get("analysis_results", {})

            # Update with both old and new column names for compatibility
            db_client.table("contract_analyses").update(
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
                    "overall_risk_score": analysis_result.get(
                        "risk_assessment", {}
                    ).get("overall_risk_score", 0),
                    "confidence_score": analysis_result.get(
                        "executive_summary", {}
                    ).get("confidence_level", 0),
                    "confidence_level": analysis_result.get(
                        "executive_summary", {}
                    ).get("confidence_level", 0),
                    "processing_time": final_state.get("processing_time", 0),
                    "processing_time_seconds": final_state.get("processing_time", 0),
                }
            ).eq("id", analysis_id).execute()

            # Deduct user credit
            if user_profile.get("subscription_status") == "free":
                new_credits = max(0, user_profile.get("credits_remaining", 0) - 1)
                db_client.table("profiles").update(
                    {"credits_remaining": new_credits}
                ).eq("id", user_id).execute()

            # Log usage
            db_client.table("usage_logs").insert(
                {
                    "user_id": user_id,
                    "action_type": "contract_analysis",
                    "credits_used": 1,
                    "remaining_credits": user_profile.get("credits_remaining", 0) - 1,
                }
            ).execute()

            # Send completion WebSocket update
            await websocket_manager.send_message(
                contract_id,
                {
                    "event_type": "analysis_completed",
                    "data": {
                        "contract_id": contract_id,
                        "analysis_summary": {
                            "overall_risk_score": analysis_result.get(
                                "risk_assessment", {}
                            ).get("overall_risk_score", 0),
                            "total_recommendations": len(
                                analysis_result.get("recommendations", [])
                            ),
                            "compliance_status": (
                                "compliant"
                                if analysis_result.get("compliance_check", {}).get(
                                    "state_compliance", False
                                )
                                else "non-compliant"
                            ),
                            "processing_time_seconds": final_state.get(
                                "processing_time", 0
                            ),
                        },
                    },
                },
            )

            logger.info(f"Contract analysis {analysis_id} completed successfully")

        except Exception as e:
            logger.error(f"Contract analysis failed for {analysis_id}: {str(e)}")

            # Update analysis status to failed
            db_client.table("contract_analyses").update({"status": "failed"}).eq(
                "id", analysis_id
            ).execute()

            # Send error WebSocket update
            await websocket_manager.send_message(
                contract_id,
                {
                    "event_type": "analysis_failed",
                    "data": {"contract_id": contract_id, "error_message": str(e)},
                },
            )

    # Run the async function
    return asyncio.run(_async_analyze_contract())


async def enhanced_reprocess_document_with_ocr_background(
    document_id: str,
    user_id: str,
    document: Dict[str, Any],
    contract_context: Dict[str, Any],
    processing_options: Dict[str, Any],
):
    """Background task for OCR reprocessing"""

    try:
        # Update document status
        db_client.table("documents").update({"status": "reprocessing_ocr"}).eq(
            "id", document_id
        ).execute()

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
            "gemini_model_used": "gemini-2.5-pro",
        }

        # Update document with OCR results
        db_client.table("documents").update(
            {"status": "processed", "processing_results": extraction_result}
        ).eq("id", document_id).execute()

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
        db_client.table("documents").update(
            {"status": "ocr_failed", "processing_results": {"error": str(e)}}
        ).eq("id", document_id).execute()

        # Send error notification
        await websocket_manager.send_message(
            document_id,
            {
                "event_type": "ocr_reprocessing_failed",
                "data": {"document_id": document_id, "error_message": str(e)},
            },
        )


async def batch_ocr_processing_background(
    document_ids: List[str],
    user_id: str,
    batch_context: Dict[str, Any],
    processing_options: Dict[str, Any],
):
    """Background task for batch OCR processing with intelligent optimization"""

    batch_id = batch_context["batch_id"]
    total_docs = len(document_ids)
    processed_docs = 0
    start_time = time.time()

    try:
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
                        doc_result = (
                            db_client.table("documents")
                            .select("*")
                            .eq("id", doc_id)
                            .execute()
                        )

                        if not doc_result.data:
                            logger.warning(
                                f"Document {doc_id} not found in batch processing"
                            )
                            return

                        document = doc_result.data[0]

                        # Update document status
                        db_client.table("documents").update(
                            {"status": "processing_ocr"}
                        ).eq("id", doc_id).execute()

                        # Process with OCR
                        extraction_result = (
                            await document_service.extract_text_with_ocr(
                                document["storage_path"],
                                document["file_type"],
                                contract_context=batch_context,
                            )
                        )

                        # Update document with results
                        db_client.table("documents").update(
                            {
                                "status": "processed",
                                "processing_results": extraction_result,
                            }
                        ).eq("id", doc_id).execute()

                        processed_docs += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to process document {doc_id} in batch: {str(e)}"
                        )

                        # Update document status to failed
                        db_client.table("documents").update(
                            {
                                "status": "ocr_failed",
                                "processing_results": {"error": str(e)},
                            }
                        ).eq("id", doc_id).execute()

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
                    doc_result = (
                        db_client.table("documents")
                        .select("*")
                        .eq("id", doc_id)
                        .execute()
                    )

                    if not doc_result.data:
                        continue

                    document = doc_result.data[0]

                    # Update document status
                    db_client.table("documents").update(
                        {"status": "processing_ocr"}
                    ).eq("id", doc_id).execute()

                    # Process with OCR
                    extraction_result = await document_service.extract_text_with_ocr(
                        document["storage_path"],
                        document["file_type"],
                        contract_context=batch_context,
                    )

                    # Update document with results
                    db_client.table("documents").update(
                        {"status": "processed", "processing_results": extraction_result}
                    ).eq("id", doc_id).execute()

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


async def generate_pdf_report(analysis_data: Dict[str, Any]) -> bytes:
    """Generate PDF report from analysis data"""
    # Placeholder - would implement with reportlab or similar
    return b"PDF report content"
