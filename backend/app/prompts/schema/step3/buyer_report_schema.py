from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class SectionType(str, Enum):
    PARTIES_PROPERTY = "parties_property"
    FINANCIAL_TERMS = "financial_terms"
    CONDITIONS = "conditions"
    WARRANTIES = "warranties"
    DEFAULT_TERMINATION = "default_termination"
    SETTLEMENT_LOGISTICS = "settlement_logistics"
    TITLE_ENCUMBRANCES = "title_encumbrances"
    ADJUSTMENTS_OUTGOINGS = "adjustments_outgoings"
    DISCLOSURE_COMPLIANCE = "disclosure_compliance"
    SPECIAL_RISKS = "special_risks"
    CROSS_SECTION_VALIDATION = "cross_section_validation"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SectionSummary(BaseModel):
    section_type: SectionType = Field(..., description="Type of section")
    name: str = Field(
        ..., min_length=3, max_length=50, description="Display name for the section"
    )
    summary: str = Field(
        ..., min_length=20, max_length=300, description="Summary for the section"
    )
    status: str = Field(..., description="Status: OK, WARNING, or ISSUE")

    @field_validator("status")
    def validate_status(cls, v):
        valid_statuses = ["OK", "WARNING", "ISSUE"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class KeyRisk(BaseModel):
    title: str = Field(..., min_length=5, max_length=80, description="Risk title")
    description: str = Field(
        ..., min_length=20, max_length=200, description="Brief risk description"
    )
    severity: RiskSeverity = Field(..., description="Risk severity level")
    impact_summary: str = Field(
        ..., min_length=10, max_length=150, description="Brief impact summary"
    )

    @field_validator("title", "description", "impact_summary")
    def validate_strings(cls, v):
        return v.strip() if v else v


class ActionPlanOverviewItem(BaseModel):
    title: str = Field(..., min_length=5, max_length=80, description="Action title")
    owner: str = Field(
        ..., min_length=3, max_length=20, description="Responsible party"
    )
    urgency: str = Field(..., description="IMMEDIATE, HIGH, MEDIUM, or LOW")
    timeline: Optional[str] = Field(
        None, max_length=50, description="Expected timeline"
    )

    @field_validator("urgency")
    def validate_urgency(cls, v):
        valid_urgencies = ["IMMEDIATE", "HIGH", "MEDIUM", "LOW"]
        if v not in valid_urgencies:
            raise ValueError(f"Urgency must be one of {valid_urgencies}")
        return v


class BuyerReportResult(BaseModel):
    executive_summary: str = Field(
        ...,
        min_length=100,
        max_length=800,
        description="Buyer-facing executive summary",
    )
    section_summaries: List[SectionSummary] = Field(
        ..., min_items=3, max_items=12, description="Summaries per major section"
    )
    key_risks: List[KeyRisk] = Field(
        ..., min_items=1, max_items=8, description="Key risks for the buyer"
    )
    action_plan_overview: List[ActionPlanOverviewItem] = Field(
        ..., min_items=1, max_items=15, description="High-level action plan overview"
    )
    evidence_refs: List[str] = Field(
        ..., min_items=1, description="Evidence references used in report"
    )
    overall_recommendation: str = Field(
        ..., description="PROCEED, PROCEED_WITH_CAUTION, or RECONSIDER"
    )
    confidence_level: float = Field(
        ..., ge=0.7, le=1.0, description="Confidence in the analysis (minimum 0.7)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata and rendering hints"
    )

    @field_validator("overall_recommendation")
    def validate_recommendation(cls, v):
        valid_recommendations = ["PROCEED", "PROCEED_WITH_CAUTION", "RECONSIDER"]
        if v not in valid_recommendations:
            raise ValueError(
                f"Overall recommendation must be one of {valid_recommendations}"
            )
        return v

    @field_validator("evidence_refs")
    def validate_evidence_refs(cls, v):
        if not v:
            raise ValueError("Must provide at least one evidence reference")
        return [ref.strip() for ref in v if ref and ref.strip()]

    @field_validator("section_summaries")
    def validate_unique_sections(cls, v):
        section_types = [summary.section_type for summary in v]
        if len(section_types) != len(set(section_types)):
            raise ValueError("Section types must be unique")
        return v

    @field_validator("key_risks")
    def sort_risks_by_severity(cls, v):
        severity_order = {
            RiskSeverity.CRITICAL: 4,
            RiskSeverity.HIGH: 3,
            RiskSeverity.MEDIUM: 2,
            RiskSeverity.LOW: 1,
        }
        return sorted(v, key=lambda r: severity_order.get(r.severity, 0), reverse=True)

    @field_validator("action_plan_overview")
    def sort_actions_by_urgency(cls, v):
        urgency_order = {"IMMEDIATE": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return sorted(v, key=lambda a: urgency_order.get(a.urgency, 0), reverse=True)
