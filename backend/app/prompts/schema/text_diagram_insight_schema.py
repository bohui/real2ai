from typing import Optional
from pydantic import BaseModel, Field


class TextDiagramInsight(BaseModel):
    """Minimal schema for OCR text + diagram classification result."""

    text: str = Field(..., description="Extracted full text from the image")
    confidence: float = Field(..., description="OCR confidence score (0.0-1.0)")
    is_diagram: bool = Field(
        ..., description="Whether the image is a diagram/plan/map relevant to property"
    )
    diagram_type: Optional[str] = Field(
        None,
        description="Specific diagram type if applicable (e.g., sewer_service_diagram)",
    )

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
