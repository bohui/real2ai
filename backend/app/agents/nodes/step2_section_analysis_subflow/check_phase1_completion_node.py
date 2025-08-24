from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class CheckPhase1CompletionNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (48, 50)):
        super().__init__("check_phase1_completion", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        required_results = [
            "parties_property_result",
            "financial_terms_result",
            "conditions_result",
            "warranties_result",
            "default_termination_result",
        ]
        completed_count = sum(
            1 for key in required_results if state.get(key) is not None
        )
        total_count = len(required_results)

        if completed_count == total_count:
            await self.emit_progress(state, self.progress_range[1], "Phase 1 completed")
            return {
                "phase1_complete": True,
                "phase_completion_times": {"phase1": datetime.now(UTC)},
            }
        return {}
