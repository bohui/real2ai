"""
SaveDiagramsNode - Persist diagram detection results to database

This node migrates the _save_document_diagrams method from DocumentService
to persist diagram detection results to the document_diagrams table.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class SaveDiagramsNode(DocumentProcessingNodeBase):
    """
    Node responsible for saving diagram detection results to database.
    
    This node:
    1. Takes text extraction results with page-level diagram analysis
    2. Persists diagram detections to document_diagrams table
    3. Uses upsert to handle duplicate entries on retry
    
    State Updates:
    - No state changes (database operation only)
    """
    
    def __init__(self):
        super().__init__("save_diagrams")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Save diagram detection results to database.
        
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
            text_extraction_result = state.get("text_extraction_result")
            
            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "save_diagrams"}
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
                self._log_info(f"No pages to process for diagram detection, document {document_id}")
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)
                return state
            
            self._log_info(
                f"Saving diagram detections for document {document_id}",
                extra={
                    "document_id": document_id,
                    "total_pages": len(pages)
                }
            )
            
            # Get user-authenticated client
            user_client = await self.get_user_client()
            diagrams_saved = 0
            
            for page in pages:
                page_analysis = page.content_analysis
                layout_features = page_analysis.layout_features
                
                # Only save if diagrams were detected on this page
                if layout_features.has_diagrams:
                    # Use diagram type from content analysis or default to unknown
                    resolved_type = getattr(page_analysis, 'diagram_type', 'unknown') or "unknown"
                    
                    diagram_data = {
                        # Note: Intentionally omit "id" to let DB assign or handle conflicts
                        "document_id": document_id,
                        "page_number": page.page_number,
                        # Classification from content analysis
                        "diagram_type": resolved_type,
                        "classification_confidence": page.confidence,
                        # Analysis status
                        "basic_analysis_completed": True,
                        "detailed_analysis_completed": False,
                        # Basic analysis results
                        "basic_analysis": {
                            "content_types": getattr(page_analysis, 'content_types', []),
                            "primary_type": getattr(page_analysis, 'primary_type', None),
                            "detection_method": "text_analysis",
                            "quality_indicators": getattr(page_analysis, 'quality_indicators', {}),
                        },
                        # Quality metrics
                        "image_quality_score": getattr(
                            page_analysis.quality_indicators, 'structure_score', 0.0
                        ) if hasattr(page_analysis, 'quality_indicators') else 0.0,
                        "clarity_score": getattr(
                            page_analysis.quality_indicators, 'readability_score', 0.0
                        ) if hasattr(page_analysis, 'quality_indicators') else 0.0,
                        # Metadata
                        "detected_at": datetime.now(timezone.utc),
                        "basic_analysis_at": datetime.now(timezone.utc),
                    }
                    
                    # Upsert to avoid duplicates on retry
                    # Requires unique index on (document_id, page_number, diagram_type)
                    await user_client.database.upsert(
                        "document_diagrams",
                        diagram_data,
                        conflict_columns=["document_id", "page_number", "diagram_type"]
                    )
                    diagrams_saved += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            if diagrams_saved > 0:
                self._log_info(
                    f"Successfully saved {diagrams_saved} diagrams for document {document_id}",
                    extra={
                        "document_id": document_id,
                        "diagrams_saved": diagrams_saved,
                        "duration_seconds": duration
                    }
                )
            else:
                self._log_info(
                    f"No diagrams detected to save for document {document_id}",
                    extra={
                        "document_id": document_id,
                        "pages_processed": len(pages),
                        "duration_seconds": duration
                    }
                )
            
            return state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to save document diagrams: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_upsert",
                    "table": "document_diagrams",
                    "page_count": len(state.get("text_extraction_result", {}).get("pages", [])) if state.get("text_extraction_result") else 0
                }
            )