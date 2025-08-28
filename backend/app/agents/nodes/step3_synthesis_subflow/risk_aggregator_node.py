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
        from app.prompts.schema.step3.risk_summary_schema import RiskSummaryResult

        super().__init__(
            workflow=workflow,
            node_name="aggregate_risks",
            contract_attribute="risk_summary",
            result_model=RiskSummaryResult,
        )
        self.progress_range = progress_range

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
            "diagram_risk_assessment_result": state.get(
                "diagram_risk_assessment_result", {}
            ),
        }

        required_inputs = [
            "cross_section_validation_result",
            "special_risks_result",
            "disclosure_compliance_result",
            "title_encumbrances_result",
            "settlement_logistics_result",
            "diagram_risk_assessment_result",
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
