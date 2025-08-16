"""
ErrorHandlingNode - Uniform error handling and status update

This node provides uniform error handling for document processing failures,
updating the document status to FAILED and storing error details.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from app.models import ProcessingStatus
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class ErrorHandlingNode(DocumentProcessingNodeBase):
    """
    Node responsible for uniform error handling and status updates.
    
    This node:
    1. Updates document processing_status to FAILED
    2. Stores detailed error information
    3. Provides cleanup for failed processing attempts
    
    State Updates:
    - Ensures error fields are properly set in state
    """
    
    def __init__(self):
        super().__init__("error_handling")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Handle processing error and update document status.
        
        Args:
            state: Current processing state with error information
            
        Returns:
            Updated state with final error handling complete
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()
        
        try:
            document_id = state.get("document_id")
            error_message = state.get("error", "Unknown processing error")
            error_details = state.get("error_details", {})
            
            if not document_id:
                # If we don't have a document_id, we can't update the database
                # Just ensure error state is properly set
                updated_state = state.copy()
                updated_state["error"] = error_message or "Missing document ID during error handling"
                updated_state["error_details"] = error_details or {
                    "error_type": "ValidationError",
                    "error_message": "Missing document ID",
                    "node": "error_handling",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                self._log_warning(
                    "Error handling called without document_id",
                    extra={"error_message": error_message}
                )
                return updated_state
            
            self._log_info(
                f"Handling processing error for document {document_id}",
                extra={
                    "document_id": document_id,
                    "error_message": error_message,
                    "error_details_keys": list(error_details.keys()) if error_details else []
                }
            )
            
            # Get user_id from state for repository pattern
            user_id = state.get("user_id")
            if not user_id:
                self._log_warning(
                    f"Missing user_id in workflow state during error handling for document {document_id}",
                    extra={"document_id": document_id, "error_message": error_message}
                )
                # Still try to update with service role if user_id is not available
                user_id = None
            
            # Get user-authenticated client to update document status
            try:
                user_client = await self.get_user_client()
                
                # Prepare error details for database storage
                processing_errors = {
                    "error": error_message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": error_details,
                    "processing_failed": True,
                    "failure_stage": error_details.get("node") if error_details else "unknown",
                }
                
                update_data = {
                    "processing_status": ProcessingStatus.FAILED.value,
                    "processing_errors": processing_errors,
                    "processing_completed_at": datetime.now(timezone.utc),
                }
                
                # Update document record with failure status using repository
                from app.services.repositories.documents_repository import DocumentsRepository
                from uuid import UUID
                
                docs_repo = DocumentsRepository(user_id=user_id)
                # Use update_document_status method which properly handles processing_errors field
                await docs_repo.update_document_status(
                    UUID(document_id),
                    ProcessingStatus.FAILED.value,
                    error_details=processing_errors,
                    processing_completed_at=datetime.now(timezone.utc)
                )
                
                self._log_info(
                    f"Successfully updated document {document_id} status to FAILED",
                    extra={
                        "document_id": document_id,
                        "error_message": error_message,
                        "failure_stage": processing_errors["failure_stage"]
                    }
                )
                
            except Exception as db_error:
                self._log_warning(
                    f"Failed to update database status for document {document_id}: {db_error}",
                    extra={
                        "document_id": document_id,
                        "original_error": error_message,
                        "db_error": str(db_error)
                    }
                )
                # Continue - don't fail error handling due to database issues
            
            # Ensure state has proper error information set
            updated_state = state.copy()
            if not updated_state.get("error"):
                updated_state["error"] = error_message
            if not updated_state.get("error_details"):
                updated_state["error_details"] = error_details or {
                    "error_type": "ProcessingError",
                    "error_message": error_message,
                    "node": "error_handling",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "document_id": document_id
                }
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Error handling complete for document {document_id}",
                extra={
                    "document_id": document_id,
                    "duration_seconds": duration,
                    "database_updated": True  # Assume success unless caught above
                }
            )
            
            return updated_state
            
        except Exception as e:
            # Error in error handling - this is a critical issue
            self._log_warning(
                f"Critical error in error handling: {e}",
                extra={
                    "document_id": state.get("document_id"),
                    "original_error": state.get("error"),
                    "error_handling_error": str(e)
                }
            )
            
            # Ensure we return a state with error information
            updated_state = state.copy()
            updated_state["error"] = state.get("error") or f"Error handling failed: {str(e)}"
            updated_state["error_details"] = {
                "error_type": "ErrorHandlingFailure", 
                "error_message": str(e),
                "node": "error_handling",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "original_error": state.get("error"),
                "original_error_details": state.get("error_details")
            }
            
            return updated_state