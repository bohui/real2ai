"""Valuation and market enums."""

from enum import Enum


class ValuationSource(str, Enum):
    """Sources of property valuations"""

    DOMAIN = "domain"
    CORELOGIC = "corelogic"
    COMBINED = "combined"


class ValuationType(str, Enum):
    """Types of property valuations"""

    AVM = "avm"
    DESKTOP = "desktop"
    PROFESSIONAL = "professional"


class MarketOutlook(str, Enum):
    """Market outlook indicators"""

    DECLINING = "declining"
    STABLE = "stable"
    GROWING = "growing"
    STRONG_GROWTH = "strong_growth"


class MarketTrend(Enum):
    """Market trend indicators"""

    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class MarketSegment(Enum):
    """Market segments"""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    LUXURY = "luxury"
    AFFORDABLE = "affordable"


class LiquidityLevel(Enum):
    """Market liquidity levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
