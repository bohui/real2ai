"""Confidence and quality enums."""

from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence levels for semantic extraction"""

    HIGH = "high"  # >90% confidence
    MEDIUM = "medium"  # 70-90% confidence
    LOW = "low"  # 50-70% confidence
    UNCERTAIN = "uncertain"  # <50% confidence


class QualityTier(Enum):
    """Quality tier levels"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
