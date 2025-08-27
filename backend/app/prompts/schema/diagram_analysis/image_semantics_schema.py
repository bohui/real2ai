from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Type, Union
from abc import ABC, abstractmethod
from app.schema.enums import (
    DiagramType,
    ConfidenceLevel,
    TextType,
    RelationshipType,
    GeometryType,
)


class LocationReference(BaseModel):
    """Spatial location reference within the image"""

    x_coordinate: Optional[float] = Field(
        None, description="X coordinate (0-1 normalized)"
    )
    y_coordinate: Optional[float] = Field(
        None, description="Y coordinate (0-1 normalized)"
    )
    width: Optional[float] = Field(None, description="Width (0-1 normalized)")
    height: Optional[float] = Field(None, description="Height (0-1 normalized)")
    description: str = Field(..., description="Text description of location")
    landmarks: List[str] = Field(
        default_factory=list, description="Nearby landmarks or reference points"
    )
    geometry_type: Optional[GeometryType] = Field(
        None, description="Geometry representation when not a simple bbox"
    )
    points: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="List of points for polyline/polygon with normalized coords",
    )

    @model_validator(mode="after")
    def validate_bbox_normalization(self):
        if self.width is not None or self.height is not None:
            for v in (self.x_coordinate, self.y_coordinate, self.width, self.height):
                if v is None or not (0.0 <= v <= 1.0):
                    raise ValueError("LocationReference bbox values must be in [0,1]")
        if self.geometry_type in {GeometryType.POLYLINE, GeometryType.POLYGON}:
            if not self.points or not isinstance(self.points, list):
                raise ValueError(
                    "points must be provided for polyline/polygon geometry"
                )
            for p in self.points:
                x = p.get("x")
                y = p.get("y")
                if (
                    x is None
                    or y is None
                    or not (0.0 <= x <= 1.0)
                    or not (0.0 <= y <= 1.0)
                ):
                    raise ValueError("points must contain normalized x,y in [0,1]")
        return self


class SemanticElement(BaseModel):
    """Individual semantic element identified in the image"""

    element_id: str = Field(..., description="Unique identifier for this element")
    element_type: str = Field(
        ..., description="Type of element (pipe, building, boundary, etc.)"
    )
    description: str = Field(..., description="Detailed description of the element")
    location: LocationReference = Field(..., description="Location within the image")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional properties (size, material, etc.)"
    )
    confidence: ConfidenceLevel = Field(..., description="Confidence in identification")


class InfrastructureElement(SemanticElement):
    """Infrastructure-specific semantic element"""

    infrastructure_type: str = Field(
        ..., description="Type of infrastructure (sewer, water, gas, power, etc.)"
    )
    pipe_diameter: Optional[str] = Field(
        None, description="Pipe diameter if applicable"
    )
    depth: Optional[str] = Field(None, description="Depth below surface if shown")
    material: Optional[str] = Field(None, description="Material type if visible")
    ownership: Optional[str] = Field(
        None, description="Council/private ownership if indicated"
    )
    maintenance_access: Optional[str] = Field(
        None, description="Access requirements for maintenance"
    )


class BoundaryElement(SemanticElement):
    """Property boundary semantic element"""

    boundary_type: str = Field(
        ..., description="Type of boundary (front, rear, side, common)"
    )
    boundary_marking: Optional[str] = Field(
        None, description="How boundary is marked (fence, survey pegs, etc.)"
    )
    dimensions: Optional[str] = Field(None, description="Boundary dimensions if shown")
    encroachments: List[str] = Field(
        default_factory=list, description="Any encroachments noted"
    )
    easements: List[str] = Field(
        default_factory=list, description="Easements along this boundary"
    )


class EnvironmentalElement(SemanticElement):
    """Environmental feature semantic element"""

    environmental_type: str = Field(..., description="Type of environmental feature")
    risk_level: Optional[str] = Field(
        None, description="Associated risk level if indicated"
    )
    impact_area: Optional[str] = Field(None, description="Area of impact if shown")
    mitigation_measures: List[str] = Field(
        default_factory=list, description="Mitigation measures if noted"
    )


class BuildingElement(SemanticElement):
    """Building or structure semantic element"""

    building_type: str = Field(..., description="Type of building or structure")
    construction_stage: Optional[str] = Field(
        None, description="Construction stage if applicable"
    )
    height_restrictions: Optional[str] = Field(
        None, description="Height restrictions if shown"
    )
    setback_requirements: Optional[str] = Field(
        None, description="Setback requirements if noted"
    )
    building_envelope: Optional[str] = Field(
        None, description="Building envelope constraints"
    )


class TextualInformation(BaseModel):
    """Text found in the image with semantic context"""

    text_content: str = Field(..., description="The extracted text")
    location: LocationReference = Field(..., description="Location of the text")
    text_type: TextType = Field(
        ..., description="Type of text (label, measurement, title, etc.)"
    )
    font_size: Optional[str] = Field(
        None, description="Relative font size (large, medium, small)"
    )
    significance: str = Field(
        ..., description="How significant this text is to property understanding"
    )


class SpatialRelationship(BaseModel):
    """Relationship between different elements in the image"""

    element1_id: str = Field(..., description="ID of first element")
    element2_id: str = Field(..., description="ID of second element")
    relationship_type: RelationshipType = Field(
        ..., description="Type of relationship (adjacent, under, crosses, etc.)"
    )
    distance: Optional[str] = Field(
        None, description="Distance between elements if measurable"
    )
    impact_description: str = Field(
        ..., description="How this relationship impacts property risk"
    )


class DiagramSemanticsBase(BaseModel, ABC):
    """Abstract base class for diagram semantic analysis"""

    # Image metadata (common to all diagrams)
    image_type: DiagramType = Field(..., description="Type of image analyzed")
    image_title: Optional[str] = Field(
        None, description="Title or heading found in image"
    )
    scale_information: Optional[str] = Field(
        None, description="Scale information if present"
    )
    orientation: Optional[str] = Field(
        None, description="Orientation (North arrow, etc.)"
    )
    legend_information: List[str] = Field(
        default_factory=list, description="Legend or key information"
    )

    # Textual content (common to all diagrams)
    textual_information: List[TextualInformation] = Field(
        default_factory=list, description="All text found in image"
    )

    # Spatial analysis (common to all diagrams)
    spatial_relationships: List[SpatialRelationship] = Field(
        default_factory=list, description="Relationships between elements"
    )

    # Overall assessment (common to all diagrams)
    semantic_summary: str = Field(
        ..., description="High-level summary of what the image shows"
    )
    property_impact_summary: str = Field(
        ..., description="How this image impacts property understanding"
    )
    key_findings: List[str] = Field(
        default_factory=list, description="Most important findings from this image"
    )
    areas_of_concern: List[str] = Field(
        default_factory=list, description="Areas requiring attention or investigation"
    )

    # Analysis metadata (common to all diagrams)
    analysis_confidence: ConfidenceLevel = Field(
        ..., description="Overall confidence in analysis"
    )
    processing_notes: List[str] = Field(
        default_factory=list, description="Notes about analysis process"
    )
    suggested_followup: List[str] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )

    # Provenance
    source_image_id: Optional[str] = Field(None, description="Source image identifier")
    source_page_number: Optional[int] = Field(
        None, description="Source page number, if PDF"
    )
    extraction_method: Optional[str] = Field(
        None, description="Extractor used, e.g., gemini-ocr-vX"
    )
    model_version: Optional[str] = Field(
        None, description="Model version used for extraction"
    )
    processing_started_at: Optional[str] = Field(
        None, description="Start timestamp (ISO)"
    )
    processing_completed_at: Optional[str] = Field(
        None, description="Completion timestamp (ISO)"
    )

    model_config = {"use_enum_values": True, "arbitrary_types_allowed": True}

    @abstractmethod
    def get_primary_focus(self) -> str:
        """Get the primary focus area for this diagram type"""
        pass


# Legacy class for backward compatibility
# class DiagramSemantics(DiagramSemanticsBase):
#     """Complete semantic analysis of an image/diagram - legacy implementation"""

#     # Core semantic elements (all types for backward compatibility)
#     infrastructure_elements: List[InfrastructureElement] = Field(
#         default=[], description="Infrastructure identified"
#     )
#     boundary_elements: List[BoundaryElement] = Field(
#         default=[], description="Property boundaries identified"
#     )
#     environmental_elements: List[EnvironmentalElement] = Field(
#         default=[], description="Environmental features"
#     )
#     building_elements: List[BuildingElement] = Field(
#         default=[], description="Buildings and structures"
#     )
#     other_elements: List[SemanticElement] = Field(
#         default=[], description="Other significant elements"
#     )

#     def get_primary_focus(self) -> str:
#         """Get the primary focus area for this diagram type"""
#         return "general_analysis"


# Specialized semantic classes for each diagram type


class SitePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to site plans"""

    # Site plan specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default_factory=list, description="Property boundaries and lot lines"
    )
    building_elements: List[BuildingElement] = Field(
        default_factory=list, description="Buildings and structures on site"
    )
    infrastructure_elements: List[InfrastructureElement] = Field(
        default_factory=list, description="Site infrastructure (driveways, utilities)"
    )

    # Site plan specific fields
    lot_dimensions: Optional[str] = Field(None, description="Overall lot dimensions")
    building_setbacks: List[str] = Field(
        default_factory=list, description="Building setback requirements"
    )
    access_points: List[str] = Field(
        default_factory=list, description="Vehicle and pedestrian access points"
    )
    parking_areas: List[str] = Field(
        default_factory=list, description="Parking and vehicle areas"
    )

    def get_primary_focus(self) -> str:
        return "site_layout_and_boundaries"


class SewerServiceSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to sewer service diagrams"""

    # Sewer specific elements
    infrastructure_elements: List[InfrastructureElement] = Field(
        default_factory=list, description="Sewer pipes, manholes, and connections"
    )

    # Sewer specific fields
    pipe_network: List[str] = Field(
        default_factory=list, description="Sewer pipe network layout"
    )
    connection_points: List[str] = Field(
        default_factory=list, description="Property connection points"
    )
    maintenance_access: List[str] = Field(
        default_factory=list, description="Maintenance access requirements"
    )
    easement_areas: List[str] = Field(
        default_factory=list, description="Sewer easement areas"
    )

    def get_primary_focus(self) -> str:
        return "sewer_infrastructure"


class FloodMapSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to flood maps"""

    # Flood specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Flood zones and water features"
    )

    # Flood specific fields
    flood_zones: List[str] = Field(
        default_factory=list, description="Flood zone classifications"
    )
    water_levels: List[str] = Field(
        default_factory=list, description="Water level indicators"
    )
    escape_routes: List[str] = Field(
        default_factory=list, description="Emergency escape routes"
    )
    flood_mitigation: List[str] = Field(
        default=[], description="Flood mitigation measures"
    )

    def get_primary_focus(self) -> str:
        return "flood_risk_assessment"


class SurveyDiagramSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to survey diagrams"""

    # Survey specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default_factory=list, description="Surveyed property boundaries"
    )

    # Survey specific fields
    survey_marks: List[str] = Field(
        default_factory=list, description="Survey marks and reference points"
    )
    measurements: List[str] = Field(
        default_factory=list, description="Precise measurements and distances"
    )
    elevation_data: List[str] = Field(
        default_factory=list, description="Elevation and contour information"
    )
    coordinate_system: Optional[str] = Field(None, description="Coordinate system used")

    def get_primary_focus(self) -> str:
        return "precise_boundaries_and_measurements"


class TitlePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to title plans"""

    # Title plan specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default_factory=list, description="Legal property boundaries"
    )

    # Title plan specific fields
    lot_numbers: List[str] = Field(
        default_factory=list, description="Lot identification numbers"
    )
    plan_numbers: List[str] = Field(
        default_factory=list, description="Plan registration numbers"
    )
    easements: List[str] = Field(
        default_factory=list, description="Easements and restrictions"
    )
    owners_details: List[str] = Field(
        default_factory=list, description="Ownership information"
    )

    def get_primary_focus(self) -> str:
        return "legal_boundaries_and_ownership"


class ZoningMapSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to zoning maps"""

    # Zoning specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Zoning areas and overlays"
    )

    # Zoning specific fields
    zoning_classifications: List[str] = Field(
        default_factory=list, description="Zoning categories"
    )
    development_controls: List[str] = Field(
        default_factory=list, description="Development control areas"
    )
    height_restrictions: List[str] = Field(
        default_factory=list, description="Height limit zones"
    )
    land_use_permissions: List[str] = Field(
        default_factory=list, description="Permitted land uses"
    )

    def get_primary_focus(self) -> str:
        return "zoning_and_development_controls"


class EnvironmentalOverlaySemantics(DiagramSemanticsBase):
    """Semantic analysis specific to environmental overlays"""

    # Environmental specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Environmental features and restrictions"
    )

    # Environmental specific fields
    overlay_zones: List[str] = Field(
        default_factory=list, description="Environmental overlay zones"
    )
    protected_areas: List[str] = Field(
        default_factory=list, description="Protected environmental areas"
    )
    development_restrictions: List[str] = Field(
        default_factory=list, description="Environmental development restrictions"
    )
    vegetation_controls: List[str] = Field(
        default_factory=list, description="Vegetation protection controls"
    )

    def get_primary_focus(self) -> str:
        return "environmental_protection_and_restrictions"


class BushfireMapSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to bushfire maps"""

    # Bushfire specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Bushfire zones and vegetation areas"
    )

    # Bushfire specific fields
    bushfire_zones: List[str] = Field(
        default_factory=list, description="Bushfire attack level zones (BAL ratings)"
    )
    vegetation_types: List[str] = Field(
        default_factory=list, description="Vegetation classifications and fuel loads"
    )
    defensible_space: List[str] = Field(
        default_factory=list, description="Required defensible space zones"
    )
    evacuation_routes: List[str] = Field(
        default_factory=list, description="Emergency evacuation routes"
    )
    construction_requirements: List[str] = Field(
        default_factory=list,
        description="Special construction requirements for bushfire",
    )

    def get_primary_focus(self) -> str:
        return "bushfire_risk_assessment"


class ContourMapSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to contour maps"""

    # Contour specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Topographical features and elevation changes"
    )

    # Contour specific fields
    elevation_ranges: List[str] = Field(
        default_factory=list, description="Elevation ranges across the property"
    )
    contour_intervals: Optional[str] = Field(
        None, description="Contour line intervals (e.g., 1m, 2m)"
    )
    slope_analysis: List[str] = Field(
        default_factory=list, description="Slope gradients and stability assessment"
    )
    drainage_patterns: List[str] = Field(
        default_factory=list, description="Natural drainage flow patterns"
    )
    cut_fill_requirements: List[str] = Field(
        default_factory=list,
        description="Potential cut and fill requirements for development",
    )

    def get_primary_focus(self) -> str:
        return "topography_and_elevation"


class DrainagePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to drainage plans"""

    # Drainage specific elements
    infrastructure_elements: List[InfrastructureElement] = Field(
        default_factory=list, description="Drainage infrastructure and systems"
    )

    # Drainage specific fields
    drainage_network: List[str] = Field(
        default_factory=list, description="Stormwater drainage network layout"
    )
    catchment_areas: List[str] = Field(
        default_factory=list, description="Water catchment and collection areas"
    )
    outfall_points: List[str] = Field(
        default_factory=list, description="Drainage outfall and discharge points"
    )
    retention_systems: List[str] = Field(
        default_factory=list, description="Water retention and detention systems"
    )
    pipe_capacities: List[str] = Field(
        default_factory=list, description="Drainage pipe sizes and capacities"
    )

    def get_primary_focus(self) -> str:
        return "stormwater_management"


class UtilityPlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to utility plans"""

    # Utility specific elements
    infrastructure_elements: List[InfrastructureElement] = Field(
        default_factory=list,
        description="Utility infrastructure (power, gas, water, telecoms)",
    )

    # Utility specific fields
    utility_types: List[str] = Field(
        default_factory=list,
        description="Types of utilities present (power, gas, water, telecoms)",
    )
    service_connections: List[str] = Field(
        default_factory=list, description="Utility service connection points"
    )
    easement_corridors: List[str] = Field(
        default_factory=list, description="Utility easement corridors and restrictions"
    )
    meter_locations: List[str] = Field(
        default_factory=list, description="Utility meter and equipment locations"
    )
    capacity_information: List[str] = Field(
        default_factory=list, description="Utility capacity and load information"
    )

    def get_primary_focus(self) -> str:
        return "utility_infrastructure"


class BuildingEnvelopePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to building envelope plans"""

    # Building envelope specific elements
    building_elements: List[BuildingElement] = Field(
        default_factory=list,
        description="Building envelope constraints and allowable areas",
    )
    boundary_elements: List[BoundaryElement] = Field(
        default_factory=list,
        description="Property boundaries affecting building envelope",
    )

    # Building envelope specific fields
    setback_requirements: List[str] = Field(
        default_factory=list, description="Required setbacks from all boundaries"
    )
    height_limits: List[str] = Field(
        default_factory=list, description="Maximum building height restrictions"
    )
    floor_area_ratio: Optional[str] = Field(
        None, description="Floor area ratio limitations"
    )
    coverage_limits: Optional[str] = Field(
        None, description="Site coverage percentage limits"
    )
    buildable_area: Optional[str] = Field(
        None, description="Total buildable area dimensions"
    )

    def get_primary_focus(self) -> str:
        return "development_constraints"


class StrataPlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to strata plans"""

    # Strata specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default_factory=list, description="Strata lot boundaries and common areas"
    )
    building_elements: List[BuildingElement] = Field(
        default_factory=list,
        description="Buildings and structures within strata scheme",
    )

    # Strata specific fields
    lot_entitlements: List[str] = Field(
        default_factory=list, description="Unit entitlements and ownership percentages"
    )
    common_areas: List[str] = Field(
        default_factory=list, description="Common property areas and facilities"
    )
    exclusive_use_areas: List[str] = Field(
        default_factory=list, description="Exclusive use areas allocated to lots"
    )
    strata_restrictions: List[str] = Field(
        default_factory=list, description="Strata scheme restrictions and bylaws"
    )
    management_areas: List[str] = Field(
        default_factory=list, description="Areas under strata management control"
    )

    def get_primary_focus(self) -> str:
        return "strata_ownership_structure"


class LandscapePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to landscape plans"""

    # Landscape specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default_factory=list, description="Vegetation and landscape features"
    )

    # Landscape specific fields
    vegetation_zones: List[str] = Field(
        default_factory=list, description="Existing and proposed vegetation zones"
    )
    tree_preservation: List[str] = Field(
        default_factory=list, description="Trees to be preserved or protected"
    )
    planting_requirements: List[str] = Field(
        default_factory=list, description="Required landscaping and planting"
    )
    irrigation_systems: List[str] = Field(
        default_factory=list, description="Irrigation and water management systems"
    )
    hardscape_elements: List[str] = Field(
        default_factory=list, description="Paved areas, retaining walls, and structures"
    )

    def get_primary_focus(self) -> str:
        return "landscape_requirements"


class ParkingPlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to parking plans"""

    # Parking specific elements
    infrastructure_elements: List[InfrastructureElement] = Field(
        default_factory=list, description="Parking areas and vehicle circulation"
    )

    # Parking specific fields
    parking_spaces: List[str] = Field(
        default_factory=list, description="Number and types of parking spaces"
    )
    access_arrangements: List[str] = Field(
        default_factory=list, description="Vehicle access and circulation routes"
    )
    disabled_access: List[str] = Field(
        default_factory=list, description="Disabled parking and access provisions"
    )
    visitor_parking: List[str] = Field(
        default_factory=list, description="Visitor parking arrangements"
    )
    loading_areas: List[str] = Field(
        default_factory=list, description="Loading and service vehicle areas"
    )

    def get_primary_focus(self) -> str:
        return "parking_and_access"


class BodyCorporatePlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to body corporate plans"""

    # Body corporate specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default=[], description="Body corporate boundaries and common areas"
    )
    building_elements: List[BuildingElement] = Field(
        default=[], description="Buildings under body corporate control"
    )

    # Body corporate specific fields
    management_areas: List[str] = Field(
        default=[], description="Areas under body corporate management"
    )
    maintenance_responsibilities: List[str] = Field(
        default=[], description="Maintenance responsibility allocations"
    )
    common_facilities: List[str] = Field(
        default=[], description="Shared facilities and amenities"
    )
    levies_structure: List[str] = Field(
        default=[], description="Body corporate levy structure information"
    )
    restrictions: List[str] = Field(
        default=[], description="Body corporate restrictions and rules"
    )

    def get_primary_focus(self) -> str:
        return "body_corporate_management"


class DevelopmentPlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to development plans"""

    # Development specific elements
    building_elements: List[BuildingElement] = Field(
        default=[], description="Proposed development buildings and structures"
    )
    boundary_elements: List[BoundaryElement] = Field(
        default=[], description="Development site boundaries"
    )
    infrastructure_elements: List[InfrastructureElement] = Field(
        default=[], description="Infrastructure for development"
    )

    # Development specific fields
    development_stages: List[str] = Field(
        default=[], description="Development staging and timeline"
    )
    density_requirements: List[str] = Field(
        default=[], description="Density and dwelling yield requirements"
    )
    open_space_provision: List[str] = Field(
        default=[], description="Public and private open space provisions"
    )
    infrastructure_contributions: List[str] = Field(
        default=[], description="Required infrastructure contributions"
    )
    affordable_housing: List[str] = Field(
        default=[], description="Affordable housing requirements"
    )

    def get_primary_focus(self) -> str:
        return "development_requirements"


class SubdivisionPlanSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to subdivision plans"""

    # Subdivision specific elements
    boundary_elements: List[BoundaryElement] = Field(
        default=[], description="Subdivision lot boundaries and layout"
    )
    infrastructure_elements: List[InfrastructureElement] = Field(
        default=[], description="Subdivision infrastructure requirements"
    )

    # Subdivision specific fields
    lot_layout: List[str] = Field(
        default=[], description="Subdivision lot sizes and configuration"
    )
    road_dedications: List[str] = Field(
        default=[], description="Roads to be dedicated to council"
    )
    easement_dedications: List[str] = Field(
        default=[], description="Easements to be created or dedicated"
    )
    infrastructure_works: List[str] = Field(
        default=[], description="Required infrastructure construction"
    )
    approval_conditions: List[str] = Field(
        default=[], description="Subdivision approval conditions"
    )

    def get_primary_focus(self) -> str:
        return "subdivision_layout"


class OffThePlanMarketingSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to off-the-plan marketing materials"""

    # Marketing specific elements
    building_elements: List[BuildingElement] = Field(
        default=[], description="Proposed buildings and developments"
    )

    # Marketing specific fields
    unit_types: List[str] = Field(
        default=[], description="Types and sizes of units/dwellings"
    )
    amenities: List[str] = Field(
        default=[], description="Proposed amenities and facilities"
    )
    completion_timeline: Optional[str] = Field(
        None, description="Expected completion dates"
    )
    pricing_information: List[str] = Field(
        default=[], description="Pricing ranges or guides"
    )
    marketing_features: List[str] = Field(
        default=[], description="Key marketing features highlighted"
    )

    def get_primary_focus(self) -> str:
        return "marketing_information"


class HeritageOverlaySemantics(DiagramSemanticsBase):
    """Semantic analysis specific to heritage overlays"""

    # Heritage specific elements
    environmental_elements: List[EnvironmentalElement] = Field(
        default=[], description="Heritage areas and protected features"
    )
    building_elements: List[BuildingElement] = Field(
        default=[], description="Heritage buildings and structures"
    )

    # Heritage specific fields
    heritage_significance: List[str] = Field(
        default=[], description="Heritage significance categories and ratings"
    )
    protection_requirements: List[str] = Field(
        default=[], description="Heritage protection requirements"
    )
    development_controls: List[str] = Field(
        default=[], description="Heritage development controls and restrictions"
    )
    conservation_areas: List[str] = Field(
        default=[], description="Heritage conservation areas"
    )
    permit_requirements: List[str] = Field(
        default=[], description="Heritage permit requirements for works"
    )

    def get_primary_focus(self) -> str:
        return "heritage_protection"


class AerialViewSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to aerial view images"""

    # Aerial view specific elements
    building_elements: List[BuildingElement] = Field(
        default=[], description="Buildings and structures visible from above"
    )
    environmental_elements: List[EnvironmentalElement] = Field(
        default=[], description="Landscape and environmental features"
    )
    infrastructure_elements: List[InfrastructureElement] = Field(
        default=[], description="Infrastructure visible from aerial perspective"
    )

    # Aerial view specific fields
    site_context: List[str] = Field(
        default=[], description="Surrounding area context and land uses"
    )
    access_visibility: List[str] = Field(
        default=[], description="Visible access routes and connections"
    )
    neighboring_developments: List[str] = Field(
        default=[], description="Adjacent developments and their characteristics"
    )
    natural_features: List[str] = Field(
        default=[], description="Natural features and vegetation patterns"
    )
    urban_fabric: List[str] = Field(
        default=[], description="Urban development patterns and density"
    )

    def get_primary_focus(self) -> str:
        return "contextual_analysis"


class CrossSectionSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to cross-section diagrams"""

    # Cross section specific elements
    building_elements: List[BuildingElement] = Field(
        default=[], description="Building elements shown in cross-section"
    )
    environmental_elements: List[EnvironmentalElement] = Field(
        default=[], description="Ground conditions and environmental layers"
    )

    # Cross section specific fields
    elevation_profile: List[str] = Field(
        default=[], description="Elevation changes along the section line"
    )
    subsurface_conditions: List[str] = Field(
        default=[], description="Subsurface conditions and soil layers"
    )
    structural_elements: List[str] = Field(
        default=[], description="Structural elements and construction details"
    )
    vertical_relationships: List[str] = Field(
        default=[], description="Vertical relationships between elements"
    )
    construction_challenges: List[str] = Field(
        default=[], description="Construction challenges revealed by section"
    )

    def get_primary_focus(self) -> str:
        return "vertical_analysis"


class ElevationViewSemantics(DiagramSemanticsBase):
    """Semantic analysis specific to elevation view diagrams"""

    # Elevation view specific elements
    building_elements: List[BuildingElement] = Field(
        default=[], description="Building facades and external features"
    )

    # Elevation view specific fields
    facade_treatments: List[str] = Field(
        default=[], description="Building facade materials and treatments"
    )
    height_relationships: List[str] = Field(
        default=[], description="Height relationships to surroundings"
    )
    architectural_features: List[str] = Field(
        default=[], description="Significant architectural features"
    )
    material_specifications: List[str] = Field(
        default=[], description="External material specifications"
    )
    visual_impact: List[str] = Field(
        default=[], description="Visual impact on streetscape and neighbors"
    )

    def get_primary_focus(self) -> str:
        return "architectural_appearance"


class GenericDiagramSemantics(DiagramSemanticsBase):
    """Concrete generic schema for unknown or unsupported diagram types."""

    def get_primary_focus(self) -> str:
        return "general_analysis"


# Add more specialized classes as needed...

# Mapping between DiagramType and semantic schema classes
DIAGRAM_SEMANTICS_MAPPING: Dict[DiagramType, Type[DiagramSemanticsBase]] = {
    # Common types
    DiagramType.SITE_PLAN: SitePlanSemantics,
    DiagramType.SURVEY_DIAGRAM: SurveyDiagramSemantics,
    DiagramType.SEWER_SERVICE_DIAGRAM: SewerServiceSemantics,
    DiagramType.FLOOD_MAP: FloodMapSemantics,
    DiagramType.BUSHFIRE_MAP: BushfireMapSemantics,
    DiagramType.ZONING_MAP: ZoningMapSemantics,
    DiagramType.ENVIRONMENTAL_OVERLAY: EnvironmentalOverlaySemantics,
    DiagramType.CONTOUR_MAP: ContourMapSemantics,
    DiagramType.DRAINAGE_PLAN: DrainagePlanSemantics,
    DiagramType.UTILITY_PLAN: UtilityPlanSemantics,
    DiagramType.BUILDING_ENVELOPE_PLAN: BuildingEnvelopePlanSemantics,
    DiagramType.STRATA_PLAN: StrataPlanSemantics,
    DiagramType.LANDSCAPE_PLAN: LandscapePlanSemantics,
    DiagramType.PARKING_PLAN: ParkingPlanSemantics,
    # Diagram-specific types
    DiagramType.TITLE_PLAN: TitlePlanSemantics,
    DiagramType.BODY_CORPORATE_PLAN: BodyCorporatePlanSemantics,
    DiagramType.DEVELOPMENT_PLAN: DevelopmentPlanSemantics,
    DiagramType.SUBDIVISION_PLAN: SubdivisionPlanSemantics,
    DiagramType.OFF_THE_PLAN_MARKETING: OffThePlanMarketingSemantics,
    DiagramType.HERITAGE_OVERLAY: HeritageOverlaySemantics,
    # Image-specific types
    DiagramType.AERIAL_VIEW: AerialViewSemantics,
    DiagramType.CROSS_SECTION: CrossSectionSemantics,
    DiagramType.ELEVATION_VIEW: ElevationViewSemantics,
    # UNKNOWN maps to a generic concrete schema to avoid abstract base
    # It will carry general fields without specialized elements
    DiagramType.UNKNOWN: GenericDiagramSemantics,
}


def get_semantic_schema_class(diagram_type: DiagramType) -> Type[DiagramSemanticsBase]:
    """Get the appropriate semantic schema class for a diagram type"""
    return DIAGRAM_SEMANTICS_MAPPING.get(diagram_type, DiagramSemanticsBase)


def create_semantic_instance(
    diagram_type: DiagramType, **kwargs
) -> DiagramSemanticsBase:
    """Factory function to create the appropriate semantic instance"""
    schema_class = get_semantic_schema_class(diagram_type)

    # Ensure image_type is set
    if "image_type" not in kwargs:
        kwargs["image_type"] = diagram_type

    return schema_class(**kwargs)


# Type alias for all semantic schemas
SemanticSchema = Union[
    DiagramSemanticsBase,
    SitePlanSemantics,
    SewerServiceSemantics,
    FloodMapSemantics,
    SurveyDiagramSemantics,
    TitlePlanSemantics,
    ZoningMapSemantics,
    EnvironmentalOverlaySemantics,
    BushfireMapSemantics,
    ContourMapSemantics,
    DrainagePlanSemantics,
    UtilityPlanSemantics,
    BuildingEnvelopePlanSemantics,
    StrataPlanSemantics,
    LandscapePlanSemantics,
    ParkingPlanSemantics,
    BodyCorporatePlanSemantics,
    DevelopmentPlanSemantics,
    SubdivisionPlanSemantics,
    OffThePlanMarketingSemantics,
    HeritageOverlaySemantics,
    AerialViewSemantics,
    CrossSectionSemantics,
    ElevationViewSemantics,
]


# Helper functions for semantic analysis
class SemanticAnalyzer:
    """Helper class for semantic analysis operations"""

    @staticmethod
    def create_element_id(element_type: str, index: int) -> str:
        """Create unique ID for semantic elements"""
        return f"{element_type.lower()}_{index:03d}"

    # Risk prioritization moved to risk assessment phase; no longer calculated here.

    @staticmethod
    def create_example_sewer_analysis() -> SewerServiceSemantics:
        """Create example analysis for sewer diagram using specialized semantic class"""

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
                landmarks=["Eastern boundary", "Western boundary"],
            ),
            properties={
                "material": "concrete",
                "condition": "good",
                "age_estimate": "20-30 years",
            },
            confidence=ConfidenceLevel.HIGH,
            infrastructure_type="sewer_main",
            pipe_diameter="225mm",
            depth="1.5m below surface",
            material="concrete",
            ownership="council",
            maintenance_access="3m clear access zone required",
        )

        return SewerServiceSemantics(
            image_type=DiagramType.SEWER_SERVICE_DIAGRAM,
            image_title="Sewer Service Connection Plan",
            scale_information="1:500",
            infrastructure_elements=[sewer_pipe],
            pipe_network=[
                "Main sewer line east-west",
                "Property connection north side",
            ],
            connection_points=[
                "Property boundary connection at 15m from eastern boundary"
            ],
            maintenance_access=["3m clear access zone along pipe route"],
            easement_areas=[
                "3m wide easement running east-west through center of property"
            ],
            semantic_summary="Sewer service diagram showing main sewer line running under property from east to west",
            property_impact_summary="Sewer main placement significantly impacts building envelope and foundation design options",
            key_findings=[
                "225mm concrete sewer main crosses property",
                "3m access zone required for maintenance",
                "May impact foundation design and building placement",
            ],
            areas_of_concern=[
                "Building envelope restrictions due to sewer easement",
                "Foundation design requirements around sewer main",
            ],
            analysis_confidence=ConfidenceLevel.HIGH,
            suggested_followup=[
                "Consult structural engineer regarding foundation design",
                "Verify exact easement boundaries with council",
                "Check building permit requirements for construction over sewer",
            ],
        )

    @staticmethod
    def create_example_using_factory(diagram_type: DiagramType) -> DiagramSemanticsBase:
        """Example of using the factory function to create appropriate semantic instance"""
        return create_semantic_instance(
            diagram_type=diagram_type,
            semantic_summary=f"Example analysis for {diagram_type.value}",
            property_impact_summary=f"Impact assessment for {diagram_type.value}",
            analysis_confidence=ConfidenceLevel.MEDIUM,
        )
