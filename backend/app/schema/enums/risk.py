"""Risk and analysis enums."""

from enum import Enum


class RiskLevel(str, Enum):
    """Risk level indicators"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Deprecated: RiskSeverity
# Use RiskLevel (low, medium, high, critical) across the system.


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


class RiskCategory(str, Enum):
    """Unified risk categories for consolidated risk reporting."""

    INFRASTRUCTURE = "infrastructure"
    EASEMENT = "easement"
    BOUNDARY = "boundary"
    DEVELOPMENT = "development"
    ENVIRONMENTAL = "environmental"
    ZONING = "zoning"
    DISCREPANCY = "discrepancy"
    ACCESS = "access"
    COMPLIANCE = "compliance"
    LEGAL = "legal"
    OTHER = "other"
