#!/usr/bin/env python3
"""
Test script for Market Analysis Service.
"""

import sys
import os
from datetime import datetime, timezone

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_market_metrics_combination():
    """Test market metrics combination from multiple sources."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
            MarketSegment,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test metrics combination
        mock_domain_data = {
            "current": {
                "median_price": 750000,
                "price_growth_12_month": 0.08,
                "sales_volume_12_month": 45,
                "days_on_market_avg": 35,
                "market_outlook_score": 0.7,
            }
        }

        mock_corelogic_data = {
            "market_indicators": {
                "supply_demand_ratio": 0.85,
                "price_momentum": "positive",
                "market_sentiment": "optimistic",
            }
        }

        mock_historical_data = {
            "price_history": [
                {
                    "period_months": 3,
                    "median_price": 745000,
                    "price_growth": 0.02,
                    "sales_volume": 12,
                },
                {
                    "period_months": 6,
                    "median_price": 735000,
                    "price_growth": 0.05,
                    "sales_volume": 23,
                },
                {
                    "period_months": 12,
                    "median_price": 720000,
                    "price_growth": 0.08,
                    "sales_volume": 45,
                },
            ]
        }

        combined = service._combine_market_metrics(
            mock_domain_data, mock_corelogic_data, mock_historical_data
        )

        # Validate combined metrics
        assert combined["median_price"] == 750000
        assert combined["price_growth_12m"] == 0.08
        assert combined["sales_volume_12m"] == 45
        assert combined["supply_demand_ratio"] == 0.85
        assert combined["market_sentiment"] == "optimistic"
        assert (
            combined["price_volatility"] > 0
        )  # Should calculate volatility from price history

        print("✅ Market metrics combination works correctly")
        print(f"   - Median price: ${combined['median_price']:,}")
        print(f"   - 12m growth: {combined['price_growth_12m']:.1%}")
        print(f"   - Price volatility: {combined['price_volatility']:.3f}")
        print(f"   - Market sentiment: {combined['market_sentiment']}")

        return True

    except Exception as e:
        print(f"❌ Market metrics combination test failed: {e}")
        return False


def test_trend_analysis():
    """Test market trend analysis functionality."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test strong growth scenario
        strong_growth_metrics = {
            "price_growth_12m": 0.15,  # 15% growth
            "price_growth_6m": 0.08,
            "price_growth_3m": 0.04,
            "price_volatility": 0.08,  # Low volatility
            "sales_volume_12m": 60,
            "sales_volume_3m": 18,
        }

        historical_data = {
            "price_history": [
                {"period_months": 3, "price_growth": 0.04},
                {"period_months": 6, "price_growth": 0.08},
                {"period_months": 12, "price_growth": 0.15},
                {"period_months": 24, "price_growth": 0.12},
            ]
        }

        trend_analysis = service._analyze_market_trends(
            strong_growth_metrics, historical_data
        )

        # Validate trend analysis
        assert trend_analysis["current_trend"] == MarketTrend.STRONG_GROWTH
        assert trend_analysis["trend_strength"] > 0.8
        assert "momentum_indicators" in trend_analysis
        assert (
            trend_analysis["momentum_indicators"]["short_term_momentum"] == "positive"
        )

        # Test declining market scenario
        declining_metrics = {
            "price_growth_12m": -0.08,  # -8% decline
            "price_growth_6m": -0.05,
            "price_growth_3m": -0.03,
            "price_volatility": 0.12,
            "sales_volume_12m": 25,
            "sales_volume_3m": 5,
        }

        declining_analysis = service._analyze_market_trends(declining_metrics, None)
        assert declining_analysis["current_trend"] == MarketTrend.DECLINING
        assert declining_analysis["trend_strength"] < 0.5

        print("✅ Trend analysis works correctly")
        print(f"   - Strong growth trend: {trend_analysis['current_trend'].value}")
        print(f"   - Trend strength: {trend_analysis['trend_strength']:.2f}")
        print(f"   - Declining trend: {declining_analysis['current_trend'].value}")

        return True

    except Exception as e:
        print(f"❌ Trend analysis test failed: {e}")
        return False


def test_market_forecast():
    """Test market forecast generation."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test forecast for strong growth market
        strong_growth_metrics = {
            "price_growth_12m": 0.12,
            "price_volatility": 0.06,
            "sales_volume_12m": 50,
        }

        strong_growth_trends = {
            "current_trend": MarketTrend.STRONG_GROWTH,
            "trend_strength": 0.9,
            "trend_consistency": 0.8,
        }

        forecast = service._generate_market_forecast(
            strong_growth_metrics, strong_growth_trends
        )

        # Validate forecast structure
        assert "forecast_horizon_months" in forecast
        assert "price_forecast" in forecast
        assert "volume_forecast" in forecast
        assert "market_conditions_forecast" in forecast

        # Validate price forecast
        price_forecast = forecast["price_forecast"]
        assert "expected_growth" in price_forecast
        assert "confidence_interval" in price_forecast
        assert "forecast_confidence" in price_forecast

        # For strong growth, expected growth should be positive but moderated
        assert price_forecast["expected_growth"] > 0
        assert price_forecast["expected_growth"] <= 0.15  # Capped at 15%
        assert (
            price_forecast["forecast_confidence"] > 0.6
        )  # High confidence for strong consistent trend

        # Test forecast for stable market
        stable_metrics = {
            "price_growth_12m": 0.02,
            "price_volatility": 0.04,
            "sales_volume_12m": 30,
        }

        stable_trends = {
            "current_trend": MarketTrend.STABLE,
            "trend_strength": 0.5,
            "trend_consistency": 0.6,
        }

        stable_forecast = service._generate_market_forecast(
            stable_metrics, stable_trends
        )

        # Stable market should have lower expected growth
        assert (
            stable_forecast["price_forecast"]["expected_growth"]
            < strong_growth_metrics["price_growth_12m"]
        )
        assert stable_forecast["market_conditions_forecast"] == "stable"

        print("✅ Market forecast generation works correctly")
        print(f"   - Strong growth forecast: {price_forecast['expected_growth']:.1%}")
        print(f"   - Forecast confidence: {price_forecast['forecast_confidence']:.2f}")
        print(f"   - Market conditions: {forecast['market_conditions_forecast']}")

        return True

    except Exception as e:
        print(f"❌ Market forecast test failed: {e}")
        return False


def test_investment_insights():
    """Test investment insights generation."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test strong investment scenario
        strong_investment_analysis = {
            "market_metrics": {
                "price_growth_12m": 0.10,  # 10% growth
                "price_volatility": 0.08,  # Low volatility
                "days_on_market_avg": 25,  # Good liquidity
            },
            "trend_analysis": {
                "current_trend": MarketTrend.STRONG_GROWTH,
                "trend_strength": 0.85,
                "momentum_indicators": {"acceleration": 0.02},
            },
            "market_forecast": {"price_forecast": {"expected_growth": 0.08}},
        }

        insights = service._generate_investment_insights(strong_investment_analysis)

        # Validate investment insights structure
        assert "investment_rating" in insights
        assert "investment_horizon" in insights
        assert "expected_returns" in insights
        assert "investment_risks" in insights
        assert "investment_opportunities" in insights
        assert "market_timing" in insights

        # Strong scenario should get positive rating
        assert insights["investment_rating"] in ["buy", "strong_buy"]
        assert insights["market_timing"] in ["favorable", "neutral"]
        assert insights["expected_returns"]["capital_growth"] > 0

        # Test weak investment scenario
        weak_investment_analysis = {
            "market_metrics": {
                "price_growth_12m": -0.06,  # -6% decline
                "price_volatility": 0.20,  # High volatility
                "days_on_market_avg": 75,  # Poor liquidity
            },
            "trend_analysis": {
                "current_trend": MarketTrend.DECLINING,
                "trend_strength": 0.3,
                "momentum_indicators": {"acceleration": -0.03},
            },
            "market_forecast": {"price_forecast": {"expected_growth": -0.03}},
        }

        weak_insights = service._generate_investment_insights(weak_investment_analysis)

        # Weak scenario should get negative rating
        assert weak_insights["investment_rating"] in ["avoid", "neutral"]
        assert weak_insights["market_timing"] in ["wait", "neutral"]

        print("✅ Investment insights generation works correctly")
        print(f"   - Strong market rating: {insights['investment_rating']}")
        print(
            f"   - Expected capital growth: {insights['expected_returns']['capital_growth']:.1%}"
        )
        print(f"   - Weak market rating: {weak_insights['investment_rating']}")
        print(f"   - Market timing: {insights['market_timing']}")

        return True

    except Exception as e:
        print(f"❌ Investment insights test failed: {e}")
        return False


def test_risk_assessment():
    """Test market risk assessment functionality."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        from app.schema import RiskLevel

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test high risk scenario
        high_risk_analysis = {
            "market_metrics": {
                "price_volatility": 0.25,  # High volatility
                "sales_volume_12m": 15,  # Low volume
                "days_on_market_avg": 95,  # Long selling times
            },
            "trend_analysis": {"current_trend": MarketTrend.VOLATILE},
        }

        risk_assessment = service._assess_market_risks(high_risk_analysis)

        # Validate risk assessment structure
        assert "overall_risk_level" in risk_assessment
        assert "risk_factors" in risk_assessment
        assert "risk_score" in risk_assessment
        assert "mitigation_strategies" in risk_assessment

        # High risk scenario validation
        assert risk_assessment["overall_risk_level"] in [
            RiskLevel.HIGH,
            RiskLevel.MEDIUM,
        ]
        assert risk_assessment["risk_factors"]["price_volatility_risk"] == "high"
        assert risk_assessment["risk_factors"]["liquidity_risk"] == "high"
        assert len(risk_assessment["mitigation_strategies"]) > 0

        # Test low risk scenario
        low_risk_analysis = {
            "market_metrics": {
                "price_volatility": 0.05,  # Low volatility
                "sales_volume_12m": 60,  # High volume
                "days_on_market_avg": 30,  # Quick selling times
            },
            "trend_analysis": {"current_trend": MarketTrend.MODERATE_GROWTH},
        }

        low_risk_assessment = service._assess_market_risks(low_risk_analysis)

        # Low risk scenario should have lower risk score
        assert low_risk_assessment["risk_score"] < risk_assessment["risk_score"]
        assert low_risk_assessment["risk_factors"]["price_volatility_risk"] == "low"
        assert low_risk_assessment["risk_factors"]["liquidity_risk"] == "low"

        print("✅ Risk assessment works correctly")
        print(f"   - High risk level: {risk_assessment['overall_risk_level'].value}")
        print(f"   - High risk score: {risk_assessment['risk_score']:.2f}")
        print(f"   - Low risk score: {low_risk_assessment['risk_score']:.2f}")
        print(
            f"   - Mitigation strategies: {len(risk_assessment['mitigation_strategies'])}"
        )

        return True

    except Exception as e:
        print(f"❌ Risk assessment test failed: {e}")
        return False


def test_recommendations_generation():
    """Test market recommendations generation."""
    try:
        from app.services.market_analysis_service import (
            MarketAnalysisService,
            MarketTrend,
        )
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig
        from app.schema import RiskLevel

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test favorable market scenario
        favorable_analysis = {
            "market_metrics": {"sales_volume_12m": 60},  # High volume
            "trend_analysis": {
                "current_trend": MarketTrend.STRONG_GROWTH,
                "momentum_indicators": {"acceleration": 0.03},
            },
            "investment_insights": {"investment_rating": "strong_buy"},
            "risk_assessment": {"overall_risk_level": RiskLevel.LOW},
            "data_quality": {"overall_quality": "high"},
        }

        recommendations = service._generate_market_recommendations(favorable_analysis)

        # Validate recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Should contain positive investment recommendations
        investment_recs = [r for r in recommendations if "investment" in r.lower()]
        assert len(investment_recs) > 0

        # Test unfavorable market scenario
        unfavorable_analysis = {
            "market_metrics": {"sales_volume_12m": 15},  # Low volume
            "trend_analysis": {
                "current_trend": MarketTrend.DECLINING,
                "momentum_indicators": {"acceleration": -0.02},
            },
            "investment_insights": {"investment_rating": "avoid"},
            "risk_assessment": {"overall_risk_level": RiskLevel.HIGH},
            "data_quality": {"overall_quality": "low"},
        }

        unfavorable_recommendations = service._generate_market_recommendations(
            unfavorable_analysis
        )

        # Should contain cautionary recommendations
        caution_recs = [
            r
            for r in unfavorable_recommendations
            if any(word in r.lower() for word in ["wait", "caution", "avoid", "risk"])
        ]
        assert len(caution_recs) > 0

        print("✅ Recommendations generation works correctly")
        print(f"   - Favorable scenario recommendations: {len(recommendations)}")
        print(f"   - Sample recommendation: {recommendations[0]}")
        print(
            f"   - Unfavorable scenario recommendations: {len(unfavorable_recommendations)}"
        )

        return True

    except Exception as e:
        print(f"❌ Recommendations generation test failed: {e}")
        return False


def test_analysis_quality_assessment():
    """Test analysis quality assessment."""
    try:
        from app.services.market_analysis_service import MarketAnalysisService
        from app.clients.domain.client import DomainClient
        from app.clients.corelogic.client import CoreLogicClient
        from app.clients.domain.config import DomainClientConfig
        from app.clients.corelogic.config import CoreLogicClientConfig

        # Create mock clients
        domain_config = DomainClientConfig(api_key="test_key")
        corelogic_config = CoreLogicClientConfig(
            api_key="test_key", client_id="test_client", client_secret="test_secret"
        )

        domain_client = DomainClient(domain_config)
        corelogic_client = CoreLogicClient(corelogic_config)

        service = MarketAnalysisService(domain_client, corelogic_client)

        # Test high quality analysis
        high_quality_analysis = {
            "data_sources": ["domain", "corelogic"],
            "market_metrics": {"median_price": 750000},
            "trend_analysis": {"current_trend": "strong_growth"},
            "competitive_analysis": {"suburb_ranking": {}},
            "market_forecast": {"price_forecast": {"forecast_confidence": 0.85}},
            "investment_insights": {"investment_rating": "buy"},
            "warnings": [],
        }

        quality = service._assess_analysis_quality(high_quality_analysis)

        # Validate quality assessment structure
        assert "overall_quality" in quality
        assert "data_completeness" in quality
        assert "data_reliability" in quality
        assert "analysis_confidence" in quality
        assert "limitations" in quality

        # High quality scenario validation
        assert quality["data_completeness"] >= 0.8  # All major sections present
        assert quality["data_reliability"] >= 0.7  # Multiple data sources
        assert quality["overall_quality"] in ["high", "medium"]

        # Test low quality analysis
        low_quality_analysis = {
            "data_sources": [],  # No data sources
            "market_metrics": {},
            "warnings": ["Data unavailable", "Limited coverage", "API errors"],
        }

        low_quality = service._assess_analysis_quality(low_quality_analysis)

        # Low quality should have lower scores
        assert low_quality["data_completeness"] < quality["data_completeness"]
        assert low_quality["data_reliability"] < quality["data_reliability"]
        assert low_quality["overall_quality"] in ["low", "medium"]
        assert len(low_quality["limitations"]) > 0

        print("✅ Analysis quality assessment works correctly")
        print(f"   - High quality overall: {quality['overall_quality']}")
        print(f"   - Data completeness: {quality['data_completeness']:.2f}")
        print(f"   - Data reliability: {quality['data_reliability']:.2f}")
        print(f"   - Low quality limitations: {len(low_quality['limitations'])}")

        return True

    except Exception as e:
        print(f"❌ Analysis quality assessment test failed: {e}")
        return False


def main():
    """Run all Market Analysis Service tests."""
    print("=" * 60)
    print("MARKET ANALYSIS SERVICE TESTS")
    print("=" * 60)

    tests = [
        test_market_metrics_combination,
        test_trend_analysis,
        test_market_forecast,
        test_investment_insights,
        test_risk_assessment,
        test_recommendations_generation,
        test_analysis_quality_assessment,
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
        print("🎉 All Market Analysis Service tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
