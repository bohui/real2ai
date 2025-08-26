from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState


class ActionPlanNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (5, 10)):
        super().__init__(
            workflow=workflow,
            node_name="generate_action_plan",
            contract_attribute="action_plan",
            state_field="action_plan_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step3SynthesisState
    ) -> Optional[Step3SynthesisState]:
        return None

    async def _build_context_and_parser(self, state: Step3SynthesisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.step3.action_plan_schema import ActionPlanResult

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "australian_state": state.get("australian_state") or "NSW",
                "cross_section_validation_result": state.get("cross_section_validation_result"),
                "settlement_logistics_result": state.get("settlement_logistics_result"),
                "adjustments_outgoings_result": state.get("adjustments_outgoings_result"),
                "disclosure_compliance_result": state.get("disclosure_compliance_result"),
                "conditions_result": state.get("conditions_result"),
                "retrieval_index_id": state.get("retrieval_index_id"),
                "seed_snippets": (state.get("section_seeds", {}) or {}).get("snippets", {}).get("action_plan"),
            },
        )
        parser = create_parser(ActionPlanResult, strict_mode=False, retry_on_failure=True)
        return context, parser, "step3_action_plan"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step3.action_plan_schema import ActionPlanResult

            if isinstance(data, ActionPlanResult):
                return data
            if hasattr(data, "model_validate"):
                return ActionPlanResult.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step3SynthesisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            actions = getattr(result, "actions", []) or []
            ok = len(actions) >= 1
            return {"ok": ok, "actions_count": len(actions)}
        except Exception:
            return {"ok": False}

    async def _persist_results(self, state: Step3SynthesisState, parsed: Any) -> None:
        try:
            from app.services.repositories.contracts_repository import ContractsRepository

            content_hash = state.get("content_hash") or (
                (state.get("document_data", {}) or {}).get("content_hash")
                or (state.get("document_metadata", {}) or {}).get("content_hash")
            )
            if not content_hash:
                return
            repo = ContractsRepository()
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            await repo.update_section_analysis_key(
                content_hash, "action_plan", value, updated_by=self.node_name
            )
        except Exception:
            pass

    async def _update_state_success(
        self, state: Step3SynthesisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step3SynthesisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["action_plan_result"] = value
        await self.emit_progress(state, self.progress_range[1], "Action plan generated")
        return {"action_plan_result": value}