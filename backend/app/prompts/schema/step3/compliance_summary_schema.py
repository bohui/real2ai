from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    REQUIRES_REVIEW = "requires_review"


class ComplianceGap(BaseModel):
    name: str = Field(..., min_length=5, max_length=100, description="Gap name or requirement")
    description: str = Field(..., min_length=20, max_length=500, description="Description of the gap")
    severity: SeverityLevel = Field(..., description="Severity level")
    remediation: str = Field(..., min_length=20, max_length=400, description="Suggested remediation")
    legal_reference: Optional[str] = Field(None, max_length=200, description="Relevant legal reference")
    estimated_remediation_days: Optional[int] = Field(None, ge=1, le=90, description="Days to remediate")
    
    @validator("name", "description", "remediation")
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class ComplianceSummaryResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Compliance score (0-1)")
    status: ComplianceStatus = Field(..., description="Overall compliance status")
    gaps: List[ComplianceGap] = Field(default_factory=list, max_items=15, description="Identified gaps")
    remediation_readiness: str = Field(..., min_length=20, max_length=500, description="Readiness level description")
    key_dependencies: List[str] = Field(default_factory=list, max_items=10, description="Dependencies impacting compliance")
    total_gaps_by_severity: Dict[SeverityLevel, int] = Field(default_factory=dict, description="Count of gaps by severity")
    estimated_remediation_timeline: Optional[int] = Field(None, ge=1, description="Total estimated remediation days")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and provenance")
    
    @validator("score")
    def validate_score_consistency(cls, v, values):
        # Score should reflect severity of gaps
        return v
    
    @validator("key_dependencies")
    def validate_dependencies(cls, v):
        return [dep.strip() for dep in v if dep and dep.strip()]
    
    @root_validator
    def validate_compliance_consistency(cls, values):
        score = values.get("score", 0)
        gaps = values.get("gaps", [])
        status = values.get("status")
        
        # Calculate gaps by severity
        severity_count = {}
        for gap in gaps:
            severity_count[gap.severity] = severity_count.get(gap.severity, 0) + 1
        
        values["total_gaps_by_severity"] = severity_count
        
        # Validate score consistency with gaps
        critical_gaps = severity_count.get(SeverityLevel.CRITICAL, 0)
        high_gaps = severity_count.get(SeverityLevel.HIGH, 0)
        
        if critical_gaps > 0 and score > 0.8:
            raise ValueError("Score cannot be high (>0.8) with critical compliance gaps")
        
        if critical_gaps > 2 and score > 0.5:
            raise ValueError("Score cannot be medium (>0.5) with multiple critical gaps")
        
        # Validate status consistency
        if score >= 0.9 and status != ComplianceStatus.COMPLIANT:
            raise ValueError("High score should indicate compliant status")
        
        if critical_gaps > 0 and status == ComplianceStatus.COMPLIANT:
            raise ValueError("Cannot be compliant with critical gaps")
        
        return values
