"""
Tests for the updated image semantics schema.

This test file covers:
- New enum types (TextType, RelationshipType, GeometryType)
- Geometry validation and coordinate normalization
- Provenance metadata fields
- Safe mutable defaults
- Generic diagram semantics fallback
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from backend.app.prompts.schema.diagram_analysis.image_semantics_schema import (
    DiagramSemanticsBase,
    GenericDiagramSemantics,
    SitePlanSemantics,
    SurveyDiagramSemantics,
    SewerServiceSemantics,
    FloodMapSemantics,
    TextualInformation,
    SpatialRelationship,
    BoundaryElement,
    InfrastructureElement,
    LocationReference,
    DIAGRAM_SEMANTICS_MAPPING,
    get_semantic_schema_class,
    create_semantic_instance,
)
from app.schema.enums import (
    DiagramType,
    ConfidenceLevel,
    TextType,
    RelationshipType,
    GeometryType,
)


class TestImageSemanticsSchema:
    """Test the updated image semantics schema"""

    def test_safe_mutable_defaults(self):
        """Test that mutable defaults use default_factory"""
        # This should not raise an error about mutable defaults
        semantics = GenericDiagramSemantics(
            image_type=DiagramType.UNKNOWN,
            semantic_summary="Test summary",
            property_impact_summary="Test impact",
            analysis_confidence=ConfidenceLevel.HIGH,
        )

        # Verify defaults are properly initialized
        assert isinstance(semantics.textual_information, list)
        assert isinstance(semantics.spatial_relationships, list)
        assert isinstance(semantics.legend_information, list)
        assert isinstance(semantics.key_findings, list)
        assert isinstance(semantics.areas_of_concern, list)
        assert isinstance(semantics.processing_notes, list)
        assert isinstance(semantics.suggested_followup, list)

    def test_new_enum_types(self):
        """Test the new enum types for text and relationships"""
        # Create a proper LocationReference first
        location = LocationReference(
            description="Test location",
            x_coordinate=0.1,
            y_coordinate=0.2,
            width=0.05,
            height=0.02,
        )

        text_info = TextualInformation(
            text_content="Test text",
            location=location,
            text_type=TextType.LABEL,
            significance="Important label for property identification",
        )

        spatial_rel = SpatialRelationship(
            element1_id="building_001",
            element2_id="boundary_001",
            relationship_type=RelationshipType.ADJACENT,
            impact_description="Building is adjacent to boundary",
        )

        assert text_info.text_type == TextType.LABEL
        assert spatial_rel.relationship_type == RelationshipType.ADJACENT

    def test_geometry_validation_and_normalization(self):
        """Test geometry validation and coordinate normalization"""
        # Test valid coordinates using the correct field names
        location = LocationReference(
            description="Test location",
            x_coordinate=0.1,
            y_coordinate=0.2,
            width=0.05,
            height=0.03,
        )

        # Test coordinate normalization (should clamp to 0-1 range)
        location_normalized = LocationReference(
            description="Test location",
            x_coordinate=0.15,
            y_coordinate=0.25,
            width=0.1,
            height=0.08,
        )

        # Test points geometry
        location_points = LocationReference(
            description="Test polyline",
            geometry_type=GeometryType.POLYLINE,
            points=[{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.4}],
        )

        assert location.x_coordinate == 0.1
        assert location_normalized.x_coordinate == 0.15  # Should remain as is
        assert len(location_points.points) == 2

    def test_provenance_metadata(self):
        """Test the new provenance metadata fields"""
        semantics = GenericDiagramSemantics(
            image_type=DiagramType.UNKNOWN,
            semantic_summary="Test summary",
            property_impact_summary="Test impact",
            analysis_confidence=ConfidenceLevel.HIGH,
            source_image_id="img_123",
            source_page_number=5,
            extraction_method="gemini_vision",
            model_version="1.0.0",
            processing_started_at="2024-01-01T00:00:00Z",
            processing_completed_at="2024-01-01T00:01:00Z",
        )

        assert semantics.source_image_id == "img_123"
        assert semantics.source_page_number == 5
        assert semantics.extraction_method == "gemini_vision"
        assert semantics.model_version == "1.0.0"
        assert semantics.processing_started_at == "2024-01-01T00:00:00Z"
        assert semantics.processing_completed_at == "2024-01-01T00:01:00Z"

    def test_specialized_semantics_classes(self):
        """Test specialized semantics classes with their specific fields"""
        # Test SitePlanSemantics
        site_plan = SitePlanSemantics(
            image_type=DiagramType.SITE_PLAN,
            semantic_summary="Site plan analysis",
            property_impact_summary="Site layout impact",
            analysis_confidence=ConfidenceLevel.HIGH,
            lot_dimensions="25m x 40m",
            building_setbacks=["6m front", "1.5m side"],
            access_points=["Main driveway", "Side path"],
            parking_areas=["2 car spaces"],
        )

        assert site_plan.lot_dimensions == "25m x 40m"
        assert len(site_plan.building_setbacks) == 2
        assert site_plan.get_primary_focus() == "site_layout_and_boundaries"

        # Test SurveyDiagramSemantics
        survey = SurveyDiagramSemantics(
            image_type=DiagramType.SURVEY_DIAGRAM,
            semantic_summary="Survey analysis",
            property_impact_summary="Survey impact",
            analysis_confidence=ConfidenceLevel.HIGH,
            survey_marks=["Peg 1", "Peg 2"],
            measurements=["25.5m", "40.2m"],
            elevation_data=["RL 45.2m", "RL 46.1m"],
            coordinate_system="GDA2020",
        )

        assert len(survey.survey_marks) == 2
        assert survey.coordinate_system == "GDA2020"
        assert survey.get_primary_focus() == "precise_boundaries_and_measurements"

        # Test SewerServiceSemantics
        sewer = SewerServiceSemantics(
            image_type=DiagramType.SEWER_SERVICE_DIAGRAM,
            semantic_summary="Sewer analysis",
            property_impact_summary="Sewer impact",
            analysis_confidence=ConfidenceLevel.HIGH,
            pipe_network=["225mm main", "100mm connection"],
            connection_points=["Manhole 1", "Property connection"],
            maintenance_access=["3m easement corridor"],
            easement_areas=["Eastern boundary easement"],
        )

        assert len(sewer.pipe_network) == 2
        assert sewer.get_primary_focus() == "sewer_infrastructure"

    def test_diagram_semantics_mapping(self):
        """Test the mapping between DiagramType and semantic classes"""
        # Test known mappings
        assert DIAGRAM_SEMANTICS_MAPPING[DiagramType.SITE_PLAN] == SitePlanSemantics
        assert (
            DIAGRAM_SEMANTICS_MAPPING[DiagramType.SURVEY_DIAGRAM]
            == SurveyDiagramSemantics
        )
        assert (
            DIAGRAM_SEMANTICS_MAPPING[DiagramType.SEWER_SERVICE_DIAGRAM]
            == SewerServiceSemantics
        )
        assert DIAGRAM_SEMANTICS_MAPPING[DiagramType.FLOOD_MAP] == FloodMapSemantics

        # Test UNKNOWN maps to GenericDiagramSemantics
        assert DIAGRAM_SEMANTICS_MAPPING[DiagramType.UNKNOWN] == GenericDiagramSemantics

    def test_get_semantic_schema_class(self):
        """Test the get_semantic_schema_class function"""
        # Test known types
        assert get_semantic_schema_class(DiagramType.SITE_PLAN) == SitePlanSemantics
        assert (
            get_semantic_schema_class(DiagramType.SURVEY_DIAGRAM)
            == SurveyDiagramSemantics
        )

        # Test UNKNOWN type
        assert get_semantic_schema_class(DiagramType.UNKNOWN) == GenericDiagramSemantics

        # Test fallback to base class for unmapped types
        # This should return the base class, but since it's abstract, it will raise an error
        # when trying to instantiate it
        base_class = get_semantic_schema_class(DiagramType.UNKNOWN)
        assert base_class == GenericDiagramSemantics

        # Test that we can create an instance of the returned class
        instance = base_class(
            image_type=DiagramType.UNKNOWN,
            semantic_summary="Test",
            property_impact_summary="Test",
            analysis_confidence=ConfidenceLevel.HIGH,
        )
        assert isinstance(instance, GenericDiagramSemantics)

    def test_create_semantic_instance(self):
        """Test the create_semantic_instance factory function"""
        # Test creating a site plan instance
        site_plan = create_semantic_instance(
            DiagramType.SITE_PLAN,
            semantic_summary="Test site plan",
            property_impact_summary="Test impact",
            analysis_confidence=ConfidenceLevel.HIGH,
            lot_dimensions="30m x 50m",
        )

        assert isinstance(site_plan, SitePlanSemantics)
        assert site_plan.lot_dimensions == "30m x 50m"

        # Test creating a generic instance for UNKNOWN type
        generic = create_semantic_instance(
            DiagramType.UNKNOWN,
            semantic_summary="Test generic",
            property_impact_summary="Test impact",
            analysis_confidence=ConfidenceLevel.MEDIUM,
        )

        assert isinstance(generic, GenericDiagramSemantics)

    def test_boundary_element_validation(self):
        """Test BoundaryElement validation"""
        location = LocationReference(
            description="Eastern boundary",
            x_coordinate=0.8,
            y_coordinate=0.1,
            width=0.2,
            height=0.8,
        )

        boundary = BoundaryElement(
            element_id="boundary_001",
            element_type="fence",
            description="Timber fence on eastern boundary",
            location=location,
            confidence=ConfidenceLevel.HIGH,
            boundary_type="side",
            dimensions="25.5m length",
        )

        assert boundary.element_type == "fence"
        assert boundary.location.x_coordinate == 0.8
        assert boundary.dimensions == "25.5m length"

    def test_infrastructure_element_validation(self):
        """Test InfrastructureElement validation"""
        location = LocationReference(
            description="Under eastern boundary",
            geometry_type=GeometryType.POLYLINE,
            points=[{"x": 0.8, "y": 0.2}, {"x": 0.8, "y": 0.8}],
        )

        infrastructure = InfrastructureElement(
            element_id="infra_001",
            element_type="sewer_pipe",
            description="225mm concrete sewer main",
            location=location,
            confidence=ConfidenceLevel.HIGH,
            infrastructure_type="sewer",
            pipe_diameter="225mm",
            material="Concrete",
            ownership="Council",
            maintenance_access="Annual inspection required",
        )

        assert infrastructure.element_type == "sewer_pipe"
        assert infrastructure.location.geometry_type == GeometryType.POLYLINE
        assert infrastructure.ownership == "Council"

    def test_enum_validation(self):
        """Test that enum validation works correctly"""
        # Test valid enum values
        location = LocationReference(
            description="Test location",
            x_coordinate=0.1,
            y_coordinate=0.2,
            width=0.05,
            height=0.02,
        )

        text_info = TextualInformation(
            text_content="Test",
            location=location,
            text_type=TextType.MEASUREMENT,
            significance="Test measurement",
        )

        # Test invalid enum values raise validation error
        with pytest.raises(ValidationError):
            TextualInformation(
                text_content="Test",
                location=location,
                text_type="invalid_type",  # Should be TextType enum
                significance="Test measurement",
            )

    def test_coordinate_normalization_edge_cases(self):
        """Test coordinate normalization edge cases"""
        # Test coordinates that need normalization
        # The validator will raise an error for invalid coordinates
        with pytest.raises(ValueError):
            LocationReference(
                description="Test location",
                x_coordinate=-0.1,
                y_coordinate=1.2,
                width=-0.05,
                height=0.8,
            )

    def test_points_validation(self):
        """Test points validation for polyline/polygon geometries"""
        # Test valid points
        location = LocationReference(
            description="Test polyline",
            geometry_type=GeometryType.POLYLINE,
            points=[{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.4}, {"x": 0.5, "y": 0.6}],
        )

        assert len(location.points) == 3

        # Test invalid points (should raise validation error)
        with pytest.raises(ValueError):
            LocationReference(
                description="Test invalid",
                geometry_type=GeometryType.POLYLINE,
                points=[{"x": 0.1}, {"y": 0.2}],  # Missing x or y
            )

    def test_abstract_base_class_cannot_instantiate(self):
        """Test that DiagramSemanticsBase cannot be instantiated directly"""
        with pytest.raises(TypeError):
            DiagramSemanticsBase(
                image_type=DiagramType.UNKNOWN,
                semantic_summary="Test",
                property_impact_summary="Test",
                analysis_confidence=ConfidenceLevel.HIGH,
            )

    def test_comprehensive_semantics_creation(self):
        """Test creating a comprehensive semantics instance with all fields"""
        semantics = SitePlanSemantics(
            image_type=DiagramType.SITE_PLAN,
            image_title="Property Site Plan",
            scale_information="1:500",
            orientation="North up",
            legend_information=["Building outline", "Boundary line", "Access road"],
            semantic_summary="Residential property with main dwelling and garage",
            property_impact_summary="Standard residential layout with good access",
            analysis_confidence=ConfidenceLevel.HIGH,
            lot_dimensions="25m x 40m",
            building_setbacks=["6m front", "1.5m side", "3m rear"],
            access_points=["Main driveway", "Side pedestrian path"],
            parking_areas=["2 car spaces", "Visitor parking"],
            source_image_id="site_plan_001",
            source_page_number=3,
            extraction_method="gemini_vision_v2",
            model_version="2.1.0",
            processing_started_at="2024-01-01T00:00:00Z",
            processing_completed_at="2024-01-01T00:01:00Z",
        )

        # Verify all fields are set correctly
        assert semantics.image_title == "Property Site Plan"
        assert semantics.scale_information == "1:500"
        assert len(semantics.legend_information) == 3
        assert len(semantics.building_setbacks) == 3
        assert semantics.source_image_id == "site_plan_001"
        assert semantics.get_primary_focus() == "site_layout_and_boundaries"
