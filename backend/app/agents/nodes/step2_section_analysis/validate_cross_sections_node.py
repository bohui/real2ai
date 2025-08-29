from datetime import datetime, UTC
from typing import Any, Dict, Optional

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.cross_validation_schema import (
    CrossValidationResult,
)
from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)


class CrossSectionValidationNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (98, 99),
    ):

        super().__init__(
            workflow=workflow,
            node_name="validate_cross_sections",
            contract_attribute="cross_section_validation",
            result_model=CrossValidationResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser

        all_section_results = {
            "parties_property": state.get("parties_property"),
            "financial_terms": state.get("financial_terms"),
            "conditions": state.get("conditions"),
            "warranties": state.get("warranties"),
            "default_termination": state.get("default_termination"),
            "settlement_logistics": state.get("settlement_logistics"),
            "title_encumbrances": state.get("title_encumbrances"),
            "adjustments_outgoings": state.get("adjustments_outgoings"),
            "disclosure_compliance": state.get("disclosure_compliance"),
            "special_risks": state.get("special_risks"),
        }

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "australian_state": state.get("australian_state") or "NSW",
                "contract_type": state.get("contract_type") or "purchase_agreement",
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "seed_snippets": (state.get("section_seeds", {}) or {})
                .get("snippets", {})
                .get("cross_validation"),
                "all_section_results": all_section_results,
            },
        )

        parser = create_parser(
            CrossValidationResult, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_cross_validation"

    # Coercion handled by base class via result_model

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["cross_section_validation"] = value
        await self.emit_progress(
            state, self.progress_range[1], "Cross-section validation completed"
        )
        return {"cross_section_validation": value}
