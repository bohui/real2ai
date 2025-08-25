from typing import List
from pydantic import BaseModel, Field

from app.schema.enums import ImageType


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


class TextDiagramInsightList(BaseModel):
    """Structured OCR result that supports multiple diagram hints per page."""

    text: str = Field(
        "",
        description="Extracted full text from the image, default to empty string if no text is found",
    )
    text_confidence: float = Field(0.0, description="OCR confidence score (0.0-1.0)")
    diagrams: List[ImageType] = Field(
        default_factory=list,
        description="List of diagram hints detected in the image",
    )
    diagrams_confidence: float = Field(
        0.0, description="Diagram detection confidence score (0.0-1.0)"
    )

    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True,
    }
