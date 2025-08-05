"""
Market Analysis Service - Provides comprehensive market analysis and insights for property investments.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import statistics

from ..clients.domain.client import DomainClient
from ..clients.corelogic.client import CoreLogicClient
from ..clients.base.exceptions import (
    ClientError, PropertyNotFoundError, InvalidPropertyAddressError
)
from ..api.models import RiskLevel

logger = logging.getLogger(__name__)


class MarketTrend(Enum):
    """Enumeration for market trend directions."""
    STRONG_GROWTH = "strong_growth"
    MODERATE_GROWTH = "moderate_growth"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class MarketSegment(Enum):
    """Enumeration for market segments."""
    LUXURY = "luxury"
    PREMIUM = "premium"
    MID_MARKET = "mid_market"
    ENTRY_LEVEL = "entry_level"
    AFFORDABLE = "affordable"


class LiquidityLevel(Enum):
    """Enumeration for market liquidity levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class MarketMetrics:
    """Data class for market performance metrics."""
    median_price: float
    price_growth_3m: float
    price_growth_6m: float
    price_growth_12m: float
    sales_volume_3m: int
    sales_volume_12m: int
    days_on_market_avg: int
    price_volatility: float
    market_activity_score: float
    
    def __post_init__(self):
        """Validate metrics after initialization."""
        if self.median_price < 0:
            self.median_price = 0
        if self.days_on_market_avg < 0:
            self.days_on_market_avg = 0


@dataclass
class CompetitiveAnalysis:
    """Data class for competitive market analysis."""
    suburb_rank: int
    total_suburbs_analyzed: int
    price_percentile: float
    growth_percentile: float
    volume_percentile: float
    competitive_advantages: List[str]
    competitive_disadvantages: List[str]


class MarketAnalysisService:
    """
    Service for comprehensive market analysis and investment insights.
    Integrates data from multiple sources to provide detailed market intelligence.
    """
    
    def __init__(self, domain_client: DomainClient, corelogic_client: CoreLogicClient):
        self.domain_client = domain_client
        self.corelogic_client = corelogic_client
        self.logger = logger
        
        # Service configuration
        self.config = {
            "trend_analysis_periods": [3, 6, 12, 24],  # months
            "competitor_radius_km": 5.0,
            "min_sales_for_reliable_trends": 10,
            "volatility_threshold": 0.15,  # 15% coefficient of variation
            "high_growth_threshold": 0.10,  # 10% annual growth
            "high_volume_threshold": 50  # sales per year
        }
    
    async def get_comprehensive_market_analysis(
        self,
        location: Dict[str, str],
        property_type: Optional[str] = None,
        include_competitors: bool = True,
        include_forecasts: bool = True,
        include_investment_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive market analysis for a location.
        
        Args:
            location: Location dictionary with suburb and state
            property_type: Optional property type filter
            include_competitors: Include competitive analysis
            include_forecasts: Include market forecasts
            include_investment_metrics: Include investment-specific metrics
            
        Returns:
            Comprehensive market analysis with insights and recommendations
        """
        analysis_start_time = datetime.now(timezone.utc)
        
        try:
            # Initialize analysis structure
            market_analysis = {
                "location": location,
                "property_type": property_type,
                "analysis_timestamp": analysis_start_time,
                "data_sources": [],
                "market_metrics": {},
                "trend_analysis": {},
                "competitive_analysis": {},
                "market_forecast": {},
                "investment_insights": {},
                "risk_assessment": {},
                "recommendations": [],
                "data_quality": {},
                "warnings": []
            }
            
            # Concurrent data collection
            tasks = []
            
            # Core market metrics from Domain
            tasks.append(self._get_domain_market_data(location, property_type))
            
            # Additional insights from CoreLogic if available
            tasks.append(self._get_corelogic_market_data(location, property_type))
            
            # Historical trend analysis
            tasks.append(self._get_historical_trends(location, property_type))
            
            # Competitive analysis if requested
            if include_competitors:
                tasks.append(self._get_competitive_analysis(location, property_type))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            domain_data = results[0] if not isinstance(results[0], Exception) else None
            corelogic_data = results[1] if not isinstance(results[1], Exception) else None
            historical_data = results[2] if not isinstance(results[2], Exception) else None
            competitive_data = results[3] if include_competitors and len(results) > 3 and not isinstance(results[3], Exception) else None
            
            # Track data sources
            if domain_data:
                market_analysis["data_sources"].append("domain")
            if corelogic_data:
                market_analysis["data_sources"].append("corelogic")
            
            # Combine and analyze market metrics
            market_analysis["market_metrics"] = self._combine_market_metrics(
                domain_data, corelogic_data, historical_data
            )
            
            # Trend analysis
            market_analysis["trend_analysis"] = self._analyze_market_trends(
                market_analysis["market_metrics"], historical_data
            )
            
            # Competitive analysis
            if competitive_data:
                market_analysis["competitive_analysis"] = competitive_data
            
            # Market forecasts if requested
            if include_forecasts:
                market_analysis["market_forecast"] = self._generate_market_forecast(
                    market_analysis["market_metrics"], 
                    market_analysis["trend_analysis"]
                )
            
            # Investment insights if requested
            if include_investment_metrics:
                market_analysis["investment_insights"] = self._generate_investment_insights(
                    market_analysis
                )
            
            # Risk assessment
            market_analysis["risk_assessment"] = self._assess_market_risks(market_analysis)
            
            # Generate recommendations
            market_analysis["recommendations"] = self._generate_market_recommendations(market_analysis)
            
            # Assess data quality
            market_analysis["data_quality"] = self._assess_analysis_quality(market_analysis)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - analysis_start_time).total_seconds()
            market_analysis["processing_summary"] = {
                "processing_time_seconds": processing_time,
                "data_sources_used": len(market_analysis["data_sources"]),
                "analysis_completeness": self._calculate_analysis_completeness(market_analysis)
            }
            
            return market_analysis
            
        except Exception as e:
            self.logger.error(f"Market analysis failed for {location}: {e}")
            raise ClientError(f"Market analysis failed: {str(e)}")
    
    async def _get_domain_market_data(self, location: Dict[str, str], property_type: Optional[str]) -> Dict[str, Any]:
        """Get market data from Domain API."""
        try:
            # Get current market analytics
            current_data = await self.domain_client.get_market_analytics(
                location, 
                property_type, 
                include_trends=True,
                lookback_months=12
            )
            
            # Get longer-term historical data for trend analysis
            historical_data = await self.domain_client.get_market_analytics(
                location,
                property_type,
                include_trends=True,
                lookback_months=24
            )
            
            return {
                "current": current_data,
                "historical": historical_data,
                "source": "domain"
            }
            
        except Exception as e:
            self.logger.warning(f"Domain market data failed: {e}")
            raise e
    
    async def _get_corelogic_market_data(self, location: Dict[str, str], property_type: Optional[str]) -> Dict[str, Any]:
        """Get market data from CoreLogic API if available."""
        try:
            # CoreLogic market analytics would be called here
            # For now, return a placeholder structure
            return {
                "market_indicators": {
                    "supply_demand_ratio": 0.85,
                    "price_momentum": "positive",
                    "market_sentiment": "optimistic"
                },
                "source": "corelogic"
            }
            
        except Exception as e:
            self.logger.warning(f"CoreLogic market data failed: {e}")
            raise e
    
    async def _get_historical_trends(self, location: Dict[str, str], property_type: Optional[str]) -> Dict[str, Any]:
        """Get historical trend data for deeper analysis."""
        try:
            historical_trends = {
                "price_history": [],
                "volume_history": [],
                "seasonal_patterns": {},
                "cyclical_indicators": {}
            }
            
            # Get data for different time periods
            for months in self.config["trend_analysis_periods"]:
                try:
                    period_data = await self.domain_client.get_market_analytics(
                        location,
                        property_type,
                        lookback_months=months
                    )
                    
                    historical_trends["price_history"].append({
                        "period_months": months,
                        "median_price": period_data.get("median_price", 0),
                        "price_growth": period_data.get("price_growth_12_month", 0),
                        "sales_volume": period_data.get("sales_volume_12_month", 0)
                    })
                    
                except Exception as e:
                    self.logger.debug(f"Historical data for {months} months failed: {e}")
                    continue
            
            return historical_trends
            
        except Exception as e:
            self.logger.warning(f"Historical trends analysis failed: {e}")
            raise e
    
    async def _get_competitive_analysis(self, location: Dict[str, str], property_type: Optional[str]) -> Dict[str, Any]:
        """Get competitive analysis comparing to nearby suburbs."""
        try:
            # This would typically involve getting data for surrounding suburbs
            # For now, provide a structured analysis framework
            
            competitive_analysis = {
                "suburb_ranking": {
                    "price_rank": 0,
                    "growth_rank": 0,
                    "volume_rank": 0,
                    "total_compared": 0
                },
                "peer_comparison": {
                    "price_vs_peers": "above_average",
                    "growth_vs_peers": "average",
                    "volume_vs_peers": "below_average"
                },
                "competitive_advantages": [
                    "Strong transport links",
                    "Quality schools nearby",
                    "Growing employment hub"
                ],
                "competitive_disadvantages": [
                    "Higher price point than surrounding areas",
                    "Limited development opportunities"
                ],
                "market_positioning": "premium"
            }
            
            return competitive_analysis
            
        except Exception as e:
            self.logger.warning(f"Competitive analysis failed: {e}")
            raise e
    
    def _combine_market_metrics(
        self, 
        domain_data: Optional[Dict[str, Any]], 
        corelogic_data: Optional[Dict[str, Any]], 
        historical_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine market metrics from multiple sources."""
        
        combined_metrics = {
            "median_price": 0,
            "price_growth_3m": 0,
            "price_growth_6m": 0,
            "price_growth_12m": 0,
            "price_growth_24m": 0,
            "sales_volume_3m": 0,
            "sales_volume_12m": 0,
            "days_on_market_avg": 0,
            "price_volatility": 0,
            "market_activity_score": 0,
            "supply_demand_ratio": 1.0,
            "market_sentiment": "neutral"
        }
        
        # Extract Domain data
        if domain_data and domain_data.get("current"):
            current = domain_data["current"]
            combined_metrics.update({
                "median_price": current.get("median_price", 0),
                "price_growth_12m": current.get("price_growth_12_month", 0),
                "sales_volume_12m": current.get("sales_volume_12_month", 0),
                "days_on_market_avg": current.get("days_on_market_avg", 0),
                "market_activity_score": current.get("market_outlook_score", 0.5)
            })
        
        # Enhance with CoreLogic data
        if corelogic_data and corelogic_data.get("market_indicators"):
            indicators = corelogic_data["market_indicators"]
            combined_metrics.update({
                "supply_demand_ratio": indicators.get("supply_demand_ratio", 1.0),
                "market_sentiment": indicators.get("market_sentiment", "neutral")
            })
        
        # Calculate additional metrics from historical data
        if historical_data and historical_data.get("price_history"):
            price_history = historical_data["price_history"]
            if len(price_history) >= 2:
                # Calculate price volatility
                prices = [p["median_price"] for p in price_history if p["median_price"] > 0]
                if len(prices) >= 2:
                    price_std = statistics.stdev(prices)
                    price_mean = statistics.mean(prices)
                    combined_metrics["price_volatility"] = price_std / price_mean if price_mean > 0 else 0
                
                # Calculate shorter-term growth rates
                for period in price_history:
                    months = period["period_months"]
                    if months == 3:
                        combined_metrics["price_growth_3m"] = period["price_growth"]
                    elif months == 6:
                        combined_metrics["price_growth_6m"] = period["price_growth"]
                    elif months == 24:
                        combined_metrics["price_growth_24m"] = period["price_growth"]
        
        return combined_metrics
    
    def _analyze_market_trends(
        self, 
        metrics: Dict[str, Any], 
        historical_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze market trends and classify market conditions."""
        
        trend_analysis = {
            "current_trend": MarketTrend.STABLE,
            "trend_strength": 0.5,
            "trend_consistency": 0.5,
            "seasonal_patterns": {},
            "cyclical_position": "unknown",
            "momentum_indicators": {},
            "trend_forecast": "stable"
        }
        
        # Analyze price growth trends
        growth_12m = metrics.get("price_growth_12m", 0)
        volatility = metrics.get("price_volatility", 0)
        
        # Classify current trend
        if growth_12m > self.config["high_growth_threshold"]:
            if volatility < self.config["volatility_threshold"]:
                trend_analysis["current_trend"] = MarketTrend.STRONG_GROWTH
                trend_analysis["trend_strength"] = 0.9
            else:
                trend_analysis["current_trend"] = MarketTrend.VOLATILE
                trend_analysis["trend_strength"] = 0.6
        elif growth_12m > 0:
            trend_analysis["current_trend"] = MarketTrend.MODERATE_GROWTH
            trend_analysis["trend_strength"] = 0.7
        elif growth_12m > -0.05:  # -5%
            trend_analysis["current_trend"] = MarketTrend.STABLE
            trend_analysis["trend_strength"] = 0.5
        else:
            trend_analysis["current_trend"] = MarketTrend.DECLINING
            trend_analysis["trend_strength"] = 0.3
        
        # Calculate momentum indicators
        growth_3m = metrics.get("price_growth_3m", 0)
        growth_6m = metrics.get("price_growth_6m", 0)
        
        trend_analysis["momentum_indicators"] = {
            "short_term_momentum": "positive" if growth_3m > 0 else "negative",
            "medium_term_momentum": "positive" if growth_6m > 0 else "negative",
            "acceleration": growth_3m - growth_6m,
            "volume_trend": "increasing" if metrics.get("sales_volume_12m", 0) > metrics.get("sales_volume_3m", 0) * 4 else "decreasing"
        }
        
        # Assess trend consistency
        if historical_data and historical_data.get("price_history"):
            price_history = historical_data["price_history"]
            growth_rates = [p["price_growth"] for p in price_history if p["price_growth"] is not None]
            
            if len(growth_rates) >= 3:
                # Calculate consistency (lower standard deviation = more consistent)
                growth_std = statistics.stdev(growth_rates)
                growth_mean = abs(statistics.mean(growth_rates))
                trend_analysis["trend_consistency"] = max(0, 1 - (growth_std / max(growth_mean, 0.01)))
        
        return trend_analysis
    
    def _generate_market_forecast(
        self, 
        metrics: Dict[str, Any], 
        trend_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate market forecasts based on current trends and metrics."""
        
        forecast = {
            "forecast_horizon_months": 12,
            "price_forecast": {
                "expected_growth": 0,
                "confidence_interval": {"low": 0, "high": 0},
                "forecast_confidence": 0.5
            },
            "volume_forecast": {
                "expected_volume": 0,
                "seasonal_adjustments": {},
                "forecast_confidence": 0.5
            },
            "market_conditions_forecast": "stable",
            "key_assumptions": [],
            "risk_factors": []
        }
        
        # Price forecast based on current trends
        current_trend = trend_analysis.get("current_trend", MarketTrend.STABLE)
        trend_strength = trend_analysis.get("trend_strength", 0.5)
        current_growth = metrics.get("price_growth_12m", 0)
        
        # Simple trend continuation model (in production, use more sophisticated forecasting)
        if current_trend == MarketTrend.STRONG_GROWTH:
            forecast["price_forecast"]["expected_growth"] = min(current_growth * 0.8, 0.15)  # Cap at 15%
        elif current_trend == MarketTrend.MODERATE_GROWTH:
            forecast["price_forecast"]["expected_growth"] = current_growth * 0.7
        elif current_trend == MarketTrend.STABLE:
            forecast["price_forecast"]["expected_growth"] = current_growth * 0.5
        elif current_trend == MarketTrend.DECLINING:
            forecast["price_forecast"]["expected_growth"] = max(current_growth * 1.2, -0.10)  # Floor at -10%
        else:  # VOLATILE
            forecast["price_forecast"]["expected_growth"] = current_growth * 0.3
        
        # Calculate confidence intervals
        expected_growth = forecast["price_forecast"]["expected_growth"]
        volatility = metrics.get("price_volatility", 0.05)
        
        forecast["price_forecast"]["confidence_interval"] = {
            "low": expected_growth - (volatility * 1.96),  # 95% confidence interval
            "high": expected_growth + (volatility * 1.96)
        }
        
        # Forecast confidence based on trend consistency and data quality
        trend_consistency = trend_analysis.get("trend_consistency", 0.5)
        forecast["price_forecast"]["forecast_confidence"] = min(0.9, trend_consistency * trend_strength)
        
        # Volume forecast
        current_volume = metrics.get("sales_volume_12m", 0)
        forecast["volume_forecast"]["expected_volume"] = int(current_volume * (1 + expected_growth * 0.5))
        
        # Market conditions forecast
        if expected_growth > 0.05:
            forecast["market_conditions_forecast"] = "improving"
        elif expected_growth < -0.05:
            forecast["market_conditions_forecast"] = "declining"
        else:
            forecast["market_conditions_forecast"] = "stable"
        
        # Key assumptions and risk factors
        forecast["key_assumptions"] = [
            "Economic conditions remain stable",
            "Interest rates remain within current range",
            "No major policy changes affecting property market"
        ]
        
        forecast["risk_factors"] = [
            "Interest rate changes could impact demand",
            "Economic downturn could reduce buyer confidence",
            "Supply increases could pressure prices"
        ]
        
        return forecast
    
    def _generate_investment_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment-specific insights and recommendations."""
        
        metrics = analysis.get("market_metrics", {})
        trends = analysis.get("trend_analysis", {})
        forecast = analysis.get("market_forecast", {})
        
        investment_insights = {
            "investment_rating": "neutral",
            "investment_horizon": "medium_term",
            "expected_returns": {
                "capital_growth": 0,
                "rental_yield": 0,
                "total_return": 0
            },
            "investment_risks": [],
            "investment_opportunities": [],
            "market_timing": "neutral",
            "buyer_seller_advantage": "balanced",
            "investment_strategy_recommendations": []
        }
        
        # Calculate investment rating
        price_growth = metrics.get("price_growth_12m", 0)
        trend_strength = trends.get("trend_strength", 0.5)
        volatility = metrics.get("price_volatility", 0)
        
        if price_growth > 0.08 and trend_strength > 0.7 and volatility < 0.15:
            investment_insights["investment_rating"] = "strong_buy"
        elif price_growth > 0.05 and trend_strength > 0.6:
            investment_insights["investment_rating"] = "buy"
        elif price_growth > 0 and trend_strength > 0.4:
            investment_insights["investment_rating"] = "hold"
        elif price_growth < -0.05:
            investment_insights["investment_rating"] = "avoid"
        else:
            investment_insights["investment_rating"] = "neutral"
        
        # Expected returns
        forecast_growth = forecast.get("price_forecast", {}).get("expected_growth", 0)
        investment_insights["expected_returns"]["capital_growth"] = forecast_growth
        investment_insights["expected_returns"]["rental_yield"] = 0.04  # Placeholder - would calculate from rental data
        investment_insights["expected_returns"]["total_return"] = forecast_growth + 0.04
        
        # Market timing assessment
        current_trend = trends.get("current_trend", MarketTrend.STABLE)
        momentum = trends.get("momentum_indicators", {})
        
        if current_trend in [MarketTrend.STRONG_GROWTH, MarketTrend.MODERATE_GROWTH]:
            if momentum.get("acceleration", 0) > 0:
                investment_insights["market_timing"] = "favorable"
            else:
                investment_insights["market_timing"] = "neutral"
        elif current_trend == MarketTrend.DECLINING:
            investment_insights["market_timing"] = "wait"
        else:
            investment_insights["market_timing"] = "neutral"
        
        # Investment opportunities and risks
        if price_growth > 0.05:
            investment_insights["investment_opportunities"].append("Strong capital growth potential")
        
        if volatility > 0.15:
            investment_insights["investment_risks"].append("High price volatility")
        
        if metrics.get("days_on_market_avg", 0) > 60:
            investment_insights["investment_risks"].append("Slower market - longer selling times")
        else:
            investment_insights["investment_opportunities"].append("Active market with good liquidity")
        
        return investment_insights
    
    def _assess_market_risks(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess various market risks and their likelihood."""
        
        metrics = analysis.get("market_metrics", {})
        trends = analysis.get("trend_analysis", {})
        
        risk_assessment = {
            "overall_risk_level": RiskLevel.MEDIUM,
            "risk_factors": {
                "price_volatility_risk": "medium",
                "liquidity_risk": "low",
                "market_cycle_risk": "medium",
                "external_factors_risk": "medium"
            },
            "risk_score": 0.5,
            "mitigation_strategies": []
        }
        
        risk_score = 0.5  # Base risk
        
        # Price volatility risk
        volatility = metrics.get("price_volatility", 0)
        if volatility > 0.20:
            risk_assessment["risk_factors"]["price_volatility_risk"] = "high"
            risk_score += 0.2
        elif volatility < 0.10:
            risk_assessment["risk_factors"]["price_volatility_risk"] = "low"
            risk_score -= 0.1
        
        # Liquidity risk
        volume = metrics.get("sales_volume_12m", 0)
        days_on_market = metrics.get("days_on_market_avg", 0)
        
        if volume < 20 or days_on_market > 90:
            risk_assessment["risk_factors"]["liquidity_risk"] = "high"
            risk_score += 0.15
        elif volume > 50 and days_on_market < 45:
            risk_assessment["risk_factors"]["liquidity_risk"] = "low"
            risk_score -= 0.05
        
        # Market cycle risk
        current_trend = trends.get("current_trend", MarketTrend.STABLE)
        if current_trend == MarketTrend.VOLATILE:
            risk_assessment["risk_factors"]["market_cycle_risk"] = "high"
            risk_score += 0.15
        elif current_trend in [MarketTrend.STRONG_GROWTH, MarketTrend.MODERATE_GROWTH]:
            risk_assessment["risk_factors"]["market_cycle_risk"] = "medium"
        
        # Set overall risk level
        risk_assessment["risk_score"] = min(1.0, max(0.0, risk_score))
        
        if risk_score > 0.7:
            risk_assessment["overall_risk_level"] = RiskLevel.HIGH
        elif risk_score < 0.4:
            risk_assessment["overall_risk_level"] = RiskLevel.LOW
        
        # Generate mitigation strategies
        if risk_assessment["risk_factors"]["price_volatility_risk"] == "high":
            risk_assessment["mitigation_strategies"].append("Consider longer investment horizon to ride out volatility")
        
        if risk_assessment["risk_factors"]["liquidity_risk"] == "high":
            risk_assessment["mitigation_strategies"].append("Ensure adequate holding period and exit strategy")
        
        return risk_assessment
    
    def _generate_market_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable market recommendations."""
        
        recommendations = []
        
        metrics = analysis.get("market_metrics", {})
        trends = analysis.get("trend_analysis", {})
        investment = analysis.get("investment_insights", {})
        risks = analysis.get("risk_assessment", {})
        
        # Investment timing recommendations
        investment_rating = investment.get("investment_rating", "neutral")
        
        if investment_rating == "strong_buy":
            recommendations.append("Strong market conditions favor immediate investment consideration")
        elif investment_rating == "buy":
            recommendations.append("Market conditions are favorable for investment")
        elif investment_rating == "avoid":
            recommendations.append("Consider waiting for more favorable market conditions")
        
        # Risk-based recommendations
        overall_risk = risks.get("overall_risk_level", RiskLevel.MEDIUM)
        if overall_risk == RiskLevel.HIGH:
            recommendations.append("High market risk - ensure thorough due diligence and risk management")
        elif overall_risk == RiskLevel.LOW:
            recommendations.append("Low market risk environment supports confident investment decisions")
        
        # Market timing recommendations
        current_trend = trends.get("current_trend", MarketTrend.STABLE)
        momentum = trends.get("momentum_indicators", {})
        
        if current_trend == MarketTrend.DECLINING:
            recommendations.append("Declining market - consider waiting for stabilization before investing")
        elif momentum.get("acceleration", 0) > 0.02:
            recommendations.append("Positive market momentum - consider acting before further price increases")
        
        # Liquidity recommendations
        volume = metrics.get("sales_volume_12m", 0)
        if volume < 20:
            recommendations.append("Low market activity - factor in longer selling times for exit strategy")
        elif volume > 50:
            recommendations.append("Active market provides good liquidity for both buying and selling")
        
        # Data quality recommendations
        data_quality = analysis.get("data_quality", {})
        if data_quality.get("overall_quality", "medium") == "low":
            recommendations.append("Limited market data available - seek additional local market intelligence")
        
        return recommendations
    
    def _assess_analysis_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality and reliability of the market analysis."""
        
        quality_assessment = {
            "overall_quality": "medium",
            "data_completeness": 0.5,
            "data_reliability": 0.5,
            "analysis_confidence": 0.5,
            "limitations": []
        }
        
        # Data completeness score
        completeness_factors = []
        
        if analysis.get("market_metrics", {}).get("median_price", 0) > 0:
            completeness_factors.append(0.2)
        if analysis.get("trend_analysis", {}).get("current_trend"):
            completeness_factors.append(0.2)
        if analysis.get("competitive_analysis"):
            completeness_factors.append(0.2)
        if analysis.get("market_forecast"):
            completeness_factors.append(0.2)
        if analysis.get("investment_insights"):
            completeness_factors.append(0.2)
        
        quality_assessment["data_completeness"] = sum(completeness_factors)
        
        # Data reliability based on sources
        source_count = len(analysis.get("data_sources", []))
        if source_count >= 2:
            quality_assessment["data_reliability"] = 0.8
        elif source_count == 1:
            quality_assessment["data_reliability"] = 0.6
        else:
            quality_assessment["data_reliability"] = 0.3
        
        # Analysis confidence
        forecast_confidence = analysis.get("market_forecast", {}).get("price_forecast", {}).get("forecast_confidence", 0.5)
        trend_consistency = analysis.get("trend_analysis", {}).get("trend_consistency", 0.5)
        quality_assessment["analysis_confidence"] = (forecast_confidence + trend_consistency) / 2
        
        # Overall quality rating
        overall_score = (
            quality_assessment["data_completeness"] * 0.4 +
            quality_assessment["data_reliability"] * 0.3 +
            quality_assessment["analysis_confidence"] * 0.3
        )
        
        if overall_score > 0.7:
            quality_assessment["overall_quality"] = "high"
        elif overall_score < 0.4:
            quality_assessment["overall_quality"] = "low"
        
        # Identify limitations
        if source_count < 2:
            quality_assessment["limitations"].append("Limited data sources - analysis based primarily on single source")
        
        if analysis.get("warnings"):
            quality_assessment["limitations"].append("Data quality warnings present - see warnings section")
        
        if forecast_confidence < 0.6:
            quality_assessment["limitations"].append("Lower confidence in market forecasts due to trend inconsistency")
        
        return quality_assessment
    
    def _calculate_analysis_completeness(self, analysis: Dict[str, Any]) -> float:
        """Calculate analysis completeness score."""
        
        sections = [
            "market_metrics",
            "trend_analysis", 
            "competitive_analysis",
            "market_forecast",
            "investment_insights",
            "risk_assessment"
        ]
        
        completed_sections = sum(1 for section in sections if analysis.get(section))
        return completed_sections / len(sections)


# Factory function for creating the service
async def create_market_analysis_service(
    domain_config: Optional[Dict[str, Any]] = None,
    corelogic_config: Optional[Dict[str, Any]] = None
) -> MarketAnalysisService:
    """
    Factory function to create MarketAnalysisService with initialized clients.
    
    Args:
        domain_config: Domain API configuration
        corelogic_config: CoreLogic API configuration
        
    Returns:
        Initialized MarketAnalysisService
    """
    from ..clients.domain.config import DomainClientConfig
    from ..clients.corelogic.config import CoreLogicClientConfig
    
    # Initialize Domain client
    if not domain_config:
        domain_config = {"api_key": "demo_key"}
    
    domain_client_config = DomainClientConfig(**domain_config)
    domain_client = DomainClient(domain_client_config)
    await domain_client.initialize()
    
    # Initialize CoreLogic client
    if not corelogic_config:
        corelogic_config = {
            "api_key": "demo_key",
            "client_id": "demo_client", 
            "client_secret": "demo_secret"
        }
    
    corelogic_client_config = CoreLogicClientConfig(**corelogic_config)
    corelogic_client = CoreLogicClient(corelogic_client_config)
    await corelogic_client.initialize()
    
    return MarketAnalysisService(domain_client, corelogic_client)