"""
Australian contract terms extraction tools
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
import re

from backend.app.schema.enums import AustralianState, RiskLevel


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
        "overall_confidence": sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
    }


def _calculate_extraction_confidence(match, document_text: str) -> float:
    """Calculate confidence score for text extraction match"""
    base_confidence = 0.7
    
    # Boost confidence if surrounded by structured text
    start_pos = max(0, match.start() - 50)
    end_pos = min(len(document_text), match.end() + 50)
    context = document_text[start_pos:end_pos]
    
    # Look for structured indicators
    if any(indicator in context.lower() for indicator in [':', '$', 'aud', 'section', 'clause']):
        base_confidence += 0.2
    
    # Check for specific formatting
    matched_text = match.group(0)
    if '$' in matched_text or 'AUD' in matched_text.upper():
        base_confidence += 0.1
    
    return min(1.0, base_confidence)


def _clean_extracted_value(term: str, value: str) -> Any:
    """Clean and convert extracted values to appropriate types"""
    value = value.strip()
    
    if term in ['purchase_price', 'deposit']:
        # Clean monetary values
        cleaned = re.sub(r'[^\d.]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return value
    
    return value


def _get_state_specific_requirements(state: str) -> Dict[str, Any]:
    """Get state-specific contract requirements"""
    requirements = {
        "NSW": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "VIC": {"cooling_off_days": 3, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "QLD": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "WA": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "SA": {"cooling_off_days": 2, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "TAS": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "NT": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
        "ACT": {"cooling_off_days": 5, "mandatory_terms": ["purchase_price", "deposit", "settlement_date"]},
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