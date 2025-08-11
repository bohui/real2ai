"""
Diagram Analysis Node for Contract Analysis Workflow

This module contains the node responsible for analyzing contract diagrams and visual elements.
"""

import re
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class DiagramAnalysisNode(BaseNode):
    """
    Node responsible for analyzing contract diagrams and visual elements.

    This node handles:
    - Contract diagram extraction and analysis
    - Visual element interpretation
    - Diagram-based information extraction
    - Integration with textual contract analysis
    """

    def __init__(self, workflow):
        super().__init__(workflow, "diagram_analysis")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Analyze contract diagrams and visual elements.

        Args:
            state: Current workflow state with document data

        Returns:
            Updated state with diagram analysis results
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting diagram analysis", state)

            # Get document data
            document_data = state.get("document_data", {})
            document_metadata = state.get("document_metadata", {})
            
            if not document_data and not document_metadata:
                # No diagram data available - return empty analysis
                diagram_result = {
                    "diagrams_found": False,
                    "diagram_count": 0,
                    "extracted_information": {},
                    "analysis_notes": ["No diagram data available for analysis"],
                    "confidence": 0.0,
                }
                
                state["diagram_analysis"] = diagram_result
                state["confidence_scores"]["diagram_analysis"] = 0.0

                return self.update_state_step(
                    state, 
                    "diagram_analysis_skipped",
                    data={"diagram_result": diagram_result}
                )

            # Check for visual elements or diagram indicators
            has_diagrams = self._detect_diagrams(document_data, document_metadata)
            
            if not has_diagrams:
                # No diagrams detected
                diagram_result = {
                    "diagrams_found": False,
                    "diagram_count": 0,
                    "extracted_information": {},
                    "analysis_notes": ["No diagrams or visual elements detected"],
                    "confidence": 0.8,  # High confidence in "no diagrams"
                }
            else:
                # Analyze detected diagrams
                diagram_result = await self._analyze_detected_diagrams(
                    document_data, document_metadata
                )

            # Update state
            state["diagram_analysis"] = diagram_result
            diagram_confidence = diagram_result.get("confidence", 0.5)
            state["confidence_scores"]["diagram_analysis"] = diagram_confidence

            diagram_data = {
                "diagram_result": diagram_result,
                "diagrams_found": diagram_result.get("diagrams_found", False),
                "diagram_count": diagram_result.get("diagram_count", 0),
                "confidence_score": diagram_confidence,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Diagram analysis completed (found: {diagram_result.get('diagrams_found', False)}, confidence: {diagram_confidence:.2f})",
                state,
                {"diagram_count": diagram_result.get("diagram_count", 0)}
            )

            return self.update_state_step(
                state, "diagram_analysis_completed", data=diagram_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Diagram analysis failed: {str(e)}",
                {"has_document_data": bool(state.get("document_data"))}
            )

    def _detect_diagrams(
        self, document_data: Dict[str, Any], document_metadata: Dict[str, Any]
    ) -> bool:
        """Detect if the document contains diagrams or visual elements."""
        try:
            # Check for image data
            if document_data.get("images") or document_data.get("figures"):
                return True

            # Check for diagram-related keywords in text
            full_text = document_metadata.get("full_text", "")
            if full_text:
                diagram_keywords = [
                    "diagram", "figure", "chart", "map", "plan", "sketch",
                    "illustration", "drawing", "layout", "blueprint"
                ]
                
                text_lower = full_text.lower()
                if any(keyword in text_lower for keyword in diagram_keywords):
                    return True

            # Check metadata for visual elements
            if document_metadata.get("has_images") or document_metadata.get("visual_elements"):
                return True

            return False

        except Exception as e:
            self._log_exception(e, context={"detection_method": "diagram_detection"})
            return False

    async def _analyze_detected_diagrams(
        self, document_data: Dict[str, Any], document_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze detected diagrams and extract relevant information."""
        try:
            extracted_info = {}
            analysis_notes = []
            diagram_count = 0

            # Analyze image data if available
            images = document_data.get("images", [])
            if images:
                diagram_count += len(images)
                analysis_notes.append(f"Found {len(images)} image(s) in document")
                
                # Basic image analysis (placeholder for future enhancement)
                extracted_info["images"] = {
                    "count": len(images),
                    "analysis": "Image content analysis not implemented"
                }

            # Analyze text references to diagrams
            full_text = document_metadata.get("full_text", "")
            if full_text:
                diagram_references = self._extract_diagram_references(full_text)
                if diagram_references:
                    extracted_info["text_references"] = diagram_references
                    analysis_notes.append(f"Found {len(diagram_references)} diagram references in text")

            # Determine confidence based on available data
            if diagram_count > 0:
                confidence = 0.8
            elif extracted_info.get("text_references"):
                confidence = 0.6
            else:
                confidence = 0.3

            return {
                "diagrams_found": diagram_count > 0 or bool(extracted_info.get("text_references")),
                "diagram_count": diagram_count,
                "extracted_information": extracted_info,
                "analysis_notes": analysis_notes,
                "confidence": confidence,
                "analysis_method": "basic_detection",
            }

        except Exception as e:
            self._log_exception(e, context={"analysis_method": "diagram_analysis"})
            return {
                "diagrams_found": False,
                "diagram_count": 0,
                "extracted_information": {},
                "analysis_notes": ["Diagram analysis failed"],
                "confidence": 0.2,
                "error": str(e),
            }

    def _extract_diagram_references(self, text: str) -> list:
        """Extract references to diagrams from text content."""
        try:
            references = []
            
            # Pattern to match diagram references
            patterns = [
                r"see\s+(diagram|figure|chart|map|plan)\s+(\w+)",
                r"(diagram|figure|chart|map|plan)\s+(\d+)",
                r"refer\s+to\s+(diagram|figure|chart|map|plan)",
                r"as\s+shown\s+in\s+(diagram|figure|chart|map|plan)",
            ]
            
            text_lower = text.lower()
            
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    references.append({
                        "reference": match.group(0),
                        "type": match.group(1),
                        "context": text[max(0, match.start()-50):match.end()+50]
                    })
            
            return references
            
        except Exception as e:
            self._log_exception(e, context={"extraction_method": "diagram_references"})
            return []