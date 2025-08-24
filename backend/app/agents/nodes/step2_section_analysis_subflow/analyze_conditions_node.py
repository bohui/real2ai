from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState
from app.agents.nodes.contract_llm_base import ContractLLMNode


class ConditionsNode(ContractLLMNode):
    def __init__(self, progress_range: tuple[int, int] = (22, 32)):
        super().__init__(
            workflow=None,
            node_name="analyze_conditions",
            contract_attribute="conditions",
            state_field="conditions_result",
        )
        self.progress_range = progress_range

    def _ensure_content_hash_on_state(self, state: Step2AnalysisState) -> None:
        try:
            if state.get("content_hash") or state.get("content_hmac"):
                return
            entities = state.get("entities_extraction", {}) or {}
            content_hash = entities.get("content_hash") or (
                (entities.get("document", {}) or {}).get("content_hash")
            )
            if content_hash:
                state["content_hash"] = content_hash
        except Exception:
            pass

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        self._ensure_content_hash_on_state(state)
        return await super()._short_circuit_check(state)

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.prompts.schema.step2.conditions_schema import (
            ConditionsAnalysisResult,
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
                .get("conditions"),
            },
        )

        parser = create_parser(
            ConditionsAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_conditions"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.conditions_schema import (
                ConditionsAnalysisResult,
            )

            if isinstance(data, ConditionsAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return ConditionsAnalysisResult.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            has_conditions = bool(getattr(result, "conditions", []) or [])
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            ok = (conf >= 0.75 and completeness >= 0.6) or has_conditions
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "has_conditions": has_conditions,
            }
        except Exception:
            return {"ok": False}

    async def _persist_results(self, state: Step2AnalysisState, parsed: Any) -> None:
        self._ensure_content_hash_on_state(state)
        await super()._persist_results(state, parsed)

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["conditions_result"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Conditions analysis completed"
        )

        return {"conditions_result": value}
