"""
Australian contract template identification tools
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
import re

from backend.app.schema.enums import AustralianState


@tool
def identify_contract_template_type(document_text: str, state: str) -> Dict[str, Any]:
    """Identify the type of Australian contract template and state-specific requirements"""
    
    # Template identification patterns
    template_patterns = {
        "REIV": [
            r"real\s+estate\s+institute\s+of\s+victoria",
            r"reiv\s+contract",
            r"standard\s+sale\s+of\s+land",
            r"section\s+32\s+statement"
        ],
        "REI_NSW": [
            r"real\s+estate\s+institute\s+of\s+nsw",
            r"rei\s+nsw",
            r"standard\s+contract\s+for\s+sale\s+of\s+land",
            r"conveyancing\s+act.*nsw"
        ],
        "REIQ": [
            r"real\s+estate\s+institute\s+of\s+queensland",
            r"reiq\s+contract",
            r"standard\s+sale\s+contract",
            r"property\s+law\s+act.*qld"
        ],
        "REIWA": [
            r"real\s+estate\s+institute\s+of\s+western\s+australia",
            r"reiwa\s+contract",
            r"offer\s+and\s+acceptance",
            r"settlement\s+agents\s+act.*wa"
        ],
        "GENERIC": [
            r"sale\s+of\s+land\s+contract",
            r"property\s+purchase\s+agreement",
            r"real\s+estate\s+contract",
            r"vendor\s+and\s+purchaser"
        ]
    }
    
    identified_templates = []
    confidence_scores = {}
    
    document_lower = document_text.lower()
    
    for template_type, patterns in template_patterns.items():
        matches = 0
        total_patterns = len(patterns)
        
        for pattern in patterns:
            if re.search(pattern, document_lower, re.IGNORECASE):
                matches += 1
        
        if matches > 0:
            confidence = matches / total_patterns
            confidence_scores[template_type] = confidence
            identified_templates.append({
                "template_type": template_type,
                "confidence": confidence,
                "matches": matches,
                "total_patterns": total_patterns
            })
    
    # Sort by confidence
    identified_templates.sort(key=lambda x: x["confidence"], reverse=True)
    
    # Primary template identification
    primary_template = identified_templates[0] if identified_templates else {
        "template_type": "UNKNOWN",
        "confidence": 0.0,
        "matches": 0,
        "total_patterns": 0
    }
    
    # Get state-specific requirements
    state_requirements = _get_state_template_requirements(state, primary_template["template_type"])
    
    # Validate template compliance
    validation_issues = _validate_template_compliance(document_text, state, primary_template["template_type"])
    
    # Get compliance notes
    compliance_notes = _get_template_compliance_notes(state, primary_template["template_type"])
    
    return {
        "primary_template_type": primary_template["template_type"],
        "primary_confidence": primary_template["confidence"],
        "all_identified_templates": identified_templates,
        "confidence_scores": confidence_scores,
        "state_requirements": state_requirements,
        "validation_issues": validation_issues,
        "compliance_notes": compliance_notes,
        "template_metadata": {
            "state": state,
            "analysis_timestamp": "2024-01-01T00:00:00Z",  # Would be current timestamp in production
            "document_length": len(document_text)
        }
    }


def _get_state_template_requirements(state: str, template_type: str) -> Dict[str, Any]:
    """Get state-specific template requirements"""
    
    base_requirements = {
        "mandatory_sections": ["parties", "property_description", "purchase_price", "settlement"],
        "disclosure_requirements": ["vendor_statement", "title_documents"],
        "cooling_off_provisions": True,
        "warranty_requirements": ["title", "planning", "building"]
    }
    
    state_requirements = {
        "NSW": {
            **base_requirements,
            "specific_sections": ["section_149_certificate", "strata_certificate"],
            "disclosure_period": "7_days_before_exchange",
            "cooling_off_days": 5
        },
        "VIC": {
            **base_requirements,
            "specific_sections": ["section_32_statement", "owners_corporation_certificate"],
            "disclosure_period": "3_days_before_auction_or_exchange",
            "cooling_off_days": 3
        },
        "QLD": {
            **base_requirements,
            "specific_sections": ["disclosure_statement", "body_corporate_search"],
            "disclosure_period": "at_exchange",
            "cooling_off_days": 5
        }
    }
    
    return state_requirements.get(state, base_requirements)


def _validate_template_compliance(document_text: str, state: str, template_type: str) -> List[Dict[str, Any]]:
    """Validate template compliance with state requirements"""
    
    issues = []
    document_lower = document_text.lower()
    
    # Common validation checks
    required_sections = {
        "parties": [r"vendor", r"purchaser", r"buyer", r"seller"],
        "property": [r"property", r"land", r"premises"],
        "price": [r"purchase\s+price", r"consideration"],
        "settlement": [r"settlement", r"completion"]
    }
    
    for section, patterns in required_sections.items():
        found = False
        for pattern in patterns:
            if re.search(pattern, document_lower):
                found = True
                break
        
        if not found:
            issues.append({
                "issue_type": "missing_section",
                "section": section,
                "severity": "high",
                "description": f"Required section '{section}' not found or unclear"
            })
    
    # State-specific validation
    if state == "VIC" and template_type == "REIV":
        if not re.search(r"section\s+32", document_lower):
            issues.append({
                "issue_type": "missing_disclosure",
                "section": "section_32",
                "severity": "critical",
                "description": "Section 32 statement reference not found (VIC requirement)"
            })
    
    return issues


def _get_template_compliance_notes(state: str, template_type: str) -> List[str]:
    """Get compliance notes for state and template type"""
    
    notes = []
    
    if state == "NSW":
        notes.extend([
            "Must comply with Conveyancing Act 1919 (NSW)",
            "Section 149 certificate required",
            "5 business day cooling-off period applies"
        ])
    elif state == "VIC":
        notes.extend([
            "Must comply with Sale of Land Act 1962 (Vic)",
            "Section 32 statement required before signing",
            "3 business day cooling-off period applies"
        ])
    elif state == "QLD":
        notes.extend([
            "Must comply with Property Law Act 1974 (Qld)",
            "Disclosure statement required",
            "5 business day cooling-off period applies"
        ])
    
    if template_type == "UNKNOWN":
        notes.append("Template type could not be determined - manual review recommended")
    
    return notes