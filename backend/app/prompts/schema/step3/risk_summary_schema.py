from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class RiskItem(BaseModel):
    title: str = Field(..., description="Short risk title")
    description: str = Field(..., description="Detailed description of the risk")
    category: str = Field(..., description="Risk category (e.g., financial, legal, settlement, title)")
    severity: str = Field(..., description="Severity level: low, medium, high, critical")
    likelihood: float = Field(..., ge=0.0, le=1.0, description="Likelihood (0-1)")
    impact: float = Field(..., ge=0.0, le=1.0, description="Impact (0-1)")
    evidence_refs: List[str] = Field(default_factory=list, description="Evidence references")

    @validator("severity", pre=True)
    def normalize_severity(cls, v: str) -> str:
        return (v or "").lower()


class RiskSummaryResult(BaseModel):
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score (0-1)")
    top_risks: List[RiskItem] = Field(default_factory=list, description="Top prioritized risks")
    category_breakdown: Dict[str, float] = Field(default_factory=dict, description="Risk score by category (0-1)")
    rationale: str = Field(..., description="Reasoning behind scoring and prioritization")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in the summary")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generator metadata, stability info, etc.")