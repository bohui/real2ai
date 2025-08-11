"""
SavePagesNode - Persist page-level analysis results to database

This node migrates the _save_document_pages method from DocumentService
to persist page-level text extraction and analysis results.
"""

import uuid
from typing import Dict, Any
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class SavePagesNode(DocumentProcessingNodeBase):
    """
    Node responsible for saving page-level analysis results to database.
    
    This node:
    1. Takes text extraction results from state
    2. Persists page-level data to document_pages table
    3. Maintains user authentication context for RLS enforcement
    
    State Updates:
    - No state changes (database operation only)
    """
    
    def __init__(self):
        super().__init__("save_pages")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Save page-level analysis results to database.
        
        Args:
            state: Current processing state with text_extraction_result
            
        Returns:
            Updated state (no changes, database updated)
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()
        
        try:
            # Validate required state
            document_id = state.get("document_id")
            content_hash = state.get("content_hash")
            text_extraction_result = state.get("text_extraction_result")
            
            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "save_pages"}
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
            
            pages = text_extraction_result.pages
            if not pages:
                self._log_info(f"No pages to save for document {document_id}")
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)
                return state
            
            self._log_info(
                f"Saving {len(pages)} pages for document {document_id}",
                extra={
                    "document_id": document_id,
                    "page_count": len(pages),
                    "has_content_hash": bool(content_hash)
                }
            )
            
            # Get user-authenticated client
            user_client = await self.get_user_client()
            
            # Save each page to database
            pages_saved = 0
            for page in pages:
                page_analysis = page.content_analysis
                layout_features = page_analysis.layout_features
                quality_indicators = page_analysis.quality_indicators
                
                page_data = {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "content_hash": content_hash,
                    "page_number": page.page_number,
                    # Content analysis
                    "text_content": page.text_content,
                    "text_length": page.text_length,
                    "word_count": page.word_count,
                    # Content classification
                    "content_types": page_analysis.content_types,
                    "primary_content_type": page_analysis.primary_type,
                    # Quality metrics
                    "extraction_confidence": page.confidence,
                    "content_quality_score": quality_indicators.structure_score,
                    # Layout analysis
                    "has_header": layout_features.has_header,
                    "has_footer": layout_features.has_footer,
                    "has_signatures": layout_features.has_signatures,
                    "has_diagrams": layout_features.has_diagrams,
                    "has_tables": layout_features.has_tables,
                    # Processing metadata
                    "processed_at": datetime.now(timezone.utc),
                    "processing_method": page.extraction_method or "unknown",
                }
                
                # Save page record with user context
                await user_client.database.create("document_pages", page_data)
                pages_saved += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Successfully saved {pages_saved} pages for document {document_id}",
                extra={
                    "document_id": document_id,
                    "pages_saved": pages_saved,
                    "duration_seconds": duration
                }
            )
            
            return state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to save document pages: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_create",
                    "table": "document_pages",
                    "page_count": len(state.get("text_extraction_result", {}).get("pages", [])) if state.get("text_extraction_result") else 0
                }
            )