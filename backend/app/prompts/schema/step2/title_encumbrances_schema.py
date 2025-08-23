"""
Pydantic schema for Title and Encumbrances Analysis with Diagram Integration (Step 2.8)

This schema defines the structured output for title analysis, encumbrance assessment,
and comprehensive diagram integration covering 20+ diagram types.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schema.enums import RiskLevel
from app.schema.enums.diagrams import DiagramType


class EncumbranceType(str, Enum):
    """Type of property encumbrance"""

    MORTGAGE = "mortgage"
    EASEMENT = "easement"
    COVENANT = "covenant"
    CAVEAT = "caveat"
    LEASE = "lease"
    LICENSE = "license"
    RESTRICTION = "restriction"
    CHARGE = "charge"
    LIEN = "lien"
    STATUTORY = "statutory"
    OTHER = "other"


class TitleAnalysis(BaseModel):
    """Title analysis details"""

    title_reference: Optional[str] = Field(
        None, description="Title reference (Volume/Folio or identifier)"
    )
    title_type: Optional[str] = Field(
        None, description="Type of title (Torrens, Old System, etc.)"
    )

    # Ownership analysis
    registered_proprietor: Optional[str] = Field(
        None, description="Registered proprietor details"
    )
    ownership_structure: Optional[str] = Field(
        None, description="Ownership structure analysis"
    )
    capacity_to_sell: str = Field(
        ..., description="Assessment of vendor's capacity to sell"
    )

    # Title quality
    title_quality: str = Field(..., description="Overall title quality assessment")
    title_defects: List[str] = Field(
        default_factory=list, description="Identified title defects"
    )
    investigation_requirements: List[str] = Field(
        default_factory=list, description="Required title investigations"
    )

    # Guarantees and insurance
    title_insurance_required: bool = Field(
        default=False, description="Whether title insurance is required"
    )
    title_guarantee_provisions: List[str] = Field(
        default_factory=list, description="Title guarantee provisions"
    )


class Encumbrance(BaseModel):
    """Individual encumbrance analysis"""

    encumbrance_description: str = Field(
        ..., description="Description of the encumbrance"
    )
    encumbrance_type: EncumbranceType = Field(..., description="Type classification")
    registration_details: Optional[str] = Field(
        None, description="Registration details"
    )

    # Impact assessment
    affects_property_use: bool = Field(
        default=False, description="Whether it affects property use"
    )
    affects_property_value: bool = Field(
        default=False, description="Whether it affects property value"
    )
    impact_description: str = Field(..., description="Description of impact")

    # Removal prospects
    can_be_removed: bool = Field(
        default=False, description="Whether encumbrance can be removed"
    )
    removal_requirements: List[str] = Field(
        default_factory=list, description="Requirements for removal"
    )
    removal_cost: Optional[float] = Field(None, description="Estimated cost of removal")
    removal_timeframe: Optional[str] = Field(None, description="Timeframe for removal")

    # Risk assessment
    risk_level: RiskLevel = Field(..., description="Risk level for buyer")
    ongoing_obligations: List[str] = Field(
        default_factory=list, description="Ongoing obligations from encumbrance"
    )

    # Recommendations
    buyer_actions: List[str] = Field(
        default_factory=list, description="Required buyer actions"
    )
    investigation_needed: List[str] = Field(
        default_factory=list, description="Further investigation needed"
    )


class DiagramAnalysis(BaseModel):
    """Comprehensive diagram analysis"""

    diagram_reference: str = Field(
        ..., description="Reference or identifier for diagram"
    )
    diagram_type: DiagramType = Field(..., description="Type classification")

    # Content analysis
    shows_property_boundaries: bool = Field(
        default=False, description="Whether it shows property boundaries"
    )
    shows_easements: bool = Field(
        default=False, description="Whether it shows easements"
    )
    shows_services: bool = Field(
        default=False, description="Whether it shows services/utilities"
    )
    shows_improvements: bool = Field(
        default=False, description="Whether it shows improvements"
    )

    # Quality assessment
    diagram_quality: str = Field(..., description="Quality and clarity assessment")
    completeness: str = Field(..., description="Completeness of information shown")
    accuracy_indicators: List[str] = Field(
        default_factory=list, description="Indicators of accuracy"
    )

    # Title integration
    consistent_with_title: bool = Field(
        default=True, description="Whether consistent with title description"
    )
    discrepancies_identified: List[str] = Field(
        default_factory=list, description="Discrepancies with title or contract"
    )

    # Legal status
    legal_status: str = Field(
        ..., description="Legal status of diagram (approved, draft, etc.)"
    )
    approval_details: Optional[str] = Field(
        None, description="Approval details if applicable"
    )

    # Risk assessment
    reliance_risk: RiskLevel = Field(..., description="Risk of relying on this diagram")
    verification_needed: List[str] = Field(
        default_factory=list, description="Verification needed before reliance"
    )

    # Practical implications
    practical_implications: List[str] = Field(
        default_factory=list, description="Practical implications for buyer"
    )
    future_development_impact: Optional[str] = Field(
        None, description="Impact on future development potential"
    )


class ServicesAndUtilities(BaseModel):
    """Services and utilities analysis from diagrams"""

    available_services: List[str] = Field(
        default_factory=list, description="Services shown as available"
    )
    service_locations: Dict[str, str] = Field(
        default_factory=dict, description="Service connection locations"
    )

    # Adequacy assessment
    service_adequacy: str = Field(
        ..., description="Adequacy of services for property use"
    )
    upgrade_requirements: List[str] = Field(
        default_factory=list, description="Required service upgrades"
    )

    # Connection analysis
    connection_responsibilities: Dict[str, str] = Field(
        default_factory=dict, description="Connection responsibilities by service"
    )
    connection_costs: Dict[str, float] = Field(
        default_factory=dict, description="Estimated connection costs"
    )

    # Risk factors
    service_risks: List[str] = Field(
        default_factory=list, description="Service-related risks"
    )
    capacity_concerns: List[str] = Field(
        default_factory=list, description="Service capacity concerns"
    )


class BoundaryAnalysis(BaseModel):
    """Property boundary analysis from diagrams"""

    boundary_clarity: str = Field(..., description="Clarity of boundary definitions")
    boundary_markers: List[str] = Field(
        default_factory=list, description="Boundary markers shown"
    )

    # Encroachment assessment
    potential_encroachments: List[str] = Field(
        default_factory=list, description="Potential encroachments identified"
    )
    encroachment_risks: List[str] = Field(
        default_factory=list, description="Encroachment risks"
    )

    # Survey requirements
    survey_accuracy: str = Field(..., description="Apparent survey accuracy")
    resurvey_recommended: bool = Field(
        default=False, description="Whether resurvey is recommended"
    )
    resurvey_reasons: List[str] = Field(
        default_factory=list, description="Reasons for resurvey recommendation"
    )

    # Neighbor relationships
    shared_boundaries: List[str] = Field(
        default_factory=list, description="Shared boundary arrangements"
    )
    boundary_disputes_risk: RiskLevel = Field(
        ..., description="Risk of boundary disputes"
    )


class TitleEncumbrancesAnalysisResult(BaseModel):
    """
    Complete result structure for Title and Encumbrances Analysis with Diagram Integration.

    Covers PRD 4.1.2.8 requirements:
    - Comprehensive title analysis and verification
    - Complete encumbrance identification and impact assessment
    - Integrated diagram analysis across 20+ diagram types
    - Services and utilities mapping from diagrams
    - Boundary analysis and encroachment assessment
    """

    # Title analysis
    title_analysis: TitleAnalysis = Field(
        ..., description="Comprehensive title analysis"
    )
    title_verification_required: List[str] = Field(
        default_factory=list, description="Required title verifications"
    )

    # Encumbrances analysis
    total_encumbrances: int = Field(
        ..., description="Total number of encumbrances identified"
    )
    encumbrances: List[Encumbrance] = Field(
        ..., description="Detailed encumbrance analysis"
    )
    high_impact_encumbrances: List[str] = Field(
        default_factory=list, description="High-impact encumbrances"
    )
    removable_encumbrances: List[str] = Field(
        default_factory=list, description="Potentially removable encumbrances"
    )

    # Comprehensive diagram integration
    total_diagrams: int = Field(..., description="Total number of diagrams analyzed")
    diagrams_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Count of diagrams by type"
    )
    diagram_analyses: List[DiagramAnalysis] = Field(
        ..., description="Detailed diagram analysis"
    )

    # Diagram-specific analyses
    services_analysis: Optional[ServicesAndUtilities] = Field(
        None, description="Services and utilities analysis from diagrams"
    )
    boundary_analysis: Optional[BoundaryAnalysis] = Field(
        None, description="Boundary analysis from diagrams"
    )

    # Integration assessment
    diagram_title_consistency: str = Field(
        ..., description="Consistency between diagrams and title"
    )
    diagram_contract_consistency: str = Field(
        ..., description="Consistency between diagrams and contract terms"
    )
    cross_diagram_consistency: str = Field(
        ..., description="Consistency across multiple diagrams"
    )

    # Risk assessment
    overall_title_risk: RiskLevel = Field(
        ..., description="Overall title and encumbrance risk"
    )
    diagram_reliance_risk: RiskLevel = Field(
        ..., description="Risk of relying on provided diagrams"
    )
    title_defect_risk: RiskLevel = Field(..., description="Risk of title defects")
    encumbrance_impact_risk: RiskLevel = Field(
        ..., description="Risk from encumbrance impacts"
    )

    # Title insurance considerations
    title_insurance_recommended: bool = Field(
        default=False, description="Whether title insurance is recommended"
    )
    insurance_coverage_needed: List[str] = Field(
        default_factory=list, description="Types of insurance coverage needed"
    )

    # Verification requirements
    independent_verification_needed: List[str] = Field(
        default_factory=list, description="Items requiring independent verification"
    )
    survey_requirements: List[str] = Field(
        default_factory=list, description="Survey requirements identified"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    investigation_requirements: List[str] = Field(
        default_factory=list, description="Required investigations"
    )
    risk_mitigation: List[str] = Field(
        default_factory=list, description="Risk mitigation strategies"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness of title and encumbrance identification",
    )
    diagram_integration_score: float = Field(
        ..., ge=0.0, le=1.0, description="Quality of diagram integration"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    diagram_references: List[str] = Field(
        default_factory=list, description="References to analyzed diagrams"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the title/encumbrances analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title_analysis": {
                    "title_reference": "Vol 12345 Fol 678",
                    "title_type": "Torrens Title",
                    "registered_proprietor": "John Smith",
                    "capacity_to_sell": "Full capacity confirmed",
                    "title_quality": "Good quality with minor encumbrances",
                    "title_defects": [],
                },
                "total_encumbrances": 3,
                "encumbrances": [
                    {
                        "encumbrance_description": "Easement for drainage 3m wide",
                        "encumbrance_type": "easement",
                        "affects_property_use": True,
                        "affects_property_value": False,
                        "impact_description": "Restricts building in drainage corridor",
                        "can_be_removed": False,
                        "risk_level": "medium",
                    }
                ],
                "total_diagrams": 8,
                "diagrams_by_type": {
                    "floor_plan": 2,
                    "site_plan": 1,
                    "services_diagram": 1,
                    "easement_diagram": 1,
                    "survey_plan": 1,
                    "strata_plan": 2,
                },
                "overall_title_risk": "low",
                "diagram_reliance_risk": "medium",
                "diagram_title_consistency": "Good consistency with minor clarifications needed",
                "confidence_score": 0.90,
                "completeness_score": 0.94,
                "diagram_integration_score": 0.87,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
