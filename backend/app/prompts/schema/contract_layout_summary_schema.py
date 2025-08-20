"""
Contract Layout Summary Output Schema

Defines structured output for the layout_summarise step which cleans full text
and extracts basic contract information suitable for taxonomy upsert.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schema.enums import (
    AustralianState,
    ContractType,
    PurchaseMethod,
    UseCategory,
)


class ContractLayoutSummary(BaseModel):
    """Model for summarised contract layout and basic information."""

    success: bool = True
    error: Optional[str] = None
    # Cleaned and normalised raw text (headers/footers removed, spacing normalised)
    raw_text: str = Field(
        ...,
        description="Cleaned full text with headers/footers removed and normalised formatting",
    )

    # Basic classification/taxonomy
    contract_type: ContractType = Field(..., description="Detected contract type")
    purchase_method: Optional[PurchaseMethod] = Field(
        None, description="Detected purchase method when applicable"
    )
    use_category: Optional[UseCategory] = Field(
        None, description="Detected property use category when applicable"
    )

    # Optional state override if confidently inferred from content
    australian_state: Optional[AustralianState] = Field(
        None, description="Australian state if detected from document content"
    )

    # Structured terms dictionary (keys depend on detected contract type)
    contract_terms: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted key contract terms"
    )

    # Optional property address normalised when confidently detected
    property_address: Optional[str] = Field(
        None, description="Detected property address if available"
    )

    # Confidence per extracted field (0.0 - 1.0)
    ocr_confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores per extracted field (e.g., contract_type, purchase_method)",
    )
