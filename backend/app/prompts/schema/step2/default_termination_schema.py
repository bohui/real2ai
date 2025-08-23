"""
Pydantic schema for Default and Termination Analysis (Step 2.6)

This schema defines the structured output for default events, termination rights,
remedy provisions, and enforcement mechanisms analysis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import date


class DefaultType(str, Enum):
    """Type of default event"""

    MONETARY = "monetary"
    NON_MONETARY = "non_monetary"
    CONDITION_FAILURE = "condition_failure"
    BREACH_WARRANTY = "breach_warranty"
    BREACH_COVENANT = "breach_covenant"
    REPUDIATION = "repudiation"


class PartyAtFault(str, Enum):
    """Party potentially at fault"""

    VENDOR = "vendor"
    PURCHASER = "purchaser"
    BOTH = "both"
    THIRD_PARTY = "third_party"


class RemedyType(str, Enum):
    """Type of legal remedy"""

    TERMINATION = "termination"
    DAMAGES = "damages"
    SPECIFIC_PERFORMANCE = "specific_performance"
    FORFEITURE = "forfeiture"
    RETENTION = "retention"
    COMPENSATION = "compensation"
    CURE_PERIOD = "cure_period"


class RiskLevel(str, Enum):
    """Risk level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DefaultEvent(BaseModel):
    """Individual default event analysis"""

    event_description: str = Field(..., description="Description of the default event")
    default_type: DefaultType = Field(..., description="Classification of default type")
    party_at_fault: PartyAtFault = Field(..., description="Party potentially at fault")

    # Triggering conditions
    triggering_conditions: List[str] = Field(
        default_factory=list, description="Conditions that trigger this default"
    )
    notice_requirements: List[str] = Field(
        default_factory=list, description="Notice requirements before declaring default"
    )
    cure_period: Optional[str] = Field(
        None, description="Period allowed to cure default"
    )

    # Consequences
    immediate_consequences: List[str] = Field(
        default_factory=list, description="Immediate consequences of default"
    )
    available_remedies: List[str] = Field(
        default_factory=list, description="Available remedies for non-defaulting party"
    )

    # Risk assessment
    likelihood: str = Field(..., description="Likelihood of this default occurring")
    severity: RiskLevel = Field(..., description="Severity if default occurs")
    prevention_measures: List[str] = Field(
        default_factory=list, description="Measures to prevent default"
    )

    # Legal analysis
    enforceability: str = Field(..., description="Enforceability of default provisions")
    ambiguities: List[str] = Field(
        default_factory=list, description="Ambiguities in default definition"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations regarding this default"
    )


class TerminationRight(BaseModel):
    """Termination right analysis"""

    termination_trigger: str = Field(
        ..., description="Event or condition triggering termination right"
    )
    party_exercising: str = Field(..., description="Party who can exercise termination")

    # Exercise conditions
    notice_period: Optional[str] = Field(None, description="Required notice period")
    notice_method: Optional[str] = Field(None, description="Required method of notice")
    conditions_precedent: List[str] = Field(
        default_factory=list, description="Conditions precedent to termination"
    )

    # Effects of termination
    deposit_treatment: str = Field(
        ..., description="Treatment of deposit upon termination"
    )
    cost_allocation: str = Field(..., description="Allocation of costs and expenses")
    other_consequences: List[str] = Field(
        default_factory=list, description="Other consequences of termination"
    )

    # Fairness assessment
    fairness_to_buyer: str = Field(..., description="Fairness assessment for buyer")
    fairness_to_vendor: str = Field(..., description="Fairness assessment for vendor")

    # Risk factors
    abuse_potential: str = Field(
        ..., description="Potential for abuse of termination right"
    )
    mitigation_available: bool = Field(
        default=False, description="Whether mitigation is available"
    )
    risk_level: RiskLevel = Field(
        ..., description="Risk level for this termination right"
    )


class RemedyProvision(BaseModel):
    """Remedy provision analysis"""

    remedy_description: str = Field(..., description="Description of the remedy")
    remedy_type: RemedyType = Field(..., description="Type of remedy")

    # Availability
    triggering_breach: str = Field(..., description="Breach that triggers this remedy")
    available_to: str = Field(..., description="Party who can seek this remedy")

    # Procedural requirements
    procedural_steps: List[str] = Field(
        default_factory=list, description="Required procedural steps"
    )
    time_limitations: Optional[str] = Field(
        None, description="Time limitations on remedy"
    )
    notice_requirements: List[str] = Field(
        default_factory=list, description="Notice requirements"
    )

    # Scope and limitations
    monetary_cap: Optional[float] = Field(
        None, description="Monetary cap on remedy if applicable"
    )
    scope_limitations: List[str] = Field(
        default_factory=list, description="Limitations on remedy scope"
    )
    exclusions: List[str] = Field(
        default_factory=list, description="Exclusions from remedy"
    )

    # Assessment
    adequacy: str = Field(..., description="Adequacy of remedy for breach type")
    enforceability: str = Field(..., description="Enforceability assessment")
    practical_effectiveness: str = Field(
        ..., description="Practical effectiveness of remedy"
    )

    # Risk factors
    enforcement_risks: List[str] = Field(
        default_factory=list, description="Risks in enforcing remedy"
    )
    cost_considerations: List[str] = Field(
        default_factory=list, description="Cost considerations for enforcement"
    )


class DepositForfeiture(BaseModel):
    """Deposit forfeiture analysis"""

    forfeiture_triggers: List[str] = Field(
        default_factory=list, description="Events triggering deposit forfeiture"
    )
    forfeiture_amount: Optional[str] = Field(
        None, description="Amount subject to forfeiture"
    )

    # Procedural requirements
    notice_requirements: List[str] = Field(
        default_factory=list, description="Notice requirements for forfeiture"
    )
    cure_opportunities: List[str] = Field(
        default_factory=list, description="Opportunities to cure before forfeiture"
    )

    # Fairness assessment
    proportionality: str = Field(
        ..., description="Proportionality of forfeiture to breach"
    )
    enforceability: str = Field(
        ..., description="Enforceability under penalty provisions"
    )
    buyer_protection: str = Field(
        ..., description="Level of buyer protection against forfeiture"
    )

    # Risk assessment
    forfeiture_risk: RiskLevel = Field(..., description="Risk of deposit forfeiture")
    mitigation_strategies: List[str] = Field(
        default_factory=list, description="Strategies to mitigate forfeiture risk"
    )


class TimeOfEssence(BaseModel):
    """Time is of the essence analysis"""

    applies_to_obligations: List[str] = Field(
        default_factory=list, description="Obligations where time is of essence"
    )
    specific_deadlines: List[str] = Field(
        default_factory=list, description="Specific deadlines with time of essence"
    )

    # Grace periods
    grace_periods_available: bool = Field(
        default=False, description="Whether grace periods are available"
    )
    grace_period_details: List[str] = Field(
        default_factory=list, description="Details of any grace periods"
    )

    # Risk assessment
    strict_enforcement_risk: RiskLevel = Field(
        ..., description="Risk of strict time enforcement"
    )
    delay_consequences: List[str] = Field(
        default_factory=list, description="Consequences of delays"
    )

    # Recommendations
    timing_recommendations: List[str] = Field(
        default_factory=list, description="Timing recommendations for buyer"
    )


class DefaultTerminationAnalysisResult(BaseModel):
    """
    Complete result structure for Default and Termination Analysis.

    Covers PRD 4.1.2.6 requirements:
    - Default event identification and consequences
    - Termination rights and procedures
    - Remedy provisions and enforceability
    - Deposit forfeiture risks
    - Time of essence implications
    """

    # Overall summary
    total_default_events: int = Field(
        ..., description="Total number of default events identified"
    )
    vendor_default_events: int = Field(
        ..., description="Default events attributable to vendor"
    )
    purchaser_default_events: int = Field(
        ..., description="Default events attributable to purchaser"
    )

    # Detailed analyses
    default_events: List[DefaultEvent] = Field(
        ..., description="Detailed default event analysis"
    )
    termination_rights: List[TerminationRight] = Field(
        default_factory=list, description="Termination rights analysis"
    )
    remedy_provisions: List[RemedyProvision] = Field(
        default_factory=list, description="Available remedies analysis"
    )

    # Specific risk areas
    deposit_forfeiture: Optional[DepositForfeiture] = Field(
        None, description="Deposit forfeiture analysis"
    )
    time_of_essence: Optional[TimeOfEssence] = Field(
        None, description="Time of essence analysis"
    )

    # Risk assessment
    overall_default_risk: RiskLevel = Field(
        ..., description="Overall default and termination risk"
    )
    highest_risk_defaults: List[str] = Field(
        default_factory=list, description="Highest risk default scenarios"
    )
    buyer_vulnerability: str = Field(
        ..., description="Assessment of buyer vulnerability"
    )
    vendor_advantages: List[str] = Field(
        default_factory=list, description="Vendor advantages in default scenarios"
    )

    # Balance assessment
    remedy_balance: str = Field(..., description="Balance of remedies between parties")
    procedural_fairness: str = Field(
        ..., description="Fairness of default and termination procedures"
    )
    consumer_protection_compliance: str = Field(
        ..., description="Compliance with consumer protection laws"
    )

    # Practical considerations
    enforcement_practicality: str = Field(
        ..., description="Practical considerations for remedy enforcement"
    )
    cost_implications: List[str] = Field(
        default_factory=list, description="Cost implications of defaults and remedies"
    )
    timing_criticality: str = Field(..., description="Criticality of timing compliance")

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    risk_mitigation: List[str] = Field(
        default_factory=list, description="Risk mitigation strategies"
    )
    negotiation_points: List[str] = Field(
        default_factory=list, description="Key negotiation points"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness of default/termination identification",
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the default/termination analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_default_events": 6,
                "vendor_default_events": 2,
                "purchaser_default_events": 4,
                "default_events": [
                    {
                        "event_description": "Failure to pay deposit by due date",
                        "default_type": "monetary",
                        "party_at_fault": "purchaser",
                        "triggering_conditions": [
                            "Non-payment of deposit within 3 business days"
                        ],
                        "notice_requirements": [
                            "Written notice to purchaser's solicitor"
                        ],
                        "cure_period": "2 business days after notice",
                        "likelihood": "Low with proper planning",
                        "severity": "high",
                    }
                ],
                "termination_rights": [
                    {
                        "termination_trigger": "Purchaser default in deposit payment",
                        "party_exercising": "vendor",
                        "notice_period": "2 business days",
                        "deposit_treatment": "Forfeited to vendor",
                        "fairness_to_buyer": "Standard market terms",
                        "risk_level": "medium",
                    }
                ],
                "overall_default_risk": "medium",
                "buyer_vulnerability": "Moderate - standard default provisions",
                "remedy_balance": "Slightly vendor-favored but within market norms",
                "confidence_score": 0.89,
                "completeness_score": 0.92,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
