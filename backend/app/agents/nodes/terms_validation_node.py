"""
Terms Validation Node for Contract Analysis Workflow

This module contains the node responsible for validating the completeness and accuracy of extracted contract terms.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState, ContractTerms
from .base import BaseNode

logger = logging.getLogger(__name__)


class TermsValidationNode(BaseNode):
    """
    Node responsible for validating the completeness and accuracy of extracted contract terms.

    This node performs:
    - Terms completeness validation
    - Required fields verification
    - Data consistency checks
    - Confidence scoring for validation results
    """

    def __init__(self, workflow):
        super().__init__(workflow, "terms_validation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Validate completeness of extracted contract terms.

        Args:
            state: Current workflow state with extracted contract terms

        Returns:
            Updated state with validation results
        """
        if not self.enable_validation:
            return state

        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting contract terms validation", state)

            # Get contract terms
            contract_terms = state.get("contract_terms", {})
            if not contract_terms:
                return self._handle_node_error(
                    state,
                    Exception("No contract terms available for validation"),
                    "No contract terms available for validation",
                    {"state_keys": list(state.keys())},
                )

            # Perform validation
            use_llm = self.use_llm_config.get("terms_validation", True)

            if use_llm:
                try:
                    validation_result = (
                        await self._validate_terms_completeness_with_llm(contract_terms)
                    )
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks:
                        validation_result = (
                            await self._validate_terms_completeness_rule_based(
                                contract_terms
                            )
                        )
                    else:
                        raise llm_error
            else:
                validation_result = await self._validate_terms_completeness_rule_based(
                    contract_terms
                )

            # Update state with validation results
            state["terms_validation_result"] = validation_result
            validation_confidence = validation_result.get("overall_confidence", 0.5)
            state["confidence_scores"]["terms_validation"] = validation_confidence

            # Determine validation outcome
            validation_threshold = 0.6
            validation_passed = validation_confidence >= validation_threshold

            validation_data = {
                "validation_result": validation_result,
                "confidence_score": validation_confidence,
                "validation_passed": validation_passed,
                "validation_timestamp": datetime.now(UTC).isoformat(),
            }

            if validation_passed:
                self._log_step_debug(
                    f"Terms validation passed (confidence: {validation_confidence:.2f})",
                    state,
                    {"validation_result": validation_result},
                )
                return self.update_state_step(
                    state, "terms_validation_passed", data=validation_data
                )
            else:
                self._log_step_debug(
                    f"Terms validation failed (confidence: {validation_confidence:.2f})",
                    state,
                    {"validation_result": validation_result},
                )
                return self.update_state_step(
                    state,
                    "terms_validation_failed",
                    error=f"Terms validation below threshold (confidence: {validation_confidence:.2f})",
                    data=validation_data,
                )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Terms validation failed: {str(e)}",
                {"use_llm": self.use_llm_config.get("terms_validation", True)},
            )

    async def _validate_terms_completeness_with_llm(
        self, contract_terms: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate contract terms completeness using LLM analysis."""
        try:
            from app.core.prompts import PromptContext, ContextType

            # Provide required service/template context with safe defaults
            australian_state_value = "NSW"
            contract_type_value = "purchase_agreement"
            user_type_value = "general"
            user_experience_level_value = "intermediate"
            analysis_timestamp_value = datetime.now(UTC).isoformat()

            context = PromptContext(
                context_type=ContextType.VALIDATION,
                variables={
                    "contract_terms": contract_terms,
                    "validation_type": "terms_completeness",
                    "required_fields": [
                        "purchase_price",
                        "settlement_date",
                        "deposit_amount",
                        "property_address",
                        "vendor_details",
                        "purchaser_details",
                    ],
                    "validation_criteria": [
                        "field_presence",
                        "data_quality",
                        "consistency",
                        "completeness",
                    ],
                    # Service mapping required variables
                    "extracted_text": "",  # not needed for this step
                    "australian_state": australian_state_value,
                    "contract_type": contract_type_value,
                    "user_type": user_type_value,
                    "user_experience_level": user_experience_level_value,
                    # Template-required timestamp alias (some templates expect this)
                    "analysis_timestamp": analysis_timestamp_value,
                    # Some templates use 'user_experience'
                    "user_experience": user_experience_level_value,
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="validation/terms_completeness_validation",
                context=context,
                service_name="contract_analysis_workflow",
                output_parser=self.structured_parsers.get("terms_validation"),
            )

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            # Parse LLM response if we got one
            if response:
                if self.structured_parsers.get("terms_validation"):
                    parsing_result = self.structured_parsers["terms_validation"].parse(
                        response
                    )
                    if parsing_result.success and parsing_result.data:
                        return parsing_result.data

                validation_result = self._safe_json_parse(response)
                if validation_result:
                    return validation_result

            # Fallback to rule-based if no response or parsing fails
            return await self._validate_terms_completeness_rule_based(contract_terms)

        except Exception as e:
            self._log_exception(e, context={"validation_method": "llm"})
            if self.enable_fallbacks:
                return await self._validate_terms_completeness_rule_based(
                    contract_terms
                )
            raise

    async def _validate_terms_completeness_rule_based(
        self, contract_terms: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate contract terms completeness using rule-based analysis."""
        try:
            from app.agents.tools.validation import validate_contract_terms_completeness

            # Determine context inputs expected by the tool
            # No access to workflow state here; provide conservative defaults
            australian_state = "NSW"
            contract_type = "purchase_agreement"

            validation_result = validate_contract_terms_completeness.invoke(
                {
                    "contract_terms": contract_terms,
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                }
            )

            # Enhance validation result with additional analysis
            required_fields = [
                "purchase_price",
                "settlement_date",
                "deposit_amount",
                "property_address",
                "vendor_details",
                "purchaser_details",
            ]

            present_fields = [
                field for field in required_fields if contract_terms.get(field)
            ]
            missing_fields = [
                field for field in required_fields if not contract_terms.get(field)
            ]

            completeness_score = len(present_fields) / len(required_fields)

            # Map tool output to ContractTermsValidationOutput-compatible shape
            terms_validated = {name: name in present_fields for name in required_fields}
            overall_confidence = float(
                validation_result.get("confidence", completeness_score)
            )

            enhanced_result = {
                "terms_validated": terms_validated,
                "missing_mandatory_terms": validation_result.get(
                    "missing_terms", missing_fields
                ),
                "incomplete_terms": validation_result.get("incomplete_terms", []),
                "validation_confidence": overall_confidence,
                "state_specific_requirements": validation_result.get(
                    "state_requirements", {}
                ),
                "recommendations": validation_result.get("recommendations", []),
                # Keep legacy fields for internal summaries
                "completeness_score": completeness_score,
                "present_fields": present_fields,
                "missing_fields": missing_fields,
                "field_count": len(contract_terms),
                "required_field_count": len(required_fields),
                "validation_method": "rule_based",
            }

            return enhanced_result

        except Exception as e:
            self._log_exception(e, context={"validation_method": "rule_based"})
            # Return minimal validation result
            return {
                "completeness_score": 0.5,
                "present_fields": [],
                "missing_fields": ["validation_error"],
                "validation_issues": ["Validation process failed"],
                "improvement_suggestions": ["Manual review recommended"],
                "overall_confidence": 0.3,
                "validation_method": "error_fallback",
                "error": str(e),
            }
