from typing import Dict, Any
from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class InitializeWorkflowNode(Step2NodeBase):
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
