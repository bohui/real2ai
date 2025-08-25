"""
Pydantic schema for Disclosure Compliance Check (Step 2.10)

This schema defines the structured output for mandatory disclosure compliance,
vendor statement adequacy, and regulatory requirement verification.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schema.enums import RiskLevel


class DisclosureType(str, Enum):
    """Type of disclosure requirement"""

    VENDOR_STATEMENT = "vendor_statement"
    BUILDING_SAFETY = "building_safety"
    ENVIRONMENTAL = "environmental"
    PLANNING = "planning"
    HERITAGE = "heritage"
    CONTAMINATION = "contamination"
    FLOODING = "flooding"
    NOISE = "noise"
    INFRASTRUCTURE = "infrastructure"
    DEVELOPMENT = "development"
    STRATA = "strata"
    TENANCY = "tenancy"
    OTHER = "other"


class ComplianceStatus(str, Enum):
    """Compliance status classification"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"


class DisclosureRequirement(BaseModel):
    """Individual disclosure requirement analysis"""

    requirement_name: str = Field(..., description="Name of disclosure requirement")
    disclosure_type: DisclosureType = Field(..., description="Type classification")

    # Legal basis
    legal_source: str = Field(
        ..., description="Legal source of requirement (Act, Regulation)"
    )
    applicable_sections: List[str] = Field(
        default_factory=list, description="Applicable legal sections"
    )

    # Compliance assessment
    compliance_status: ComplianceStatus = Field(
        ..., description="Current compliance status"
    )
    provided_disclosure: Optional[str] = Field(
        None, description="Disclosure provided if any"
    )
    adequacy_assessment: str = Field(..., description="Adequacy of provided disclosure")

    # Gap analysis
    missing_elements: List[str] = Field(
        default_factory=list, description="Missing disclosure elements"
    )
    additional_requirements: List[str] = Field(
        default_factory=list, description="Additional requirements needed"
    )

    # Risk assessment
    non_compliance_risk: RiskLevel = Field(..., description="Risk of non-compliance")
    buyer_impact: str = Field(..., description="Impact on buyer from non-compliance")
    legal_consequences: List[str] = Field(
        default_factory=list, description="Legal consequences of non-compliance"
    )

    # Remediation
    remediation_required: bool = Field(
        default=False, description="Whether remediation is required"
    )
    remediation_steps: List[str] = Field(
        default_factory=list, description="Steps to achieve compliance"
    )
    remediation_timeline: Optional[str] = Field(
        None, description="Timeline for remediation"
    )

    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for this requirement"
    )


class VendorStatementAnalysis(BaseModel):
    """Vendor statement compliance analysis"""

    statement_provided: bool = Field(
        ..., description="Whether vendor statement is provided"
    )
    statement_type: Optional[str] = Field(None, description="Type of vendor statement")

    # Content analysis
    required_sections: List[str] = Field(
        default_factory=list, description="Required sections per legislation"
    )
    provided_sections: List[str] = Field(
        default_factory=list, description="Sections actually provided"
    )
    missing_sections: List[str] = Field(
        default_factory=list, description="Missing required sections"
    )

    # Quality assessment
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness score"
    )
    accuracy_indicators: List[str] = Field(
        default_factory=list, description="Indicators of accuracy"
    )
    concerns_identified: List[str] = Field(
        default_factory=list, description="Concerns identified"
    )

    # Compliance analysis
    legislative_compliance: ComplianceStatus = Field(
        ..., description="Compliance with legislation"
    )
    disclosure_adequacy: str = Field(..., description="Adequacy of disclosures")

    # Risk factors
    reliance_risks: List[str] = Field(
        default_factory=list, description="Risks in relying on statement"
    )
    verification_needed: List[str] = Field(
        default_factory=list, description="Items requiring independent verification"
    )


class EnvironmentalDisclosure(BaseModel):
    """Environmental disclosure analysis"""

    contamination_disclosure: ComplianceStatus = Field(
        ..., description="Contamination disclosure compliance"
    )
    flooding_risk_disclosure: ComplianceStatus = Field(
        ..., description="Flooding risk disclosure compliance"
    )

    # Environmental assessments
    environmental_assessments_required: List[str] = Field(
        default_factory=list, description="Required environmental assessments"
    )
    assessment_adequacy: str = Field(
        ..., description="Adequacy of provided assessments"
    )

    # Risk evaluation
    environmental_risks_identified: List[str] = Field(
        default_factory=list, description="Environmental risks identified"
    )
    further_investigation_needed: List[str] = Field(
        default_factory=list, description="Further investigation needed"
    )

    # Compliance requirements
    ongoing_compliance_obligations: List[str] = Field(
        default_factory=list, description="Ongoing compliance obligations"
    )
    regulatory_approvals_needed: List[str] = Field(
        default_factory=list, description="Regulatory approvals needed"
    )


class PlanningDisclosure(BaseModel):
    """Planning and development disclosure analysis"""

    planning_approvals_disclosed: ComplianceStatus = Field(
        ..., description="Planning approval disclosure compliance"
    )
    development_restrictions_disclosed: ComplianceStatus = Field(
        ..., description="Development restriction disclosure compliance"
    )

    # Planning analysis
    current_approvals: List[str] = Field(
        default_factory=list, description="Current planning approvals"
    )
    pending_applications: List[str] = Field(
        default_factory=list, description="Pending planning applications"
    )

    # Development potential
    development_restrictions: List[str] = Field(
        default_factory=list, description="Development restrictions identified"
    )
    future_development_risks: List[str] = Field(
        default_factory=list, description="Future development risks"
    )

    # Compliance verification
    approval_verification_needed: List[str] = Field(
        default_factory=list, description="Approvals requiring verification"
    )
    council_search_requirements: List[str] = Field(
        default_factory=list, description="Council search requirements"
    )


class BuildingSafetyDisclosure(BaseModel):
    """Building safety disclosure analysis"""

    building_approvals_disclosed: ComplianceStatus = Field(
        ..., description="Building approval disclosure compliance"
    )
    safety_compliance_disclosed: ComplianceStatus = Field(
        ..., description="Safety compliance disclosure compliance"
    )

    # Building compliance
    building_approvals: List[str] = Field(
        default_factory=list, description="Building approvals disclosed"
    )
    compliance_certificates: List[str] = Field(
        default_factory=list, description="Compliance certificates provided"
    )

    # Safety assessments
    safety_issues_disclosed: List[str] = Field(
        default_factory=list, description="Safety issues disclosed"
    )
    safety_upgrades_required: List[str] = Field(
        default_factory=list, description="Safety upgrades required"
    )

    # Risk evaluation
    building_compliance_risks: List[str] = Field(
        default_factory=list, description="Building compliance risks"
    )
    safety_investigation_needed: List[str] = Field(
        default_factory=list, description="Safety investigations needed"
    )


class DisclosureAnalysisResult(BaseModel):
    """
    Complete result structure for Disclosure Compliance Check.

    Covers PRD 4.1.2.10 requirements:
    - Complete mandatory disclosure compliance verification
    - Vendor statement adequacy assessment
    - Environmental and contamination disclosure review
    - Planning and development disclosure analysis
    - Building safety and compliance disclosure check
    """

    # Overall compliance summary
    total_disclosure_requirements: int = Field(
        ..., description="Total disclosure requirements identified"
    )
    compliant_disclosures: int = Field(
        ..., description="Number of compliant disclosures"
    )
    non_compliant_disclosures: int = Field(
        ..., description="Number of non-compliant disclosures"
    )
    overall_compliance_status: ComplianceStatus = Field(
        ..., description="Overall compliance status"
    )

    # Detailed requirement analysis
    disclosure_requirements: List[DisclosureRequirement] = Field(
        ..., description="Detailed disclosure requirement analysis"
    )
    critical_non_compliance: List[str] = Field(
        default_factory=list, description="Critical non-compliance issues"
    )

    # Specialized analyses
    vendor_statement_analysis: Optional[VendorStatementAnalysis] = Field(
        None, description="Vendor statement analysis"
    )
    environmental_disclosure: Optional[EnvironmentalDisclosure] = Field(
        None, description="Environmental disclosure analysis"
    )
    planning_disclosure: Optional[PlanningDisclosure] = Field(
        None, description="Planning disclosure analysis"
    )
    building_safety_disclosure: Optional[BuildingSafetyDisclosure] = Field(
        None, description="Building safety disclosure analysis"
    )

    # Risk assessment
    overall_disclosure_risk: RiskLevel = Field(
        ..., description="Overall disclosure compliance risk"
    )
    buyer_protection_level: str = Field(
        ..., description="Level of buyer protection from disclosures"
    )
    legal_remedy_availability: str = Field(
        ..., description="Availability of legal remedies for non-disclosure"
    )

    # Verification requirements
    independent_verification_needed: List[str] = Field(
        default_factory=list, description="Items requiring independent verification"
    )
    professional_advice_recommended: List[str] = Field(
        default_factory=list, description="Areas requiring professional advice"
    )

    # Regulatory compliance
    state_specific_requirements: List[str] = Field(
        default_factory=list, description="State-specific disclosure requirements"
    )
    federal_requirements: List[str] = Field(
        default_factory=list, description="Federal disclosure requirements"
    )
    industry_standards: List[str] = Field(
        default_factory=list, description="Industry standard disclosures"
    )

    # Timeline and procedures
    compliance_timeline: List[str] = Field(
        default_factory=list, description="Timeline for achieving compliance"
    )
    procedural_requirements: List[str] = Field(
        default_factory=list, description="Procedural requirements for compliance"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    compliance_checklist: List[str] = Field(
        default_factory=list, description="Disclosure compliance checklist"
    )
    verification_recommendations: List[str] = Field(
        default_factory=list, description="Verification recommendations"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness of disclosure requirement identification",
    )
    compliance_assessment_score: float = Field(
        ..., ge=0.0, le=1.0, description="Accuracy of compliance assessment"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    legal_references: List[str] = Field(
        default_factory=list, description="References to legal requirements"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the disclosure analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_disclosure_requirements": 12,
                "compliant_disclosures": 9,
                "non_compliant_disclosures": 2,
                "overall_compliance_status": "partially_compliant",
                "disclosure_requirements": [
                    {
                        "requirement_name": "Section 32 Vendor Statement",
                        "disclosure_type": "vendor_statement",
                        "legal_source": "Sale of Land Act 1962 (Vic)",
                        "compliance_status": "compliant",
                        "adequacy_assessment": "Adequate with all required sections",
                        "non_compliance_risk": "low",
                    }
                ],
                "vendor_statement_analysis": {
                    "statement_provided": True,
                    "statement_type": "Section 32 Statement",
                    "completeness_score": 0.92,
                    "legislative_compliance": "compliant",
                    "disclosure_adequacy": "Good with minor clarifications needed",
                },
                "overall_disclosure_risk": "medium",
                "buyer_protection_level": "Good with some verification needed",
                "confidence_score": 0.88,
                "completeness_score": 0.94,
                "compliance_assessment_score": 0.91,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
