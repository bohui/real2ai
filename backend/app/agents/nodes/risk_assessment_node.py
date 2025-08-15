"""
Risk Assessment Node for Contract Analysis Workflow

This module contains the node responsible for assessing risks in contract terms and conditions.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from app.models.contract_state import RealEstateAgentState, RiskFactor
from .base import BaseNode

logger = logging.getLogger(__name__)


class RiskAssessmentNode(BaseNode):
    """
    Node responsible for assessing risks in contract terms and conditions.

    This node handles:
    - Comprehensive risk analysis of contract terms
    - Risk categorization and scoring
    - Financial and legal risk identification
    - Risk mitigation suggestions
    - Confidence scoring for risk assessments
    """

    def __init__(self, workflow):
        super().__init__(workflow, "risk_assessment")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Assess contract risks and generate risk analysis.

        Args:
            state: Current workflow state with contract terms and compliance data

        Returns:
            Updated state with risk assessment results
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting risk assessment", state)

            # Get required data
            contract_terms = state.get("contract_terms", {})
            compliance_analysis = state.get("compliance_analysis", {})

            if not contract_terms:
                return self._handle_node_error(
                    state,
                    Exception("No contract terms available for risk assessment"),
                    "No contract terms available for risk assessment",
                    {"available_keys": list(state.keys())},
                )

            # Perform risk assessment
            use_llm = self.use_llm_config.get("risk_assessment", True)

            if use_llm:
                try:
                    risk_result = await self._assess_risks_with_llm(
                        contract_terms, compliance_analysis, state
                    )
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks:
                        risk_result = await self._assess_risks_rule_based(
                            contract_terms, compliance_analysis
                        )
                    else:
                        raise llm_error
            else:
                risk_result = await self._assess_risks_rule_based(
                    contract_terms, compliance_analysis
                )

            # Update state with risk assessment
            state["risk_assessment"] = risk_result
            risk_confidence = risk_result.get("overall_confidence", 0.5)
            state["confidence_scores"]["risk_assessment"] = risk_confidence

            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(risk_result)
            state["overall_risk_score"] = overall_risk_score

            risk_data = {
                "risk_result": risk_result,
                "overall_risk_score": overall_risk_score,
                "confidence_score": risk_confidence,
                "risk_factors_count": len(risk_result.get("risk_factors", [])),
                "assessment_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Risk assessment completed (overall score: {overall_risk_score:.2f}, confidence: {risk_confidence:.2f})",
                state,
                {"risk_factors": len(risk_result.get("risk_factors", []))},
            )

            return self.update_state_step(
                state, "risk_assessment_completed", data=risk_data
            )

        except Exception as e:
            return self._handle_node_error(
                state, e, f"Risk assessment failed: {str(e)}", {"use_llm": use_llm}
            )

    async def _assess_risks_with_llm(
        self,
        contract_terms: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        state: Optional[RealEstateAgentState] = None,
    ) -> Dict[str, Any]:
        """Assess risks using LLM analysis."""
        try:
            from app.core.prompts import PromptContext, ContextType

            # Safely derive required context variables for service validation and templates
            document_metadata: Dict[str, Any] = {}
            if isinstance(state, dict):
                document_metadata = state.get("document_metadata", {}) or {}

            extracted_text_value = (
                (
                    document_metadata.get("full_text")
                    or (state or {}).get("extracted_text")
                    or ""
                )
                if isinstance(state, dict)
                else ""
            )

            australian_state_value = (
                state.get("australian_state") if isinstance(state, dict) else None
            ) or "NSW"
            contract_type_value = (
                state.get("contract_type") if isinstance(state, dict) else None
            ) or "purchase_agreement"
            user_type_value = (
                state.get("user_type") if isinstance(state, dict) else None
            ) or "general"
            user_experience_level_value = (
                (
                    state.get("user_experience_level")
                    if isinstance(state, dict)
                    else None
                )
                or (state.get("user_experience") if isinstance(state, dict) else None)
                or "intermediate"
            )

            # Build prompt context including both service mapping requirements and template requirements
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    # Existing analysis inputs
                    "contract_terms": contract_terms,
                    "compliance_analysis": compliance_analysis,
                    "analysis_type": "risk_assessment",
                    "risk_categories": [
                        "financial",
                        "legal",
                        "operational",
                        "market",
                        "regulatory",
                    ],
                    "assessment_criteria": [
                        "probability",
                        "impact",
                        "mitigation",
                        "confidence",
                    ],
                    # Service 'contract_analysis_workflow' required variables
                    "extracted_text": (extracted_text_value or ""),
                    "australian_state": australian_state_value,
                    "contract_type": contract_type_value,
                    "user_type": user_type_value,
                    "user_experience_level": user_experience_level_value,
                    # Template 'analysis/risk_analysis_structured' required variables
                    "document_content": (extracted_text_value or ""),
                    # Use a sensible default focus; template supports specific branches
                    "analysis_focus": "compliance",
                    # Optional template variable for nicer rendering
                    "user_experience": user_experience_level_value,
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="analysis/risk_analysis_structured",
                context=context,
                service_name="contract_analysis_workflow",
            )

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            # Parse structured response if we got one
            if response:
                if self.structured_parsers.get("risk_analysis"):
                    parsing_result = self.structured_parsers["risk_analysis"].parse(
                        response
                    )
                    if parsing_result.success and parsing_result.data:
                        return parsing_result.data

                # Fallback to JSON parsing
                risk_result = self._safe_json_parse(response)
                if risk_result:
                    return risk_result

            # Fallback to rule-based assessment if no response or parsing fails
            return await self._assess_risks_rule_based(
                contract_terms, compliance_analysis
            )

        except Exception as e:
            self._log_exception(e, context={"assessment_method": "llm"})
            if self.enable_fallbacks:
                return await self._assess_risks_rule_based(
                    contract_terms, compliance_analysis, state
                )
            raise

    async def _assess_risks_rule_based(
        self,
        contract_terms: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        state: Optional[RealEstateAgentState] = None,
    ) -> Dict[str, Any]:
        """Assess risks using rule-based analysis."""
        try:
            from app.agents.tools.analysis import comprehensive_risk_scoring_system

            # Use comprehensive risk scoring tool
            # Determine state and optional user profile from workflow state
            # Resolve state from provided workflow state dict if available
            australian_state = None
            if isinstance(state, dict):
                australian_state = state.get("australian_state")
            user_profile = {
                "experience": (
                    state.get("user_experience_level")
                    if isinstance(state, dict)
                    else None
                ),
                "user_type": (
                    state.get("user_type") if isinstance(state, dict) else None
                ),
            }

            risk_scoring_result = comprehensive_risk_scoring_system.invoke(
                {
                    "contract_terms": contract_terms,
                    "state": australian_state or "",
                    "user_profile": user_profile,
                }
            )

            # Enhance with additional risk analysis
            risk_factors = self._identify_rule_based_risks(
                contract_terms, compliance_analysis
            )

            # Calculate risk scores
            risk_categories = self._categorize_risks(risk_factors)
            overall_risk_level = self._determine_risk_level(risk_factors)

            enhanced_result = {
                "risk_factors": risk_factors,
                "risk_categories": risk_categories,
                "overall_risk_level": overall_risk_level,
                "risk_score": risk_scoring_result.get("overall_risk_score", 0.5),
                "mitigation_strategies": self._generate_mitigation_strategies(
                    risk_factors
                ),
                "priority_risks": self._identify_priority_risks(risk_factors),
                "overall_confidence": 0.8,  # High confidence in rule-based assessment
                "assessment_method": "rule_based",
                "detailed_analysis": risk_scoring_result,
            }

            return enhanced_result

        except Exception as e:
            self._log_exception(e, context={"assessment_method": "rule_based"})
            # Return minimal risk assessment
            return {
                "risk_factors": [],
                "risk_categories": {"financial": [], "legal": [], "operational": []},
                "overall_risk_level": "medium",
                "risk_score": 0.5,
                "mitigation_strategies": ["Manual risk review recommended"],
                "priority_risks": [],
                "overall_confidence": 0.3,
                "assessment_method": "error_fallback",
                "error": str(e),
            }

    def _identify_rule_based_risks(
        self, contract_terms: Dict[str, Any], compliance_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify risks using rule-based logic."""
        risk_factors = []

        # Financial risks
        purchase_price = contract_terms.get("purchase_price")
        if purchase_price:
            try:
                price_value = float(
                    str(purchase_price).replace("$", "").replace(",", "")
                )
                if price_value > 1000000:
                    risk_factors.append(
                        {
                            "category": "financial",
                            "type": "high_value_transaction",
                            "description": f"High-value transaction (${price_value:,.0f})",
                            "probability": 0.3,
                            "impact": 0.8,
                            "risk_score": 0.24,
                            "confidence": 0.9,
                        }
                    )
            except (ValueError, TypeError):
                risk_factors.append(
                    {
                        "category": "financial",
                        "type": "price_validation_error",
                        "description": "Unable to validate purchase price format",
                        "probability": 0.6,
                        "impact": 0.4,
                        "risk_score": 0.24,
                        "confidence": 0.8,
                    }
                )

        # Compliance-based risks
        if compliance_analysis:
            compliance_score = compliance_analysis.get("compliance_score", 1.0)
            if compliance_score < 0.8:
                risk_factors.append(
                    {
                        "category": "legal",
                        "type": "compliance_issues",
                        "description": f"Compliance concerns identified (score: {compliance_score:.2f})",
                        "probability": 0.7,
                        "impact": 0.8,
                        "risk_score": 0.56,
                        "confidence": 0.9,
                    }
                )

        return risk_factors

    def _categorize_risks(
        self, risk_factors: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize risks by type."""
        categories = {
            "financial": [],
            "legal": [],
            "operational": [],
            "regulatory": [],
            "market": [],
        }

        for risk in risk_factors:
            category = risk.get("category", "operational")
            if category in categories:
                categories[category].append(risk)
            else:
                categories["operational"].append(risk)

        return categories

    def _determine_risk_level(self, risk_factors: List[Dict[str, Any]]) -> str:
        """Determine overall risk level."""
        if not risk_factors:
            return "low"

        # Calculate average risk score
        total_risk_score = sum(risk.get("risk_score", 0.5) for risk in risk_factors)
        average_risk_score = total_risk_score / len(risk_factors)

        if average_risk_score >= 0.7:
            return "high"
        elif average_risk_score >= 0.4:
            return "medium"
        else:
            return "low"

    def _generate_mitigation_strategies(
        self, risk_factors: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate mitigation strategies for identified risks."""
        strategies = []
        risk_types = set(risk.get("type", "") for risk in risk_factors)

        for risk_type in risk_types:
            if "financial" in risk_type or "high_value" in risk_type:
                strategies.append("Consider obtaining professional financial advice")
                strategies.append("Ensure adequate financing is secured")

            if "compliance" in risk_type or "regulatory" in risk_type:
                strategies.append("Obtain legal review of compliance requirements")

        if not strategies:
            strategies.append("Regular monitoring and professional review recommended")

        return list(set(strategies))  # Remove duplicates

    def _identify_priority_risks(
        self, risk_factors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify the highest priority risks."""
        # Sort by risk score (probability * impact)
        sorted_risks = sorted(
            risk_factors, key=lambda x: x.get("risk_score", 0), reverse=True
        )

        # Return top 3 highest risks
        return sorted_risks[:3]

    def _calculate_overall_risk_score(self, risk_result: Dict[str, Any]) -> float:
        """Calculate overall risk score from assessment results."""
        try:
            # Use explicit risk score if available
            if "risk_score" in risk_result:
                return risk_result["risk_score"]

            # Calculate from risk factors
            risk_factors = risk_result.get("risk_factors", [])
            if not risk_factors:
                return 0.3  # Default low-medium risk

            # Weighted average of risk scores
            total_score = sum(risk.get("risk_score", 0.5) for risk in risk_factors)
            return min(1.0, total_score / len(risk_factors))

        except Exception as e:
            self._log_exception(e, context={"calculation_method": "overall_risk_score"})
            return 0.5  # Default medium risk
