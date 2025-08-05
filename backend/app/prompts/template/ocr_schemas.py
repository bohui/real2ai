"""OCR-specific output parser schemas for document extraction."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from app.model.enums import AustralianState, ContractType, RiskLevel


class DocumentQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNREADABLE = "unreadable"


class ExtractionConfidence(str, Enum):
    HIGH = "high"        # 90-100% confidence
    MEDIUM = "medium"    # 70-89% confidence
    LOW = "low"          # 50-69% confidence
    UNCERTAIN = "uncertain"  # <50% confidence


class DocumentSection(str, Enum):
    HEADER = "header"
    FOOTER = "footer"
    BODY = "body"
    TABLE = "table"
    SIGNATURE_BLOCK = "signature_block"
    SCHEDULE = "schedule"
    ATTACHMENT = "attachment"


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    ADDRESS = "address"
    PHONE = "phone"
    EMAIL = "email"
    SIGNATURE = "signature"
    TABLE_DATA = "table_data"


class OCRExtractedField(BaseModel):
    """Individual extracted field with confidence and position metadata."""

    field_name: str = Field(description="Name/identifier of the extracted field")
    field_type: FieldType = Field(description="Type of data in this field")
    raw_value: str = Field(description="Raw OCR extracted text")
    processed_value: Optional[str] = Field(None, description="Cleaned/processed value")
    confidence: ExtractionConfidence = Field(description="Extraction confidence level")
    
    # Position and context
    document_section: DocumentSection = Field(description="Section where field was found")
    page_number: Optional[int] = Field(None, description="Page number (1-based)")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Bounding box coordinates")
    surrounding_context: Optional[str] = Field(None, description="Text context around field")
    
    # Quality indicators
    ocr_confidence_score: Optional[float] = Field(None, description="OCR engine confidence (0-1)")
    requires_manual_review: bool = Field(default=False, description="Needs human verification")
    extraction_notes: Optional[str] = Field(None, description="Notes about extraction challenges")


class OCRDocumentMetadata(BaseModel):
    """Metadata about the OCR processed document."""

    document_name: Optional[str] = Field(None, description="Document filename or title")
    document_type: Optional[str] = Field(None, description="Detected document type")
    total_pages: int = Field(description="Total number of pages processed")
    overall_quality: DocumentQuality = Field(description="Overall document quality assessment")
    
    # Processing details
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    ocr_engine_version: Optional[str] = Field(None, description="OCR engine version used")
    processing_settings: Optional[Dict[str, Any]] = Field(None, description="OCR settings used")
    
    # Quality metrics
    average_confidence: Optional[float] = Field(None, description="Average OCR confidence across document")
    low_confidence_areas: List[str] = Field(default_factory=list, description="Areas with low confidence")
    manual_review_required: bool = Field(default=False, description="Requires manual review")
    
    # Content analysis
    detected_languages: List[str] = Field(default_factory=list, description="Detected languages")
    handwritten_text_detected: bool = Field(default=False, description="Handwritten text present")
    table_count: int = Field(default=0, description="Number of tables detected")
    signature_count: int = Field(default=0, description="Number of signatures detected")


class OCRFinancialExtraction(BaseModel):
    """Financial information extracted via OCR."""

    # Purchase/Sale amounts
    purchase_price: Optional[OCRExtractedField] = Field(None, description="Purchase price")
    deposit_amount: Optional[OCRExtractedField] = Field(None, description="Deposit amount")
    balance_due: Optional[OCRExtractedField] = Field(None, description="Balance due at settlement")
    
    # Additional amounts
    adjustments: List[OCRExtractedField] = Field(default_factory=list, description="Price adjustments")
    additional_costs: List[OCRExtractedField] = Field(default_factory=list, description="Additional costs")
    gst_amounts: List[OCRExtractedField] = Field(default_factory=list, description="GST related amounts")
    
    # Payment schedule
    payment_schedule: List[OCRExtractedField] = Field(default_factory=list, description="Payment schedule items")
    
    # Validation flags
    amounts_consistent: Optional[bool] = Field(None, description="Financial amounts are internally consistent")
    calculation_errors: List[str] = Field(default_factory=list, description="Detected calculation errors")


class OCRDateExtraction(BaseModel):
    """Date information extracted via OCR."""

    # Critical dates
    contract_date: Optional[OCRExtractedField] = Field(None, description="Contract execution date")
    settlement_date: Optional[OCRExtractedField] = Field(None, description="Settlement date")
    cooling_off_expiry: Optional[OCRExtractedField] = Field(None, description="Cooling off period end")
    possession_date: Optional[OCRExtractedField] = Field(None, description="Possession date")
    
    # Condition deadlines
    finance_approval_deadline: Optional[OCRExtractedField] = Field(None, description="Finance approval deadline")
    building_inspection_deadline: Optional[OCRExtractedField] = Field(None, description="Building inspection deadline")
    pest_inspection_deadline: Optional[OCRExtractedField] = Field(None, description="Pest inspection deadline")
    
    # Other important dates
    other_deadlines: List[OCRExtractedField] = Field(default_factory=list, description="Other critical dates")
    
    # Validation
    date_format_consistent: bool = Field(default=True, description="Dates use consistent format")
    chronological_issues: List[str] = Field(default_factory=list, description="Chronological inconsistencies")


class OCRPartyExtraction(BaseModel):
    """Party information extracted via OCR."""

    # Vendor/Seller
    vendor_names: List[OCRExtractedField] = Field(default_factory=list, description="Vendor names")
    vendor_addresses: List[OCRExtractedField] = Field(default_factory=list, description="Vendor addresses")
    vendor_contacts: List[OCRExtractedField] = Field(default_factory=list, description="Vendor contact details")
    
    # Purchaser/Buyer
    purchaser_names: List[OCRExtractedField] = Field(default_factory=list, description="Purchaser names")
    purchaser_addresses: List[OCRExtractedField] = Field(default_factory=list, description="Purchaser addresses")
    purchaser_contacts: List[OCRExtractedField] = Field(default_factory=list, description="Purchaser contact details")
    
    # Legal representatives
    vendor_solicitor: Optional[OCRExtractedField] = Field(None, description="Vendor's solicitor")
    purchaser_solicitor: Optional[OCRExtractedField] = Field(None, description="Purchaser's solicitor")
    
    # Real estate agents
    selling_agent: Optional[OCRExtractedField] = Field(None, description="Selling agent")
    buyer_agent: Optional[OCRExtractedField] = Field(None, description="Buyer's agent")
    
    # Corporate entities
    company_details: List[OCRExtractedField] = Field(default_factory=list, description="Company ABN, ACN details")


class OCRPropertyExtraction(BaseModel):
    """Property information extracted via OCR."""

    # Address components
    street_address: Optional[OCRExtractedField] = Field(None, description="Street address")
    suburb: Optional[OCRExtractedField] = Field(None, description="Suburb")
    state: Optional[OCRExtractedField] = Field(None, description="State")
    postcode: Optional[OCRExtractedField] = Field(None, description="Postcode")
    
    # Legal identifiers
    lot_number: Optional[OCRExtractedField] = Field(None, description="Lot number")
    plan_number: Optional[OCRExtractedField] = Field(None, description="Plan number")
    title_reference: Optional[OCRExtractedField] = Field(None, description="Title reference")
    
    # Property details
    property_type: Optional[OCRExtractedField] = Field(None, description="Property type")
    land_size: Optional[OCRExtractedField] = Field(None, description="Land size")
    zoning: Optional[OCRExtractedField] = Field(None, description="Zoning")
    
    # Address validation
    address_complete: bool = Field(default=False, description="All address components extracted")
    address_validation_issues: List[str] = Field(default_factory=list, description="Address validation problems")


class OCRConditionsExtraction(BaseModel):
    """Contract conditions extracted via OCR."""

    # Standard conditions
    finance_condition: Optional[OCRExtractedField] = Field(None, description="Finance approval condition")
    finance_amount: Optional[OCRExtractedField] = Field(None, description="Finance amount required")
    building_inspection: Optional[OCRExtractedField] = Field(None, description="Building inspection condition")
    pest_inspection: Optional[OCRExtractedField] = Field(None, description="Pest inspection condition")
    
    # Additional conditions
    additional_conditions: List[OCRExtractedField] = Field(default_factory=list, description="Additional conditions text")
    special_clauses: List[OCRExtractedField] = Field(default_factory=list, description="Special clauses")
    
    # Condition analysis
    conditions_numbered: bool = Field(default=False, description="Conditions are properly numbered")
    handwritten_additions: List[OCRExtractedField] = Field(default_factory=list, description="Handwritten additions")


class OCRTableExtraction(BaseModel):
    """Structured table data extracted via OCR."""

    table_title: Optional[str] = Field(None, description="Table title or caption")
    table_type: Optional[str] = Field(None, description="Type of table (payment, adjustment, etc.)")
    page_number: Optional[int] = Field(None, description="Page where table appears")
    
    # Table structure
    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[List[OCRExtractedField]] = Field(default_factory=list, description="Table rows data")
    
    # Quality indicators
    structure_confidence: ExtractionConfidence = Field(description="Confidence in table structure")
    cell_extraction_issues: List[str] = Field(default_factory=list, description="Cell extraction problems")
    
    # Calculations
    calculated_totals: Optional[Dict[str, OCRExtractedField]] = Field(None, description="Calculated totals from table")
    calculation_verification: Optional[bool] = Field(None, description="Calculations verified as correct")


class OCRSignatureExtraction(BaseModel):
    """Signature and execution information extracted via OCR."""

    # Signature blocks
    vendor_signatures: List[OCRExtractedField] = Field(default_factory=list, description="Vendor signatures")
    purchaser_signatures: List[OCRExtractedField] = Field(default_factory=list, description="Purchaser signatures")
    witness_signatures: List[OCRExtractedField] = Field(default_factory=list, description="Witness signatures")
    
    # Execution dates
    execution_dates: List[OCRExtractedField] = Field(default_factory=list, description="Execution dates")
    
    # Validation
    all_parties_signed: Optional[bool] = Field(None, description="All required parties have signed")
    signature_quality: List[Dict[str, Any]] = Field(default_factory=list, description="Signature quality assessment")


class OCRValidationResults(BaseModel):
    """Validation results for OCR extraction."""

    # Cross-field validation
    internal_consistency: bool = Field(description="Fields are internally consistent")
    required_fields_present: bool = Field(description="All required fields extracted")
    
    # Quality metrics
    overall_extraction_quality: ExtractionConfidence = Field(description="Overall extraction quality")
    manual_review_priority: RiskLevel = Field(description="Priority for manual review")
    
    # Specific issues
    missing_critical_fields: List[str] = Field(default_factory=list, description="Missing critical information")
    conflicting_information: List[str] = Field(default_factory=list, description="Conflicting data found")
    formatting_issues: List[str] = Field(default_factory=list, description="Formatting or structure issues")
    
    # Recommendations
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended next steps")
    specialist_review_needed: List[str] = Field(default_factory=list, description="Areas needing specialist review")


# Main OCR Extraction Schema
class OCRExtractionResults(BaseModel):
    """Complete OCR extraction results for Australian real estate contracts."""

    # Document metadata
    document_metadata: OCRDocumentMetadata = Field(description="Document processing metadata")
    
    # Core extracted data
    financial_data: OCRFinancialExtraction = Field(description="Financial terms and amounts")
    date_information: OCRDateExtraction = Field(description="Critical dates and deadlines")
    party_information: OCRPartyExtraction = Field(description="Parties involved in contract")
    property_details: OCRPropertyExtraction = Field(description="Property information")
    conditions: OCRConditionsExtraction = Field(description="Contract conditions and clauses")
    
    # Structured data
    tables: List[OCRTableExtraction] = Field(default_factory=list, description="Extracted table data")
    signatures: OCRSignatureExtraction = Field(description="Signature and execution information")
    
    # Quality and validation
    validation_results: OCRValidationResults = Field(description="Extraction validation results")
    
    # Additional extracted content
    raw_text_sections: Optional[Dict[str, str]] = Field(None, description="Raw text by section")
    unstructured_content: List[OCRExtractedField] = Field(default_factory=list, description="Other extracted content")
    
    # Processing notes
    extraction_notes: List[str] = Field(default_factory=list, description="Notes from extraction process")
    error_log: List[str] = Field(default_factory=list, description="Errors encountered during processing")


# State-specific OCR schema variations
class NSWOCRSpecifics(BaseModel):
    """NSW-specific OCR extraction requirements."""

    section_10_7_certificate: Optional[OCRExtractedField] = Field(None, description="Section 10.7 planning certificate")
    contract_for_sale_compliance: Optional[OCRExtractedField] = Field(None, description="Conveyancing Act compliance")
    vendor_disclosure_statement: Optional[OCRExtractedField] = Field(None, description="VDS details")
    
    # NSW specific terms
    cooling_off_period: Optional[OCRExtractedField] = Field(None, description="5 business day cooling off")
    mine_subsidence_district: Optional[OCRExtractedField] = Field(None, description="Mine subsidence information")


class VICOCRSpecifics(BaseModel):
    """Victoria-specific OCR extraction requirements."""

    section_32_statement: Optional[OCRExtractedField] = Field(None, description="Section 32 vendor statement")
    owners_corporation_details: Optional[OCRExtractedField] = Field(None, description="Owners corporation information")
    
    # VIC specific terms
    cooling_off_period: Optional[OCRExtractedField] = Field(None, description="3 business day cooling off")
    building_permits: Optional[OCRExtractedField] = Field(None, description="Building permit information")


class QLDOCRSpecifics(BaseModel):
    """Queensland-specific OCR extraction requirements."""

    property_information_form: Optional[OCRExtractedField] = Field(None, description="Property information form")
    body_corporate_certificate: Optional[OCRExtractedField] = Field(None, description="Body corporate information")
    
    # QLD specific terms
    cooling_off_period: Optional[OCRExtractedField] = Field(None, description="5 business day cooling off")
    management_rights: Optional[OCRExtractedField] = Field(None, description="Management rights disclosure")


# Contract type specific schemas
class PurchaseAgreementOCR(OCRExtractionResults):
    """Purchase agreement specific OCR extraction."""
    
    state_specifics: Optional[Union[NSWOCRSpecifics, VICOCRSpecifics, QLDOCRSpecifics]] = Field(
        None, description="State-specific extracted information"
    )


class AuctionContractOCR(OCRExtractionResults):
    """Auction contract specific OCR extraction."""
    
    auction_date: Optional[OCRExtractedField] = Field(None, description="Auction date")
    auction_conditions: Optional[OCRExtractedField] = Field(None, description="Auction specific conditions")
    reserve_price: Optional[OCRExtractedField] = Field(None, description="Reserve price if disclosed")


class OffPlanContractOCR(OCRExtractionResults):
    """Off-plan contract specific OCR extraction."""
    
    development_details: Optional[OCRExtractedField] = Field(None, description="Development information")
    completion_date: Optional[OCRExtractedField] = Field(None, description="Expected completion date")
    sunset_clause: Optional[OCRExtractedField] = Field(None, description="Sunset clause terms")


# OCR Quality Validation Prompt Template
OCR_EXTRACTION_PROMPT_TEMPLATE = """
You are an expert OCR specialist focused on Australian real estate contract extraction.
Extract all information from the provided document with high attention to quality and accuracy.

Document Type: {contract_type}
State Jurisdiction: {state}
Quality Requirements: {quality_level}

EXTRACTION PRIORITIES:

1. **CRITICAL FINANCIAL DATA** (highest accuracy required):
   - Purchase price, deposit amounts, balance due
   - Payment schedules and adjustment calculations
   - All dollar amounts with confidence scoring

2. **CRITICAL DATES** (verify format consistency):
   - Contract date, settlement date, cooling off expiry
   - All condition deadlines with DD/MM/YYYY format validation
   - Chronological consistency checks

3. **PARTY IDENTIFICATION**:
   - Full legal names, addresses, contact details
   - Corporate entities with ABN/ACN numbers
   - Legal representatives and agents

4. **PROPERTY DETAILS**:
   - Complete address with validation
   - Title references, lot/plan numbers
   - Property type and characteristics

5. **CONDITIONS AND CLAUSES**:
   - All numbered conditions with full text
   - Special clauses and handwritten additions
   - Additional conditions beyond template

QUALITY CONTROL REQUIREMENTS:

- Flag any field with <70% OCR confidence for manual review
- Cross-validate financial calculations and date sequences  
- Identify handwritten text requiring special attention
- Note any missing critical information
- Assess overall document readability and extraction completeness

For each extracted field, provide:
- Raw OCR text and processed value
- Confidence level and quality indicators
- Position information and context
- Flags for manual review if needed

Focus on accuracy over completeness - better to flag uncertain extractions than provide incorrect data.

Return results in the OCRExtractionResults schema format with comprehensive validation.
"""


# OCR Processing Configuration
OCR_QUALITY_SETTINGS = {
    "high_quality": {
        "min_confidence_threshold": 0.8,
        "manual_review_threshold": 0.7,
        "multiple_pass_processing": True,
        "advanced_image_enhancement": True,
        "legal_terminology_dictionary": True,
    },
    "standard": {
        "min_confidence_threshold": 0.7,
        "manual_review_threshold": 0.6,
        "multiple_pass_processing": False,
        "advanced_image_enhancement": True,
        "legal_terminology_dictionary": True,
    },
    "fast": {
        "min_confidence_threshold": 0.6,
        "manual_review_threshold": 0.5,
        "multiple_pass_processing": False,
        "advanced_image_enhancement": False,
        "legal_terminology_dictionary": False,
    }
}


# Field validation patterns
FIELD_VALIDATION_PATTERNS = {
    "currency": r"^\$?[\d,]+\.?\d{0,2}$",
    "date_australian": r"^\d{1,2}\/\d{1,2}\/\d{4}$",
    "postcode_australian": r"^\d{4}$",
    "abn": r"^\d{2}\s?\d{3}\s?\d{3}\s?\d{3}$",
    "acn": r"^\d{3}\s?\d{3}\s?\d{3}$",
    "lot_plan": r"^(Lot\s?\d+|Unit\s?\d+).*(Plan\s?\w+)$",
    "title_reference": r"^(Volume\s?\d+|Vol\s?\d+).*(Folio\s?\d+|Fol\s?\d+)$",
}


# Contract type to schema mapping
CONTRACT_OCR_SCHEMA_MAPPING = {
    ContractType.PURCHASE_AGREEMENT: PurchaseAgreementOCR,
    ContractType.AUCTION_CONTRACT: AuctionContractOCR,
    ContractType.OFF_PLAN_CONTRACT: OffPlanContractOCR,
    ContractType.LEASE_AGREEMENT: OCRExtractionResults,  # Default for now
}


# State-specific schema mapping
STATE_OCR_SPECIFICS_MAPPING = {
    AustralianState.NSW: NSWOCRSpecifics,
    AustralianState.VIC: VICOCRSpecifics,  
    AustralianState.QLD: QLDOCRSpecifics,
    # Other states default to base extraction
}