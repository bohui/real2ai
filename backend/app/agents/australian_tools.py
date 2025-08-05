"""
Australian-specific tools for Real2.AI contract analysis
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
from datetime import datetime, timedelta
import re
from decimal import Decimal

from app.model.enums import AustralianState, RiskLevel
from app.models.contract_state import StampDutyCalculation


@tool
def extract_australian_contract_terms(document_text: str, state: str) -> Dict[str, Any]:
    """Extract key terms from Australian property contract with state-specific rules"""
    
    # Australian-specific patterns
    patterns = {
        "purchase_price": [
            r"purchase\s+price[:\s]+\$?([\d,]+\.?\d*)",
            r"consideration[:\s]+\$?([\d,]+\.?\d*)",
            r"total\s+amount[:\s]+\$?([\d,]+\.?\d*)"
        ],
        "deposit": [
            r"deposit[:\s]+\$?([\d,]+\.?\d*)",
            r"initial\s+payment[:\s]+\$?([\d,]+\.?\d*)"
        ],
        "settlement_date": [
            r"settlement\s+date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"completion\s+date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
        ],
        "cooling_off": [
            r"cooling[\s\-]?off\s+period[:\s]+(\d+)\s+days?",
            r"rescission\s+period[:\s]+(\d+)\s+days?"
        ],
        "property_address": [
            r"property[:\s]+(.+?)(?=\n|\.|,)",
            r"land[:\s]+(.+?)(?=\n|\.|,)",
            r"premises[:\s]+(.+?)(?=\n|\.|,)"
        ]
    }
    
    extracted_terms = {}
    confidence_scores = {}
    
    for term, term_patterns in patterns.items():
        best_match = None
        highest_confidence = 0.0
        
        for pattern in term_patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                confidence = calculate_extraction_confidence(match, document_text)
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = match.group(1).strip()
        
        if best_match and highest_confidence > 0.5:
            extracted_terms[term] = clean_extracted_value(term, best_match)
            confidence_scores[term] = highest_confidence
    
    # State-specific validation
    state_requirements = get_state_specific_requirements(state)
    validated_terms = validate_terms_for_state(extracted_terms, state_requirements)
    
    return {
        "terms": validated_terms,
        "confidence_scores": confidence_scores,
        "state_requirements": state_requirements,
        "overall_confidence": sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
    }


@tool
def validate_cooling_off_period(contract_terms: Dict, state: str) -> Dict[str, Any]:
    """Validate cooling-off period compliance by Australian state"""
    
    cooling_off_rules = {
        "NSW": {
            "days": 5,
            "type": "business_days",
            "exclusions": ["auction", "investment_property_over_1m"],
            "waiver_allowed": True,
            "legal_reference": "Conveyancing Act 1919 (NSW) s66W"
        },
        "VIC": {
            "days": 3,
            "type": "business_days", 
            "exclusions": ["auction"],
            "waiver_allowed": True,
            "legal_reference": "Sale of Land Act 1962 (Vic) s31"
        },
        "QLD": {
            "days": 5,
            "type": "business_days",
            "exclusions": ["auction", "contract_race"],
            "waiver_allowed": False,
            "legal_reference": "Property Law Act 1974 (Qld) s365"
        },
        "SA": {
            "days": 2,
            "type": "clear_days",
            "exclusions": ["auction"],
            "waiver_allowed": True,
            "legal_reference": "Land and Business (Sale and Conveyancing) Act 1994 (SA)"
        },
        "WA": {
            "days": 5,
            "type": "business_days",
            "exclusions": ["auction"],
            "waiver_allowed": True,
            "legal_reference": "Property Law Act 1969 (WA) s11A"
        },
        "TAS": {
            "days": None,
            "note": "No statutory cooling-off period",
            "legal_reference": "Common law only"
        },
        "NT": {
            "days": None,
            "note": "No statutory cooling-off period", 
            "legal_reference": "Common law only"
        },
        "ACT": {
            "days": 5,
            "type": "business_days",
            "exclusions": ["auction"],
            "waiver_allowed": True,
            "legal_reference": "Civil Law (Sale of Residential Property) Act 2003 (ACT)"
        }
    }
    
    rule = cooling_off_rules.get(state)
    contract_period = contract_terms.get("cooling_off_period")
    
    if not rule:
        return {
            "compliant": False,
            "error": f"Unknown Australian state: {state}"
        }
    
    # Check if cooling-off period applies
    if rule.get("days") is None:
        return {
            "compliant": True,
            "note": rule.get("note"),
            "legal_reference": rule.get("legal_reference"),
            "warnings": ["No statutory cooling-off period in this state"]
        }
    
    # Validate period
    validation_result = {
        "compliant": False,
        "required_period": rule,
        "contract_period": contract_period,
        "legal_reference": rule.get("legal_reference"),
        "warnings": [],
        "recommendations": []
    }
    
    if not contract_period:
        validation_result["warnings"].append("No cooling-off period specified in contract")
        validation_result["recommendations"].append("Ensure cooling-off period is clearly stated")
        return validation_result
    
    # Extract number of days from contract
    contract_days = extract_days_from_period(contract_period)
    required_days = rule["days"]
    
    if contract_days >= required_days:
        validation_result["compliant"] = True
        if contract_days > required_days:
            validation_result["warnings"].append(
                f"Contract provides {contract_days} days, which exceeds minimum requirement of {required_days} days"
            )
    else:
        validation_result["warnings"].append(
            f"Contract cooling-off period ({contract_days} days) is less than required minimum ({required_days} days)"
        )
        validation_result["recommendations"].append(
            f"Extend cooling-off period to at least {required_days} {rule['type']}"
        )
    
    return validation_result


@tool
def calculate_stamp_duty(
    purchase_price: float, 
    state: str, 
    is_first_home: bool = False,
    is_foreign_buyer: bool = False,
    is_investment: bool = False
) -> StampDutyCalculation:
    """Calculate Australian stamp duty with state-specific rates and exemptions"""
    
    stamp_duty_rates = {
        "NSW": {
            "thresholds": [
                (14000, 0.0125),
                (32000, 0.015), 
                (85000, 0.0175),
                (319000, 0.035),
                (1064000, 0.045),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 650000,
            "first_home_concession_threshold": 800000,
            "foreign_buyer_surcharge": 0.08,
            "investment_surcharge": 0.02
        },
        "VIC": {
            "thresholds": [
                (25000, 0.014),
                (130000, 0.024),
                (960000, 0.06),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 600000,
            "first_home_concession_threshold": 750000,
            "foreign_buyer_surcharge": 0.07,
            "vacant_land_tax": 0.01
        },
        "QLD": {
            "thresholds": [
                (5000, 0.015),
                (75000, 0.035),
                (540000, 0.045),
                (1000000, 0.055),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 550000,
            "foreign_buyer_surcharge": 0.07
        },
        "SA": {
            "thresholds": [
                (12000, 0.011),
                (30000, 0.022),
                (50000, 0.033),
                (100000, 0.044),
                (200000, 0.05),
                (250000, 0.055),
                (500000, 0.055),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 650000,
            "foreign_buyer_surcharge": 0.07
        },
        "WA": {
            "thresholds": [
                (120000, 0.019),
                (150000, 0.029),
                (360000, 0.039),
                (725000, 0.049),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 600000,
            "foreign_buyer_surcharge": 0.07
        }
    }
    
    rates = stamp_duty_rates.get(state)
    if not rates:
        raise ValueError(f"Stamp duty rates not available for state: {state}")
    
    # Calculate base stamp duty
    base_duty = 0.0
    remaining_value = purchase_price
    
    for i, (threshold, rate) in enumerate(rates["thresholds"]):
        if remaining_value <= 0:
            break
            
        if i == 0:
            taxable_amount = min(remaining_value, threshold)
        else:
            prev_threshold = rates["thresholds"][i-1][0]
            taxable_amount = min(remaining_value, threshold - prev_threshold)
        
        base_duty += taxable_amount * rate
        remaining_value -= taxable_amount
    
    # Calculate exemptions
    exemptions = 0.0
    if is_first_home:
        exemption_threshold = rates.get("first_home_exemption_threshold", 0)
        concession_threshold = rates.get("first_home_concession_threshold", 0)
        
        if purchase_price <= exemption_threshold:
            exemptions = base_duty  # Full exemption
        elif purchase_price <= concession_threshold:
            # Partial concession (varies by state)
            exemptions = base_duty * 0.5  # Simplified calculation
    
    # Calculate surcharges
    surcharges = 0.0
    if is_foreign_buyer and "foreign_buyer_surcharge" in rates:
        surcharges += purchase_price * rates["foreign_buyer_surcharge"]
    
    if is_investment and "investment_surcharge" in rates:
        surcharges += purchase_price * rates["investment_surcharge"]
    
    total_duty = base_duty - exemptions + surcharges
    
    return StampDutyCalculation(
        state=AustralianState(state),
        purchase_price=purchase_price,
        base_duty=base_duty,
        exemptions=exemptions,
        surcharges=surcharges,
        total_duty=max(0.0, total_duty),  # Can't be negative
        is_first_home_buyer=is_first_home,
        is_foreign_buyer=is_foreign_buyer,
        breakdown={
            "base_calculation": base_duty,
            "first_home_exemption": exemptions,
            "foreign_buyer_surcharge": surcharges,
            "net_payable": max(0.0, total_duty)
        }
    )


@tool 
def analyze_special_conditions(contract_terms: Dict, state: str) -> Dict[str, Any]:
    """Enhanced analysis of Australian-specific special conditions and risks with comprehensive risk scoring"""
    
    conditions = contract_terms.get("special_conditions", [])
    analysis_results = []
    overall_risk_score = 0.0
    critical_issues = []
    
    # Enhanced Australian special conditions with risk patterns
    condition_types = {
        "finance": {
            "keywords": ["finance", "loan", "mortgage", "bank approval", "pre-approval", "lending"],
            "risk_indicators": {
                "high": ["subject to purchaser obtaining", "unconditional approval", "bridging finance"],
                "medium": ["pre-approved", "conditional approval", "finance clause"],
                "low": ["finance approved", "cash purchase", "unconditional"]
            },
            "australian_requirements": "Must specify exact date, lender, and loan amount",
            "compliance_checks": ["date_specified", "lender_identified", "amount_stated"],
            "mitigation_strategies": [
                "Obtain pre-approval before contract signing",
                "Set realistic finance deadlines (21-30 days minimum)", 
                "Include backup lender options",
                "Consider finance broker assistance"
            ]
        },
        "building_pest": {
            "keywords": ["building", "pest", "inspection", "structural", "timber pest", "termite"],
            "risk_indicators": {
                "high": ["subject to satisfactory", "purchaser's sole discretion", "major defects"],
                "medium": ["building inspection", "pest inspection", "structural report"],
                "low": ["building report received", "inspection waived"]
            },
            "australian_requirements": "Licensed inspector required in most states, report within 5-7 days",
            "compliance_checks": ["inspector_licensed", "report_timeframe", "scope_defined"],
            "mitigation_strategies": [
                "Use qualified, licensed inspector familiar with local building codes",
                "Allow sufficient time for thorough inspection (5-7 business days)",
                "Specify what constitutes 'satisfactory' report",
                "Consider pre-purchase inspection for peace of mind"
            ]
        },
        "strata": {
            "keywords": ["strata", "body corporate", "owners corporation", "levies", "by-laws"],
            "risk_indicators": {
                "high": ["financial difficulties", "major works", "special levy", "litigation"],
                "medium": ["strata search", "by-laws review", "levy increases"],
                "low": ["healthy strata", "no issues", "standard levies"]
            },
            "australian_requirements": "Strata search must be current (30 days max), include financials and by-laws",
            "compliance_checks": ["search_current", "financials_reviewed", "bylaws_obtained"],
            "mitigation_strategies": [
                "Review strata minutes for past 12 months",
                "Check for planned maintenance or capital works",
                "Verify levy payment history and budget",
                "Understand by-laws restrictions before purchase"
            ]
        },
        "council": {
            "keywords": ["council", "rates", "planning", "zoning", "development", "approvals"],
            "risk_indicators": {
                "high": ["outstanding rates", "unapproved works", "development application pending"],
                "medium": ["council certificate", "zoning compliance", "rates current"],
                "low": ["no issues", "compliant", "rates paid"]
            },
            "australian_requirements": "Council certificate and rates certificate required",
            "compliance_checks": ["rates_current", "approvals_valid", "zoning_compliant"],
            "mitigation_strategies": [
                "Obtain council rates certificate and planning certificate",
                "Check for any outstanding council orders or notices",
                "Verify all works have proper approvals",
                "Review development potential and restrictions"
            ]
        },
        "settlement": {
            "keywords": ["settlement", "completion", "possession", "handover", "keys"],
            "risk_indicators": {
                "high": ["time is of the essence", "penalty interest", "immediate possession"],
                "medium": ["settlement date", "possession date", "delay provisions"],
                "low": ["standard settlement", "reasonable timeframe"]
            },
            "australian_requirements": "Must align with state requirements and allow reasonable timeframe",
            "compliance_checks": ["timeframe_reasonable", "penalty_clauses", "possession_terms"],
            "mitigation_strategies": [
                "Allow adequate time for settlement (typically 6-8 weeks)",
                "Negotiate reasonable penalty clauses",
                "Clarify possession and key handover arrangements",
                "Consider settlement agent or solicitor involvement"
            ]
        },
        "vendor_disclosure": {
            "keywords": ["disclosure", "vendor statement", "contract note", "material facts"],
            "risk_indicators": {
                "high": ["non-disclosure", "material defects", "hidden issues"],
                "medium": ["standard disclosure", "vendor statement", "some issues noted"],
                "low": ["full disclosure", "no issues", "transparent"]
            },
            "australian_requirements": "Vendor must disclose all material facts",
            "compliance_checks": ["statement_provided", "material_facts", "defects_disclosed"],
            "mitigation_strategies": [
                "Review vendor statement thoroughly",
                "Ask specific questions about property history",
                "Consider independent investigations for major purchases",
                "Verify all disclosed information independently"
            ]
        }
    }
    
    for condition in conditions:
        condition_text = condition.lower() if isinstance(condition, str) else str(condition).lower()
        
        # Enhanced condition classification with confidence scoring
        condition_type, classification_confidence = classify_condition_enhanced(condition_text, condition_types)
        
        # Advanced risk assessment with detailed scoring
        risk_analysis = assess_condition_risk_enhanced(condition_text, condition_type, state, condition_types)
        
        # Compliance checking
        compliance_results = check_condition_compliance(condition_text, condition_type, state, condition_types)
        
        # Generate targeted mitigation strategies
        mitigation_strategies = generate_mitigation_strategies(
            condition_text, condition_type, risk_analysis["risk_level"], state, condition_types
        )
        
        # Calculate condition-specific risk score (0-100)
        condition_risk_score = calculate_condition_risk_score(risk_analysis, compliance_results)
        
        condition_analysis = {
            "condition": condition,
            "type": condition_type,
            "classification_confidence": classification_confidence,
            "risk_level": risk_analysis["risk_level"].value,
            "risk_score": condition_risk_score,
            "risk_factors": risk_analysis["risk_factors"],
            "compliance_status": compliance_results["status"],
            "compliance_issues": compliance_results["issues"],
            "mitigation_strategies": mitigation_strategies,
            "state_specific_notes": get_state_specific_notes_enhanced(condition_type, state),
            "australian_requirements": condition_types.get(condition_type, {}).get("australian_requirements", ""),
            "priority": determine_condition_priority(condition_risk_score, risk_analysis["risk_level"]),
            "estimated_cost_impact": estimate_condition_cost_impact(condition_type, risk_analysis["risk_level"]),
            "confidence": classification_confidence
        }
        
        analysis_results.append(condition_analysis)
        overall_risk_score += condition_risk_score
        
        # Track critical issues
        if risk_analysis["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            critical_issues.append({
                "condition": condition,
                "type": condition_type,
                "risk_level": risk_analysis["risk_level"].value,
                "primary_concern": risk_analysis["primary_concern"]
            })
    
    # Calculate overall assessment
    num_conditions = len(analysis_results) if analysis_results else 1
    average_risk_score = overall_risk_score / num_conditions
    
    # Generate comprehensive recommendations
    comprehensive_recommendations = generate_comprehensive_recommendations(
        analysis_results, state, average_risk_score
    )
    
    return {
        "conditions_analysis": analysis_results,
        "overall_risk_score": round(average_risk_score, 2),
        "risk_category": categorize_overall_risk(average_risk_score),
        "critical_issues_count": len(critical_issues),
        "critical_issues": critical_issues,
        "state_compliance_summary": generate_state_compliance_summary(analysis_results, state),
        "comprehensive_recommendations": comprehensive_recommendations,
        "next_steps": generate_next_steps(analysis_results, critical_issues),
        "confidence_level": calculate_overall_confidence(analysis_results)
    }


# Enhanced Helper Functions

def classify_condition_enhanced(condition_text: str, condition_types: Dict) -> tuple[str, float]:
    """Enhanced condition classification with confidence scoring"""
    best_match = "other"
    highest_confidence = 0.0
    
    for ctype, details in condition_types.items():
        keyword_matches = sum(1 for keyword in details["keywords"] if keyword in condition_text)
        if keyword_matches > 0:
            confidence = min(0.95, 0.3 + (keyword_matches * 0.2))
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_match = ctype
    
    return best_match, highest_confidence


def assess_condition_risk_enhanced(condition_text: str, condition_type: str, state: str, condition_types: Dict) -> Dict[str, Any]:
    """Enhanced risk assessment with detailed analysis"""
    if condition_type not in condition_types:
        return {
            "risk_level": RiskLevel.MEDIUM,
            "risk_factors": ["Unknown condition type"],
            "primary_concern": "Unclassified condition requires manual review"
        }
    
    risk_indicators = condition_types[condition_type]["risk_indicators"]
    risk_factors = []
    risk_score = 50  # Base score
    
    # Check for high-risk indicators
    for high_risk_phrase in risk_indicators["high"]:
        if high_risk_phrase in condition_text:
            risk_score += 25
            risk_factors.append(f"High-risk phrase detected: '{high_risk_phrase}'")
    
    # Check for medium-risk indicators
    for medium_risk_phrase in risk_indicators["medium"]:
        if medium_risk_phrase in condition_text:
            risk_score += 10
            risk_factors.append(f"Medium-risk phrase detected: '{medium_risk_phrase}'")
    
    # Check for low-risk indicators (reduce risk)
    for low_risk_phrase in risk_indicators["low"]:
        if low_risk_phrase in condition_text:
            risk_score -= 15
            risk_factors.append(f"Low-risk phrase detected: '{low_risk_phrase}'")
    
    # Determine risk level
    if risk_score >= 85:
        risk_level = RiskLevel.CRITICAL
        primary_concern = "Critical risk factors require immediate attention"
    elif risk_score >= 70:
        risk_level = RiskLevel.HIGH
        primary_concern = "High risk factors need careful management"
    elif risk_score >= 40:
        risk_level = RiskLevel.MEDIUM
        primary_concern = "Moderate risk factors require monitoring"
    else:
        risk_level = RiskLevel.LOW
        primary_concern = "Low risk factors, standard precautions apply"
    
    return {
        "risk_level": risk_level,
        "risk_score": min(100, max(0, risk_score)),
        "risk_factors": risk_factors,
        "primary_concern": primary_concern
    }


def check_condition_compliance(condition_text: str, condition_type: str, state: str, condition_types: Dict) -> Dict[str, Any]:
    """Check compliance against Australian legal requirements"""
    if condition_type not in condition_types:
        return {"status": "unknown", "issues": ["Condition type not recognized"]}
    
    compliance_checks = condition_types[condition_type].get("compliance_checks", [])
    issues = []
    compliant_items = []
    
    # Specific compliance checks based on condition type
    if condition_type == "finance":
        if not any(word in condition_text for word in ["date", "deadline", "by"]):
            issues.append("Finance deadline not clearly specified")
        else:
            compliant_items.append("Finance deadline specified")
            
        if not any(word in condition_text for word in ["bank", "lender", "financial institution"]):
            issues.append("Lender not identified")
        else:
            compliant_items.append("Lender identified")
    
    elif condition_type == "building_pest":
        if not any(word in condition_text for word in ["licensed", "qualified", "certified"]):
            issues.append("Inspector qualifications not specified")
        else:
            compliant_items.append("Inspector qualifications mentioned")
            
        if not any(word in condition_text for word in ["days", "business days", "within"]):
            issues.append("Inspection timeframe not specified")
        else:
            compliant_items.append("Inspection timeframe specified")
    
    elif condition_type == "strata":
        if not any(word in condition_text for word in ["search", "certificate", "report"]):
            issues.append("Strata search requirement not clear")
        else:
            compliant_items.append("Strata search referenced")
    
    status = "compliant" if len(issues) == 0 else "partial" if len(compliant_items) > 0 else "non-compliant"
    
    return {
        "status": status,
        "issues": issues,
        "compliant_items": compliant_items,
        "compliance_percentage": len(compliant_items) / max(1, len(compliant_items) + len(issues)) * 100
    }


def generate_mitigation_strategies(condition_text: str, condition_type: str, risk_level: RiskLevel, state: str, condition_types: Dict) -> List[Dict[str, Any]]:
    """Generate targeted mitigation strategies based on risk level and condition type"""
    if condition_type not in condition_types:
        return [{"strategy": "Seek legal advice for unrecognized condition", "priority": "high", "cost": "medium"}]
    
    base_strategies = condition_types[condition_type].get("mitigation_strategies", [])
    strategies = []
    
    for strategy in base_strategies:
        priority = "medium"
        cost = "low"
        
        # Adjust priority and cost based on risk level
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            priority = "high"
            if "pre-approval" in strategy or "broker" in strategy:
                cost = "medium"
        
        strategies.append({
            "strategy": strategy,
            "priority": priority,
            "estimated_cost": cost,
            "timeframe": estimate_strategy_timeframe(strategy, risk_level)
        })
    
    # Add risk-level specific strategies
    if risk_level == RiskLevel.CRITICAL:
        strategies.append({
            "strategy": "Seek immediate legal advice before proceeding",
            "priority": "critical",
            "estimated_cost": "high",
            "timeframe": "1-2 days"
        })
    
    return strategies


def calculate_condition_risk_score(risk_analysis: Dict, compliance_results: Dict) -> float:
    """Calculate numerical risk score for a condition (0-100)"""
    base_score = risk_analysis.get("risk_score", 50)
    
    # Adjust based on compliance
    compliance_adjustment = 0
    if compliance_results["status"] == "compliant":
        compliance_adjustment = -10
    elif compliance_results["status"] == "non-compliant":
        compliance_adjustment = +15
    
    final_score = base_score + compliance_adjustment
    return min(100, max(0, final_score))


def determine_condition_priority(risk_score: float, risk_level: RiskLevel) -> str:
    """Determine action priority for a condition"""
    if risk_level == RiskLevel.CRITICAL or risk_score >= 85:
        return "immediate"
    elif risk_level == RiskLevel.HIGH or risk_score >= 70:
        return "urgent"
    elif risk_level == RiskLevel.MEDIUM or risk_score >= 40:
        return "moderate"
    else:
        return "low"


def estimate_condition_cost_impact(condition_type: str, risk_level: RiskLevel) -> Dict[str, Any]:
    """Estimate potential financial impact of condition issues"""
    base_costs = {
        "finance": {"low": 500, "medium": 2000, "high": 10000, "critical": 50000},
        "building_pest": {"low": 1000, "medium": 5000, "high": 25000, "critical": 100000},
        "strata": {"low": 500, "medium": 3000, "high": 15000, "critical": 75000},
        "council": {"low": 1000, "medium": 5000, "high": 30000, "critical": 150000},
        "settlement": {"low": 500, "medium": 2000, "high": 10000, "critical": 50000},
        "vendor_disclosure": {"low": 2000, "medium": 10000, "high": 50000, "critical": 200000}
    }
    
    costs = base_costs.get(condition_type, {"low": 1000, "medium": 5000, "high": 20000, "critical": 100000})
    risk_key = risk_level.value
    
    return {
        "estimated_min": costs[risk_key],
        "estimated_max": costs[risk_key] * 2,
        "category": risk_key,
        "description": f"Potential {risk_key}-level cost impact for {condition_type} issues"
    }


def categorize_overall_risk(average_risk_score: float) -> str:
    """Categorize overall risk level"""
    if average_risk_score >= 80:
        return "critical"
    elif average_risk_score >= 60:
        return "high"
    elif average_risk_score >= 40:
        return "medium"
    else:
        return "low"


def generate_comprehensive_recommendations(analysis_results: List, state: str, average_risk_score: float) -> List[Dict[str, Any]]:
    """Generate comprehensive recommendations based on all conditions"""
    recommendations = []
    
    # High-priority recommendations
    critical_conditions = [r for r in analysis_results if r["risk_level"] in ["high", "critical"]]
    if critical_conditions:
        recommendations.append({
            "type": "immediate_action",
            "priority": "critical",
            "recommendation": f"Address {len(critical_conditions)} critical/high-risk conditions immediately",
            "details": [f"{c['type']}: {c['condition'][:100]}..." for c in critical_conditions[:3]]
        })
    
    # State-specific recommendations
    if state in ["NSW", "VIC", "QLD"]:
        recommendations.append({
            "type": "state_compliance",
            "priority": "high",
            "recommendation": f"Ensure all conditions comply with {state} property law requirements",
            "details": [f"Review {state}-specific cooling-off periods", f"Verify {state} disclosure requirements"]
        })
    
    # General recommendations based on risk score
    if average_risk_score >= 70:
        recommendations.append({
            "type": "professional_advice",
            "priority": "high",
            "recommendation": "Seek immediate legal and professional advice",
            "details": ["High overall risk score requires expert review", "Consider independent property advice"]
        })
    
    return recommendations


def generate_next_steps(analysis_results: List, critical_issues: List) -> List[Dict[str, Any]]:
    """Generate actionable next steps"""
    next_steps = []
    
    if critical_issues:
        next_steps.append({
            "step": "Address critical issues",
            "action": "Review and resolve all critical risk conditions before proceeding",
            "timeline": "Within 24-48 hours",
            "responsible": "Legal advisor/Buyer"
        })
    
    next_steps.extend([
        {
            "step": "Professional review",
            "action": "Have qualified professionals review identified conditions",
            "timeline": "Within 1 week", 
            "responsible": "Solicitor/Conveyancer"
        },
        {
            "step": "Compliance verification",
            "action": "Verify all conditions meet state legal requirements",
            "timeline": "Before contract signing",
            "responsible": "Legal team"
        }
    ])
    
    return next_steps


def generate_state_compliance_summary(analysis_results: List, state: str) -> Dict[str, Any]:
    """Generate state-specific compliance summary"""
    total_conditions = len(analysis_results)
    compliant = len([r for r in analysis_results if r["compliance_status"] == "compliant"])
    
    return {
        "state": state,
        "total_conditions": total_conditions,
        "compliant_conditions": compliant,
        "compliance_rate": (compliant / total_conditions * 100) if total_conditions > 0 else 0,
        "major_compliance_issues": [
            r["type"] for r in analysis_results 
            if r["compliance_status"] == "non-compliant"
        ]
    }


def calculate_overall_confidence(analysis_results: List) -> float:
    """Calculate overall confidence in the analysis"""
    if not analysis_results:
        return 0.0
    
    total_confidence = sum(r["confidence"] for r in analysis_results)
    return total_confidence / len(analysis_results)


def estimate_strategy_timeframe(strategy: str, risk_level: RiskLevel) -> str:
    """Estimate timeframe for implementing mitigation strategy"""
    if "immediate" in strategy or risk_level == RiskLevel.CRITICAL:
        return "1-2 days"
    elif "pre-approval" in strategy or "inspection" in strategy:
        return "1-2 weeks"
    elif "review" in strategy or "verify" in strategy:
        return "3-5 days"
    else:
        return "1 week"


def get_state_specific_notes_enhanced(condition_type: str, state: str) -> List[Dict[str, Any]]:
    """Enhanced state-specific notes with detailed requirements"""
    notes = []
    
    state_requirements = {
        "NSW": {
            "building_pest": [
                {"note": "Inspector must be licensed under NSW Home Building Act", "importance": "critical"},
                {"note": "Report must include both building and pest inspection", "importance": "high"}
            ],
            "finance": [
                {"note": "Finance clause must specify exact approval date", "importance": "high"},
                {"note": "Consider NSW property purchase process timelines", "importance": "medium"}
            ],
            "strata": [
                {"note": "Strata search must include by-laws and financial statements", "importance": "critical"},
                {"note": "Check for any special levies or major works planned", "importance": "high"}
            ]
        },
        "VIC": {
            "building_pest": [
                {"note": "Inspector must be registered with VBA", "importance": "critical"},
                {"note": "Consider thermal imaging for pest detection", "importance": "medium"}
            ],
            "vendor_disclosure": [
                {"note": "Vendor statement must comply with Sale of Land Act", "importance": "critical"},
                {"note": "Check for any planning overlays or restrictions", "importance": "high"}
            ]
        },
        "QLD": {
            "finance": [
                {"note": "Finance clause cannot be waived in QLD", "importance": "critical"},
                {"note": "Must allow minimum 14 days for finance approval", "importance": "high"}
            ],
            "building_pest": [
                {"note": "Pest inspection particularly important in QLD climate", "importance": "high"},
                {"note": "Consider flood risk and building compliance", "importance": "medium"}
            ]
        }
    }
    
    if state in state_requirements and condition_type in state_requirements[state]:
        notes = state_requirements[state][condition_type]
    
    return notes


def calculate_extraction_confidence(match, document_text: str) -> float:
    """Calculate confidence score for extracted terms"""
    # Simplified confidence calculation
    # Consider factors like position in document, surrounding context, etc.
    confidence = 0.7  # Base confidence
    
    # Boost confidence if found near relevant keywords
    context_window = 100
    start = max(0, match.start() - context_window)
    end = min(len(document_text), match.end() + context_window)
    context = document_text[start:end].lower()
    
    relevant_keywords = ["contract", "agreement", "purchase", "sale", "property"]
    keyword_boost = sum(0.05 for keyword in relevant_keywords if keyword in context)
    
    return min(1.0, confidence + keyword_boost)


def clean_extracted_value(term: str, value: str) -> Any:
    """Clean and convert extracted values to appropriate types"""
    if term in ["purchase_price", "deposit"]:
        # Clean currency values
        cleaned = re.sub(r'[,$\s]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return value
    
    return value.strip()


def get_state_specific_requirements(state: str) -> Dict[str, Any]:
    """Get state-specific contract requirements"""
    # Simplified requirements - would be expanded in production
    return {
        "mandatory_clauses": ["cooling_off", "finance", "building_pest"],
        "disclosure_requirements": ["vendor_statement", "contract_note"],
        "legal_references": f"{state} Property Law"
    }


def validate_terms_for_state(terms: Dict, requirements: Dict) -> Dict[str, Any]:
    """Validate extracted terms against state requirements"""
    # Add state-specific validation logic
    return terms


def extract_days_from_period(period_text: str) -> int:
    """Extract number of days from cooling-off period text"""
    match = re.search(r'(\d+)', str(period_text))
    return int(match.group(1)) if match else 0


@tool
def comprehensive_risk_scoring_system(contract_terms: Dict, state: str, user_profile: Dict = None) -> Dict[str, Any]:
    """Comprehensive risk scoring system for Australian property contracts"""
    
    # Initialize risk scoring components
    risk_components = {
        "financial_risk": 0.0,
        "legal_compliance_risk": 0.0,
        "market_risk": 0.0,
        "structural_risk": 0.0,
        "timeline_risk": 0.0
    }
    
    # Analyze financial risks
    purchase_price = contract_terms.get("purchase_price", 0)
    deposit = contract_terms.get("deposit", 0)
    
    # Financial risk assessment
    if purchase_price > 2000000:  # High-value property
        risk_components["financial_risk"] += 15
    elif purchase_price > 1000000:
        risk_components["financial_risk"] += 10
    elif purchase_price > 500000:
        risk_components["financial_risk"] += 5
    
    # Deposit risk
    if deposit and purchase_price:
        deposit_ratio = deposit / purchase_price
        if deposit_ratio < 0.05:  # Less than 5% deposit
            risk_components["financial_risk"] += 20
        elif deposit_ratio < 0.10:  # Less than 10% deposit  
            risk_components["financial_risk"] += 10
        elif deposit_ratio < 0.20:  # Less than 20% deposit
            risk_components["financial_risk"] += 5
    
    # Legal compliance risk
    cooling_off_validation = validate_cooling_off_period(contract_terms, state)
    if not cooling_off_validation.get("compliant", False):
        risk_components["legal_compliance_risk"] += 25
    
    # Special conditions risk
    special_conditions_analysis = analyze_special_conditions(contract_terms, state)
    conditions_risk_score = special_conditions_analysis.get("overall_risk_score", 50)
    risk_components["structural_risk"] += conditions_risk_score * 0.5  # Scale to component
    
    # Timeline risk assessment
    settlement_date = contract_terms.get("settlement_date")
    if settlement_date:
        # Parse settlement date and assess timeline risk
        try:
            from datetime import datetime, timedelta
            # Simplified date parsing - would need more robust parsing in production
            today = datetime.now()
            # Assuming 6-8 weeks is optimal settlement period
            optimal_min = today + timedelta(weeks=6)
            optimal_max = today + timedelta(weeks=8)
            
            # If settlement is too soon (< 4 weeks)
            if settlement_date and "week" in str(settlement_date).lower():
                risk_components["timeline_risk"] += 15
        except:
            risk_components["timeline_risk"] += 10  # Unknown timeline = risk
    
    # Market risk factors (would integrate with property data in full implementation)
    market_factors = assess_market_risk_factors(contract_terms, state)
    risk_components["market_risk"] += market_factors["risk_score"]
    
    # Calculate overall risk score (weighted average)
    weights = {
        "financial_risk": 0.25,
        "legal_compliance_risk": 0.30,
        "market_risk": 0.20,
        "structural_risk": 0.15,
        "timeline_risk": 0.10
    }
    
    overall_risk_score = sum(
        risk_components[component] * weights[component] 
        for component in risk_components
    )
    
    # Risk categorization
    if overall_risk_score >= 80:
        risk_category = "CRITICAL"
        recommendation = "DO NOT PROCEED without immediate legal intervention"
    elif overall_risk_score >= 60:
        risk_category = "HIGH"
        recommendation = "Proceed with extreme caution - seek multiple professional opinions"
    elif overall_risk_score >= 40:
        risk_category = "MEDIUM"
        recommendation = "Standard due diligence required - professional advice recommended"
    elif overall_risk_score >= 20:
        risk_category = "LOW-MEDIUM"
        recommendation = "Minor risks identified - basic professional review advised"
    else:
        risk_category = "LOW"
        recommendation = "Low risk transaction - standard precautions apply"
    
    # Generate detailed risk breakdown
    risk_breakdown = []
    for component, score in risk_components.items():
        if score > 20:
            risk_breakdown.append({
                "component": component.replace("_", " ").title(),
                "score": round(score, 1),
                "level": "High" if score > 30 else "Medium",
                "description": get_risk_component_description(component, score)
            })
    
    # User-specific recommendations based on profile
    user_recommendations = generate_user_specific_recommendations(
        user_profile, overall_risk_score, risk_components, state
    )
    
    return {
        "overall_risk_score": round(overall_risk_score, 2),
        "risk_category": risk_category,
        "primary_recommendation": recommendation,
        "risk_components": {k: round(v, 2) for k, v in risk_components.items()},
        "risk_breakdown": risk_breakdown,
        "critical_factors": [item for item in risk_breakdown if item["level"] == "High"],
        "user_specific_recommendations": user_recommendations,
        "confidence_level": calculate_scoring_confidence(contract_terms, risk_components),
        "next_review_date": suggest_review_timeline(risk_category),
        "professional_advice_required": overall_risk_score >= 40,
        "estimated_professional_cost": estimate_professional_advice_cost(overall_risk_score, state)
    }


def assess_market_risk_factors(contract_terms: Dict, state: str) -> Dict[str, Any]:
    """Assess market-related risk factors"""
    risk_score = 0
    factors = []
    
    # Property type risk
    property_address = contract_terms.get("property_address", "")
    if "apartment" in property_address.lower() or "unit" in property_address.lower():
        risk_score += 5
        factors.append("Apartment/unit properties have higher market volatility")
    
    # Location-based risk (simplified - would use actual market data)
    high_risk_areas = ["remote", "mining", "industrial"]
    for area_type in high_risk_areas:
        if area_type in property_address.lower():
            risk_score += 10
            factors.append(f"Property in {area_type} area has elevated market risk")
    
    # State-specific market risks
    state_risks = {
        "WA": 5,  # Mining-dependent economy
        "NT": 8,  # Smaller market, higher volatility
        "TAS": 6,  # Limited market size
        "ACT": 3,  # Government-dependent but stable
        "NSW": 2,  # Large, stable market
        "VIC": 2,  # Large, stable market
        "QLD": 4,  # Tourism and mining dependent
        "SA": 5   # Smaller market
    }
    
    state_risk = state_risks.get(state, 5)
    risk_score += state_risk
    factors.append(f"{state} market risk factor: {state_risk}/10")
    
    return {
        "risk_score": min(30, risk_score),  # Cap at 30
        "factors": factors
    }


def get_risk_component_description(component: str, score: float) -> str:
    """Get description for risk component"""
    descriptions = {
        "financial_risk": {
            "high": "Significant financial exposure due to high property value or low deposit",
            "medium": "Moderate financial risk factors present",
            "low": "Financial risk is within acceptable parameters"
        },
        "legal_compliance_risk": {
            "high": "Major legal compliance issues that could void contract",
            "medium": "Some legal requirements may not be fully met",
            "low": "Legal compliance appears satisfactory"
        },
        "market_risk": {
            "high": "Property market factors pose significant risk to value",
            "medium": "Some market volatility factors present",
            "low": "Market conditions appear stable"
        },
        "structural_risk": {
            "high": "Contract conditions pose significant structural risks",
            "medium": "Some contract conditions require attention", 
            "low": "Contract structure appears sound"
        },
        "timeline_risk": {
            "high": "Settlement timeline poses significant challenges",
            "medium": "Timeline may require careful management",
            "low": "Settlement timeline appears reasonable"
        }
    }
    
    level = "high" if score > 30 else "medium" if score > 15 else "low"
    return descriptions.get(component, {}).get(level, "Risk assessment unavailable")


def generate_user_specific_recommendations(user_profile: Dict, risk_score: float, risk_components: Dict, state: str) -> List[Dict[str, Any]]:
    """Generate recommendations based on user profile"""
    if not user_profile:
        return [{"recommendation": "Consider your personal risk tolerance and financial situation", "priority": "medium"}]
    
    recommendations = []
    user_type = user_profile.get("user_type", "buyer")
    experience_level = user_profile.get("experience_level", "novice")
    
    # Experience-based recommendations
    if experience_level == "novice" and risk_score > 40:
        recommendations.append({
            "recommendation": "As a first-time buyer, consider engaging a buyer's advocate for this higher-risk transaction",
            "priority": "high",
            "cost_estimate": "2000-5000"
        })
    
    # User type specific recommendations
    if user_type == "investor":
        if risk_components.get("market_risk", 0) > 20:
            recommendations.append({
                "recommendation": "High market risk detected - consider rental yield analysis and exit strategy",
                "priority": "high",
                "cost_estimate": "1000-3000"
            })
    elif user_type == "buyer":
        if risk_components.get("financial_risk", 0) > 25:
            recommendations.append({
                "recommendation": "Consider mortgage broker consultation given financial risk factors",
                "priority": "medium",
                "cost_estimate": "500-1500"
            })
    
    return recommendations


def calculate_scoring_confidence(contract_terms: Dict, risk_components: Dict) -> float:
    """Calculate confidence in risk scoring"""
    # Base confidence
    confidence = 0.6
    
    # Boost confidence based on data availability
    if contract_terms.get("purchase_price"):
        confidence += 0.1
    if contract_terms.get("deposit"):
        confidence += 0.1
    if contract_terms.get("settlement_date"):
        confidence += 0.1
    if contract_terms.get("special_conditions"):
        confidence += 0.1
    
    return min(0.95, confidence)


def suggest_review_timeline(risk_category: str) -> str:
    """Suggest when to review the risk assessment"""
    timelines = {
        "CRITICAL": "Daily review required",
        "HIGH": "Review every 2-3 days",
        "MEDIUM": "Weekly review recommended",
        "LOW-MEDIUM": "Review in 2 weeks",
        "LOW": "Review before settlement"
    }
    return timelines.get(risk_category, "Review before settlement")


def estimate_professional_advice_cost(risk_score: float, state: str) -> Dict[str, Any]:
    """Estimate cost of professional advice based on risk level"""
    base_costs = {
        "NSW": {"solicitor": 1500, "building_inspector": 600, "buyer_advocate": 3000},
        "VIC": {"solicitor": 1400, "building_inspector": 550, "buyer_advocate": 2800},
        "QLD": {"solicitor": 1300, "building_inspector": 500, "buyer_advocate": 2500},
        "SA": {"solicitor": 1200, "building_inspector": 450, "buyer_advocate": 2200},
        "WA": {"solicitor": 1350, "building_inspector": 520, "buyer_advocate": 2600},
        "TAS": {"solicitor": 1100, "building_inspector": 400, "buyer_advocate": 2000},
        "NT": {"solicitor": 1250, "building_inspector": 480, "buyer_advocate": 2300},
        "ACT": {"solicitor": 1450, "building_inspector": 580, "buyer_advocate": 2900}
    }
    
    state_costs = base_costs.get(state, base_costs["NSW"])
    
    # Adjust costs based on risk level
    multiplier = 1.0
    if risk_score >= 80:
        multiplier = 2.0  # Critical risk requires comprehensive advice
        recommended_services = ["solicitor", "building_inspector", "buyer_advocate", "financial_advisor"]
    elif risk_score >= 60:
        multiplier = 1.5  # High risk requires multiple professionals
        recommended_services = ["solicitor", "building_inspector", "buyer_advocate"]
    elif risk_score >= 40:
        multiplier = 1.2  # Medium risk requires standard professional advice
        recommended_services = ["solicitor", "building_inspector"]
    else:
        recommended_services = ["solicitor"]
    
    estimated_costs = {}
    total_cost = 0
    
    for service in recommended_services:
        cost = state_costs.get(service, 1000) * multiplier
        estimated_costs[service] = round(cost)
        total_cost += cost
    
    return {
        "recommended_services": recommended_services,
        "individual_costs": estimated_costs,
        "total_estimated_cost": round(total_cost),
        "cost_range": f"${round(total_cost * 0.8)}-${round(total_cost * 1.3)}",
        "justification": f"Professional advice recommended for {risk_score:.1f}/100 risk score"
    }


# Legacy functions removed - replaced with enhanced versions above