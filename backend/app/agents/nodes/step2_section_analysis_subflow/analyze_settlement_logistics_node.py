from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


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
            state_field="settlement_logistics_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        # No reliable contract cache column for settlement yet; skip short-circuit
        return None

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
                "financial_terms_result": state.get("financial_terms_result"),
                "conditions_result": state.get("conditions_result"),
            },
        )

        parser = create_parser(
            SettlementAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_settlement"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.settlement_schema import (
                SettlementAnalysisResult,
            )

            if isinstance(data, SettlementAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return SettlementAnalysisResult.model_validate(data)
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
            ok = conf >= 0.75 and completeness >= 0.6
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
            }
        except Exception:
            return {"ok": False}

    async def _persist_results(self, state: Step2AnalysisState, parsed: Any) -> None:
        # Persist into contracts.section_analysis-like column via repository method
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash") or (
                (state.get("document_data", {}) or {}).get("content_hash")
                or (state.get("document_metadata", {}) or {}).get("content_hash")
            )
            if not content_hash:
                self.logger.warning(
                    "SettlementLogisticsNode: Missing content_hash; skipping persist"
                )
                return

            repo = ContractsRepository()
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            await repo.update_section_analysis_key(
                content_hash, "settlement_logistics", value, updated_by=self.node_name
            )
        except Exception as pe:
            self.logger.warning(
                f"Failed to persist settlement_logistics via repository: {pe}"
            )

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["settlement_logistics_result"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Settlement logistics analysis completed"
        )
        return {"settlement_logistics_result": value}
