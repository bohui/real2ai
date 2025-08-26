from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ComplianceGap(BaseModel):
    name: str = Field(..., description="Gap name or requirement")
    description: str = Field(..., description="Description of the gap")
    severity: str = Field(..., description="low, medium, high, critical")
    remediation: str = Field(..., description="Suggested remediation")


class ComplianceSummaryResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Compliance score (0-1)")
    gaps: List[ComplianceGap] = Field(default_factory=list, description="Identified gaps")
    remediation_readiness: str = Field(..., description="Readiness level description")
    key_dependencies: List[str] = Field(default_factory=list, description="Dependencies impacting compliance")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and provenance")