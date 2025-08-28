"""Semantics-related enums for diagram content."""

from enum import Enum


class TextType(str, Enum):
    """Types of textual information found on diagrams."""

    LABEL = "label"
    MEASUREMENT = "measurement"
    TITLE = "title"
    LEGEND = "legend"
    NOTE = "note"
    WARNING = "warning"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Spatial relationship types between elements."""

    ADJACENT = "adjacent"
    ABOVE = "above"
    BELOW = "below"
    UNDER = "under"
    CROSSES = "crosses"
    INTERSECTS = "intersects"
    CONNECTED_TO = "connected_to"
    OVERLAPS = "overlaps"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    NEAR = "near"
    FAR = "far"
    WITHIN = "within"
    OTHER = "other"


class GeometryType(str, Enum):
    """Geometry representation of a location reference."""

    POINT = "point"
    BBOX = "bbox"
    POLYLINE = "polyline"
    POLYGON = "polygon"
