"""
Final Validation Node for Contract Analysis Workflow

This module contains the node responsible for final validation of all workflow outputs.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class FinalValidationNode(BaseNode):
    """
    Node responsible for final validation of all workflow outputs.

    This node performs:
    - Comprehensive output validation
    - Data consistency checks
    - Completeness verification
    - Quality assurance for final results
    - Confidence score aggregation
    """

    def __init__(self, workflow):
        super().__init__(workflow, "final_validation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Perform final validation of all workflow outputs.

        Args:
            state: Current workflow state with all analysis results

        Returns:
            Updated state with final validation results
        """
        if not self.enable_validation:
            return state

        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        # Initialize variable used in error context
        use_llm = self.use_llm_config.get("final_validation", True)
        try:
            self._log_step_debug("Starting final validation", state)

            # Gather all workflow outputs
            workflow_outputs = self._gather_workflow_outputs(state)

            if not workflow_outputs:
                return self._handle_node_error(
                    state,
                    Exception("No workflow outputs available for validation"),
                    "No workflow outputs available for validation",
                    {"state_keys": list(state.keys())},
                )

            # Perform validation

            if use_llm:
                try:
                    validation_result = await self._validate_final_output_with_llm(
                        workflow_outputs, state
                    )
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks:
                        validation_result = (
                            await self._validate_final_output_rule_based(
                                workflow_outputs
                            )
                        )
                    else:
                        raise llm_error
            else:
                validation_result = await self._validate_final_output_rule_based(
                    workflow_outputs
                )

            # Update state with validation results
            state["final_validation_result"] = validation_result
            validation_confidence = validation_result.get("overall_confidence", 0.5)
            # Defensive access for confidence_scores
            state.setdefault("confidence_scores", {})[
                "final_validation"
            ] = validation_confidence

            # Determine overall validation status
            validation_passed = validation_result.get("validation_passed", False)
            validation_threshold = 0.7

            if validation_confidence >= validation_threshold and validation_passed:
                validation_status = "passed"
            else:
                validation_status = "failed"

            # Calculate final workflow confidence
            final_confidence = self._calculate_final_workflow_confidence(state)
            state["final_workflow_confidence"] = final_confidence

            validation_data = {
                "validation_result": validation_result,
                "validation_status": validation_status,
                "validation_confidence": validation_confidence,
                "final_workflow_confidence": final_confidence,
                "outputs_validated": len(workflow_outputs),
                "validation_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Final validation completed (status: {validation_status}, confidence: {validation_confidence:.2f})",
                state,
                {"final_workflow_confidence": final_confidence},
            )

            return self.update_state_step(
                state, f"final_validation_{validation_status}", data=validation_data
            )

        except Exception as e:
            return self._handle_node_error(
                state, e, f"Final validation failed: {str(e)}", {"use_llm": use_llm}
            )

    def _gather_workflow_outputs(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Gather all workflow outputs for validation."""
        outputs = {}

        # Core analysis outputs
        core_outputs = [
            "contract_terms",
            "compliance_analysis",
            "risk_assessment",
            "recommendations",
            "diagram_analysis",
        ]

        for output_key in core_outputs:
            if output_key in state and state[output_key]:
                outputs[output_key] = state[output_key]

        # Validation outputs
        validation_outputs = ["document_quality_metrics", "terms_validation_result"]

        for output_key in validation_outputs:
            if output_key in state and state[output_key]:
                outputs[output_key] = state[output_key]

        # Confidence scores
        if "confidence_scores" in state:
            outputs["confidence_scores"] = state["confidence_scores"]

        # Document metadata
        if "document_metadata" in state:
            outputs["document_metadata"] = state["document_metadata"]

        return outputs

    async def _validate_final_output_with_llm(
        self, workflow_outputs: Dict[str, Any], state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Validate final output using LLM analysis."""
        try:
            from app.core.prompts import PromptContext, ContextType

            # Include service-required context variables to satisfy prompt manager validation
            doc_meta = (
                state.get("document_metadata", {}) if isinstance(state, dict) else {}
            )

            # Extract analysis results from state for template variables
            from datetime import datetime, timezone

            # Coalesce None values to satisfy prompt context validation
            risk_assessment_data = state.get("risk_assessment")
            if risk_assessment_data is None:
                risk_assessment_data = {}

            # Prefer canonical key, fall back to compliance_analysis during rendering phase
            compliance_check_data = state.get("compliance_check")
            if not compliance_check_data:
                compliance_check_data = state.get("compliance_analysis") or {}

            # Ensure contract_type is always populated for prompts
            contract_type_value = state.get("contract_type") or "purchase_agreement"

            context = PromptContext(
                context_type=ContextType.VALIDATION,
                variables={
                    "workflow_outputs": workflow_outputs,
                    "validation_type": "final_output",
                    "validation_criteria": [
                        "completeness",
                        "consistency",
                        "accuracy",
                        "relevance",
                    ],
                    "required_outputs": [
                        "contract_terms",
                        "compliance_analysis",
                        "risk_assessment",
                        "recommendations",
                    ],
                    # Service mapping context requirements (best-effort)
                    "extracted_text": (doc_meta.get("full_text", "") or "")[:8000],
                    "australian_state": state.get("australian_state"),
                    "contract_type": contract_type_value,
                    "user_type": state.get("user_type", "general"),
                    "user_experience_level": state.get(
                        "user_experience_level", "intermediate"
                    ),
                    # Template-required variables
                    "analysis_type": state.get("analysis_type", "comprehensive"),
                    "user_experience": state.get(
                        "user_experience",
                        state.get("user_experience_level", "intermediate"),
                    ),
                    "risk_assessment": risk_assessment_data,
                    "compliance_check": compliance_check_data,
                    "recommendations": state.get("recommendations", []),
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="validation/final_output_validation",
                context=context,
                service_name="contract_analysis_workflow",
                # Final validation should not fail hard on missing optional context
                # Disable strict context validation here to allow graceful fallbacks
                validate=False,
            )

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            # Parse structured response
            if self.structured_parsers.get("workflow_validation"):
                parsing_result = self.structured_parsers["workflow_validation"].parse(
                    response
                )
                if parsing_result.success and parsing_result.data:
                    return parsing_result.data

            # Fallback to JSON parsing
            validation_result = self._safe_json_parse(response)
            if validation_result:
                return validation_result

            # Final fallback to rule-based validation
            return await self._validate_final_output_rule_based(workflow_outputs)

        except Exception as e:
            self._log_exception(e, context={"validation_method": "llm"})
            if self.enable_fallbacks:
                return await self._validate_final_output_rule_based(workflow_outputs)
            raise

    async def _validate_final_output_rule_based(
        self, workflow_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate final output using rule-based analysis."""
        try:
            validation_checks = []
            validation_issues = []
            validation_passed = True

            # Check for required outputs
            required_outputs = [
                "contract_terms",
                "compliance_analysis",
                "risk_assessment",
                "recommendations",
            ]

            for required_output in required_outputs:
                if (
                    required_output in workflow_outputs
                    and workflow_outputs[required_output]
                ):
                    validation_checks.append(
                        {
                            "check": f"{required_output}_present",
                            "status": "passed",
                            "details": f"{required_output} is present and populated",
                        }
                    )
                else:
                    validation_checks.append(
                        {
                            "check": f"{required_output}_present",
                            "status": "failed",
                            "details": f"{required_output} is missing or empty",
                        }
                    )
                    validation_issues.append(
                        f"Missing required output: {required_output}"
                    )
                    validation_passed = False

            # Calculate overall validation confidence
            passed_checks = sum(
                1
                for vc in validation_checks
                if isinstance(vc, dict) and vc.get("status") == "passed"
            )
            total_checks = len(validation_checks)
            validation_confidence = (
                passed_checks / total_checks if total_checks > 0 else 0.5
            )

            return {
                "validation_passed": validation_passed,
                "validation_checks": validation_checks,
                "validation_issues": validation_issues,
                "overall_confidence": validation_confidence,
                "validation_method": "rule_based",
                "checks_passed": passed_checks,
                "total_checks": total_checks,
            }

        except Exception as e:
            self._log_exception(e, context={"validation_method": "rule_based"})
            return {
                "validation_passed": False,
                "validation_checks": [],
                "validation_issues": ["Validation process failed"],
                "overall_confidence": 0.2,
                "validation_method": "error_fallback",
                "error": str(e),
            }

    def _calculate_final_workflow_confidence(
        self, state: RealEstateAgentState
    ) -> float:
        """Calculate final workflow confidence based on all step confidences."""
        try:
            confidence_scores = state.get("confidence_scores", {})

            if not confidence_scores:
                return 0.5  # Default medium confidence

            # Weight different steps based on importance
            step_weights = {
                "document_processing": 0.15,
                "contract_extraction": 0.25,
                "compliance_analysis": 0.20,
                "risk_assessment": 0.20,
                "recommendations": 0.15,
                "final_validation": 0.05,
            }

            weighted_sum = 0.0
            total_weight = 0.0

            for step, confidence in confidence_scores.items():
                weight = step_weights.get(
                    step, 0.1
                )  # Default weight for unlisted steps
                weighted_sum += confidence * weight
                total_weight += weight

            final_confidence = weighted_sum / total_weight if total_weight > 0 else 0.5

            # Ensure confidence stays within bounds
            return max(0.0, min(1.0, final_confidence))

        except Exception as e:
            self._log_exception(
                e, context={"calculation_method": "final_workflow_confidence"}
            )
            return 0.5  # Default medium confidence
