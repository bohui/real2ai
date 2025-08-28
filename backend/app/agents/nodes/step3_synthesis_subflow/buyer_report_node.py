from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.buyer_report_schema import BuyerReportResult
from app.core.prompts.parsers import create_parser

logger = logging.getLogger(__name__)


class BuyerReportNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (15, 20)):
        super().__init__(
            workflow=workflow,
            node_name="synthesize_buyer_report",
            contract_attribute="buyer_report",
            result_model=BuyerReportResult,
        )
        self.progress_range = progress_range

    async def _build_context_and_parser(
        self, state: Step3SynthesisState
    ) -> Tuple[Any, Any, str]:
        from app.core.prompts.context import PromptContext

        # Build comprehensive context from ALL Step 2 and Step 3 results
        context_dict = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "australian_state": state.get("australian_state", "NSW"),
            # Step 3 synthesis results
            "risk_summary_result": state.get("risk_summary_result", {}),
            "action_plan_result": state.get("action_plan_result", {}),
            "compliance_summary_result": state.get("compliance_summary_result", {}),
            # Step 2 analysis results
            "parties_property_result": state.get("parties_property_result", {}),
            "financial_terms_result": state.get("financial_terms_result", {}),
            "conditions_result": state.get("conditions_result", {}),
            "warranties_result": state.get("warranties_result", {}),
            "default_termination_result": state.get("default_termination_result", {}),
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
            "title_encumbrances_result": state.get("title_encumbrances_result", {}),
            "adjustments_outgoings_result": state.get(
                "adjustments_outgoings_result", {}
            ),
            "disclosure_compliance_result": state.get(
                "disclosure_compliance_result", {}
            ),
            "special_risks_result": state.get("special_risks_result", {}),
        }

        # Validate required inputs for buyer report
        step3_inputs = [
            "risk_summary_result",
            "action_plan_result",
            "compliance_summary_result",
        ]
        step2_inputs = [
            "parties_property_result",
            "financial_terms_result",
            "conditions_result",
            "settlement_logistics_result",
            "title_encumbrances_result",
            "disclosure_compliance_result",
        ]

        missing_step3 = [inp for inp in step3_inputs if not context_dict.get(inp)]
        missing_step2 = [inp for inp in step2_inputs if not context_dict.get(inp)]

        if missing_step3:
            logger.warning(f"Missing Step 3 inputs for buyer report: {missing_step3}")
        if missing_step2:
            logger.warning(f"Missing Step 2 inputs for buyer report: {missing_step2}")

        context = PromptContext(**context_dict)

        populated_fields = len([k for k, v in context_dict.items() if v])
        logger.info(
            f"Built buyer report context with {populated_fields} populated fields"
        )

        parser = create_parser(
            BuyerReportResult, strict_mode=False, retry_on_failure=True
        )
        composition_name = "step3_buyer_report"
        return context, parser, composition_name

    # Coercion handled by base class via result_model

    async def _validate_and_enhance_result(
        self, raw_result: Dict[str, Any], state: Step3SynthesisState
    ) -> Dict[str, Any]:
        """Validate and enhance the buyer report result"""
        try:
            # Validate against our strict schema
            validated_result = BuyerReportResult(**raw_result)

            # Add metadata about the analysis
            enhanced_result = validated_result.dict()
            enhanced_result["metadata"].update(
                {
                    "generator_node": "buyer_report",
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "step3_input_sources": [
                        "risk_summary_result",
                        "action_plan_result",
                        "compliance_summary_result",
                    ],
                    "step2_input_sources": [
                        "parties_property_result",
                        "financial_terms_result",
                        "conditions_result",
                        "warranties_result",
                        "default_termination_result",
                        "settlement_logistics_result",
                        "title_encumbrances_result",
                        "adjustments_outgoings_result",
                        "disclosure_compliance_result",
                        "special_risks_result",
                    ],
                    "total_sections": len(validated_result.section_summaries),
                    "total_risks": len(validated_result.key_risks),
                    "total_actions": len(validated_result.action_plan_overview),
                    "overall_recommendation": validated_result.overall_recommendation,
                    "confidence_level": validated_result.confidence_level,
                    "schema_version": "1.2.0",
                }
            )

            logger.info(
                f"Buyer report completed: {len(validated_result.section_summaries)} sections, "
                f"{len(validated_result.key_risks)} risks, {len(validated_result.action_plan_overview)} actions, "
                f"recommendation: {validated_result.overall_recommendation}"
            )

            return enhanced_result

        except Exception as e:
            logger.error(f"Buyer report validation failed: {e}")
            # Return a minimal valid result
            fallback_result = {
                "executive_summary": f"System error prevented complete buyer report generation: {str(e)}. Manual review and analysis required.",
                "section_summaries": [
                    {
                        "section_type": "special_risks",
                        "name": "System Error",
                        "summary": "Report generation failed due to technical issues",
                        "status": "ISSUE",
                    }
                ],
                "key_risks": [
                    {
                        "title": "Incomplete Analysis",
                        "description": f"Technical error prevented full contract analysis: {str(e)}",
                        "severity": "high",
                        "impact_summary": "Manual review required to identify all risks and issues",
                    }
                ],
                "action_plan_overview": [
                    {
                        "title": "Manual Contract Review",
                        "owner": "solicitor",
                        "urgency": "IMMEDIATE",
                        "timeline": "immediately",
                    }
                ],
                "evidence_refs": ["system_error"],
                "overall_recommendation": "RECONSIDER",
                "confidence_level": 0.7,
                "metadata": {
                    "validation_error": str(e),
                    "fallback_result": True,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            }
            return fallback_result

    # Use base class execute()
