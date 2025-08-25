"""
Configuration for CoreLogic API client.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from ..base.client import ClientConfig


@dataclass
class CoreLogicClientConfig(ClientConfig):
    """Configuration for CoreLogic API client."""
    
    # CoreLogic API Configuration
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    environment: str = "sandbox"  # sandbox, production
    
    # API Endpoints
    base_url: str = "https://api.corelogic.com.au"
    auth_url: str = "https://auth.corelogic.com.au"
    api_version: str = "v2"
    
    # Request settings
    timeout: int = 60  # CoreLogic valuations can take longer
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Rate limiting - CoreLogic has stricter limits
    rate_limit_rph: int = 1000  # Requests per hour
    requests_per_second: float = 0.28  # Conservative to stay under hourly limit
    concurrent_requests_limit: int = 5  # Lower concurrency
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 3  # More sensitive for expensive operations
    circuit_timeout: int = 300  # 5 minutes for recovery
    
    # Cache settings - Longer TTL for expensive valuation data
    enable_caching: bool = True
    cache_ttl_seconds: int = 86400  # 24 hours for valuations
    market_data_cache_ttl: int = 259200  # 3 days for market analytics
    risk_assessment_cache_ttl: int = 604800  # 7 days for risk assessments
    
    # Data validation
    validate_responses: bool = True
    strict_valuation_validation: bool = True
    require_confidence_scores: bool = True
    
    # Australian specific settings
    default_state: str = "NSW"
    supported_states: list = field(default_factory=lambda: [
        "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"
    ])
    
    # Valuation settings
    default_valuation_type: str = "avm"  # avm, professional, desktop
    valuation_timeout: int = 120  # 2 minutes for valuations
    bulk_valuation_batch_size: int = 50
    
    # Service tiers with cost tracking
    service_tier: str = "professional"  # basic, professional, enterprise
    tier_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "basic": {
            "max_requests_per_hour": 100,
            "max_concurrent_requests": 2,
            "cost_per_valuation": 2.50,
            "features": ["avm", "basic_analytics", "comparable_sales"]
        },
        "professional": {
            "max_requests_per_hour": 500,
            "max_concurrent_requests": 5,
            "cost_per_valuation": 5.00,
            "features": ["avm", "desktop_valuation", "market_analytics", 
                        "risk_assessment", "comparable_sales", "yield_analysis"]
        },
        "enterprise": {
            "max_requests_per_hour": 2000,
            "max_concurrent_requests": 10,
            "cost_per_valuation": 8.00,
            "features": ["avm", "desktop_valuation", "professional_valuation",
                        "market_analytics", "risk_assessment", "comparable_sales",
                        "yield_analysis", "bulk_operations", "custom_reports"]
        }
    })
    
    # Retry settings for specific operations
    retry_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "avm_valuation": {"max_retries": 2, "backoff_factor": 3.0},
        "desktop_valuation": {"max_retries": 1, "backoff_factor": 5.0},
        "professional_valuation": {"max_retries": 1, "backoff_factor": 10.0},
        "market_analytics": {"max_retries": 3, "backoff_factor": 2.0},
        "risk_assessment": {"max_retries": 2, "backoff_factor": 3.0},
        "comparable_sales": {"max_retries": 3, "backoff_factor": 1.5}
    })
    
    # Data quality and validation settings
    data_quality_settings: Dict[str, Any] = field(default_factory=lambda: {
        "min_confidence_score": 0.6,  # Lower threshold for CoreLogic
        "require_valuation_confidence": True,
        "validate_property_characteristics": True,
        "check_market_data_currency": True,
        "max_comparable_age_months": 12,
        "min_comparable_count": 3
    })
    
    # Cost management
    cost_management: Dict[str, Any] = field(default_factory=lambda: {
        "enable_cost_tracking": True,
        "daily_budget_limit": 500.00,  # AUD
        "monthly_budget_limit": 10000.00,  # AUD
        "alert_threshold_percentage": 80.0,
        "auto_suspend_on_budget_exceeded": True
    })
    
    # Monitoring and debugging
    enable_request_logging: bool = True
    enable_response_logging: bool = False  # Sensitive valuation data
    enable_cost_logging: bool = True
    log_level: str = "INFO"
    
    # Performance tuning
    connection_pool_size: int = 10  # Smaller pool for CoreLogic
    keep_alive_timeout: int = 60
    read_timeout: int = 120  # Longer for valuations
    connect_timeout: int = 15
    
    # Authentication settings
    token_refresh_threshold: int = 300  # Refresh 5 minutes before expiry
    max_auth_retries: int = 3
    
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
    
    def get_operation_cost(self, operation: str, quantity: int = 1) -> float:
        """Calculate cost for operation."""
        cost_per_valuation = self.get_tier_setting("cost_per_valuation", 0.0)
        
        operation_multipliers = {
            "avm_valuation": 1.0,
            "desktop_valuation": 2.0,
            "professional_valuation": 3.5,
            "bulk_valuation": 0.8,  # Bulk discount
            "market_analytics": 0.5,
            "risk_assessment": 1.5,
            "comparable_sales": 0.3
        }
        
        multiplier = operation_multipliers.get(operation, 1.0)
        return cost_per_valuation * multiplier * quantity
    
    @property
    def full_base_url(self) -> str:
        """Get full base URL with version."""
        return f"{self.base_url}/{self.api_version}"
    
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
    
    def get_api_headers(self, access_token: str) -> Dict[str, str]:
        """Get API request headers with access token."""
        return {
            "Authorization": f"Bearer {access_token}",
            "X-Client-ID": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Real2AI/1.0.0 CoreLogic-Client"
        }
    
    @property
    def environment_config(self) -> Dict[str, str]:
        """Get environment-specific configuration."""
        if self.environment == "production":
            return {
                "base_url": "https://api.corelogic.com.au",
                "auth_url": "https://auth.corelogic.com.au"
            }
        else:  # sandbox
            return {
                "base_url": "https://api-sandbox.corelogic.com.au",
                "auth_url": "https://auth-sandbox.corelogic.com.au"
            }
    
    def validate_config(self) -> None:
        """Validate configuration settings."""
        if not self.api_key:
            raise ValueError("CoreLogic API key is required")
        
        if not self.client_id:
            raise ValueError("CoreLogic Client ID is required")
        
        if not self.client_secret:
            raise ValueError("CoreLogic Client Secret is required")
        
        if self.environment not in ["sandbox", "production"]:
            raise ValueError("Environment must be 'sandbox' or 'production'")
        
        if self.service_tier not in self.tier_settings:
            raise ValueError(f"Invalid service tier: {self.service_tier}")
        
        if self.default_state not in self.supported_states:
            raise ValueError(f"Invalid default state: {self.default_state}")
        
        if self.rate_limit_rph <= 0:
            raise ValueError("Rate limit must be positive")
        
        # Validate cost management settings
        cost_settings = self.cost_management
        if cost_settings["daily_budget_limit"] <= 0:
            raise ValueError("Daily budget limit must be positive")
        
        if cost_settings["monthly_budget_limit"] <= 0:
            raise ValueError("Monthly budget limit must be positive")