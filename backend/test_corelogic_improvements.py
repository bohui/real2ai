#!/usr/bin/env python3
"""
Test script for CoreLogic API client improvements.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_corelogic_address_validation():
    """Test CoreLogic address validation improvements."""
    try:
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.corelogic.config import CoreLogicClientConfig
        from app.clients.base.exceptions import InvalidPropertyAddressError
        
        # Test configuration
        config = CoreLogicClientConfig(
            api_key="test_key",
            client_id="test_client",
            client_secret="test_secret"
        )
        client = CoreLogicClient(config)
        
        # Test valid address cleaning
        cleaned = client._clean_and_validate_address("123 Collins Street Melbourne VIC 3000")
        assert "123 Collins Street Melbourne VIC 3000" == cleaned
        
        # Test address with extra spaces
        cleaned = client._clean_and_validate_address("  456   George   Street   Sydney   NSW   2000  ")
        assert "456 George Street Sydney NSW 2000" == cleaned
        
        # Test invalid addresses
        try:
            client._clean_and_validate_address("")
            assert False, "Should have raised InvalidPropertyAddressError for empty address"
        except InvalidPropertyAddressError:
            pass
        
        try:
            client._clean_and_validate_address("123")
            assert False, "Should have raised InvalidPropertyAddressError for too short address"
        except InvalidPropertyAddressError:
            pass
        
        print("✅ CoreLogic address validation works correctly")
        return True
        
    except Exception as e:
        print(f"❌ CoreLogic address validation test failed: {e}")
        return False

def test_corelogic_valuation_request_builder():
    """Test CoreLogic valuation request builder."""
    try:
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        config = CoreLogicClientConfig(
            api_key="test_key",
            client_id="test_client", 
            client_secret="test_secret"
        )
        client = CoreLogicClient(config)
        
        # Test basic request building
        property_details = {
            "property_type": "house",
            "bedrooms": 3,
            "bathrooms": 2.5,
            "land_area": 600,
            "building_area": 200,
            "features": ["pool", "garage"]
        }
        
        request = client._build_valuation_request(
            "123 Test Street Sydney NSW", 
            property_details, 
            "avm"
        )
        
        assert request["address"] == "123 Test Street Sydney NSW"
        assert request["property_type"] == "house"
        assert request["bedrooms"] == 3
        assert request["bathrooms"] == 2.5
        assert request["land_area"] == 600
        assert request["building_area"] == 200
        assert request["valuation_type"] == "avm"
        assert "pool" in request["additional_features"]
        
        # Test professional valuation request
        request_prof = client._build_valuation_request(
            "456 Test Avenue Brisbane QLD",
            {"include_risk_assessment": True},
            "professional"
        )
        
        assert "valuation_preferences" in request_prof
        assert request_prof["valuation_preferences"]["include_risk_assessment"] == True
        
        print("✅ CoreLogic valuation request builder works correctly")
        return True
        
    except Exception as e:
        print(f"❌ CoreLogic valuation request builder test failed: {e}")
        return False

def test_corelogic_response_validation():
    """Test CoreLogic response validation improvements."""
    try:
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        config = CoreLogicClientConfig(
            api_key="test_key",
            client_id="test_client",
            client_secret="test_secret"
        )
        client = CoreLogicClient(config)
        
        # Test valid response
        valid_response = {
            "valuation_amount": 750000,
            "confidence_score": 0.85,
            "comparables_count": 6,
            "methodology": "Automated Valuation Model",
            "value_range": {"low": 700000, "high": 800000},
            "market_conditions": {"data_age_days": 30}
        }
        
        result = client._validate_valuation_response(valid_response, "avm")
        assert result["is_valid"] == True
        assert len(result["warnings"]) == 0
        
        # Test response with warnings
        warning_response = {
            "valuation_amount": 1200000,
            "confidence_score": 0.7,
            "comparables_count": 2,  # Below minimum
            "market_conditions": {"data_age_days": 200}  # Old data
        }
        
        result = client._validate_valuation_response(warning_response, "desktop")
        assert result["is_valid"] == True
        assert len(result["warnings"]) > 0
        assert any("Limited comparable data" in w for w in result["warnings"])
        
        # Test invalid response
        invalid_response = {
            "valuation_amount": 0,  # Invalid
            "confidence_score": 0.3  # Too low
        }
        
        result = client._validate_valuation_response(invalid_response)
        assert result["is_valid"] == False
        assert "Invalid valuation amount" in result["reason"]
        
        print("✅ CoreLogic response validation works correctly")
        return True
        
    except Exception as e:
        print(f"❌ CoreLogic response validation test failed: {e}")
        return False

def test_corelogic_quality_assessment():
    """Test CoreLogic valuation quality assessment."""
    try:
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        config = CoreLogicClientConfig(
            api_key="test_key",
            client_id="test_client",
            client_secret="test_secret"
        )
        client = CoreLogicClient(config)
        
        # Test high quality response
        high_quality_response = {
            "confidence_score": 0.9,
            "comparables_count": 8,
            "market_conditions": {"data_age_days": 15}
        }
        
        assessment = client._assess_valuation_quality(high_quality_response, "professional")
        assert assessment["quality_rating"] == "high"
        assert assessment["quality_score"] >= 0.8
        
        # Test medium quality response
        medium_quality_response = {
            "confidence_score": 0.7,
            "comparables_count": 4,
            "market_conditions": {"data_age_days": 60}
        }
        
        assessment = client._assess_valuation_quality(medium_quality_response, "avm")
        assert assessment["quality_rating"] in ["medium", "high"]
        
        # Test low quality response
        low_quality_response = {
            "confidence_score": 0.4,
            "comparables_count": 1,
            "market_conditions": {"data_age_days": 250}
        }
        
        assessment = client._assess_valuation_quality(low_quality_response, "avm")
        assert assessment["quality_rating"] == "low"
        assert len(assessment["warnings"]) > 0
        
        print("✅ CoreLogic quality assessment works correctly")
        return True
        
    except Exception as e:
        print(f"❌ CoreLogic quality assessment test failed: {e}")
        return False

def main():
    """Run all CoreLogic improvement tests."""
    print("=" * 60)
    print("CORELOGIC API CLIENT IMPROVEMENTS TEST")
    print("=" * 60)
    
    tests = [
        test_corelogic_address_validation,
        test_corelogic_valuation_request_builder,
        test_corelogic_response_validation,
        test_corelogic_quality_assessment
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
        print("🎉 All CoreLogic API client improvement tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())