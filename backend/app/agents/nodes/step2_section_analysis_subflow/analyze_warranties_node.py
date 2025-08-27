from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.warranties_schema import WarrantiesAnalysisResult


class WarrantiesNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (32, 40),
    ):

        super().__init__(
            workflow=workflow,
            node_name="analyze_warranties",
            contract_attribute="warranties",
            result_model=WarrantiesAnalysisResult,
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
                .get("warranties"),
            },
        )

        parser = create_parser(
            WarrantiesAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_warranties"

    # Coercion handled by base class via result_model

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
        state["warranties"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Warranties analysis completed"
        )

        return {"warranties": value}
