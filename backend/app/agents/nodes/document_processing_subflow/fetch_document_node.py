"""
FetchDocumentRecordNode - Load document metadata from database

This node loads document metadata including storage_path, file_type, and content_hash
from the database using user-authenticated context.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase
from app.services.repositories.documents_repository import DocumentsRepository


class FetchDocumentRecordNode(DocumentProcessingNodeBase):
    """
    Node responsible for fetching document metadata from the database.
    
    This node:
    1. Validates document access using user authentication context
    2. Loads document metadata (storage_path, file_type, content_hash) 
    3. Ensures the document exists and user has access
    
    State Updates:
    - storage_path: Path to document in storage
    - file_type: Document file type
    - content_hash: Document content hash (if available)
    """
    
    def __init__(self):
        super().__init__("fetch_document_record")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Fetch document metadata from database.
        
        Args:
            state: Current processing state with document_id
            
        Returns:
            Updated state with document metadata or error
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
                    {"provided_state_keys": list(state.keys())}
                )
            
            self._log_info(f"Fetching document record for ID: {document_id}")
            
            # Fetch document record with RLS enforcement using repository
            docs_repo = DocumentsRepository()
            document_obj = await docs_repo.get_document(UUID(document_id))
            
            if not document_obj:
                return self._handle_error(
                    state,
                    ValueError("Document not found or access denied"),
                    "Document not found or access denied",
                    {
                        "document_id": document_id,
                        "user_has_access": False
                    }
                )
            
            # Convert to dict for backward compatibility
            document = {
                "id": str(document_obj.id),
                "storage_path": document_obj.storage_path,
                "file_type": document_obj.file_type,
                "content_hash": document_obj.content_hash,
                "processing_status": document_obj.processing_status,
                "original_filename": document_obj.original_filename,
            }
            
            # Extract required metadata
            storage_path = document.get("storage_path")
            file_type = document.get("file_type")
            content_hash = document.get("content_hash")
            processing_status = document.get("processing_status")
            original_filename = document.get("original_filename")
            
            if not storage_path or not file_type:
                return self._handle_error(
                    state,
                    ValueError("Incomplete document metadata"),
                    "Document metadata is incomplete",
                    {
                        "document_id": document_id,
                        "has_storage_path": bool(storage_path),
                        "has_file_type": bool(file_type)
                    }
                )
            
            # Update state with fetched metadata
            updated_state = state.copy()
            updated_state["storage_path"] = storage_path
            updated_state["file_type"] = file_type
            updated_state["content_hash"] = content_hash or state.get("content_hash")
            
            # Store additional metadata for later use
            updated_state["_document_metadata"] = {
                "original_filename": original_filename,
                "processing_status": processing_status,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Successfully fetched document metadata",
                extra={
                    "document_id": document_id,
                    "storage_path": storage_path,
                    "file_type": file_type,
                    "has_content_hash": bool(content_hash),
                    "processing_status": processing_status,
                    "duration_seconds": duration
                }
            )
            
            return updated_state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to fetch document metadata: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_select",
                    "table": "documents"
                }
            )