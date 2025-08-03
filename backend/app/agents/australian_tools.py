"""
Australian-specific tools for Real2.AI contract analysis
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
from datetime import datetime, timedelta
import re
from decimal import Decimal

from app.models.contract_state import AustralianState, RiskLevel, StampDutyCalculation


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
def analyze_special_conditions(contract_terms: Dict, state: str) -> List[Dict[str, Any]]:
    """Analyze Australian-specific special conditions and risks"""
    
    conditions = contract_terms.get("special_conditions", [])
    analysis_results = []
    
    # Common Australian special conditions
    condition_types = {
        "finance": {
            "keywords": ["finance", "loan", "mortgage", "bank approval"],
            "risk_indicators": ["subject to", "conditional upon"],
            "australian_requirements": "Must specify exact date and lender"
        },
        "building_pest": {
            "keywords": ["building", "pest", "inspection", "structural"],
            "risk_indicators": ["satisfactory", "subject to"],
            "australian_requirements": "Licensed inspector required in most states"
        },
        "strata": {
            "keywords": ["strata", "body corporate", "owners corporation"],
            "risk_indicators": ["financial", "minutes", "by-laws"],
            "australian_requirements": "Strata search must be current (usually 30 days)"
        },
        "council": {
            "keywords": ["council", "rates", "planning", "zoning"],
            "risk_indicators": ["outstanding", "approvals", "development"],
            "australian_requirements": "Council certificate required"
        },
        "settlement": {
            "keywords": ["settlement", "completion", "possession"],
            "risk_indicators": ["time of essence", "delay"],
            "australian_requirements": "Must align with state requirements"
        }
    }
    
    for condition in conditions:
        condition_text = condition.lower() if isinstance(condition, str) else str(condition).lower()
        
        # Classify condition type
        condition_type = "other"
        for ctype, details in condition_types.items():
            if any(keyword in condition_text for keyword in details["keywords"]):
                condition_type = ctype
                break
        
        # Assess risk level
        risk_level = assess_condition_risk(condition_text, condition_type, state)
        
        # Generate recommendations
        recommendations = generate_condition_recommendations(
            condition, condition_type, state
        )
        
        analysis_results.append({
            "condition": condition,
            "type": condition_type,
            "risk_level": risk_level.value,
            "recommendations": recommendations,
            "state_specific_notes": get_state_specific_notes(condition_type, state),
            "compliance_requirements": condition_types.get(condition_type, {}).get("australian_requirements", ""),
            "confidence": calculate_condition_confidence(condition_text, condition_type)
        })
    
    return analysis_results


# Helper functions

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


def assess_condition_risk(condition_text: str, condition_type: str, state: str) -> RiskLevel:
    """Assess risk level of a special condition"""
    # Simplified risk assessment
    high_risk_indicators = ["subject to", "conditional", "satisfactory to purchaser"]
    
    if any(indicator in condition_text for indicator in high_risk_indicators):
        return RiskLevel.HIGH
    
    return RiskLevel.MEDIUM


def generate_condition_recommendations(condition: str, condition_type: str, state: str) -> List[str]:
    """Generate recommendations for special conditions"""
    recommendations = []
    
    if condition_type == "finance":
        recommendations.append("Ensure finance approval deadline is realistic")
        recommendations.append("Consider pre-approval before signing")
    
    elif condition_type == "building_pest":
        recommendations.append("Use qualified, licensed inspector")
        recommendations.append("Allow sufficient time for inspection")
    
    return recommendations


def get_state_specific_notes(condition_type: str, state: str) -> List[str]:
    """Get state-specific notes for condition types"""
    notes = []
    
    if condition_type == "building_pest" and state in ["NSW", "VIC"]:
        notes.append("Inspector must be licensed in this state")
    
    if condition_type == "strata" and state == "NSW":
        notes.append("Strata search must include by-laws and financial statements")
    
    return notes


def calculate_condition_confidence(condition_text: str, condition_type: str) -> float:
    """Calculate confidence in condition classification"""
    # Simplified confidence calculation
    return 0.8 if condition_type != "other" else 0.5