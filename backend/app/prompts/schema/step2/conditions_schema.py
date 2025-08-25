"""
Pydantic schema for Conditions Risk Assessment Analysis (Step 2.4)

This schema defines the structured output for condition classification,
finance/inspection term analysis, and timeline dependency mapping.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.schema.enums.entities import PartyRole
from app.schema.enums import (
    ConditionType,
    ConditionCategory,
    ConditionDependencyType,
    RiskLevel,
)


"""
Note: Local enum classes were removed in favor of shared enums from app.schema.enums.
"""


class BusinessDayCalculation(BaseModel):
    """Business day calculation details"""

    calendar_date: Optional[str] = Field(None, description="Calendar date if specified")
    business_days_from_contract: Optional[int] = Field(
        None, description="Business days from contract date"
    )
    calculated_deadline: Optional[str] = Field(
        None, description="Calculated deadline date"
    )
    holiday_considerations: List[str] = Field(
        default_factory=list, description="Holiday considerations affecting calculation"
    )
    calculation_notes: Optional[str] = Field(
        None, description="Notes on calculation methodology"
    )


class ConditionDetail(BaseModel):
    """Individual condition analysis"""

    description: str = Field(..., description="Full description of the condition")
    condition_type: ConditionType = Field(
        ..., description="Classification of condition type"
    )
    category: ConditionCategory = Field(..., description="Condition category")

    # Timeline analysis
    deadline: Optional[str] = Field(None, description="Deadline for satisfaction")
    deadline_calculation: Optional[BusinessDayCalculation] = Field(
        None, description="Deadline calculation details"
    )
    time_sensitive: bool = Field(
        default=False, description="Whether condition is time-sensitive"
    )

    # Satisfaction requirements
    satisfaction_requirements: List[str] = Field(
        default_factory=list, description="Requirements for satisfaction"
    )
    party_responsible: Optional[List[PartyRole]] = Field(
        None, description="Party responsible for satisfaction"
    )
    evidence_required: List[str] = Field(
        default_factory=list, description="Evidence required for satisfaction"
    )

    # Risk assessment
    risk_level: RiskLevel = Field(..., description="Assessed risk level")
    risk_factors: List[str] = Field(
        default_factory=list, description="Identified risk factors"
    )
    failure_consequences: List[str] = Field(
        default_factory=list, description="Consequences of failure to satisfy"
    )

    # Analysis notes
    unusual_aspects: List[str] = Field(
        default_factory=list, description="Unusual or non-standard aspects"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for this condition"
    )


class FinanceConditionAnalysis(BaseModel):
    """Detailed finance condition analysis"""

    finance_required: bool = Field(..., description="Whether finance is required")
    loan_amount: Optional[float] = Field(None, description="Loan amount specified")
    loan_percentage: Optional[float] = Field(
        None, description="Loan as percentage of purchase price"
    )

    approval_timeframe: Optional[str] = Field(
        None, description="Finance approval timeframe"
    )
    approval_timeframe_assessment: str = Field(
        ..., description="Assessment of timeframe adequacy"
    )

    interest_rate_specification: Optional[str] = Field(
        None, description="Interest rate specification"
    )
    lender_restrictions: List[str] = Field(
        default_factory=list, description="Any lender restrictions"
    )

    escape_clause_quality: str = Field(
        ..., description="Assessment of escape clause quality"
    )
    buyer_protection_level: str = Field(..., description="Level of buyer protection")

    finance_risks: List[str] = Field(
        default_factory=list, description="Identified finance-related risks"
    )


class InspectionConditionAnalysis(BaseModel):
    """Detailed inspection condition analysis"""

    inspection_types: List[str] = Field(
        default_factory=list, description="Types of inspections required"
    )
    inspection_timeframe: Optional[str] = Field(
        None, description="Timeframe for inspections"
    )
    timeframe_assessment: str = Field(
        ..., description="Assessment of timeframe adequacy"
    )

    scope_requirements: List[str] = Field(
        default_factory=list, description="Scope requirements for inspections"
    )
    standards_specified: List[str] = Field(
        default_factory=list, description="Standards specified for inspections"
    )

    action_requirements: List[str] = Field(
        default_factory=list, description="Actions required based on inspection results"
    )
    defect_thresholds: Optional[str] = Field(
        None, description="Defect thresholds or materiality requirements"
    )

    access_provisions: List[str] = Field(
        default_factory=list, description="Property access provisions"
    )
    cost_responsibility: Optional[str] = Field(
        None, description="Who bears inspection costs"
    )

    inspection_risks: List[str] = Field(
        default_factory=list, description="Identified inspection-related risks"
    )


class SpecialConditionAnalysis(BaseModel):
    """Analysis of special conditions"""

    condition_description: str = Field(
        ..., description="Description of the special condition"
    )
    condition_purpose: str = Field(
        ..., description="Purpose or rationale for the condition"
    )

    # Risk assessment
    seller_favoring: bool = Field(
        default=False, description="Whether condition favors seller"
    )
    buyer_protection: bool = Field(
        default=False, description="Whether condition protects buyer"
    )
    risk_allocation: str = Field(
        ..., description="How risk is allocated by this condition"
    )

    # Specific analyses for common special conditions
    sunset_clause_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Sunset clause analysis if applicable"
    )
    subject_to_sale_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Subject to sale analysis if applicable"
    )
    development_approval_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Development approval analysis if applicable"
    )

    enforceability_concerns: List[str] = Field(
        default_factory=list, description="Enforceability concerns"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for this special condition"
    )


class TimelineDependency(BaseModel):
    """Timeline dependency between conditions"""

    condition_1: str = Field(..., description="First condition description")
    condition_2: str = Field(..., description="Second condition description")
    dependency_type: ConditionDependencyType = Field(
        ..., description="Type of dependency (sequential, parallel, etc.)"
    )
    potential_conflicts: List[str] = Field(
        default_factory=list, description="Potential timeline conflicts"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations to resolve conflicts"
    )


class ConditionsAnalysisResult(BaseModel):
    """
    Complete result structure for Conditions Risk Assessment Analysis.

    Covers PRD 4.1.2.4 requirements:
    - Condition classification (standard vs special, precedent vs subsequent)
    - Finance condition analysis with approval timeframes
    - Inspection condition review with scope validation
    - Special condition assessment including sunset clauses
    - Timeline dependency mapping and conflict identification
    """

    # Overall condition summary
    total_conditions: int = Field(
        ..., description="Total number of conditions identified"
    )
    standard_conditions_count: int = Field(
        ..., description="Number of standard conditions"
    )
    special_conditions_count: int = Field(
        ..., description="Number of special conditions"
    )

    # Detailed condition analysis
    conditions: List[ConditionDetail] = Field(
        ..., description="Detailed analysis of all conditions"
    )

    # Specialized analyses
    finance_condition: Optional[FinanceConditionAnalysis] = Field(
        None, description="Finance condition analysis"
    )
    inspection_condition: Optional[InspectionConditionAnalysis] = Field(
        None, description="Inspection condition analysis"
    )
    special_conditions: List[SpecialConditionAnalysis] = Field(
        default_factory=list, description="Special condition analyses"
    )

    # Timeline and dependency analysis
    timeline_dependencies: List[TimelineDependency] = Field(
        default_factory=list, description="Timeline dependencies between conditions"
    )
    critical_deadlines: List[str] = Field(
        default_factory=list, description="Critical deadlines in chronological order"
    )
    timeline_risks: List[str] = Field(
        default_factory=list, description="Timeline-related risks"
    )

    # Risk assessment
    overall_condition_risk: RiskLevel = Field(
        ..., description="Overall risk level for all conditions"
    )
    high_risk_conditions: List[str] = Field(
        default_factory=list, description="Conditions assessed as high risk"
    )

    # Summary assessments
    buyer_protection_level: str = Field(
        ..., description="Overall buyer protection level"
    )
    seller_advantage_assessment: str = Field(
        ..., description="Assessment of seller advantages in conditions"
    )
    unusual_conditions_summary: Optional[str] = Field(
        None, description="Summary of unusual conditions"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    negotiation_points: List[str] = Field(
        default_factory=list, description="Key negotiation points"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness of condition identification"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    seed_references: List[str] = Field(
        default_factory=list,
        description="Identifiers or brief references to seed snippets used (e.g., clause ids)",
    )
    retrieval_expanded: bool = Field(
        default=False, description="Whether targeted retrieval beyond seeds was used"
    )
    retrieved_snippets_count: int = Field(
        default=0, ge=0, description="Number of additional snippets retrieved"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the conditions analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_conditions": 5,
                "standard_conditions_count": 3,
                "special_conditions_count": 2,
                "conditions": [
                    {
                        "description": "Finance approval within 21 business days",
                        "condition_type": "precedent",
                        "category": "finance",
                        "deadline": "2024-02-15",
                        "risk_level": "medium",
                        "satisfaction_requirements": ["Unconditional loan approval"],
                        "party_responsible": "purchaser",
                    }
                ],
                "finance_condition": {
                    "finance_required": True,
                    "loan_amount": 640000.0,
                    "loan_percentage": 80.0,
                    "approval_timeframe": "21 business days",
                    "approval_timeframe_assessment": "Adequate for standard home loan",
                    "escape_clause_quality": "Standard buyer protection",
                    "buyer_protection_level": "Good",
                },
                "overall_condition_risk": "medium",
                "buyer_protection_level": "Good - standard market conditions",
                "confidence_score": 0.92,
                "completeness_score": 0.95,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
