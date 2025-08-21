#!/usr/bin/env python3
"""
Contract Analysis Workflow Integration Example

This example shows how to integrate the structured output parsing fixes
into the existing ContractAnalysisWorkflow to resolve the JSON parsing issues
identified in the troubleshooting analysis.
"""

import logging
from typing import Dict, Any, Optional, List
from app.core.prompts.parsers import create_parser, ParsingResult
from app.models.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    ContractTermsOutput,
    ComplianceAnalysisOutput,
    ContractTermsValidationOutput,
)

logger = logging.getLogger(__name__)


class EnhancedContractAnalysisWorkflow:
    """
    Example integration of structured parsing into ContractAnalysisWorkflow

    This class shows how to replace all the manual JSON parsing calls
    with the structured LangChain OutputParser system.
    """

    def __init__(self, **kwargs):
        # Initialize the existing workflow components
        super().__init__(**kwargs)

        # Initialize output parsers for structured responses
        self.risk_parser = create_parser(
            RiskAnalysisOutput, strict_mode=False, retry_on_failure=True, max_retries=2
        )

        self.recommendations_parser = create_parser(
            RecommendationsOutput,
            strict_mode=False,
            retry_on_failure=True,
            max_retries=2,
        )

        self.contract_terms_parser = create_parser(
            ContractTermsOutput, strict_mode=False, retry_on_failure=True, max_retries=2
        )

        self.compliance_parser = create_parser(
            ComplianceAnalysisOutput,
            strict_mode=False,
            retry_on_failure=True,
            max_retries=2,
        )

        self.validation_parser = create_parser(
            ContractTermsValidationOutput,
            strict_mode=False,
            retry_on_failure=True,
            max_retries=2,
        )

    async def assess_contract_risks(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced risk assessment with structured output parsing
        REPLACES: Lines 2980-3000 in original workflow
        """
        contract_terms = state.get("contract_terms", {})
        document_content = state.get("document_data", {}).get("content", "")
        australian_state = state.get("australian_state", "NSW")

        logger.info("Starting enhanced risk assessment with structured parsing")

        try:
            # Build base prompt (existing logic)
            base_prompt = await self._build_risk_assessment_prompt(
                contract_terms, document_content, australian_state
            )

            # Add format instructions using the parser
            format_instructions = self.risk_parser.get_format_instructions()

            full_prompt = f"""
{base_prompt}

{format_instructions}
"""

            # Generate LLM response
            llm_response = await self._generate_content_with_fallback(
                full_prompt, use_gemini_fallback=True
            )

            # Parse response using structured parser
            parsing_result = self.risk_parser.parse_with_retry(llm_response)

            if parsing_result.success:
                logger.info(
                    f"Risk assessment parsed successfully (confidence: {parsing_result.confidence_score:.2f})"
                )

                # Convert to expected format
                risk_data = parsing_result.parsed_data.dict()

                # Update state
                state["risk_assessment"] = risk_data
                state["confidence_scores"][
                    "risk_assessment"
                ] = parsing_result.confidence_score

                return update_state_step(state, ["assess_risks"])

            else:
                # Handle parsing failure
                logger.warning(
                    f"Risk assessment parsing failed: {parsing_result.parsing_errors + parsing_result.validation_errors}"
                )

                if self.enable_fallbacks:
                    return await self._handle_risk_assessment_fallback(
                        state, llm_response
                    )
                else:
                    raise ValueError(
                        "Risk assessment parsing failed and fallbacks disabled"
                    )

        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            if self.enable_fallbacks:
                return await self._handle_risk_assessment_fallback(state, "")
            else:
                raise

    async def generate_recommendations(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced recommendations generation with structured parsing
        REPLACES: Lines 3108-3130 in original workflow
        """
        contract_terms = state.get("contract_terms", {})
        risk_assessment = state.get("risk_assessment", {})
        compliance_check = state.get("compliance_check", {})
        australian_state = state.get("australian_state", "NSW")

        logger.info("Starting enhanced recommendations generation")

        try:
            # Build base prompt
            base_prompt = await self._build_recommendations_prompt(
                contract_terms, risk_assessment, compliance_check, australian_state
            )

            # Add format instructions
            format_instructions = self.recommendations_parser.get_format_instructions()

            full_prompt = f"""
{base_prompt}

{format_instructions}
"""

            # Generate and parse response
            llm_response = await self._generate_content_with_fallback(
                full_prompt, use_gemini_fallback=True
            )

            parsing_result = self.recommendations_parser.parse_with_retry(llm_response)

            if parsing_result.success:
                recommendations_data = parsing_result.parsed_data.dict()
                recommendations_list = recommendations_data.get("recommendations", [])

                logger.info(
                    f"Generated {len(recommendations_list)} recommendations successfully"
                )

                # Update state
                state["recommendations"] = recommendations_list
                # Fix: final_recommendations should be a list, not the entire data dict
                state["final_recommendations"] = recommendations_list
                state["confidence_scores"][
                    "recommendations"
                ] = parsing_result.confidence_score

                return update_state_step(state, ["generate_recommendations"])

            else:
                logger.warning(
                    f"Recommendations parsing failed: {parsing_result.parsing_errors + parsing_result.validation_errors}"
                )

                if self.enable_fallbacks:
                    return await self._handle_recommendations_fallback(
                        state, llm_response
                    )
                else:
                    raise ValueError(
                        "Recommendations parsing failed and fallbacks disabled"
                    )

        except Exception as e:
            logger.error(f"Recommendations generation failed: {str(e)}")
            if self.enable_fallbacks:
                return await self._handle_recommendations_fallback(state, "")
            else:
                raise

    async def extract_contract_terms(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced contract terms extraction with australian_state validation
        REPLACES: Lines 965-990 in original workflow
        """
        document_data = state.get("document_data", {})
        document_content = document_data.get("content", "")
        australian_state = state.get("australian_state", "NSW")

        if not document_content:
            logger.error("No document content available for terms extraction")
            state["error_state"] = "Missing document content"
            return state

        logger.info(
            f"Starting enhanced contract terms extraction for state: {australian_state}"
        )

        try:
            # Build base prompt with state context
            base_prompt = f"""
Analyze this Australian real estate contract for the state of {australian_state} and extract all key terms.

Document Content:
{document_content[:10000]}  # Limit for context

Extract all relevant contract terms including parties, property details, financial terms, conditions, and special clauses.
Ensure the australian_state field is set to: {australian_state}
"""

            # Add format instructions
            format_instructions = self.contract_terms_parser.get_format_instructions()

            full_prompt = f"""
{base_prompt}

{format_instructions}
"""

            # Generate and parse response
            llm_response = await self._generate_content_with_fallback(
                full_prompt, use_gemini_fallback=True
            )

            parsing_result = self.contract_terms_parser.parse_with_retry(llm_response)

            if parsing_result.success:
                terms_data = parsing_result.parsed_data.dict()

                # Ensure australian_state is correctly set
                terms_data["australian_state"] = australian_state
                terms_data["terms"]["australian_state"] = australian_state

                logger.info(
                    "Contract terms extraction successful with state validation"
                )

                # Update state
                state["contract_terms"] = terms_data["terms"]
                state["confidence_scores"][
                    "contract_terms"
                ] = parsing_result.confidence_score

                return update_state_step(state, ["extract_terms"])

            else:
                logger.warning(
                    f"Contract terms parsing failed: {parsing_result.parsing_errors + parsing_result.validation_errors}"
                )

                if self.enable_fallbacks:
                    return await self._handle_terms_extraction_fallback(
                        state, australian_state
                    )
                else:
                    raise ValueError(
                        "Terms extraction parsing failed and fallbacks disabled"
                    )

        except Exception as e:
            logger.error(f"Contract terms extraction failed: {str(e)}")
            if self.enable_fallbacks:
                return await self._handle_terms_extraction_fallback(
                    state, australian_state
                )
            else:
                raise

    async def analyze_australian_compliance(
        self, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced compliance analysis with structured parsing
        REPLACES: Lines 2785-2820 in original workflow
        """
        contract_terms = state.get("contract_terms", {})
        australian_state = state.get("australian_state", "NSW")

        logger.info(f"Starting enhanced compliance analysis for {australian_state}")

        try:
            # Build base prompt
            base_prompt = await self._build_compliance_prompt(
                contract_terms, australian_state
            )

            # Add format instructions
            format_instructions = self.compliance_parser.get_format_instructions()

            full_prompt = f"""
{base_prompt}

{format_instructions}
"""

            # Generate and parse response
            llm_response = await self._generate_content_with_fallback(
                full_prompt, use_gemini_fallback=True
            )

            parsing_result = self.compliance_parser.parse_with_retry(llm_response)

            if parsing_result.success:
                compliance_data = parsing_result.parsed_data.dict()

                # Ensure australian_state is set
                compliance_data["australian_state"] = australian_state

                logger.info("Compliance analysis successful")

                # Update state
                state["compliance_check"] = compliance_data
                state["confidence_scores"][
                    "compliance"
                ] = parsing_result.confidence_score

                return update_state_step(state, ["analyze_compliance"])

            else:
                logger.warning(
                    f"Compliance analysis parsing failed: {parsing_result.parsing_errors + parsing_result.validation_errors}"
                )

                if self.enable_fallbacks:
                    return await self._handle_compliance_fallback(
                        state, australian_state
                    )
                else:
                    raise ValueError(
                        "Compliance analysis parsing failed and fallbacks disabled"
                    )

        except Exception as e:
            logger.error(f"Compliance analysis failed: {str(e)}")
            if self.enable_fallbacks:
                return await self._handle_compliance_fallback(state, australian_state)
            else:
                raise

    async def validate_terms_completeness_step(
        self, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced terms validation with structured parsing
        REPLACES: Lines 3307-3330 in original workflow
        """
        contract_terms = state.get("contract_terms", {})
        australian_state = state.get("australian_state", "NSW")

        logger.info("Starting enhanced terms completeness validation")

        try:
            # Build base prompt
            base_prompt = await self._build_terms_validation_prompt(
                contract_terms, australian_state
            )

            # Add format instructions
            format_instructions = self.validation_parser.get_format_instructions()

            full_prompt = f"""
{base_prompt}

{format_instructions}
"""

            # Generate and parse response
            llm_response = await self._generate_content_with_fallback(
                full_prompt, use_gemini_fallback=True
            )

            parsing_result = self.validation_parser.parse_with_retry(llm_response)

            if parsing_result.success:
                validation_data = parsing_result.parsed_data.dict()

                # Ensure australian_state is set
                validation_data["australian_state"] = australian_state

                logger.info("Terms validation successful")

                # Update state
                state["terms_validation"] = validation_data
                state["confidence_scores"][
                    "terms_validation"
                ] = parsing_result.confidence_score

                return update_state_step(state, ["validate_terms"])

            else:
                logger.warning(
                    f"Terms validation parsing failed: {parsing_result.parsing_errors + parsing_result.validation_errors}"
                )

                if self.enable_fallbacks:
                    return await self._handle_validation_fallback(
                        state, australian_state
                    )
                else:
                    raise ValueError(
                        "Terms validation parsing failed and fallbacks disabled"
                    )

        except Exception as e:
            logger.error(f"Terms validation failed: {str(e)}")
            if self.enable_fallbacks:
                return await self._handle_validation_fallback(state, australian_state)
            else:
                raise

    # Fallback handlers for when structured parsing fails
    async def _handle_risk_assessment_fallback(
        self, state: Dict[str, Any], llm_response: str
    ) -> Dict[str, Any]:
        """Fallback risk assessment using rule-based approach"""
        logger.info("Using fallback risk assessment")

        # Create minimal risk assessment
        fallback_assessment = {
            "overall_risk_score": 5.0,  # Medium risk default
            "risk_factors": [
                {
                    "factor": "Analysis Incomplete",
                    "severity": "medium",
                    "description": "Unable to complete full automated risk analysis",
                    "mitigation_suggestions": ["Manual legal review recommended"],
                }
            ],
            "confidence_level": 0.3,
            "critical_issues": ["Automated analysis incomplete"],
            "state_specific_risks": [],
        }

        state["risk_assessment"] = fallback_assessment
        state["confidence_scores"]["risk_assessment"] = 0.3

        return update_state_step(state, ["assess_risks"])

    async def _handle_recommendations_fallback(
        self, state: Dict[str, Any], llm_response: str
    ) -> Dict[str, Any]:
        """Fallback recommendations generation"""
        logger.info("Using fallback recommendations generation")

        fallback_recommendations = [
            {
                "priority": "high",
                "category": "legal",
                "recommendation": "Obtain professional legal review of this contract",
                "action_required": True,
                "australian_context": "Professional legal review recommended for all property transactions",
                "timeline": "Before settlement",
            }
        ]

        state["recommendations"] = fallback_recommendations
        # Fix: final_recommendations should be a list, not a dict
        state["final_recommendations"] = fallback_recommendations
        state["confidence_scores"]["recommendations"] = 0.3

        return update_state_step(state, ["generate_recommendations"])

    async def _handle_terms_extraction_fallback(
        self, state: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Fallback terms extraction"""
        logger.info("Using fallback terms extraction")

        fallback_terms = {
            "australian_state": australian_state,
            "property_information": {"extraction_status": "failed"},
            "financial_terms": {"extraction_status": "failed"},
            "parties_information": {"extraction_status": "failed"},
            "conditions": [],
            "special_conditions": [],
            "extraction_notes": [
                "Automated extraction failed - manual review required"
            ],
        }

        state["contract_terms"] = fallback_terms
        state["confidence_scores"]["contract_terms"] = 0.2

        return update_state_step(state, ["extract_terms"])

    async def _handle_compliance_fallback(
        self, state: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Fallback compliance analysis"""
        logger.info("Using fallback compliance analysis")

        fallback_compliance = {
            "australian_state": australian_state,
            "overall_compliance": False,
            "compliance_score": 0.5,
            "compliance_issues": [
                {
                    "issue_type": "analysis_incomplete",
                    "description": "Automated compliance analysis failed",
                    "severity": "medium",
                    "legal_reference": "Manual review required",
                    "resolution_required": True,
                }
            ],
            "warnings": ["Automated compliance check incomplete"],
        }

        state["compliance_check"] = fallback_compliance
        state["confidence_scores"]["compliance"] = 0.3

        return update_state_step(state, ["analyze_compliance"])

    async def _handle_validation_fallback(
        self, state: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Fallback terms validation"""
        logger.info("Using fallback terms validation")

        fallback_validation = {
            "australian_state": australian_state,
            "terms_validated": {},
            "missing_mandatory_terms": ["Unable to validate"],
            "validation_confidence": 0.2,
            "recommendations": ["Manual validation required"],
        }

        state["terms_validation"] = fallback_validation
        state["confidence_scores"]["terms_validation"] = 0.2

        return update_state_step(state, ["validate_terms"])


# Helper functions to show integration patterns
def demonstrate_integration_pattern():
    """
    Demonstrates the pattern for integrating structured parsing
    """

    integration_example = """
    # BEFORE: Manual JSON parsing (problematic)
    try:
        risk_result = json.loads(llm_response)
        return risk_result
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {e}")
        return fallback_response
    
    # AFTER: Structured parsing with LangChain OutputParser
    parser = create_parser(RiskAnalysisOutput, strict_mode=False)
    
    # Build prompt with format instructions
    format_instructions = parser.get_format_instructions()
    full_prompt = f"{base_prompt}\\n\\n{format_instructions}"
    
    # Generate response
    llm_response = await generate_content(full_prompt)
    
    # Parse with structured parser
    result = parser.parse_with_retry(llm_response)
    
    if result.success:
        return result.parsed_data.dict()
    else:
        logger.warning(f"Parsing failed: {result.parsing_errors}")
        return create_fallback_response()
    """

    print("Integration Pattern:")
    print(integration_example)


if __name__ == "__main__":
    print("Contract Analysis Workflow Integration Example")
    print("=" * 60)
    demonstrate_integration_pattern()

    print("\n✅ Key Benefits of Structured Parsing Integration:")
    print("1. Eliminates manual JSON parsing failures")
    print("2. Provides detailed format instructions to LLM")
    print("3. Handles code block wrapped responses automatically")
    print("4. Includes retry logic with text cleaning")
    print("5. Validates against Pydantic schemas")
    print("6. Provides confidence scoring")
    print("7. Fixes australian_state validation issues")
