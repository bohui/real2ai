from typing import Dict, Any
from datetime import datetime, UTC

from app.agents.nodes.base import BaseNode
from app.agents.states.section_analysis_state import Step2AnalysisState


class InitializeWorkflowNode(BaseNode):
    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        self.logger.info("Initializing Step 2 section analysis workflow")

        # Validate inputs and set start time
        updates: Dict[str, Any] = {}
        updates["start_time"] = datetime.now(UTC)

        if not state.get("contract_text"):
            updates.setdefault("processing_errors", []).append(
                "No contract text provided for Step 2 analysis"
            )

        if not state.get("extracted_entity"):
            updates.setdefault("processing_errors", []).append(
                "No entities extraction result provided for Step 2 analysis"
            )

        # Emit progress
        await self.emit_progress(
            state, self.progress_range[1], "Starting Step 2 section analysis"
        )

        return updates
