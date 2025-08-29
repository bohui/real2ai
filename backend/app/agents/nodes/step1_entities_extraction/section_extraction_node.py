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

        document_metadata = state.get("document_metadata", {})
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

    def _evaluate_quality(
        self, result: Optional[SectionExtractionOutput], state: RealEstateAgentState
    ) -> Dict[str, Any]:
        try:
            if result is None:
                return {"ok": False}

            data = result.model_dump() if hasattr(result, "model_dump") else {}
            seeds = data.get("section_seeds") or {}
            has_any_snippets = (
                any(
                    isinstance(v, list) and len(v) > 0
                    for v in (seeds.get("snippets") or {}).values()
                )
                if isinstance(seeds, dict)
                else False
            )

            confidence = float(getattr(result, "confidence_score", 0.0))
            min_conf = float(self.CONFIG_KEYS.get("min_confidence", 0.5))
            ok = has_any_snippets or confidence >= min_conf
            return {
                "ok": ok,
                "has_snippets": has_any_snippets,
                "confidence_score": confidence,
            }
        except Exception:
            return {"ok": False}

    async def _persist_results(
        self, state: RealEstateAgentState, parsed: SectionExtractionOutput
    ) -> None:
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")
            if not content_hash:
                logger.warning(
                    f"{self.__class__.__name__}: Missing content_hash; skipping contract persist"
                )
                return

            seeds = None
            try:
                payload = parsed.model_dump(mode="json")
                seeds = payload.get("section_seeds") or {}
            except Exception:
                seeds = {}

            repo = ContractsRepository()
            # Persist to dedicated column via generic updater
            await repo.update_section_analysis_key(
                content_hash,
                "extracted_sections",
                seeds,
                updated_by=self.node_name,
            )
        except Exception as repo_err:
            logger.warning(
                f"{self.__class__.__name__}: Section persist failed (non-fatal): {repo_err}"
            )

    def _build_updated_fields(
        self, parsed: SectionExtractionOutput, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        try:
            data = parsed.model_dump()
            seeds = data.get("section_seeds") or {}
        except Exception:
            seeds = {}
        return {"extracted_sections": seeds}

    async def _update_state_success(
        self,
        state: RealEstateAgentState,
        parsed: SectionExtractionOutput,
        quality: Dict[str, Any],
    ) -> RealEstateAgentState:
        try:
            data = parsed.model_dump()
            seeds = data.get("section_seeds") or {}
        except Exception:
            seeds = {}

        state["extracted_sections"] = seeds

        return self.update_state_step(
            state,
            "section_extraction_complete",
            data={
                "has_section_snippets": any(
                    isinstance(v, list) and len(v) > 0
                    for v in (seeds.get("snippets") or {}).values()
                )
            },
        )
