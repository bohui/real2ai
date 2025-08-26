from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.risk_summary_schema import RiskSummaryResult
from app.core.prompts.parsers import create_parser

logger = logging.getLogger(__name__)


class RiskAggregatorNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (0, 5)):
        super().__init__(
            workflow=workflow,
            node_name="aggregate_risks",
            contract_attribute="risk_summary",
            state_field="risk_summary_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step3SynthesisState
    ) -> Optional[Step3SynthesisState]:
        """Check if risk summary already exists and is valid"""
        existing_result = state.get("risk_summary_result")
        if existing_result:
            try:
                validated_result = RiskSummaryResult(**existing_result)
                logger.info(
                    f"Risk aggregation already completed with score: {validated_result.overall_risk_score}"
                )
                return state
            except Exception as e:
                logger.warning(f"Existing risk summary invalid, will regenerate: {e}")
                return None
        return None

    async def _build_context_and_parser(
        self, state: Step3SynthesisState
    ) -> Tuple[Any, Any, str]:
        from app.core.prompts.context import PromptContext

        context_dict = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "australian_state": state.get("australian_state", "NSW"),
            "cross_section_validation_result": state.get(
                "cross_section_validation_result", {}
            ),
            "special_risks_result": state.get("special_risks_result", {}),
            "disclosure_compliance_result": state.get(
                "disclosure_compliance_result", {}
            ),
            "title_encumbrances_result": state.get("title_encumbrances_result", {}),
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
        }

        required_inputs = [
            "cross_section_validation_result",
            "special_risks_result",
            "disclosure_compliance_result",
            "title_encumbrances_result",
            "settlement_logistics_result",
        ]

        missing_inputs = [
            name for name in required_inputs if not context_dict.get(name)
        ]
        if missing_inputs:
            logger.warning(
                f"Missing required inputs for risk aggregation: {missing_inputs}"
            )

        context = PromptContext(**context_dict)
        logger.info(
            f"Built risk aggregation context with {len([k for k, v in context_dict.items() if v])} populated fields"
        )

        parser = create_parser(
            RiskSummaryResult, strict_mode=False, retry_on_failure=True
        )
        composition_name = "step3_risk_aggregation"
        return context, parser, composition_name

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            if isinstance(data, RiskSummaryResult):
                return data
            if hasattr(data, "model_validate"):
                return RiskSummaryResult.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step3SynthesisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            overall = float(getattr(result, "overall_risk_score", 0.0) or 0.0)
            confidence = float(getattr(result, "confidence", 0.0) or 0.0)
            risks_len = len(getattr(result, "top_risks", []) or [])
            coverage_score = 1.0 if risks_len >= 1 else 0.0
            min_conf = 0.75
            ok = (confidence >= min_conf) and (coverage_score >= 0.5)
            return {
                "ok": ok,
                "overall_confidence": confidence,
                "coverage_score": coverage_score,
                "overall_risk_score": overall,
                "num_top_risks": risks_len,
            }
        except Exception:
            return {"ok": False}
