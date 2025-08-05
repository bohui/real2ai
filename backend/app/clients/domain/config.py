"""
Configuration for Domain API client.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from ..base.client import ClientConfig


@dataclass
class DomainClientConfig(ClientConfig):
    """Configuration for Domain API client."""
    
    # Domain API Configuration
    api_key: str = ""
    project_id: Optional[str] = None
    
    # API Endpoints
    base_url: str = "https://api.domain.com.au"
    api_version: str = "v1"
    
    # Request settings
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Rate limiting
    rate_limit_rpm: int = 500  # Domain API allows 500 requests per minute
    requests_per_second: float = 8.0  # Conservative limit to avoid bursts
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    circuit_timeout: int = 60
    
    # Cache settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour for property data
    market_data_cache_ttl: int = 86400  # 24 hours for market data
    
    # Data validation
    validate_responses: bool = True
    strict_address_validation: bool = True
    
    # Australian specific settings
    default_state: str = "NSW"
    supported_states: list = field(default_factory=lambda: [
        "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"
    ])
    
    # Property search settings
    max_search_results: int = 100
    default_search_radius_km: float = 2.0
    
    # Service tiers
    service_tier: str = "standard"  # standard, premium, enterprise
    tier_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "standard": {
            "max_requests_per_minute": 500,
            "max_concurrent_requests": 10,
            "features": ["property_search", "property_details", "sales_history"]
        },
        "premium": {
            "max_requests_per_minute": 1500,
            "max_concurrent_requests": 25,
            "features": ["property_search", "property_details", "sales_history", 
                        "market_analytics", "comparable_sales", "demographics"]
        },
        "enterprise": {
            "max_requests_per_minute": 5000,
            "max_concurrent_requests": 50,
            "features": ["property_search", "property_details", "sales_history",
                        "market_analytics", "comparable_sales", "demographics",
                        "bulk_operations", "real_time_updates"]
        }
    })
    
    # Retry settings for specific operations
    retry_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "property_search": {"max_retries": 3, "backoff_factor": 1.5},
        "property_details": {"max_retries": 5, "backoff_factor": 2.0},
        "valuation": {"max_retries": 3, "backoff_factor": 2.0},
        "market_analytics": {"max_retries": 2, "backoff_factor": 1.0},
        "sales_history": {"max_retries": 3, "backoff_factor": 1.5}
    })
    
    # Data quality settings
    data_quality_settings: Dict[str, Any] = field(default_factory=lambda: {
        "min_confidence_score": 0.7,
        "require_address_geocoding": True,
        "validate_property_type": True,
        "check_data_freshness": True,
        "max_data_age_days": 30
    })
    
    # Monitoring and debugging
    enable_request_logging: bool = True
    enable_response_logging: bool = False  # Disable by default due to size
    log_level: str = "INFO"
    
    # Performance tuning
    connection_pool_size: int = 20
    keep_alive_timeout: int = 30
    read_timeout: int = 30
    connect_timeout: int = 10
    
    def get_tier_setting(self, key: str, default: Any = None) -> Any:
        """Get setting for current service tier."""
        return self.tier_settings.get(self.service_tier, {}).get(key, default)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if feature is enabled for current tier."""
        features = self.get_tier_setting("features", [])
        return feature in features
    
    def get_retry_config(self, operation: str) -> Dict[str, Any]:
        """Get retry configuration for specific operation."""
        return self.retry_settings.get(operation, {
            "max_retries": self.max_retries,
            "backoff_factor": self.backoff_factor
        })
    
    @property
    def full_base_url(self) -> str:
        """Get full base URL with version."""
        return f"{self.base_url}/{self.api_version}"
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get default request headers."""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Real2AI/1.0.0 Domain-Client"
        }
    
    def validate_config(self) -> None:
        """Validate configuration settings."""
        if not self.api_key:
            raise ValueError("Domain API key is required")
        
        if self.service_tier not in self.tier_settings:
            raise ValueError(f"Invalid service tier: {self.service_tier}")
        
        if self.default_state not in self.supported_states:
            raise ValueError(f"Invalid default state: {self.default_state}")
        
        if self.rate_limit_rpm <= 0:
            raise ValueError("Rate limit must be positive")
        
        if self.max_search_results > 1000:
            raise ValueError("Max search results cannot exceed 1000")