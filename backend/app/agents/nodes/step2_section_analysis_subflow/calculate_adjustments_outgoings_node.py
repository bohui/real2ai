from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


class AdjustmentsOutgoingsNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (94, 96),
    ):
        super().__init__(
            workflow=workflow,
            node_name="calculate_adjustments_outgoings",
            contract_attribute="adjustments_outgoings",
            state_field="adjustments_outgoings_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        return None

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.step2.adjustments_schema import (
            AdjustmentsAnalysisResult,
        )

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
                .get("adjustments"),
                # Dependencies per DAG
                "financial_terms_result": state.get("financial_terms_result"),
                "settlement_logistics_result": state.get("settlement_logistics_result"),
            },
        )

        parser = create_parser(
            AdjustmentsAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_adjustments"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.adjustments_schema import (
                AdjustmentsAnalysisResult,
            )

            if isinstance(data, AdjustmentsAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return AdjustmentsAnalysisResult.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            conf = float(getattr(result, "confidence_score", 0.0) or 0.0)
            completeness = float(getattr(result, "completeness_score", 0.0) or 0.0)
            accuracy = float(getattr(result, "calculation_accuracy_score", 0.0) or 0.0)
            ok = conf >= 0.75 and completeness >= 0.6 and accuracy >= 0.7
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "calculation_accuracy_score": accuracy,
            }
        except Exception:
            return {"ok": False}

    async def _persist_results(self, state: Step2AnalysisState, parsed: Any) -> None:
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")
            if not content_hash:
                return

            repo = ContractsRepository()
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            await repo.update_section_analysis_key(
                content_hash, "adjustments_outgoings", value, updated_by=self.node_name
            )
        except Exception:
            pass

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["adjustments_outgoings_result"] = value
        await self.emit_progress(
            state,
            self.progress_range[1],
            "Adjustments and outgoings calculation completed",
        )
        return {"adjustments_outgoings_result": value}
