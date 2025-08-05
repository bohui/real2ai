#!/usr/bin/env python3
"""
Test script for Domain.com.au API client improvements.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_domain_client_improvements():
    """Test Domain client improvements without API calls."""
    try:
        from app.clients.domain.client import DomainClient
        from app.clients.domain.config import DomainClientConfig
        
        # Test configuration
        config = DomainClientConfig(api_key="test_key")
        client = DomainClient(config)
        
        # Test address cleaning
        cleaned = client._clean_address("  123  Test Street,  Sydney   NSW  2000  ")
        assert "123 Test Street, Sydney NSW 2000" in cleaned or "123 Test Street" in cleaned
        
        # Test similarity calculation
        similarity = client._calculate_simple_similarity("123 main street", "123 main st")
        assert similarity > 0.5
        
        # Test address match confidence
        mock_address = {"displayAddress": "123 Main Street, Sydney NSW 2000"}
        confidence = client._calculate_address_match_confidence("123 Main St Sydney NSW", mock_address)
        assert 0.0 <= confidence <= 1.0
        
        print("✅ Domain client improvements work correctly")
        print(f"   - Address cleaning: {cleaned}")
        print(f"   - Similarity score: {similarity:.2f}")
        print(f"   - Match confidence: {confidence:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Domain client improvements test failed: {e}")
        return False

def test_market_analytics_helpers():
    """Test market analytics helper functions."""
    try:
        from app.clients.domain.client import DomainClient
        from app.clients.domain.config import DomainClientConfig
        
        config = DomainClientConfig(api_key="test_key")
        client = DomainClient(config)
        
        # Test market outlook determination
        outlook = client._determine_market_outlook([100000, 200000, 300000], 25)
        assert outlook in ["active", "moderate", "quiet", "insufficient_data"]
        
        # Test days on market estimation
        mock_sales = [{"price": 100000} for _ in range(30)]
        days = client._estimate_days_on_market(mock_sales)
        assert isinstance(days, int) and days > 0
        
        # Test quality warnings generation
        warnings = client._generate_quality_warnings(0.3, 5, 3)
        assert isinstance(warnings, list)
        
        print("✅ Market analytics helpers work correctly")
        print(f"   - Market outlook: {outlook}")
        print(f"   - Days on market: {days}")
        print(f"   - Quality warnings: {len(warnings)} generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Market analytics helpers test failed: {e}")
        return False

def main():
    """Run all improvement tests."""
    print("=" * 60)
    print("DOMAIN API CLIENT IMPROVEMENTS TEST")
    print("=" * 60)
    
    tests = [
        test_domain_client_improvements,
        test_market_analytics_helpers
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
        print("🎉 All Domain API client improvement tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())