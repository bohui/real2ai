from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.special_risks_schema import (
    SpecialRisksAnalysisResult,
)


class SpecialRisksNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (97, 98),
    ):
        super().__init__(
            workflow=workflow,
            node_name="identify_special_risks",
            contract_attribute="special_risks",
            result_model=SpecialRisksAnalysisResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.step2.special_risks_schema import (
            SpecialRisksAnalysisResult,
        )

        # Build a compact cross-section bundle instead of full text
        all_section_results = {
            "parties_property": state.get("parties_property"),
            "financial_terms": state.get("financial_terms"),
            "conditions": state.get("conditions"),
            "warranties": state.get("warranties"),
            "default_termination": state.get("default_termination"),
            "settlement_logistics": state.get("settlement_logistics"),
            "title_encumbrances": state.get("title_encumbrances"),
        }

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
                .get("special_risks"),
                "all_section_results": all_section_results,
            },
        )

        parser = create_parser(
            SpecialRisksAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_special_risks"

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            accuracy = float(getattr(result, "risk_assessment_accuracy", 0.0) or 0.0)
            ok = conf >= 0.75 and completeness >= 0.6 and accuracy >= 0.7
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "risk_assessment_accuracy": accuracy,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["special_risks"] = value
        await self.emit_progress(
            state, self.progress_range[1], "Special risks identification completed"
        )
        return {"special_risks": value}
