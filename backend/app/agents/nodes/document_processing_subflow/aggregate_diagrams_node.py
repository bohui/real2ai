"""
AggregateDiagramsNode - Aggregate diagram detection results from page analysis

This node migrates the _aggregate_diagram_detections method from DocumentService
to analyze page-level diagram detection and create aggregated results.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class AggregateDiagramsNode(DocumentProcessingNodeBase):
    """
    Node responsible for aggregating diagram detection results from page-level analysis.
    
    This node:
    1. Takes text extraction results with page-level diagram analysis
    2. Aggregates diagram detections across all pages
    3. Creates summary statistics and detection metadata
    
    State Updates:
    - diagram_processing_result: Aggregated diagram detection results
    """
    
    def __init__(self):
        super().__init__("aggregate_diagrams")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Aggregate diagram detection results from page analysis.
        
        Args:
            state: Current processing state with text_extraction_result
            
        Returns:
            Updated state with diagram_processing_result
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
                    {"operation": "aggregate_diagrams"}
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
            
            self._log_info(
                f"Aggregating diagram detections for document {document_id}",
                extra={
                    "document_id": document_id,
                    "total_pages": len(text_extraction_result.pages) if text_extraction_result.pages else 0
                }
            )
            
            # Aggregate diagram detection results directly without DocumentService dependency
            diagram_processing_result = self._aggregate_diagram_detections(text_extraction_result)
            
            # Update state with aggregated results
            updated_state = state.copy()
            updated_state["diagram_processing_result"] = diagram_processing_result
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(
                f"Successfully aggregated diagram detections for document {document_id}",
                extra={
                    "document_id": document_id,
                    "total_diagrams": diagram_processing_result.get("total_diagrams", 0),
                    "diagram_pages": len(diagram_processing_result.get("diagram_pages", [])),
                    "diagram_types": list(diagram_processing_result.get("diagram_types", {}).keys()),
                    "detection_summary": diagram_processing_result.get("detection_summary", {}),
                    "duration_seconds": duration
                }
            )
            
            return updated_state
            
        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to aggregate diagram detections: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "aggregate_diagram_detections",
                    "has_extraction_result": bool(state.get("text_extraction_result"))
                }
            )
    
    def _aggregate_diagram_detections(self, text_extraction_result) -> Dict[str, Any]:
        """
        Aggregate diagram detection results from page-level analysis.
        
        Migrated from DocumentService._aggregate_diagram_detections to avoid circular dependency.
        
        Args:
            text_extraction_result: TextExtractionResult with page-level analysis
            
        Returns:
            Dictionary with aggregated diagram detection statistics
        """
        # Constants (copied from DocumentServiceConstants to avoid dependency)
        DEFAULT_PAGE_NUMBER = 0
        MIN_COMPLEX_SHAPE_ITEMS = 1
        
        if not text_extraction_result.success or not text_extraction_result.pages:
            return {
                "total_diagrams": DEFAULT_PAGE_NUMBER,
                "diagram_pages": [],
                "diagram_types": {},
                "detection_summary": {
                    "embedded_images": DEFAULT_PAGE_NUMBER,
                    "vector_graphics": DEFAULT_PAGE_NUMBER,
                    "text_indicators": DEFAULT_PAGE_NUMBER,
                    "mixed_content": DEFAULT_PAGE_NUMBER,
                },
            }

        diagram_pages = []
        diagram_types = {}
        detection_summary = {
            "embedded_images": DEFAULT_PAGE_NUMBER,
            "vector_graphics": DEFAULT_PAGE_NUMBER,
            "text_indicators": DEFAULT_PAGE_NUMBER,
            "mixed_content": DEFAULT_PAGE_NUMBER,
        }

        for page in text_extraction_result.pages:
            page_analysis = page.content_analysis
            layout_features = page_analysis.layout_features

            if layout_features.has_diagrams:
                page_num = page.page_number
                diagram_pages.append(
                    {
                        "page_number": page_num,
                        "content_types": page_analysis.content_types,
                        "primary_type": page_analysis.primary_type,
                        "confidence": page.confidence,
                    }
                )

                # Count diagram types based on content analysis
                primary_type = page_analysis.primary_type
                if primary_type == "diagram":
                    diagram_types["diagram"] = (
                        diagram_types.get("diagram", DEFAULT_PAGE_NUMBER)
                        + MIN_COMPLEX_SHAPE_ITEMS
                    )
                elif primary_type == "mixed" and "diagram" in page_analysis.content_types:
                    diagram_types["mixed"] = (
                        diagram_types.get("mixed", DEFAULT_PAGE_NUMBER)
                        + MIN_COMPLEX_SHAPE_ITEMS
                    )
                    detection_summary["mixed_content"] += MIN_COMPLEX_SHAPE_ITEMS
                else:
                    diagram_types["other"] = (
                        diagram_types.get("other", DEFAULT_PAGE_NUMBER)
                        + MIN_COMPLEX_SHAPE_ITEMS
                    )

                # Increment detection summary (simplified heuristic)
                # In a full implementation, we'd track detection method per page
                detection_summary["text_indicators"] += MIN_COMPLEX_SHAPE_ITEMS

        total_diagrams = len(diagram_pages)

        return {
            "total_diagrams": total_diagrams,
            "diagram_pages": diagram_pages,
            "diagram_types": diagram_types,
            "detection_summary": detection_summary,
            "processing_notes": [
                f"Detected diagrams on {total_diagrams} pages",
                f"Primary detection method: text-based indicators",
                (
                    f"Diagram types found: {list(diagram_types.keys())}"
                    if diagram_types
                    else "No specific diagram types classified"
                ),
            ],
        }