"""
Australian contract terms extraction tools
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
import re

from app.schema.enums import (
    ContractType,
    PurchaseMethod,
    UseCategory,
)


def infer_contract_taxonomy_core(
    document_text: str, user_contract_type: str
) -> Dict[str, Any]:
    """
    Pure Python implementation used internally to avoid LangChain callback plumbing.
    """
    result = {
        "contract_type": user_contract_type,
        "purchase_method": None,
        "use_category": None,
        "confidence_scores": {},
        "inference_evidence": {},
    }

    # Convert string to enum for validation
    try:
        contract_type_enum = ContractType(user_contract_type)
    except ValueError:
        result["error"] = f"Invalid contract_type: {user_contract_type}"
        return result

    # Infer purchase_method for purchase agreements
    if contract_type_enum == ContractType.PURCHASE_AGREEMENT:
        purchase_method, confidence, evidence = _infer_purchase_method(document_text)
        result["purchase_method"] = purchase_method
        result["confidence_scores"]["purchase_method"] = confidence
        result["inference_evidence"]["purchase_method"] = evidence

        # Also infer use_category for purchase agreements
        use_category, use_confidence, use_evidence = _infer_use_category(document_text)
        if use_category:
            result["use_category"] = use_category
            result["confidence_scores"]["use_category"] = use_confidence
            result["inference_evidence"]["use_category"] = use_evidence

    # Infer use_category for lease agreements (no purchase_method)
    elif contract_type_enum == ContractType.LEASE_AGREEMENT:
        use_category, confidence, evidence = _infer_use_category(document_text)
        if use_category:
            result["use_category"] = use_category
            result["confidence_scores"]["use_category"] = confidence
            result["inference_evidence"]["use_category"] = evidence

    # Option to purchase and unknown types need no inference
    return result


@tool
def infer_contract_taxonomy(
    document_text: str, user_contract_type: str
) -> Dict[str, Any]:
    """
    LangChain Tool wrapper delegating to the pure implementation.
    """
    return infer_contract_taxonomy_core(document_text, user_contract_type)


def _infer_purchase_method(
    document_text: str,
) -> tuple[Optional[str], float, List[str]]:
    """Infer purchase method from document text with confidence scoring"""

    # Purchase method detection patterns
    patterns = {
        PurchaseMethod.OFF_PLAN: [
            r"off[\s\-]?the[\s\-]?plan",
            r"proposed\s+development",
            r"future\s+construction",
            r"plan\s+of\s+subdivision",
            r"building\s+works\s+to\s+be\s+commenced",
            r"completion\s+certificate",
            r"occupation\s+certificate",
        ],
        PurchaseMethod.AUCTION: [
            r"auction\s+sale",
            r"highest\s+bidder",
            r"hammer\s+falls",
            r"auctioneer",
            r"reserve\s+price",
            r"bidding\s+process",
            r"auction\s+conditions",
        ],
        PurchaseMethod.PRIVATE_TREATY: [
            r"private\s+treaty",
            r"by\s+private\s+negotiation",
            r"direct\s+negotiation",
            r"private\s+sale",
        ],
        PurchaseMethod.TENDER: [
            r"tender\s+process",
            r"call\s+for\s+tenders",
            r"submission\s+of\s+tender",
            r"tender\s+documents",
            r"highest\s+conforming\s+tender",
        ],
        PurchaseMethod.EXPRESSION_OF_INTEREST: [
            r"expression\s+of\s+interest",
            r"EOI\s+process",
            r"invitation\s+to\s+treat",
            r"preliminary\s+offer",
        ],
    }

    best_method = None
    highest_confidence = 0.0
    evidence_found = []

    for method, method_patterns in patterns.items():
        method_confidence = 0.0
        method_evidence = []

        for pattern in method_patterns:
            matches = list(re.finditer(pattern, document_text, re.IGNORECASE))
            if matches:
                # Weight by number of matches and pattern specificity
                # Start with higher base confidence for clear pattern matches
                pattern_confidence = min(0.95, 0.6 + (len(matches) * 0.15))
                method_confidence = max(method_confidence, pattern_confidence)
                method_evidence.extend([match.group(0) for match in matches])

        if method_confidence > highest_confidence:
            highest_confidence = method_confidence
            best_method = method.value
            evidence_found = method_evidence

    # Default to standard if no specific method detected but sufficient generic purchase language
    if not best_method:
        standard_patterns = [
            r"contract\s+of\s+sale",
            r"purchase\s+agreement",
            r"sale\s+agreement",
            r"vendor\s+and\s+purchaser",
        ]

        standard_evidence = []
        for pattern in standard_patterns:
            matches = list(re.finditer(pattern, document_text, re.IGNORECASE))
            if matches:
                standard_evidence.extend([match.group(0) for match in matches])

        if standard_evidence:
            best_method = PurchaseMethod.STANDARD.value
            highest_confidence = 0.7
            evidence_found = standard_evidence

    return best_method, highest_confidence, evidence_found


def _infer_use_category(document_text: str) -> tuple[Optional[str], float, List[str]]:
    """Infer property use category from document text with confidence scoring

    Applies to both purchase agreements and lease agreements.
    """

    # Use category detection patterns
    patterns = {
        UseCategory.RESIDENTIAL: [
            r"residential\s+(?:lease|agreement|premises|property|use)",
            r"dwelling\s+(?:rental|property|use)",
            r"residential\s+tenancy",
            r"house\s+(?:rental|purchase|sale)",
            r"apartment\s+(?:lease|purchase|sale)",
            r"unit\s+(?:rental|purchase|sale)",
            r"home\s+(?:purchase|sale)",
            r"private\s+residence",
            r"family\s+home",
        ],
        UseCategory.COMMERCIAL: [
            r"commercial\s+(?:lease|agreement|premises|property|use)",
            r"business\s+premises",
            r"office\s+(?:space|premises|building)",
            r"commercial\s+tenancy",
            r"commercial\s+rental",
            r"business\s+(?:purchase|sale)",
            r"office\s+(?:purchase|sale)",
            r"commercial\s+building",
        ],
        UseCategory.INDUSTRIAL: [
            r"industrial\s+(?:lease|agreement|premises|property|use)",
            r"warehouse\s+(?:rental|lease|purchase|sale)",
            r"factory\s+(?:lease|purchase|sale)",
            r"industrial\s+premises",
            r"manufacturing\s+facility",
            r"storage\s+facility",
            r"industrial\s+building",
            r"logistics\s+(?:facility|premises)",
        ],
        UseCategory.RETAIL: [
            r"retail\s+(?:lease|agreement|premises|property|use)",
            r"shop\s+(?:lease|purchase|sale)",
            r"retail\s+premises",
            r"shopping\s+centre",
            r"retail\s+tenancy",
            r"store\s+(?:rental|lease|purchase|sale)",
            r"retail\s+space",
            r"showroom\s+(?:lease|purchase|sale)",
        ],
    }

    best_category = None
    highest_confidence = 0.0
    evidence_found = []

    for category, category_patterns in patterns.items():
        category_confidence = 0.0
        category_evidence = []

        for pattern in category_patterns:
            matches = list(re.finditer(pattern, document_text, re.IGNORECASE))
            if matches:
                # Weight by number of matches and pattern specificity
                # Start with higher base confidence for clear pattern matches
                pattern_confidence = min(0.95, 0.65 + (len(matches) * 0.15))
                category_confidence = max(category_confidence, pattern_confidence)
                category_evidence.extend([match.group(0) for match in matches])

        if category_confidence > highest_confidence:
            highest_confidence = category_confidence
            best_category = category.value
            evidence_found = category_evidence

    return best_category, highest_confidence, evidence_found


@tool
def extract_australian_contract_terms(document_text: str, state: str) -> Dict[str, Any]:
    """Extract key terms from Australian property contract with state-specific rules"""

    # Australian-specific patterns
    patterns = {
        "purchase_price": [
            r"purchase\s+price[:\s]+\$?([\d,]+\.?\d*)",
            r"consideration[:\s]+\$?([\d,]+\.?\d*)",
            r"total\s+amount[:\s]+\$?([\d,]+\.?\d*)",
        ],
        "deposit": [
            r"deposit[:\s]+\$?([\d,]+\.?\d*)",
            r"initial\s+payment[:\s]+\$?([\d,]+\.?\d*)",
        ],
        "settlement_date": [
            r"settlement\s+date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"completion\s+date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ],
        "cooling_off": [
            r"cooling[\s\-]?off\s+period[:\s]+(\d+)\s+days?",
            r"rescission\s+period[:\s]+(\d+)\s+days?",
        ],
        "property_address": [
            r"property[:\s]+(.+?)(?=\n|\.|,)",
            r"land[:\s]+(.+?)(?=\n|\.|,)",
            r"premises[:\s]+(.+?)(?=\n|\.|,)",
        ],
    }

    extracted_terms = {}
    confidence_scores = {}

    for term, term_patterns in patterns.items():
        best_match = None
        highest_confidence = 0.0

        for pattern in term_patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                confidence = _calculate_extraction_confidence(match, document_text)
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = match.group(1).strip()

        if best_match and highest_confidence > 0.5:
            extracted_terms[term] = _clean_extracted_value(term, best_match)
            confidence_scores[term] = highest_confidence

    # State-specific validation
    state_requirements = _get_state_specific_requirements(state)
    validated_terms = _validate_terms_for_state(extracted_terms, state_requirements)

    return {
        "terms": validated_terms,
        "confidence_scores": confidence_scores,
        "state_requirements": state_requirements,
        "overall_confidence": (
            sum(confidence_scores.values()) / len(confidence_scores)
            if confidence_scores
            else 0.0
        ),
    }


def _calculate_extraction_confidence(match, document_text: str) -> float:
    """Calculate confidence score for text extraction match"""
    base_confidence = 0.7

    # Boost confidence if surrounded by structured text
    start_pos = max(0, match.start() - 50)
    end_pos = min(len(document_text), match.end() + 50)
    context = document_text[start_pos:end_pos]

    # Look for structured indicators
    if any(
        indicator in context.lower()
        for indicator in [":", "$", "aud", "section", "clause"]
    ):
        base_confidence += 0.2

    # Check for specific formatting
    matched_text = match.group(0)
    if "$" in matched_text or "AUD" in matched_text.upper():
        base_confidence += 0.1

    return min(1.0, base_confidence)


def _clean_extracted_value(term: str, value: str) -> Any:
    """Clean and convert extracted values to appropriate types"""
    value = value.strip()

    if term in ["purchase_price", "deposit"]:
        # Clean monetary values
        cleaned = re.sub(r"[^\d.]", "", value)
        try:
            return float(cleaned)
        except ValueError:
            return value

    return value


def _get_state_specific_requirements(state: str) -> Dict[str, Any]:
    """Get state-specific contract requirements"""
    requirements = {
        "NSW": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "VIC": {
            "cooling_off_days": 3,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "QLD": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "WA": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "SA": {
            "cooling_off_days": 2,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "TAS": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "NT": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
        "ACT": {
            "cooling_off_days": 5,
            "mandatory_terms": ["purchase_price", "deposit", "settlement_date"],
        },
    }
    return requirements.get(state, requirements["NSW"])


def _validate_terms_for_state(terms: Dict, requirements: Dict) -> Dict[str, Any]:
    """Validate extracted terms against state requirements"""
    validated = terms.copy()
    issues = []

    for mandatory_term in requirements.get("mandatory_terms", []):
        if mandatory_term not in terms:
            issues.append(f"Missing mandatory term: {mandatory_term}")

    validated["validation_issues"] = issues
    return validated
