"""Insight and content enums."""

from enum import Enum


class InsightType(str, Enum):
    """Types of insights"""

    TREND = "trend"
    FORECAST = "forecast"
    COMPARISON = "comparison"
    HOTSPOT = "hotspot"


class ViewSource(str, Enum):
    """Sources of property views"""

    SEARCH = "search"
    BOOKMARK = "bookmark"
    ANALYSIS = "analysis"
    UPLOAD = "upload"
    CACHE_HIT = "cache_hit"
    SHARED = "shared"


class ContentType(str, Enum):
    """Types of content"""

    TEXT = "text"
    DIAGRAM = "diagram"
    TABLE = "table"
    SIGNATURE = "signature"
    MIXED = "mixed"
    EMPTY = "empty"
