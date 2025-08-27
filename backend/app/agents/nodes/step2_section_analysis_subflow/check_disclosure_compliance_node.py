from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.disclosure_schema import (
    DisclosureAnalysisResult,
)


class DisclosureComplianceNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (96, 97),
    ):

        super().__init__(
            workflow=workflow,
            node_name="check_disclosure_compliance",
            contract_attribute="disclosure_compliance",
            result_model=DisclosureAnalysisResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "australian_state": state.get("australian_state") or "NSW",
                "contract_type": state.get("contract_type") or "purchase_agreement",
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "retrieval_index_id": state.get("retrieval_index_id"),
                "seed_snippets": (state.get("section_seeds", {}) or {})
                .get("snippets", {})
                .get("disclosure"),
                # DAG dependencies
                "settlement_logistics_result": state.get("settlement_logistics"),
                "title_encumbrances_result": state.get("title_encumbrances"),
                # soft inputs
                "warranties_result": state.get("warranties"),
                "default_termination_result": state.get("default_termination"),
            },
        )

        parser = create_parser(
            DisclosureAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_disclosure"

    # Coercion handled by base class via result_model

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            assessment = float(
                getattr(result, "compliance_assessment_score", 0.0) or 0.0
            )
            ok = conf >= 0.75 and completeness >= 0.6 and assessment >= 0.7
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "compliance_assessment_score": assessment,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["disclosure_compliance"] = value
        await self.emit_progress(
            state, self.progress_range[1], "Disclosure compliance check completed"
        )
        return {"disclosure_compliance": value}
