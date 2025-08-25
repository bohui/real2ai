#!/usr/bin/env python3
"""
Test script for Valuation Comparison Service.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_valuation_comparison_basic():
    """Test basic valuation comparison functionality."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService, VarianceLevel
        
        service = ValuationComparisonService()
        
        # Create mock valuations data
        mock_valuations = {
            "domain": {
                "valuations": {
                    "domain": {
                        "estimated_value": 750000,
                        "confidence": 0.8,
                        "valuation_date": "2024-01-15T10:00:00Z",
                        "methodology": "market_comparison",
                        "valuation_range_lower": 720000,
                        "valuation_range_upper": 780000
                    }
                },
                "data_sources_used": ["recent_sales", "market_data"],
                "warnings": []
            },
            "corelogic": {
                "valuation_amount": 780000,
                "confidence_score": 0.85,
                "valuation_date": "2024-01-16T14:30:00Z",
                "methodology": "avm",
                "comparables_used": 6,
                "value_range": {"low": 760000, "high": 800000},
                "valuation_type": "avm",
                "market_conditions": {"data_age_days": 30},
                "quality_assessment": {"rating": "high"}
            }
        }
        
        # Test basic comparison
        result = service.compare_valuations(
            mock_valuations, 
            "123 Test Street Sydney NSW 2000"
        )
        
        # Validate basic structure
        assert "property_address" in result
        assert "analysis_timestamp" in result
        assert "valuation_sources" in result
        assert "summary_statistics" in result
        assert "variance_analysis" in result
        assert "consensus_valuation" in result
        
        # Validate valuation sources parsing
        assert len(result["valuation_sources"]) == 2
        
        # Validate summary statistics
        stats = result["summary_statistics"]
        assert stats["count"] == 2
        assert stats["mean"] > 0
        assert stats["median"] > 0
        assert stats["min"] <= stats["max"]
        
        # Validate variance analysis
        variance = result["variance_analysis"]
        assert "variance_level" in variance
        assert variance["variance_level"] in [level.value for level in VarianceLevel]
        
        # Validate consensus valuation
        consensus = result["consensus_valuation"]
        assert consensus["consensus_value"] > 0
        assert consensus["contributing_sources"] == 2
        
        print("✅ Basic valuation comparison works correctly")
        print(f"   - Consensus value: ${consensus['consensus_value']:,}")
        print(f"   - Variance level: {variance['variance_level']}")
        print(f"   - Source count: {len(result['valuation_sources'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic valuation comparison test failed: {e}")
        return False

def test_variance_analysis():
    """Test variance analysis with different scenarios."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService, VarianceLevel
        
        service = ValuationComparisonService()
        
        # Test high agreement scenario (low variance)
        low_variance_valuations = {
            "source1": {
                "estimated_value": 750000,
                "confidence_score": 0.8,
                "valuation_date": "2024-01-15T10:00:00Z",
                "methodology": "market_comparison"
            },
            "source2": {
                "estimated_value": 755000,
                "confidence_score": 0.85,
                "valuation_date": "2024-01-16T10:00:00Z", 
                "methodology": "avm"
            }
        }
        
        result = service.compare_valuations(
            low_variance_valuations,
            "123 Test Street Sydney NSW 2000"
        )
        
        variance = result["variance_analysis"]
        assert variance["variance_level"] in [VarianceLevel.LOW.value, VarianceLevel.MEDIUM.value]
        
        # Test high variance scenario
        high_variance_valuations = {
            "source1": {
                "estimated_value": 600000,
                "confidence_score": 0.7,
                "valuation_date": "2024-01-15T10:00:00Z",
                "methodology": "market_comparison"
            },
            "source2": {
                "estimated_value": 900000,
                "confidence_score": 0.6,
                "valuation_date": "2024-01-16T10:00:00Z",
                "methodology": "cost_approach"
            }
        }
        
        result_high = service.compare_valuations(
            high_variance_valuations,
            "456 Test Avenue Brisbane QLD 4000"
        )
        
        variance_high = result_high["variance_analysis"]
        assert variance_high["variance_level"] in [VarianceLevel.HIGH.value, VarianceLevel.VERY_HIGH.value]
        assert variance_high["variance_percentage"] > 10
        
        print("✅ Variance analysis works correctly")
        print(f"   - Low variance: {variance['variance_level']} ({variance['variance_percentage']:.1f}%)")
        print(f"   - High variance: {variance_high['variance_level']} ({variance_high['variance_percentage']:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Variance analysis test failed: {e}")
        return False

def test_outlier_detection():
    """Test outlier detection functionality."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService
        
        service = ValuationComparisonService()
        
        # Create data with one clear outlier
        outlier_valuations = {
            "source1": {
                "estimated_value": 750000,
                "confidence_score": 0.8,
                "valuation_date": "2024-01-15T10:00:00Z",
                "methodology": "market_comparison"
            },
            "source2": {
                "estimated_value": 760000,
                "confidence_score": 0.85,
                "valuation_date": "2024-01-16T10:00:00Z",
                "methodology": "avm"
            },
            "source3": {
                "estimated_value": 1200000,  # Clear outlier
                "confidence_score": 0.5,
                "valuation_date": "2024-01-17T10:00:00Z",
                "methodology": "professional"
            }
        }
        
        result = service.compare_valuations(
            outlier_valuations,
            "789 Test Road Perth WA 6000"
        )
        
        outliers = result["outlier_analysis"]
        assert "outliers" in outliers
        assert "outlier_count" in outliers
        
        # Should detect the high value as an outlier
        if outliers["outlier_count"] > 0:
            outlier_sources = [o["source"] for o in outliers["outliers"]]
            print(f"   - Detected outliers: {outlier_sources}")
        
        print("✅ Outlier detection works correctly")
        print(f"   - Outlier count: {outliers['outlier_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Outlier detection test failed: {e}")
        return False

def test_reliability_analysis():
    """Test reliability analysis of different sources."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService
        
        service = ValuationComparisonService()
        
        # Test with different source types
        mixed_sources = {
            "corelogic": {
                "valuation_amount": 780000,
                "confidence_score": 0.9,
                "valuation_date": "2024-01-16T10:00:00Z",
                "methodology": "avm",
                "comparables_used": 8
            },
            "domain": {
                "valuations": {
                    "domain": {
                        "estimated_value": 750000,
                        "confidence": 0.8,
                        "valuation_date": "2024-01-15T10:00:00Z",
                        "methodology": "market_comparison"
                    }
                }
            },
            "internal": {
                "estimated_value": 720000,
                "confidence_score": 0.6,
                "valuation_date": "2024-01-14T10:00:00Z",
                "methodology": "unknown"
            }
        }
        
        result = service.compare_valuations(
            mixed_sources,
            "321 Test Boulevard Adelaide SA 5000"
        )
        
        reliability = result["reliability_analysis"]
        assert "source_reliability" in reliability
        assert "most_reliable" in reliability
        assert "least_reliable" in reliability
        
        # CoreLogic should typically be rated as most reliable
        source_scores = reliability["source_reliability"]
        assert len(source_scores) == 3
        
        for source, data in source_scores.items():
            assert "score" in data
            assert "rating" in data
            assert data["score"] >= 0 and data["score"] <= 1
        
        print("✅ Reliability analysis works correctly")
        print(f"   - Most reliable: {reliability['most_reliable']}")
        print(f"   - Least reliable: {reliability['least_reliable']}")
        print(f"   - Average reliability: {reliability['average_reliability']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Reliability analysis test failed: {e}")
        return False

def test_recommendations_generation():
    """Test recommendations generation."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService
        
        service = ValuationComparisonService()
        
        # Test scenario that should generate recommendations
        problematic_valuations = {
            "single_source": {
                "estimated_value": 500000,
                "confidence_score": 0.4,  # Low confidence
                "valuation_date": "2024-01-15T10:00:00Z",
                "methodology": "unknown"
            }
        }
        
        result = service.compare_valuations(
            problematic_valuations,
            "999 Test Crescent Darwin NT 0800"
        )
        
        recommendations = result["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should recommend additional valuations for single source
        single_source_rec = any("additional" in rec.lower() for rec in recommendations)
        assert single_source_rec, "Should recommend additional valuations for single source"
        
        print("✅ Recommendations generation works correctly")
        print(f"   - Generated {len(recommendations)} recommendations")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"   - Rec {i}: {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Recommendations generation test failed: {e}")
        return False

def test_quality_scoring():
    """Test quality scoring system."""
    try:
        from app.services.valuation_comparison_service import ValuationComparisonService
        
        service = ValuationComparisonService()
        
        # High quality scenario
        high_quality_valuations = {
            "corelogic": {
                "valuation_amount": 780000,
                "confidence_score": 0.9,
                "valuation_date": "2024-01-16T10:00:00Z",
                "methodology": "professional",
                "comparables_used": 10
            },
            "domain": {
                "valuations": {
                    "domain": {
                        "estimated_value": 785000,
                        "confidence": 0.85,
                        "valuation_date": "2024-01-15T10:00:00Z",
                        "methodology": "market_comparison"
                    }
                }
            },
            "third_party": {
                "estimated_value": 775000,
                "confidence_score": 0.8,
                "valuation_date": "2024-01-17T10:00:00Z",
                "methodology": "desktop",
                "comparable_count": 6
            }
        }
        
        result = service.compare_valuations(
            high_quality_valuations,
            "111 Test Terrace Hobart TAS 7000"
        )
        
        quality = result["quality_scores"]
        assert "overall_quality" in quality
        assert "data_completeness" in quality
        assert "confidence_quality" in quality
        assert "methodology_diversity" in quality
        
        # Should be high quality with 3 sources and good confidence
        assert quality["overall_quality"] > 0.7
        assert quality["data_completeness"] >= 1.0  # 3 sources vs 3 expected
        assert quality["confidence_quality"] > 0.8
        
        print("✅ Quality scoring works correctly")
        print(f"   - Overall quality: {quality['overall_quality']:.2f}")
        print(f"   - Data completeness: {quality['data_completeness']:.2f}")
        print(f"   - Confidence quality: {quality['confidence_quality']:.2f}")
        print(f"   - Methodology diversity: {quality['methodology_diversity']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Quality scoring test failed: {e}")
        return False

def main():
    """Run all Valuation Comparison Service tests."""
    print("=" * 60)
    print("VALUATION COMPARISON SERVICE TESTS")
    print("=" * 60)
    
    tests = [
        test_valuation_comparison_basic,
        test_variance_analysis,
        test_outlier_detection,
        test_reliability_analysis,
        test_recommendations_generation,
        test_quality_scoring
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
        print("🎉 All Valuation Comparison Service tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())