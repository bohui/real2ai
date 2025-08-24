from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class FinalizeResultsNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (98, 100)):
        super().__init__("finalize_results", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        total_duration = (
            (datetime.now(UTC) - state["start_time"]).total_seconds()
            if state.get("start_time")
            else 0
        )
        self.logger.info(
            "Step 2 workflow completed",
            extra={
                "total_duration_seconds": total_duration,
                "phase1_complete": state.get("phase1_complete", False),
                "phase2_complete": state.get("phase2_complete", False),
                "phase3_complete": state.get("phase3_complete", False),
                "processing_errors": len(state.get("processing_errors", [])),
                "skipped_analyzers": len(state.get("skipped_analyzers", [])),
                "total_risk_flags": len(state.get("total_risk_flags", [])),
                "diagrams_processed": state.get("total_diagrams_processed", 0),
            },
        )
        await self.emit_progress(
            state, self.progress_range[1], "Finalized Step 2 results"
        )
        return {}
