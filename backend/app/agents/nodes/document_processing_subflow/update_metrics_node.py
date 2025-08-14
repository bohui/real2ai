"""
UpdateMetricsNode - Update document with aggregated processing metrics

This node migrates the _update_document_metrics method from DocumentService
to update the main document record with aggregated metrics from processing.
"""

from typing import Dict, Any
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
    
    def __init__(self):
        super().__init__("update_metrics")
        self.runs_repo = None

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
                    {"operation": "update_metrics"}
                )
            
            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Text extraction result is missing or unsuccessful", 
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": text_extraction_result.success if text_extraction_result else False
                    }
                )
            
            if not diagram_processing_result:
                self._log_warning(
                    f"No diagram processing result for document {document_id}, using empty result",
                    extra={"document_id": document_id}
                )
                diagram_processing_result = {
                    "total_diagrams": 0,
                    "diagram_pages": [],
                    "diagram_types": {},
                    "detection_summary": {}
                }
            
            self._log_info(
                f"Updating metrics for document {document_id}",
                extra={
                    "document_id": document_id,
                    "has_extraction_result": True,
                    "has_diagram_result": bool(diagram_processing_result)
                }
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
            total_diagrams = diagram_processing_result.get("total_diagrams", 0)
            has_diagrams = total_diagrams > 0
            
            # Page-based metrics only
            
            # Determine primary text extraction method
            extraction_methods = text_extraction_result.extraction_methods or []
            primary_method = extraction_methods[0] if extraction_methods else "unknown"
            
            # Prepare update data
            update_data = {
                "full_text": text_extraction_result.full_text,
                "total_pages": total_pages,
                "total_word_count": total_word_count,
                "total_text_length": total_text_length,
                "has_diagrams": has_diagrams,
                "diagram_count": total_diagrams,
                "extraction_confidence": avg_confidence,
                "overall_quality_score": avg_confidence,  # Use confidence as quality proxy
                "text_extraction_method": primary_method,
                "processing_completed_at": datetime.now(timezone.utc),
                "processing_results": {
                    "text_extraction": text_extraction_result,
                    "diagram_processing": diagram_processing_result,
                    # Paragraph processing removed - now using page-based processing
                },
            }
            
            # Update document record using repository
            from app.services.repositories.documents_repository import DocumentsRepository
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
                            "avg_confidence": avg_confidence
                        }
                    )
                    self._log_info(f"Recorded step completion for run {run_id}")
                except Exception as e:
                    self._log_warning(f"Failed to record step completion: {e}")
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
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
                    "duration_seconds": duration
                }
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
                    "has_diagram_result": bool(state.get("diagram_processing_result"))
                }
            )