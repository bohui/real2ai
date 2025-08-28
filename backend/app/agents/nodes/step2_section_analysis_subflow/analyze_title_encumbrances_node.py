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
        from app.prompts.schema.step2.title_encumbrances_schema import (
            TitleEncumbrancesAnalysisResult,
        )

        super().__init__(
            workflow=workflow,
            node_name="analyze_title_encumbrances",
            contract_attribute="title_encumbrances",
            result_model=TitleEncumbrancesAnalysisResult,
        )
        self.progress_range = progress_range

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
                "image_semantics_result": state.get("image_semantics"),
                # Parties & property baseline from Phase 1 (Step 2 foundation)
                "parties_property_result": state.get("parties_property"),
            },
        )

        parser = create_parser(
            TitleEncumbrancesAnalysisResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_title_encumbrances"

    # Coercion handled by base class via result_model

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["title_encumbrances"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Title and encumbrances analysis completed"
        )
        return {"title_encumbrances": value}
