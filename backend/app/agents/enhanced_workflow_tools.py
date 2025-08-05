"""
Enhanced tools for contract analysis workflow with validation and quality checking
"""

from typing import Dict, List, Any, Optional, Tuple
from langchain.tools import tool
from datetime import datetime, timedelta
import re
import logging
from decimal import Decimal
from pathlib import Path

from app.models.contract_state import AustralianState, RiskLevel
from app.models.workflow_outputs import (
    DocumentQualityMetrics, 
    WorkflowValidationOutput,
    ContractTermsValidationOutput
)

logger = logging.getLogger(__name__)


@tool
def validate_document_quality(document_text: str, document_metadata: Dict[str, Any]) -> DocumentQualityMetrics:
    """
    Comprehensive document quality assessment for contract analysis
    
    Args:
        document_text: Extracted text from the document
        document_metadata: Metadata about document extraction process
        
    Returns:
        DocumentQualityMetrics with detailed quality assessment
    """
    
    if not document_text or len(document_text.strip()) < 50:
        return DocumentQualityMetrics(
            text_quality_score=0.0,
            completeness_score=0.0,
            readability_score=0.0,
            key_terms_coverage=0.0,
            extraction_confidence=0.0,
            issues_identified=["Document text is too short or empty"],
            improvement_suggestions=["Verify document was properly extracted", "Check document format and quality"]
        )
    
    # Calculate text quality metrics
    text_quality = _assess_text_quality(document_text)
    completeness = _assess_document_completeness(document_text)
    readability = _assess_readability(document_text)
    key_terms_coverage = _assess_key_terms_coverage(document_text)
    
    # Extract confidence from metadata
    extraction_confidence = document_metadata.get("extraction_confidence", 0.5)
    
    # Identify issues
    issues = []
    suggestions = []
    
    if text_quality < 0.7:
        issues.append("Poor text quality - possible OCR issues")
        suggestions.append("Consider re-scanning document at higher resolution")
    
    if completeness < 0.8:
        issues.append("Document appears incomplete")
        suggestions.append("Verify all pages were captured and processed")
    
    if readability < 0.6:
        issues.append("Document text is difficult to parse")
        suggestions.append("Manual review may be required for accurate analysis")
    
    if key_terms_coverage < 0.5:
        issues.append("Few contract-specific terms found")
        suggestions.append("Verify this is a property contract document")
    
    return DocumentQualityMetrics(
        text_quality_score=text_quality,
        completeness_score=completeness,
        readability_score=readability,
        key_terms_coverage=key_terms_coverage,
        extraction_confidence=extraction_confidence,
        issues_identified=issues,
        improvement_suggestions=suggestions
    )


@tool
def validate_contract_terms_completeness(
    contract_terms: Dict[str, Any], 
    australian_state: str,
    contract_type: str = "purchase_agreement"
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
    
    # Define mandatory terms by contract type and state
    mandatory_terms = _get_mandatory_terms(contract_type, australian_state)
    
    # Validate each term
    terms_validated = {}
    missing_mandatory = []
    incomplete_terms = []
    
    for term_name, requirements in mandatory_terms.items():
        if term_name not in contract_terms:
            terms_validated[term_name] = False
            missing_mandatory.append(term_name)
        else:
            term_value = contract_terms[term_name]
            is_valid = _validate_term_value(term_name, term_value, requirements)
            terms_validated[term_name] = is_valid
            
            if not is_valid:
                incomplete_terms.append(term_name)
    
    # Calculate validation confidence
    total_terms = len(mandatory_terms)
    valid_terms = sum(1 for valid in terms_validated.values() if valid)
    confidence = valid_terms / total_terms if total_terms > 0 else 0.0
    
    # Generate recommendations
    recommendations = []
    if missing_mandatory:
        recommendations.append(f"Locate and extract missing mandatory terms: {', '.join(missing_mandatory)}")
    
    if incomplete_terms:
        recommendations.append(f"Verify and complete incomplete terms: {', '.join(incomplete_terms)}")
    
    # State-specific requirements
    state_requirements = _get_state_specific_validation(australian_state, contract_terms)
    
    return ContractTermsValidationOutput(
        terms_validated=terms_validated,
        missing_mandatory_terms=missing_mandatory,
        incomplete_terms=incomplete_terms,
        validation_confidence=confidence,
        state_specific_requirements=state_requirements,
        recommendations=recommendations
    )


@tool
def validate_workflow_step(
    step_name: str,
    step_data: Dict[str, Any],
    validation_criteria: Dict[str, Any]
) -> WorkflowValidationOutput:
    """
    Validate a workflow step against defined criteria
    
    Args:
        step_name: Name of the workflow step
        step_data: Data produced by the workflow step
        validation_criteria: Criteria for validation
        
    Returns:
        WorkflowValidationOutput with validation results
    """
    
    issues = []
    recommendations = []
    validation_score = 1.0
    
    # Validate based on step type
    if step_name == "document_processing":
        validation_score, step_issues, step_recs = _validate_document_processing_step(step_data)
        issues.extend(step_issues)
        recommendations.extend(step_recs)
    
    elif step_name == "term_extraction":
        validation_score, step_issues, step_recs = _validate_term_extraction_step(step_data)
        issues.extend(step_issues)
        recommendations.extend(step_recs)
    
    elif step_name == "risk_assessment":
        validation_score, step_issues, step_recs = _validate_risk_assessment_step(step_data)
        issues.extend(step_issues)
        recommendations.extend(step_recs)
    
    elif step_name == "compliance_check":
        validation_score, step_issues, step_recs = _validate_compliance_check_step(step_data)
        issues.extend(step_issues)
        recommendations.extend(step_recs)
    
    validation_passed = validation_score >= validation_criteria.get("min_score", 0.7)
    
    return WorkflowValidationOutput(
        step_name=step_name,
        validation_passed=validation_passed,
        validation_score=validation_score,
        issues_found=issues,
        recommendations=recommendations,
        metadata={
            "validation_criteria": validation_criteria,
            "timestamp": datetime.now().isoformat()
        }
    )


@tool
def calculate_overall_confidence_score(
    confidence_scores: Dict[str, float],
    step_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Calculate overall confidence score with weighted step contributions
    
    Args:
        confidence_scores: Confidence scores for each workflow step
        step_weights: Optional weights for each step (defaults to equal weighting)
        
    Returns:
        Dict with overall confidence and breakdown
    """
    
    if not confidence_scores:
        return {
            "overall_confidence": 0.0,
            "confidence_breakdown": {},
            "quality_assessment": "No confidence data available"
        }
    
    # Default weights if not provided
    if step_weights is None:
        step_weights = {
            "input_validation": 0.1,
            "document_processing": 0.15,
            "term_extraction": 0.25,
            "compliance_check": 0.2,
            "risk_assessment": 0.2,
            "recommendations": 0.1
        }
    
    # Calculate weighted average
    total_weighted_score = 0.0
    total_weights = 0.0
    
    for step, score in confidence_scores.items():
        weight = step_weights.get(step, 0.1)  # Default weight for unknown steps
        total_weighted_score += score * weight
        total_weights += weight
    
    overall_confidence = total_weighted_score / total_weights if total_weights > 0 else 0.0
    
    # Assess quality level
    if overall_confidence >= 0.9:
        quality_assessment = "Excellent - High confidence in all analysis areas"
    elif overall_confidence >= 0.8:
        quality_assessment = "Good - Reliable analysis with minor uncertainties"
    elif overall_confidence >= 0.7:
        quality_assessment = "Acceptable - Generally reliable with some areas of uncertainty"
    elif overall_confidence >= 0.6:
        quality_assessment = "Fair - Adequate analysis but professional review recommended"
    else:
        quality_assessment = "Poor - Low confidence, manual review strongly recommended"
    
    return {
        "overall_confidence": overall_confidence,
        "confidence_breakdown": confidence_scores,
        "step_weights": step_weights,
        "quality_assessment": quality_assessment,
        "recommendation": _get_confidence_recommendation(overall_confidence)
    }


# Helper functions

def _assess_text_quality(text: str) -> float:
    """Assess the quality of extracted text"""
    if not text:
        return 0.0
    
    words = text.split()
    if not words:
        return 0.0
    
    # Calculate quality metrics
    total_chars = len(text)
    total_words = len(words)
    avg_word_length = sum(len(word) for word in words) / total_words
    
    # Check for OCR artifacts
    single_char_words = sum(1 for word in words if len(word) == 1)
    single_char_ratio = single_char_words / total_words
    
    # Check for repeated characters (OCR errors)
    repeated_char_patterns = len(re.findall(r'(.)\1{3,}', text))
    
    # Calculate score
    quality_score = 1.0
    
    # Penalize high single character ratio
    if single_char_ratio > 0.1:
        quality_score *= (1 - single_char_ratio)
    
    # Penalize repeated character patterns
    if repeated_char_patterns > 5:
        quality_score *= 0.7
    
    # Penalize very short or very long average word length
    if avg_word_length < 2 or avg_word_length > 15:
        quality_score *= 0.8
    
    return max(0.0, min(1.0, quality_score))


def _assess_document_completeness(text: str) -> float:
    """Assess document completeness based on expected sections"""
    text_lower = text.lower()
    
    # Expected sections in a property contract
    expected_sections = [
        ["vendor", "seller"],
        ["purchaser", "buyer"],
        ["property", "premises", "land"],
        ["price", "consideration", "amount"],
        ["settlement", "completion"],
        ["special conditions", "conditions"],
        ["deposit"]
    ]
    
    sections_found = 0
    for section_terms in expected_sections:
        if any(term in text_lower for term in section_terms):
            sections_found += 1
    
    return sections_found / len(expected_sections)


def _assess_readability(text: str) -> float:
    """Assess text readability and structure"""
    if not text:
        return 0.0
    
    # Count sentences and words
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = text.split()
    
    if not sentences or not words:
        return 0.0
    
    # Calculate average sentence length
    avg_sentence_length = len(words) / len(sentences)
    
    # Optimal sentence length for legal documents is typically 15-25 words
    if 10 <= avg_sentence_length <= 30:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - abs(avg_sentence_length - 20) / 50)
    
    # Check for proper capitalization and punctuation
    properly_capitalized = sum(1 for s in sentences if s[0].isupper()) / len(sentences)
    
    return (length_score + properly_capitalized) / 2


def _assess_key_terms_coverage(text: str) -> float:
    """Assess coverage of key contract terms"""
    text_lower = text.lower()
    
    # Key terms expected in property contracts
    key_terms = [
        "contract", "agreement", "purchase", "sale", "property",
        "vendor", "purchaser", "settlement", "deposit", "price",
        "title", "possession", "condition", "warranty", "clause",
        "conveyance", "transfer", "mortgage", "easement", "covenant"
    ]
    
    terms_found = sum(1 for term in key_terms if term in text_lower)
    return terms_found / len(key_terms)


def _get_mandatory_terms(contract_type: str, state: str) -> Dict[str, Dict[str, Any]]:
    """Get mandatory terms for contract type and state"""
    base_terms = {
        "purchase_price": {"type": "float", "required": True, "min_value": 0},
        "deposit_amount": {"type": "float", "required": True, "min_value": 0},
        "settlement_date": {"type": "date", "required": True},
        "property_address": {"type": "string", "required": True, "min_length": 10},
        "vendor_name": {"type": "string", "required": True, "min_length": 2},
        "purchaser_name": {"type": "string", "required": True, "min_length": 2}
    }
    
    # Add state-specific terms
    if state in ["NSW", "VIC", "QLD", "SA", "WA", "ACT"]:
        base_terms["cooling_off_period"] = {"type": "string", "required": True}
    
    return base_terms


def _validate_term_value(term_name: str, value: Any, requirements: Dict[str, Any]) -> bool:
    """Validate a term value against requirements"""
    if value is None:
        return not requirements.get("required", False)
    
    term_type = requirements.get("type", "string")
    
    if term_type == "float":
        try:
            float_value = float(value) if not isinstance(value, (int, float)) else value
            min_value = requirements.get("min_value")
            if min_value is not None and float_value < min_value:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    elif term_type == "string":
        str_value = str(value)
        min_length = requirements.get("min_length", 0)
        return len(str_value.strip()) >= min_length
    
    elif term_type == "date":
        # Basic date validation - could be enhanced
        return len(str(value)) >= 8  # Minimum reasonable date string
    
    return True


def _get_state_specific_validation(state: str, contract_terms: Dict[str, Any]) -> Dict[str, Any]:
    """Get state-specific validation requirements and results"""
    requirements = {}
    
    if state == "NSW":
        requirements["vendor_statement_required"] = True
        requirements["cooling_off_minimum_days"] = 5
        requirements["conveyancer_required"] = True
    
    elif state == "VIC":
        requirements["section_32_statement_required"] = True
        requirements["cooling_off_minimum_days"] = 3
        requirements["conveyancer_required"] = True
    
    elif state == "QLD":
        requirements["contract_disclosure_required"] = True
        requirements["cooling_off_minimum_days"] = 5
        requirements["cooling_off_waiver_prohibited"] = True
    
    return requirements


def _validate_document_processing_step(step_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Validate document processing step"""
    issues = []
    recommendations = []
    score = 1.0
    
    metadata = step_data.get("document_metadata", {})
    text_quality = metadata.get("text_quality", {})
    
    if text_quality.get("score", 0) < 0.7:
        issues.append("Poor text extraction quality")
        recommendations.append("Consider re-processing document with higher quality settings")
        score *= 0.8
    
    char_count = metadata.get("character_count", 0)
    if char_count < 500:
        issues.append("Very short document - may be incomplete")
        recommendations.append("Verify all pages were processed")
        score *= 0.7
    
    return score, issues, recommendations


def _validate_term_extraction_step(step_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Validate term extraction step"""
    issues = []
    recommendations = []
    score = 1.0
    
    contract_terms = step_data.get("contract_terms", {})
    extraction_metadata = step_data.get("extraction_metadata", {})
    
    if len(contract_terms) < 3:
        issues.append("Very few terms extracted")
        recommendations.append("Review document quality and extraction process")
        score *= 0.6
    
    confidence_scores = extraction_metadata.get("confidence_scores", {})
    avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
    
    if avg_confidence < 0.7:
        issues.append("Low confidence in term extraction")
        recommendations.append("Manual review of extracted terms recommended")
        score *= 0.8
    
    return score, issues, recommendations


def _validate_risk_assessment_step(step_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Validate risk assessment step"""
    issues = []
    recommendations = []
    score = 1.0
    
    risk_assessment = step_data.get("risk_assessment", {})
    
    if not risk_assessment.get("risk_factors"):
        issues.append("No risk factors identified")
        recommendations.append("Review risk assessment process")
        score *= 0.5
    
    overall_risk = risk_assessment.get("overall_risk_score", 0)
    if overall_risk == 0:
        issues.append("Risk score not calculated")
        recommendations.append("Ensure risk scoring algorithm is working")
        score *= 0.7
    
    return score, issues, recommendations


def _validate_compliance_check_step(step_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Validate compliance check step"""
    issues = []
    recommendations = []
    score = 1.0
    
    compliance_check = step_data.get("compliance_check", {})
    
    if compliance_check.get("compliance_confidence", 0) < 0.7:
        issues.append("Low confidence in compliance assessment")
        recommendations.append("Manual compliance review recommended")
        score *= 0.8
    
    compliance_issues = compliance_check.get("compliance_issues", [])
    if len(compliance_issues) > 5:
        issues.append("Many compliance issues identified")
        recommendations.append("Professional legal review strongly recommended")
        score *= 0.9
    
    return score, issues, recommendations


def _get_confidence_recommendation(confidence: float) -> str:
    """Get recommendation based on confidence level"""
    if confidence >= 0.9:
        return "Analysis is highly reliable and can be used with confidence"
    elif confidence >= 0.8:
        return "Analysis is generally reliable, minor professional review may be beneficial"
    elif confidence >= 0.7:
        return "Analysis is acceptable, professional review recommended for critical decisions"
    elif confidence >= 0.6:
        return "Analysis has limitations, professional review strongly recommended"
    else:
        return "Analysis has significant limitations, manual review and professional advice essential"