"""
Contract Analysis Service V2 - Refactored to use GeminiClient
AI-powered contract analysis with specialized Australian real estate focus
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum
import json
import re

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.contract_state import AustralianState, ContractType
from app.clients import get_gemini_client
from app.core.langsmith_config import langsmith_trace, langsmith_session, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

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
    """Advanced AI-powered contract analysis service using GeminiClient"""

    def __init__(self):
        self.settings = get_settings()
        self.gemini_client = None

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
                "mandatory_searches": ["title_search", "planning_certificate"],
            },
            AustralianState.QLD: {
                "cooling_off_period_days": 5,
                "stamp_duty_threshold": 10000,
                "first_home_buyer_threshold": 550000,
                "foreign_buyer_surcharge": 0.075,
                "mandatory_searches": ["title_search", "body_corporate_search"],
            },
            AustralianState.SA: {
                "cooling_off_period_days": 2,
                "stamp_duty_threshold": 12000,
                "first_home_buyer_threshold": 600000,
                "foreign_buyer_surcharge": 0.07,
                "mandatory_searches": ["title_search", "planning_certificate"],
            },
            AustralianState.WA: {
                "cooling_off_period_days": 0,  # No cooling off in WA
                "stamp_duty_threshold": 25000,
                "first_home_buyer_threshold": 550000,
                "foreign_buyer_surcharge": 0.075,
                "mandatory_searches": ["title_search", "property_information_report"],
            },
            AustralianState.TAS: {
                "cooling_off_period_days": 3,
                "stamp_duty_threshold": 3000,
                "first_home_buyer_threshold": 600000,
                "foreign_buyer_surcharge": 0.08,
                "mandatory_searches": ["title_search", "planning_certificate"],
            },
            AustralianState.NT: {
                "cooling_off_period_days": 4,
                "stamp_duty_threshold": 0,
                "first_home_buyer_threshold": 650000,
                "foreign_buyer_surcharge": 0.015,
                "mandatory_searches": ["title_search"],
            },
            AustralianState.ACT: {
                "cooling_off_period_days": 5,
                "stamp_duty_threshold": 0,
                "first_home_buyer_threshold": 750000,
                "foreign_buyer_surcharge": 0.075,
                "mandatory_searches": ["title_search", "planning_certificate"],
            },
        }

        # Contract type specific requirements
        self.contract_requirements = {
            ContractType.SALE_OF_LAND: {
                "mandatory_clauses": [
                    "purchase_price",
                    "settlement_date",
                    "deposit_amount",
                    "cooling_off_period",
                ],
                "recommended_clauses": [
                    "finance_clause",
                    "building_inspection",
                    "pest_inspection",
                ],
            },
            ContractType.OFF_THE_PLAN: {
                "mandatory_clauses": [
                    "purchase_price",
                    "completion_date",
                    "deposit_structure",
                    "sunset_clause",
                ],
                "recommended_clauses": ["material_changes", "defects_liability"],
            },
            ContractType.AUCTION: {
                "mandatory_clauses": [
                    "purchase_price",
                    "auction_date",
                    "deposit_amount",
                    "settlement_terms",
                ],
                "recommended_clauses": ["vendor_bid_declaration"],
            },
        }

    async def initialize(self):
        """Initialize contract analysis service with GeminiClient"""
        try:
            # Get initialized Gemini client from factory
            self.gemini_client = await get_gemini_client()

            # Verify client is available
            if not self.gemini_client:
                raise ClientConnectionError(
                    "Failed to get Gemini client",
                    client_name="ContractAnalysisService",
                )

            logger.info("Contract Analysis Service V2 initialized with GeminiClient")

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to Gemini service: {e}")
            raise HTTPException(
                status_code=503, detail="AI analysis service unavailable"
            )
        except Exception as e:
            logger.error(f"Failed to initialize contract analysis service: {str(e)}")
            raise

    @langsmith_trace(
        name="contract_analysis_service_analyze_contract", run_type="chain"
    )
    async def analyze_contract(
        self,
        contract_text: str,
        config: ContractAnalysisConfig,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze contract text using AI with Australian-specific legal framework

        Args:
            contract_text: The extracted contract text
            config: Analysis configuration
            metadata: Additional metadata about the contract

        Returns:
            Dict containing comprehensive contract analysis
        """

        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="AI analysis service not initialized"
            )

        try:
            log_trace_info(
                "contract_analysis_service_analyze_contract",
                contract_length=len(contract_text),
                state=config.state.value if config.state else None,
                contract_type=(
                    config.contract_type.value if config.contract_type else None
                ),
                analysis_type=(
                    config.analysis_type.value if config.analysis_type else None
                ),
            )
            start_time = time.time()

            # Prepare analysis prompt
            analysis_prompt = self._create_analysis_prompt(
                contract_text, config, metadata
            )

            # Use Gemini client for analysis
            try:
                ai_response = await self.gemini_client.generate_content(
                    prompt=analysis_prompt,
                    temperature=0.2,  # Lower temperature for more consistent analysis
                    max_tokens=4000,
                )
            except ClientQuotaExceededError:
                raise HTTPException(
                    status_code=429,
                    detail="AI analysis quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during analysis: {e}")
                raise HTTPException(
                    status_code=500, detail=f"AI analysis failed: {str(e)}"
                )

            # Parse AI response
            analysis_result = self._parse_ai_response(ai_response, config)

            # Add compliance checks
            compliance_result = self._check_compliance(analysis_result, config)

            # Add risk assessment
            risk_assessment = self._assess_risks(analysis_result, config)

            # Calculate financial implications
            financial_analysis = self._analyze_financial_terms(analysis_result, config)

            # Get authentication method from client
            auth_method = "unknown"
            try:
                client_health = await self.gemini_client.health_check()
                auth_method = client_health.get("authentication", {}).get(
                    "method", "unknown"
                )
            except Exception:
                pass

            return {
                "contract_summary": analysis_result.get("summary", {}),
                "key_terms": analysis_result.get("key_terms", {}),
                "parties": analysis_result.get("parties", {}),
                "property_details": analysis_result.get("property_details", {}),
                "financial_terms": financial_analysis,
                "compliance_check": compliance_result,
                "risk_assessment": risk_assessment,
                "recommendations": self._generate_recommendations(
                    analysis_result, compliance_result, risk_assessment
                ),
                "analysis_metadata": {
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "analysis_duration_seconds": time.time() - start_time,
                    "contract_type": config.contract_type.value,
                    "australian_state": config.australian_state.value,
                    "analysis_depth": config.analysis_depth.value,
                    "ai_model": "gemini",
                    "authentication_method": auth_method,
                    "service": "ContractAnalysisService",
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Contract analysis error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Contract analysis failed: {str(e)}"
            )

    def _create_analysis_prompt(
        self,
        contract_text: str,
        config: ContractAnalysisConfig,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a comprehensive prompt for contract analysis"""

        state_info = self.state_regulations.get(config.australian_state, {})
        contract_reqs = self.contract_requirements.get(config.contract_type, {})

        prompt = f"""
You are an expert Australian real estate lawyer specializing in {config.australian_state.value} property law.

Analyze the following {config.contract_type.value} contract and provide a comprehensive analysis.

Contract Text:
{contract_text[:15000]}  # Limit to prevent token overflow

Analysis Requirements:
1. **Contract Summary**: Provide a clear, concise summary of the contract
2. **Key Terms Extraction**: Extract and categorize all important terms
3. **Party Information**: Identify all parties and their roles
4. **Property Details**: Extract all property-related information
5. **Financial Terms**: Identify all financial obligations and terms
6. **Legal Compliance**: Check compliance with {config.australian_state.value} regulations
7. **Risk Identification**: Identify potential risks and issues
8. **Missing Elements**: Identify any missing mandatory clauses

State-Specific Information:
- Cooling-off period: {state_info.get('cooling_off_period_days', 'N/A')} days
- Stamp duty threshold: ${state_info.get('stamp_duty_threshold', 'N/A')}
- First home buyer threshold: ${state_info.get('first_home_buyer_threshold', 'N/A')}
- Foreign buyer surcharge: {state_info.get('foreign_buyer_surcharge', 0) * 100}%
- Mandatory searches: {', '.join(state_info.get('mandatory_searches', []))}

Contract Type Requirements:
- Mandatory clauses: {', '.join(contract_reqs.get('mandatory_clauses', []))}
- Recommended clauses: {', '.join(contract_reqs.get('recommended_clauses', []))}

Provide your analysis in a structured JSON format with the following sections:
- summary: Brief overview of the contract
- key_terms: Dictionary of important terms and their values
- parties: Information about vendor, purchaser, and other parties
- property_details: Address, title, and other property information
- financial_terms: Purchase price, deposit, and payment structure
- compliance_issues: List of any compliance problems found
- risks: List of identified risks with severity levels
- missing_clauses: List of missing mandatory or recommended clauses
- recommendations: Specific recommendations for the buyer/seller

Focus Areas: {', '.join([area.value for area in config.focus_areas])}
"""

        if metadata:
            prompt += f"\n\nAdditional Context: {json.dumps(metadata)}"

        return prompt

    def _parse_ai_response(
        self, ai_response: str, config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Parse and structure the AI response"""

        try:
            # Try to extract JSON from the response
            json_match = re.search(r"\{[\s\S]*\}", ai_response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")

        # Fallback: Create structured response from text
        return self._extract_structured_data(ai_response)

    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from unstructured text response"""

        result = {
            "summary": "",
            "key_terms": {},
            "parties": {},
            "property_details": {},
            "financial_terms": {},
            "compliance_issues": [],
            "risks": [],
            "missing_clauses": [],
        }

        # Extract sections using pattern matching
        sections = text.split("\n\n")

        for section in sections:
            section_lower = section.lower()

            if "summary" in section_lower:
                result["summary"] = section
            elif "purchase price" in section_lower or "price" in section_lower:
                # Extract price
                price_match = re.search(r"\$[\d,]+", section)
                if price_match:
                    result["key_terms"]["purchase_price"] = price_match.group()
            elif "vendor" in section_lower or "seller" in section_lower:
                result["parties"]["vendor"] = section
            elif "purchaser" in section_lower or "buyer" in section_lower:
                result["parties"]["purchaser"] = section
            elif "property" in section_lower or "address" in section_lower:
                result["property_details"]["description"] = section
            elif "risk" in section_lower:
                result["risks"].append(section)
            elif "compliance" in section_lower:
                result["compliance_issues"].append(section)

        return result

    def _check_compliance(
        self, analysis_result: Dict[str, Any], config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Check contract compliance with state regulations"""

        compliance_issues = []
        state_regs = self.state_regulations.get(config.australian_state, {})
        contract_reqs = self.contract_requirements.get(config.contract_type, {})

        # Check mandatory clauses
        missing_mandatory = []
        for clause in contract_reqs.get("mandatory_clauses", []):
            if clause not in analysis_result.get("key_terms", {}):
                missing_mandatory.append(clause)

        if missing_mandatory:
            compliance_issues.append(
                {
                    "issue": "Missing mandatory clauses",
                    "severity": "high",
                    "details": missing_mandatory,
                    "recommendation": f"Add missing clauses: {', '.join(missing_mandatory)}",
                }
            )

        # Check cooling-off period
        if state_regs.get("cooling_off_period_days", 0) > 0:
            cooling_off = analysis_result.get("key_terms", {}).get("cooling_off_period")
            if not cooling_off:
                compliance_issues.append(
                    {
                        "issue": "No cooling-off period specified",
                        "severity": "high",
                        "details": f"Required: {state_regs['cooling_off_period_days']} days",
                        "recommendation": "Add standard cooling-off period clause",
                    }
                )

        return {
            "compliant": len(compliance_issues) == 0,
            "issues": compliance_issues,
            "checked_regulations": list(state_regs.keys()),
            "state": config.australian_state.value,
        }

    def _assess_risks(
        self, analysis_result: Dict[str, Any], config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Assess risks in the contract"""

        risks = []
        risk_score = 0

        # Check for sunset clause in off-the-plan
        if config.contract_type == ContractType.OFF_THE_PLAN:
            sunset_clause = analysis_result.get("key_terms", {}).get("sunset_clause")
            if not sunset_clause:
                risks.append(
                    {
                        "risk": "No sunset clause",
                        "severity": "high",
                        "impact": "Developer can delay indefinitely",
                        "mitigation": "Negotiate sunset clause with reasonable timeframe",
                    }
                )
                risk_score += 30

        # Check finance clause
        finance_clause = analysis_result.get("key_terms", {}).get("finance_clause")
        if not finance_clause and config.contract_type != ContractType.AUCTION:
            risks.append(
                {
                    "risk": "No finance clause",
                    "severity": "medium",
                    "impact": "Risk of losing deposit if finance not approved",
                    "mitigation": "Add finance clause with specific conditions",
                }
            )
            risk_score += 20

        # Add identified risks from AI analysis
        for risk in analysis_result.get("risks", []):
            risks.append(
                {
                    "risk": risk,
                    "severity": "medium",
                    "impact": "Review required",
                    "mitigation": "Seek legal advice",
                }
            )
            risk_score += 15

        return {
            "overall_risk_level": self._calculate_risk_level(risk_score),
            "risk_score": risk_score,
            "identified_risks": risks,
            "risk_count": len(risks),
        }

    def _calculate_risk_level(self, score: int) -> str:
        """Calculate overall risk level based on score"""
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"

    def _analyze_financial_terms(
        self, analysis_result: Dict[str, Any], config: ContractAnalysisConfig
    ) -> Dict[str, Any]:
        """Analyze financial terms and implications"""

        financial_terms = {}
        key_terms = analysis_result.get("key_terms", {})

        # Extract purchase price
        purchase_price = key_terms.get("purchase_price", "0")
        if isinstance(purchase_price, str):
            # Extract numeric value
            price_match = re.search(r"[\d,]+", purchase_price.replace("$", ""))
            if price_match:
                purchase_price = float(price_match.group().replace(",", ""))
            else:
                purchase_price = 0

        financial_terms["purchase_price"] = purchase_price

        # Calculate stamp duty (simplified)
        state_regs = self.state_regulations.get(config.australian_state, {})
        if purchase_price > state_regs.get("stamp_duty_threshold", 0):
            # Simplified stamp duty calculation (actual rates are more complex)
            stamp_duty_rate = 0.055  # Average rate
            financial_terms["estimated_stamp_duty"] = purchase_price * stamp_duty_rate
        else:
            financial_terms["estimated_stamp_duty"] = 0

        # Extract deposit
        deposit = key_terms.get("deposit_amount", "10%")
        if isinstance(deposit, str) and "%" in deposit:
            deposit_percent = float(deposit.replace("%", "")) / 100
            financial_terms["deposit_amount"] = purchase_price * deposit_percent
        else:
            financial_terms["deposit_amount"] = deposit

        # Total upfront costs
        financial_terms["total_upfront_costs"] = (
            financial_terms.get("deposit_amount", 0)
            + financial_terms.get("estimated_stamp_duty", 0)
            + 5000  # Estimated legal and other fees
        )

        return financial_terms

    def _generate_recommendations(
        self,
        analysis_result: Dict[str, Any],
        compliance_result: Dict[str, Any],
        risk_assessment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""

        recommendations = []

        # Compliance recommendations
        if not compliance_result["compliant"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "compliance",
                    "recommendation": "Address compliance issues before proceeding",
                    "details": compliance_result["issues"],
                }
            )

        # Risk recommendations
        if risk_assessment["overall_risk_level"] in ["high", "medium"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "risk",
                    "recommendation": "Review identified risks with legal counsel",
                    "details": risk_assessment["identified_risks"],
                }
            )

        # Missing clause recommendations
        missing_clauses = analysis_result.get("missing_clauses", [])
        if missing_clauses:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "contract_terms",
                    "recommendation": "Consider adding recommended clauses",
                    "details": missing_clauses,
                }
            )

        # General recommendations
        recommendations.extend(
            [
                {
                    "priority": "medium",
                    "category": "due_diligence",
                    "recommendation": "Complete all mandatory property searches",
                    "details": "Ensure title search, planning certificates are obtained",
                },
                {
                    "priority": "low",
                    "category": "professional_advice",
                    "recommendation": "Review contract with qualified conveyancer",
                    "details": "Professional review recommended for all property transactions",
                },
            ]
        )

        return recommendations

    async def generate_contract_summary(
        self, contract_text: str, config: ContractAnalysisConfig
    ) -> str:
        """Generate a plain English summary of the contract"""

        if not self.gemini_client:
            raise HTTPException(status_code=503, detail="AI service not initialized")

        prompt = f"""
Provide a clear, plain English summary of this {config.contract_type.value} contract 
for {config.australian_state.value}. The summary should be suitable for a property buyer 
with no legal background.

Contract Text:
{contract_text[:10000]}

Include:
1. What is being sold and where
2. How much it costs
3. When settlement happens
4. Key conditions and requirements
5. Important dates and deadlines
6. What the buyer needs to do next

Keep the summary under 500 words and use simple language.
"""

        try:
            summary = await self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
            )
            return summary
        except ClientError as e:
            logger.error(f"Summary generation failed: {e}")
            return "Summary generation failed. Please review the full analysis."

    async def health_check(self) -> Dict[str, Any]:
        """Check health of contract analysis service"""

        health_status = {
            "service": "ContractAnalysisService",
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Check Gemini client
        if self.gemini_client:
            try:
                gemini_health = await self.gemini_client.health_check()
                health_status["gemini_status"] = gemini_health.get("status", "unknown")
                health_status["authentication_method"] = gemini_health.get(
                    "authentication", {}
                ).get("method", "unknown")
            except Exception as e:
                health_status["gemini_status"] = "error"
                health_status["status"] = "degraded"
                health_status["error"] = str(e)
        else:
            health_status["gemini_status"] = "not_initialized"
            health_status["status"] = "degraded"

        # Check configuration
        health_status["states_configured"] = len(self.state_regulations)
        health_status["contract_types_configured"] = len(self.contract_requirements)

        return health_status
