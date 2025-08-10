"""
Settings for Domain API client using Pydantic.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from .config import DomainClientConfig


class DomainSettings(BaseSettings):
    """Domain API client settings from environment variables."""
    
    # API Configuration
    domain_api_key: str = Field(..., env="DOMAIN_API_KEY")
    domain_project_id: Optional[str] = Field(None, env="DOMAIN_PROJECT_ID")
    
    # API Endpoints
    domain_base_url: str = Field("https://api.domain.com.au", env="DOMAIN_BASE_URL")
    domain_api_version: str = Field("v1", env="DOMAIN_API_VERSION")
    
    # Service Configuration
    domain_service_tier: str = Field("standard", env="DOMAIN_SERVICE_TIER")
    domain_timeout: int = Field(30, env="DOMAIN_TIMEOUT")
    domain_max_retries: int = Field(3, env="DOMAIN_MAX_RETRIES")
    domain_backoff_factor: float = Field(2.0, env="DOMAIN_BACKOFF_FACTOR")
    
    # Rate Limiting
    domain_rate_limit_rpm: int = Field(500, env="DOMAIN_RATE_LIMIT_RPM")
    domain_requests_per_second: float = Field(8.0, env="DOMAIN_REQUESTS_PER_SECOND")
    
    # Caching
    domain_enable_caching: bool = Field(True, env="DOMAIN_ENABLE_CACHING")
    domain_cache_ttl: int = Field(3600, env="DOMAIN_CACHE_TTL")
    domain_market_data_cache_ttl: int = Field(86400, env="DOMAIN_MARKET_DATA_CACHE_TTL")
    
    # Australian Configuration
    domain_default_state: str = Field("NSW", env="DOMAIN_DEFAULT_STATE")
    
    # Performance Settings
    domain_connection_pool_size: int = Field(20, env="DOMAIN_CONNECTION_POOL_SIZE")
    domain_keep_alive_timeout: int = Field(30, env="DOMAIN_KEEP_ALIVE_TIMEOUT")
    domain_read_timeout: int = Field(30, env="DOMAIN_READ_TIMEOUT")
    domain_connect_timeout: int = Field(10, env="DOMAIN_CONNECT_TIMEOUT")
    
    # Circuit Breaker
    domain_circuit_breaker_enabled: bool = Field(True, env="DOMAIN_CIRCUIT_BREAKER_ENABLED")
    domain_failure_threshold: int = Field(5, env="DOMAIN_FAILURE_THRESHOLD")
    domain_circuit_timeout: int = Field(60, env="DOMAIN_CIRCUIT_TIMEOUT")
    
    # Data Quality
    domain_validate_responses: bool = Field(True, env="DOMAIN_VALIDATE_RESPONSES")
    domain_strict_address_validation: bool = Field(True, env="DOMAIN_STRICT_ADDRESS_VALIDATION")
    domain_min_confidence_score: float = Field(0.7, env="DOMAIN_MIN_CONFIDENCE_SCORE")
    
    # Search Settings
    domain_max_search_results: int = Field(100, env="DOMAIN_MAX_SEARCH_RESULTS")
    domain_default_search_radius_km: float = Field(2.0, env="DOMAIN_DEFAULT_SEARCH_RADIUS_KM")
    
    # Logging
    domain_enable_request_logging: bool = Field(True, env="DOMAIN_ENABLE_REQUEST_LOGGING")
    domain_enable_response_logging: bool = Field(False, env="DOMAIN_ENABLE_RESPONSE_LOGGING")
    domain_log_level: str = Field("INFO", env="DOMAIN_LOG_LEVEL")
    
    @validator("domain_service_tier")
    def validate_service_tier(cls, v):
        """Validate service tier."""
        valid_tiers = ["standard", "premium", "enterprise"]
        if v not in valid_tiers:
            raise ValueError(f"Invalid service tier. Must be one of: {', '.join(valid_tiers)}")
        return v
    
    @validator("domain_default_state")
    def validate_default_state(cls, v):
        """Validate default Australian state."""
        valid_states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
        if v not in valid_states:
            raise ValueError(f"Invalid state. Must be one of: {', '.join(valid_states)}")
        return v
    
    @validator("domain_rate_limit_rpm")
    def validate_rate_limit(cls, v):
        """Validate rate limit is positive."""
        if v <= 0:
            raise ValueError("Rate limit must be positive")
        return v
    
    @validator("domain_max_search_results")
    def validate_max_search_results(cls, v):
        """Validate max search results."""
        if v > 1000:
            raise ValueError("Max search results cannot exceed 1000")
        return v
    
    @validator("domain_min_confidence_score")
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return v
    
    @validator("domain_log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    def to_client_config(self) -> DomainClientConfig:
        """Convert settings to Domain client configuration."""
        return DomainClientConfig(
            # API Configuration
            api_key=self.domain_api_key,
            project_id=self.domain_project_id,
            base_url=self.domain_base_url,
            api_version=self.domain_api_version,
            
            # Service Configuration
            service_tier=self.domain_service_tier,
            timeout=self.domain_timeout,
            max_retries=self.domain_max_retries,
            backoff_factor=self.domain_backoff_factor,
            
            # Rate Limiting
            rate_limit_rpm=self.domain_rate_limit_rpm,
            requests_per_second=self.domain_requests_per_second,
            
            # Caching
            enable_caching=self.domain_enable_caching,
            cache_ttl_seconds=self.domain_cache_ttl,
            market_data_cache_ttl=self.domain_market_data_cache_ttl,
            
            # Australian Configuration
            default_state=self.domain_default_state,
            
            # Performance Settings
            connection_pool_size=self.domain_connection_pool_size,
            keep_alive_timeout=self.domain_keep_alive_timeout,
            read_timeout=self.domain_read_timeout,
            connect_timeout=self.domain_connect_timeout,
            
            # Circuit Breaker
            circuit_breaker_enabled=self.domain_circuit_breaker_enabled,
            failure_threshold=self.domain_failure_threshold,
            circuit_timeout=self.domain_circuit_timeout,
            
            # Data Quality
            validate_responses=self.domain_validate_responses,
            strict_address_validation=self.domain_strict_address_validation,
            data_quality_settings={
                "min_confidence_score": self.domain_min_confidence_score,
                "require_address_geocoding": True,
                "validate_property_type": True,
                "check_data_freshness": True,
                "max_data_age_days": 30
            },
            
            # Search Settings
            max_search_results=self.domain_max_search_results,
            default_search_radius_km=self.domain_default_search_radius_km,
            
            # Logging
            enable_request_logging=self.domain_enable_request_logging,
            enable_response_logging=self.domain_enable_response_logging,
            log_level=self.domain_log_level,
        )
    
    model_config = {
        # Pydantic configuration
        "env_file": ".env",
        "case_sensitive": False,
        "validate_assignment": True,
        "extra": "ignore"  # Ignore extra environment variables
    }