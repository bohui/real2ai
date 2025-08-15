"""Diagram and image enums."""

from enum import Enum


class DiagramType(str, Enum):
    """Types of diagrams and plans"""

    TITLE_PLAN = "title_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    STRATA_PLAN = "strata_plan"
    BODY_CORPORATE_PLAN = "body_corporate_plan"
    DEVELOPMENT_PLAN = "development_plan"
    SUBDIVISION_PLAN = "subdivision_plan"
    OFF_THE_PLAN_MARKETING = "off_the_plan_marketing"
    SITE_PLAN = "site_plan"
    SEWER_SERVICE_DIAGRAM = "sewer_service_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    ZONING_MAP = "zoning_map"
    ENVIRONMENTAL_OVERLAY = "environmental_overlay"
    HERITAGE_OVERLAY = "heritage_overlay"
    CONTOUR_MAP = "contour_map"
    DRAINAGE_PLAN = "drainage_plan"
    UTILITY_PLAN = "utility_plan"
    PARKING_PLAN = "parking_plan"
    LANDSCAPE_PLAN = "landscape_plan"
    BUILDING_ENVELOPE_PLAN = "building_envelope_plan"
    UNKNOWN = "unknown"


class ImageType(str, Enum):
    """Types of images/diagrams that can be analyzed"""

    SITE_PLAN = "site_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    SEWER_SERVICE_DIAGRAM = "sewer_service_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    ZONING_MAP = "zoning_map"
    ENVIRONMENTAL_OVERLAY = "environmental_overlay"
    CONTOUR_MAP = "contour_map"
    DRAINAGE_PLAN = "drainage_plan"
    UTILITY_PLAN = "utility_plan"
    BUILDING_ENVELOPE_PLAN = "building_envelope_plan"
    STRATA_PLAN = "strata_plan"
    AERIAL_VIEW = "aerial_view"
    CROSS_SECTION = "cross_section"
    ELEVATION_VIEW = "elevation_view"
    LANDSCAPE_PLAN = "landscape_plan"
    PARKING_PLAN = "parking_plan"
    UNKNOWN = "unknown"
