"""
Contract terms completeness validation
"""

from typing import Dict, List, Any
from langchain.tools import tool

from app.prompts.schema.workflow_outputs import ContractTermsValidationOutput


@tool
def validate_contract_terms_completeness(
    contract_terms: Dict[str, Any],
    australian_state: str,
    contract_type: str = "purchase_agreement",
) -> ContractTermsValidationOutput:
    """
    Validate completeness of extracted contract terms against state requirements

    Args:
        contract_terms: Extracted contract terms
        australian_state: Australian state for compliance requirements
        contract_type: Type of contract being validated

    Returns:
        ContractTermsValidationOutput with validation results
    """

    # Get mandatory terms for contract type and state
    mandatory_terms = _get_mandatory_terms(contract_type, australian_state)

    missing_terms: List[str] = []
    incomplete_terms: List[str] = []
    valid_terms: List[str] = []

    for term_name, requirements in mandatory_terms.items():
        term_value = contract_terms.get(term_name)

        if term_value is None:
            missing_terms.append(term_name)
        elif not _validate_term_value(term_name, term_value, requirements):
            incomplete_terms.append(
                f"{term_name}: {requirements.get('validation_message', 'Invalid value format')}"
            )
        else:
            valid_terms.append(term_name)

    # Calculate completeness score
    total_terms = len(mandatory_terms)
    valid_count = len(valid_terms)
    completeness_score = valid_count / total_terms if total_terms > 0 else 0.0

    # Get state-specific validation
    state_validation = _get_state_specific_validation(australian_state, contract_terms)

    # Generate recommendations
    recommendations = []
    if missing_terms:
        recommendations.append(f"Extract missing terms: {', '.join(missing_terms)}")
    if incomplete_terms:
        recommendations.append("Review and correct incomplete term values")
    if completeness_score < 0.8:
        recommendations.append(
            "Overall term completeness is below acceptable threshold"
        )

    # Build terms_validated mapping
    terms_validated = {name: name in valid_terms for name in mandatory_terms.keys()}

    # Derive validation confidence from completeness
    validation_confidence = completeness_score

    return ContractTermsValidationOutput(
        terms_validated=terms_validated,
        missing_mandatory_terms=missing_terms,
        incomplete_terms=incomplete_terms,
        validation_confidence=validation_confidence,
        state_specific_requirements={"issues": state_validation.get("issues", [])},
        recommendations=recommendations,
        australian_state=australian_state or "NSW",
    )


def _get_mandatory_terms(contract_type: str, state: str) -> Dict[str, Dict[str, Any]]:
    """Get mandatory terms for contract type and state"""

    base_terms = {
        "purchase_price": {
            "type": "float",
            "min_value": 1000.0,
            "validation_message": "Purchase price must be a positive number above $1,000",
        },
        "deposit_amount": {
            "type": "float",
            "min_value": 0.0,
            "validation_message": "Deposit amount must be a non-negative number",
        },
        "settlement_date": {
            "type": "string",
            "pattern": r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}",
            "validation_message": "Settlement date must be in date format (DD/MM/YYYY or similar)",
        },
        "property_address": {
            "type": "string",
            "min_length": 10,
            "validation_message": "Property address must be clearly specified",
        },
    }

    # State-specific additions
    if state == "NSW":
        base_terms["section_149_certificate"] = {
            "type": "string",
            "validation_message": "Section 149 certificate reference required for NSW",
        }
    elif state == "VIC":
        base_terms["section_32_statement"] = {
            "type": "string",
            "validation_message": "Section 32 statement reference required for VIC",
        }
    elif state == "QLD":
        base_terms["disclosure_statement"] = {
            "type": "string",
            "validation_message": "Disclosure statement reference required for QLD",
        }

    return base_terms


def _validate_term_value(
    term_name: str, value: Any, requirements: Dict[str, Any]
) -> bool:
    """Validate a term value against requirements"""

    if value is None:
        return False

    # Type validation
    expected_type = requirements.get("type", "string")
    if expected_type == "float":
        try:
            float_value = float(value)
            min_value = requirements.get("min_value")
            if min_value is not None and float_value < min_value:
                return False
        except (ValueError, TypeError):
            return False

    elif expected_type == "string":
        str_value = str(value).strip()
        min_length = requirements.get("min_length", 1)
        if len(str_value) < min_length:
            return False

        pattern = requirements.get("pattern")
        if pattern:
            import re

            if not re.search(pattern, str_value):
                return False

    return True


def _get_state_specific_validation(
    state: str, contract_terms: Dict[str, Any]
) -> Dict[str, Any]:
    """Get state-specific validation requirements and results"""

    issues = []

    # NSW specific validations
    if state == "NSW":
        purchase_price = contract_terms.get("purchase_price", 0)
        if purchase_price > 1000000:
            if not contract_terms.get("foreign_buyer_declaration"):
                issues.append(
                    "Foreign buyer declaration may be required for purchases over $1M"
                )

    # VIC specific validations
    elif state == "VIC":
        if contract_terms.get("property_type") == "apartment":
            if not contract_terms.get("owners_corporation_certificate"):
                issues.append(
                    "Owners corporation certificate required for apartment purchases"
                )

    # QLD specific validations
    elif state == "QLD":
        cooling_off = contract_terms.get("cooling_off_period")
        if cooling_off and "waived" in str(cooling_off).lower():
            issues.append(
                "Cooling-off period waiver requires special consideration in QLD"
            )

    return {"issues": issues}
