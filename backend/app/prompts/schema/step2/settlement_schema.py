"""
Pydantic schema for Settlement Logistics Analysis (Step 2.7)

This schema defines the structured output for settlement procedures, document requirements,
timing coordination, and completion obligations analysis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schema.enums import RiskLevel


class SettlementLocation(str, Enum):
    """Settlement location options"""

    VENDOR_SOLICITOR = "vendor_solicitor"
    PURCHASER_SOLICITOR = "purchaser_solicitor"
    AGREED_LOCATION = "agreed_location"
    ELECTRONIC = "electronic"
    NOT_SPECIFIED = "not_specified"


class DocumentType(str, Enum):
    """Type of settlement document"""

    TITLE_DOCUMENTS = "title_documents"
    CERTIFICATE_TITLE = "certificate_title"
    DISCHARGE_MORTGAGE = "discharge_mortgage"
    PLANNING_PERMITS = "planning_permits"
    BUILDING_PERMITS = "building_permits"
    COMPLIANCE_CERTIFICATES = "compliance_certificates"
    RATES_NOTICES = "rates_notices"
    UTILITY_ACCOUNTS = "utility_accounts"
    INSURANCE = "insurance"
    STRATA_DOCUMENTS = "strata_documents"
    OTHER = "other"


class FundingSource(str, Enum):
    """Source of settlement funds"""

    CASH = "cash"
    BANK_FINANCE = "bank_finance"
    VENDOR_FINANCE = "vendor_finance"
    DEPOSIT_RELEASE = "deposit_release"
    SALE_PROCEEDS = "sale_proceeds"
    OTHER = "other"


class SettlementDocument(BaseModel):
    """Settlement document requirement analysis"""

    document_name: str = Field(..., description="Name of required document")
    document_type: DocumentType = Field(..., description="Type classification")

    # Requirements
    required_by: str = Field(..., description="Party required to provide")
    required_at: str = Field(..., description="When document must be available")
    original_required: bool = Field(
        default=True, description="Whether original is required"
    )

    # Preparation assessment
    preparation_time_needed: Optional[str] = Field(
        None, description="Time needed to prepare document"
    )
    potential_delays: List[str] = Field(
        default_factory=list, description="Potential causes of delay"
    )

    # Risk assessment
    availability_risk: RiskLevel = Field(
        ..., description="Risk of document not being available"
    )
    compliance_requirements: List[str] = Field(
        default_factory=list, description="Compliance requirements for document"
    )

    # Alternatives
    alternative_arrangements: List[str] = Field(
        default_factory=list, description="Alternative arrangements if unavailable"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for this document"
    )


class SettlementProcedure(BaseModel):
    """Settlement procedure analysis"""

    procedure_description: str = Field(..., description="Description of the procedure")

    # Timing and logistics
    timing_requirements: List[str] = Field(
        default_factory=list, description="Timing requirements"
    )
    location_requirements: SettlementLocation = Field(
        ..., description="Location requirements"
    )
    attendance_required: List[str] = Field(
        default_factory=list, description="Who must attend settlement"
    )

    # Process steps
    required_steps: List[str] = Field(
        default_factory=list, description="Required procedural steps"
    )
    step_sequence: List[str] = Field(
        default_factory=list, description="Sequence of settlement steps"
    )

    # Risk factors
    procedural_risks: List[str] = Field(
        default_factory=list, description="Procedural risks identified"
    )
    complexity_assessment: str = Field(
        ..., description="Assessment of procedure complexity"
    )

    # Recommendations
    preparation_recommendations: List[str] = Field(
        default_factory=list, description="Preparation recommendations"
    )


class FundsAnalysis(BaseModel):
    """Settlement funds analysis"""

    total_funds_required: Optional[float] = Field(
        None, description="Total funds required at settlement"
    )

    # Funding sources
    funding_breakdown: List[Dict[str, Any]] = Field(
        default_factory=list, description="Breakdown of funding sources"
    )
    bank_finance_amount: Optional[float] = Field(
        None, description="Amount from bank finance"
    )
    cash_contribution: Optional[float] = Field(
        None, description="Cash contribution required"
    )

    # Timing requirements
    funds_availability_date: Optional[str] = Field(
        None, description="When funds must be available"
    )
    banking_arrangements: List[str] = Field(
        default_factory=list, description="Required banking arrangements"
    )

    # Risk assessment
    funding_risks: List[str] = Field(
        default_factory=list, description="Funding-related risks"
    )
    contingency_requirements: List[str] = Field(
        default_factory=list, description="Contingency fund requirements"
    )

    # Foreign exchange
    foreign_currency_issues: bool = Field(
        default=False, description="Whether foreign currency is involved"
    )
    fx_risk_assessment: Optional[str] = Field(
        None, description="Foreign exchange risk assessment"
    )


class PossessionArrangement(BaseModel):
    """Property possession arrangement analysis"""

    possession_date: Optional[str] = Field(
        None, description="Date possession is granted"
    )
    possession_time: Optional[str] = Field(
        None, description="Time possession is granted"
    )

    # Conditions for possession
    possession_conditions: List[str] = Field(
        default_factory=list, description="Conditions for granting possession"
    )
    early_possession_provisions: List[str] = Field(
        default_factory=list, description="Early possession arrangements"
    )
    delayed_possession_provisions: List[str] = Field(
        default_factory=list, description="Delayed possession arrangements"
    )

    # Risk assessment
    possession_risks: List[str] = Field(
        default_factory=list, description="Possession-related risks"
    )
    insurance_during_transition: Optional[str] = Field(
        None, description="Insurance arrangements during possession transition"
    )

    # Practical considerations
    keys_handover: Optional[str] = Field(None, description="Key handover arrangements")
    property_condition_requirements: List[str] = Field(
        default_factory=list, description="Property condition requirements"
    )


class CompletionObligation(BaseModel):
    """Settlement completion obligation analysis"""

    obligation_description: str = Field(
        ..., description="Description of the obligation"
    )
    responsible_party: str = Field(..., description="Party responsible for completion")

    # Timing
    completion_deadline: Optional[str] = Field(
        None, description="Deadline for completion"
    )
    time_critical: bool = Field(default=False, description="Whether timing is critical")

    # Dependencies
    dependent_on: List[str] = Field(
        default_factory=list, description="What this obligation depends on"
    )
    affects: List[str] = Field(
        default_factory=list, description="What is affected by completion"
    )

    # Risk assessment
    completion_risk: RiskLevel = Field(..., description="Risk of non-completion")
    failure_consequences: List[str] = Field(
        default_factory=list, description="Consequences of failure to complete"
    )

    # Mitigation
    mitigation_strategies: List[str] = Field(
        default_factory=list, description="Strategies to ensure completion"
    )


class SettlementAnalysisResult(BaseModel):
    """
    Complete result structure for Settlement Logistics Analysis.

    Covers PRD 4.1.2.7 requirements:
    - Settlement procedure and timing analysis
    - Document preparation and availability assessment
    - Funds coordination and availability
    - Possession arrangements and transition
    - Completion obligations and dependencies
    """

    # Settlement logistics overview
    settlement_date: Optional[str] = Field(
        None, description="Scheduled settlement date"
    )
    settlement_location: SettlementLocation = Field(
        ..., description="Settlement location arrangement"
    )
    settlement_method: str = Field(
        ..., description="Settlement method (in-person, electronic, etc.)"
    )

    # Document requirements
    required_documents: List[SettlementDocument] = Field(
        ..., description="All required settlement documents"
    )
    total_documents: int = Field(..., description="Total number of documents required")
    high_risk_documents: List[str] = Field(
        default_factory=list, description="Documents with high availability risk"
    )

    # Settlement procedures
    settlement_procedures: List[SettlementProcedure] = Field(
        ..., description="Settlement procedure analysis"
    )
    procedural_complexity: str = Field(
        ..., description="Assessment of procedural complexity"
    )

    # Funds analysis
    funds_analysis: Optional[FundsAnalysis] = Field(
        None, description="Settlement funds analysis"
    )
    funds_coordination_risk: RiskLevel = Field(
        ..., description="Risk of funds coordination issues"
    )

    # Possession arrangements
    possession_arrangement: Optional[PossessionArrangement] = Field(
        None, description="Property possession analysis"
    )
    possession_risk: RiskLevel = Field(
        ..., description="Risk related to possession transition"
    )

    # Completion obligations
    completion_obligations: List[CompletionObligation] = Field(
        ..., description="Settlement completion obligations"
    )
    critical_path_analysis: List[str] = Field(
        default_factory=list, description="Critical path for settlement completion"
    )

    # Timeline analysis
    settlement_timeline: List[str] = Field(
        default_factory=list, description="Settlement timeline and milestones"
    )
    coordination_requirements: List[str] = Field(
        default_factory=list, description="Coordination requirements between parties"
    )
    potential_delays: List[str] = Field(
        default_factory=list, description="Potential sources of settlement delays"
    )

    # Risk assessment
    overall_settlement_risk: RiskLevel = Field(
        ..., description="Overall settlement risk level"
    )
    settlement_failure_risks: List[str] = Field(
        default_factory=list, description="Risks that could cause settlement failure"
    )
    buyer_preparation_risks: List[str] = Field(
        default_factory=list, description="Buyer preparation risks"
    )
    vendor_preparation_risks: List[str] = Field(
        default_factory=list, description="Vendor preparation risks"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    preparation_checklist: List[str] = Field(
        default_factory=list, description="Settlement preparation checklist"
    )
    coordination_recommendations: List[str] = Field(
        default_factory=list, description="Coordination recommendations"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness of settlement logistics identification",
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the settlement analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "settlement_date": "2024-03-15",
                "settlement_location": "vendor_solicitor",
                "settlement_method": "In-person with electronic lodgment",
                "required_documents": [
                    {
                        "document_name": "Certificate of Title",
                        "document_type": "certificate_title",
                        "required_by": "vendor",
                        "required_at": "settlement",
                        "original_required": True,
                        "preparation_time_needed": "2-3 business days",
                        "availability_risk": "low",
                    }
                ],
                "total_documents": 12,
                "high_risk_documents": ["Building permit approval"],
                "funds_analysis": {
                    "total_funds_required": 850000.0,
                    "bank_finance_amount": 680000.0,
                    "cash_contribution": 170000.0,
                    "funding_risks": ["Finance approval timing"],
                },
                "overall_settlement_risk": "medium",
                "procedural_complexity": "Standard complexity with electronic elements",
                "confidence_score": 0.88,
                "completeness_score": 0.93,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
