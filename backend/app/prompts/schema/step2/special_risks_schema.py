"""
Pydantic schema for Special Risks Identification (Step 2.11)

This schema defines the structured output for special risk identification,
unusual terms assessment, and buyer protection evaluation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class RiskCategory(str, Enum):
    """Category of special risk"""

    LEGAL = "legal"
    FINANCIAL = "financial"
    PHYSICAL = "physical"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"
    MARKET = "market"
    OPERATIONAL = "operational"
    REPUTATIONAL = "reputational"


class RiskLevel(str, Enum):
    """Risk level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UnusualTermType(str, Enum):
    """Type of unusual contract term"""

    PRICING = "pricing"
    TIMING = "timing"
    CONDITIONS = "conditions"
    WARRANTIES = "warranties"
    OBLIGATIONS = "obligations"
    RIGHTS = "rights"
    PROCEDURES = "procedures"
    PENALTIES = "penalties"


class MitigationStrategy(str, Enum):
    """Type of risk mitigation strategy"""

    NEGOTIATION = "negotiation"
    INVESTIGATION = "investigation"
    INSURANCE = "insurance"
    PROFESSIONAL_ADVICE = "professional_advice"
    ALTERNATIVE_ARRANGEMENT = "alternative_arrangement"
    ACCEPTANCE = "acceptance"
    WITHDRAWAL = "withdrawal"


class SpecialRisk(BaseModel):
    """Individual special risk analysis"""

    risk_description: str = Field(..., description="Description of the special risk")
    risk_category: RiskCategory = Field(..., description="Category classification")
    risk_level: RiskLevel = Field(..., description="Risk level assessment")

    # Risk characteristics
    probability: str = Field(..., description="Probability of risk occurrence")
    impact_assessment: str = Field(..., description="Impact if risk materializes")
    timing_relevance: str = Field(..., description="When risk is most relevant")

    # Context and causes
    risk_source: str = Field(..., description="Source or cause of the risk")
    contract_provisions: List[str] = Field(
        default_factory=list,
        description="Contract provisions creating or addressing risk",
    )
    external_factors: List[str] = Field(
        default_factory=list, description="External factors contributing to risk"
    )

    # Impact analysis
    financial_impact: Optional[str] = Field(
        None, description="Potential financial impact"
    )
    legal_implications: List[str] = Field(
        default_factory=list, description="Legal implications of risk"
    )
    practical_consequences: List[str] = Field(
        default_factory=list, description="Practical consequences for buyer"
    )

    # Mitigation options
    mitigation_strategies: List[str] = Field(
        default_factory=list, description="Available mitigation strategies"
    )
    preferred_mitigation: Optional[MitigationStrategy] = Field(
        None, description="Recommended mitigation approach"
    )
    mitigation_cost: Optional[str] = Field(
        None, description="Cost of mitigation measures"
    )

    # Monitoring and management
    monitoring_requirements: List[str] = Field(
        default_factory=list, description="Requirements for monitoring risk"
    )
    management_strategies: List[str] = Field(
        default_factory=list, description="Ongoing risk management strategies"
    )

    # Recommendations
    immediate_actions: List[str] = Field(
        default_factory=list, description="Immediate actions recommended"
    )
    professional_advice_needed: List[str] = Field(
        default_factory=list, description="Professional advice needed"
    )


class UnusualTerm(BaseModel):
    """Unusual contract term analysis"""

    term_description: str = Field(..., description="Description of the unusual term")
    term_type: UnusualTermType = Field(..., description="Type classification")

    # Unusualness assessment
    deviation_from_standard: str = Field(
        ..., description="How it deviates from standard practice"
    )
    market_comparison: str = Field(..., description="Comparison to market norms")
    precedent_analysis: Optional[str] = Field(
        None, description="Analysis of legal precedents"
    )

    # Party impact
    favors_party: str = Field(..., description="Which party the term favors")
    buyer_disadvantage: str = Field(..., description="Potential buyer disadvantage")
    vendor_advantage: str = Field(..., description="Vendor advantage created")

    # Risk assessment
    enforceability: str = Field(..., description="Enforceability assessment")
    challenge_prospects: str = Field(
        ..., description="Prospects for successful challenge"
    )
    unfair_terms_analysis: str = Field(
        ..., description="Analysis under unfair contract terms legislation"
    )

    # Strategic considerations
    negotiation_potential: str = Field(..., description="Potential for negotiation")
    alternative_approaches: List[str] = Field(
        default_factory=list, description="Alternative approaches or terms"
    )

    # Recommendations
    response_strategy: str = Field(..., description="Recommended response strategy")
    legal_advice_needed: bool = Field(
        default=False, description="Whether specialized legal advice is needed"
    )


class MarketRisk(BaseModel):
    """Market and economic risk analysis"""

    risk_type: str = Field(..., description="Type of market risk")

    # Market conditions
    current_market_assessment: str = Field(
        ..., description="Current market condition assessment"
    )
    market_trend_analysis: str = Field(..., description="Market trend analysis")

    # Contract exposure
    market_exposure: str = Field(..., description="Contract's exposure to market risks")
    price_protection: str = Field(..., description="Price protection mechanisms")
    timing_risks: List[str] = Field(
        default_factory=list, description="Market timing risks"
    )

    # Risk factors
    volatility_factors: List[str] = Field(
        default_factory=list, description="Market volatility factors"
    )
    external_influences: List[str] = Field(
        default_factory=list, description="External market influences"
    )

    # Mitigation
    risk_mitigation_options: List[str] = Field(
        default_factory=list, description="Available risk mitigation options"
    )


class RegulatoryRisk(BaseModel):
    """Regulatory and compliance risk analysis"""

    regulatory_area: str = Field(..., description="Area of regulatory risk")

    # Regulatory environment
    current_regulations: List[str] = Field(
        default_factory=list, description="Current applicable regulations"
    )
    pending_changes: List[str] = Field(
        default_factory=list, description="Pending regulatory changes"
    )

    # Compliance assessment
    compliance_status: str = Field(..., description="Current compliance status")
    compliance_gaps: List[str] = Field(
        default_factory=list, description="Identified compliance gaps"
    )

    # Future implications
    regulatory_change_risk: RiskLevel = Field(
        ..., description="Risk of adverse regulatory changes"
    )
    compliance_cost_implications: List[str] = Field(
        default_factory=list, description="Cost implications of compliance"
    )

    # Management strategies
    compliance_strategies: List[str] = Field(
        default_factory=list, description="Compliance management strategies"
    )
    monitoring_requirements: List[str] = Field(
        default_factory=list, description="Regulatory monitoring requirements"
    )


class SpecialRisksAnalysisResult(BaseModel):
    """
    Complete result structure for Special Risks Identification.

    Covers PRD 4.1.2.11 requirements:
    - Comprehensive special risk identification
    - Unusual contract terms assessment
    - Market and economic risk evaluation
    - Regulatory and compliance risk analysis
    - Risk mitigation and management strategies
    """

    # Overall risk summary
    total_special_risks: int = Field(
        ..., description="Total number of special risks identified"
    )
    critical_risks: int = Field(..., description="Number of critical risks")
    high_risks: int = Field(..., description="Number of high risks")
    overall_risk_assessment: RiskLevel = Field(
        ..., description="Overall special risk assessment"
    )

    # Detailed risk analysis
    special_risks: List[SpecialRisk] = Field(
        ..., description="Detailed special risk analysis"
    )
    risk_interactions: List[str] = Field(
        default_factory=list, description="Interactions between different risks"
    )

    # Unusual terms analysis
    unusual_terms: List[UnusualTerm] = Field(
        default_factory=list, description="Unusual contract terms analysis"
    )
    terms_requiring_negotiation: List[str] = Field(
        default_factory=list, description="Terms requiring negotiation"
    )

    # Specialized risk analyses
    market_risks: List[MarketRisk] = Field(
        default_factory=list, description="Market and economic risk analysis"
    )
    regulatory_risks: List[RegulatoryRisk] = Field(
        default_factory=list, description="Regulatory and compliance risk analysis"
    )

    # Risk prioritization
    immediate_attention_risks: List[str] = Field(
        default_factory=list, description="Risks requiring immediate attention"
    )
    long_term_monitoring_risks: List[str] = Field(
        default_factory=list, description="Risks requiring long-term monitoring"
    )

    # Mitigation strategies
    priority_mitigation_strategies: List[str] = Field(
        default_factory=list, description="Priority mitigation strategies"
    )
    professional_advice_requirements: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Professional advice requirements by specialty",
    )

    # Contract negotiation
    negotiation_priorities: List[str] = Field(
        default_factory=list, description="Priority items for contract negotiation"
    )
    deal_breaker_risks: List[str] = Field(
        default_factory=list, description="Risks that could be deal breakers"
    )
    acceptable_risk_threshold: str = Field(
        ..., description="Assessment of acceptable risk levels"
    )

    # Risk management framework
    risk_monitoring_plan: List[str] = Field(
        default_factory=list, description="Plan for ongoing risk monitoring"
    )
    contingency_planning: List[str] = Field(
        default_factory=list, description="Contingency planning requirements"
    )

    # Industry and market context
    industry_specific_risks: List[str] = Field(
        default_factory=list, description="Industry-specific risks identified"
    )
    market_positioning_risks: List[str] = Field(
        default_factory=list, description="Market positioning risks"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    risk_mitigation_roadmap: List[str] = Field(
        default_factory=list, description="Risk mitigation roadmap"
    )
    decision_framework: List[str] = Field(
        default_factory=list, description="Decision framework for risk acceptance"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness of risk identification"
    )
    risk_assessment_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="Accuracy of risk assessments"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    market_data_sources: List[str] = Field(
        default_factory=list, description="Market data sources used"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the special risks analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_special_risks": 5,
                "critical_risks": 1,
                "high_risks": 2,
                "overall_risk_assessment": "high",
                "special_risks": [
                    {
                        "risk_description": "Property located in flood-prone area with inadequate insurance",
                        "risk_category": "environmental",
                        "risk_level": "high",
                        "probability": "Medium likelihood given recent flooding events",
                        "impact_assessment": "Significant property damage and insurance gaps",
                        "timing_relevance": "Immediate and ongoing",
                        "risk_source": "Location in designated flood zone",
                        "financial_impact": "Potential $50,000-200,000 in damages",
                        "mitigation_strategies": [
                            "Comprehensive flood insurance",
                            "Flood mitigation works",
                        ],
                        "preferred_mitigation": "insurance",
                    }
                ],
                "unusual_terms": [
                    {
                        "term_description": "Vendor retains mineral rights below 10 meters",
                        "term_type": "rights",
                        "deviation_from_standard": "Unusual retention of subsurface rights",
                        "favors_party": "vendor",
                        "buyer_disadvantage": "Potential future mining activity",
                        "enforceability": "Likely enforceable",
                        "negotiation_potential": "Limited",
                        "response_strategy": "Accept with conditions or withdraw",
                    }
                ],
                "overall_risk_assessment": "high",
                "confidence_score": 0.87,
                "completeness_score": 0.92,
                "risk_assessment_accuracy": 0.89,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
