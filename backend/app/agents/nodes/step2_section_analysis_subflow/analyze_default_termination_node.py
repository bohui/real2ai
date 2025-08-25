from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


class DefaultTerminationNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (40, 48),
    ):
        super().__init__(
            workflow=workflow,
            node_name="analyze_default_termination",
            contract_attribute="default_termination",
            state_field="default_termination_result",
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.prompts.schema.step2.default_termination_schema import (
            DefaultTerminationAnalysisResult,
        )
        from app.core.prompts.parsers import create_parser

        entities = state.get("entities_extraction", {}) or {}
        meta = (entities or {}).get("metadata") or {}

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "entities_extraction": entities,
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
                .get("default_termination"),
            },
        )

        parser = create_parser(
            DefaultTerminationAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_default_termination"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.default_termination_schema import (
                DefaultTerminationAnalysisResult,
            )

            if isinstance(data, DefaultTerminationAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return DefaultTerminationAnalysisResult.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            has_default_termination = bool(
                getattr(result, "default_termination", []) or []
            )
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            ok = (conf >= 0.75 and completeness >= 0.6) or has_default_termination
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "has_default_termination": has_default_termination,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["default_termination_result"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Default and termination analysis completed"
        )

        return {"default_termination_result": value}
