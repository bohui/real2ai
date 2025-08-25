"""
Cooling-off period compliance validation for Australian property contracts
"""

from typing import Dict, Any
from langchain.tools import tool
import re



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
    contract_days = _extract_days_from_period(contract_period)
    required_days = rule["days"]
    
    if contract_days >= required_days:
        validation_result["compliant"] = True
        if contract_days > required_days:
            validation_result["warnings"].append(
                f"Contract provides {contract_days} days, more than required {required_days} days"
            )
    else:
        validation_result["warnings"].append(
            f"Contract provides {contract_days} days, less than required {required_days} days"
        )
        validation_result["recommendations"].append(
            f"Increase cooling-off period to at least {required_days} {rule['type']}"
        )
    
    # Check for exclusions
    if "exclusions" in rule:
        for exclusion in rule["exclusions"]:
            if _check_exclusion_applies(contract_terms, exclusion):
                validation_result["warnings"].append(
                    f"Cooling-off exclusion may apply: {exclusion}"
                )
    
    return validation_result


def _extract_days_from_period(period_text: str) -> int:
    """Extract number of days from period text"""
    if not period_text:
        return 0
    
    # Look for number patterns
    match = re.search(r'(\d+)', str(period_text))
    return int(match.group(1)) if match else 0


def _check_exclusion_applies(contract_terms: Dict, exclusion: str) -> bool:
    """Check if a cooling-off exclusion applies"""
    
    if exclusion == "auction":
        # Check if this was an auction sale
        sale_method = contract_terms.get("sale_method", "").lower()
        return "auction" in sale_method
    
    elif exclusion == "investment_property_over_1m":
        purchase_price = contract_terms.get("purchase_price", 0)
        property_type = contract_terms.get("property_type", "").lower()
        return purchase_price > 1000000 and "investment" in property_type
    
    elif exclusion == "contract_race":
        # Check for contract race conditions
        special_conditions = contract_terms.get("special_conditions", [])
        if isinstance(special_conditions, list):
            return any("race" in str(condition).lower() for condition in special_conditions)
    
    return False