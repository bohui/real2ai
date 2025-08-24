from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class CheckPhase2CompletionNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (75, 77)):
        super().__init__("check_phase2_completion", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        required_results = ["settlement_logistics_result", "title_encumbrances_result"]
        completed_count = sum(
            1 for key in required_results if state.get(key) is not None
        )
        total_count = len(required_results)
        if completed_count == total_count:
            await self.emit_progress(state, self.progress_range[1], "Phase 2 completed")
            return {
                "phase2_complete": True,
                "phase_completion_times": {"phase2": datetime.now(UTC)},
            }
        return {}
