"""
Recommendations Generation Node for Contract Analysis Workflow

This module contains the node responsible for generating recommendations based on analysis results.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from app.models.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class RecommendationsGenerationNode(BaseNode):
    """
    Node responsible for generating recommendations based on analysis results.

    This node handles:
    - Comprehensive recommendation generation
    - Action item prioritization
    - Risk-based recommendations
    - Compliance-driven suggestions
    - Implementation guidance
    """

    def __init__(self, workflow):
        super().__init__(workflow, "recommendations_generation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Generate recommendations based on all analysis results.

        Args:
            state: Current workflow state with all analysis data

        Returns:
            Updated state with generated recommendations
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting recommendations generation", state)

            # Gather all analysis data
            contract_terms = state.get("contract_terms", {})
            compliance_analysis = state.get("compliance_analysis", {})
            risk_assessment = state.get("risk_assessment", {})

            # Log data availability for debugging
            self._log_step_debug(
                f"Analysis data available: contract_terms={bool(contract_terms)}, "
                f"compliance_analysis={bool(compliance_analysis)}, "
                f"risk_assessment={bool(risk_assessment)}",
                state,
            )

            # Perform recommendations generation
            use_llm = self.use_llm_config.get("recommendations", True)

            if use_llm:
                try:
                    recommendations_result = (
                        await self._generate_recommendations_with_llm(
                            contract_terms, compliance_analysis, risk_assessment, state
                        )
                    )
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks:
                        recommendations_result = (
                            await self._generate_recommendations_rule_based(
                                contract_terms, compliance_analysis, risk_assessment
                            )
                        )
                    else:
                        raise llm_error
            else:
                recommendations_result = (
                    await self._generate_recommendations_rule_based(
                        contract_terms, compliance_analysis, risk_assessment
                    )
                )

            # Update state with recommendations
            state["recommendations"] = recommendations_result
            recommendations_confidence = recommendations_result.get(
                "overall_confidence", 0.5
            )
            # Defensive access for confidence_scores
            state.setdefault("confidence_scores", {})[
                "recommendations"
            ] = recommendations_confidence

            recommendations_data = {
                "recommendations_result": recommendations_result,
                "confidence_score": recommendations_confidence,
                "recommendations_count": len(
                    recommendations_result.get("recommendations", [])
                ),
                "priority_actions_count": len(
                    recommendations_result.get("priority_actions", [])
                ),
                "generation_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Recommendations generated (count: {len(recommendations_result.get('recommendations', []))}, confidence: {recommendations_confidence:.2f})",
                state,
                {
                    "priority_actions": len(
                        recommendations_result.get("priority_actions", [])
                    )
                },
            )

            return self.update_state_step(
                state, "recommendations_generated", data=recommendations_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Recommendations generation failed: {str(e)}",
                {"use_llm": use_llm},
            )

    async def _generate_recommendations_with_llm(
        self,
        contract_terms: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        state: RealEstateAgentState,
    ) -> Dict[str, Any]:
        """Generate recommendations using LLM analysis."""
        try:
            from app.core.prompts import PromptContext, ContextType

            # Include service-required context variables to satisfy prompt manager validation
            doc_meta = self.workflow_state_safe_get(state, "document_metadata", {})
            context = PromptContext(
                context_type=ContextType.GENERATION,
                variables={
                    # Fix variable name mapping and provide defaults for null values
                    "contract_terms": contract_terms or {},
                    "compliance_check": compliance_analysis
                    or {},  # Template expects 'compliance_check'
                    "risk_assessment": risk_assessment or {},
                    "recommendation_categories": [
                        "immediate_actions",
                        "due_diligence",
                        "risk_mitigation",
                        "compliance_steps",
                        "professional_advice",
                    ],
                    "priority_levels": ["high", "medium", "low"],
                    # Service mapping context requirements (best-effort)
                    "extracted_text": (doc_meta.get("full_text", "") or ""),
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "user_type": state.get("user_type", "general"),
                    # Template expects 'user_experience', not 'user_experience_level'
                    "user_experience": state.get(
                        "user_experience_level", "intermediate"
                    ),
                },
            )

            # Use composition for recommendations generation
            composition_result = await self.prompt_manager.render_composed(
                composition_name="recommendations_only",
                context=context,
                output_parser=self.structured_parsers.get("recommendations"),
            )
            rendered_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True, system_prompt=system_prompt
            )

            # Parse structured response if we got one
            if response:
                if self.structured_parsers.get("recommendations"):
                    parsing_result = self.structured_parsers["recommendations"].parse(
                        response
                    )
                    if parsing_result.success and parsing_result.parsed_data:
                        return parsing_result.parsed_data

                # Fallback to JSON parsing
                recommendations_result = self._safe_json_parse(response)
                if recommendations_result:
                    return recommendations_result

            # Fallback to rule-based generation if no response or parsing fails
            return await self._generate_recommendations_rule_based(
                contract_terms, compliance_analysis, risk_assessment
            )

        except Exception as e:
            self._log_exception(e, context={"generation_method": "llm"})
            if self.enable_fallbacks:
                return await self._generate_recommendations_rule_based(
                    contract_terms, compliance_analysis, risk_assessment
                )
            raise

    async def _generate_recommendations_rule_based(
        self,
        contract_terms: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate recommendations using rule-based logic."""
        try:
            recommendations = []
            priority_actions = []

            # Risk-based recommendations
            if risk_assessment:
                risk_level = risk_assessment.get("overall_risk_level", "medium")
                risk_factors = risk_assessment.get("risk_factors", [])

                if risk_level == "high":
                    priority_actions.append(
                        {
                            "action": "Immediate professional review required",
                            "category": "professional_advice",
                            "priority": "high",
                            "rationale": "High risk level identified in contract analysis",
                        }
                    )

                for risk_factor in risk_factors[:3]:  # Top 3 risks
                    recommendations.append(
                        {
                            "type": "risk_mitigation",
                            "description": f"Address {risk_factor.get('description', 'identified risk')}",
                            "priority": (
                                "high"
                                if risk_factor.get("risk_score", 0) > 0.5
                                else "medium"
                            ),
                            "category": risk_factor.get("category", "general"),
                        }
                    )

            # Compliance-based recommendations
            if compliance_analysis:
                compliance_score = compliance_analysis.get("compliance_score", 1.0)

                if compliance_score < 0.8:
                    priority_actions.append(
                        {
                            "action": "Review compliance issues with legal counsel",
                            "category": "legal_review",
                            "priority": "high",
                            "rationale": f"Compliance score below threshold ({compliance_score:.2f})",
                        }
                    )

                compliance_issues = compliance_analysis.get("issues", [])
                for issue in compliance_issues:
                    recommendations.append(
                        {
                            "type": "compliance",
                            "description": f"Resolve: {issue}",
                            "priority": "medium",
                            "category": "regulatory",
                        }
                    )

            # Contract terms-based recommendations
            if contract_terms:
                self._add_terms_based_recommendations(contract_terms, recommendations)

            # General recommendations
            if not recommendations:
                recommendations.extend(
                    [
                        {
                            "type": "general",
                            "description": "Consider professional legal review",
                            "priority": "medium",
                            "category": "professional_advice",
                        },
                        {
                            "type": "due_diligence",
                            "description": "Verify all contract terms and conditions",
                            "priority": "medium",
                            "category": "verification",
                        },
                    ]
                )

            return {
                "recommendations": recommendations,
                "priority_actions": priority_actions,
                "summary": self._generate_recommendations_summary(
                    recommendations, priority_actions
                ),
                "overall_confidence": 0.8,
                "generation_method": "rule_based",
                "recommendation_count": len(recommendations),
                "priority_action_count": len(priority_actions),
            }

        except Exception as e:
            self._log_exception(e, context={"generation_method": "rule_based"})
            # Return minimal recommendations
            return {
                "recommendations": [
                    {
                        "type": "general",
                        "description": "Professional review recommended due to analysis limitations",
                        "priority": "high",
                        "category": "professional_advice",
                    }
                ],
                "priority_actions": [],
                "summary": "Manual review required",
                "overall_confidence": 0.3,
                "generation_method": "error_fallback",
                "error": str(e),
            }

    def _add_terms_based_recommendations(
        self, contract_terms: Dict[str, Any], recommendations: List[Dict[str, Any]]
    ) -> None:
        """Add recommendations based on contract terms analysis."""
        # Check for missing critical terms
        critical_terms = ["purchase_price", "settlement_date", "property_address"]
        missing_terms = [
            term for term in critical_terms if not contract_terms.get(term)
        ]

        for term in missing_terms:
            recommendations.append(
                {
                    "type": "completeness",
                    "description": f"Verify and complete {term.replace('_', ' ')} information",
                    "priority": "high",
                    "category": "data_completeness",
                }
            )

        # Check settlement date
        settlement_date = contract_terms.get("settlement_date")
        if settlement_date and "30" in str(settlement_date):
            recommendations.append(
                {
                    "type": "timeline",
                    "description": "Review tight settlement timeline - ensure adequate preparation time",
                    "priority": "medium",
                    "category": "timeline_management",
                }
            )

        # Check special conditions
        special_conditions = contract_terms.get("special_conditions", [])
        if len(special_conditions) > 3:
            recommendations.append(
                {
                    "type": "complexity",
                    "description": "Multiple special conditions identified - detailed review recommended",
                    "priority": "medium",
                    "category": "contract_complexity",
                }
            )

    def _generate_recommendations_summary(
        self,
        recommendations: List[Dict[str, Any]],
        priority_actions: List[Dict[str, Any]],
    ) -> str:
        """Generate a summary of recommendations."""
        high_priority_count = len(
            [r for r in recommendations if r.get("priority") == "high"]
        )
        total_recommendations = len(recommendations)
        priority_actions_count = len(priority_actions)

        if priority_actions_count > 0:
            summary = f"{priority_actions_count} immediate action(s) required. "
        else:
            summary = ""

        if high_priority_count > 0:
            summary += (
                f"{high_priority_count} high-priority recommendation(s) identified. "
            )

        summary += f"Total of {total_recommendations} recommendation(s) generated for contract review."

        return summary
