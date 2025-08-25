"""
Pydantic schema for Cross-Section Validation and Consistency Checks (Step 2.12)

This schema defines the structured output for cross-section validation,
consistency checks, and comprehensive synthesis analysis.
"""

from typing import List, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schema.enums import RiskLevel


class ConsistencyLevel(str, Enum):
    """Level of consistency between sections"""

    CONSISTENT = "consistent"
    MINOR_DISCREPANCY = "minor_discrepancy"
    MAJOR_DISCREPANCY = "major_discrepancy"
    CONTRADICTORY = "contradictory"


class ValidationStatus(str, Enum):
    """Validation status classification"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    REQUIRES_CLARIFICATION = "requires_clarification"


class SectionValidation(BaseModel):
    """Individual section validation result"""

    section_name: str = Field(..., description="Name of the section analyzed")
    validation_status: ValidationStatus = Field(..., description="Validation status")

    # Data quality assessment
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness score for section"
    )
    accuracy_indicators: List[str] = Field(
        default_factory=list, description="Indicators of data accuracy"
    )
    quality_concerns: List[str] = Field(
        default_factory=list, description="Quality concerns identified"
    )

    # Internal consistency
    internal_consistency: ConsistencyLevel = Field(
        ..., description="Internal consistency level"
    )
    internal_conflicts: List[str] = Field(
        default_factory=list, description="Internal conflicts identified"
    )

    # Cross-references
    cross_references_verified: List[str] = Field(
        default_factory=list, description="Cross-references verified"
    )
    broken_references: List[str] = Field(
        default_factory=list, description="Broken or invalid cross-references"
    )

    # Recommendations
    improvement_recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )


class CrossSectionConsistency(BaseModel):
    """Cross-section consistency analysis"""

    section_1: str = Field(..., description="First section in comparison")
    section_2: str = Field(..., description="Second section in comparison")

    # Consistency assessment
    consistency_level: ConsistencyLevel = Field(..., description="Level of consistency")
    consistent_elements: List[str] = Field(
        default_factory=list, description="Elements that are consistent"
    )
    discrepancies: List[str] = Field(
        default_factory=list, description="Discrepancies identified"
    )

    # Impact analysis
    discrepancy_impact: str = Field(..., description="Impact of discrepancies")
    resolution_required: bool = Field(
        default=False, description="Whether resolution is required"
    )
    resolution_methods: List[str] = Field(
        default_factory=list, description="Methods to resolve discrepancies"
    )

    # Risk assessment
    consistency_risk: RiskLevel = Field(..., description="Risk from consistency issues")
    buyer_impact: str = Field(..., description="Impact on buyer from discrepancies")

    # Recommendations
    resolution_priority: str = Field(
        ..., description="Priority for resolving discrepancy"
    )
    recommended_approach: str = Field(
        ..., description="Recommended approach for resolution"
    )


class DataIntegrityCheck(BaseModel):
    """Data integrity and accuracy verification"""

    check_type: str = Field(..., description="Type of integrity check performed")

    # Verification results
    data_verified: List[str] = Field(
        default_factory=list, description="Data elements verified"
    )
    verification_method: str = Field(..., description="Method used for verification")
    verification_sources: List[str] = Field(
        default_factory=list, description="Sources used for verification"
    )

    # Accuracy assessment
    accuracy_level: str = Field(..., description="Overall accuracy level")
    accuracy_concerns: List[str] = Field(
        default_factory=list, description="Accuracy concerns identified"
    )

    # Confidence metrics
    verification_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in verification"
    )
    data_reliability: float = Field(
        ..., ge=0.0, le=1.0, description="Reliability of underlying data"
    )

    # Recommendations
    additional_verification_needed: List[str] = Field(
        default_factory=list, description="Additional verification needed"
    )
    data_improvement_recommendations: List[str] = Field(
        default_factory=list, description="Data improvement recommendations"
    )


class ComprehensiveSynthesis(BaseModel):
    """Comprehensive synthesis of all section analyses"""

    # Overall contract assessment
    contract_coherence: str = Field(
        ..., description="Overall contract coherence assessment"
    )
    internal_logic: str = Field(
        ..., description="Internal logic and structure assessment"
    )
    commercial_sensibility: str = Field(
        ..., description="Commercial sensibility of terms"
    )

    # Risk profile synthesis
    primary_risk_themes: List[str] = Field(
        default_factory=list, description="Primary risk themes across sections"
    )
    risk_concentration_areas: List[str] = Field(
        default_factory=list, description="Areas of risk concentration"
    )
    risk_mitigation_effectiveness: str = Field(
        ..., description="Effectiveness of built-in risk mitigation"
    )

    # Buyer protection synthesis
    overall_buyer_protection: str = Field(
        ..., description="Overall buyer protection assessment"
    )
    protection_gaps: List[str] = Field(
        default_factory=list, description="Significant protection gaps"
    )
    protection_strengths: List[str] = Field(
        default_factory=list, description="Areas of strong buyer protection"
    )

    # Contract balance
    party_balance_assessment: str = Field(
        ..., description="Assessment of balance between parties"
    )
    vendor_advantages: List[str] = Field(
        default_factory=list, description="Key vendor advantages"
    )
    buyer_advantages: List[str] = Field(
        default_factory=list, description="Key buyer advantages"
    )

    # Strategic recommendations
    strategic_approach: str = Field(..., description="Recommended strategic approach")
    negotiation_strategy: List[str] = Field(
        default_factory=list, description="Negotiation strategy recommendations"
    )
    professional_advice_priorities: List[str] = Field(
        default_factory=list, description="Professional advice priorities"
    )


class CrossValidationResult(BaseModel):
    """
    Complete result structure for Cross-Section Validation and Consistency Checks.

    Covers PRD 4.1.2.12 requirements:
    - Cross-section consistency validation
    - Data integrity and accuracy verification
    - Comprehensive contract synthesis
    - Overall risk profile assessment
    - Strategic guidance for buyer decision-making
    """

    # Validation overview
    total_sections_validated: int = Field(
        ..., description="Total number of sections validated"
    )
    sections_passed: int = Field(
        ..., description="Number of sections passing validation"
    )
    sections_with_warnings: int = Field(
        ..., description="Number of sections with warnings"
    )
    sections_failed: int = Field(
        ..., description="Number of sections failing validation"
    )

    # Individual section validation
    section_validations: List[SectionValidation] = Field(
        ..., description="Individual section validation results"
    )
    critical_validation_failures: List[str] = Field(
        default_factory=list, description="Critical validation failures"
    )

    # Cross-section consistency
    consistency_checks: List[CrossSectionConsistency] = Field(
        ..., description="Cross-section consistency analysis"
    )
    major_inconsistencies: List[str] = Field(
        default_factory=list, description="Major inconsistencies requiring resolution"
    )

    # Data integrity verification
    integrity_checks: List[DataIntegrityCheck] = Field(
        ..., description="Data integrity verification results"
    )
    data_quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall data quality score"
    )

    # Comprehensive synthesis
    synthesis: ComprehensiveSynthesis = Field(
        ..., description="Comprehensive contract synthesis"
    )

    # Overall assessment
    contract_validation_status: ValidationStatus = Field(
        ..., description="Overall contract validation status"
    )
    overall_risk_profile: RiskLevel = Field(
        ..., description="Overall contract risk profile"
    )
    buyer_decision_framework: str = Field(
        ..., description="Decision framework for buyer"
    )

    # Critical findings
    deal_breaker_issues: List[str] = Field(
        default_factory=list, description="Issues that could be deal breakers"
    )
    immediate_action_required: List[str] = Field(
        default_factory=list, description="Issues requiring immediate action"
    )
    negotiation_imperatives: List[str] = Field(
        default_factory=list, description="Must-negotiate items"
    )

    # Risk prioritization
    risk_priority_matrix: Dict[str, List[str]] = Field(
        default_factory=dict, description="Risk prioritization by urgency and impact"
    )
    mitigation_roadmap: List[str] = Field(
        default_factory=list, description="Comprehensive risk mitigation roadmap"
    )

    # Professional guidance
    specialized_advice_required: Dict[str, List[str]] = Field(
        default_factory=dict, description="Specialized advice requirements"
    )
    professional_consultation_priorities: List[str] = Field(
        default_factory=list, description="Professional consultation priorities"
    )

    # Decision support
    proceed_conditions: List[str] = Field(
        default_factory=list, description="Conditions for proceeding with transaction"
    )
    withdrawal_indicators: List[str] = Field(
        default_factory=list, description="Indicators suggesting withdrawal"
    )
    renegotiation_targets: List[str] = Field(
        default_factory=list, description="Priority renegotiation targets"
    )

    # Quality assurance
    validation_completeness: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness of validation process"
    )
    cross_check_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="Accuracy of cross-checks performed"
    )
    synthesis_reliability: float = Field(
        ..., ge=0.0, le=1.0, description="Reliability of synthesis conclusions"
    )

    # Evidence and methodology
    validation_methodology: List[str] = Field(
        default_factory=list, description="Validation methodology applied"
    )
    evidence_sources: List[str] = Field(
        default_factory=list, description="Evidence sources used"
    )
    cross_reference_verification: List[str] = Field(
        default_factory=list, description="Cross-reference verification performed"
    )

    # Final recommendations
    executive_summary: str = Field(
        ..., description="Executive summary of validation findings"
    )
    strategic_recommendations: List[str] = Field(
        default_factory=list, description="Strategic recommendations for buyer"
    )
    implementation_priorities: List[str] = Field(
        default_factory=list, description="Implementation priority order"
    )

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the cross-validation analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_sections_validated": 11,
                "sections_passed": 8,
                "sections_with_warnings": 2,
                "sections_failed": 1,
                "section_validations": [
                    {
                        "section_name": "financial_terms",
                        "validation_status": "passed",
                        "completeness_score": 0.94,
                        "internal_consistency": "consistent",
                        "quality_concerns": [],
                    }
                ],
                "consistency_checks": [
                    {
                        "section_1": "financial_terms",
                        "section_2": "conditions",
                        "consistency_level": "consistent",
                        "discrepancies": [],
                        "consistency_risk": "low",
                    }
                ],
                "synthesis": {
                    "contract_coherence": "Good overall coherence with minor inconsistencies",
                    "commercial_sensibility": "Commercially reasonable terms",
                    "overall_buyer_protection": "Adequate protection with some negotiation opportunities",
                    "party_balance_assessment": "Reasonably balanced with slight vendor favor",
                },
                "contract_validation_status": "warning",
                "overall_risk_profile": "medium",
                "buyer_decision_framework": "Proceed with targeted negotiations and professional advice",
                "validation_completeness": 0.96,
                "cross_check_accuracy": 0.93,
                "synthesis_reliability": 0.91,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
