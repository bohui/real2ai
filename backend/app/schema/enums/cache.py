"""Cache and performance enums."""

from enum import Enum


class CacheStatus(str, Enum):
    """Cache status indicators"""

    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"


class CachePolicy(Enum):
    """Cache policy types"""

    NO_CACHE = "no_cache"
    CACHE_FIRST = "cache_first"
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"
    CACHE_ONLY = "cache_only"


class CachePriority(Enum):
    """Cache priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
