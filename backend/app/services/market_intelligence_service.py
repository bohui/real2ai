"""
Market Intelligence Service for Real2.AI
Provides market trends, forecasting, and investment insights
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json
import statistics

from app.schema.property import (
    PropertyMarketData
)
from app.models.contract_state import AustralianState
from app.clients.factory import get_supabase_client
from app.services.unified_cache_service import UnifiedCacheService

logger = logging.getLogger(__name__)


class MarketIntelligenceService:
    """
    Market Intelligence Service providing comprehensive market analysis,
    trends forecasting, and investment opportunity identification.
    """
    
    def __init__(self):
        self.cache_service = UnifiedCacheService()
        self.db_client = None
        
    async def initialize(self):
        """Initialize service with database connection"""
        try:
            self.db_client = await get_supabase_client()
            logger.info("Market Intelligence Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Market Intelligence Service: {e}")
            raise
    
    async def get_market_trends(
        self,
        location: str,
        property_type: Optional[str] = None,
        time_horizon: str = "12_months"
    ) -> List[PropertyMarketTrends]:
        """
        Get comprehensive market trends for location
        """
        try:
            cache_key = f"market_trends:{location}:{property_type or 'all'}:{time_horizon}"
            cached_trends = await self.cache_service.get(cache_key)
            
            if cached_trends:
                return [PropertyMarketTrends.parse_obj(trend) for trend in cached_trends]
            
            # Parse location
            suburb, state = await self._parse_location(location)
            
            # Get historical market data
            historical_data = await self._get_historical_market_data(suburb, state, property_type)
            
            # Calculate trends and forecasts
            trends = await self._calculate_market_trends(historical_data, time_horizon)
            
            # Cache results for 2 hours
            await self.cache_service.set(
                cache_key, 
                [trend.dict() for trend in trends], 
                ttl=7200
            )
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get market trends for {location}: {e}", exc_info=True)
            raise
    
    async def get_market_insights(
        self,
        location: str,
        insight_types: List[str] = ["trends", "forecasts", "opportunities"],
        limit: int = 10
    ) -> List[PropertyMarketInsight]:
        """
        Generate market insights using AI analysis
        """
        try:
            cache_key = f"market_insights:{location}:{','.join(sorted(insight_types))}"
            cached_insights = await self.cache_service.get(cache_key)
            
            if cached_insights:
                return [PropertyMarketInsight.parse_obj(insight) for insight in cached_insights]
            
            # Generate insights based on market data and trends
            insights = []
            
            if "trends" in insight_types:
                trend_insights = await self._generate_trend_insights(location)
                insights.extend(trend_insights)
            
            if "forecasts" in insight_types:
                forecast_insights = await self._generate_forecast_insights(location)
                insights.extend(forecast_insights)
            
            if "opportunities" in insight_types:
                opportunity_insights = await self._generate_opportunity_insights(location)
                insights.extend(opportunity_insights)
            
            # Sort by impact level and limit results
            insights.sort(key=lambda x: self._impact_score(x.impact_level), reverse=True)
            insights = insights[:limit]
            
            # Cache for 4 hours
            await self.cache_service.set(
                cache_key,
                [insight.dict() for insight in insights],
                ttl=14400
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate market insights for {location}: {e}", exc_info=True)
            raise
    
    async def analyze_investment_opportunities(
        self,
        location: str,
        budget_range: Optional[Tuple[float, float]] = None,
        investment_strategy: str = "growth"
    ) -> Dict[str, Any]:
        """
        Identify and analyze investment opportunities in location
        """
        try:
            # Get market data and trends
            market_trends = await self.get_market_trends(location)
            
            # Get current listings and off-market opportunities
            opportunities = await self._identify_investment_opportunities(
                location, budget_range, investment_strategy
            )
            
            # Score and rank opportunities
            scored_opportunities = await self._score_investment_opportunities(
                opportunities, market_trends, investment_strategy
            )
            
            # Generate investment strategy recommendations
            strategy_recommendations = await self._generate_investment_strategy(
                location, market_trends, investment_strategy
            )
            
            return {
                "location": location,
                "analysis_date": datetime.now().isoformat(),
                "market_summary": {
                    "trend_direction": self._get_dominant_trend(market_trends),
                    "investment_attractiveness": self._calculate_investment_attractiveness(market_trends),
                    "risk_level": self._assess_market_risk_level(market_trends)
                },
                "opportunities": scored_opportunities,
                "strategy_recommendations": strategy_recommendations,
                "market_forecasts": await self._generate_market_forecasts(location)
            }
            
        except Exception as e:
            logger.error(f"Investment opportunity analysis failed for {location}: {e}", exc_info=True)
            raise
    
    async def get_comparative_market_analysis(
        self,
        locations: List[str],
        comparison_metrics: List[str] = ["growth", "yield", "risk", "liquidity"]
    ) -> Dict[str, Any]:
        """
        Compare multiple markets for investment decision making
        """
        try:
            comparison_data = {}
            
            # Get market data for each location
            for location in locations:
                market_trends = await self.get_market_trends(location)
                comparison_data[location] = await self._extract_comparison_metrics(
                    market_trends, comparison_metrics
                )
            
            # Generate comparative analysis
            analysis = await self._generate_comparative_analysis(comparison_data, comparison_metrics)
            
            # Rank locations by investment potential
            rankings = await self._rank_investment_locations(comparison_data, comparison_metrics)
            
            return {
                "comparison_date": datetime.now().isoformat(),
                "locations_compared": locations,
                "metrics_analyzed": comparison_metrics,
                "location_data": comparison_data,
                "comparative_analysis": analysis,
                "investment_rankings": rankings,
                "recommendations": await self._generate_location_recommendations(rankings)
            }
            
        except Exception as e:
            logger.error(f"Comparative market analysis failed: {e}", exc_info=True)
            raise
    
    async def predict_market_cycles(
        self,
        location: str,
        forecast_years: int = 5
    ) -> Dict[str, Any]:
        """
        Predict market cycles and optimal buy/sell timing
        """
        try:
            # Get long-term historical data
            historical_data = await self._get_long_term_market_data(location, years=20)
            
            # Identify historical cycles
            cycles = await self._identify_market_cycles(historical_data)
            
            # Current market position analysis
            current_position = await self._analyze_current_market_position(location, cycles)
            
            # Generate cycle-based forecasts
            cycle_forecasts = await self._forecast_market_cycles(cycles, forecast_years)
            
            # Generate timing recommendations
            timing_recommendations = await self._generate_timing_recommendations(
                current_position, cycle_forecasts
            )
            
            return {
                "location": location,
                "analysis_date": datetime.now().isoformat(),
                "historical_cycles": cycles,
                "current_market_position": current_position,
                "cycle_forecasts": cycle_forecasts,
                "timing_recommendations": timing_recommendations,
                "confidence_score": 0.75
            }
            
        except Exception as e:
            logger.error(f"Market cycle prediction failed for {location}: {e}", exc_info=True)
            raise
    
    # Private helper methods
    
    async def _parse_location(self, location: str) -> Tuple[str, str]:
        """Parse location string to suburb and state"""
        # Simple parsing - would be enhanced with geocoding service
        parts = location.split(",")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        return location.strip(), "NSW"  # Default to NSW
    
    async def _get_historical_market_data(
        self, 
        suburb: str, 
        state: str, 
        property_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical market data from database"""
        try:
            if self.db_client:
                query = self.db_client.table("property_market_data").select("*").eq("suburb", suburb).eq("state", state)
                
                if property_type:
                    # Would filter by property type in related properties
                    pass
                
                result = await query.execute()
                return result.data if result.data else []
            
            # Mock historical data
            return [
                {
                    "date": (datetime.now() - timedelta(days=i*30)).isoformat(),
                    "median_price": 750000 + i*5000,
                    "sales_volume": 45 + i*2,
                    "days_on_market": 25 + i,
                    "price_growth": 0.5 + i*0.1
                }
                for i in range(24)  # 24 months of data
            ]
            
        except Exception as e:
            logger.error(f"Failed to get historical market data: {e}")
            return []
    
    async def _calculate_market_trends(
        self, 
        historical_data: List[Dict[str, Any]], 
        time_horizon: str
    ) -> List[PropertyMarketTrends]:
        """Calculate market trends from historical data"""
        
        if not historical_data:
            return []
        
        # Mock trend calculation - would use actual statistical analysis
        return [PropertyMarketTrends(
            suburb="Parramatta",
            state="NSW",
            property_type="House",
            median_price_current=785000,
            median_price_12_months_ago=745000,
            price_change_percentage=5.37,
            price_volatility_score=35.2,
            market_activity_score=72.5,
            demand_supply_ratio=1.25,
            auction_clearance_rate=0.68,
            days_on_market_average=28,
            sales_volume_trend="increasing",
            market_segment_performance="outperforming",
            forecast_confidence=0.82
        )]
    
    async def _generate_trend_insights(self, location: str) -> List[PropertyMarketInsight]:
        """Generate trend-based market insights"""
        return [
            PropertyMarketInsight(
                insight_id=f"trend_{location}_{datetime.now().strftime('%Y%m%d')}",
                insight_type="trend",
                title="Strong Growth Momentum",
                description=f"{location} showing consistent price appreciation with increasing buyer activity",
                impact_level="high",
                affected_areas=[location],
                time_horizon="short_term",
                confidence_level="high",
                data_sources=["domain", "corelogic"],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30)
            )
        ]
    
    async def _generate_forecast_insights(self, location: str) -> List[PropertyMarketInsight]:
        """Generate forecast-based market insights"""
        return [
            PropertyMarketInsight(
                insight_id=f"forecast_{location}_{datetime.now().strftime('%Y%m%d')}",
                insight_type="forecast",
                title="Continued Growth Expected",
                description=f"Market forecasting 5-7% growth for {location} over next 12 months",
                impact_level="medium",
                affected_areas=[location],
                time_horizon="medium_term",
                confidence_level="high",
                data_sources=["predictive_model", "market_analysis"],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=90)
            )
        ]
    
    async def _generate_opportunity_insights(self, location: str) -> List[PropertyMarketInsight]:
        """Generate opportunity-based market insights"""
        return [
            PropertyMarketInsight(
                insight_id=f"opportunity_{location}_{datetime.now().strftime('%Y%m%d')}",
                insight_type="opportunity",
                title="Infrastructure Investment Impact",
                description=f"Upcoming transport projects expected to boost {location} property values by 10-15%",
                impact_level="high",
                affected_areas=[location],
                time_horizon="long_term",
                confidence_level="medium",
                data_sources=["government_data", "infrastructure_projects"],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=180)
            )
        ]
    
    def _impact_score(self, impact_level: str) -> int:
        """Convert impact level to numerical score for sorting"""
        scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return scores.get(impact_level, 1)
    
    async def _identify_investment_opportunities(
        self, 
        location: str, 
        budget_range: Optional[Tuple[float, float]], 
        strategy: str
    ) -> List[Dict[str, Any]]:
        """Identify investment opportunities based on criteria"""
        
        # Mock opportunity identification
        opportunities = [
            {
                "address": f"123 Investment Street, {location}",
                "price": 680000,
                "estimated_value": 720000,
                "opportunity_type": "undervalued",
                "investment_score": 8.5,
                "expected_return": 12.3
            },
            {
                "address": f"456 Growth Avenue, {location}",
                "price": 750000,
                "estimated_value": 785000,
                "opportunity_type": "growth_potential",
                "investment_score": 7.8,
                "expected_return": 9.8
            }
        ]
        
        # Filter by budget if specified
        if budget_range:
            min_budget, max_budget = budget_range
            opportunities = [
                opp for opp in opportunities 
                if min_budget <= opp["price"] <= max_budget
            ]
        
        return opportunities
    
    async def _score_investment_opportunities(
        self, 
        opportunities: List[Dict[str, Any]], 
        market_trends: List[PropertyMarketTrends], 
        strategy: str
    ) -> List[Dict[str, Any]]:
        """Score investment opportunities based on market trends and strategy"""
        
        for opportunity in opportunities:
            # Calculate composite score based on multiple factors
            base_score = opportunity.get("investment_score", 5.0)
            market_factor = 1.2 if market_trends and market_trends[0].sales_volume_trend == "increasing" else 1.0
            strategy_factor = 1.1 if strategy == "growth" and opportunity["opportunity_type"] == "growth_potential" else 1.0
            
            opportunity["composite_score"] = base_score * market_factor * strategy_factor
            opportunity["ranking"] = None  # Will be set after sorting
        
        # Sort by composite score
        opportunities.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Add rankings
        for i, opportunity in enumerate(opportunities):
            opportunity["ranking"] = i + 1
        
        return opportunities
    
    async def _generate_investment_strategy(
        self, 
        location: str, 
        market_trends: List[PropertyMarketTrends], 
        strategy: str
    ) -> List[str]:
        """Generate investment strategy recommendations"""
        
        recommendations = []
        
        if market_trends:
            trend = market_trends[0]
            
            if trend.price_change_percentage > 5:
                recommendations.append("Consider accelerating investment timeline due to strong price growth")
            
            if trend.days_on_market_average < 30:
                recommendations.append("Fast-moving market - be prepared to act quickly on good opportunities")
            
            if trend.auction_clearance_rate and trend.auction_clearance_rate > 0.7:
                recommendations.append("High auction clearance rates indicate strong buyer demand")
        
        # Strategy-specific recommendations
        if strategy == "growth":
            recommendations.append("Focus on areas with infrastructure development and population growth")
        elif strategy == "yield":
            recommendations.append("Target properties in high-rental-demand areas near employment centers")
        
        return recommendations
    
    async def _generate_market_forecasts(self, location: str) -> Dict[str, Any]:
        """Generate market forecasts for location"""
        
        return {
            "6_month_forecast": {
                "price_change_percentage": 2.8,
                "confidence": 0.85
            },
            "12_month_forecast": {
                "price_change_percentage": 6.2,
                "confidence": 0.78
            },
            "24_month_forecast": {
                "price_change_percentage": 13.5,
                "confidence": 0.65
            }
        }
    
    def _get_dominant_trend(self, market_trends: List[PropertyMarketTrends]) -> str:
        """Determine dominant market trend"""
        if not market_trends:
            return "stable"
        
        trend = market_trends[0]
        if trend.price_change_percentage > 5:
            return "strong_growth"
        elif trend.price_change_percentage > 0:
            return "moderate_growth"
        elif trend.price_change_percentage < -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_investment_attractiveness(self, market_trends: List[PropertyMarketTrends]) -> float:
        """Calculate overall investment attractiveness score (0-100)"""
        if not market_trends:
            return 50.0
        
        trend = market_trends[0]
        score = 50.0  # Base score
        
        # Price growth factor
        score += min(trend.price_change_percentage * 2, 20)
        
        # Market activity factor
        score += (trend.market_activity_score - 50) * 0.3
        
        # Volatility adjustment (lower volatility is better)
        score -= (trend.price_volatility_score - 30) * 0.2
        
        return max(0, min(100, score))
    
    def _assess_market_risk_level(self, market_trends: List[PropertyMarketTrends]) -> str:
        """Assess market risk level based on trends"""
        if not market_trends:
            return "medium"
        
        trend = market_trends[0]
        
        # High volatility or extreme price changes indicate higher risk
        if trend.price_volatility_score > 70 or abs(trend.price_change_percentage) > 15:
            return "high"
        elif trend.price_volatility_score < 30 and 0 <= trend.price_change_percentage <= 8:
            return "low"
        else:
            return "medium"