from datetime import datetime, UTC
from typing import Dict, Any, Optional, TYPE_CHECKING

from app.agents.states.section_analysis_state import Step2AnalysisState

if TYPE_CHECKING:
    from app.agents.subflows.step2_section_analysis_workflow import (
        Step2AnalysisWorkflow,
    )
from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.prompts.schema.step2.parties_property_schema import (
    PartiesPropertyAnalysisResult,
)


class PartiesPropertyNode(ContractLLMNode):
    def __init__(
        self,
        workflow: "Step2AnalysisWorkflow",
        progress_range: tuple[int, int] = (2, 12),
    ):
        super().__init__(
            workflow=workflow,  # will be set by caller if needed; BaseNode doesn't require it
            node_name="analyze_parties_property",
            contract_attribute="parties_property",
            result_model=PartiesPropertyAnalysisResult,
        )
        # Use BaseNode progress tracking if available in caller context
        self.progress_range = progress_range

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.prompts.schema.step2.parties_property_schema import (
            PartiesPropertyAnalysisResult,
        )

        # Prefer metadata from extracted_entity
        entities = state.get("extracted_entity", {}) or {}
        meta = (entities or {}).get("metadata") or {}

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                # Seeds + metadata; avoid passing full text by default
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "extracted_entity": entities,
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

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["parties_property"] = value

        await self.emit_progress(
            state, self.progress_range[1], "Parties and property analysis completed"
        )

        return {
            "parties_property": value,
        }
