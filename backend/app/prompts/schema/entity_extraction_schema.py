"""
Entity Extraction Schemas for Contract Analysis
Pydantic models for structured entity extraction from legal documents
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime, date
from decimal import Decimal


class AustralianState(str, Enum):
    """Australian states and territories"""
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    WA = "WA"
    SA = "SA"
    TAS = "TAS"
    ACT = "ACT"
    NT = "NT"


class ContractType(str, Enum):
    """Contract types for analysis"""
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    RENTAL_AGREEMENT = "rental_agreement"
    COMMERCIAL_LEASE = "commercial_lease"
    OPTION_TO_PURCHASE = "option_to_purchase"
    UNKNOWN = "unknown"


class PartyRole(str, Enum):
    """Roles of parties in contract"""
    VENDOR = "vendor"
    PURCHASER = "purchaser"
    LANDLORD = "landlord"
    TENANT = "tenant"
    AGENT = "agent"
    SOLICITOR = "solicitor"
    CONVEYANCER = "conveyancer"
    OTHER = "other"


class PropertyType(str, Enum):
    """Property types"""
    RESIDENTIAL_HOUSE = "residential_house"
    UNIT_APARTMENT = "unit_apartment"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    OTHER = "other"


class DateType(str, Enum):
    """Types of dates in contracts"""
    SETTLEMENT_DATE = "settlement_date"
    COMPLETION_DATE = "completion_date"
    EXCHANGE_DATE = "exchange_date"
    LEASE_START = "lease_start"
    LEASE_END = "lease_end"
    COOLING_OFF_EXPIRY = "cooling_off_expiry"
    FINANCE_APPROVAL_DUE = "finance_approval_due"
    INSPECTION_DUE = "inspection_due"
    CONTRACT_DATE = "contract_date"
    OTHER = "other"


class FinancialType(str, Enum):
    """Types of financial amounts"""
    PURCHASE_PRICE = "purchase_price"
    DEPOSIT = "deposit"
    RENT_AMOUNT = "rent_amount"
    BOND = "bond"
    STAMP_DUTY = "stamp_duty"
    LEGAL_FEES = "legal_fees"
    AGENT_COMMISSION = "agent_commission"
    BODY_CORPORATE_FEES = "body_corporate_fees"
    COUNCIL_RATES = "council_rates"
    OTHER_FEES = "other_fees"


# Base entity models
class EntityBase(BaseModel):
    """Base class for all entities"""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for extraction")
    page_number: int = Field(..., ge=1, description="Page number where entity appears")
    context: Optional[str] = Field(None, description="Surrounding text context")
    extraction_method: str = Field(default="llm", description="Method used for extraction")


class PropertyAddress(EntityBase):
    """Property address information"""
    street_address: str = Field(..., description="Street address")
    suburb: Optional[str] = Field(None, description="Suburb/locality")
    state: Optional[AustralianState] = Field(None, description="Australian state")
    postcode: Optional[str] = Field(None, description="Postal code")
    full_address: str = Field(..., description="Complete address as found in document")
    
    # Property identifiers
    lot_number: Optional[str] = Field(None, description="Lot number")
    plan_number: Optional[str] = Field(None, description="Plan number")
    title_reference: Optional[str] = Field(None, description="Title reference")
    property_type: Optional[PropertyType] = Field(None, description="Type of property")


class ContractParty(EntityBase):
    """Party to the contract"""
    name: str = Field(..., description="Full name of party")
    role: PartyRole = Field(..., description="Role in the contract")
    
    # Contact information
    address: Optional[str] = Field(None, description="Address of party")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    
    # Legal representation
    solicitor_name: Optional[str] = Field(None, description="Name of solicitor/conveyancer")
    solicitor_firm: Optional[str] = Field(None, description="Law firm name")
    solicitor_contact: Optional[str] = Field(None, description="Solicitor contact details")


class ContractDate(EntityBase):
    """Important dates in contract"""
    date_value: date = Field(..., description="The actual date")
    date_type: DateType = Field(..., description="Type/purpose of this date")
    date_text: str = Field(..., description="Date as it appears in document")
    
    # Additional context
    is_business_days: Optional[bool] = Field(None, description="Whether date calculation uses business days")
    timezone: Optional[str] = Field(None, description="Timezone if specified")
    conditions: Optional[str] = Field(None, description="Conditions attached to this date")


class FinancialAmount(EntityBase):
    """Financial amounts and terms"""
    amount: Decimal = Field(..., description="Monetary amount")
    currency: str = Field(default="AUD", description="Currency code")
    amount_type: FinancialType = Field(..., description="Type of financial amount")
    amount_text: str = Field(..., description="Amount as written in document")
    
    # Payment terms
    payment_method: Optional[str] = Field(None, description="How payment is to be made")
    payment_due_date: Optional[date] = Field(None, description="When payment is due")
    payment_conditions: Optional[str] = Field(None, description="Conditions for payment")
    
    # Calculations
    is_percentage: bool = Field(default=False, description="Whether amount is a percentage")
    percentage_of: Optional[str] = Field(None, description="What the percentage is calculated on")


class LegalReference(EntityBase):
    """Legal references and compliance information"""
    reference_type: str = Field(..., description="Type of legal reference")
    reference_text: str = Field(..., description="The legal reference as written")
    
    # Australian-specific
    act_name: Optional[str] = Field(None, description="Name of legislation")
    section_number: Optional[str] = Field(None, description="Section or clause number")
    state_specific: Optional[AustralianState] = Field(None, description="State-specific legislation")
    
    # Compliance
    compliance_requirement: Optional[str] = Field(None, description="What compliance is required")
    mandatory: bool = Field(default=False, description="Whether compliance is mandatory")


class ContractCondition(EntityBase):
    """Contract conditions and clauses"""
    condition_type: str = Field(..., description="Type of condition")
    condition_text: str = Field(..., description="Full text of condition")
    condition_summary: str = Field(..., description="Brief summary of condition")
    
    # Classification
    is_special_condition: bool = Field(default=False, description="Whether this is a special condition")
    is_standard_condition: bool = Field(default=False, description="Whether this is a standard condition")
    
    # Requirements
    requires_action: bool = Field(default=False, description="Whether condition requires action from parties")
    action_required: Optional[str] = Field(None, description="What action is required")
    action_by_whom: Optional[PartyRole] = Field(None, description="Who must take action")
    action_deadline: Optional[date] = Field(None, description="Deadline for action")


class PropertyDetails(EntityBase):
    """Detailed property information"""
    property_description: str = Field(..., description="Description of property")
    
    # Physical characteristics
    land_size: Optional[str] = Field(None, description="Size of land")
    building_area: Optional[str] = Field(None, description="Building area")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    parking: Optional[str] = Field(None, description="Parking arrangements")
    
    # Legal characteristics
    zoning: Optional[str] = Field(None, description="Zoning classification")
    easements: Optional[List[str]] = Field(None, description="Easements affecting property")
    encumbrances: Optional[List[str]] = Field(None, description="Encumbrances on property")
    
    # Strata/body corporate
    is_strata: bool = Field(default=False, description="Whether property is strata titled")
    strata_plan_number: Optional[str] = Field(None, description="Strata plan number")
    body_corporate_name: Optional[str] = Field(None, description="Body corporate name")
    strata_fees: Optional[FinancialAmount] = Field(None, description="Strata fees")


# Comprehensive extraction result
class ContractEntityExtraction(BaseModel):
    """Complete entity extraction results for a contract"""
    
    # Document metadata
    document_id: str = Field(..., description="Document identifier")
    contract_type: ContractType = Field(..., description="Type of contract")
    australian_state: Optional[AustralianState] = Field(None, description="Australian state for contract")
    
    # Core entities
    property_address: Optional[PropertyAddress] = Field(None, description="Main property address")
    parties: List[ContractParty] = Field(default_factory=list, description="All parties to contract")
    dates: List[ContractDate] = Field(default_factory=list, description="Important dates")
    financial_amounts: List[FinancialAmount] = Field(default_factory=list, description="Financial amounts")
    
    # Legal and compliance
    legal_references: List[LegalReference] = Field(default_factory=list, description="Legal references")
    conditions: List[ContractCondition] = Field(default_factory=list, description="Contract conditions")
    
    # Property details
    property_details: Optional[PropertyDetails] = Field(None, description="Detailed property information")
    
    # Additional entities
    additional_addresses: List[PropertyAddress] = Field(default_factory=list, description="Additional addresses mentioned")
    contact_references: List[str] = Field(default_factory=list, description="Contact information found")
    
    # Extraction metadata
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall extraction confidence")
    pages_processed: List[int] = Field(default_factory=list, description="Pages that were processed")
    extraction_notes: List[str] = Field(default_factory=list, description="Notes about extraction process")
    
    # Quality assessment
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="How complete the extraction is")
    accuracy_indicators: Dict[str, float] = Field(default_factory=dict, description="Accuracy scores by entity type")


# Diagram-specific entity extraction
class DiagramEntityExtraction(BaseModel):
    """Entity extraction specific to diagram analysis"""
    
    diagram_id: str = Field(..., description="Diagram identifier")
    diagram_type: str = Field(..., description="Type of diagram")
    page_number: int = Field(..., description="Page number of diagram")
    
    # Infrastructure elements
    infrastructure_elements: List[str] = Field(default_factory=list, description="Infrastructure found in diagram")
    utilities: List[str] = Field(default_factory=list, description="Utilities shown")
    boundaries: List[str] = Field(default_factory=list, description="Boundary information")
    
    # Measurements and specifications
    measurements: List[str] = Field(default_factory=list, description="Measurements found")
    specifications: List[str] = Field(default_factory=list, description="Technical specifications")
    
    # Risk indicators
    risk_indicators: List[str] = Field(default_factory=list, description="Potential risk indicators")
    compliance_elements: List[str] = Field(default_factory=list, description="Compliance-related elements")
    
    # Metadata
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in diagram analysis")
    analysis_notes: List[str] = Field(default_factory=list, description="Analysis notes")


# Validation helpers
@validator('postcode', 'always', pre=True)
def validate_australian_postcode(cls, v):
    """Validate Australian postcode format"""
    if v and isinstance(v, str):
        v = v.strip()
        if len(v) == 4 and v.isdigit():
            return v
    return v


@validator('amount', pre=True)
def parse_financial_amount(cls, v):
    """Parse financial amounts from text"""
    if isinstance(v, str):
        # Remove currency symbols and commas
        cleaned = v.replace('$', '').replace(',', '').strip()
        try:
            return Decimal(cleaned)
        except:
            raise ValueError(f"Invalid financial amount: {v}")
    return v