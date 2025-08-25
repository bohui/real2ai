"""
UpdateMetricsNode - Update document with aggregated processing metrics

This node migrates the _update_document_metrics method from DocumentService
to update the main document record with aggregated metrics from processing.
"""

from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase
from app.services.repositories.runs_repository import RunsRepository
import uuid


class UpdateMetricsNode(DocumentProcessingNodeBase):
    """
    Node responsible for updating document with aggregated processing metrics.

    This node:
    1. Calculates aggregated metrics from text extraction and diagram results
    2. Updates main document record with processing results
    3. Stores full processing results for future reference

    State Updates:
    - No state changes (database operation only)
    """

    runs_repo = None
    # Inherit constructor from DocumentProcessingNodeBase

    async def initialize(self, user_id):
        """Initialize runs repository with user context"""
        if not self.runs_repo:
            self.runs_repo = RunsRepository(user_id)

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Update document with aggregated processing metrics.

        Args:
            state: Current processing state with extraction and diagram results

        Returns:
            Updated state (no changes, database updated)
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            # Validate required state
            document_id = state.get("document_id")
            text_extraction_result = state.get("text_extraction_result")
            diagram_processing_result = state.get("diagram_processing_result")

            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "update_metrics"},
                )

            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Text extraction result is missing or unsuccessful",
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": (
                            text_extraction_result.success
                            if text_extraction_result
                            else False
                        ),
                    },
                )

            if not diagram_processing_result:
                self._log_warning(
                    f"No diagram processing result for document {document_id}, using empty result",
                    extra={"document_id": document_id},
                )
                from app.schema.document import DiagramProcessingResult

                diagram_processing_result = DiagramProcessingResult(
                    total_diagrams=0,
                    diagram_pages=[],
                    diagram_types={},
                    detection_summary={},
                )

            self._log_info(
                f"Updating metrics for document {document_id}",
                extra={
                    "document_id": document_id,
                    "has_extraction_result": True,
                    "has_diagram_result": bool(diagram_processing_result),
                },
            )

            # Get user context and initialize repos
            user_context = await self.get_user_context()
            await self.initialize(uuid.UUID(user_context.user_id))

            # Get user-authenticated client
            user_client = await self.get_user_client()

            # Calculate aggregated metrics from extraction results
            pages = text_extraction_result.pages
            total_pages = len(pages)
            total_word_count = sum(p.word_count for p in pages)
            total_text_length = sum(p.text_length for p in pages)

            # Calculate average confidence
            confidences = [p.confidence for p in pages if p.confidence > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Diagram information
            total_diagrams = (
                diagram_processing_result.total_diagrams
                if diagram_processing_result
                else 0
            )
            has_diagrams = total_diagrams > 0

            # Page-based metrics only

            # Determine primary text extraction method
            extraction_methods = text_extraction_result.extraction_methods or []
            primary_method = extraction_methods[0] if extraction_methods else "unknown"

            # Prepare update data (ensure JSON-serializable values)
            processing_completed_at = datetime.now(timezone.utc).isoformat()

            # Prepare text extraction metadata (excluding full_text)
            try:
                text_extraction_dict = (
                    text_extraction_result.model_dump()
                    if hasattr(text_extraction_result, "model_dump")
                    else dict(text_extraction_result)
                )
                # Remove full_text from processing_results to avoid redundant storage
                text_extraction_dict.pop("full_text", None)
            except Exception:
                # Best-effort fallback
                text_extraction_dict = (
                    text_extraction_result.__dict__
                    if hasattr(text_extraction_result, "__dict__")
                    else str(text_extraction_result)
                )
                # Remove full_text if it exists
                if isinstance(text_extraction_dict, dict):
                    text_extraction_dict.pop("full_text", None)

            # diagram_processing_result may already be a dict; if it's a pydantic model, convert
            if hasattr(diagram_processing_result, "model_dump"):
                try:
                    diagram_processing_serializable = (
                        diagram_processing_result.model_dump()
                    )
                except Exception:
                    diagram_processing_serializable = str(diagram_processing_result)
            else:
                diagram_processing_serializable = diagram_processing_result

            # Get artifact_text_id from state if available
            artifact_text_id = state.get("artifact_text_id")

            update_data = {
                # full_text is NOT saved here - it's stored in artifacts_full_text via ExtractTextNode
                "total_pages": total_pages,
                "total_word_count": total_word_count,
                "total_text_length": total_text_length,
                "has_diagrams": has_diagrams,
                "diagram_count": total_diagrams,
                "extraction_confidence": avg_confidence,
                "overall_quality_score": avg_confidence,  # Use confidence as quality proxy
                "text_extraction_method": primary_method,
                "processing_completed_at": processing_completed_at,
                "processing_results": {
                    "text_extraction": text_extraction_dict,  # full_text excluded
                    "diagram_processing": diagram_processing_serializable,
                },
            }

            # Add artifact_text_id if available to link document to its text artifact
            if artifact_text_id:
                update_data["artifact_text_id"] = artifact_text_id
                self._log_info(
                    f"Linking document {document_id} to text artifact {artifact_text_id}",
                    extra={
                        "document_id": document_id,
                        "artifact_text_id": str(artifact_text_id),
                    },
                )

            # Update document record using repository
            from app.services.repositories.documents_repository import (
                DocumentsRepository,
            )
            from uuid import UUID

            docs_repo = DocumentsRepository()
            await docs_repo.update_processing_results(UUID(document_id), update_data)

            # Record final step completion in runs tracking
            run_id = state.get("run_id")
            if run_id and self.runs_repo:
                try:
                    await self.runs_repo.complete_step(
                        run_id=uuid.UUID(run_id),
                        step_name="update_metrics",
                        step_status="completed",
                        step_output={
                            "metrics_updated": True,
                            "total_pages": total_pages,
                            "total_word_count": total_word_count,
                            "total_diagrams": total_diagrams,
                            "avg_confidence": avg_confidence,
                        },
                    )
                    self._log_info(f"Recorded step completion for run {run_id}")
                except Exception as e:
                    self._log_warning(f"Failed to record step completion: {e}")

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            # Progress is handled by workflow level

            self._log_info(
                f"Successfully updated metrics for document {document_id}",
                extra={
                    "document_id": document_id,
                    "total_pages": total_pages,
                    "total_word_count": total_word_count,
                    "total_text_length": total_text_length,
                    "total_diagrams": total_diagrams,
                    "avg_confidence": avg_confidence,
                    "primary_method": primary_method,
                    "duration_seconds": duration,
                },
            )

            return state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to update document metrics: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_update",
                    "table": "documents",
                    "fields": "processing_metrics",
                    "has_extraction_result": bool(state.get("text_extraction_result")),
                    "has_diagram_result": bool(state.get("diagram_processing_result")),
                },
            )
