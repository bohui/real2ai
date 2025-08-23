"""
Pydantic schema for Adjustments and Outgoings Calculator (Step 2.9)

This schema defines the structured output for settlement adjustments,
outgoings calculations, and apportionment analysis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import date


class AdjustmentType(str, Enum):
    """Type of settlement adjustment"""

    RATES = "rates"
    LAND_TAX = "land_tax"
    WATER_RATES = "water_rates"
    SEWERAGE_RATES = "sewerage_rates"
    STRATA_LEVIES = "strata_levies"
    RENT = "rent"
    OUTGOINGS = "outgoings"
    INSURANCE = "insurance"
    UTILITIES = "utilities"
    BODY_CORPORATE = "body_corporate"
    OTHER = "other"


class ApportionmentBasis(str, Enum):
    """Basis for apportionment calculation"""

    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ACTUAL_USAGE = "actual_usage"
    PRO_RATA = "pro_rata"


class CalculationMethod(str, Enum):
    """Method of calculation"""

    STANDARD = "standard"
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    AGREED = "agreed"
    STATUTORY = "statutory"


class RiskLevel(str, Enum):
    """Risk level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AdjustmentItem(BaseModel):
    """Individual adjustment calculation"""

    item_name: str = Field(..., description="Name of the adjustment item")
    adjustment_type: AdjustmentType = Field(..., description="Type classification")

    # Calculation details
    total_amount: Optional[float] = Field(
        None, description="Total amount for the period"
    )
    period_covered: Optional[str] = Field(
        None, description="Period covered by the amount"
    )
    apportionment_basis: ApportionmentBasis = Field(
        ..., description="Basis for apportionment"
    )
    calculation_method: CalculationMethod = Field(
        ..., description="Method of calculation"
    )

    # Apportionment calculation
    vendor_portion: Optional[float] = Field(
        None, description="Vendor's portion of the amount"
    )
    purchaser_portion: Optional[float] = Field(
        None, description="Purchaser's portion of the amount"
    )
    apportionment_date: Optional[str] = Field(
        None, description="Date for apportionment calculation"
    )

    # Verification details
    supporting_documentation: List[str] = Field(
        default_factory=list, description="Supporting documentation required"
    )
    verification_method: Optional[str] = Field(
        None, description="Method for verifying amounts"
    )

    # Risk assessment
    calculation_risk: RiskLevel = Field(..., description="Risk of calculation errors")
    documentation_risk: RiskLevel = Field(
        ..., description="Risk of inadequate documentation"
    )
    disputes_risk: RiskLevel = Field(
        ..., description="Risk of disputes over calculation"
    )

    # Notes and recommendations
    calculation_notes: Optional[str] = Field(
        None, description="Notes on calculation methodology"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for this adjustment"
    )


class OutgoingsAnalysis(BaseModel):
    """Property outgoings analysis"""

    ongoing_outgoings: List[str] = Field(
        default_factory=list, description="Ongoing property outgoings"
    )
    annual_outgoings_estimate: Optional[float] = Field(
        None, description="Estimated annual outgoings"
    )

    # Apportionment requirements
    apportionment_required: List[str] = Field(
        default_factory=list, description="Items requiring apportionment"
    )
    apportionment_calculations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Detailed apportionment calculations"
    )

    # Documentation requirements
    vendor_responsibilities: List[str] = Field(
        default_factory=list, description="Vendor documentation responsibilities"
    )
    purchaser_responsibilities: List[str] = Field(
        default_factory=list, description="Purchaser documentation responsibilities"
    )

    # Timing analysis
    timing_for_calculations: List[str] = Field(
        default_factory=list, description="Timing requirements for calculations"
    )
    settlement_statement_preparation: Optional[str] = Field(
        None, description="Settlement statement preparation timeline"
    )


class StrataLevyAnalysis(BaseModel):
    """Strata levy and body corporate analysis"""

    strata_levies_current: bool = Field(
        ..., description="Whether strata levies are current"
    )
    outstanding_levies: Optional[float] = Field(
        None, description="Outstanding levy amounts"
    )

    # Levy details
    quarterly_levy_amount: Optional[float] = Field(
        None, description="Quarterly levy amount"
    )
    special_levies: List[Dict[str, Any]] = Field(
        default_factory=list, description="Special levy details"
    )

    # Apportionment
    levy_apportionment_method: Optional[str] = Field(
        None, description="Method for levy apportionment"
    )
    settlement_adjustments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Required settlement adjustments"
    )

    # Risk assessment
    levy_arrears_risk: RiskLevel = Field(..., description="Risk of levy arrears")
    special_levy_risk: RiskLevel = Field(
        ..., description="Risk of unexpected special levies"
    )

    # Verification requirements
    strata_search_required: bool = Field(
        default=True, description="Whether strata search is required"
    )
    body_corporate_certificates: List[str] = Field(
        default_factory=list, description="Required body corporate certificates"
    )


class UtilityAdjustment(BaseModel):
    """Utility adjustment analysis"""

    utility_type: str = Field(
        ..., description="Type of utility (electricity, gas, water, etc.)"
    )

    # Account details
    account_number: Optional[str] = Field(
        None, description="Utility account number if available"
    )
    account_holder: Optional[str] = Field(None, description="Current account holder")

    # Transfer arrangements
    transfer_required: bool = Field(
        default=True, description="Whether account transfer is required"
    )
    transfer_procedures: List[str] = Field(
        default_factory=list, description="Account transfer procedures"
    )

    # Adjustments
    final_reading_required: bool = Field(
        default=True, description="Whether final reading is required"
    )
    adjustment_calculation: Optional[str] = Field(
        None, description="Method for adjustment calculation"
    )
    estimated_adjustment: Optional[float] = Field(
        None, description="Estimated adjustment amount"
    )

    # Risk factors
    transfer_risks: List[str] = Field(
        default_factory=list, description="Account transfer risks"
    )
    adjustment_disputes_risk: RiskLevel = Field(
        ..., description="Risk of adjustment disputes"
    )


class TaxAdjustment(BaseModel):
    """Tax and statutory charges adjustment"""

    tax_type: str = Field(..., description="Type of tax or charge")

    # Current status
    current_status: str = Field(..., description="Current payment status")
    amount_owing: Optional[float] = Field(None, description="Amount currently owing")

    # Apportionment
    apportionment_required: bool = Field(
        default=True, description="Whether apportionment is required"
    )
    apportionment_method: Optional[str] = Field(
        None, description="Method for apportionment"
    )
    vendor_liability: Optional[float] = Field(
        None, description="Vendor's liability portion"
    )
    purchaser_liability: Optional[float] = Field(
        None, description="Purchaser's liability portion"
    )

    # Risk assessment
    calculation_complexity: str = Field(..., description="Complexity of calculation")
    verification_requirements: List[str] = Field(
        default_factory=list, description="Verification requirements"
    )
    dispute_risk: RiskLevel = Field(
        ..., description="Risk of disputes over calculation"
    )


class AdjustmentsAnalysisResult(BaseModel):
    """
    Complete result structure for Adjustments and Outgoings Calculator.

    Covers PRD 4.1.2.9 requirements:
    - Complete adjustment identification and calculation
    - Outgoings apportionment analysis
    - Strata levy and body corporate adjustments
    - Utility account transfer and adjustment coordination
    - Tax and statutory charge apportionment
    """

    # Overall adjustment summary
    total_adjustments: int = Field(
        ..., description="Total number of adjustments identified"
    )
    total_adjustment_amount: Optional[float] = Field(
        None, description="Total estimated adjustment amount"
    )
    net_adjustment_to_purchaser: Optional[float] = Field(
        None, description="Net adjustment amount to purchaser"
    )

    # Detailed adjustments
    adjustment_items: List[AdjustmentItem] = Field(
        ..., description="Detailed adjustment analysis"
    )
    high_value_adjustments: List[str] = Field(
        default_factory=list, description="High-value adjustments requiring attention"
    )

    # Specialized analyses
    outgoings_analysis: Optional[OutgoingsAnalysis] = Field(
        None, description="Property outgoings analysis"
    )
    strata_levy_analysis: Optional[StrataLevyAnalysis] = Field(
        None, description="Strata levy analysis"
    )
    utility_adjustments: List[UtilityAdjustment] = Field(
        default_factory=list, description="Utility adjustment analysis"
    )
    tax_adjustments: List[TaxAdjustment] = Field(
        default_factory=list, description="Tax and statutory adjustment analysis"
    )

    # Settlement statement preparation
    settlement_statement_requirements: List[str] = Field(
        default_factory=list,
        description="Settlement statement preparation requirements",
    )
    documentation_timeline: List[str] = Field(
        default_factory=list, description="Documentation preparation timeline"
    )

    # Verification and accuracy
    verification_procedures: List[str] = Field(
        default_factory=list, description="Required verification procedures"
    )
    accuracy_safeguards: List[str] = Field(
        default_factory=list, description="Accuracy safeguards and cross-checks"
    )

    # Risk assessment
    overall_adjustment_risk: RiskLevel = Field(
        ..., description="Overall adjustment and calculation risk"
    )
    calculation_dispute_risk: RiskLevel = Field(
        ..., description="Risk of calculation disputes"
    )
    documentation_risk: RiskLevel = Field(
        ..., description="Risk of inadequate documentation"
    )

    # Timing coordination
    preparation_timeline: List[str] = Field(
        default_factory=list, description="Preparation timeline for adjustments"
    )
    coordination_requirements: List[str] = Field(
        default_factory=list, description="Coordination requirements with parties"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    preparation_checklist: List[str] = Field(
        default_factory=list, description="Adjustment preparation checklist"
    )
    verification_recommendations: List[str] = Field(
        default_factory=list, description="Verification recommendations"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness of adjustment identification"
    )
    calculation_accuracy_score: float = Field(
        ..., ge=0.0, le=1.0, description="Accuracy confidence for calculations"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    calculation_references: List[str] = Field(
        default_factory=list, description="References to calculation methodologies"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the adjustments analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_adjustments": 7,
                "total_adjustment_amount": 2450.75,
                "net_adjustment_to_purchaser": -320.50,
                "adjustment_items": [
                    {
                        "item_name": "Council rates",
                        "adjustment_type": "rates",
                        "total_amount": 1800.00,
                        "period_covered": "Annual assessment",
                        "apportionment_basis": "daily",
                        "calculation_method": "standard",
                        "vendor_portion": 900.00,
                        "purchaser_portion": 900.00,
                        "calculation_risk": "low",
                        "documentation_risk": "low",
                        "disputes_risk": "low",
                    }
                ],
                "strata_levy_analysis": {
                    "strata_levies_current": True,
                    "quarterly_levy_amount": 850.00,
                    "levy_apportionment_method": "Daily pro-rata",
                    "levy_arrears_risk": "low",
                    "special_levy_risk": "medium",
                },
                "overall_adjustment_risk": "low",
                "calculation_dispute_risk": "low",
                "documentation_risk": "medium",
                "confidence_score": 0.91,
                "completeness_score": 0.95,
                "calculation_accuracy_score": 0.93,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
