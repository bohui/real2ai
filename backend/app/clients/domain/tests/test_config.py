"""
Unit tests for Domain API client configuration.
"""

import pytest
from ..config import DomainClientConfig


class TestDomainClientConfig:
    """Test cases for Domain API client configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DomainClientConfig(api_key="test_key")
        
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.domain.com.au"
        assert config.api_version == "v1"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.backoff_factor == 2.0
        assert config.rate_limit_rpm == 500
        assert config.requests_per_second == 8.0
        assert config.service_tier == "standard"
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600
        assert config.default_state == "NSW"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = DomainClientConfig(
            api_key="custom_key",
            base_url="https://custom.api.domain.com.au",
            timeout=60,
            service_tier="premium",
            rate_limit_rpm=1000,
            default_state="VIC"
        )
        
        assert config.api_key == "custom_key"
        assert config.base_url == "https://custom.api.domain.com.au"
        assert config.timeout == 60
        assert config.service_tier == "premium"
        assert config.rate_limit_rpm == 1000
        assert config.default_state == "VIC"
    
    def test_full_base_url(self):
        """Test full base URL construction."""
        config = DomainClientConfig(
            api_key="test_key",
            base_url="https://api.domain.com.au",
            api_version="v2"
        )
        
        assert config.full_base_url == "https://api.domain.com.au/v2"
    
    def test_headers(self):
        """Test default headers."""
        config = DomainClientConfig(api_key="test_api_key_123")
        headers = config.headers
        
        assert headers["X-Api-Key"] == "test_api_key_123"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
        assert "Real2AI" in headers["User-Agent"]
    
    def test_tier_settings(self):
        """Test service tier settings."""
        config = DomainClientConfig(api_key="test_key")
        
        # Test standard tier
        config.service_tier = "standard"
        assert config.get_tier_setting("max_requests_per_minute") == 500
        assert config.get_tier_setting("max_concurrent_requests") == 10
        
        # Test premium tier
        config.service_tier = "premium"
        assert config.get_tier_setting("max_requests_per_minute") == 1500
        assert config.get_tier_setting("max_concurrent_requests") == 25
        
        # Test enterprise tier
        config.service_tier = "enterprise"
        assert config.get_tier_setting("max_requests_per_minute") == 5000
        assert config.get_tier_setting("max_concurrent_requests") == 50
        
        # Test unknown setting
        assert config.get_tier_setting("unknown_setting", "default") == "default"
    
    def test_feature_availability(self):
        """Test feature availability by tier."""
        config = DomainClientConfig(api_key="test_key")
        
        # Standard tier features
        config.service_tier = "standard"
        assert config.is_feature_enabled("property_search") is True
        assert config.is_feature_enabled("property_details") is True
        assert config.is_feature_enabled("sales_history") is True
        assert config.is_feature_enabled("market_analytics") is False
        assert config.is_feature_enabled("demographics") is False
        
        # Premium tier features
        config.service_tier = "premium"
        assert config.is_feature_enabled("property_search") is True
        assert config.is_feature_enabled("market_analytics") is True
        assert config.is_feature_enabled("comparable_sales") is True
        assert config.is_feature_enabled("demographics") is True
        assert config.is_feature_enabled("bulk_operations") is False
        
        # Enterprise tier features
        config.service_tier = "enterprise"
        assert config.is_feature_enabled("bulk_operations") is True
        assert config.is_feature_enabled("real_time_updates") is True
    
    def test_retry_config(self):
        """Test retry configuration for operations."""
        config = DomainClientConfig(api_key="test_key")
        
        # Test specific operation retry config
        property_search_config = config.get_retry_config("property_search")
        assert property_search_config["max_retries"] == 3
        assert property_search_config["backoff_factor"] == 1.5
        
        # Test default retry config for unknown operation
        unknown_config = config.get_retry_config("unknown_operation")
        assert unknown_config["max_retries"] == 3  # Default from config
        assert unknown_config["backoff_factor"] == 2.0  # Default from config
    
    def test_supported_states(self):
        """Test supported Australian states."""
        config = DomainClientConfig(api_key="test_key")
        
        expected_states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
        assert config.supported_states == expected_states
        assert config.default_state in expected_states
    
    def test_data_quality_settings(self):
        """Test data quality settings."""
        config = DomainClientConfig(api_key="test_key")
        
        quality_settings = config.data_quality_settings
        assert quality_settings["min_confidence_score"] == 0.7
        assert quality_settings["require_address_geocoding"] is True
        assert quality_settings["validate_property_type"] is True
        assert quality_settings["check_data_freshness"] is True
        assert quality_settings["max_data_age_days"] == 30
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config = DomainClientConfig(
            api_key="valid_api_key",
            service_tier="premium",
            default_state="NSW",
            rate_limit_rpm=1000,
            max_search_results=500
        )
        
        # Should not raise any exceptions
        config.validate_config()
    
    def test_config_validation_missing_api_key(self):
        """Test validation failure for missing API key."""
        config = DomainClientConfig(api_key="")
        
        with pytest.raises(ValueError, match="Domain API key is required"):
            config.validate_config()
    
    def test_config_validation_invalid_service_tier(self):
        """Test validation failure for invalid service tier."""
        config = DomainClientConfig(
            api_key="test_key",
            service_tier="invalid_tier"
        )
        
        with pytest.raises(ValueError, match="Invalid service tier"):
            config.validate_config()
    
    def test_config_validation_invalid_state(self):
        """Test validation failure for invalid default state."""
        config = DomainClientConfig(
            api_key="test_key",
            default_state="INVALID"
        )
        
        with pytest.raises(ValueError, match="Invalid default state"):
            config.validate_config()
    
    def test_config_validation_invalid_rate_limit(self):
        """Test validation failure for invalid rate limit."""
        config = DomainClientConfig(
            api_key="test_key",
            rate_limit_rpm=0
        )
        
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            config.validate_config()
    
    def test_config_validation_max_search_results(self):
        """Test validation failure for excessive max search results."""
        config = DomainClientConfig(
            api_key="test_key",
            max_search_results=2000
        )
        
        with pytest.raises(ValueError, match="Max search results cannot exceed 1000"):
            config.validate_config()
    
    def test_performance_settings(self):
        """Test performance-related settings."""
        config = DomainClientConfig(api_key="test_key")
        
        assert config.connection_pool_size == 20
        assert config.keep_alive_timeout == 30
        assert config.read_timeout == 30
        assert config.connect_timeout == 10
    
    def test_cache_settings(self):
        """Test caching configuration."""
        config = DomainClientConfig(api_key="test_key")
        
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600
        assert config.market_data_cache_ttl == 86400
    
    def test_logging_settings(self):
        """Test logging configuration."""
        config = DomainClientConfig(api_key="test_key")
        
        assert config.enable_request_logging is True
        assert config.enable_response_logging is False
        assert config.log_level == "INFO"
    
    def test_circuit_breaker_settings(self):
        """Test circuit breaker configuration."""
        config = DomainClientConfig(api_key="test_key")
        
        assert config.circuit_breaker_enabled is True
        assert config.failure_threshold == 5
        assert config.circuit_timeout == 60