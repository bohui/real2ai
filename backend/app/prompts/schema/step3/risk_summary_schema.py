from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    SETTLEMENT = "settlement"
    TITLE = "title"
    PROPERTY = "property"
    COMPLIANCE = "compliance"
    OTHER = "other"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskItem(BaseModel):
    title: str = Field(
        ..., min_length=5, max_length=100, description="Short risk title"
    )
    description: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Detailed description of the risk",
    )
    category: RiskCategory = Field(..., description="Risk category")
    severity: SeverityLevel = Field(..., description="Severity level")
    likelihood: float = Field(..., ge=0.0, le=1.0, description="Likelihood (0-1)")
    impact: float = Field(..., ge=0.0, le=1.0, description="Impact (0-1)")
    evidence_refs: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Evidence references from Step 2 analysis",
    )

    @field_validator("evidence_refs", mode="after")
    def validate_evidence_refs(cls, v: List[str]) -> List[str]:
        cleaned: List[str] = []
        for ref in v:
            if not ref or len(ref.strip()) < 3:
                raise ValueError("Evidence reference must be meaningful and non-empty")
            cleaned.append(ref.strip())
        return cleaned

    @property
    def risk_score(self) -> float:
        """Calculate combined risk score from likelihood and impact"""
        return self.likelihood * self.impact


class RiskSummaryResult(BaseModel):
    overall_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall risk score (0-1)"
    )
    top_risks: List[RiskItem] = Field(
        ..., min_items=1, max_items=10, description="Top prioritized risks"
    )
    category_breakdown: Dict[RiskCategory, float] = Field(
        ..., description="Risk score by category (0-1)"
    )
    rationale: str = Field(
        ...,
        min_length=50,
        max_length=1000,
        description="Reasoning behind scoring and prioritization",
    )
    confidence: float = Field(
        ..., ge=0.5, le=1.0, description="Model confidence in the summary (minimum 0.5)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Generator metadata, stability info, etc."
    )

    @field_validator("category_breakdown", mode="after")
    def validate_category_breakdown(
        cls, v: Dict[RiskCategory, float]
    ) -> Dict[RiskCategory, float]:
        if not v:
            raise ValueError("Category breakdown cannot be empty")
        for category, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(
                    f"Category score for {category} must be between 0.0 and 1.0"
                )
        return v

    @field_validator("top_risks", mode="after")
    def sort_and_validate_risks(cls, v: List[RiskItem]) -> List[RiskItem]:
        if not v:
            raise ValueError("Must provide at least one risk")

        # Define order for severity
        severity_order = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }

        # Sort by severity first, then by risk score (likelihood * impact)
        sorted_risks = sorted(
            v,
            key=lambda r: (severity_order.get(r.severity, 0), r.risk_score),
            reverse=True,
        )

        # Ensure at least one high or critical risk if overall score > 0.7
        return sorted_risks

    @model_validator(mode="after")
    def validate_consistency(self):
        overall_score = self.overall_risk_score
        top_risks = self.top_risks or []
        category_breakdown = self.category_breakdown or {}

        if not top_risks:
            return self

        # Check that overall score is consistent with top risks
        max_risk_score = max((risk.risk_score for risk in top_risks), default=0)
        if overall_score > 0.8 and max_risk_score < 0.5:
            raise ValueError(
                "High overall risk score should have at least one significant individual risk"
            )

        # Ensure category breakdown includes categories from top risks
        risk_categories = {risk.category for risk in top_risks}
        missing_categories = risk_categories - set(category_breakdown.keys())
        if missing_categories:
            raise ValueError(
                f"Category breakdown missing categories from top risks: {missing_categories}"
            )

        return self
