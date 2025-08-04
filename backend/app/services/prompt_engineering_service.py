"""
Advanced Prompt Engineering Service for Real2.AI
Specialized prompts for Australian contract document parsing and analysis
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from app.models.contract_state import AustralianState, ContractType

logger = logging.getLogger(__name__)

class PromptTemplate(Enum):
    OCR_EXTRACTION = "ocr_extraction"
    STRUCTURE_ANALYSIS = "structure_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    FINANCIAL_ANALYSIS = "financial_analysis"
    RECOMMENDATIONS = "recommendations"

class ContractComplexity(Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    COMMERCIAL = "commercial"

@dataclass
class PromptContext:
    """Context for prompt engineering"""
    australian_state: AustralianState
    contract_type: ContractType
    user_type: str  # buyer, seller, investor, etc.
    complexity: ContractComplexity
    focus_areas: List[str]
    user_experience_level: str  # novice, intermediate, expert
    language_preference: str = "en"

class PromptEngineeringService:
    """Advanced prompt engineering for Australian contract analysis"""
    
    def __init__(self):
        self.australian_legal_terms = {
            "general": [
                "vendor", "purchaser", "settlement", "completion", "exchange",
                "cooling-off period", "rescission", "deposit", "purchase price",
                "title", "caveat", "encumbrance", "easement", "covenant",
                "strata", "body corporate", "rates", "outgoings"
            ],
            "nsw": [
                "planning certificate", "section 149 certificate", "conveyancing act",
                "home building act", "fair trading", "consumer guarantees"
            ],
            "vic": [
                "section 32", "owners corporation", "planning permit",
                "building permit", "pest inspection", "sale of land act"
            ],
            "qld": [
                "building and pest inspection", "form 1", "community titles scheme",
                "body corporate", "queensland building and construction commission"
            ]
        }
        
        self.contract_structures = {
            ContractType.PURCHASE_AGREEMENT: {
                "sections": [
                    "parties", "property_description", "purchase_price",
                    "deposit", "settlement_terms", "conditions_precedent",
                    "warranties", "special_conditions", "default_provisions"
                ],
                "key_clauses": [
                    "finance_clause", "building_inspection", "pest_inspection",
                    "cooling_off", "vendor_disclosure", "chattels"
                ]
            },
            ContractType.LEASE_AGREEMENT: {
                "sections": [
                    "parties", "premises", "term", "rent", "bond",
                    "maintenance", "termination", "special_conditions"
                ],
                "key_clauses": [
                    "rent_review", "break_clause", "assignment", "subletting"
                ]
            }
        }
        
        self.risk_indicators = {
            "high_risk": [
                "unconditional", "no cooling off", "vendor finance",
                "subject to subdivision", "heritage listed", "contaminated land",
                "flooding risk", "bushfire zone", "mining lease"
            ],
            "medium_risk": [
                "short settlement", "strata dispute", "building defects",
                "council orders", "easement variations", "leasehold"
            ],
            "financial_risk": [
                "price above valuation", "low deposit", "finance pre-approval required",
                "GST implications", "foreign buyer duties", "land tax"
            ]
        }

    def create_ocr_extraction_prompt(
        self,
        context: PromptContext,
        document_type: str = "contract",
        quality_requirements: str = "high"
    ) -> str:
        """Create optimized prompt for OCR text extraction"""
        
        state_specific_terms = self._get_state_specific_terms(context.australian_state)
        
        base_prompt = f"""
You are an expert OCR system specialized in extracting text from Australian real estate {document_type}s.
This document is from {context.australian_state.value}, Australia.

EXTRACTION REQUIREMENTS:
1. **Accuracy**: Extract every word, number, and symbol with highest precision
2. **Structure**: Preserve document formatting, spacing, and layout
3. **Completeness**: Include headers, footers, fine print, and annotations
4. **Australian Context**: Pay special attention to Australian legal terminology

KEY TERMS TO IDENTIFY ACCURATELY:
{self._format_terms_list(state_specific_terms)}

SPECIFIC FOCUS AREAS:
"""
        
        # Add focus areas based on contract type
        if context.contract_type == ContractType.PURCHASE_AGREEMENT:
            base_prompt += """
- Purchase price and deposit amounts (look for $ symbols and numbers)
- Settlement/completion dates
- Cooling-off period duration
- Finance clause conditions
- Inspection requirements (building, pest, strata)
- Special conditions and warranties
- Vendor and purchaser details
"""
        
        # Add state-specific requirements
        base_prompt += f"""
{context.australian_state.value.upper()} SPECIFIC REQUIREMENTS:
{self._get_state_specific_extraction_notes(context.australian_state)}

EXTRACTION INSTRUCTIONS:
- Extract ALL text visible in the image/document
- Maintain original formatting where possible
- Use [unclear] for illegible text with your best interpretation
- Include page numbers, headers, and footers
- Preserve table structures and lists
- Don't add explanations - only extracted text
- Handle handwritten notes and annotations carefully

OUTPUT FORMAT: Pure extracted text maintaining document structure.
"""
        
        return base_prompt

    def create_structure_analysis_prompt(
        self,
        extracted_text: str,
        context: PromptContext,
        analysis_depth: str = "comprehensive"
    ) -> str:
        """Create prompt for structured contract analysis"""
        
        contract_structure = self.contract_structures.get(
            context.contract_type, 
            self.contract_structures[ContractType.PURCHASE_AGREEMENT]
        )
        
        prompt = f"""
You are an expert Australian property lawyer specializing in {context.australian_state.value} real estate law.
Analyze this {context.contract_type.value} and extract structured information.

USER CONTEXT:
- Role: {context.user_type}
- Experience: {context.user_experience_level}
- State: {context.australian_state.value}
- Contract complexity: {context.complexity.value}

CONTRACT TEXT:
{extracted_text[:6000]}  # Limit for API efficiency

EXTRACTION SCHEMA:
Extract the following information as JSON:

{{
    "document_metadata": {{
        "contract_type": "{context.contract_type.value}",
        "state_jurisdiction": "{context.australian_state.value}",
        "document_date": "date if identifiable",
        "page_count": "estimated pages"
    }},
    "parties": {{
        "vendor": {{
            "name": "full legal name",
            "address": "address if provided",
            "solicitor": "solicitor details if mentioned",
            "abn_acn": "if business entity"
        }},
        "purchaser": {{
            "name": "full legal name", 
            "address": "address if provided",
            "solicitor": "solicitor details if mentioned"
        }}
    }},
    "property_details": {{
        "address": "full property address including postcode",
        "legal_description": "lot/plan or title details",
        "property_type": "house/unit/townhouse/land/commercial",
        "land_size": "if mentioned",
        "building_area": "if mentioned",
        "zoning": "if mentioned"
    }},
    "financial_terms": {{
        "purchase_price": numeric_value,
        "deposit": {{
            "amount": numeric_value,
            "percentage": calculated_percentage,
            "due_date": "when deposit is due",
            "method": "cash/cheque/bank_guarantee"
        }},
        "balance": calculated_balance,
        "adjustments": "rates/rent/other adjustments mentioned"
    }},
    "settlement_terms": {{
        "settlement_date": "specific date or period",
        "settlement_period": "number of days from exchange",
        "place_of_settlement": "location if specified",
        "time_of_settlement": "time if specified"
    }},
    "conditions_and_warranties": {{
        "cooling_off_period": {{
            "applicable": true/false,
            "duration": "number of business days",
            "exclusions": "any exclusions mentioned"
        }},
        "finance_clause": {{
            "applicable": true/false,
            "loan_amount": numeric_value_if_mentioned,
            "approval_period": "days for finance approval",
            "interest_rate": "if specified"
        }},
        "building_inspection": {{
            "required": true/false,
            "period": "inspection period",
            "type": "building and/or pest"
        }},
        "other_conditions": ["list all other conditions"]
    }},
    "special_conditions": {{
        "conditions_list": ["extract all special conditions"],
        "vendor_warranties": ["list vendor warranties"],
        "purchaser_obligations": ["list purchaser obligations"]
    }},
    "legal_and_compliance": {{
        "governing_law": "{context.australian_state.value}",
        "gst_applicable": true/false,
        "foreign_buyer_duties": "if mentioned",
        "disclosure_statements": ["list required disclosures"]
    }}
}}

ANALYSIS GUIDELINES:
- Extract only information explicitly stated in the contract
- Convert currency amounts to numeric values (remove $ and commas)
- Calculate percentages where amounts allow
- Identify all conditions precedent and warranties
- Note any unusual or non-standard clauses
- Focus on {context.australian_state.value}-specific requirements

Return ONLY the JSON structure, no additional commentary.
"""
        
        return prompt

    def create_risk_assessment_prompt(
        self,
        structured_data: Dict[str, Any],
        context: PromptContext,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """Create specialized risk assessment prompt"""
        
        risk_indicators = self._get_relevant_risk_indicators(context)
        
        prompt = f"""
You are a senior Australian property lawyer with expertise in {context.australian_state.value} real estate risk assessment.
Perform comprehensive risk analysis for this {context.contract_type.value}.

USER PROFILE:
- Role: {context.user_type}
- Experience: {context.user_experience_level}
- Risk tolerance: {"conservative" if context.user_experience_level == "novice" else "moderate"}

CONTRACT DATA:
{self._format_contract_data_for_analysis(structured_data)}

RISK ASSESSMENT FRAMEWORK:
Evaluate risks across these dimensions:

1. **Legal Risks** - Contract terms, compliance, enforceability
2. **Financial Risks** - Price, financing, costs, market factors
3. **Property Risks** - Condition, location, title, planning
4. **Transaction Risks** - Settlement, conditions, timing
5. **{context.australian_state.value} Specific Risks** - State regulations, duties, requirements

KNOWN RISK INDICATORS:
{self._format_risk_indicators(risk_indicators)}

ANALYSIS OUTPUT:
Return detailed risk assessment as JSON:

{{
    "overall_risk_assessment": {{
        "risk_score": number_1_to_10,
        "risk_level": "low/medium/high/critical",
        "confidence_level": number_0_to_1,
        "summary": "brief overall assessment"
    }},
    "risk_categories": {{
        "legal_risks": [
            {{
                "risk_factor": "specific legal risk",
                "severity": "low/medium/high/critical",
                "probability": "low/medium/high",
                "impact": "description of potential impact",
                "mitigation": "suggested mitigation strategy",
                "state_specific": true/false
            }}
        ],
        "financial_risks": [
            {{
                "risk_factor": "specific financial risk",
                "severity": "low/medium/high/critical", 
                "probability": "low/medium/high",
                "impact": "potential financial impact",
                "mitigation": "suggested mitigation strategy",
                "estimated_cost": numeric_value_if_applicable
            }}
        ],
        "property_risks": [
            {{
                "risk_factor": "specific property risk",
                "severity": "low/medium/high/critical",
                "probability": "low/medium/high", 
                "impact": "description of impact",
                "mitigation": "suggested mitigation strategy"
            }}
        ],
        "transaction_risks": [
            {{
                "risk_factor": "specific transaction risk",
                "severity": "low/medium/high/critical",
                "probability": "low/medium/high",
                "impact": "impact on transaction",
                "mitigation": "suggested mitigation strategy"
            }}
        ]
    }},
    "critical_attention_areas": [
        "list items requiring immediate attention"
    ],
    "state_specific_considerations": [
        "list {context.australian_state.value}-specific risks and requirements"
    ],
    "recommended_actions": [
        {{
            "action": "specific recommended action",
            "priority": "critical/high/medium/low",
            "timeline": "immediate/before_exchange/before_settlement",
            "professional_required": "lawyer/accountant/inspector/surveyor"
        }}
    ]
}}

ASSESSMENT PRINCIPLES:
- Consider {context.user_type} perspective and experience level
- Apply {context.australian_state.value} property law and regulations
- Balance thoroughness with practical applicability
- Highlight actionable risks with clear mitigation strategies
- Consider current market conditions and trends

Return ONLY the JSON structure with comprehensive risk analysis.
"""
        
        return prompt

    def create_compliance_check_prompt(
        self,
        structured_data: Dict[str, Any],
        context: PromptContext
    ) -> str:
        """Create compliance checking prompt"""
        
        state_requirements = self._get_state_compliance_requirements(context.australian_state)
        
        prompt = f"""
You are a compliance expert for Australian property law, specializing in {context.australian_state.value} regulations.
Check this {context.contract_type.value} for compliance with current laws and regulations.

CONTRACT DETAILS:
{self._format_contract_data_for_analysis(structured_data)}

{context.australian_state.value.upper()} COMPLIANCE REQUIREMENTS:
{state_requirements}

COMPLIANCE CHECK FRAMEWORK:
{{
    "overall_compliance": {{
        "compliant": true/false,
        "compliance_score": number_0_to_10,
        "major_issues": number,
        "minor_issues": number
    }},
    "mandatory_requirements": {{
        "cooling_off_period": {{
            "required": true/false,
            "provided": true/false,
            "duration_correct": true/false,
            "issues": ["list any issues"]
        }},
        "disclosure_requirements": {{
            "vendor_statement": "provided/not_provided/unclear",
            "planning_certificate": "required/provided/not_mentioned",
            "building_certificates": "required/provided/not_mentioned",
            "other_disclosures": ["list other required disclosures"]
        }},
        "financial_compliance": {{
            "deposit_requirements": "compliant/non_compliant",
            "gst_treatment": "correct/incorrect/unclear",
            "stamp_duty_implications": "acknowledged/not_mentioned",
            "foreign_buyer_duties": "applicable/not_applicable/unclear"
        }}
    }},
    "regulatory_compliance": {{
        "consumer_protection": {{
            "fair_trading_compliance": true/false,
            "consumer_guarantees": "applicable/not_applicable",
            "unconscionable_conduct": "no_issues/potential_issues"
        }},
        "professional_standards": {{
            "legal_representation": "adequate/inadequate/unclear",
            "proper_execution": "compliant/non_compliant",
            "witnessing_requirements": "met/not_met/unclear"
        }}
    }},
    "compliance_issues": [
        {{
            "issue": "description of compliance issue",
            "severity": "critical/high/medium/low",
            "legal_basis": "relevant law or regulation",
            "consequence": "potential consequence of non-compliance",
            "remedy": "suggested remedy or action"
        }}
    ],
    "recommendations": [
        {{
            "recommendation": "specific compliance recommendation",
            "urgency": "immediate/before_exchange/before_settlement",
            "responsibility": "vendor/purchaser/legal_representative"
        }}
    ]
}}

Focus on:
- {context.australian_state.value} specific statutory requirements
- Consumer protection obligations
- Professional compliance standards
- Disclosure requirements
- Financial and tax compliance

Return ONLY the JSON compliance analysis.
"""
        
        return prompt

    def create_financial_analysis_prompt(
        self,
        structured_data: Dict[str, Any],
        context: PromptContext,
        user_financial_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create financial analysis prompt"""
        
        financial_context = ""
        if user_financial_profile:
            financial_context = f"""
USER FINANCIAL PROFILE:
- Annual income: ${user_financial_profile.get('annual_income', 'not_provided'):,}
- Available deposit: ${user_financial_profile.get('available_deposit', 'not_provided'):,}
- Current debt: ${user_financial_profile.get('current_debt', 'not_provided'):,}
- First home buyer: {user_financial_profile.get('first_home_buyer', 'unknown')}
- Investment purpose: {user_financial_profile.get('investment_purpose', 'unknown')}
"""

        prompt = f"""
You are a qualified financial advisor specializing in Australian property transactions.
Analyze the financial aspects of this {context.contract_type.value} for a {context.user_type}.

{financial_context}

CONTRACT FINANCIAL DATA:
{self._format_financial_data_for_analysis(structured_data)}

FINANCIAL ANALYSIS FRAMEWORK:
{{
    "cost_analysis": {{
        "purchase_price": {{
            "amount": numeric_value,
            "price_per_sqm": calculated_if_possible,
            "market_assessment": "above/at/below_market"
        }},
        "upfront_costs": {{
            "deposit": {{
                "amount": numeric_value,
                "percentage": calculated_percentage,
                "adequacy": "adequate/low/high"
            }},
            "stamp_duty": {{
                "estimated_amount": calculated_amount,
                "basis": "calculation_method",
                "concessions_available": true/false
            }},
            "legal_fees": {{
                "estimated_range": "low_to_high_estimate",
                "factors": ["factors_affecting_cost"]
            }},
            "other_costs": {{
                "building_inspection": estimated_amount,
                "pest_inspection": estimated_amount,
                "loan_costs": estimated_amount,
                "insurance": estimated_amount,
                "total_estimated": sum_of_all_costs
            }}
        }},
        "ongoing_costs": {{
            "rates": "estimated_annual",
            "strata_fees": "if_applicable",
            "insurance": "estimated_annual",
            "maintenance": "estimated_annual"
        }}
    }},
    "financing_analysis": {{
        "loan_requirements": {{
            "loan_amount": calculated_amount,
            "loan_to_value_ratio": calculated_percentage,
            "serviceability_estimate": "adequate/marginal/challenging"
        }},
        "finance_clause_analysis": {{
            "protection_level": "adequate/inadequate",
            "approval_timeframe": "sufficient/tight/inadequate",
            "conditions": ["list_finance_conditions"]
        }}
    }},
    "investment_analysis": {{
        "rental_yield": "estimated_if_investment",
        "capital_growth_potential": "assessment",
        "tax_implications": {{
            "negative_gearing": "applicable/not_applicable",
            "depreciation": "available/not_available",
            "capital_gains": "considerations"
        }}
    }},
    "risk_factors": {{
        "affordability_risks": ["list_risks"],
        "market_risks": ["list_risks"],
        "financing_risks": ["list_risks"]
    }},
    "recommendations": [
        {{
            "area": "financing/costs/investment",
            "recommendation": "specific_recommendation",
            "priority": "high/medium/low",
            "action_required": "specific_action"
        }}
    ]
}}

ANALYSIS CONSIDERATIONS:
- Current {context.australian_state.value} market conditions
- Interest rate environment
- {context.user_type} specific financial objectives
- Tax implications and optimization opportunities
- Cash flow impact and sustainability

Return ONLY the JSON financial analysis.
"""
        
        return prompt

    def create_recommendations_prompt(
        self,
        analysis_summary: Dict[str, Any],
        context: PromptContext
    ) -> str:
        """Create comprehensive recommendations prompt"""
        
        prompt = f"""
You are a senior property advisor providing strategic recommendations for this {context.contract_type.value}.
Synthesize all analysis into actionable advice for a {context.user_type} in {context.australian_state.value}.

COMPLETE ANALYSIS SUMMARY:
{self._format_analysis_summary(analysis_summary)}

USER CONTEXT:
- Role: {context.user_type}
- Experience level: {context.user_experience_level}
- Location: {context.australian_state.value}

RECOMMENDATION FRAMEWORK:
{{
    "executive_summary": {{
        "overall_recommendation": "proceed/proceed_with_caution/do_not_proceed/seek_advice",
        "confidence_level": number_0_to_1,
        "key_strengths": ["list_main_positives"],
        "key_concerns": ["list_main_concerns"],
        "critical_actions": ["immediate_actions_required"]
    }},
    "immediate_actions": [
        {{
            "action": "specific_action_to_take",
            "priority": "critical/high/medium/low",
            "timeline": "immediate/within_days/before_settlement",
            "responsible_party": "you/lawyer/accountant/inspector",
            "estimated_cost": numeric_value,
            "consequence_of_inaction": "what_happens_if_not_done"
        }}
    ],
    "professional_advice_required": [
        {{
            "professional": "lawyer/accountant/building_inspector/valuer",
            "purpose": "specific_reason_for_consultation",
            "urgency": "immediate/high/medium/low",
            "estimated_cost": numeric_value,
            "questions_to_ask": ["specific_questions_to_ask"]
        }}
    ],
    "negotiation_opportunities": [
        {{
            "area": "price/conditions/settlement",
            "opportunity": "specific_negotiation_point",
            "strategy": "how_to_approach",
            "potential_benefit": "expected_outcome"
        }}
    ],
    "risk_mitigation": [
        {{
            "risk": "specific_risk_identified",
            "mitigation_strategy": "how_to_address",
            "cost": numeric_value,
            "effectiveness": "high/medium/low"
        }}
    ],
    "long_term_considerations": [
        {{
            "consideration": "future_planning_aspect",
            "recommendation": "suggested_approach",
            "timeline": "months/years"
        }}
    ],
    "state_specific_advice": [
        {{
            "area": "{context.australian_state.value}_specific_area",
            "advice": "state_specific_recommendation",
            "regulation": "relevant_regulation_or_law"
        }}
    ]
}}

RECOMMENDATION PRINCIPLES:
- Prioritize user's best interests and experience level
- Provide specific, actionable advice
- Consider {context.australian_state.value} regulations and market
- Balance risk management with opportunity
- Include realistic cost estimates
- Suggest specific professionals when needed

Return ONLY the JSON recommendations structure.
"""
        
        return prompt

    # Helper methods for prompt construction

    def _get_state_specific_terms(self, state: AustralianState) -> List[str]:
        """Get state-specific legal terms"""
        general_terms = self.australian_legal_terms["general"]
        state_key = state.value.lower()
        state_terms = self.australian_legal_terms.get(state_key, [])
        return general_terms + state_terms

    def _format_terms_list(self, terms: List[str]) -> str:
        """Format terms list for prompt"""
        return "- " + "\n- ".join(terms)

    def _get_state_specific_extraction_notes(self, state: AustralianState) -> str:
        """Get state-specific extraction requirements"""
        notes = {
            AustralianState.NSW: """
- Look for Section 149 planning certificates
- Identify Home Building Act warranties
- Note any Fair Trading Act disclosures
- Check for cooling-off period (5 business days standard)
""",
            AustralianState.VIC: """
- Look for Section 32 vendor statements
- Identify owners corporation details
- Note building and planning permits
- Check cooling-off period (3 business days standard)
""",
            AustralianState.QLD: """
- Look for Form 1 disclosure statements
- Identify body corporate information
- Note QBCC licensing details
- Check cooling-off period (5 business days standard)
"""
        }
        return notes.get(state, "Check for standard Australian property law requirements")

    def _get_relevant_risk_indicators(self, context: PromptContext) -> Dict[str, List[str]]:
        """Get relevant risk indicators for context"""
        base_indicators = self.risk_indicators.copy()
        
        # Add context-specific indicators
        if context.user_experience_level == "novice":
            base_indicators["novice_specific"] = [
                "complex conditions", "tight timeframes", "unusual terms",
                "high financial commitment", "limited cooling-off"
            ]
        
        return base_indicators

    def _format_risk_indicators(self, indicators: Dict[str, List[str]]) -> str:
        """Format risk indicators for prompt"""
        formatted = ""
        for category, risks in indicators.items():
            formatted += f"\n{category.upper().replace('_', ' ')}:\n"
            formatted += "- " + "\n- ".join(risks) + "\n"
        return formatted

    def _get_state_compliance_requirements(self, state: AustralianState) -> str:
        """Get state-specific compliance requirements"""
        requirements = {
            AustralianState.NSW: """
- Cooling-off period: 5 business days (unless waived)
- Vendor disclosure: Property, planning, and legal disclosures required
- Section 149 planning certificate required
- Home warranty insurance for residential building work
- Fair Trading Act consumer protections apply
""",
            AustralianState.VIC: """
- Cooling-off period: 3 business days (unless at auction)
- Section 32 vendor statement mandatory
- Building permits and certificates required
- Owners corporation certificate for strata properties
- Sale of Land Act requirements
""",
            AustralianState.QLD: """
- Cooling-off period: 5 business days (unless waived)
- Form 1 disclosure statement required
- Building and pest inspection standard
- Body corporate information for strata
- QBCC licensing requirements for building work
"""
        }
        return requirements.get(state, "Standard Australian property law requirements apply")

    def _format_contract_data_for_analysis(self, data: Dict[str, Any]) -> str:
        """Format contract data for analysis prompts"""
        formatted = json.dumps(data, indent=2, default=str)
        return formatted[:3000]  # Limit size for API efficiency

    def _format_financial_data_for_analysis(self, data: Dict[str, Any]) -> str:
        """Format financial data specifically"""
        financial_data = data.get("financial_terms", {})
        property_data = data.get("property_details", {})
        
        formatted = f"""
Purchase Price: ${financial_data.get('purchase_price', 'not_specified'):,}
Deposit: ${financial_data.get('deposit', {}).get('amount', 'not_specified'):,}
Property: {property_data.get('address', 'address_not_specified')}
Property Type: {property_data.get('property_type', 'not_specified')}
Settlement Period: {data.get('settlement_terms', {}).get('settlement_period', 'not_specified')}
"""
        return formatted

    def _format_analysis_summary(self, analysis: Dict[str, Any]) -> str:
        """Format complete analysis summary"""
        summary = {
            "risk_score": analysis.get("risk_assessment", {}).get("overall_risk_assessment", {}).get("risk_score", "unknown"),
            "compliance_status": analysis.get("compliance_analysis", {}).get("overall_compliance", {}).get("compliant", "unknown"),
            "financial_adequacy": analysis.get("financial_analysis", {}).get("financing_analysis", {}).get("serviceability_estimate", "unknown"),
            "critical_issues": len(analysis.get("critical_issues", [])),
            "major_concerns": analysis.get("major_concerns", [])
        }
        return json.dumps(summary, indent=2, default=str)[:2000]

    def optimize_prompt_for_model(
        self,
        base_prompt: str,
        model_name: str = "gemini-2.5-pro",
        max_tokens: int = 30000
    ) -> str:
        """Optimize prompt for specific model capabilities"""
        
        # Model-specific optimizations
        if "gemini" in model_name.lower():
            # Gemini performs well with structured instructions
            optimized = f"""<INSTRUCTIONS>
{base_prompt}
</INSTRUCTIONS>

Remember:
- Provide precise, structured analysis
- Focus on Australian legal context
- Return only requested JSON format
- Ensure all numeric values are properly formatted
"""
        else:
            # Generic optimization
            optimized = base_prompt
        
        # Truncate if too long
        if len(optimized) > max_tokens:
            optimized = optimized[:max_tokens] + "\n\n[Content truncated for length]"
        
        return optimized