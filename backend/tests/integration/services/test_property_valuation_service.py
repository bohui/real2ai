#!/usr/bin/env python3
"""
Test script for Property Valuation Service.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_valuation_consensus():
    """Test valuation consensus calculation."""
    try:
        from app.services.property_valuation_service import PropertyValuationService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", 
            client_id="test_client", 
            client_secret="test_secret"
        )
        
        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)
        
        service = PropertyValuationService(domain_client, corelogic_client)
        
        # Test consensus calculation with mock data
        mock_valuations = {
            "domain": {
                "valuations": {
                    "domain": {
                        "estimated_value": 750000,
                        "confidence": 0.8
                    }
                }
            },
            "corelogic": {
                "valuation_amount": 780000,
                "confidence_score": 0.85
            }
        }
        
        consensus = service._calculate_valuation_consensus(mock_valuations)
        
        assert consensus["source_count"] == 2
        assert consensus["consensus_value"] > 0
        assert 740000 <= consensus["consensus_value"] <= 790000  # Should be between the two values
        assert consensus["confidence"] > 0.8  # Should reflect the confidence scores
        assert consensus["agreement_level"] in ["high", "medium", "low"]
        
        print("✅ Valuation consensus calculation works correctly")
        print(f"   - Consensus value: ${consensus['consensus_value']:,}")
        print(f"   - Agreement level: {consensus['agreement_level']}")
        print(f"   - Confidence: {consensus['confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Valuation consensus test failed: {e}")
        return False

def test_location_extraction():
    """Test location extraction from address."""
    try:
        from app.services.property_valuation_service import PropertyValuationService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", 
            client_id="test_client", 
            client_secret="test_secret"
        )
        
        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)
        
        service = PropertyValuationService(domain_client, corelogic_client)
        
        # Test location extraction
        test_addresses = [
            "123 Collins Street Melbourne VIC 3000",
            "456 George Street Sydney NSW 2000",
            "789 Queen Street Brisbane QLD 4000"
        ]
        
        for address in test_addresses:
            location = service._extract_location_from_address(address)
            
            assert "suburb" in location
            assert "state" in location
            assert location["state"] in ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
            
            print(f"   - Address: {address}")
            print(f"     Location: {location['suburb']}, {location['state']}")
        
        print("✅ Location extraction works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Location extraction test failed: {e}")
        return False

def test_confidence_assessment():
    """Test overall confidence assessment."""
    try:
        from app.services.property_valuation_service import PropertyValuationService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", 
            client_id="test_client", 
            client_secret="test_secret"
        )
        
        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)
        
        service = PropertyValuationService(domain_client, corelogic_client)
        
        # Test high confidence scenario
        high_confidence_analysis = {
            "data_sources": ["domain", "corelogic"],
            "market_data": {"median_price": 500000},
            "risk_assessment": {"overall_risk": "medium"},
            "enriched_insights": {
                "valuation_consensus": {
                    "agreement_level": "high"
                }
            }
        }
        
        confidence = service._assess_overall_confidence(high_confidence_analysis)
        
        assert confidence["confidence_level"] in ["high", "medium", "low"]
        assert confidence["overall_confidence"] >= 0.0
        assert confidence["overall_confidence"] <= 1.0
        assert isinstance(confidence["contributing_factors"], list)
        
        print("✅ Confidence assessment works correctly")
        print(f"   - Overall confidence: {confidence['overall_confidence']:.2f}")
        print(f"   - Confidence level: {confidence['confidence_level']}")
        print(f"   - Contributing factors: {len(confidence['contributing_factors'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Confidence assessment test failed: {e}")
        return False

def test_data_quality_assessment():
    """Test data quality assessment."""
    try:
        from app.services.property_valuation_service import PropertyValuationService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", 
            client_id="test_client", 
            client_secret="test_secret"
        )
        
        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)
        
        service = PropertyValuationService(domain_client, corelogic_client)
        
        # Test quality assessment with comprehensive data
        comprehensive_analysis = {
            "data_sources": ["domain", "corelogic"],
            "valuations": {"domain": {}, "corelogic": {}},
            "market_data": {"median_price": 500000},
            "risk_assessment": {"overall_risk": "medium"},
            "comparable_sales": {"comparables": []},
            "warnings": ["Minor data inconsistency"]
        }
        
        quality = service._assess_overall_data_quality(comprehensive_analysis)
        
        assert quality["overall_quality"] in ["high", "medium", "low"]
        assert quality["quality_score"] >= 0.0
        assert quality["quality_score"] <= 1.0
        assert quality["data_completeness"] >= 0.0
        assert quality["data_completeness"] <= 1.0
        assert quality["source_diversity"] >= 1
        
        print("✅ Data quality assessment works correctly")
        print(f"   - Overall quality: {quality['overall_quality']}")
        print(f"   - Quality score: {quality['quality_score']:.2f}")
        print(f"   - Data completeness: {quality['data_completeness']:.2f}")
        print(f"   - Source diversity: {quality['source_diversity']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data quality assessment test failed: {e}")
        return False

def test_market_position_analysis():
    """Test market position analysis."""
    try:
        from app.services.property_valuation_service import PropertyValuationService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        
        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", 
            client_id="test_client", 
            client_secret="test_secret"
        )
        
        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)
        
        service = PropertyValuationService(domain_client, corelogic_client)
        
        # Test market position analysis
        mock_valuations = {
            "corelogic": {
                "valuation_amount": 600000,
                "confidence_score": 0.8
            }
        }
        
        mock_market_data = {
            "median_price": 500000,
            "sales_volume_12_month": 35
        }
        
        position = service._analyze_market_position(mock_valuations, mock_market_data)
        
        assert position["price_vs_median"] in ["above_market", "above_median", "at_median", "below_median", "unknown"]
        assert position["market_tier"] in ["premium", "upper_middle", "middle", "entry_level", "unknown"]
        assert position["liquidity_assessment"] in ["high", "medium", "low", "unknown"]
        
        print("✅ Market position analysis works correctly")
        print(f"   - Price vs median: {position['price_vs_median']}")
        print(f"   - Market tier: {position['market_tier']}")
        print(f"   - Liquidity: {position['liquidity_assessment']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Market position analysis test failed: {e}")
        return False

def main():
    """Run all Property Valuation Service tests."""
    print("=" * 60)
    print("PROPERTY VALUATION SERVICE TESTS")
    print("=" * 60)
    
    tests = [
        test_valuation_consensus,
        test_location_extraction,
        test_confidence_assessment,
        test_data_quality_assessment,
        test_market_position_analysis
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
        print("🎉 All Property Valuation Service tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())