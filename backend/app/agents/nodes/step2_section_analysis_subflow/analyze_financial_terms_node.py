from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.financial_terms_schema import (
    FinancialTermsAnalysisResult,
)


class FinancialTermsNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (12, 22),
    ):

        super().__init__(
            workflow=workflow,
            node_name="analyze_financial_terms",
            contract_attribute="financial_terms",
            result_model=FinancialTermsAnalysisResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType

        from app.core.prompts.parsers import create_parser

        entities = state.get("extracted_entity", {}) or {}
        meta = (entities or {}).get("metadata") or {}

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "extracted_entity": entities,
                "australian_state": state.get("australian_state")
                or meta.get("state")
                or "NSW",
                "contract_type": state.get("contract_type")
                or meta.get("contract_type")
                or "purchase_agreement",
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "retrieval_index_id": state.get("retrieval_index_id"),
                "seed_snippets": (state.get("section_seeds", {}) or {})
                .get("snippets", {})
                .get("financial_terms"),
            },
        )

        parser = create_parser(
            FinancialTermsAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_financial_terms"

    # Coercion handled by base class via result_model

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            calc_ok = float(getattr(result, "calculation_accuracy_score", 0.0) or 0.0)
            ok = conf >= 0.75 and calc_ok >= 0.7
            return {
                "ok": ok,
                "confidence_score": conf,
                "calculation_accuracy_score": calc_ok,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["financial_terms"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Financial terms analysis completed"
        )

        return {"financial_terms": value}
