from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.states.section_analysis_state import Step2AnalysisState


class FinalizeResultsNode(Step2NodeBase):
    def __init__(
        self,
        workflow,
        node_name: str = "finalize_results",
        progress_range: tuple[int, int] = (98, 100),
    ):
        super().__init__(workflow, node_name, progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        total_duration = (
            (datetime.now(UTC) - state["start_time"]).total_seconds()
            if state.get("start_time")
            else 0
        )
        # Summarize presence of section results (DAG-based; no phase flags)
        section_keys = [
            "parties_property_result",
            "financial_terms_result",
            "conditions_result",
            "warranties_result",
            "default_termination_result",
            "settlement_logistics_result",
            "title_encumbrances_result",
            "adjustments_outgoings_result",
            "disclosure_compliance_result",
            "special_risks_result",
            "cross_section_validation_result",
        ]
        results_present = sum(1 for k in section_keys if state.get(k) is not None)

        self.logger.info(
            "Step 2 workflow completed",
            extra={
                "total_duration_seconds": total_duration,
                "results_present": results_present,
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
