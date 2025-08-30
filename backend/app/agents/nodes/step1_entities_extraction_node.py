"""
Step 1 Entry Node - Entities + Sections Extraction

This node acts as the Step 1 entry point. It invokes a small subflow that runs
the existing `EntitiesExtractionNode` and `SectionExtractionNode` in sequence.

Pattern mirrors Step 0 `DocumentProcessingNode` and Step 2 `SectionAnalysisNode`.
"""

import logging
from datetime import datetime, UTC
from typing import Any, Dict

from app.agents.states.contract_state import RealEstateAgentState
from .base import BaseNode

from app.agents.subflows.step1_entities_extraction_workflow import (
    Step1EntitiesExtractionWorkflow,
)

logger = logging.getLogger(__name__)


class Step1EntitiesExtractionNode(BaseNode):
    def __init__(self, workflow):
        super().__init__(workflow, "step1_extraction")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug(
                "Starting Step 1 entities + sections extraction", state
            )

            # Sanity check for input text (produced by Step 0)
            full_text = (state.get("step0_ocr_processing") or {}).get("full_text", "")
            if not full_text or len(full_text.strip()) == 0:
                return self._handle_node_error(
                    state,
                    Exception("No contract text available for Step 1 extraction"),
                    "Contract text is required for Step 1 extraction",
                    {"state_keys": list(state.keys())},
                )

            # Execute mini subflow using parent workflow's initialized nodes
            subflow = Step1EntitiesExtractionWorkflow(self.workflow)
            result = await subflow.execute(state)

            if not result or not result.get("success", False):
                error_msg = (
                    result.get("error", "Unknown Step 1 subflow error")
                    if isinstance(result, dict)
                    else "Unknown Step 1 subflow error"
                )
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    "Step 1 extraction subflow failed",
                    {
                        "error_type": (
                            result.get("error_type")
                            if isinstance(result, dict)
                            else None
                        ),
                        "has_entity": bool((state or {}).get("step1_extracted_entity")),
                        "has_sections": bool(
                            (state or {}).get("step1_extracted_sections")
                        ),
                    },
                )

            # Prepare execution data for logging/state
            execution_data: Dict[str, Any] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "total_duration": result.get("total_duration_seconds", 0.0),
                "has_entity": bool(
                    state.get("step1_extracted_entity") or state.get("extracted_entity")
                ),
                "has_sections": bool(
                    state.get("step1_extracted_sections")
                    or state.get("extracted_sections")
                ),
            }

            self._log_step_debug(
                "Step 1 entities + sections extraction completed",
                state,
                {
                    "has_entity": execution_data["has_entity"],
                    "has_sections": execution_data["has_sections"],
                },
            )

            return self.update_state_step(
                state, "step1_extraction_complete", data=execution_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Step 1 entities + sections extraction failed: {str(e)}",
                {"node": "step1_extraction"},
            )
