from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


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
            state_field="special_risks_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        return None

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.step2.special_risks_schema import (
            SpecialRisksAnalysisResult,
        )

        # Build a compact cross-section bundle instead of full text
        all_section_results = {
            "parties_property": state.get("parties_property_result"),
            "financial_terms": state.get("financial_terms_result"),
            "conditions": state.get("conditions_result"),
            "warranties": state.get("warranties_result"),
            "default_termination": state.get("default_termination_result"),
            "settlement_logistics": state.get("settlement_logistics_result"),
            "title_encumbrances": state.get("title_encumbrances_result"),
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

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.special_risks_schema import (
                SpecialRisksAnalysisResult,
            )

            if isinstance(data, SpecialRisksAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return SpecialRisksAnalysisResult.model_validate(data)
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
                content_hash, "special_risks", value, updated_by=self.node_name
            )
        except Exception:
            pass

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["special_risks_result"] = value
        await self.emit_progress(
            state, self.progress_range[1], "Special risks identification completed"
        )
        return {"special_risks_result": value}
