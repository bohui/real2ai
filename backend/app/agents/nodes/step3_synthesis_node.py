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

            # Persist high-level results into state
            state.setdefault("analysis_results", {})["step3"] = {
                "risk_summary": s3_results.get("risk_summary", {}),
                "action_plan": s3_results.get("action_plan", {}),
                "compliance_summary": s3_results.get("compliance_summary", {}),
                "buyer_report": s3_results.get("buyer_report", {}),
                "timestamp": s3_results.get("timestamp"),
            }

            self._log_step_debug(
                "Step 3 synthesis completed",
                state,
                {
                    "has_risk_summary": bool(s3_results.get("risk_summary")),
                    "has_action_plan": bool(s3_results.get("action_plan")),
                    "has_compliance_summary": bool(s3_results.get("compliance_summary")),
                    "has_buyer_report": bool(s3_results.get("buyer_report")),
                },
            )

            return self.update_state_step(state, "step3_synthesis_complete", data=s3_results)
        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Step 3 synthesis failed: {str(e)}",
                {"node": "step3_synthesis"},
            )