"""
Settings management for CoreLogic API client.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from .config import CoreLogicClientConfig


class CoreLogicSettings(BaseSettings):
    """CoreLogic API client settings with environment variable support."""
    
    # Authentication
    corelogic_api_key: str = Field("", env="CORELOGIC_API_KEY")
    corelogic_client_id: str = Field("", env="CORELOGIC_CLIENT_ID")
    corelogic_client_secret: str = Field("", env="CORELOGIC_CLIENT_SECRET")
    corelogic_environment: str = Field("sandbox", env="CORELOGIC_ENVIRONMENT")
    
    # Service Configuration
    corelogic_service_tier: str = Field("professional", env="CORELOGIC_SERVICE_TIER")
    corelogic_default_valuation_type: str = Field("avm", env="CORELOGIC_DEFAULT_VALUATION_TYPE")
    
    # Rate Limiting
    corelogic_rate_limit_rph: int = Field(1000, env="CORELOGIC_RATE_LIMIT_RPH")
    corelogic_requests_per_second: float = Field(0.28, env="CORELOGIC_REQUESTS_PER_SECOND")
    corelogic_concurrent_requests: int = Field(5, env="CORELOGIC_CONCURRENT_REQUESTS")
    
    # Timeouts
    corelogic_timeout: int = Field(60, env="CORELOGIC_TIMEOUT")
    corelogic_valuation_timeout: int = Field(120, env="CORELOGIC_VALUATION_TIMEOUT")
    corelogic_connect_timeout: int = Field(15, env="CORELOGIC_CONNECT_TIMEOUT")
    
    # Caching
    corelogic_enable_caching: bool = Field(True, env="CORELOGIC_ENABLE_CACHING")
    corelogic_cache_ttl: int = Field(86400, env="CORELOGIC_CACHE_TTL")  # 24 hours
    corelogic_market_cache_ttl: int = Field(259200, env="CORELOGIC_MARKET_CACHE_TTL")  # 3 days
    corelogic_risk_cache_ttl: int = Field(604800, env="CORELOGIC_RISK_CACHE_TTL")  # 7 days
    
    # Cost Management
    corelogic_enable_cost_tracking: bool = Field(True, env="CORELOGIC_ENABLE_COST_TRACKING")
    corelogic_daily_budget: float = Field(500.0, env="CORELOGIC_DAILY_BUDGET")
    corelogic_monthly_budget: float = Field(10000.0, env="CORELOGIC_MONTHLY_BUDGET")
    corelogic_budget_alert_threshold: float = Field(80.0, env="CORELOGIC_BUDGET_ALERT_THRESHOLD")
    corelogic_auto_suspend_on_budget: bool = Field(True, env="CORELOGIC_AUTO_SUSPEND_ON_BUDGET")
    
    # Data Quality
    corelogic_min_confidence_score: float = Field(0.6, env="CORELOGIC_MIN_CONFIDENCE_SCORE")
    corelogic_require_valuation_confidence: bool = Field(True, env="CORELOGIC_REQUIRE_VALUATION_CONFIDENCE")
    corelogic_max_comparable_age_months: int = Field(12, env="CORELOGIC_MAX_COMPARABLE_AGE_MONTHS")
    
    # Logging
    corelogic_enable_request_logging: bool = Field(True, env="CORELOGIC_ENABLE_REQUEST_LOGGING")
    corelogic_enable_response_logging: bool = Field(False, env="CORELOGIC_ENABLE_RESPONSE_LOGGING")
    corelogic_enable_cost_logging: bool = Field(True, env="CORELOGIC_ENABLE_COST_LOGGING")
    corelogic_log_level: str = Field("INFO", env="CORELOGIC_LOG_LEVEL")
    
    # Circuit Breaker
    corelogic_circuit_breaker_enabled: bool = Field(True, env="CORELOGIC_CIRCUIT_BREAKER_ENABLED")
    corelogic_failure_threshold: int = Field(3, env="CORELOGIC_FAILURE_THRESHOLD")
    corelogic_circuit_timeout: int = Field(300, env="CORELOGIC_CIRCUIT_TIMEOUT")
    
    # Bulk Operations
    corelogic_bulk_batch_size: int = Field(50, env="CORELOGIC_BULK_BATCH_SIZE")
    
    # Default Location
    corelogic_default_state: str = Field("NSW", env="CORELOGIC_DEFAULT_STATE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("corelogic_environment")
    def validate_environment(cls, v):
        if v not in ["sandbox", "production"]:
            raise ValueError("Environment must be 'sandbox' or 'production'")
        return v
    
    @validator("corelogic_service_tier")
    def validate_service_tier(cls, v):
        if v not in ["basic", "professional", "enterprise"]:
            raise ValueError("Service tier must be 'basic', 'professional', or 'enterprise'")
        return v
    
    @validator("corelogic_default_valuation_type")
    def validate_valuation_type(cls, v):
        if v not in ["avm", "desktop", "professional"]:
            raise ValueError("Valuation type must be 'avm', 'desktop', or 'professional'")
        return v
    
    @validator("corelogic_default_state")
    def validate_state(cls, v):
        valid_states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
        if v not in valid_states:
            raise ValueError(f"State must be one of {valid_states}")
        return v
    
    @validator("corelogic_log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("corelogic_min_confidence_score")
    def validate_confidence_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v
    
    @validator("corelogic_budget_alert_threshold")
    def validate_alert_threshold(cls, v):
        if not 0.0 <= v <= 100.0:
            raise ValueError("Budget alert threshold must be between 0.0 and 100.0")
        return v
    
    def to_client_config(self) -> CoreLogicClientConfig:
        """Convert settings to CoreLogicClientConfig."""
        
        # Build tier settings with current configuration
        tier_settings = {
            "basic": {
                "max_requests_per_hour": min(self.corelogic_rate_limit_rph, 100),
                "max_concurrent_requests": min(self.corelogic_concurrent_requests, 2),
                "cost_per_valuation": 2.50,
                "features": ["avm", "basic_analytics", "comparable_sales"]
            },
            "professional": {
                "max_requests_per_hour": min(self.corelogic_rate_limit_rph, 500),
                "max_concurrent_requests": min(self.corelogic_concurrent_requests, 5),
                "cost_per_valuation": 5.00,
                "features": ["avm", "desktop_valuation", "market_analytics", 
                            "risk_assessment", "comparable_sales", "yield_analysis"]
            },
            "enterprise": {
                "max_requests_per_hour": self.corelogic_rate_limit_rph,
                "max_concurrent_requests": self.corelogic_concurrent_requests,
                "cost_per_valuation": 8.00,
                "features": ["avm", "desktop_valuation", "professional_valuation",
                            "market_analytics", "risk_assessment", "comparable_sales",
                            "yield_analysis", "bulk_operations", "custom_reports"]
            }
        }
        
        return CoreLogicClientConfig(
            # Authentication
            api_key=self.corelogic_api_key,
            client_id=self.corelogic_client_id,
            client_secret=self.corelogic_client_secret,
            environment=self.corelogic_environment,
            
            # Service configuration
            service_tier=self.corelogic_service_tier,
            default_valuation_type=self.corelogic_default_valuation_type,
            
            # Rate limiting
            rate_limit_rph=self.corelogic_rate_limit_rph,
            requests_per_second=self.corelogic_requests_per_second,
            concurrent_requests_limit=self.corelogic_concurrent_requests,
            
            # Timeouts
            timeout=self.corelogic_timeout,
            valuation_timeout=self.corelogic_valuation_timeout,
            connect_timeout=self.corelogic_connect_timeout,
            
            # Caching
            enable_caching=self.corelogic_enable_caching,
            cache_ttl_seconds=self.corelogic_cache_ttl,
            market_data_cache_ttl=self.corelogic_market_cache_ttl,
            risk_assessment_cache_ttl=self.corelogic_risk_cache_ttl,
            
            # Cost management
            cost_management={
                "enable_cost_tracking": self.corelogic_enable_cost_tracking,
                "daily_budget_limit": self.corelogic_daily_budget,
                "monthly_budget_limit": self.corelogic_monthly_budget,
                "alert_threshold_percentage": self.corelogic_budget_alert_threshold,
                "auto_suspend_on_budget_exceeded": self.corelogic_auto_suspend_on_budget
            },
            
            # Data quality
            data_quality_settings={
                "min_confidence_score": self.corelogic_min_confidence_score,
                "require_valuation_confidence": self.corelogic_require_valuation_confidence,
                "validate_property_characteristics": True,
                "check_market_data_currency": True,
                "max_comparable_age_months": self.corelogic_max_comparable_age_months,
                "min_comparable_count": 3
            },
            
            # Logging
            enable_request_logging=self.corelogic_enable_request_logging,
            enable_response_logging=self.corelogic_enable_response_logging,
            enable_cost_logging=self.corelogic_enable_cost_logging,
            log_level=self.corelogic_log_level,
            
            # Circuit breaker
            circuit_breaker_enabled=self.corelogic_circuit_breaker_enabled,
            failure_threshold=self.corelogic_failure_threshold,
            circuit_timeout=self.corelogic_circuit_timeout,
            
            # Bulk operations
            bulk_valuation_batch_size=self.corelogic_bulk_batch_size,
            
            # Location
            default_state=self.corelogic_default_state,
            
            # Override tier settings with current configuration
            tier_settings=tier_settings
        )
    
    def validate_required_settings(self) -> Dict[str, Any]:
        """Validate that all required settings are present."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required authentication settings
        if not self.corelogic_api_key:
            validation_results["errors"].append("CORELOGIC_API_KEY is required")
            validation_results["valid"] = False
        
        if not self.corelogic_client_id:
            validation_results["errors"].append("CORELOGIC_CLIENT_ID is required")
            validation_results["valid"] = False
        
        if not self.corelogic_client_secret:
            validation_results["errors"].append("CORELOGIC_CLIENT_SECRET is required")
            validation_results["valid"] = False
        
        # Check budget configuration
        if self.corelogic_daily_budget <= 0:
            validation_results["errors"].append("Daily budget must be positive")
            validation_results["valid"] = False
        
        if self.corelogic_monthly_budget <= 0:
            validation_results["errors"].append("Monthly budget must be positive")
            validation_results["valid"] = False
        
        if self.corelogic_daily_budget > self.corelogic_monthly_budget:
            validation_results["warnings"].append("Daily budget is higher than monthly budget")
        
        # Check rate limiting
        if self.corelogic_requests_per_second * 3600 > self.corelogic_rate_limit_rph:
            validation_results["warnings"].append(
                "Requests per second setting may exceed hourly rate limit"
            )
        
        # Check service tier compatibility
        tier_limits = {
            "basic": 100,
            "professional": 500,
            "enterprise": 2000
        }
        
        max_for_tier = tier_limits.get(self.corelogic_service_tier, 1000)
        if self.corelogic_rate_limit_rph > max_for_tier:
            validation_results["warnings"].append(
                f"Rate limit ({self.corelogic_rate_limit_rph}) exceeds typical limit for "
                f"{self.corelogic_service_tier} tier ({max_for_tier})"
            )
        
        return validation_results
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get a summary of current environment configuration."""
        return {
            "environment": self.corelogic_environment,
            "service_tier": self.corelogic_service_tier,
            "default_valuation_type": self.corelogic_default_valuation_type,
            "rate_limits": {
                "requests_per_hour": self.corelogic_rate_limit_rph,
                "requests_per_second": self.corelogic_requests_per_second,
                "concurrent_requests": self.corelogic_concurrent_requests
            },
            "budget_limits": {
                "daily_budget_aud": self.corelogic_daily_budget,
                "monthly_budget_aud": self.corelogic_monthly_budget,
                "alert_threshold_percent": self.corelogic_budget_alert_threshold
            },
            "timeouts": {
                "general_timeout_seconds": self.corelogic_timeout,
                "valuation_timeout_seconds": self.corelogic_valuation_timeout,
                "connect_timeout_seconds": self.corelogic_connect_timeout
            },
            "caching": {
                "enabled": self.corelogic_enable_caching,
                "cache_ttl_hours": self.corelogic_cache_ttl / 3600,
                "market_cache_ttl_hours": self.corelogic_market_cache_ttl / 3600,
                "risk_cache_ttl_hours": self.corelogic_risk_cache_ttl / 3600
            },
            "data_quality": {
                "min_confidence_score": self.corelogic_min_confidence_score,
                "require_valuation_confidence": self.corelogic_require_valuation_confidence,
                "max_comparable_age_months": self.corelogic_max_comparable_age_months
            }
        }


def get_corelogic_settings() -> CoreLogicSettings:
    """Get CoreLogic settings with environment variable loading."""
    return CoreLogicSettings()


def create_corelogic_client_config() -> CoreLogicClientConfig:
    """Create CoreLogic client configuration from environment settings."""
    settings = get_corelogic_settings()
    validation = settings.validate_required_settings()
    
    if not validation["valid"]:
        error_messages = "; ".join(validation["errors"])
        raise ValueError(f"Invalid CoreLogic configuration: {error_messages}")
    
    # Log warnings if any
    if validation["warnings"]:
        import logging
        logger = logging.getLogger(__name__)
        for warning in validation["warnings"]:
            logger.warning(f"CoreLogic configuration warning: {warning}")
    
    return settings.to_client_config()