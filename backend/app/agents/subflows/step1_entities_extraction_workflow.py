"""
Step 1 Entities + Sections Extraction Mini-Subflow

This lightweight orchestrator runs the existing Step 1 nodes in sequence:
- EntitiesExtractionNode
- SectionExtractionNode

It is intentionally minimal (no separate LangGraph) to keep overhead low and
to reuse the already-initialized node instances on the parent workflow.
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.states.contract_state import RealEstateAgentState

logger = logging.getLogger(__name__)


class Step1EntitiesExtractionWorkflow:
    """
    Mini subflow that invokes Step 1 extraction nodes using the parent workflow's
    initialized node instances. Executes sequentially to avoid re-entrancy issues.
    """

    def __init__(self, parent_workflow: Any):
        self.parent_workflow = parent_workflow

    async def execute(self, state: RealEstateAgentState) -> Dict[str, Any]:
        start_time = datetime.now(UTC)

        # Preconditions: require some text to be available in state
        full_text = (
            (state.get("step0_ocr_processing") or {}).get("full_text")
            if isinstance(state, dict)
            else None
        )
        if not full_text or len(full_text.strip()) == 0:
            logger.warning("Step 1 subflow invoked without available contract text")
            return {
                "success": False,
                "error": "No contract text available",
                "error_type": "MissingTextError",
            }

        try:
            # 1) Entities extraction
            state = await self.parent_workflow.entities_extraction_node.execute(state)

            # 2) Section seeds extraction
            state = await self.parent_workflow.section_extraction_node.execute(state)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "success": True,
                "timestamp": datetime.now(UTC).isoformat(),
                "total_duration_seconds": duration,
                "extracted_entity": state.get("step1_extracted_entity")
                or state.get("extracted_entity"),
                "extracted_sections": state.get("step1_extracted_sections")
                or state.get("extracted_sections"),
                "workflow_metadata": {
                    "nodes_executed": [
                        "entities_extraction",
                        "section_extraction",
                    ],
                },
            }
        except Exception as e:
            logger.error(f"Step 1 subflow failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }
