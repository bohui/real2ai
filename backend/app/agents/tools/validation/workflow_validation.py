"""
Workflow step validation tools
"""

from typing import Dict, List, Any, Optional, Tuple
from langchain.tools import tool

from app.prompts.schema.workflow_outputs import WorkflowValidationOutput


@tool
def validate_workflow_step(
    step_name: str,
    step_data: Dict[str, Any],
    expected_outputs: Optional[List[str]] = None,
    quality_thresholds: Optional[Dict[str, float]] = None,
) -> WorkflowValidationOutput:
    """
    Validate a workflow step's execution and outputs

    Args:
        step_name: Name of the workflow step being validated
        step_data: Data produced by the workflow step
        expected_outputs: List of expected output keys
        quality_thresholds: Quality thresholds for validation

    Returns:
        WorkflowValidationOutput with validation results
    """

    if quality_thresholds is None:
        quality_thresholds = {
            "minimum_confidence": 0.6,
            "minimum_completeness": 0.7,
            "maximum_error_rate": 0.1,
        }

    # Step-specific validation
    if step_name == "document_processing":
        confidence, issues, recommendations = _validate_document_processing_step(
            step_data
        )
    elif step_name == "term_extraction":
        confidence, issues, recommendations = _validate_term_extraction_step(step_data)
    elif step_name == "risk_assessment":
        confidence, issues, recommendations = _validate_risk_assessment_step(step_data)
    elif step_name == "compliance_check":
        confidence, issues, recommendations = _validate_compliance_check_step(step_data)
    else:
        # Generic validation
        confidence = 0.7  # Default confidence
        issues = []
        recommendations = []

        if not step_data:
            issues.append("No data produced by workflow step")
            confidence = 0.0

    # Check expected outputs
    missing_outputs = []
    if expected_outputs:
        for expected_key in expected_outputs:
            if expected_key not in step_data:
                missing_outputs.append(expected_key)

    if missing_outputs:
        issues.append(f"Missing expected outputs: {', '.join(missing_outputs)}")
        confidence *= 0.8  # Reduce confidence for missing outputs

    # Apply quality thresholds
    validation_passed = (
        confidence >= quality_thresholds.get("minimum_confidence", 0.6)
        and len(issues) == 0
    )

    # Generate overall recommendation
    overall_recommendation = _get_confidence_recommendation(confidence)
    if not validation_passed:
        overall_recommendation = "Step validation failed - review and retry recommended"

    return WorkflowValidationOutput(
        step_name=step_name,
        validation_passed=validation_passed,
        confidence_score=confidence,
        issues_found=issues,
        missing_outputs=missing_outputs,
        recommendations=recommendations,
        overall_recommendation=overall_recommendation,
        quality_metrics={
            "confidence": confidence,
            "completeness": 1.0
            - (len(missing_outputs) / max(1, len(expected_outputs or []))),
            "error_rate": len(issues) / max(1, len(step_data)),
        },
    )


def _validate_document_processing_step(
    step_data: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """Validate document processing step"""

    issues = []
    recommendations = []
    confidence = 0.8  # Base confidence

    # Check for document metadata
    doc_metadata = step_data.get("document_metadata", {})
    if not doc_metadata:
        issues.append("Document metadata missing")
        confidence *= 0.5
    else:
        # Check extraction confidence
        extraction_confidence = doc_metadata.get("extraction_confidence", 0)
        if extraction_confidence < 0.7:
            issues.append("Low document extraction confidence")
            recommendations.append("Consider re-processing document at higher quality")

        # Check text quality
        text_quality = doc_metadata.get("text_quality", {})
        if text_quality and text_quality.get("score", 0) < 0.6:
            issues.append("Poor document text quality")
            recommendations.append("Verify document scan quality and OCR settings")

    return confidence, issues, recommendations


def _validate_term_extraction_step(
    step_data: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """Validate term extraction step"""

    issues = []
    recommendations = []
    confidence = 0.8

    # Check for extracted terms
    contract_terms = step_data.get("contract_terms", {})
    if not contract_terms:
        issues.append("No contract terms extracted")
        confidence = 0.2
    else:
        # Check key terms presence
        essential_terms = ["purchase_price", "property_address", "settlement_date"]
        missing_terms = [term for term in essential_terms if term not in contract_terms]

        if missing_terms:
            issues.append(f"Missing essential terms: {', '.join(missing_terms)}")
            confidence *= 0.7
            recommendations.append(
                "Review document for missing terms or improve extraction patterns"
            )

    # Check extraction metadata
    extraction_metadata = step_data.get("extraction_metadata", {})
    if extraction_metadata:
        overall_confidence = extraction_metadata.get("confidence_scores", {})
        if overall_confidence:
            avg_confidence = sum(overall_confidence.values()) / len(overall_confidence)
            if avg_confidence < 0.6:
                issues.append("Low average term extraction confidence")
                recommendations.append(
                    "Consider manual verification of extracted terms"
                )

    return confidence, issues, recommendations


def _validate_risk_assessment_step(
    step_data: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """Validate risk assessment step"""

    issues = []
    recommendations = []
    confidence = 0.8

    # Check for risk assessment data
    risk_assessment = step_data.get("risk_assessment", {})
    if not risk_assessment:
        issues.append("Risk assessment data missing")
        confidence = 0.3
    else:
        # Check risk score
        risk_score = risk_assessment.get("overall_risk_score", 0)
        if risk_score == 0:
            issues.append("Risk score not calculated")
            confidence *= 0.6

        # Check risk factors
        risk_factors = risk_assessment.get("risk_factors", [])
        if not risk_factors:
            issues.append("No risk factors identified")
            recommendations.append("Verify risk analysis completeness")

    return confidence, issues, recommendations


def _validate_compliance_check_step(
    step_data: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """Validate compliance check step"""

    issues = []
    recommendations = []
    confidence = 0.8

    # Check for compliance data
    compliance_check = step_data.get("compliance_check", {})
    if not compliance_check:
        issues.append("Compliance check data missing")
        confidence = 0.3
    else:
        # Check state compliance
        state_compliance = compliance_check.get("state_compliance")
        if state_compliance is None:
            issues.append("State compliance status not determined")
            confidence *= 0.7

        # Check for compliance issues
        compliance_issues = compliance_check.get("compliance_issues", [])
        if compliance_issues:
            recommendations.append("Address identified compliance issues")

    return confidence, issues, recommendations


def _get_confidence_recommendation(confidence: float) -> str:
    """Get recommendation based on confidence level"""

    if confidence >= 0.9:
        return "Step completed successfully with high confidence"
    elif confidence >= 0.8:
        return "Step completed successfully with good confidence"
    elif confidence >= 0.7:
        return "Step completed with acceptable confidence"
    elif confidence >= 0.6:
        return "Step completed with moderate confidence - review recommended"
    elif confidence >= 0.4:
        return "Step completed with low confidence - manual review required"
    else:
        return "Step validation failed - retry or manual intervention required"
