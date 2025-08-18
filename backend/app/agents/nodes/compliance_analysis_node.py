"""
Compliance Analysis Node for Contract Analysis Workflow

This module contains the node responsible for analyzing contract compliance with Australian regulations.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState, ComplianceCheck
from .base import BaseNode

logger = logging.getLogger(__name__)


class ComplianceAnalysisNode(BaseNode):
    """
    Node responsible for analyzing contract compliance with Australian regulations.

    This node handles:
    - Australian state-specific compliance checks
    - Cooling-off period validation
    - Stamp duty calculations
    - Legal requirement verification
    - Compliance scoring and reporting
    """

    def __init__(self, workflow):
        super().__init__(workflow, "compliance_analysis")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Analyze contract compliance with Australian regulations.

        Args:
            state: Current workflow state with extracted contract terms

        Returns:
            Updated state with compliance analysis results
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        # Initialize variables referenced in exception context
        use_llm = self.use_llm_config.get("compliance_analysis", True)
        try:
            self._log_step_debug("Starting compliance analysis", state)

            # Get contract terms and state information
            contract_terms = state.get("contract_terms", {})
            if not contract_terms:
                return self._handle_node_error(
                    state,
                    Exception("No contract terms available for compliance analysis"),
                    "No contract terms available for compliance analysis",
                    {"available_keys": list(state.keys())},
                )

            # Determine Australian state for compliance rules
            australian_state = self._determine_australian_state(contract_terms, state)

            # Perform compliance analysis

            if use_llm:
                try:
                    compliance_result = await self._analyze_compliance_with_llm(
                        contract_terms, australian_state
                    )
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks:
                        compliance_result = await self._analyze_compliance_rule_based(
                            contract_terms, australian_state
                        )
                    else:
                        raise llm_error
            else:
                compliance_result = await self._analyze_compliance_rule_based(
                    contract_terms, australian_state
                )

            # Update state with compliance results
            state["compliance_analysis"] = compliance_result
            compliance_confidence = compliance_result.get("overall_confidence", 0.5)
            state["confidence_scores"]["compliance_analysis"] = compliance_confidence

            compliance_data = {
                "compliance_result": compliance_result,
                "australian_state": australian_state,
                "confidence_score": compliance_confidence,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Compliance analysis completed (confidence: {compliance_confidence:.2f})",
                state,
                {
                    "australian_state": australian_state,
                    "compliance_checks": len(compliance_result.get("checks", [])),
                },
            )

            return self.update_state_step(
                state, "compliance_analysis_completed", data=compliance_data
            )

        except Exception as e:
            return self._handle_node_error(
                state, e, f"Compliance analysis failed: {str(e)}", {"use_llm": use_llm}
            )

    def _determine_australian_state(
        self, contract_terms: Dict[str, Any], state: RealEstateAgentState
    ) -> str:
        """Determine Australian state from contract terms or user input."""
        # Check contract terms for state information
        property_address = contract_terms.get("property_address", "")
        if isinstance(property_address, str):
            # Simple state detection from address
            state_mappings = {
                "NSW": ["nsw", "new south wales", "sydney"],
                "VIC": ["vic", "victoria", "melbourne"],
                "QLD": ["qld", "queensland", "brisbane"],
                "SA": ["sa", "south australia", "adelaide"],
                "WA": ["wa", "western australia", "perth"],
                "TAS": ["tas", "tasmania", "hobart"],
                "NT": ["nt", "northern territory", "darwin"],
                "ACT": ["act", "australian capital territory", "canberra"],
            }

            address_lower = property_address.lower()
            for state_code, keywords in state_mappings.items():
                if any(keyword in address_lower for keyword in keywords):
                    return state_code

        # Check state metadata
        document_metadata = state.get("document_metadata", {})
        detected_state = document_metadata.get("australian_state")
        if detected_state:
            return detected_state

        # Default to NSW if unable to determine
        return "NSW"

    async def _analyze_compliance_with_llm(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Analyze compliance using LLM with template system."""
        try:
            from app.core.prompts import PromptContext, ContextType

            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "extracted_text": "",  # Required by service mapping
                    "australian_state": australian_state,
                    "contract_terms": contract_terms,
                    "contract_type": "property_contract",
                    "user_type": "general",
                    "user_experience_level": "intermediate",
                    "analysis_type": "compliance_check",
                    "user_experience": "intermediate",  # For template compatibility
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Get state-aware parser for compliance analysis
            state_aware_parser = self.get_state_aware_parser(
                "compliance_analysis", australian_state
            )

            # Use composition for compliance analysis
            composition_result = await self.prompt_manager.render_composed(
                composition_name="compliance_check_only",
                context=context,
                output_parser=state_aware_parser,
            )
            rendered_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")

            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True, system_prompt=system_prompt
            )

            # Parse structured response if we got one
            if llm_response:
                # Use state-aware parser for structured parsing
                state_aware_parser = self.get_state_aware_parser(
                    "compliance_analysis", australian_state
                )
                if state_aware_parser:
                    parsing_result = state_aware_parser.parse_with_retry(
                        llm_response, australian_state
                    )
                    if parsing_result.success and parsing_result.parsed_data:
                        # Convert Pydantic model to dict if needed
                        if hasattr(parsing_result.parsed_data, "dict"):
                            return parsing_result.parsed_data.dict()
                        return parsing_result.parsed_data

                # Fallback to JSON parsing
                compliance_result = self._safe_json_parse(llm_response)
                if compliance_result:
                    return compliance_result

            # Fallback to rule-based analysis if no response or parsing fails
            return await self._analyze_compliance_rule_based(
                contract_terms, australian_state
            )

        except Exception as e:
            self._log_exception(
                e, context={"analysis_method": "llm", "state": australian_state}
            )

            if not self.enable_fallbacks:
                raise

            # Try fallback prompt method
            try:
                fallback_prompt = self._create_compliance_fallback_prompt(
                    contract_terms, australian_state
                )
                llm_response = await self._generate_content_with_fallback(
                    fallback_prompt,
                    use_gemini_fallback=True,
                    system_prompt=system_prompt,
                )

                if llm_response:
                    compliance_result = self._safe_json_parse(llm_response)
                    if compliance_result:
                        return compliance_result

            except Exception as fallback_error:
                self._log_exception(
                    fallback_error, context={"fallback_method": "prompt"}
                )

            # Final fallback to rule-based analysis
            return await self._analyze_compliance_rule_based(
                contract_terms, australian_state
            )

    def _create_compliance_fallback_prompt(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> str:
        """Create a fallback prompt for compliance analysis."""
        return f"""
Analyze the following contract terms for compliance with {australian_state} property law:

Contract Terms: {contract_terms}

Please provide a JSON response with the following structure:
{{
    "overall_compliance": "compliant|non_compliant|partially_compliant",
    "compliance_score": 0.0-1.0,
    "checks": [
        {{
            "requirement": "requirement name",
            "status": "compliant|non_compliant|unknown",
            "details": "explanation",
            "confidence": 0.0-1.0
        }}
    ],
    "issues": ["list of compliance issues"],
    "recommendations": ["list of recommendations"],
    "overall_confidence": 0.0-1.0
}}
"""

    async def _analyze_compliance_rule_based(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Analyze compliance using rule-based methods."""
        try:
            compliance_checks = []
            compliance_confidence = 0.0
            compliance_components = 0

            # Validate cooling-off period
            try:
                from app.agents.tools.compliance import validate_cooling_off_period

                cooling_off_result = validate_cooling_off_period.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )

                compliance_checks.append(
                    {
                        "requirement": "cooling_off_period",
                        "status": (
                            "compliant"
                            if cooling_off_result.get("valid", False)
                            else "non_compliant"
                        ),
                        "details": cooling_off_result.get(
                            "details", "Cooling-off period validation"
                        ),
                        "confidence": 0.9,
                    }
                )

                compliance_confidence += 0.9
                compliance_components += 1

            except Exception as e:
                self._log_exception(e, context={"check": "cooling_off_period"})
                compliance_checks.append(
                    {
                        "requirement": "cooling_off_period",
                        "status": "unknown",
                        "details": f"Validation failed: {str(e)}",
                        "confidence": 0.3,
                    }
                )

            # Calculate stamp duty if possible
            try:
                from app.agents.tools.compliance import calculate_stamp_duty

                # Extract purchase price for stamp duty calc
                purchase_price_raw = contract_terms.get("purchase_price")
                try:
                    purchase_price_val = None
                    if isinstance(purchase_price_raw, (int, float)):
                        purchase_price_val = float(purchase_price_raw)
                    elif isinstance(purchase_price_raw, str):
                        cleaned = (
                            purchase_price_raw.replace("$", "").replace(",", "").strip()
                        )
                        purchase_price_val = float(cleaned) if cleaned else None
                except Exception:
                    purchase_price_val = None

                stamp_duty_result = {}
                if purchase_price_val is not None and australian_state:
                    stamp_duty_result = calculate_stamp_duty.invoke(
                        {
                            "purchase_price": purchase_price_val,
                            "state": australian_state,
                        }
                    )

                compliance_checks.append(
                    {
                        "requirement": "stamp_duty_calculation",
                        "status": ("compliant" if stamp_duty_result else "unknown"),
                        "details": f"Estimated stamp duty: {stamp_duty_result.get('total_duty', 'N/A')}",
                        "confidence": 0.8,
                    }
                )

                compliance_confidence += 0.8
                compliance_components += 1

            except Exception as e:
                self._log_exception(e, context={"check": "stamp_duty"})

            # Additional compliance checks
            self._check_required_fields_compliance(contract_terms, compliance_checks)
            compliance_components += 1
            compliance_confidence += 0.7

            # Calculate overall compliance score
            overall_confidence = (
                compliance_confidence / compliance_components
                if compliance_components > 0
                else 0.5
            )

            # Determine compliance status
            compliant_checks = sum(
                1 for check in compliance_checks if check["status"] == "compliant"
            )
            total_checks = len(compliance_checks)
            compliance_ratio = (
                compliant_checks / total_checks if total_checks > 0 else 0
            )

            if compliance_ratio >= 0.8:
                overall_compliance = "compliant"
            elif compliance_ratio >= 0.5:
                overall_compliance = "partially_compliant"
            else:
                overall_compliance = "non_compliant"

            return {
                "overall_compliance": overall_compliance,
                "compliance_score": compliance_ratio,
                "checks": compliance_checks,
                "issues": [
                    check["details"]
                    for check in compliance_checks
                    if check["status"] == "non_compliant"
                ],
                "recommendations": self._generate_compliance_recommendations(
                    compliance_checks, australian_state
                ),
                "overall_confidence": overall_confidence,
                "analysis_method": "rule_based",
                "state": australian_state,
            }

        except Exception as e:
            self._log_exception(e, context={"analysis_method": "rule_based"})
            # Return minimal compliance result
            return {
                "overall_compliance": "unknown",
                "compliance_score": 0.5,
                "checks": [],
                "issues": ["Compliance analysis failed"],
                "recommendations": ["Manual legal review recommended"],
                "overall_confidence": 0.3,
                "analysis_method": "error_fallback",
                "error": str(e),
            }

    def _check_required_fields_compliance(
        self, contract_terms: Dict[str, Any], compliance_checks: list
    ) -> None:
        """Check compliance of required contract fields."""
        required_fields = {
            "purchase_price": "Purchase price must be specified",
            "settlement_date": "Settlement date must be specified",
            "property_address": "Property address must be complete",
            "vendor_details": "Vendor details must be provided",
            "purchaser_details": "Purchaser details must be provided",
        }

        for field, description in required_fields.items():
            field_value = contract_terms.get(field)

            if field_value and str(field_value).strip():
                status = "compliant"
                details = f"{description} - Present"
            else:
                status = "non_compliant"
                details = f"{description} - Missing or incomplete"

            compliance_checks.append(
                {
                    "requirement": field.replace("_", " ").title(),
                    "status": status,
                    "details": details,
                    "confidence": 0.9,
                }
            )

    def _generate_compliance_recommendations(
        self, compliance_checks: list, australian_state: str
    ) -> list:
        """Generate compliance recommendations based on check results."""
        recommendations = []

        non_compliant_checks = [
            check for check in compliance_checks if check["status"] == "non_compliant"
        ]

        if non_compliant_checks:
            recommendations.append(
                f"Address {len(non_compliant_checks)} compliance issues identified"
            )

            for check in non_compliant_checks:
                if "cooling_off" in check["requirement"].lower():
                    recommendations.append(
                        f"Verify cooling-off period requirements for {australian_state}"
                    )
                elif "stamp_duty" in check["requirement"].lower():
                    recommendations.append(
                        f"Calculate accurate stamp duty for {australian_state}"
                    )
                else:
                    recommendations.append(
                        f"Review {check['requirement']} requirements"
                    )

        if not recommendations:
            recommendations.append(
                "Contract appears to meet basic compliance requirements"
            )
            recommendations.append(
                "Consider professional legal review for complete compliance verification"
            )

        return recommendations
