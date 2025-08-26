from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


class TitleEncumbrancesNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (88, 92),
    ):
        super().__init__(
            workflow=workflow,
            node_name="analyze_title_encumbrances",
            contract_attribute="title_encumbrances",
            state_field="title_encumbrances_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        # Allow base cache check to run (if column is present and populated)
        try:
            return await super()._short_circuit_check(state)  # type: ignore[misc]
        except Exception:
            return None

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.step2.title_encumbrances_schema import (
            TitleEncumbrancesAnalysisResult,
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
                .get("title_encumbrances"),
                # Diagram semantics from Phase 1
                "image_semantics_result": state.get("image_semantics_result"),
                # Parties & property baseline from Phase 1 (Step 2 foundation)
                "parties_property_result": state.get("parties_property_result"),
            },
        )

        parser = create_parser(
            TitleEncumbrancesAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_title_encumbrances"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.step2.title_encumbrances_schema import (
                TitleEncumbrancesAnalysisResult,
            )

            if isinstance(data, TitleEncumbrancesAnalysisResult):
                return data
            if hasattr(data, "model_validate"):
                return TitleEncumbrancesAnalysisResult.model_validate(data)
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
            diagram_integr = float(
                getattr(result, "diagram_integration_score", 0.0) or 0.0
            )
            ok = (conf >= 0.75 and completeness >= 0.6) or (diagram_integr >= 0.6)
            return {
                "ok": ok,
                "confidence_score": conf,
                "completeness_score": completeness,
                "diagram_integration_score": diagram_integr,
            }
        except Exception:
            return {"ok": False}

    async def _persist_results(self, state: Step2AnalysisState, parsed: Any) -> None:
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
                    "TitleEncumbrancesNode: Missing content_hash; skipping persist"
                )
                return

            repo = ContractsRepository()
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            await repo.update_section_analysis_key(
                content_hash, "title_encumbrances", value, updated_by=self.node_name
            )
        except Exception as pe:
            self.logger.warning(
                f"Failed to persist title_encumbrances via repository: {pe}"
            )

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["title_encumbrances_result"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Title and encumbrances analysis completed"
        )
        return {"title_encumbrances_result": value}
