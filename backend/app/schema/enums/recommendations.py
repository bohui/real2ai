"""Recommendation enums."""

from enum import Enum


class RecommendationPriority(str, Enum):
    """Recommendation priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCategory(str, Enum):
    """Recommendation categories"""

    LEGAL = "legal"
    FINANCIAL = "financial"
    PROPERTY = "property"
    MARKET = "market"
    RISK = "risk"
    OTHER = "other"
