from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.settlement_schema import (
    SettlementAnalysisResult,
)


class SettlementLogisticsNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (84, 88),
    ):
        super().__init__(
            workflow=workflow,
            node_name="analyze_settlement_logistics",
            contract_attribute="settlement_logistics",
            result_model=SettlementAnalysisResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.prompts.schema.step2.settlement_schema import (
            SettlementAnalysisResult,
        )
        from app.core.prompts.parsers import create_parser

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "australian_state": state.get("australian_state") or "NSW",
                "contract_type": state.get("contract_type") or "purchase_agreement",
                "retrieval_index_id": state.get("retrieval_index_id"),
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "seed_snippets": (state.get("section_seeds", {}) or {})
                .get("snippets", {})
                .get("settlement"),
                # Dependencies used by the user prompt for integration sections
                "financial_terms_result": state.get("financial_terms"),
                "conditions_result": state.get("conditions"),
            },
        )

        parser = create_parser(
            SettlementAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_settlement"

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            ok = conf >= 0.75 and completeness >= 0.6
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["settlement_logistics"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Settlement logistics analysis completed"
        )
        return {"settlement_logistics": value}
