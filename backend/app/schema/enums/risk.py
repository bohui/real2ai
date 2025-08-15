"""Risk and analysis enums."""

from enum import Enum


class RiskLevel(str, Enum):
    """Risk level indicators"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSeverity(str, Enum):
    """Risk severity levels"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class VarianceLevel(Enum):
    """Variance level indicators"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ReliabilityRating(Enum):
    """Reliability rating levels"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
