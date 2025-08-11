"""
MarkBasicCompleteNode - Mark document processing as BASIC_COMPLETE

This node updates the document processing status to BASIC_COMPLETE,
indicating that basic document processing (text extraction, page analysis,
diagram detection) has been completed successfully.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from app.models.supabase_models import ProcessingStatus
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class MarkBasicCompleteNode(DocumentProcessingNodeBase):
    """
    Node responsible for marking document processing as basic complete.
    
    This node:
    1. Updates processing_status to BASIC_COMPLETE
    2. Sets processing completion timestamp
    3. Provides audit trail for workflow completion
    
    State Updates:
    - Updates database record only (no state changes)
    """
    
    def __init__(self):
        super().__init__("mark_basic_complete")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Mark document processing as basic complete.
        
        Args:
            state: Current processing state with document_id
            
        Returns:
            Updated state (no changes, but database updated)
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()
        
        try:
            document_id = state.get("document_id")
            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "mark_basic_complete"}
                )
            
            self._log_info(f"Marking basic processing complete for document {document_id}")
            
            # Get user-authenticated client
            user_client = await self.get_user_client()
            
            # Set completion status and timestamp
            processing_completed_at = datetime.now(timezone.utc)
            
            update_data = {
                "processing_status": ProcessingStatus.BASIC_COMPLETE.value,
                "processing_completed_at": processing_completed_at
            }
            
            # Update document record
            await user_client.database.update(
                "documents",
                document_id,
                update_data
            )
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Successfully marked basic processing complete for document {document_id}",
                extra={
                    "document_id": document_id,
                    "processing_completed_at": processing_completed_at.isoformat(),
                    "status": ProcessingStatus.BASIC_COMPLETE.value,
                    "duration_seconds": duration
                }
            )
            
            # Return state unchanged (database operation only)
            return state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to mark basic processing complete: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_update",
                    "table": "documents",
                    "field": "processing_status",
                    "target_status": ProcessingStatus.BASIC_COMPLETE.value
                }
            )