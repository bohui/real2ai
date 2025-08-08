"""
Pydantic models for structured workflow outputs
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime

from .contract_state import RiskLevel, AustralianState


class RiskSeverity(str, Enum):
    """Risk severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationPriority(str, Enum):
    """Recommendation priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationCategory(str, Enum):
    """Recommendation categories"""

    LEGAL = "legal"
    FINANCIAL = "financial"
    PRACTICAL = "practical"
    COMPLIANCE = "compliance"


class RiskFactor(BaseModel):
    """Individual risk factor in contract analysis"""

    factor: str = Field(..., description="Description of the risk factor")
    severity: RiskSeverity = Field(..., description="Severity level of the risk")
    description: str = Field(..., description="Detailed explanation of the risk")
    impact: str = Field(..., description="Potential consequences of this risk")
    australian_specific: bool = Field(
        ..., description="Whether this risk is specific to Australian property law"
    )
    mitigation_suggestions: Optional[List[str]] = Field(
        default=[], description="Suggestions to mitigate this risk"
    )
    legal_reference: Optional[str] = Field(
        default=None, description="Relevant legal reference or case law"
    )

    @validator("severity", pre=True)
    def validate_severity(cls, v):
        if isinstance(v, str):
            return RiskSeverity(v.lower())
        return v


class RiskAnalysisOutput(BaseModel):
    """Structured output for risk assessment"""

    overall_risk_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Overall risk score from 0-10 where 10 is highest risk",
    )
    risk_factors: List[RiskFactor] = Field(
        ..., description="List of identified risk factors"
    )
    risk_summary: str = Field(
        ..., description="Executive summary of the risk assessment"
    )
    confidence_level: float = Field(
        ..., ge=0, le=1, description="Confidence in the risk assessment (0-1)"
    )
    critical_issues: List[str] = Field(
        default=[], description="Critical issues requiring immediate attention"
    )
    state_specific_risks: List[str] = Field(
        default=[], description="Risks specific to the Australian state"
    )

    @validator("overall_risk_score")
    def validate_risk_score(cls, v):
        return max(0.0, min(10.0, v))

    @validator("confidence_level")
    def validate_confidence(cls, v):
        return max(0.0, min(1.0, v))


class Recommendation(BaseModel):
    """Individual recommendation"""

    priority: RecommendationPriority = Field(
        ..., description="Priority level of this recommendation"
    )
    category: RecommendationCategory = Field(
        ..., description="Category of the recommendation"
    )
    recommendation: str = Field(..., description="Specific actionable recommendation")
    action_required: bool = Field(
        ..., description="Whether immediate action is required"
    )
    australian_context: str = Field(
        ..., description="Australian state-specific context or notes"
    )
    estimated_cost: Optional[float] = Field(
        default=None, ge=0, description="Estimated cost in AUD if applicable"
    )
    timeline: Optional[str] = Field(
        default=None, description="Suggested timeline for implementation"
    )
    legal_basis: Optional[str] = Field(
        default=None, description="Legal basis or requirement for this recommendation"
    )
    consequences_if_ignored: Optional[str] = Field(
        default=None, description="Potential consequences if not followed"
    )

    @validator("priority", pre=True)
    def validate_priority(cls, v):
        if isinstance(v, str):
            return RecommendationPriority(v.lower())
        return v

    @validator("category", pre=True)
    def validate_category(cls, v):
        if isinstance(v, str):
            return RecommendationCategory(v.lower())
        return v


class RecommendationsOutput(BaseModel):
    """Structured output for recommendations"""

    recommendations: List[Recommendation] = Field(
        ..., description="List of actionable recommendations"
    )
    executive_summary: str = Field(
        ..., description="Executive summary of key recommendations"
    )
    immediate_actions: List[str] = Field(
        default=[], description="Actions that must be taken immediately"
    )
    next_steps: List[str] = Field(
        default=[], description="Suggested next steps in order of priority"
    )
    total_estimated_cost: Optional[float] = Field(
        default=None, ge=0, description="Total estimated cost of all recommendations"
    )
    compliance_requirements: List[str] = Field(
        default=[], description="Mandatory compliance requirements"
    )
    state_specific_advice: Dict[str, Any] = Field(
        default={}, description="State-specific advice and requirements"
    )

    @validator("total_estimated_cost")
    def calculate_total_cost(cls, v, values):
        if v is None and "recommendations" in values:
            total = sum(
                rec.estimated_cost or 0
                for rec in values["recommendations"]
                if rec.estimated_cost is not None
            )
            return total if total > 0 else None
        return v


class ComplianceIssue(BaseModel):
    """Individual compliance issue"""

    issue_type: str = Field(..., description="Type of compliance issue")
    description: str = Field(..., description="Description of the compliance issue")
    severity: RiskSeverity = Field(..., description="Severity of the compliance issue")
    legal_reference: str = Field(..., description="Relevant legal reference")
    resolution_required: bool = Field(
        ..., description="Whether resolution is required before settlement"
    )
    estimated_resolution_time: Optional[str] = Field(
        default=None, description="Estimated time to resolve"
    )


class ComplianceAnalysisOutput(BaseModel):
    """Structured output for compliance analysis"""

    overall_compliance: bool = Field(..., description="Overall compliance status")
    compliance_score: float = Field(
        ..., ge=0, le=1, description="Compliance score from 0-1"
    )
    compliance_issues: List[ComplianceIssue] = Field(
        default=[], description="List of compliance issues"
    )
    state_requirements_met: Dict[str, bool] = Field(
        default={}, description="State requirement compliance status"
    )
    mandatory_corrections: List[str] = Field(
        default=[], description="Corrections that must be made"
    )
    warnings: List[str] = Field(default=[], description="Compliance warnings")
    legal_opinion_required: bool = Field(
        default=False, description="Whether legal opinion is required"
    )
    australian_state: Optional[str] = Field(
        default=None, description="Australian state for compliance check"
    )


class DocumentQualityMetrics(BaseModel):
    """Document quality assessment metrics"""

    text_quality_score: float = Field(
        ..., ge=0, le=1, description="Quality of extracted text (0-1)"
    )
    completeness_score: float = Field(
        ..., ge=0, le=1, description="Completeness of document (0-1)"
    )
    readability_score: float = Field(
        ..., ge=0, le=1, description="Document readability (0-1)"
    )
    key_terms_coverage: float = Field(
        ..., ge=0, le=1, description="Coverage of key contract terms (0-1)"
    )
    extraction_confidence: float = Field(
        ..., ge=0, le=1, description="Confidence in text extraction (0-1)"
    )
    issues_identified: List[str] = Field(
        default=[], description="Issues identified in document quality"
    )
    improvement_suggestions: List[str] = Field(
        default=[], description="Suggestions to improve document quality"
    )


class WorkflowValidationOutput(BaseModel):
    """Output for workflow validation steps"""

    step_name: str = Field(..., description="Name of the workflow step")
    validation_passed: bool = Field(..., description="Whether validation passed")
    validation_score: float = Field(
        ..., ge=0, le=1, description="Validation score (0-1)"
    )
    issues_found: List[str] = Field(
        default=[], description="Issues found during validation"
    )
    recommendations: List[str] = Field(
        default=[], description="Recommendations for improvement"
    )
    metadata: Dict[str, Any] = Field(
        default={}, description="Additional validation metadata"
    )


class ContractTermsValidationOutput(BaseModel):
    """Output for contract terms validation"""

    terms_validated: Dict[str, bool] = Field(
        ..., description="Validation status for each term"
    )
    missing_mandatory_terms: List[str] = Field(
        default=[], description="List of missing mandatory terms"
    )
    incomplete_terms: List[str] = Field(
        default=[], description="List of incomplete terms"
    )
    validation_confidence: float = Field(
        ..., ge=0, le=1, description="Overall validation confidence"
    )
    state_specific_requirements: Dict[str, Any] = Field(
        default={}, description="State-specific requirement compliance"
    )
    recommendations: List[str] = Field(
        default=[], description="Recommendations for term improvements"
    )


class ContractTermsOutput(BaseModel):
    """Structured output for contract terms extraction"""

    terms: Dict[str, Any] = Field(..., description="Extracted contract terms")
    confidence_scores: Dict[str, float] = Field(
        default={}, description="Confidence scores for each term"
    )
    overall_confidence: float = Field(
        ..., ge=0, le=1, description="Overall extraction confidence"
    )
    state_requirements: Dict[str, Any] = Field(
        default={}, description="State-specific requirements"
    )
    extraction_method: str = Field(
        default="llm_structured", description="Method used for extraction"
    )
    extraction_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of extraction"
    )
    missing_terms: List[str] = Field(
        default=[], description="Terms that could not be extracted"
    )
    extraction_notes: List[str] = Field(
        default=[], description="Notes about the extraction process"
    )


# Export all models for easy import
__all__ = [
    "RiskSeverity",
    "RecommendationPriority",
    "RecommendationCategory",
    "RiskFactor",
    "RiskAnalysisOutput",
    "Recommendation",
    "RecommendationsOutput",
    "ComplianceIssue",
    "ComplianceAnalysisOutput",
    "DocumentQualityMetrics",
    "WorkflowValidationOutput",
    "ContractTermsValidationOutput",
    "ContractTermsOutput",
]
