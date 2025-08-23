"""
Pydantic schema for Warranties and Representations Analysis (Step 2.5)

This schema defines the structured output for warranties, representations,
vendor disclosures, and buyer acknowledgments analysis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import date


class WarrantyType(str, Enum):
    """Type of warranty or representation"""

    EXPRESS = "express"
    IMPLIED = "implied"
    STATUTORY = "statutory"
    LIMITATION = "limitation"
    EXCLUSION = "exclusion"


class WarrantyScope(str, Enum):
    """Scope of warranty coverage"""

    FULL = "full"
    LIMITED = "limited"
    EXCLUDED = "excluded"
    CONDITIONAL = "conditional"


class DisclosureCategory(str, Enum):
    """Category of vendor disclosure"""

    DEFECTS = "defects"
    ENCUMBRANCES = "encumbrances"
    DISPUTES = "disputes"
    ENVIRONMENTAL = "environmental"
    PLANNING = "planning"
    STRUCTURAL = "structural"
    SERVICES = "services"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WarrantyDetail(BaseModel):
    """Individual warranty or representation analysis"""

    description: str = Field(
        ..., description="Full description of the warranty/representation"
    )
    warranty_type: WarrantyType = Field(..., description="Type classification")
    scope: WarrantyScope = Field(..., description="Scope of warranty coverage")

    # Party information
    given_by: str = Field(..., description="Party providing the warranty")
    beneficiary: str = Field(..., description="Party benefiting from the warranty")

    # Coverage details
    coverage_details: List[str] = Field(
        default_factory=list, description="What is covered"
    )
    exclusions: List[str] = Field(default_factory=list, description="What is excluded")
    limitations: List[str] = Field(
        default_factory=list, description="Limitations on warranty"
    )

    # Time constraints
    duration: Optional[str] = Field(None, description="Duration of warranty")
    expiry_date: Optional[str] = Field(None, description="Expiry date if specified")
    survival_period: Optional[str] = Field(
        None, description="Survival period after settlement"
    )

    # Risk assessment
    enforceability: str = Field(..., description="Assessment of enforceability")
    risk_level: RiskLevel = Field(..., description="Risk level for buyer")
    potential_issues: List[str] = Field(
        default_factory=list, description="Potential issues identified"
    )

    # Legal context
    statutory_requirements: List[str] = Field(
        default_factory=list, description="Related statutory requirements"
    )
    case_law_references: List[str] = Field(
        default_factory=list, description="Relevant case law if applicable"
    )


class VendorDisclosure(BaseModel):
    """Vendor disclosure analysis"""

    disclosure_item: str = Field(..., description="Item being disclosed")
    category: DisclosureCategory = Field(..., description="Category of disclosure")

    # Disclosure details
    full_description: str = Field(..., description="Full description of the disclosure")
    severity: str = Field(..., description="Severity assessment")
    impact_on_property: str = Field(..., description="Impact on property value/use")

    # Remediation
    remediation_required: bool = Field(
        default=False, description="Whether remediation is required"
    )
    remediation_details: Optional[str] = Field(
        None, description="Details of required remediation"
    )
    estimated_cost: Optional[float] = Field(
        None, description="Estimated remediation cost"
    )

    # Risk assessment
    buyer_acknowledgment_adequate: bool = Field(
        ..., description="Whether buyer acknowledgment is adequate"
    )
    further_investigation_needed: bool = Field(
        ..., description="Whether further investigation is needed"
    )
    risk_level: RiskLevel = Field(..., description="Risk level for buyer")

    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for buyer"
    )


class BuyerAcknowledgment(BaseModel):
    """Buyer acknowledgment analysis"""

    acknowledgment_item: str = Field(..., description="Item being acknowledged")

    # Acknowledgment details
    full_text: str = Field(..., description="Full text of acknowledgment")
    scope: str = Field(..., description="Scope of acknowledgment")

    # Risk assessment
    waives_rights: bool = Field(default=False, description="Whether rights are waived")
    rights_waived: List[str] = Field(
        default_factory=list, description="Specific rights waived"
    )

    # Fairness assessment
    fairness_assessment: str = Field(..., description="Assessment of fairness to buyer")
    unusual_aspects: List[str] = Field(
        default_factory=list, description="Unusual or concerning aspects"
    )

    # Legal implications
    legal_implications: List[str] = Field(
        default_factory=list, description="Legal implications for buyer"
    )
    enforceability: str = Field(..., description="Enforceability assessment")

    # Recommendations
    negotiation_points: List[str] = Field(
        default_factory=list, description="Potential negotiation points"
    )
    risk_mitigation: List[str] = Field(
        default_factory=list, description="Risk mitigation strategies"
    )


class StatutoryWarranty(BaseModel):
    """Statutory warranty analysis"""

    warranty_name: str = Field(..., description="Name of statutory warranty")
    legislation: str = Field(..., description="Relevant legislation")

    # Application
    applies_to_transaction: bool = Field(
        ..., description="Whether it applies to this transaction"
    )
    can_be_excluded: bool = Field(..., description="Whether it can be excluded")
    exclusion_attempted: bool = Field(
        default=False, description="Whether exclusion is attempted"
    )

    # Validity assessment
    exclusion_valid: Optional[bool] = Field(
        None, description="Whether exclusion is valid if attempted"
    )
    exclusion_reasons: List[str] = Field(
        default_factory=list, description="Reasons for exclusion validity/invalidity"
    )

    # Coverage
    coverage: str = Field(..., description="What the warranty covers")
    duration: str = Field(..., description="Duration of warranty")

    # Buyer protection
    buyer_protection_level: str = Field(..., description="Level of buyer protection")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations regarding this warranty"
    )


class WarrantiesAnalysisResult(BaseModel):
    """
    Complete result structure for Warranties and Representations Analysis.

    Covers PRD 4.1.2.5 requirements:
    - Express and implied warranties identification
    - Vendor representations and disclosures
    - Buyer acknowledgments and waivers
    - Statutory warranty implications
    - Risk assessment of warranty limitations
    """

    # Overall warranty summary
    total_warranties: int = Field(
        ..., description="Total number of warranties identified"
    )
    express_warranties_count: int = Field(
        ..., description="Number of express warranties"
    )
    implied_warranties_count: int = Field(
        ..., description="Number of implied warranties"
    )
    exclusions_count: int = Field(..., description="Number of warranty exclusions")

    # Detailed warranty analysis
    warranties: List[WarrantyDetail] = Field(
        ..., description="Detailed warranty analysis"
    )

    # Vendor disclosures
    vendor_disclosures: List[VendorDisclosure] = Field(
        default_factory=list, description="Vendor disclosure analysis"
    )
    total_disclosures: int = Field(
        ..., description="Total number of vendor disclosures"
    )
    high_risk_disclosures: List[str] = Field(
        default_factory=list, description="High-risk disclosures requiring attention"
    )

    # Buyer acknowledgments
    buyer_acknowledgments: List[BuyerAcknowledgment] = Field(
        default_factory=list, description="Buyer acknowledgment analysis"
    )
    concerning_acknowledgments: List[str] = Field(
        default_factory=list, description="Concerning acknowledgments for buyer"
    )

    # Statutory warranties
    statutory_warranties: List[StatutoryWarranty] = Field(
        default_factory=list, description="Statutory warranty analysis"
    )
    statutory_protection_assessment: str = Field(
        ..., description="Overall statutory protection assessment"
    )

    # Risk assessment
    overall_warranty_risk: RiskLevel = Field(
        ..., description="Overall warranty risk level"
    )
    warranty_gaps: List[str] = Field(
        default_factory=list, description="Identified warranty gaps"
    )
    exclusion_concerns: List[str] = Field(
        default_factory=list, description="Concerns about warranty exclusions"
    )

    # Balance assessment
    vendor_buyer_balance: str = Field(
        ..., description="Assessment of vendor/buyer balance"
    )
    buyer_protection_level: str = Field(
        ..., description="Overall buyer protection level"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations"
    )
    negotiation_points: List[str] = Field(
        default_factory=list, description="Key negotiation points"
    )
    further_investigation: List[str] = Field(
        default_factory=list, description="Items requiring further investigation"
    )

    # Quality metrics
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness of warranty identification"
    )

    # Evidence and context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")

    # Metadata
    analyzer_version: str = Field(
        default="1.0", description="Version of the warranties analyzer"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_warranties": 8,
                "express_warranties_count": 5,
                "implied_warranties_count": 2,
                "exclusions_count": 1,
                "warranties": [
                    {
                        "description": "Vendor warrants good title free from encumbrances",
                        "warranty_type": "express",
                        "scope": "full",
                        "given_by": "vendor",
                        "beneficiary": "purchaser",
                        "coverage_details": [
                            "Title validity",
                            "Freedom from encumbrances",
                        ],
                        "enforceability": "Fully enforceable",
                        "risk_level": "low",
                    }
                ],
                "vendor_disclosures": [
                    {
                        "disclosure_item": "Boundary fence dispute with neighbor",
                        "category": "disputes",
                        "severity": "Medium",
                        "buyer_acknowledgment_adequate": True,
                        "risk_level": "medium",
                    }
                ],
                "overall_warranty_risk": "medium",
                "vendor_buyer_balance": "Reasonably balanced with slight vendor favor",
                "buyer_protection_level": "Adequate with some gaps",
                "confidence_score": 0.91,
                "completeness_score": 0.94,
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )
