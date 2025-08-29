from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.compliance_summary_schema import ComplianceSummaryResult
from app.core.prompts.parsers import create_parser

logger = logging.getLogger(__name__)


class ComplianceScoreNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (10, 15)):
        super().__init__(
            workflow=workflow,
            node_name="compute_compliance_score",
            contract_attribute="compliance_summary",
            result_model=ComplianceSummaryResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(
        self, state: Step3SynthesisState
    ) -> Tuple[Any, Any, str]:
        from app.core.prompts.context import PromptContext

        # Build comprehensive context from Step 2 results
        context_dict = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "australian_state": state.get("australian_state", "NSW"),
            "cross_section_validation_result": state.get(
                "cross_section_validation_result", {}
            ),
            "disclosure_compliance_result": state.get(
                "disclosure_compliance_result", {}
            ),
            "conditions_result": state.get("conditions_result", {}),
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
        }

        # Validate required inputs for compliance analysis
        required_inputs = [
            "cross_section_validation_result",
            "disclosure_compliance_result",
            "conditions_result",
        ]

        missing_inputs = []
        for input_name in required_inputs:
            if not context_dict.get(input_name):
                missing_inputs.append(input_name)

        if missing_inputs:
            logger.warning(
                f"Missing required inputs for compliance analysis: {missing_inputs}"
            )

        context = PromptContext(**context_dict)
        populated = len([k for k, v in context_dict.items() if v])
        logger.info(f"Built compliance context with {populated} populated fields")

        parser = create_parser(
            ComplianceSummaryResult, strict_mode=False, retry_on_failure=True
        )
        composition_name = "step3_compliance_score"
        return context, parser, composition_name

    # Coercion handled by base class via result_model

    async def _validate_and_enhance_result(
        self, raw_result: Dict[str, Any], state: Step3SynthesisState
    ) -> Dict[str, Any]:
        """Validate and enhance the compliance summary result"""
        try:
            # Validate against our strict schema
            validated_result = ComplianceSummaryResult(**raw_result)

            # Add metadata about the analysis
            enhanced_result = validated_result.dict()
            enhanced_result["metadata"].update(
                {
                    "generator_node": "compliance_score",
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "input_sources": [
                        "cross_section_validation_result",
                        "disclosure_compliance_result",
                        "conditions_result",
                        "settlement_logistics_result",
                    ],
                    "total_gaps": len(validated_result.gaps),
                    "compliance_status": validated_result.status.value,
                    "critical_gaps": validated_result.total_gaps_by_severity.get(
                        "critical", 0
                    ),
                    "high_gaps": validated_result.total_gaps_by_severity.get("high", 0),
                    "schema_version": "1.2.0",
                }
            )

            logger.info(
                f"Compliance analysis completed: score={validated_result.score:.3f}, "
                f"status={validated_result.status.value}, gaps={len(validated_result.gaps)}"
            )

            return enhanced_result

        except Exception as e:
            logger.error(f"Compliance summary validation failed: {e}")
            # Return a minimal valid result
            fallback_result = {
                "score": 0.5,
                "status": "requires_review",
                "gaps": [
                    {
                        "name": "System Validation Error",
                        "description": f"Compliance analysis validation failed: {str(e)}",
                        "severity": "high",
                        "remediation": "Manual compliance review required due to system error",
                        "estimated_remediation_days": 5,
                    }
                ],
                "remediation_readiness": f"System error prevented complete compliance analysis: {str(e)}. Manual review required.",
                "key_dependencies": ["manual_review"],
                "total_gaps_by_severity": {"high": 1},
                "estimated_remediation_timeline": 5,
                "metadata": {
                    "validation_error": str(e),
                    "fallback_result": True,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            }
            return fallback_result

    # Use base class execute()
