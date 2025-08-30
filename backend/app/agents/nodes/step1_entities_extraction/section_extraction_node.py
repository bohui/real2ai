"""
Section Extraction Node for Contract Analysis Workflow

Extracts only section_seeds using the same prompt context as entities extraction,
and persists to a dedicated contracts column/state field.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.states.contract_state import RealEstateAgentState
from app.prompts.schema.section_extraction_schema import SectionExtractionOutput
from app.core.prompts.parsers import create_parser
from ..contract_llm_base import ContractLLMNode

logger = logging.getLogger(__name__)


class SectionExtractionNode(ContractLLMNode):
    """
    Extracts only section seeds from the Step 1 prompt output and saves them separately.
    """

    def __init__(self, workflow):
        super().__init__(
            workflow=workflow,
            node_name="section_extraction",
            contract_attribute="extracted_sections",
            result_model=SectionExtractionOutput,
        )
        self._parser = create_parser(
            SectionExtractionOutput, strict_mode=False, retry_on_failure=True
        )

    async def _build_context_and_parser(self, state: RealEstateAgentState):
        from app.core.prompts import PromptContext, ContextType

        full_text = await self.get_full_text(state)

        document_metadata = state.get("step0_ocr_processing", {})
        contract_type_value = state.get("contract_type") or "purchase_agreement"
        user_type_value = state.get("user_type") or "general"
        user_experience_value = (
            state.get("user_experience_level")
            or state.get("user_experience")
            or "intermediate"
        )

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "contract_text": full_text,
                "analysis_type": "section_seeds",
                "document_metadata": document_metadata,
                "contract_type": contract_type_value,
                "user_type": user_type_value,
                "user_experience": user_experience_value,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            },
        )
        parser = self._parser
        return context, parser, "section_seeds_extraction"
