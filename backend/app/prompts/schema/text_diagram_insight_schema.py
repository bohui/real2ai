from typing import List
from pydantic import BaseModel, Field

from app.schema.enums import DiagramType


# class TextDiagramInsight(BaseModel):
#     """Minimal schema for OCR text + diagram classification result."""

#     text: str = Field(..., description="Extracted full text from the image")
#     confidence: float = Field(..., description="OCR confidence score (0.0-1.0)")
#     is_diagram: bool = Field(
#         ..., description="Whether the image is a diagram/plan/map relevant to property"
#     )
#     diagram_type: Optional[str] = Field(
#         None,
#         description="Specific diagram type if applicable (e.g., sewer_service_diagram)",
#     )

#     model_config = {"use_enum_values": True, "arbitrary_types_allowed": True}


# class DiagramHintItem(BaseModel):
#     """Single diagram hint in a page image."""

#     is_diagram: bool = Field(..., description="Whether a diagram/plan/map is present")
#     diagram_type: Optional[str] = Field(
#         None, description="Specific diagram type if applicable"
#     )

MAX_TEXT_LENGTH = 7000

# assume one diagram per page is enough for now
MAX_DIAGRAMS = 1


class TextDiagramInsightList(BaseModel):
    """Structured OCR result that supports multiple diagram hints per page."""

    text: str = Field(
        "",
        description="Extracted full text from the image, default to empty string if no text is found,"
        "truncate it if text more than 7000 characters or more than 1200 words or more than 300 lines",
        max_length=MAX_TEXT_LENGTH,
    )
    text_confidence: float = Field(0.0, description="OCR confidence score (0.0-1.0)")
    diagrams: List[DiagramType] = Field(
        default_factory=list,
        description="List of diagram types found in the image. Return empty list if the image contains only text, decorative elements (icons, banners), or no semantically meaningful diagrams",
        max_length=MAX_DIAGRAMS,
    )
    diagrams_confidence: float = Field(
        0.0, description="Diagram detection confidence score (0.0-1.0)"
    )

    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True,
    }
