"""
Section Extraction Schemas

Pydantic models dedicated to section seed extraction for Step 1 (planner-only).
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.schema.enums import SectionKey


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


class SectionExtractionOutput(BaseModel):
    """Section seeds output for Step 1 (planner-only)."""

    snippets: Dict[str, List[SectionSeedSnippet]] = Field(
        default_factory=dict,
        description="Per-section list of seed snippets keyed by section key",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for this extraction (0-1)",
    )
