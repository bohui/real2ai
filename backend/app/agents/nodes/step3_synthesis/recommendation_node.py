from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.action_plan_schema import ActionPlanResult
from app.core.prompts.parsers import create_parser

logger = logging.getLogger(__name__)


class ActionPlanNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (5, 10)):
        super().__init__(
            workflow=workflow,
            node_name="generate_recommendations",
            contract_attribute="recommendations",
            result_model=ActionPlanResult,
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
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
            "adjustments_outgoings_result": state.get(
                "adjustments_outgoings_result", {}
            ),
            "disclosure_compliance_result": state.get(
                "disclosure_compliance_result", {}
            ),
            "conditions_result": state.get("conditions_result", {}),
        }

        # Validate required inputs for recommendations
        required_inputs = [
            "cross_section_validation_result",
            "settlement_logistics_result",
            "conditions_result",
        ]

        missing_inputs = []
        for input_name in required_inputs:
            if not context_dict.get(input_name):
                missing_inputs.append(input_name)

        if missing_inputs:
            logger.warning(
                f"Missing required inputs for action planning: {missing_inputs}"
            )

        context = PromptContext(**context_dict)
        populated = len([k for k, v in context_dict.items() if v])
        logger.info(f"Built recommendations context with {populated} populated fields")

        parser = create_parser(
            ActionPlanResult, strict_mode=False, retry_on_failure=True
        )
        composition_name = "step3_recommendations"
        return context, parser, composition_name

    # Coercion handled by base class via result_model

    async def _validate_and_enhance_result(
        self, raw_result: Dict[str, Any], state: Step3SynthesisState
    ) -> Dict[str, Any]:
        """Validate and enhance the recommendations result"""
        try:
            # Validate against our strict schema
            validated_result = ActionPlanResult(**raw_result)

            # Add metadata about the analysis
            enhanced_result = validated_result.dict()
            enhanced_result["metadata"].update(
                {
                    "generator_node": "action_plan",
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "input_sources": [
                        "cross_section_validation_result",
                        "settlement_logistics_result",
                        "adjustments_outgoings_result",
                        "disclosure_compliance_result",
                        "conditions_result",
                    ],
                    "total_actions": len(validated_result.actions),
                    "critical_actions": len(
                        [
                            a
                            for a in validated_result.actions
                            if a.priority.value == "critical"
                        ]
                    ),
                    "high_priority_actions": len(
                        [
                            a
                            for a in validated_result.actions
                            if a.priority.value == "high"
                        ]
                    ),
                    "critical_path_length": len(validated_result.critical_path),
                    "schema_version": "1.2.0",
                }
            )

            logger.info(
                f"Recommendations completed: {len(validated_result.actions)} actions, "
                f"{len(validated_result.critical_path)} critical path items"
            )

            return enhanced_result

        except Exception as e:
            logger.error(f"Action plan validation failed: {e}")
            # Return a minimal valid result
            fallback_result = {
                "actions": [
                    {
                        "title": "Review Contract Analysis",
                        "description": "Manual review required due to system error in action plan generation",
                        "owner": "solicitor",
                        "priority": "high",
                        "due_by": {"relative_deadline": "before settlement"},
                        "dependencies": [],
                        "blocking_risks": ["Analysis incomplete"],
                        "estimated_duration_days": 5,
                    }
                ],
                "timeline_summary": f"Recommendations generation failed: {str(e)}. Manual review required.",
                "critical_path": ["Review Contract Analysis"],
                "total_estimated_days": 5,
                "metadata": {
                    "validation_error": str(e),
                    "fallback_result": True,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            }
            return fallback_result

    # Use base class execute()
