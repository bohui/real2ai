import logging
from datetime import datetime, UTC
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from app.agents.states.contract_state import RealEstateAgentState
from app.core.prompts import get_prompt_manager
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.agents.nodes.step3_synthesis_subflow.risk_aggregator_node import (
    RiskAggregatorNode,
)
from app.agents.nodes.step3_synthesis_subflow.action_plan_node import ActionPlanNode
from app.agents.nodes.step3_synthesis_subflow.compliance_score_node import (
    ComplianceScoreNode,
)
from app.agents.nodes.step3_synthesis_subflow.buyer_report_node import BuyerReportNode

logger = logging.getLogger(__name__)


class Step3SynthesisWorkflow:
    def __init__(self):
        # Align with Step2 workflow: provide prompt_manager for nodes
        self.prompt_manager = get_prompt_manager()

        self._create_nodes()
        self.graph = self._build_workflow_graph()

    def _create_nodes(self):
        self.risk_aggregator_node = RiskAggregatorNode(self, (0, 5))
        self.action_plan_node = ActionPlanNode(self, (5, 10))
        self.compliance_score_node = ComplianceScoreNode(self, (10, 15))
        self.buyer_report_node = BuyerReportNode(self, (15, 20))

    def _build_workflow_graph(self):
        graph = StateGraph(Step3SynthesisState)

        graph.add_node("aggregate_risks", self.aggregate_risks)
        graph.add_node("generate_action_plan", self.generate_action_plan)
        graph.add_node("compute_compliance_score", self.compute_compliance_score)
        graph.add_node("synthesize_buyer_report", self.synthesize_buyer_report)

        graph.add_edge(START, "aggregate_risks")
        graph.add_edge("aggregate_risks", "generate_action_plan")
        graph.add_edge("aggregate_risks", "compute_compliance_score")
        graph.add_edge("generate_action_plan", "synthesize_buyer_report")
        graph.add_edge("compute_compliance_score", "synthesize_buyer_report")
        graph.add_edge("synthesize_buyer_report", END)

        return graph.compile()

    async def aggregate_risks(self, state: Step3SynthesisState) -> Step3SynthesisState:
        return await self.risk_aggregator_node.execute(state)

    async def generate_action_plan(
        self, state: Step3SynthesisState
    ) -> Step3SynthesisState:
        return await self.action_plan_node.execute(state)

    async def compute_compliance_score(
        self, state: Step3SynthesisState
    ) -> Step3SynthesisState:
        return await self.compliance_score_node.execute(state)

    async def synthesize_buyer_report(
        self, state: Step3SynthesisState
    ) -> Step3SynthesisState:
        return await self.buyer_report_node.execute(state)

    async def execute(
        self, parent_state: RealEstateAgentState, step2_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        section_results = step2_results.get("section_results", {})
        xval = step2_results.get("cross_section_validation", {})

        s3_state: Step3SynthesisState = {
            "australian_state": parent_state.get("australian_state"),
            "contract_type": parent_state.get("contract_type"),
            "section_seeds": parent_state.get("section_seeds"),
            "retrieval_index_id": parent_state.get("retrieval_index_id"),
            # Inputs from Step 2
            "cross_section_validation_result": xval,
            "special_risks_result": section_results.get("special_risks"),
            "disclosure_compliance_result": section_results.get(
                "disclosure_compliance"
            ),
            "title_encumbrances_result": section_results.get("title_encumbrances"),
            "settlement_logistics_result": section_results.get("settlement_logistics"),
            "adjustments_outgoings_result": section_results.get(
                "adjustments_outgoings"
            ),
            "conditions_result": section_results.get("conditions"),
            "parties_property_result": section_results.get("parties_property"),
            "financial_terms_result": section_results.get("financial_terms"),
            "warranties_result": section_results.get("warranties"),
            "default_termination_result": section_results.get("default_termination"),
            # Outputs
            "risk_summary_result": None,
            "action_plan_result": None,
            "compliance_summary_result": None,
            "buyer_report_result": None,
            # Tracking
            "start_time": datetime.now(UTC),
            "processing_errors": [],
            # Contract linkage
            "content_hash": parent_state.get("content_hash"),
            "document_metadata": parent_state.get("document_metadata"),
            "document_data": parent_state.get("document_data"),
            "notify_progress": parent_state.get("notify_progress"),
        }

        try:
            result_state = await self.graph.ainvoke(s3_state)
            return {
                "success": True,
                "risk_summary": result_state.get("risk_summary_result"),
                "action_plan": result_state.get("action_plan_result"),
                "compliance_summary": result_state.get("compliance_summary_result"),
                "buyer_report": result_state.get("buyer_report_result"),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.error(f"Step 3 workflow execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
