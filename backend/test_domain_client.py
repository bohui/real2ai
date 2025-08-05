#!/usr/bin/env python3
"""
Simple test script to verify Domain client implementation.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_domain_config():
    """Test Domain client configuration."""
    try:
        from app.clients.domain.config import DomainClientConfig
        
        # Test basic config creation
        config = DomainClientConfig(api_key="test_key")
        
        # Test validation
        config.validate_config()
        
        # Test tier settings
        assert config.get_tier_setting("max_requests_per_minute") == 500
        assert config.is_feature_enabled("property_search") is True
        assert config.is_feature_enabled("market_analytics") is False
        
        # Test full base URL
        assert config.full_base_url == "https://api.domain.com.au/v1"
        
        # Test headers
        headers = config.headers
        assert headers["X-Api-Key"] == "test_key"
        assert "Real2AI" in headers["User-Agent"]
        
        print("✓ DomainClientConfig tests passed")
        return True
        
    except Exception as e:
        print(f"❌ DomainClientConfig test failed: {e}")
        return False


def test_domain_settings():
    """Test Domain client settings."""
    try:
        from app.clients.domain.settings import DomainSettings
        
        # Test settings creation
        settings = DomainSettings(domain_api_key="test_key")
        
        # Test conversion to client config
        config = settings.to_client_config()
        
        assert config.api_key == "test_key"
        assert config.service_tier == "standard"
        assert config.default_state == "NSW"
        
        print("✓ DomainSettings tests passed")
        return True
        
    except Exception as e:
        print(f"❌ DomainSettings test failed: {e}")
        return False


def test_rate_limiter():
    """Test rate limiter implementation."""
    try:
        from app.clients.domain.rate_limiter import AdaptiveRateLimiter, RateLimitManager
        
        # Test rate limiter creation
        limiter = AdaptiveRateLimiter(
            requests_per_minute=100,
            requests_per_second=2.0,
            burst_allowance=10
        )
        
        # Test status
        status = limiter.get_status()
        assert "requests_in_window" in status
        assert status["requests_per_minute_limit"] == 100
        
        # Test manager
        manager = RateLimitManager({"requests_per_minute": 100, "requests_per_second": 2.0})
        manager_status = manager.get_status()
        assert "global" in manager_status
        
        print("✓ Rate limiter tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        return False


def test_cache():
    """Test caching implementation."""
    try:
        from app.clients.domain.cache import InMemoryCache, PropertyDataCache
        
        # Test in-memory cache
        cache = InMemoryCache(max_size_mb=1, max_entries=100)
        
        # Test property data cache
        prop_cache = PropertyDataCache(cache)
        
        # Test key generation
        key = prop_cache._make_key("test", "arg1", kwarg1="value1")
        assert len(key) == 32  # MD5 hash length
        
        print("✓ Cache tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False


def test_models_integration():
    """Test integration with API models."""
    try:
        from app.api.models import PropertyAddress, PropertyDetails, AustralianState
        
        # Test property address creation
        address = PropertyAddress(
            street_number="123",
            street_name="Test",
            street_type="Street",
            suburb="Sydney",
            state=AustralianState.NSW,
            postcode="2000"
        )
        
        # Test property details
        details = PropertyDetails(
            property_type="House",
            bedrooms=3,
            bathrooms=2
        )
        
        print("✓ API models integration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ API models integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("DOMAIN API CLIENT TESTS")
    print("=" * 60)
    
    tests = [
        test_domain_config,
        test_domain_settings,
        test_rate_limiter,
        test_cache,
        test_models_integration
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All Domain API client tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())