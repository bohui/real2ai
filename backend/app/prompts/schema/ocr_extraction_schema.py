"""
OCR Extraction Output Schema for Structured Text Extraction
Supports multi-page documents with page number references
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.schema.enums import DocumentType, AustralianState


class TextBlock(BaseModel):
    """A block of extracted text with location reference"""

    text: str = Field(..., description="The extracted text content")
    page_number: int = Field(
        ..., description="Page number where this text appears (1-indexed)"
    )
    section_type: str = Field(
        ..., description="Type of section (header, body, footer, table, list, etc.)"
    )
    confidence: float = Field(
        default=1.0, description="Confidence score for this text block (0.0-1.0)"
    )
    position_hint: Optional[str] = Field(
        None, description="Position hint (top, middle, bottom, left, right)"
    )


class KeyValuePair(BaseModel):
    """Key-value pair extracted from document with page reference"""

    key: str = Field(..., description="The key/label")
    value: str = Field(..., description="The associated value")
    page_number: int = Field(..., description="Page number where this appears")
    confidence: float = Field(default=1.0, description="Confidence in the extraction")


class FinancialAmount(BaseModel):
    """Financial amount with page reference"""

    amount: str = Field(
        ..., description="The monetary amount as string (preserve original formatting)"
    )
    currency: str = Field(default="AUD", description="Currency code")
    context: str = Field(
        ..., description="Context of this amount (purchase price, deposit, rent, etc.)"
    )
    page_number: int = Field(..., description="Page number where this amount appears")


class ImportantDate(BaseModel):
    """Important date with page reference"""

    date_text: str = Field(..., description="Date as it appears in document")
    date_type: str = Field(
        ..., description="Type of date (settlement, completion, lease_start, etc.)"
    )
    page_number: int = Field(..., description="Page number where this date appears")


class DocumentStructure(BaseModel):
    """Document structure information"""

    total_pages: int = Field(..., description="Total number of pages in document")
    page_headers: List[str] = Field(
        default_factory=list, description="Headers found on each page"
    )
    page_footers: List[str] = Field(
        default_factory=list, description="Footers found on each page"
    )
    has_signatures: bool = Field(
        default=False, description="Whether document contains signatures"
    )
    has_handwritten_notes: bool = Field(
        default=False, description="Whether document contains handwritten text"
    )


class OCRExtractionResult(BaseModel):
    """Complete OCR extraction result with structured data and page references"""

    # Document metadata
    document_type: DocumentType = Field(..., description="Detected document type")
    australian_state: Optional[AustralianState] = Field(
        None, description="Australian state if detected"
    )
    document_structure: DocumentStructure = Field(
        ..., description="Document structure information"
    )

    # Full text extraction
    full_text: str = Field(..., description="Complete extracted text from all pages")
    text_blocks: List[TextBlock] = Field(
        ..., description="Text blocks with page references"
    )

    # Structured data extraction
    key_value_pairs: List[KeyValuePair] = Field(
        default_factory=list, description="Key-value pairs found in document"
    )
    financial_amounts: List[FinancialAmount] = Field(
        default_factory=list, description="Financial amounts with context"
    )
    important_dates: List[ImportantDate] = Field(
        default_factory=list, description="Important dates found"
    )

    # Quality and metadata
    extraction_confidence: float = Field(
        ..., description="Overall extraction confidence (0.0-1.0)"
    )
    processing_notes: List[str] = Field(
        default_factory=list,
        description="Notes about processing issues or clarifications",
    )
    unclear_sections: List[Dict[str, Any]] = Field(
        default_factory=list, description="Sections that were unclear or problematic"
    )

    # Australian legal document specific fields
    detected_legal_terms: List[str] = Field(
        default_factory=list, description="Australian legal terms detected"
    )
    compliance_indicators: List[str] = Field(
        default_factory=list,
        description="Compliance indicators found (cooling-off, warranties, etc.)",
    )


class QuickOCRResult(BaseModel):
    """Simplified OCR result for basic text extraction"""

    full_text: str = Field(..., description="Complete extracted text")
    page_count: int = Field(..., description="Number of pages processed")
    confidence: float = Field(..., description="Overall extraction confidence")
    key_information: List[KeyValuePair] = Field(
        default_factory=list, description="Key information extracted"
    )
