from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    SETTLEMENT = "settlement"
    TITLE = "title"
    PROPERTY = "property"
    OTHER = "other"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskItem(BaseModel):
    title: str = Field(..., description="Short risk title")
    description: str = Field(..., description="Detailed description of the risk")
    category: RiskCategory = Field(..., description="Risk category")
    severity: SeverityLevel = Field(..., description="Severity level")
    likelihood: float = Field(..., ge=0.0, le=1.0, description="Likelihood (0-1)")
    impact: float = Field(..., ge=0.0, le=1.0, description="Impact (0-1)")
    evidence_refs: List[str] = Field(default_factory=list, description="Evidence references")


class RiskSummaryResult(BaseModel):
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score (0-1)")
    top_risks: List[RiskItem] = Field(default_factory=list, description="Top prioritized risks")
    category_breakdown: Dict[RiskCategory, float] = Field(default_factory=dict, description="Risk score by category (0-1)")
    rationale: str = Field(..., description="Reasoning behind scoring and prioritization")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in the summary")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generator metadata, stability info, etc.")

    @validator("top_risks", pre=True)
    def sort_risks(cls, v: List[Dict]) -> List[Dict]:
        if not v:
            return []
        # Define order for severity
        severity_order = {SeverityLevel.LOW: 1, SeverityLevel.MEDIUM: 2, SeverityLevel.HIGH: 3, SeverityLevel.CRITICAL: 4}
        return sorted(v, key=lambda r: (severity_order.get(r.get("severity"), 0), r.get("likelihood", 0.0) * r.get("impact", 0.0)), reverse=True)
