"""
Entities Extraction Node for Contract Analysis Workflow

Runs entity extraction using the contract_entities_extraction prompt
and parses into ContractEntityExtraction.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.states.contract_state import RealEstateAgentState
from app.prompts.schema.entity_extraction_schema import ContractEntityExtraction
from app.core.prompts.parsers import create_parser
from app.schema.enums.property import ContractType
from ..contract_llm_base import ContractLLMNode

logger = logging.getLogger(__name__)


class EntitiesExtractionNode(ContractLLMNode):
    """
    Performs entity extraction from contracts to identify key information
    such as parties, dates, financial amounts, and property details.
    """

    def __init__(self, workflow):
        super().__init__(
            workflow=workflow,
            node_name="entities_extraction",
            contract_attribute="extracted_entity",
            state_attribute="step1_extracted_entity",
            result_model=ContractEntityExtraction,
        )
        # Local parser instance; do not rely on workflow-managed parsers
        self._parser = create_parser(
            ContractEntityExtraction, strict_mode=False, retry_on_failure=True
        )

    # Short-circuit provided by ContractLLMNode

    async def _build_context_and_parser(self, state: RealEstateAgentState):
        from app.core.prompts import PromptContext, ContextType

        # Use shared helper on base class
        full_text = await self.get_full_text(state)

        document_metadata = state.get("ocr_processing", {})
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
                "analysis_type": "extracted_entity",
                "document_metadata": document_metadata,
                "contract_type": contract_type_value,
                "user_type": user_type_value,
                "user_experience": user_experience_value,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Use local parser specific to this node
        parser = self._parser
        return context, parser, "contract_entities_extraction"

    # Coercion handled by base class via result_model

    def _evaluate_quality(
        self, result: Optional[ContractEntityExtraction], state: RealEstateAgentState
    ) -> Dict[str, Any]:

        min_confidence: float = float(self.CONFIG_KEYS["min_confidence"])
        if result is None:
            return {"ok": False}
        try:
            coverage = {
                "has_parties": bool(result.parties),
                "has_dates": bool(result.dates),
                "has_financial_amounts": bool(result.financial_amounts),
                "has_property_details": bool(result.property_details),
                "has_legal_references": bool(result.legal_references),
                "has_conditions": hasattr(result, "conditions")
                and bool(getattr(result, "conditions", [])),
            }
            overall_conf = getattr(result, "confidence_score", 0.0)
            coverage_score = sum(1 for v in coverage.values() if v) / max(
                len(coverage), 1
            )
            ok = (overall_conf >= min_confidence) or coverage_score >= 0.7
            return {
                "ok": ok,
                "confidence_score": overall_conf,
                "coverage_score": coverage_score,
                **coverage,
            }
        except Exception:
            return {"ok": False}

    # Persist handled by ContractLLMNode using _build_updated_fields

    async def _persist_results(
        self, state: RealEstateAgentState, parsed: ContractEntityExtraction
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

            # Upsert root-level taxonomy + address alongside extracted_entity payload
            repo = ContractsRepository()

            # Root fields
            try:
                metadata = getattr(parsed, "metadata", None)
                contract_type = (
                    str(getattr(metadata, "contract_type", None).value)
                    if getattr(metadata, "contract_type", None) is not None
                    else None
                )
                purchase_method = (
                    str(getattr(metadata, "purchase_method", None).value)
                    if getattr(metadata, "purchase_method", None) is not None
                    else None
                )
                use_category = (
                    str(getattr(metadata, "use_category", None).value)
                    if getattr(metadata, "use_category", None) is not None
                    else None
                )
                state_val = (
                    str(getattr(metadata, "state", None).value)
                    if getattr(metadata, "state", None) is not None
                    else None
                )
            except Exception:
                contract_type = None
                purchase_method = None
                use_category = None
                state_val = None

            try:
                property_address = None
                if parsed.property_address and parsed.property_address.full_address:
                    property_address = parsed.property_address.full_address
            except Exception:
                property_address = None

            # Persist root fields + extracted_entity JSON
            await repo.upsert_contract_by_content_hash(
                content_hash,
                contract_type=contract_type,
                purchase_method=purchase_method,
                use_category=use_category,
                state=state_val,
                extracted_entity=parsed.model_dump(mode="json"),
                property_address=property_address,
                updated_by=self.node_name,
            )
        except Exception as repo_err:
            logger.warning(
                f"{self.__class__.__name__}: Section persist failed (non-fatal): {repo_err}"
            )

    def _build_updated_fields(
        self, parsed: ContractEntityExtraction, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        def _to_str(v: Any) -> Optional[str]:
            try:
                if v is None:
                    return None
                return str(v.value) if hasattr(v, "value") else str(v)
            except Exception:
                return None

        metadata = parsed.metadata
        property_address = None
        try:
            if parsed.property_address and parsed.property_address.full_address:
                property_address = parsed.property_address.full_address
        except Exception:
            property_address = None

        return {
            "contract_type": _to_str(
                getattr(metadata, "contract_type", ContractType.UNKNOWN)
            ),
            "purchase_method": _to_str(getattr(metadata, "purchase_method", None)),
            "use_category": _to_str(getattr(metadata, "use_category", None)),
            "state": _to_str(getattr(metadata, "state", None)),
            "property_address": property_address,
            "step1_extracted_entity": parsed.model_dump(),
        }

    async def _update_state_success(
        self,
        state: RealEstateAgentState,
        parsed: ContractEntityExtraction,
        quality: Dict[str, Any],
    ) -> RealEstateAgentState:
        data = parsed.model_dump()
        # Primary: write to state field (may differ from DB column)
        state[self.state_attribute] = data
        if parsed.metadata and parsed.metadata.overall_confidence is not None:
            state.setdefault("confidence_scores", {})[
                self.state_attribute
            ] = parsed.metadata.overall_confidence

        return self.update_state_step(
            state,
            "entities_extraction_complete",
            data={
                "overall_confidence": (
                    parsed.metadata.overall_confidence if parsed.metadata else None
                ),
                "has_parties": bool(parsed.parties),
                "has_dates": bool(parsed.dates),
                "has_financial_amounts": bool(parsed.financial_amounts),
                "has_property_details": bool(parsed.property_details),
                "has_legal_references": bool(parsed.legal_references),
            },
        )
