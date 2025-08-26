from datetime import datetime, UTC
from typing import Any, Dict, Optional
import logging

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.states.step3_synthesis_state import Step3SynthesisState
from app.prompts.schema.step3.risk_summary_schema import RiskSummaryResult

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
                # Validate the existing result against our enhanced schema
                validated_result = RiskSummaryResult(**existing_result)
                logger.info(f"Risk aggregation already completed with score: {validated_result.overall_risk_score}")
                return state
            except Exception as e:
                logger.warning(f"Existing risk summary invalid, will regenerate: {e}")
                return None
        return None

    async def _build_context_and_parser(self, state: Step3SynthesisState):
        from app.core.prompts.context import PromptContext
        from app.prompts.schema.step3.risk_summary_schema import RiskSummaryResult

        # Build comprehensive context from Step 2 results
        context_dict = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "australian_state": state.get("australian_state", "NSW"),
            "cross_section_validation_result": state.get("cross_section_validation_result", {}),
            "special_risks_result": state.get("special_risks_result", {}),
            "disclosure_compliance_result": state.get("disclosure_compliance_result", {}),
            "title_encumbrances_result": state.get("title_encumbrances_result", {}),
            "settlement_logistics_result": state.get("settlement_logistics_result", {}),
        }

        # Validate that we have sufficient input data
        required_inputs = [
            "cross_section_validation_result",
            "special_risks_result", 
            "disclosure_compliance_result",
            "title_encumbrances_result",
            "settlement_logistics_result"
        ]
        
        missing_inputs = []
        for input_name in required_inputs:
            if not context_dict.get(input_name):
                missing_inputs.append(input_name)
        
        if missing_inputs:
            logger.warning(f"Missing required inputs for risk aggregation: {missing_inputs}")
            # Still proceed but with reduced confidence

        context = PromptContext(**context_dict)
        
        logger.info(f"Built risk aggregation context with {len([k for k, v in context_dict.items() if v])} populated fields")
        
        return context, RiskSummaryResult

    async def _validate_and_enhance_result(self, raw_result: Dict[str, Any], state: Step3SynthesisState) -> Dict[str, Any]:
        """Validate and enhance the risk summary result"""
        try:
            # Validate against our strict schema
            validated_result = RiskSummaryResult(**raw_result)
            
            # Add metadata about the analysis
            enhanced_result = validated_result.dict()
            enhanced_result["metadata"].update({
                "generator_node": "risk_aggregator",
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "input_sources": [
                    "cross_section_validation_result",
                    "special_risks_result",
                    "disclosure_compliance_result", 
                    "title_encumbrances_result",
                    "settlement_logistics_result"
                ],
                "total_risks_identified": len(validated_result.top_risks),
                "highest_severity": max([risk.severity.value for risk in validated_result.top_risks]) if validated_result.top_risks else "none",
                "schema_version": "1.2.0"
            })
            
            logger.info(f"Risk aggregation completed: score={validated_result.overall_risk_score:.3f}, "
                       f"risks={len(validated_result.top_risks)}, confidence={validated_result.confidence:.3f}")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Risk summary validation failed: {e}")
            # Return a minimal valid result rather than failing completely
            fallback_result = {
                "overall_risk_score": 0.5,
                "top_risks": [],
                "category_breakdown": {"other": 0.5},
                "rationale": f"Risk analysis validation failed: {str(e)}. Manual review required.",
                "confidence": 0.5,
                "metadata": {
                    "validation_error": str(e),
                    "fallback_result": True,
                    "analysis_timestamp": datetime.now(UTC).isoformat()
                }
            }
            return fallback_result

    async def execute(self, state: Step3SynthesisState) -> Step3SynthesisState:
        """Execute risk aggregation with enhanced validation"""
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
            updated_state["risk_summary_result"] = validated_result
            
            # Update progress
            progress_update = self._get_progress_update(state)
            updated_state.update(progress_update)
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Risk aggregation node failed: {e}")
            # Return state with error information
            error_state = state.copy()
            error_state["risk_summary_result"] = {
                "overall_risk_score": 0.5,
                "top_risks": [],
                "category_breakdown": {"other": 0.5},
                "rationale": f"Risk aggregation failed due to system error: {str(e)}",
                "confidence": 0.5,
                "metadata": {
                    "error": str(e),
                    "node_name": "risk_aggregator",
                    "analysis_timestamp": datetime.now(UTC).isoformat()
                }
            }
            return error_state