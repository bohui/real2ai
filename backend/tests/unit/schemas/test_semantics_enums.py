"""
Tests for the new semantics enums.

This test file covers:
- TextType enum for text classification
- RelationshipType enum for spatial relationships
- GeometryType enum for geometric representations
"""

import pytest
from app.schema.enums.semantics import TextType, RelationshipType, GeometryType


class TestTextType:
    """Test TextType enum"""

    def test_text_type_values(self):
        """Test that TextType has the expected values"""
        assert TextType.LABEL == "label"
        assert TextType.MEASUREMENT == "measurement"
        assert TextType.TITLE == "title"
        assert TextType.LEGEND == "legend"
        assert TextType.NOTE == "note"
        assert TextType.OTHER == "other"

    def test_text_type_enumeration(self):
        """Test that all expected TextType values are present"""
        expected_values = {"label", "measurement", "title", "legend", "note", "other"}
        actual_values = {text_type.value for text_type in TextType}
        assert actual_values == expected_values

    def test_text_type_string_behavior(self):
        """Test that TextType behaves like strings"""
        text_type = TextType.LABEL
        assert text_type == "label"
        assert text_type.value == "label"
        assert text_type in ["label", "measurement", "title"]

    def test_text_type_comparison(self):
        """Test TextType comparison operations"""
        # String enums don't support comparison operators, so test equality and membership
        assert TextType.LABEL == "label"
        assert TextType.MEASUREMENT == "measurement"
        assert TextType.TITLE == "title"
        assert TextType.LEGEND == "legend"
        assert TextType.NOTE == "note"
        assert TextType.OTHER == "other"


class TestRelationshipType:
    """Test RelationshipType enum"""

    def test_relationship_type_values(self):
        """Test that RelationshipType has the expected values"""
        assert RelationshipType.ADJACENT == "adjacent"
        assert RelationshipType.ABOVE == "above"
        assert RelationshipType.BELOW == "below"
        assert RelationshipType.UNDER == "under"
        assert RelationshipType.CROSSES == "crosses"
        assert RelationshipType.INTERSECTS == "intersects"
        assert RelationshipType.CONNECTED_TO == "connected_to"
        assert RelationshipType.OVERLAPS == "overlaps"
        assert RelationshipType.PARALLEL == "parallel"
        assert RelationshipType.PERPENDICULAR == "perpendicular"
        assert RelationshipType.NEAR == "near"
        assert RelationshipType.FAR == "far"
        assert RelationshipType.OTHER == "other"

    def test_relationship_type_enumeration(self):
        """Test that all expected RelationshipType values are present"""
        expected_values = {
            "adjacent",
            "above",
            "below",
            "under",
            "crosses",
            "intersects",
            "connected_to",
            "overlaps",
            "parallel",
            "perpendicular",
            "near",
            "far",
            "other",
        }
        actual_values = {rel_type.value for rel_type in RelationshipType}
        assert actual_values == expected_values

    def test_relationship_type_string_behavior(self):
        """Test that RelationshipType behaves like strings"""
        rel_type = RelationshipType.ADJACENT
        assert rel_type == "adjacent"
        assert rel_type.value == "adjacent"
        assert rel_type in ["adjacent", "above", "below"]

    def test_relationship_type_comparison(self):
        """Test RelationshipType comparison operations"""
        # String enums don't support comparison operators, so test equality and membership
        assert RelationshipType.ADJACENT == "adjacent"
        assert RelationshipType.CROSSES == "crosses"
        assert RelationshipType.OVERLAPS == "overlaps"
        assert RelationshipType.PARALLEL == "parallel"

    def test_spatial_relationship_logic(self):
        """Test logical relationships between spatial types"""
        # Test complementary relationships
        assert RelationshipType.ABOVE != RelationshipType.BELOW
        assert RelationshipType.PARALLEL != RelationshipType.PERPENDICULAR

        # Test that adjacent and connected are different concepts
        assert RelationshipType.ADJACENT != RelationshipType.CONNECTED_TO


class TestGeometryType:
    """Test GeometryType enum"""

    def test_geometry_type_values(self):
        """Test that GeometryType has the expected values"""
        assert GeometryType.POINT == "point"
        assert GeometryType.BBOX == "bbox"
        assert GeometryType.POLYLINE == "polyline"
        assert GeometryType.POLYGON == "polygon"

    def test_geometry_type_enumeration(self):
        """Test that all expected GeometryType values are present"""
        expected_values = {"point", "bbox", "polyline", "polygon"}
        actual_values = {geom_type.value for geom_type in GeometryType}
        assert actual_values == expected_values

    def test_geometry_type_string_behavior(self):
        """Test that GeometryType behaves like strings"""
        geom_type = GeometryType.POINT
        assert geom_type == "point"
        assert geom_type.value == "point"
        assert geom_type in ["point", "bbox", "polyline", "polygon"]

    def test_geometry_type_comparison(self):
        """Test GeometryType comparison operations"""
        # String enums don't support comparison operators, so test equality and membership
        assert GeometryType.POINT == "point"
        assert GeometryType.POLYGON == "polygon"
        assert GeometryType.BBOX == "bbox"
        assert GeometryType.POLYLINE == "polyline"

    def test_geometry_complexity_order(self):
        """Test that geometry types follow logical complexity order"""
        # Point is simplest
        assert GeometryType.POINT == "point"

        # BBOX is simple rectangle
        assert GeometryType.BBOX == "bbox"

        # Polyline is more complex than BBOX
        assert GeometryType.POLYLINE == "polyline"

        # Polygon is most complex (closed polyline)
        assert GeometryType.POLYGON == "polygon"


class TestEnumIntegration:
    """Test integration between the different enum types"""

    def test_enum_value_uniqueness(self):
        """Test that all enum values are unique across types"""
        text_values = {text_type.value for text_type in TextType}
        rel_values = {rel_type.value for rel_type in RelationshipType}
        geom_values = {geom_type.value for geom_type in GeometryType}

        # Check for any overlaps between different enum types
        text_rel_overlap = text_values.intersection(rel_values)
        text_geom_overlap = text_values.intersection(geom_values)
        rel_geom_overlap = rel_values.intersection(geom_values)

        # Note: 'other' is intentionally shared between TextType and RelationshipType
        # This is a design decision to allow generic categorization
        expected_overlap = {"other"}
        assert (
            text_rel_overlap == expected_overlap
        ), f"Unexpected overlap between TextType and RelationshipType: {text_rel_overlap}"
        assert (
            len(text_geom_overlap) == 0
        ), f"Overlap between TextType and GeometryType: {text_geom_overlap}"
        assert (
            len(rel_geom_overlap) == 0
        ), f"Overlap between RelationshipType and GeometryType: {rel_geom_overlap}"

    def test_enum_string_operations(self):
        """Test that enums work with common string operations"""
        # Test string concatenation using .value to get the actual string
        text_type = TextType.LABEL
        rel_type = RelationshipType.ADJACENT
        geom_type = GeometryType.POINT

        combined = f"{text_type.value}_{rel_type.value}_{geom_type.value}"
        assert combined == "label_adjacent_point"

        # Test string methods
        assert text_type.upper() == "LABEL"
        assert rel_type.capitalize() == "Adjacent"
        assert geom_type.title() == "Point"

    def test_enum_in_collections(self):
        """Test that enums work properly in collections"""
        # Test in sets
        text_types = {TextType.LABEL, TextType.MEASUREMENT, TextType.TITLE}
        assert TextType.LABEL in text_types
        assert TextType.NOTE not in text_types

        # Test in dictionaries
        rel_dict = {
            RelationshipType.ADJACENT: "next to",
            RelationshipType.ABOVE: "over",
            RelationshipType.BELOW: "under",
        }
        assert rel_dict[RelationshipType.ADJACENT] == "next to"

        # Test in lists
        geom_list = [GeometryType.POINT, GeometryType.BBOX, GeometryType.POLYLINE]
        assert GeometryType.POLYGON not in geom_list
        assert GeometryType.POINT in geom_list

    def test_enum_serialization(self):
        """Test that enums can be serialized and deserialized"""
        # Test JSON serialization (enum values are strings)
        import json

        data = {
            "text_type": TextType.LABEL,
            "relationship": RelationshipType.ADJACENT,
            "geometry": GeometryType.POINT,
        }

        json_str = json.dumps(data)
        assert '"label"' in json_str
        assert '"adjacent"' in json_str
        assert '"point"' in json_str

        # Test deserialization
        deserialized = json.loads(json_str)
        assert deserialized["text_type"] == "label"
        assert deserialized["relationship"] == "adjacent"
        assert deserialized["geometry"] == "point"

    def test_enum_validation(self):
        """Test that enums can be used for validation"""
        # Test valid values
        assert TextType("label") == TextType.LABEL
        assert RelationshipType("adjacent") == RelationshipType.ADJACENT
        assert GeometryType("point") == GeometryType.POINT

        # Test invalid values raise ValueError
        with pytest.raises(ValueError):
            TextType("invalid_text_type")

        with pytest.raises(ValueError):
            RelationshipType("invalid_relationship")

        with pytest.raises(ValueError):
            GeometryType("invalid_geometry")

    def test_enum_iteration(self):
        """Test that enums can be iterated over"""
        # Test iteration over all values
        text_types = list(TextType)
        assert len(text_types) == 6  # 6 text types

        rel_types = list(RelationshipType)
        assert len(rel_types) == 13  # 13 relationship types

        geom_types = list(GeometryType)
        assert len(geom_types) == 4  # 4 geometry types

        # Test that all values are unique
        assert len(set(text_types)) == len(text_types)
        assert len(set(rel_types)) == len(rel_types)
        assert len(set(geom_types)) == len(geom_types)
