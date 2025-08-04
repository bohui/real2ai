"""
Advanced Contract Analysis Service for Real2.AI
AI-powered contract analysis with specialized Australian real estate focus
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import re

from google import genai
from google.genai.types import HarmCategory, HarmBlockThreshold

from app.core.config import get_settings
from app.models.contract_state import AustralianState, ContractType

logger = logging.getLogger(__name__)


class AnalysisComplexity(Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class ContractSection(Enum):
    PARTIES = "parties"
    PROPERTY_DETAILS = "property_details"
    FINANCIAL_TERMS = "financial_terms"
    SETTLEMENT_TERMS = "settlement_terms"
    CONDITIONS = "conditions"
    LEGAL_CLAUSES = "legal_clauses"
    SPECIAL_CONDITIONS = "special_conditions"


@dataclass
class ContractAnalysisConfig:
    """Configuration for contract analysis"""

    australian_state: AustralianState
    contract_type: ContractType
    analysis_depth: AnalysisComplexity
    focus_areas: List[ContractSection]
    include_risk_assessment: bool = True
    include_compliance_check: bool = True
    include_financial_analysis: bool = True
    language_preference: str = "en"


class ContractAnalysisService:
    """Advanced AI-powered contract analysis service"""

    def __init__(self):
        self.settings = get_settings()

        # Initialize Gemini for contract analysis
        if hasattr(self.settings, "gemini_api_key") and self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-pro",
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
            )
        else:
            logger.warning(
                "Gemini API key not configured - Contract Analysis will be limited"
            )
            self.model = None

        # Australian state-specific regulations
        self.state_regulations = {
            AustralianState.NSW: {
                "cooling_off_period_days": 5,
                "stamp_duty_threshold": 25000,
                "first_home_buyer_threshold": 800000,
                "foreign_buyer_surcharge": 0.08,
                "mandatory_searches": [
                    "title_search",
                    "planning_certificate",
                    "building_certificate",
                ],
            },
            AustralianState.VIC: {
                "cooling_off_period_days": 3,
                "stamp_duty_threshold": 25000,
                "first_home_buyer_threshold": 750000,
                "foreign_buyer_surcharge": 0.075,
                "mandatory_searches": [
                    "title_search",
                    "planning_certificate",
                    "building_permit_search",
                ],
            },
            AustralianState.QLD: {
                "cooling_off_period_days": 5,
                "stamp_duty_threshold": 20000,
                "first_home_buyer_threshold": 550000,
                "foreign_buyer_surcharge": 0.075,
                "mandatory_searches": [
                    "title_search",
                    "planning_certificate",
                    "building_certificate",
                ],
            },
            # Add other states as needed
        }

        # Contract analysis patterns
        self.analysis_patterns = {
            "purchase_price": r"(?:purchase\s+price|sale\s+price|price).*?[\$\s]*([0-9,]+)(?:\.00)?",
            "deposit": r"(?:deposit).*?[\$\s]*([0-9,]+)(?:\.00)?",
            "settlement_date": r"(?:settlement|completion).*?(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:days?|weeks?|months?))",
            "cooling_off": r"(?:cooling[-\s]off|rescission).*?(\d+)\s*(?:business\s+)?days?",
            "finance_clause": r"(?:subject\s+to|conditional\s+on).*?(?:finance|loan|mortgage)",
            "building_inspection": r"(?:subject\s+to|conditional\s+on).*?(?:building|structural)\s+(?:inspection|report)",
            "pest_inspection": r"(?:subject\s+to|conditional\s+on).*?(?:pest|termite)\s+(?:inspection|report)",
        }

        # Risk assessment criteria
        self.risk_factors = {
            "high_risk": [
                "no_cooling_off_period",
                "unconditional_contract",
                "price_above_market_value",
                "complex_special_conditions",
                "disputed_boundaries",
                "heritage_restrictions",
            ],
            "medium_risk": [
                "short_settlement_period",
                "finance_pre_approval_required",
                "strata_building",
                "leasehold_property",
                "rural_property",
            ],
            "low_risk": [
                "standard_cooling_off",
                "building_inspection_included",
                "pest_inspection_included",
                "clear_title",
                "established_property",
            ],
        }

    async def analyze_contract_comprehensive(
        self,
        extracted_text: str,
        config: ContractAnalysisConfig,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive contract analysis with AI enhancement"""

        if not self.model:
            return await self._fallback_analysis(extracted_text, config)

        start_time = time.time()

        try:
            # Step 1: Extract structured data
            logger.info("Starting structured data extraction...")
            structured_data = await self._extract_structured_data(
                extracted_text, config
            )

            # Step 2: Perform risk assessment
            logger.info("Performing risk assessment...")
            risk_assessment = await self._perform_risk_assessment(
                extracted_text, structured_data, config
            )

            # Step 3: Check compliance
            logger.info("Checking Australian compliance...")
            compliance_analysis = self._check_australian_compliance(
                structured_data, config.australian_state
            )

            # Step 4: Financial analysis
            financial_analysis = {}
            if config.include_financial_analysis:
                logger.info("Performing financial analysis...")
                financial_analysis = await self._perform_financial_analysis(
                    structured_data, config, user_preferences
                )

            # Step 5: Generate recommendations
            logger.info("Generating recommendations...")
            recommendations = await self._generate_ai_recommendations(
                structured_data, risk_assessment, compliance_analysis, config
            )

            # Step 6: Quality assessment
            analysis_quality = self._assess_analysis_quality(
                extracted_text, structured_data, risk_assessment
            )

            processing_time = time.time() - start_time

            return {
                "analysis_id": f"analysis_{int(time.time() * 1000)}",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "processing_time_seconds": processing_time,
                "config": config.__dict__,
                "structured_data": structured_data,
                "risk_assessment": risk_assessment,
                "compliance_analysis": compliance_analysis,
                "financial_analysis": financial_analysis,
                "recommendations": recommendations,
                "analysis_quality": analysis_quality,
                "ai_confidence": self._calculate_overall_confidence(
                    structured_data, risk_assessment, analysis_quality
                ),
                "next_steps": self._generate_next_steps(
                    recommendations, risk_assessment
                ),
            }

        except Exception as e:
            logger.error(f"Contract analysis failed: {str(e)}")
            return {
                "analysis_id": f"failed_{int(time.time() * 1000)}",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "fallback_analysis": await self._fallback_analysis(
                    extracted_text, config
                ),
            }

    async def _extract_structured_data(
        self, text: str, config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Extract structured data using AI-powered analysis"""

        prompt = self._create_extraction_prompt(text, config)

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(prompt)
            )

            # Parse the AI response
            ai_extracted = self._parse_ai_extraction_response(response.text)

            # Enhance with pattern-based extraction
            pattern_extracted = self._extract_with_patterns(text)

            # Combine and validate results
            combined_data = self._combine_extraction_results(
                ai_extracted, pattern_extracted
            )

            return combined_data

        except Exception as e:
            logger.error(f"AI extraction failed, falling back to patterns: {str(e)}")
            return self._extract_with_patterns(text)

    async def _perform_risk_assessment(
        self, text: str, structured_data: Dict[str, Any], config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Perform comprehensive risk assessment"""

        # AI-powered risk analysis
        risk_prompt = self._create_risk_assessment_prompt(text, structured_data, config)

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(risk_prompt)
            )

            ai_risks = self._parse_risk_assessment_response(response.text)

        except Exception as e:
            logger.error(f"AI risk assessment failed: {str(e)}")
            ai_risks = {"ai_analysis_failed": True}

        # Rule-based risk assessment
        rule_based_risks = self._assess_risks_rule_based(structured_data, config)

        # Combine risk assessments
        combined_risks = {
            "overall_risk_score": max(
                ai_risks.get("overall_risk_score", 5.0),
                rule_based_risks.get("overall_risk_score", 5.0),
            ),
            "ai_identified_risks": ai_risks.get("risk_factors", []),
            "rule_based_risks": rule_based_risks.get("risk_factors", []),
            "risk_categories": {
                "legal": ai_risks.get("legal_risks", [])
                + rule_based_risks.get("legal_risks", []),
                "financial": ai_risks.get("financial_risks", [])
                + rule_based_risks.get("financial_risks", []),
                "practical": ai_risks.get("practical_risks", [])
                + rule_based_risks.get("practical_risks", []),
            },
            "mitigation_strategies": ai_risks.get("mitigation_strategies", []),
        }

        return combined_risks

    def _check_australian_compliance(
        self, structured_data: Dict[str, Any], state: AustralianState
    ) -> Dict[str, Any]:
        """Check compliance with Australian real estate laws"""

        state_regs = self.state_regulations.get(state, {})
        compliance_issues = []
        warnings = []

        # Check cooling-off period
        cooling_off_days = structured_data.get("cooling_off_period", 0)
        required_cooling_off = state_regs.get("cooling_off_period_days", 5)

        if cooling_off_days < required_cooling_off:
            compliance_issues.append(
                f"Cooling-off period ({cooling_off_days} days) is less than required "
                f"{required_cooling_off} days for {state.value}"
            )

        # Check mandatory searches
        mandatory_searches = state_regs.get("mandatory_searches", [])
        contract_searches = structured_data.get("required_searches", [])

        missing_searches = [s for s in mandatory_searches if s not in contract_searches]
        if missing_searches:
            warnings.extend(
                [
                    f"Consider including {search.replace('_', ' ')}"
                    for search in missing_searches
                ]
            )

        # Check stamp duty implications
        purchase_price = structured_data.get("purchase_price", 0)
        stamp_duty_threshold = state_regs.get("stamp_duty_threshold", 25000)

        if purchase_price > stamp_duty_threshold:
            stamp_duty_estimate = self._calculate_stamp_duty(purchase_price, state)
            warnings.append(f"Estimated stamp duty: ${stamp_duty_estimate:,.2f}")

        return {
            "state": state.value,
            "compliant": len(compliance_issues) == 0,
            "compliance_issues": compliance_issues,
            "warnings": warnings,
            "state_specific_requirements": state_regs,
            "compliance_score": max(0, 10 - len(compliance_issues) * 2 - len(warnings)),
        }

    async def _perform_financial_analysis(
        self,
        structured_data: Dict[str, Any],
        config: ContractAnalysisConfig,
        user_preferences: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform comprehensive financial analysis"""

        purchase_price = structured_data.get("purchase_price", 0)
        deposit = structured_data.get("deposit", 0)

        if purchase_price == 0:
            return {"error": "Purchase price not identified in contract"}

        # Calculate various costs
        stamp_duty = self._calculate_stamp_duty(purchase_price, config.australian_state)
        legal_fees = purchase_price * 0.001  # Estimate 0.1%
        inspection_costs = 800  # Typical building + pest inspection
        loan_costs = (
            purchase_price * 0.005
            if user_preferences and user_preferences.get("requires_finance")
            else 0
        )

        total_upfront_costs = (
            deposit + stamp_duty + legal_fees + inspection_costs + loan_costs
        )

        # Market analysis (would integrate with property APIs in production)
        market_analysis = {
            "estimated_market_value": purchase_price,  # Placeholder
            "price_per_sqm": 0,  # Would calculate if property size available
            "market_trend": "stable",  # Would get from market data
            "comparable_sales": [],  # Would fetch recent sales
        }

        # Risk indicators
        financial_risks = []
        if deposit < purchase_price * 0.1:
            financial_risks.append("Low deposit may indicate higher financial risk")

        if purchase_price > user_preferences.get("budget_max", float("inf")):
            financial_risks.append("Purchase price exceeds stated budget")

        return {
            "purchase_price": purchase_price,
            "deposit": deposit,
            "deposit_percentage": (
                (deposit / purchase_price * 100) if purchase_price > 0 else 0
            ),
            "estimated_costs": {
                "stamp_duty": stamp_duty,
                "legal_fees": legal_fees,
                "inspection_costs": inspection_costs,
                "loan_costs": loan_costs,
                "total_upfront": total_upfront_costs,
            },
            "market_analysis": market_analysis,
            "financial_risks": financial_risks,
            "affordability_assessment": self._assess_affordability(
                total_upfront_costs, purchase_price, user_preferences
            ),
        }

    async def _generate_ai_recommendations(
        self,
        structured_data: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        config: ContractAnalysisConfig,
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations"""

        prompt = self._create_recommendations_prompt(
            structured_data, risk_assessment, compliance_analysis, config
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(prompt)
            )

            ai_recommendations = self._parse_recommendations_response(response.text)

        except Exception as e:
            logger.error(f"AI recommendations failed: {str(e)}")
            ai_recommendations = []

        # Add rule-based recommendations
        rule_recommendations = self._generate_rule_based_recommendations(
            risk_assessment, compliance_analysis
        )

        # Combine and prioritize
        all_recommendations = ai_recommendations + rule_recommendations

        # Remove duplicates and prioritize
        return self._prioritize_recommendations(all_recommendations)

    # Helper methods for various analysis tasks

    def _create_extraction_prompt(
        self, text: str, config: ContractAnalysisConfig
    ) -> str:
        """Create AI prompt for structured data extraction"""
        return f"""
        You are an expert Australian property lawyer specializing in {config.australian_state.value} real estate contracts.
        
        Extract key information from this contract text and return it as JSON:
        
        CONTRACT TEXT:
        {text[:8000]}  # Limit text length for API
        
        Extract the following information:
        {{
            "parties": {{
                "vendor": "vendor name and details",
                "purchaser": "purchaser name and details"
            }},
            "property": {{
                "address": "full property address",
                "lot_plan": "lot and plan details if available",
                "property_type": "house/unit/land/commercial"
            }},
            "financial": {{
                "purchase_price": number,
                "deposit": number,
                "deposit_percentage": number
            }},
            "settlement": {{
                "settlement_date": "date or period",
                "settlement_period": "number of days"
            }},
            "conditions": {{
                "cooling_off_period": number of business days,
                "finance_clause": true/false,
                "building_inspection": true/false,
                "pest_inspection": true/false,
                "special_conditions": ["list of special conditions"]
            }},
            "legal": {{
                "governing_law": "{config.australian_state.value}",
                "contract_type": "{config.contract_type.value}",
                "vendor_solicitor": "if mentioned",
                "purchaser_solicitor": "if mentioned"
            }}
        }}
        
        Focus on accuracy and extract only information clearly stated in the contract.
        Return ONLY the JSON, no additional text.
        """

    def _create_risk_assessment_prompt(
        self, text: str, structured_data: Dict, config: ContractAnalysisConfig
    ) -> str:
        """Create AI prompt for risk assessment"""
        return f"""
        You are an expert Australian property lawyer performing risk assessment for a {config.australian_state.value} property contract.
        
        CONTRACT DETAILS:
        {json.dumps(structured_data, indent=2)}
        
        Perform a comprehensive risk assessment and return as JSON:
        {{
            "overall_risk_score": number from 1-10 (10 being highest risk),
            "risk_factors": [
                {{
                    "risk": "description of risk",
                    "severity": "low/medium/high/critical",
                    "category": "legal/financial/practical",
                    "likelihood": "low/medium/high",
                    "impact": "description of potential impact"
                }}
            ],
            "legal_risks": ["specific legal risks"],
            "financial_risks": ["specific financial risks"], 
            "practical_risks": ["specific practical risks"],
            "mitigation_strategies": ["recommended actions to reduce risks"]
        }}
        
        Consider {config.australian_state.value}-specific regulations and common property law issues.
        Return ONLY the JSON, no additional text.
        """

    def _create_recommendations_prompt(
        self,
        structured_data: Dict,
        risk_assessment: Dict,
        compliance_analysis: Dict,
        config: ContractAnalysisConfig,
    ) -> str:
        """Create AI prompt for generating recommendations"""
        return f"""
        You are an expert Australian property advisor providing actionable recommendations.
        
        ANALYSIS SUMMARY:
        Contract Data: {json.dumps(structured_data, indent=2)[:2000]}
        Risk Assessment: {json.dumps(risk_assessment, indent=2)[:2000]}
        Compliance Status: {json.dumps(compliance_analysis, indent=2)[:1000]}
        State: {config.australian_state.value}
        
        Provide specific, actionable recommendations as JSON:
        {{
            "recommendations": [
                {{
                    "priority": "critical/high/medium/low",
                    "category": "legal/financial/practical",
                    "title": "Brief recommendation title",
                    "description": "Detailed recommendation",
                    "action_required": true/false,
                    "timeline": "immediate/before_settlement/after_settlement",
                    "estimated_cost": number or null,
                    "australian_context": "state-specific context"
                }}
            ]
        }}
        
        Focus on practical, actionable advice specific to {config.australian_state.value} property law.
        Return ONLY the JSON, no additional text.
        """

    # Utility methods for parsing, calculations, and analysis

    def _parse_ai_extraction_response(self, response: str) -> Dict[str, Any]:
        """Parse AI extraction response"""
        try:
            # Clean up response and extract JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse AI extraction response: {str(e)}")

        return {}

    def _extract_with_patterns(self, text: str) -> Dict[str, Any]:
        """Extract data using regex patterns"""
        extracted = {}

        for field, pattern in self.analysis_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                if field in ["purchase_price", "deposit"]:
                    # Extract numeric value
                    numeric_str = match.group(1).replace(",", "")
                    try:
                        extracted[field] = float(numeric_str)
                    except ValueError:
                        pass
                elif field == "cooling_off":
                    try:
                        extracted["cooling_off_period"] = int(match.group(1))
                    except ValueError:
                        pass
                else:
                    extracted[field] = (
                        match.group(1) if match.group(1) else match.group(0)
                    )

        return extracted

    def _combine_extraction_results(
        self, ai_data: Dict, pattern_data: Dict
    ) -> Dict[str, Any]:
        """Combine AI and pattern-based extraction results"""
        combined = {}

        # Start with AI data as it's typically more comprehensive
        if ai_data:
            combined.update(ai_data)

        # Fill in missing fields with pattern data
        for key, value in pattern_data.items():
            if key not in combined or not combined[key]:
                combined[key] = value

        return combined

    def _calculate_stamp_duty(
        self, purchase_price: float, state: AustralianState
    ) -> float:
        """Calculate stamp duty (simplified calculation)"""
        # This is a simplified calculation - production would use exact state formulas
        if state == AustralianState.NSW:
            if purchase_price <= 25000:
                return purchase_price * 0.0125
            elif purchase_price <= 130000:
                return 1.25 * ((purchase_price - 25000) / 1000) + 312.5
            else:
                return purchase_price * 0.045  # Simplified for high values
        elif state == AustralianState.VIC:
            return purchase_price * 0.055  # Simplified VIC calculation
        else:
            return purchase_price * 0.05  # Generic calculation

    def _assess_affordability(
        self,
        upfront_costs: float,
        purchase_price: float,
        user_preferences: Optional[Dict],
    ) -> Dict[str, Any]:
        """Assess affordability based on user preferences"""
        if not user_preferences:
            return {"assessment": "insufficient_data"}

        budget = user_preferences.get("budget_max", 0)
        income = user_preferences.get("annual_income", 0)

        affordability_ratio = purchase_price / income if income > 0 else float("inf")

        return {
            "within_budget": purchase_price <= budget,
            "affordability_ratio": affordability_ratio,
            "recommendation": (
                "affordable" if affordability_ratio <= 6 else "challenging"
            ),
        }

    # Additional helper methods would be implemented here...

    async def _fallback_analysis(
        self, text: str, config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Fallback analysis when AI is not available"""
        pattern_data = self._extract_with_patterns(text)

        return {
            "method": "pattern_based_fallback",
            "extracted_data": pattern_data,
            "analysis_limited": True,
            "recommendation": "Consider professional legal review due to limited analysis capabilities",
        }

    def _assess_risks_rule_based(
        self, data: Dict, config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Rule-based risk assessment fallback"""
        risks = []
        risk_score = 0

        # Check for high-risk indicators
        if not data.get("cooling_off_period"):
            risks.append("No cooling-off period identified")
            risk_score += 3

        if not data.get("finance_clause"):
            risks.append("No finance clause protection")
            risk_score += 2

        return {"overall_risk_score": min(10, risk_score), "risk_factors": risks}

    def _parse_risk_assessment_response(self, response: str) -> Dict[str, Any]:
        """Parse AI risk assessment response"""
        return self._parse_ai_extraction_response(response)

    def _parse_recommendations_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI recommendations response"""
        parsed = self._parse_ai_extraction_response(response)
        return parsed.get("recommendations", [])

    def _generate_rule_based_recommendations(
        self, risk_assessment: Dict, compliance_analysis: Dict
    ) -> List[Dict[str, Any]]:
        """Generate rule-based recommendations"""
        recommendations = []

        if not compliance_analysis.get("compliant", True):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "legal",
                    "title": "Address compliance issues",
                    "description": "Contract has compliance issues that need attention",
                    "action_required": True,
                    "timeline": "immediate",
                }
            )

        return recommendations

    def _prioritize_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prioritize and deduplicate recommendations"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        # Remove duplicates based on title
        seen_titles = set()
        unique_recommendations = []
        for rec in recommendations:
            title = rec.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique_recommendations.append(rec)

        # Sort by priority
        return sorted(
            unique_recommendations,
            key=lambda x: priority_order.get(x.get("priority", "low"), 3),
        )

    def _assess_analysis_quality(
        self, text: str, structured_data: Dict, risk_assessment: Dict
    ) -> Dict[str, Any]:
        """Assess the quality of the analysis performed"""
        quality_score = 0.5  # Base score

        # Check completeness of extraction
        key_fields = ["purchase_price", "deposit", "settlement_date"]
        extracted_fields = sum(1 for field in key_fields if structured_data.get(field))
        completeness = extracted_fields / len(key_fields)
        quality_score += completeness * 0.3

        # Check risk assessment depth
        risk_factors = len(risk_assessment.get("risk_factors", []))
        if risk_factors >= 3:
            quality_score += 0.2

        return {
            "overall_quality_score": min(1.0, quality_score),
            "completeness_score": completeness,
            "analysis_depth": "comprehensive" if quality_score > 0.8 else "standard",
            "data_extraction_confidence": min(1.0, extracted_fields / 10),
        }

    def _calculate_overall_confidence(
        self, structured_data: Dict, risk_assessment: Dict, quality: Dict
    ) -> float:
        """Calculate overall analysis confidence"""
        return min(
            1.0,
            quality.get("overall_quality_score", 0.5) * 0.7
            + len(structured_data) / 20 * 0.3,
        )

    def _generate_next_steps(
        self, recommendations: List[Dict], risk_assessment: Dict
    ) -> List[str]:
        """Generate next steps based on analysis"""
        next_steps = []

        # Get immediate actions
        immediate_actions = [
            rec["title"]
            for rec in recommendations
            if rec.get("timeline") == "immediate" or rec.get("priority") == "critical"
        ]

        if immediate_actions:
            next_steps.extend(immediate_actions)
        else:
            next_steps.append("Review the detailed analysis and recommendations")

        # Add risk-based next steps
        risk_score = risk_assessment.get("overall_risk_score", 5)
        if risk_score >= 7:
            next_steps.append(
                "Consider seeking professional legal advice due to high risk factors"
            )

        return next_steps[:5]  # Limit to 5 next steps
