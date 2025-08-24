from datetime import datetime, UTC
from typing import Dict, Any, Optional

from .base_node import Step2NodeBase  # kept for typing; not used after refactor
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState
from app.agents.nodes.contract_llm_base import ContractLLMNode


class PartiesPropertyNode(ContractLLMNode):
    def __init__(self, workflow=None, progress_range: tuple[int, int] = (2, 12)):
        super().__init__(
            workflow=workflow,  # will be set by caller if needed; BaseNode doesn't require it
            node_name="analyze_parties_property",
            contract_attribute="parties_property",
            state_field="parties_property_result",
        )
        # Use BaseNode progress tracking if available in caller context
        self.progress_range = progress_range

    async def emit_progress(self, state: Step2AnalysisState, percent: int, desc: str):
        """Emit progress updates for Step 2 workflow"""
        try:
            notify = (state or {}).get("notify_progress")
            if notify and callable(notify):
                await notify(self.node_name, percent, desc)
        except Exception as e:
            self.logger.debug(f"Progress emit failed: {e}")

    def _ensure_content_hash_on_state(self, state: Step2AnalysisState) -> None:
        try:
            if state.get("content_hash") or state.get("content_hmac"):
                return
            entities = state.get("entities_extraction", {}) or {}
            content_hash = entities.get("content_hash") or (
                entities.get("document", {}) or {}
            ).get("content_hash")
            if content_hash:
                state["content_hash"] = content_hash
        except Exception:
            # Non-fatal: base class will simply skip if no content hash is available
            pass

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        self._ensure_content_hash_on_state(state)
        return await super()._short_circuit_check(state)

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.prompts.schema.step2.parties_property_schema import (
            PartiesPropertyAnalysisResult,
        )

        # Prefer metadata from entities_extraction
        entities = state.get("entities_extraction", {}) or {}
        meta = (entities or {}).get("metadata") or {}

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                # Seeds + metadata; avoid passing full text by default
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "entities_extraction": entities,
                "australian_state": state.get("australian_state")
                or meta.get("state")
                or "NSW",
                "contract_type": state.get("contract_type")
                or meta.get("contract_type")
                or "purchase_agreement",
                "use_category": state.get("use_category") or meta.get("use_category"),
                "property_condition": state.get("property_condition")
                or meta.get("property_condition"),
                "purchase_method": state.get("purchase_method")
                or meta.get("purchase_method"),
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "retrieval_index_id": state.get("retrieval_index_id"),
                "seed_snippets": (state.get("section_seeds", {}) or {})
                .get("snippets", {})
                .get("parties_property"),
            },
        )

        from app.core.prompts.parsers import create_parser

        parser = create_parser(
            PartiesPropertyAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_parties_property"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.parties_property_schema import (
                PartiesPropertyAnalysisResult,
            )

            if isinstance(data, PartiesPropertyAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return data.model_validate()
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            # Basic coverage checks
            parties_ok = bool(getattr(result, "parties", []) or [])
            prop_ok = getattr(result, "property_identification", None) is not None
            conf = getattr(result, "confidence_score", 0.0) or 0.0
            ok = (conf >= 0.75) or (parties_ok and prop_ok)
            return {
                "ok": ok,
                "confidence_score": conf,
                "has_parties": parties_ok,
                "has_property_identification": prop_ok,
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
        state["parties_property_result"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Parties and property analysis completed"
        )

        return {
            "parties_property_result": value,
        }
