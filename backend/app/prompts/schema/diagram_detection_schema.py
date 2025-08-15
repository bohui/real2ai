"""Schema for OCR-based diagram detection response"""

from typing import List
from pydantic import BaseModel, Field

from app.schema.enums import DiagramType


class DiagramDetectionItem(BaseModel):
    """Single diagram detection result"""

    type: DiagramType = Field(
        ..., description="Type of diagram detected from predefined categories"
    )
    page: int = Field(
        ..., description="Page number where the diagram is located (1-based)"
    )


class DiagramDetectionResponse(BaseModel):
    """Response schema for diagram detection from OCR service"""

    diagram: List[DiagramDetectionItem] = Field(
        default_factory=list,
        description="List of detected diagrams with their types and page numbers",
    )

    model_config = {"use_enum_values": True, "arbitrary_types_allowed": True}
