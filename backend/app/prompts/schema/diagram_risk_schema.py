from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schema.enums import RiskSeverity, DiagramType, ConfidenceLevel


class DiagramReference(BaseModel):
    diagram_type: DiagramType = Field(..., description="Type of diagram")
    diagram_name: str = Field(..., description="Name/title of the specific diagram")
    page_reference: Optional[str] = Field(
        None, description="Page number or reference in contract"
    )
    section_reference: Optional[str] = Field(
        None, description="Specific section or area of diagram showing the risk"
    )
    diagram_date: Optional[datetime] = Field(
        None, description="Date the diagram was created/updated"
    )
    diagram_scale: Optional[str] = Field(
        None, description="Scale of the diagram (e.g., 1:500)"
    )
    prepared_by: Optional[str] = Field(
        None, description="Who prepared the diagram (surveyor, architect, etc.)"
    )
    confidence_level: Optional[ConfidenceLevel] = Field(
        None, description="Confidence in diagram accuracy (high/medium/low)"
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about this diagram reference"
    )


class BoundaryRisk(BaseModel):
    risk_type: str = Field(..., description="Type of boundary risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    affected_boundaries: List[str] = Field(
        default=[], description="Which boundaries are affected"
    )
    encroachment_details: Optional[str] = Field(
        None, description="Details of any encroachments"
    )
    survey_discrepancies: Optional[str] = Field(
        None, description="Discrepancies between survey and actual"
    )
    potential_impact: str = Field(
        ..., description="Potential financial or legal impact"
    )


class EasementRisk(BaseModel):
    easement_type: str = Field(
        ..., description="Type of easement (drainage, utility, access, etc.)"
    )
    description: str = Field(..., description="Description of easement risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    width_meters: Optional[float] = Field(
        None, description="Width of easement in meters"
    )
    length_meters: Optional[float] = Field(
        None, description="Length of easement in meters"
    )
    affects_building_envelope: bool = Field(
        False, description="Whether easement affects where you can build"
    )
    maintenance_obligations: Optional[str] = Field(
        None, description="Maintenance responsibilities"
    )
    access_restrictions: Optional[str] = Field(
        None, description="Any access restrictions"
    )


class StrataRisk(BaseModel):
    risk_type: str = Field(..., description="Type of strata-related risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    unit_boundary_issues: Optional[str] = Field(
        None, description="Issues with unit boundaries"
    )
    common_property_disputes: Optional[str] = Field(
        None, description="Potential common property disputes"
    )
    exclusive_use_conflicts: Optional[str] = Field(
        None, description="Exclusive use area conflicts"
    )
    shared_facility_limitations: Optional[str] = Field(
        None, description="Limitations on shared facilities"
    )
    body_corporate_implications: Optional[str] = Field(
        None, description="Body corporate fee implications"
    )


class DevelopmentRisk(BaseModel):
    risk_type: str = Field(..., description="Type of development risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    construction_stage: Optional[str] = Field(
        None, description="What construction stage property is in"
    )
    future_development_proximity: Optional[str] = Field(
        None, description="How close future stages will be"
    )
    infrastructure_completion_risk: Optional[str] = Field(
        None, description="Risk of incomplete infrastructure"
    )
    access_road_status: Optional[str] = Field(
        None, description="Status of access roads"
    )
    utility_connection_risk: Optional[str] = Field(
        None, description="Risk with utility connections"
    )


class EnvironmentalRisk(BaseModel):
    risk_type: str = Field(..., description="Type of environmental risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    flood_zone_level: Optional[str] = Field(
        None, description="Flood zone classification"
    )
    bushfire_risk_rating: Optional[str] = Field(
        None, description="Bushfire risk rating"
    )
    slope_stability_issues: Optional[str] = Field(
        None, description="Slope or soil stability concerns"
    )
    drainage_problems: Optional[str] = Field(
        None, description="Drainage or water flow issues"
    )
    contamination_risk: Optional[str] = Field(
        None, description="Potential soil or water contamination"
    )
    noise_pollution_sources: List[str] = Field(
        default=[], description="Noise pollution sources nearby"
    )


class InfrastructureRisk(BaseModel):
    risk_type: str = Field(..., description="Type of infrastructure risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    sewer_pipe_location: Optional[str] = Field(
        None, description="Location of sewer pipes under property"
    )
    utility_line_conflicts: Optional[str] = Field(
        None, description="Conflicts with utility lines"
    )
    power_line_proximity: Optional[str] = Field(
        None, description="Proximity to power lines"
    )
    gas_line_risks: Optional[str] = Field(None, description="Gas line related risks")
    telecommunications_issues: Optional[str] = Field(
        None, description="Telecommunications infrastructure issues"
    )
    maintenance_access_requirements: Optional[str] = Field(
        None, description="Required access for maintenance"
    )


class ZoningRisk(BaseModel):
    risk_type: str = Field(..., description="Type of zoning risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    current_zoning: Optional[str] = Field(
        None, description="Current zoning classification"
    )
    proposed_zoning_changes: Optional[str] = Field(
        None, description="Any proposed zoning changes"
    )
    height_restrictions: Optional[str] = Field(
        None, description="Building height restrictions"
    )
    setback_requirements: Optional[str] = Field(
        None, description="Required setbacks from boundaries"
    )
    land_use_restrictions: List[str] = Field(
        default=[], description="Restrictions on land use"
    )
    heritage_overlay_impacts: Optional[str] = Field(
        None, description="Heritage overlay restrictions"
    )


class DiscrepancyRisk(BaseModel):
    risk_type: str = Field(..., description="Type of discrepancy risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    plan_vs_reality_differences: Optional[str] = Field(
        None, description="Differences between plan and actual property"
    )
    dimension_discrepancies: Optional[str] = Field(
        None, description="Measurement discrepancies"
    )
    area_calculation_errors: Optional[str] = Field(
        None, description="Errors in area calculations"
    )
    feature_location_errors: Optional[str] = Field(
        None, description="Errors in feature locations"
    )
    outdated_survey_information: Optional[str] = Field(
        None, description="Risks from outdated surveys"
    )


class AccessRisk(BaseModel):
    risk_type: str = Field(..., description="Type of access risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    legal_access_issues: Optional[str] = Field(
        None, description="Legal right of access concerns"
    )
    physical_access_limitations: Optional[str] = Field(
        None, description="Physical access limitations"
    )
    shared_driveway_conflicts: Optional[str] = Field(
        None, description="Shared access arrangements"
    )
    emergency_access_compliance: Optional[str] = Field(
        None, description="Emergency access requirements"
    )
    future_access_changes: Optional[str] = Field(
        None, description="Potential future access changes"
    )


class ComplianceRisk(BaseModel):
    risk_type: str = Field(..., description="Type of compliance risk")
    description: str = Field(..., description="Detailed description of the risk")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    linked_diagrams: List[DiagramReference] = Field(
        ..., description="Diagrams that show this risk"
    )
    building_code_compliance: Optional[str] = Field(
        None, description="Building code compliance issues"
    )
    council_approval_risks: Optional[str] = Field(
        None, description="Council approval related risks"
    )
    fire_safety_compliance: Optional[str] = Field(
        None, description="Fire safety compliance issues"
    )
    accessibility_compliance: Optional[str] = Field(
        None, description="Disability access compliance"
    )
    environmental_compliance: Optional[str] = Field(
        None, description="Environmental regulation compliance"
    )


class DiagramRiskAssessment(BaseModel):
    """Main schema for extracting risks from purchase contract diagrams"""

    property_identifier: str = Field(
        ..., description="Property identifier (lot number, address, etc.)"
    )
    assessment_date: datetime = Field(
        default_factory=datetime.now, description="Date of risk assessment"
    )
    diagram_sources: List[DiagramType] = Field(
        ..., description="Types of diagrams analyzed"
    )

    # Risk Categories
    boundary_risks: List[BoundaryRisk] = Field(
        default_factory=list, description="Boundary and encroachment risks"
    )
    easement_risks: List[EasementRisk] = Field(
        default_factory=list, description="Easement and right-of-way risks"
    )
    strata_risks: List[StrataRisk] = Field(
        default_factory=list, description="Strata and body corporate risks"
    )
    development_risks: List[DevelopmentRisk] = Field(
        default_factory=list, description="Development and construction risks"
    )
    environmental_risks: List[EnvironmentalRisk] = Field(
        default_factory=list, description="Environmental and natural disaster risks"
    )
    infrastructure_risks: List[InfrastructureRisk] = Field(
        default_factory=list, description="Infrastructure and utility risks"
    )
    zoning_risks: List[ZoningRisk] = Field(
        default_factory=list, description="Zoning and planning risks"
    )
    discrepancy_risks: List[DiscrepancyRisk] = Field(
        default_factory=list, description="Plan vs reality discrepancy risks"
    )
    access_risks: List[AccessRisk] = Field(
        default_factory=list, description="Access and right-of-way risks"
    )
    compliance_risks: List[ComplianceRisk] = Field(
        default_factory=list, description="Regulatory compliance risks"
    )

    # Overall Assessment
    overall_risk_score: RiskSeverity = Field(..., description="Overall risk assessment")
    total_risks_identified: int = Field(
        0, description="Total number of risks identified"
    )
    high_priority_risks: List[str] = Field(
        default_factory=list, description="List of high priority risk descriptions"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended actions to mitigate risks"
    )

    # Additional Information
    surveyor_recommendations: Optional[str] = Field(
        None, description="Surveyor recommendations if available"
    )
    legal_review_required: bool = Field(
        False, description="Whether legal review is recommended"
    )
    additional_investigations_needed: List[str] = Field(
        default_factory=list, description="Additional investigations recommended"
    )
    estimated_financial_impact: Optional[Dict[str, Any]] = Field(
        None, description="Estimated financial impact of risks"
    )

    model_config = {"use_enum_values": True, "arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def compute_derived_fields(self):
        total = (
            len(self.boundary_risks)
            + len(self.easement_risks)
            + len(self.strata_risks)
            + len(self.development_risks)
            + len(self.environmental_risks)
            + len(self.infrastructure_risks)
            + len(self.zoning_risks)
            + len(self.discrepancy_risks)
            + len(self.access_risks)
            + len(self.compliance_risks)
        )
        object.__setattr__(self, "total_risks_identified", total)

        # If overall_risk_score wasn't explicitly set by caller, compute it
        if self.overall_risk_score is None:
            object.__setattr__(
                self, "overall_risk_score", RiskExtractor.calculate_overall_risk(self)
            )
        return self


# Example usage and helper functions
class RiskExtractor:
    """Helper class for extracting risks from diagram data"""

    @staticmethod
    def calculate_overall_risk(assessment: DiagramRiskAssessment) -> RiskSeverity:
        """Calculate overall risk based on individual risk assessments"""
        all_risks = (
            assessment.boundary_risks
            + assessment.easement_risks
            + assessment.strata_risks
            + assessment.development_risks
            + assessment.environmental_risks
            + assessment.infrastructure_risks
            + assessment.zoning_risks
            + assessment.discrepancy_risks
            + assessment.access_risks
            + assessment.compliance_risks
        )

        if not all_risks:
            return RiskSeverity.LOW

        high_risk_count = sum(
            1 for risk in all_risks if risk.severity == RiskSeverity.HIGH
        )
        critical_risk_count = sum(
            1 for risk in all_risks if risk.severity == RiskSeverity.CRITICAL
        )

        if critical_risk_count > 0:
            return RiskSeverity.CRITICAL
        elif high_risk_count >= 3:
            return RiskSeverity.HIGH
        elif high_risk_count > 0:
            return RiskSeverity.MEDIUM
        else:
            return RiskSeverity.LOW

    @staticmethod
    def create_example_assessment() -> DiagramRiskAssessment:
        """Create an example assessment with linked diagrams"""

        # Example diagram references
        title_plan = DiagramReference(
            diagram_type=DiagramType.TITLE_PLAN,
            diagram_name="Certificate of Title Plan DP123456",
            page_reference="Page 5",
            section_reference="Lot 15 boundaries",
            diagram_scale="1:500",
            prepared_by="Licensed Surveyor ABC",
            confidence_level="high",
        )

        sewer_diagram = DiagramReference(
            diagram_type=DiagramType.SEWER_SERVICE_DIAGRAM,
            diagram_name="Sewer Service Connection Plan",
            page_reference="Attachment C",
            section_reference="Main sewer line under eastern boundary",
            prepared_by="Council Engineering Dept",
            confidence_level="high",
        )

        # Example risks with linked diagrams
        boundary_risk = BoundaryRisk(
            risk_type="Encroachment",
            description="Neighbor's shed extends 0.5m over eastern boundary",
            severity=RiskSeverity.HIGH,
            linked_diagrams=[title_plan],
            affected_boundaries=["Eastern boundary"],
            encroachment_details="Timber shed structure, approximately 2m x 3m",
            potential_impact="May require legal action or negotiation to resolve",
        )

        infrastructure_risk = InfrastructureRisk(
            risk_type="Sewer Main Under Property",
            description="Major sewer main runs directly under proposed building area",
            severity=RiskSeverity.HIGH,
            linked_diagrams=[sewer_diagram],
            sewer_pipe_location="2m from eastern boundary, 1.5m depth",
            maintenance_access_requirements="Council requires 3m clear access zone",
        )

        return DiagramRiskAssessment(
            property_identifier="Lot 15, DP123456",
            diagram_sources=[DiagramType.TITLE_PLAN, DiagramType.SEWER_SERVICE_DIAGRAM],
            boundary_risks=[boundary_risk],
            infrastructure_risks=[infrastructure_risk],
            overall_risk_score=RiskSeverity.MEDIUM,
            total_risks_identified=2,
            high_priority_risks=["Neighbor's shed encroachment"],
            recommended_actions=[
                "Resolve boundary encroachment before settlement",
                "Verify sewer easement requirements",
            ],
        )
