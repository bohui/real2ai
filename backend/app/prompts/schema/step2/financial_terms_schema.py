"""
Pydantic schema for Financial Terms Analysis (Step 2.2)

This schema defines the structured output for purchase price verification,
deposit analysis, payment schedule review, and GST implications assessment.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class FinancialRiskLevel(str, Enum):
    """Financial risk level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriceAssessment(str, Enum):
    """Purchase price assessment against market"""

    UNDER_MARKET = "under_market"
    AT_MARKET = "at_market"
    ABOVE_MARKET = "above_market"
    SIGNIFICANTLY_ABOVE_MARKET = "significantly_above_market"
    INSUFFICIENT_DATA = "insufficient_data"


class DepositSecurityStatus(str, Enum):
    """Deposit security arrangement status"""

    SECURE = "secure"
    STANDARD_RISK = "standard_risk"
    HIGH_RISK = "high_risk"
    INADEQUATE = "inadequate"


class GSTimplication(str, Enum):
    """GST implication classification"""

    NOT_APPLICABLE = "not_applicable"
    GST_INCLUSIVE = "gst_inclusive"
    GST_ADDITIONAL = "gst_additional"
    UNCLEAR = "unclear"
    POTENTIAL_LIABILITY = "potential_liability"


class PurchasePriceVerification(BaseModel):
    """Purchase price analysis and verification"""

    stated_price: Optional[Union[float, str]] = Field(
        None, description="Purchase price as stated in contract"
    )
    price_numeric: Optional[float] = Field(
        None, description="Purchase price as numeric value"
    )
    price_in_words: Optional[str] = Field(
        None, description="Purchase price written in words (if present)"
    )

    arithmetic_accuracy: bool = Field(
        ..., description="Whether all price-related calculations are accurate"
    )
    calculation_errors: List[str] = Field(
        default_factory=list, description="Any calculation errors found"
    )

    market_assessment: PriceAssessment = Field(
        ..., description="Assessment against market comparables"
    )
    market_variance_percentage: Optional[float] = Field(
        None, description="Percentage variance from market (if available)"
    )
    market_comparison_notes: Optional[str] = Field(
        None, description="Notes on market comparison methodology"
    )


class DepositAnalysis(BaseModel):
    """Deposit amount and security analysis"""

    deposit_amount: Optional[float] = Field(
        None, description="Deposit amount specified"
    )
    deposit_percentage: Optional[float] = Field(
        None, description="Deposit as percentage of purchase price"
    )

    payment_timeline: List[str] = Field(
        default_factory=list, description="Deposit payment schedule"
    )
    trust_account_details: Optional[str] = Field(
        None, description="Trust account arrangement details"
    )

    security_status: DepositSecurityStatus = Field(
        ..., description="Assessment of deposit security"
    )
    security_concerns: List[str] = Field(
        default_factory=list, description="Any security concerns identified"
    )
    protection_mechanisms: List[str] = Field(
        default_factory=list, description="Deposit protection mechanisms in place"
    )


class PaymentItem(BaseModel):
    """Individual payment or fee item"""

    description: str = Field(..., description="Description of the payment/fee")
    amount: Optional[float] = Field(None, description="Amount (if specified)")
    due_date: Optional[str] = Field(None, description="Due date (if specified)")
    payment_method: Optional[str] = Field(
        None, description="Payment method requirements"
    )
    notes: Optional[str] = Field(None, description="Additional notes or conditions")


class PaymentScheduleReview(BaseModel):
    """Payment schedule and obligations analysis"""

    progress_payments: List[PaymentItem] = Field(
        default_factory=list,
        description="Progress payment items (for off-plan contracts)",
    )
    additional_fees: List[PaymentItem] = Field(
        default_factory=list, description="Additional fees and charges"
    )
    interest_provisions: List[str] = Field(
        default_factory=list, description="Interest calculation provisions"
    )
    penalty_clauses: List[str] = Field(
        default_factory=list, description="Penalty clauses for late payment"
    )

    cash_flow_assessment: str = Field(
        ..., description="Assessment of buyer's cash flow requirements"
    )
    total_buyer_obligations: Optional[float] = Field(
        None, description="Total financial obligations beyond purchase price"
    )


class GSTImplications(BaseModel):
    """GST analysis and tax implications"""

    gst_status: GSTimplication = Field(
        ..., description="GST implication classification"
    )
    gst_amount: Optional[float] = Field(None, description="GST amount (if applicable)")
    gst_calculation_accuracy: bool = Field(
        default=True, description="Whether GST calculations are accurate"
    )

    vendor_gst_registration: Optional[bool] = Field(
        None, description="Whether vendor is GST registered (if determinable)"
    )
    property_gst_status: Optional[str] = Field(
        None, description="Property GST status (new, residential, commercial)"
    )

    tax_implications: List[str] = Field(
        default_factory=list, description="Other tax implications identified"
    )
    stamp_duty_considerations: Optional[str] = Field(
        None, description="Stamp duty calculation considerations"
    )


class FinancialRiskIndicator(BaseModel):
    """Individual financial risk indicator"""

    category: str = Field(
        ..., description="Risk category (price, deposit, payment, tax)"
    )
    description: str = Field(..., description="Description of the financial risk")
    risk_level: FinancialRiskLevel = Field(..., description="Assessed risk level")
    financial_impact: Optional[float] = Field(
        None, description="Estimated financial impact (if quantifiable)"
    )
    impact_description: str = Field(..., description="Description of potential impact")
    recommendation: str = Field(..., description="Recommended action or mitigation")


class FinancialTermsAnalysisResult(BaseModel):
    """
    Complete result structure for Financial Terms Analysis.

    Covers PRD 4.1.2.2 requirements:
    - Purchase price verification and market assessment
    - Deposit analysis and security evaluation
    - Payment schedule review and cash flow assessment
    - GST implications and tax analysis
    """

    # Purchase Price Analysis
    purchase_price: PurchasePriceVerification = Field(
        ..., description="Purchase price verification and analysis"
    )

    # Deposit Analysis
    deposit: DepositAnalysis = Field(
        ..., description="Deposit amount and security analysis"
    )

    # Payment Schedule
    payment_schedule: PaymentScheduleReview = Field(
        ..., description="Payment obligations and schedule analysis"
    )

    # Tax Implications
    gst_analysis: GSTImplications = Field(
        ..., description="GST and tax implications analysis"
    )

    # Risk Assessment
    risk_indicators: List[FinancialRiskIndicator] = Field(
        default_factory=list, description="Identified financial risk indicators"
    )

    # Overall Assessment
    overall_risk_level: FinancialRiskLevel = Field(
        ..., description="Overall financial risk level"
    )
    calculation_accuracy_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score for arithmetic accuracy (0-1)"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis (0-1)"
    )

    # Summary and Evidence
    financial_summary: str = Field(..., description="Summary of key financial findings")
    total_buyer_cost: Optional[float] = Field(
        None, description="Total estimated cost to buyer beyond purchase price"
    )

    evidence_references: List[str] = Field(
        default_factory=list,
        description="References to supporting evidence in contract",
    )
    analysis_notes: Optional[str] = Field(
        None, description="Additional analysis notes or observations"
    )

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the financial analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "purchase_price": {
                    "stated_price": 800000,
                    "price_numeric": 800000.0,
                    "price_in_words": "Eight Hundred Thousand Dollars",
                    "arithmetic_accuracy": True,
                    "calculation_errors": [],
                    "market_assessment": "at_market",
                    "market_variance_percentage": 0.0,
                    "market_comparison_notes": "Consistent with recent comparable sales",
                },
                "deposit": {
                    "deposit_amount": 80000.0,
                    "deposit_percentage": 10.0,
                    "payment_timeline": ["Due within 7 days of contract"],
                    "trust_account_details": "Solicitor's trust account",
                    "security_status": "secure",
                    "security_concerns": [],
                    "protection_mechanisms": [
                        "Licensed solicitor trust account",
                        "Professional indemnity insurance",
                    ],
                },
                "payment_schedule": {
                    "progress_payments": [],
                    "additional_fees": [],
                    "interest_provisions": [],
                    "penalty_clauses": [],
                    "cash_flow_assessment": "Standard residential purchase - no unusual cash flow requirements",
                    "total_buyer_obligations": 0.0,
                },
                "gst_analysis": {
                    "gst_status": "not_applicable",
                    "gst_amount": None,
                    "gst_calculation_accuracy": True,
                    "vendor_gst_registration": None,
                    "property_gst_status": "existing_residential",
                    "tax_implications": [],
                    "stamp_duty_considerations": "Standard residential stamp duty applies",
                },
                "risk_indicators": [],
                "overall_risk_level": "low",
                "calculation_accuracy_score": 1.0,
                "confidence_score": 0.95,
                "financial_summary": "Standard residential purchase with market-appropriate pricing and secure deposit arrangements",
                "total_buyer_cost": 0.0,
                "evidence_references": ["Clause 2.1", "Schedule B"],
                "analysis_notes": "Well-structured financial terms with no unusual provisions",
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
