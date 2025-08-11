"""
BuildSummaryNode - Build final ProcessedDocumentSummary result

This node builds the final ProcessedDocumentSummary from the processing results,
whether from fresh processing or from already-processed document data.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.schema.document import ProcessedDocumentSummary
from .base_node import DocumentProcessingNodeBase


class BuildSummaryNode(DocumentProcessingNodeBase):
    """
    Node responsible for building the final ProcessedDocumentSummary.
    
    This node:
    1. Takes processing results from state or existing summary
    2. Resolves authoritative australian_state from document/contract
    3. Builds ProcessedDocumentSummary with all required fields
    
    State Updates:
    - processed_summary: Final ProcessedDocumentSummary result
    """
    
    def __init__(self):
        super().__init__("build_summary")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Build final ProcessedDocumentSummary result.
        
        Args:
            state: Current processing state with results or existing summary
            
        Returns:
            Updated state with processed_summary
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()
        
        try:
            document_id = state.get("document_id")
            use_llm = state.get("use_llm", True)
            
            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "build_summary"}
                )
            
            # Check if we already have a processed summary (from already_processed_check)
            existing_summary = state.get("processed_summary")
            if existing_summary:
                self._log_info(
                    f"Using existing processed summary for document {document_id}",
                    extra={
                        "document_id": document_id,
                        "summary_source": "already_processed"
                    }
                )
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)
                return state
            
            # Build summary from fresh processing results
            text_extraction_result = state.get("text_extraction_result")
            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Cannot build summary without successful text extraction",
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": text_extraction_result.success if text_extraction_result else False
                    }
                )
            
            self._log_info(
                f"Building summary from processing results for document {document_id}",
                extra={
                    "document_id": document_id,
                    "summary_source": "fresh_processing"
                }
            )
            
            # Get user-authenticated client to resolve metadata
            user_client = await self.get_user_client()
            
            # Extract text results
            full_text = text_extraction_result.full_text or ""
            extraction_methods = text_extraction_result.extraction_methods or []
            primary_method = extraction_methods[0] if extraction_methods else "unknown"
            
            # Retrieve authoritative metadata from document record
            doc_result = await user_client.database.select(
                "documents",
                columns="australian_state, original_filename, file_type, storage_path, content_hash",
                filters={"id": document_id}
            )
            
            if not doc_result.get("data"):
                return self._handle_error(
                    state,
                    ValueError("Document not found while building summary"),
                    "Document record not found during summary building",
                    {"document_id": document_id}
                )
            
            doc_row = doc_result["data"][0]
            australian_state_value = doc_row.get("australian_state")
            original_filename = doc_row.get("original_filename")
            file_type_value = doc_row.get("file_type")
            storage_path_value = doc_row.get("storage_path")
            content_hash_value = doc_row.get("content_hash")
            
            # If document record doesn't have australian_state, derive from contract
            if not australian_state_value and content_hash_value:
                contract_result = await user_client.database.select(
                    "contracts",
                    columns="australian_state",
                    filters={"content_hash": content_hash_value}
                )
                if contract_result.get("data"):
                    australian_state_value = contract_result["data"][0].get("australian_state")
            
            if not australian_state_value:
                return self._handle_error(
                    state,
                    ValueError("Australian state missing"),
                    "Australian state missing; set it on your profile or contract before processing",
                    {
                        "document_id": document_id,
                        "content_hash": content_hash_value,
                        "has_contract_lookup": bool(content_hash_value)
                    }
                )
            
            # Build ProcessedDocumentSummary
            processed_summary = ProcessedDocumentSummary(
                success=True,
                document_id=document_id,
                australian_state=australian_state_value,
                full_text=full_text,
                character_count=len(full_text),
                total_word_count=len(full_text.split()) if full_text else 0,
                total_pages=text_extraction_result.total_pages or len(text_extraction_result.pages),
                extraction_method=primary_method,
                extraction_confidence=text_extraction_result.overall_confidence or 0.0,
                processing_timestamp=datetime.now(timezone.utc).isoformat(),
                llm_used=use_llm,
                original_filename=original_filename,
                file_type=file_type_value,
                storage_path=storage_path_value,
                content_hash=content_hash_value,
            )
            
            # Update state with final summary
            updated_state = state.copy()
            updated_state["processed_summary"] = processed_summary
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Successfully built summary for document {document_id}",
                extra={
                    "document_id": document_id,
                    "australian_state": australian_state_value,
                    "character_count": len(full_text),
                    "total_pages": processed_summary.total_pages,
                    "extraction_method": primary_method,
                    "extraction_confidence": processed_summary.extraction_confidence,
                    "llm_used": use_llm,
                    "duration_seconds": duration
                }
            )
            
            return updated_state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to build document summary: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "build_summary",
                    "has_extraction_result": bool(state.get("text_extraction_result")),
                    "has_existing_summary": bool(state.get("processed_summary"))
                }
            )