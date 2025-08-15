from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from app.schema.enums import ImageType, ConfidenceLevel

class LocationReference(BaseModel):
    """Spatial location reference within the image"""
    x_coordinate: Optional[float] = Field(None, description="X coordinate (0-1 normalized)")
    y_coordinate: Optional[float] = Field(None, description="Y coordinate (0-1 normalized)")
    width: Optional[float] = Field(None, description="Width (0-1 normalized)")
    height: Optional[float] = Field(None, description="Height (0-1 normalized)")
    description: str = Field(..., description="Text description of location")
    landmarks: List[str] = Field(default=[], description="Nearby landmarks or reference points")

class SemanticElement(BaseModel):
    """Individual semantic element identified in the image"""
    element_type: str = Field(..., description="Type of element (pipe, building, boundary, etc.)")
    description: str = Field(..., description="Detailed description of the element")
    location: LocationReference = Field(..., description="Location within the image")
    properties: Dict[str, Any] = Field(default={}, description="Additional properties (size, material, etc.)")
    confidence: ConfidenceLevel = Field(..., description="Confidence in identification")
    risk_relevance: Optional[str] = Field(None, description="Relevance to property risk assessment")

class InfrastructureElement(SemanticElement):
    """Infrastructure-specific semantic element"""
    infrastructure_type: str = Field(..., description="Type of infrastructure (sewer, water, gas, power, etc.)")
    pipe_diameter: Optional[str] = Field(None, description="Pipe diameter if applicable")
    depth: Optional[str] = Field(None, description="Depth below surface if shown")
    material: Optional[str] = Field(None, description="Material type if visible")
    ownership: Optional[str] = Field(None, description="Council/private ownership if indicated")
    maintenance_access: Optional[str] = Field(None, description="Access requirements for maintenance")

class BoundaryElement(SemanticElement):
    """Property boundary semantic element"""
    boundary_type: str = Field(..., description="Type of boundary (front, rear, side, common)")
    boundary_marking: Optional[str] = Field(None, description="How boundary is marked (fence, survey pegs, etc.)")
    dimensions: Optional[str] = Field(None, description="Boundary dimensions if shown")
    encroachments: List[str] = Field(default=[], description="Any encroachments noted")
    easements: List[str] = Field(default=[], description="Easements along this boundary")

class EnvironmentalElement(SemanticElement):
    """Environmental feature semantic element"""
    environmental_type: str = Field(..., description="Type of environmental feature")
    risk_level: Optional[str] = Field(None, description="Associated risk level if indicated")
    impact_area: Optional[str] = Field(None, description="Area of impact if shown")
    mitigation_measures: List[str] = Field(default=[], description="Mitigation measures if noted")

class BuildingElement(SemanticElement):
    """Building or structure semantic element"""
    building_type: str = Field(..., description="Type of building or structure")
    construction_stage: Optional[str] = Field(None, description="Construction stage if applicable")
    height_restrictions: Optional[str] = Field(None, description="Height restrictions if shown")
    setback_requirements: Optional[str] = Field(None, description="Setback requirements if noted")
    building_envelope: Optional[str] = Field(None, description="Building envelope constraints")

class TextualInformation(BaseModel):
    """Text found in the image with semantic context"""
    text_content: str = Field(..., description="The extracted text")
    location: LocationReference = Field(..., description="Location of the text")
    text_type: str = Field(..., description="Type of text (label, measurement, title, etc.)")
    font_size: Optional[str] = Field(None, description="Relative font size (large, medium, small)")
    significance: str = Field(..., description="How significant this text is to property understanding")

class SpatialRelationship(BaseModel):
    """Relationship between different elements in the image"""
    element1_id: str = Field(..., description="ID of first element")
    element2_id: str = Field(..., description="ID of second element")
    relationship_type: str = Field(..., description="Type of relationship (adjacent, under, crosses, etc.)")
    distance: Optional[str] = Field(None, description="Distance between elements if measurable")
    impact_description: str = Field(..., description="How this relationship impacts property risk")

class RiskIndicator(BaseModel):
    """Potential risk identified from semantic analysis"""
    risk_type: str = Field(..., description="Type of risk identified")
    severity: str = Field(..., description="Potential severity (low, medium, high, critical)")
    description: str = Field(..., description="Detailed description of the risk")
    evidence_elements: List[str] = Field(..., description="Element IDs that indicate this risk")
    location_description: str = Field(..., description="Where on the property this risk exists")
    recommended_action: Optional[str] = Field(None, description="Recommended action to address risk")

class ImageSemantics(BaseModel):
    """Complete semantic analysis of an image/diagram"""
    
    # Image metadata
    image_type: ImageType = Field(..., description="Type of image analyzed")
    image_title: Optional[str] = Field(None, description="Title or heading found in image")
    scale_information: Optional[str] = Field(None, description="Scale information if present")
    orientation: Optional[str] = Field(None, description="Orientation (North arrow, etc.)")
    legend_information: List[str] = Field(default=[], description="Legend or key information")
    
    # Core semantic elements
    infrastructure_elements: List[InfrastructureElement] = Field(default=[], description="Infrastructure identified")
    boundary_elements: List[BoundaryElement] = Field(default=[], description="Property boundaries identified")
    environmental_elements: List[EnvironmentalElement] = Field(default=[], description="Environmental features")
    building_elements: List[BuildingElement] = Field(default=[], description="Buildings and structures")
    other_elements: List[SemanticElement] = Field(default=[], description="Other significant elements")
    
    # Textual content
    textual_information: List[TextualInformation] = Field(default=[], description="All text found in image")
    
    # Spatial analysis
    spatial_relationships: List[SpatialRelationship] = Field(default=[], description="Relationships between elements")
    
    # Risk analysis
    risk_indicators: List[RiskIndicator] = Field(default=[], description="Potential risks identified")
    
    # Overall assessment
    semantic_summary: str = Field(..., description="High-level summary of what the image shows")
    property_impact_summary: str = Field(..., description="How this image impacts property understanding")
    key_findings: List[str] = Field(default=[], description="Most important findings from this image")
    areas_of_concern: List[str] = Field(default=[], description="Areas requiring attention or investigation")
    
    # Analysis metadata
    analysis_confidence: ConfidenceLevel = Field(..., description="Overall confidence in analysis")
    processing_notes: List[str] = Field(default=[], description="Notes about analysis process")
    suggested_followup: List[str] = Field(default=[], description="Suggested follow-up actions")
    
    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True
    }

# Helper functions for semantic analysis
class SemanticAnalyzer:
    """Helper class for semantic analysis operations"""
    
    @staticmethod
    def create_element_id(element_type: str, index: int) -> str:
        """Create unique ID for semantic elements"""
        return f"{element_type.lower()}_{index:03d}"
    
    @staticmethod
    def calculate_risk_priority(risk_indicators: List[RiskIndicator]) -> str:
        """Calculate overall risk priority from identified risks"""
        if not risk_indicators:
            return "low"
        
        critical_count = sum(1 for r in risk_indicators if r.severity == "critical")
        high_count = sum(1 for r in risk_indicators if r.severity == "high")
        
        if critical_count > 0:
            return "critical"
        elif high_count >= 2:
            return "high"
        elif high_count > 0:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def create_example_sewer_analysis() -> ImageSemantics:
        """Create example analysis for sewer diagram"""
        
        # Example infrastructure element - sewer pipe
        sewer_pipe = InfrastructureElement(
            element_type="sewer_pipe",
            description="Main sewer line running east-west under property",
            location=LocationReference(
                x_coordinate=0.2,
                y_coordinate=0.6,
                width=0.6,
                height=0.05,
                description="Running from eastern boundary to western boundary",
                landmarks=["Eastern boundary", "Western boundary"]
            ),
            properties={
                "material": "concrete",
                "condition": "good",
                "age_estimate": "20-30 years"
            },
            confidence=ConfidenceLevel.HIGH,
            risk_relevance="High - impacts building envelope and construction",
            infrastructure_type="sewer_main",
            pipe_diameter="225mm",
            depth="1.5m below surface",
            material="concrete",
            ownership="council",
            maintenance_access="3m clear access zone required"
        )
        
        # Example risk indicator
        construction_risk = RiskIndicator(
            risk_type="Construction Impact",
            severity="medium",
            description="Sewer main location may restrict building placement and require special construction methods",
            evidence_elements=["sewer_pipe_001"],
            location_description="Central portion of property, running east-west",
            recommended_action="Consult with structural engineer for foundation design around sewer main"
        )
        
        return ImageSemantics(
            image_type=ImageType.SEWER_SERVICE_DIAGRAM,
            image_title="Sewer Service Connection Plan",
            scale_information="1:500",
            infrastructure_elements=[sewer_pipe],
            risk_indicators=[construction_risk],
            semantic_summary="Sewer service diagram showing main sewer line running under property from east to west",
            property_impact_summary="Sewer main placement significantly impacts building envelope and foundation design options",
            key_findings=[
                "225mm concrete sewer main crosses property",
                "3m access zone required for maintenance",
                "May impact foundation design and building placement"
            ],
            areas_of_concern=[
                "Building envelope restrictions due to sewer easement",
                "Foundation design requirements around sewer main"
            ],
            analysis_confidence=ConfidenceLevel.HIGH,
            suggested_followup=[
                "Consult structural engineer regarding foundation design",
                "Verify exact easement boundaries with council",
                "Check building permit requirements for construction over sewer"
            ]
        )