"""
Pydantic schema for Parties & Property Verification Analysis (Step 2.1)

This schema defines the structured output for party validation, legal capacity assessment,
property identification verification, and inclusions/exclusions analysis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LegalCapacityStatus(str, Enum):
    """Legal capacity assessment status"""
    VERIFIED = "verified"
    REQUIRES_VERIFICATION = "requires_verification" 
    CAPACITY_CONCERN = "capacity_concern"
    INSUFFICIENT_INFO = "insufficient_info"


class PropertyDescriptionCompleteness(str, Enum):
    """Property legal description completeness assessment"""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    MISSING_CRITICAL = "missing_critical"
    AMBIGUOUS = "ambiguous"


class RiskLevel(str, Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PartyDetails(BaseModel):
    """Individual party details and verification"""
    name: str = Field(..., description="Full legal name of the party")
    role: str = Field(..., description="Role in transaction (vendor, purchaser, guarantor, etc.)")
    verification_status: LegalCapacityStatus = Field(..., description="Legal capacity verification status")
    concerns: List[str] = Field(default_factory=list, description="Any verification concerns or issues")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="Additional party information")


class PropertyIdentification(BaseModel):
    """Property identification and verification details"""
    street_address: Optional[str] = Field(None, description="Street address as stated in contract")
    lot_number: Optional[str] = Field(None, description="Lot number from legal description")
    plan_number: Optional[str] = Field(None, description="Plan number from legal description") 
    title_reference: Optional[str] = Field(None, description="Volume/folio or title reference")
    property_type: Optional[str] = Field(None, description="Property type classification")
    
    completeness_status: PropertyDescriptionCompleteness = Field(
        ..., description="Assessment of legal description completeness"
    )
    verification_issues: List[str] = Field(
        default_factory=list, description="Issues found in property identification"
    )


class InclusionExclusionItem(BaseModel):
    """Individual inclusion or exclusion item"""
    item: str = Field(..., description="Description of the item")
    category: str = Field(..., description="Category (fixture, fitting, chattel, etc.)")
    included: bool = Field(..., description="Whether item is included or excluded")
    condition_notes: Optional[str] = Field(None, description="Any condition notes about the item")
    ambiguous: bool = Field(default=False, description="Whether the item description is ambiguous")


class InclusionsExclusionsAnalysis(BaseModel):
    """Analysis of included and excluded items"""
    included_items: List[InclusionExclusionItem] = Field(
        default_factory=list, description="Items explicitly included"
    )
    excluded_items: List[InclusionExclusionItem] = Field(
        default_factory=list, description="Items explicitly excluded"
    )
    ambiguous_items: List[InclusionExclusionItem] = Field(
        default_factory=list, description="Items with ambiguous descriptions"
    )
    potential_disputes: List[str] = Field(
        default_factory=list, description="Potential disputes over included/excluded items"
    )
    completeness_assessment: str = Field(
        ..., description="Assessment of inclusions/exclusions completeness"
    )


class RiskIndicator(BaseModel):
    """Individual risk indicator"""
    category: str = Field(..., description="Risk category")
    description: str = Field(..., description="Description of the risk")
    risk_level: RiskLevel = Field(..., description="Assessed risk level")
    impact: str = Field(..., description="Potential impact of the risk")
    recommendation: str = Field(..., description="Recommended action or mitigation")


class PartiesPropertyAnalysisResult(BaseModel):
    """
    Complete result structure for Parties & Property Verification Analysis.
    
    Covers PRD 4.1.2.1 requirements:
    - Party validation and legal capacity assessment  
    - Property identification verification
    - Inclusions/exclusions analysis
    - Risk indicator identification
    """
    
    # Party Analysis
    parties: List[PartyDetails] = Field(..., description="All parties to the transaction")
    party_verification_summary: str = Field(
        ..., description="Summary of party verification findings"
    )
    
    # Property Analysis  
    property_identification: PropertyIdentification = Field(
        ..., description="Property identification and verification details"
    )
    
    # Inclusions/Exclusions
    inclusions_exclusions: InclusionsExclusionsAnalysis = Field(
        ..., description="Analysis of included and excluded items"
    )
    
    # Risk Assessment
    risk_indicators: List[RiskIndicator] = Field(
        default_factory=list, description="Identified risk indicators"
    )
    
    # Overall Assessment
    overall_risk_level: RiskLevel = Field(..., description="Overall risk level for this section")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this analysis (0-1)"
    )
    
    # Evidence and Context
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence in contract"
    )
    analysis_notes: Optional[str] = Field(
        None, description="Additional analysis notes or observations"
    )
    
    # Metadata
    analyzer_version: str = Field(default="1.0", description="Version of the analyzer")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            # Custom encoders if needed
        }
        schema_extra = {
            "example": {
                "parties": [
                    {
                        "name": "John Smith",
                        "role": "vendor", 
                        "verification_status": "verified",
                        "concerns": [],
                        "additional_info": {}
                    },
                    {
                        "name": "Jane Doe", 
                        "role": "purchaser",
                        "verification_status": "verified",
                        "concerns": [],
                        "additional_info": {}
                    }
                ],
                "party_verification_summary": "All parties verified with no legal capacity concerns",
                "property_identification": {
                    "street_address": "123 Test Street, Sydney NSW 2000",
                    "lot_number": "1",
                    "plan_number": "DP123456",
                    "title_reference": "Vol 1234 Fol 567",
                    "property_type": "residential_house",
                    "completeness_status": "complete",
                    "verification_issues": []
                },
                "inclusions_exclusions": {
                    "included_items": [
                        {
                            "item": "Built-in dishwasher",
                            "category": "fixture",
                            "included": True,
                            "condition_notes": None,
                            "ambiguous": False
                        }
                    ],
                    "excluded_items": [
                        {
                            "item": "Outdoor furniture",
                            "category": "chattel", 
                            "included": False,
                            "condition_notes": None,
                            "ambiguous": False
                        }
                    ],
                    "ambiguous_items": [],
                    "potential_disputes": [],
                    "completeness_assessment": "Comprehensive list provided"
                },
                "risk_indicators": [],
                "overall_risk_level": "low",
                "confidence_score": 0.95,
                "evidence_references": ["Section 1.1", "Schedule A"],
                "analysis_notes": "Standard residential purchase with clear party identification",
                "analyzer_version": "1.0",
                "analysis_timestamp": "2024-01-15T10:30:00Z"
            }
        }