"""
CoreLogic API client for Real2.AI platform.

Provides comprehensive property valuation, market analytics, and risk assessment
capabilities through CoreLogic's professional-grade property data APIs.
"""

from .client import CoreLogicClient
from .config import CoreLogicClientConfig
from .settings import CoreLogicSettings, get_corelogic_settings, create_corelogic_client_config
from .rate_limiter import CoreLogicRateLimitManager
from .cache import CoreLogicCacheManager, CoreLogicPropertyCacheOperations

__all__ = [
    "CoreLogicClient",
    "CoreLogicClientConfig", 
    "CoreLogicSettings",
    "get_corelogic_settings",
    "create_corelogic_client_config",
    "CoreLogicRateLimitManager",
    "CoreLogicCacheManager",
    "CoreLogicPropertyCacheOperations"
]

__version__ = "1.0.0"