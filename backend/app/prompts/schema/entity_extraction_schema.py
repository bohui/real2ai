"""
Entity Extraction Schemas for Contract Analysis
Pydantic models for structured entity extraction from legal documents
"""

from typing import Dict, List, Optional, ClassVar
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date
from decimal import Decimal
from app.schema.enums import (
    AustralianState,
    ContractType,
    PartyRole,
    PropertyType,
    DateType,
    FinancialType,
    PaymentDueEvent,
    PurchaseMethod,
    UseCategory,
    PropertyCondition,
    TransactionComplexity,
    SectionKey,
)


# Base entity models
class EntityBase(BaseModel):
    """Base class for all entities"""

    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for extraction"
    )
    page_number: int = Field(..., ge=1, description="Page number where entity appears")
    context: Optional[str] = Field(None, description="Surrounding text context")
    extraction_method: str = Field(
        default="llm", description="Method used for extraction"
    )


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

    name: Optional[str] = Field(
        None, description="Full name of party (null if unspecified)"
    )
    role: PartyRole = Field(..., description="Role in the contract")

    # Contact information
    address: Optional[str] = Field(None, description="Address of party")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")

    # Legal representation
    solicitor_name: Optional[str] = Field(
        None, description="Name of solicitor/conveyancer"
    )
    solicitor_firm: Optional[str] = Field(None, description="Law firm name")
    solicitor_contact: Optional[str] = Field(
        None, description="Solicitor contact details"
    )

    @field_validator("name")
    @classmethod
    def validate_name_when_null(cls, v, info):
        """Ensure context provides information when name is null"""
        if v is None and not info.data.get("context"):
            raise ValueError("context must be provided when name is null")
        return v


class ContractDate(EntityBase):
    """Important dates in contract"""

    date_value: Optional[date] = Field(
        None, description="The actual date (null if cannot be determined)"
    )
    date_type: DateType = Field(..., description="Type/purpose of this date")
    date_text: str = Field(..., description="Date as it appears in document")

    # Additional context
    is_business_days: Optional[bool] = Field(
        None, description="Whether date calculation uses business days"
    )
    timezone: Optional[str] = Field(None, description="Timezone if specified")
    conditions: Optional[str] = Field(
        None, description="Conditions attached to this date"
    )

    @field_validator("date_text")
    @classmethod
    def validate_date_text_when_null(cls, v, info):
        """Ensure date_text provides context when date_value is null"""
        if info.data.get("date_value") is None and not v:
            raise ValueError("date_text must be provided when date_value is null")
        return v


class FinancialAmount(EntityBase):
    """Financial amounts and terms"""

    amount: Optional[Decimal] = Field(
        None, description="Monetary amount (null if cannot be determined)"
    )
    currency: str = Field(default="AUD", description="Currency code")
    amount_type: FinancialType = Field(..., description="Type of financial amount")
    amount_text: str = Field(..., description="Amount as written in document")

    # Payment terms
    payment_method: Optional[str] = Field(None, description="How payment is to be made")
    payment_due_date: Optional[date] = Field(None, description="When payment is due")
    payment_due_event: Optional[PaymentDueEvent] = Field(
        None,
        description="Trigger event when due date is relative (e.g., completion, settlement)",
    )
    payment_conditions: Optional[str] = Field(
        None, description="Conditions for payment"
    )

    # Calculations
    is_percentage: bool = Field(
        default=False, description="Whether amount is a percentage"
    )
    percentage_of: Optional[str] = Field(
        None, description="What the percentage is calculated on"
    )

    @model_validator(mode="before")
    def normalize_due_fields(cls, values):
        """Normalize payment_due_date and payment_due_event.

        - If payment_due_date is a keyword like 'completion'/'settlement', move it into payment_due_event.
        - Keep payment_due_date strictly as a calendar date when present.
        """
        due = values.get("payment_due_date")
        if isinstance(due, str):
            lowered = due.strip().lower()
            mapping = {
                "completion": PaymentDueEvent.COMPLETION,
                "on completion": PaymentDueEvent.COMPLETION,
                "settlement": PaymentDueEvent.SETTLEMENT,
                "on settlement": PaymentDueEvent.SETTLEMENT,
                "exchange": PaymentDueEvent.EXCHANGE,
                "on exchange": PaymentDueEvent.EXCHANGE,
                "contract_date": PaymentDueEvent.CONTRACT_DATE,
                "contract date": PaymentDueEvent.CONTRACT_DATE,
                "notice to complete": PaymentDueEvent.NOTICE_TO_COMPLETE,
            }
            # Exact match first, then substring fallback for robustness
            event = mapping.get(lowered)
            if event is None:
                for key, enum_val in mapping.items():
                    if key in lowered:
                        event = enum_val
                        break
            if event is not None:
                values["payment_due_event"] = values.get("payment_due_event") or event
                values["payment_due_date"] = None
        return values


class LegalReference(EntityBase):
    """Legal references and compliance information"""

    reference_type: str = Field(..., description="Type of legal reference")
    reference_text: str = Field(..., description="The legal reference as written")

    # Australian-specific
    act_name: Optional[str] = Field(None, description="Name of legislation")
    section_number: Optional[str] = Field(None, description="Section or clause number")
    state_specific: Optional[AustralianState] = Field(
        None, description="State-specific legislation"
    )

    # Compliance
    compliance_requirement: Optional[str] = Field(
        None, description="What compliance is required"
    )
    mandatory: bool = Field(
        default=False, description="Whether compliance is mandatory"
    )


class ContractCondition(EntityBase):
    """Contract conditions and clauses (extraction-only, no risk scoring)."""

    clause_id: Optional[str] = Field(
        None, description="Clause identifier or heading as written"
    )
    condition_type: Optional[str] = Field(
        None, description="Type of condition if explicitly stated"
    )
    condition_text: str = Field(..., description="Full text of the condition excerpt")
    condition_summary: Optional[str] = Field(
        None, description="Brief summary of the condition"
    )

    # Classification (only when explicit)
    is_special_condition: Optional[bool] = Field(
        None, description="Whether this is a special condition (explicit)"
    )
    is_standard_condition: Optional[bool] = Field(
        None, description="Whether this is a standard condition (explicit)"
    )

    # Parties and responsibilities (if explicit)
    action_by_whom: Optional[List[PartyRole]] = Field(
        None, description="Parties responsible (if stated)"
    )
    requires_action: Optional[bool] = Field(
        None, description="Whether condition requires action (explicit)"
    )
    action_required: Optional[str] = Field(
        None, description="Action required (explicit)"
    )

    # Deadlines (if explicit)
    deadline_text: Optional[str] = Field(
        None, description="Deadline as written in the contract"
    )
    action_deadline: Optional[date] = Field(
        None, description="Normalized deadline if determinable"
    )


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
    easements: Optional[List[str]] = Field(
        None, description="Easements affecting property"
    )
    encumbrances: Optional[List[str]] = Field(
        None, description="Encumbrances on property"
    )

    # Strata/body corporate
    is_strata: bool = Field(
        default=False, description="Whether property is strata titled"
    )
    strata_plan_number: Optional[str] = Field(None, description="Strata plan number")
    body_corporate_name: Optional[str] = Field(None, description="Body corporate name")
    strata_fees: Optional[FinancialAmount] = Field(None, description="Strata fees")


class ContractMetadata(BaseModel):
    """Combined output for rough basic structure analysis.

    Aggregates key results to quickly understand contract structure and risks.
    """

    state: Optional[AustralianState] = Field(
        default=None, description="Australian state for contract"
    )
    contract_type: Optional[ContractType] = Field(
        default=None, description="Detected contract type"
    )
    purchase_method: Optional[PurchaseMethod] = Field(
        default=None, description="Detected purchase method (if applicable)"
    )
    use_category: Optional[UseCategory] = Field(
        default=None, description="Detected use category"
    )
    property_condition: Optional[PropertyCondition] = Field(
        default=None, description="Detected property condition/building work status"
    )
    transaction_complexity: Optional[TransactionComplexity] = Field(
        default=None, description="Detected transaction complexity level"
    )
    overall_confidence: Optional[float] = Field(
        default=None, ge=0, le=1, description="Overall confidence for this analysis"
    )
    sources: Optional[Dict[str, str]] = Field(
        default=None, description="Text excerpts from contract supporting each decision"
    )

    @field_validator("contract_type", mode="before")
    def validate_contract_type(cls, v):
        if isinstance(v, str):
            try:
                return ContractType(v.lower())
            except Exception:
                return None
        return v

    @field_validator("purchase_method", mode="before")
    def validate_purchase_method(cls, v):
        if isinstance(v, str):
            try:
                return PurchaseMethod(v.lower())
            except Exception:
                return None
        return v

    @field_validator("use_category", mode="before")
    def validate_use_category(cls, v):
        if isinstance(v, str):
            try:
                return UseCategory(v.lower())
            except Exception:
                return None
        return v

    @field_validator("property_condition", mode="before")
    def validate_property_condition(cls, v):
        if isinstance(v, str):
            try:
                return PropertyCondition(v.lower())
            except Exception:
                return None
        return v

    @field_validator("transaction_complexity", mode="before")
    def validate_transaction_complexity(cls, v):
        if isinstance(v, str):
            try:
                return TransactionComplexity(v.lower())
            except Exception:
                return None
        return v


# Comprehensive extraction result
class SectionSeedSnippet(BaseModel):
    """High-signal snippet selected by Step 1 to seed Step 2 analysis for a section."""

    section_key: SectionKey = Field(..., description="Section identifier (enum)")
    clause_id: Optional[str] = Field(None, description="Clause id/heading if available")
    page_number: Optional[int] = Field(None, description="Page number")
    start_offset: Optional[int] = Field(None, description="Character start offset")
    end_offset: Optional[int] = Field(None, description="Character end offset")
    snippet_text: str = Field(..., description="Selected snippet text")
    selection_rationale: Optional[str] = Field(
        None, description="Why this snippet was selected"
    )
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence for this selection"
    )


class SectionSeeds(BaseModel):
    """Aggregated per-section seed snippets and retrieval guidance."""

    retrieval_index_id: Optional[str] = Field(
        None, description="Identifier/handle for paragraph/clause retrieval index"
    )
    retrieval_instructions: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-section suggested retrieval queries keyed by section key",
    )
    snippets: Dict[str, List[SectionSeedSnippet]] = Field(
        default_factory=dict,
        description="Per-section list of seed snippets keyed by section key",
    )


class ContractEntityExtraction(BaseModel):
    """Complete entity extraction results for a contract"""

    # Model config: when True, schema is conveyed via prompt instead of response_schema
    schema_in_prompt: ClassVar[bool] = True

    # contract metadata
    metadata: ContractMetadata = Field(..., description="Contract metadata")

    # Core entities
    property_address: Optional[PropertyAddress] = Field(
        None, description="Main property address"
    )
    parties: List[ContractParty] = Field(
        default_factory=list, description="All parties to contract"
    )
    dates: List[ContractDate] = Field(
        default_factory=list, description="Important dates"
    )
    financial_amounts: List[FinancialAmount] = Field(
        default_factory=list, description="Financial amounts"
    )

    # Legal and compliance
    legal_references: List[LegalReference] = Field(
        default_factory=list, description="Legal references"
    )
    conditions: List[ContractCondition] = Field(
        default_factory=list, description="Contract conditions (extraction-only)"
    )

    # Property details
    property_details: Optional[PropertyDetails] = Field(
        None, description="Detailed property information"
    )

    # Additional entities
    additional_addresses: List[PropertyAddress] = Field(
        default_factory=list, description="Additional addresses mentioned"
    )
    contact_references: List[str] = Field(
        default_factory=list, description="Contact information found"
    )

    # Step 1 planner outputs for Step 2 (seeds + retrieval)
    section_seeds: Optional[SectionSeeds] = Field(
        default=None, description="Per-section seed snippets and retrieval guidance"
    )

    # # Extraction metadata
    # extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    # overall_confidence: float = Field(
    #     ..., ge=0.0, le=1.0, description="Overall extraction confidence"
    # )
    # pages_processed: List[int] = Field(
    #     default_factory=list, description="Pages that were processed"
    # )
    # extraction_notes: List[str] = Field(
    #     default_factory=list, description="Notes about extraction process"
    # )

    # # Quality assessment
    # completeness_score: float = Field(
    #     default=0.0, ge=0.0, le=1.0, description="How complete the extraction is"
    # )
    # accuracy_indicators: Dict[str, float] = Field(
    #     default_factory=dict, description="Accuracy scores by entity type"
    # )


# Diagram-specific entity extraction
class DiagramEntityExtraction(BaseModel):
    """Entity extraction specific to diagram analysis"""

    diagram_id: str = Field(..., description="Diagram identifier")
    diagram_type: str = Field(..., description="Type of diagram")
    page_number: int = Field(..., description="Page number of diagram")

    # Infrastructure elements
    infrastructure_elements: List[str] = Field(
        default_factory=list, description="Infrastructure found in diagram"
    )
    utilities: List[str] = Field(default_factory=list, description="Utilities shown")
    boundaries: List[str] = Field(
        default_factory=list, description="Boundary information"
    )

    # Measurements and specifications
    measurements: List[str] = Field(
        default_factory=list, description="Measurements found"
    )
    specifications: List[str] = Field(
        default_factory=list, description="Technical specifications"
    )

    # Risk indicators
    risk_indicators: List[str] = Field(
        default_factory=list, description="Potential risk indicators"
    )
    compliance_elements: List[str] = Field(
        default_factory=list, description="Compliance-related elements"
    )

    # Metadata
    extraction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in diagram analysis"
    )
    analysis_notes: List[str] = Field(
        default_factory=list, description="Analysis notes"
    )


# Validation helpers
@field_validator("postcode", mode="before")
@classmethod
def validate_australian_postcode(cls, v):
    """Validate Australian postcode format"""
    if v and isinstance(v, str):
        v = v.strip()
        if len(v) == 4 and v.isdigit():
            return v
    return v


@field_validator("amount", mode="before")
@classmethod
def parse_financial_amount(cls, v):
    """Parse financial amounts from text"""
    if isinstance(v, str):
        # Remove currency symbols and commas
        cleaned = v.replace("$", "").replace(",", "").strip()
        try:
            return Decimal(cleaned)
        except:
            raise ValueError(f"Invalid financial amount: {v}")
    return v
