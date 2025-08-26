from datetime import datetime, UTC
from typing import Any, Dict, Optional
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.action_plan_schema import ActionPlanResult

logger = logging.getLogger(__name__)


class ActionPlanNode(ContractLLMNode):
    def __init__(self, workflow, progress_range: tuple[int, int] = (5, 10)):
        super().__init__(
            workflow=workflow,
            node_name="generate_action_plan",
            contract_attribute="action_plan",
            state_field="action_plan_result",
        )
        self.progress_range = progress_range

    async def _short_circuit_check(
        self, state: Step3SynthesisState
    ) -> Optional[Step3SynthesisState]:
        """Check if action plan already exists and is valid"""
        existing_result = state.get("action_plan_result")
        if existing_result:
            try:
                # Validate the existing result against our enhanced schema
                validated_result = ActionPlanResult(**existing_result)
                logger.info(f"Action plan already completed with {len(validated_result.actions)} actions")
                return state
            except Exception as e:
                logger.warning(f"Existing action plan invalid, will regenerate: {e}")
                return None
        return None

    async def _build_context_and_parser(self, state: Step3SynthesisState):
        from app.core.prompts.context import PromptContext
        from app.prompts.schema.step3.action_plan_schema import ActionPlanResult

        # Build comprehensive context from Step 2 results
        context_dict = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "australian_state": state.get("australian_state", "NSW"),
            "cross_section_validation_result": state.get("cross_section_validation_result", {}),
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
            "adjustments_outgoings_result": state.get("adjustments_outgoings_result", {}),
            "disclosure_compliance_result": state.get("disclosure_compliance_result", {}),
            "conditions_result": state.get("conditions_result", {}),
            "seed_snippets": state.get("section_seeds", []),
        }

        # Validate required inputs for action planning
        required_inputs = [
            "cross_section_validation_result",
            "settlement_logistics_result",
            "conditions_result"
        ]
        
        missing_inputs = []
        for input_name in required_inputs:
            if not context_dict.get(input_name):
                missing_inputs.append(input_name)
        
        if missing_inputs:
            logger.warning(f"Missing required inputs for action planning: {missing_inputs}")

        context = PromptContext(**context_dict)
        
        logger.info(f"Built action plan context with {len([k for k, v in context_dict.items() if v])} populated fields")
        
        return context, ActionPlanResult

    async def _validate_and_enhance_result(self, raw_result: Dict[str, Any], state: Step3SynthesisState) -> Dict[str, Any]:
        """Validate and enhance the action plan result"""
        try:
            # Validate against our strict schema
            validated_result = ActionPlanResult(**raw_result)
            
            # Add metadata about the analysis
            enhanced_result = validated_result.dict()
            enhanced_result["metadata"].update({
                "generator_node": "action_plan",
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "input_sources": [
                    "cross_section_validation_result",
                    "settlement_logistics_result",
                    "adjustments_outgoings_result",
                    "disclosure_compliance_result",
                    "conditions_result"
                ],
                "total_actions": len(validated_result.actions),
                "critical_actions": len([a for a in validated_result.actions if a.priority.value == "critical"]),
                "high_priority_actions": len([a for a in validated_result.actions if a.priority.value == "high"]),
                "critical_path_length": len(validated_result.critical_path),
                "schema_version": "1.2.0"
            })
            
            logger.info(f"Action plan completed: {len(validated_result.actions)} actions, "
                       f"{len(validated_result.critical_path)} critical path items")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Action plan validation failed: {e}")
            # Return a minimal valid result
            fallback_result = {
                "actions": [{
                    "title": "Review Contract Analysis",
                    "description": "Manual review required due to system error in action plan generation",
                    "owner": "solicitor",
                    "priority": "high",
                    "due_by": {
                        "relative_deadline": "before settlement"
                    },
                    "dependencies": [],
                    "blocking_risks": ["Analysis incomplete"],
                    "estimated_duration_days": 5
                }],
                "timeline_summary": f"Action plan generation failed: {str(e)}. Manual review required.",
                "critical_path": ["Review Contract Analysis"],
                "total_estimated_days": 5,
                "metadata": {
                    "validation_error": str(e),
                    "fallback_result": True,
                    "analysis_timestamp": datetime.now(UTC).isoformat()
                }
            }
            return fallback_result

    async def execute(self, state: Step3SynthesisState) -> Step3SynthesisState:
        """Execute action plan generation with enhanced validation"""
        try:
            # Check for short circuit
            short_circuit_result = await self._short_circuit_check(state)
            if short_circuit_result:
                return short_circuit_result

            # Build context and get parser
            context, parser_class = await self._build_context_and_parser(state)
            
            # Execute LLM analysis
            raw_result = await self._execute_llm_analysis(context, parser_class)
            
            # Validate and enhance result
            validated_result = await self._validate_and_enhance_result(raw_result, state)
            
            # Update state
            updated_state = state.copy()
            updated_state["action_plan_result"] = validated_result
            
            # Update progress
            progress_update = self._get_progress_update(state)
            updated_state.update(progress_update)
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Action plan node failed: {e}")
            # Return state with error information
            error_state = state.copy()
            error_state["action_plan_result"] = {
                "actions": [{
                    "title": "Manual Contract Review Required",
                    "description": f"System error prevented action plan generation: {str(e)}",
                    "owner": "solicitor",
                    "priority": "critical",
                    "due_by": {
                        "relative_deadline": "immediately"
                    },
                    "dependencies": [],
                    "blocking_risks": ["System failure"],
                    "estimated_duration_days": 1
                }],
                "timeline_summary": "Critical system error - immediate manual intervention required",
                "critical_path": ["Manual Contract Review Required"],
                "total_estimated_days": 1,
                "metadata": {
                    "error": str(e),
                    "node_name": "action_plan",
                    "analysis_timestamp": datetime.now(UTC).isoformat()
                }
            }
            return error_state