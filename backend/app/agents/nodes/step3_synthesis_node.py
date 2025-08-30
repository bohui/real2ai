import logging
from datetime import datetime, UTC
from typing import Dict, Any

from app.agents.nodes.base import BaseNode
from app.agents.states.contract_state import RealEstateAgentState
from app.agents.subflows.step3_synthesis_workflow import Step3SynthesisWorkflow

logger = logging.getLogger(__name__)


class Step3SynthesisNode(BaseNode):
    def __init__(self, workflow):
        super().__init__(workflow, "step3_synthesis")
        self.step3_workflow = Step3SynthesisWorkflow()

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            step2_results = state.get("step2_analysis_result") or {}
            if not step2_results or not step2_results.get("success"):
                return self._handle_node_error(
                    state,
                    Exception("Missing or unsuccessful Step 2 results"),
                    "Step 3 requires Step 2 results",
                    {"has_step2": bool(step2_results)},
                )

            self._log_step_debug("Starting Step 3 synthesis", state)

            s3_results = await self.step3_workflow.execute(state, step2_results)
            if not s3_results.get("success"):
                return self._handle_node_error(
                    state,
                    Exception(s3_results.get("error", "Unknown Step 3 error")),
                    "Step 3 synthesis execution failed",
                )

            # Persist high-level results into explicit top-level keys
            if s3_results.get("risk_summary"):
                state["step3_risk_assessment"] = {
                    **(state.get("step3_risk_assessment") or {}),
                    "summary": s3_results.get("risk_summary", {}),
                }
            if s3_results.get("compliance_summary"):
                state["step3_compliance_check"] = {
                    **(state.get("step3_compliance_check") or {}),
                    "summary": s3_results.get("compliance_summary", {}),
                }
            # Overwrite recommendations from Step 3 (do not append)
            if s3_results.get("recommendations"):
                state["step3_recommendations"] = s3_results.get("recommendations", [])

            # Populate prefixed buyer report into parent state and avoid duplicating report_data
            if s3_results.get("buyer_report"):
                state["step3_buyer_report"] = s3_results.get("buyer_report")

                # Only set report_data if it's empty or different from buyer report
                current_report = state.get("report_data") or {}
                if current_report != state["step3_buyer_report"]:
                    state["report_data"] = state["step3_buyer_report"]

            self._log_step_debug(
                "Step 3 synthesis completed",
                state,
                {
                    "has_risk_summary": bool(s3_results.get("risk_summary")),
                    "has_recommendations": bool(s3_results.get("recommendations")),
                    "has_compliance_summary": bool(
                        s3_results.get("compliance_summary")
                    ),
                    "has_buyer_report": bool(s3_results.get("buyer_report")),
                },
            )
            return self.update_state_step(
                state,
                "step3_synthesis_complete",
                data={
                    "risk_summary": s3_results.get("risk_summary"),
                    "recommendations": s3_results.get("recommendations"),
                    "compliance_summary": s3_results.get("compliance_summary"),
                    "buyer_report": s3_results.get("buyer_report"),
                },
            )
        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Step 3 synthesis failed: {str(e)}",
                {"node": "step3_synthesis"},
            )
