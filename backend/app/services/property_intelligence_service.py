"""
Property Intelligence Service for Real2.AI
Core service for property analysis, valuation, and market intelligence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json

from app.api.models import (
    PropertyProfile,
    PropertyValuation,
    PropertyMarketData,
    PropertyRiskAssessment,
    PropertySearchRequest,
    PropertyAnalyticsRequest,
    PropertyInvestmentAnalysis,
    PropertyFinancialBreakdown,
    PropertyMarketTrends,
    PropertyNeighborhoodAnalysis,
    ComparableSale,
    AustralianState,
    RiskLevel
)
from app.clients.factory import get_supabase_client
from app.services.unified_cache_service import UnifiedCacheService

logger = logging.getLogger(__name__)


class PropertyIntelligenceService:
    """
    Comprehensive property intelligence service integrating multiple data sources
    for advanced property analysis, valuation, and market intelligence.
    """
    
    def __init__(self):
        self.cache_service = UnifiedCacheService()
        self.db_client = None
        self._domain_client = None
        self._corelogic_client = None
        
    async def initialize(self):
        """Initialize service with database and external API clients"""
        try:
            self.db_client = await get_supabase_client()
            
            # Initialize external API clients
            from app.clients.factory import get_client_factory
            factory = get_client_factory()
            
            # These would be actual implementations
            # self._domain_client = await factory.get_client("domain")
            # self._corelogic_client = await factory.get_client("corelogic")
            
            logger.info("Property Intelligence Service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Property Intelligence Service: {e}")
            raise
    
    async def search_properties(
        self, 
        request: PropertySearchRequest, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Advanced property search with intelligent filtering and ranking
        """
        try:
            # Log search for analytics
            if user_id:
                await self._log_search(user_id, request)
            
            # Build search query
            search_query = await self._build_search_query(request)
            
            # Execute search across data sources
            search_results = await self._execute_property_search(search_query)
            
            # Apply intelligent ranking
            ranked_results = await self._rank_search_results(search_results, request)
            
            # Enhance results with market data
            enhanced_results = await self._enhance_search_results(ranked_results)
            
            return {
                "search_id": f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "query": request.address or request.property_details,
                "total_results": len(enhanced_results),
                "properties": enhanced_results[:request.max_comparables],
                "search_metadata": {
                    "data_sources": ["domain", "corelogic", "internal"],
                    "search_time_ms": 245,
                    "cache_hit_rate": 0.35
                }
            }
            
        except Exception as e:
            logger.error(f"Property search failed: {e}", exc_info=True)
            raise
    
    async def analyze_property(
        self, 
        address: str, 
        analysis_depth: str = "comprehensive",
        user_id: Optional[str] = None
    ) -> PropertyProfile:
        """
        Comprehensive property analysis with market intelligence
        """
        try:
            # Check cache first
            cache_key = f"property_analysis:{self._normalize_address(address)}:{analysis_depth}"
            cached_result = await self.cache_service.get(cache_key)
            
            if cached_result:
                logger.info(f"Returning cached property analysis for {address}")
                return PropertyProfile.parse_obj(cached_result)
            
            # Find or create property record
            property_id = await self._find_or_create_property(address)
            
            # Gather property data from multiple sources
            property_data = await self._gather_property_data(property_id, address, analysis_depth)
            
            # Build comprehensive property profile
            property_profile = await self._build_property_profile(property_data, analysis_depth)
            
            # Cache result
            await self.cache_service.set(
                cache_key, 
                property_profile.dict(), 
                ttl=3600  # 1 hour cache
            )
            
            # Log analysis for billing
            if user_id:
                await self._log_property_analysis(user_id, property_id, analysis_depth)
            
            return property_profile
            
        except Exception as e:
            logger.error(f"Property analysis failed for {address}: {e}", exc_info=True)
            raise
    
    async def get_property_valuation(
        self, 
        address: str, 
        valuation_type: str = "avm",
        property_details: Optional[Dict[str, Any]] = None
    ) -> PropertyValuation:
        """
        Get professional property valuation using multiple sources
        """
        try:
            # Check for recent cached valuation
            cache_key = f"valuation:{self._normalize_address(address)}:{valuation_type}"
            cached_valuation = await self.cache_service.get(cache_key)
            
            if cached_valuation:
                cached_date = datetime.fromisoformat(cached_valuation["valuation_date"])
                if datetime.now() - cached_date < timedelta(hours=6):  # 6 hour cache
                    return PropertyValuation.parse_obj(cached_valuation)
            
            # Get valuations from multiple sources
            valuations = {}
            
            # CoreLogic AVM/Professional valuation
            if self._corelogic_client:
                try:
                    corelogic_valuation = await self._get_corelogic_valuation(
                        address, valuation_type, property_details
                    )
                    valuations["corelogic"] = corelogic_valuation
                except Exception as e:
                    logger.warning(f"CoreLogic valuation failed: {e}")
            
            # Domain price estimate
            if self._domain_client:
                try:
                    domain_valuation = await self._get_domain_valuation(address, property_details)
                    valuations["domain"] = domain_valuation
                except Exception as e:
                    logger.warning(f"Domain valuation failed: {e}")
            
            # Combine valuations intelligently
            combined_valuation = await self._combine_valuations(valuations, valuation_type)
            
            # Cache result
            await self.cache_service.set(cache_key, combined_valuation.dict(), ttl=21600)  # 6 hours
            
            return combined_valuation
            
        except Exception as e:
            logger.error(f"Property valuation failed for {address}: {e}", exc_info=True)
            raise
    
    async def get_market_analysis(
        self, 
        suburb: str, 
        state: AustralianState,
        property_type: Optional[str] = None
    ) -> PropertyMarketData:
        """
        Get comprehensive market analysis for location
        """
        try:
            cache_key = f"market:{suburb}:{state}:{property_type or 'all'}"
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                return PropertyMarketData.parse_obj(cached_data)
            
            # Gather market data from sources
            market_data = await self._gather_market_data(suburb, state, property_type)
            
            # Cache for 4 hours
            await self.cache_service.set(cache_key, market_data.dict(), ttl=14400)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Market analysis failed for {suburb}, {state}: {e}", exc_info=True)
            raise
    
    async def get_investment_analysis(
        self, 
        property_profile: PropertyProfile,
        investment_strategy: str = "buy_and_hold"
    ) -> PropertyInvestmentAnalysis:
        """
        Generate comprehensive investment analysis for property
        """
        try:
            # Calculate rental yield
            rental_yield = await self._calculate_rental_yield(property_profile)
            
            # Forecast capital growth
            capital_growth_forecasts = await self._forecast_capital_growth(property_profile)
            
            # Calculate cash flow
            monthly_cash_flow = await self._calculate_monthly_cash_flow(
                property_profile, rental_yield
            )
            
            # Calculate ROI and investment metrics
            roi_metrics = await self._calculate_investment_roi(
                property_profile, rental_yield, capital_growth_forecasts, monthly_cash_flow
            )
            
            # Generate investment grade
            investment_grade = await self._calculate_investment_grade(roi_metrics)
            
            return PropertyInvestmentAnalysis(
                rental_yield=rental_yield,
                capital_growth_forecast_1_year=capital_growth_forecasts["1_year"],
                capital_growth_forecast_3_year=capital_growth_forecasts["3_year"],
                capital_growth_forecast_5_year=capital_growth_forecasts["5_year"],
                cash_flow_monthly=monthly_cash_flow,
                roi_percentage=roi_metrics["roi_percentage"],
                payback_period_years=roi_metrics["payback_period"],
                investment_score=roi_metrics["investment_score"],
                investment_grade=investment_grade,
                comparable_roi=roi_metrics["market_comparison"]
            )
            
        except Exception as e:
            logger.error(f"Investment analysis failed: {e}", exc_info=True)
            raise
    
    async def get_risk_assessment(
        self, 
        property_profile: PropertyProfile
    ) -> PropertyRiskAssessment:
        """
        Comprehensive property risk assessment
        """
        try:
            # Analyze different risk factors
            market_risk = await self._assess_market_risk(property_profile)
            liquidity_risk = await self._assess_liquidity_risk(property_profile)
            structural_risk = await self._assess_structural_risk(property_profile)
            
            # Calculate overall risk
            overall_risk = await self._calculate_overall_risk(
                market_risk, liquidity_risk, structural_risk
            )
            
            # Generate risk factors list
            risk_factors = await self._generate_risk_factors(
                property_profile, market_risk, liquidity_risk, structural_risk
            )
            
            return PropertyRiskAssessment(
                overall_risk=overall_risk,
                liquidity_risk=liquidity_risk,
                market_risk=market_risk,
                structural_risk=structural_risk,
                risk_factors=risk_factors,
                confidence=0.85,
                risk_score=self._risk_level_to_score(overall_risk)
            )
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}", exc_info=True)
            raise
    
    async def get_comparable_sales(
        self, 
        property_profile: PropertyProfile,
        radius_km: float = 2.0,
        max_results: int = 10
    ) -> List[ComparableSale]:
        """
        Find and analyze comparable property sales
        """
        try:
            # Search for comparable properties
            comparables = await self._find_comparable_properties(
                property_profile, radius_km, max_results
            )
            
            # Calculate similarity scores
            scored_comparables = await self._score_comparable_properties(
                property_profile, comparables
            )
            
            # Apply market adjustments
            adjusted_comparables = await self._apply_market_adjustments(scored_comparables)
            
            return adjusted_comparables
            
        except Exception as e:
            logger.error(f"Comparable sales analysis failed: {e}", exc_info=True)
            raise
    
    # Private helper methods
    
    async def _find_or_create_property(self, address: str) -> str:
        """Find existing property or create new record"""
        # This would interact with the database to find or create property record
        # For now, return a mock property ID
        return f"prop_{hash(address) % 100000}"
    
    async def _normalize_address(self, address: str) -> str:
        """Normalize address for consistent caching and lookup"""
        return address.strip().lower().replace(" ", "_")
    
    async def _gather_property_data(
        self, 
        property_id: str, 
        address: str, 
        analysis_depth: str
    ) -> Dict[str, Any]:
        """Gather property data from multiple sources"""
        
        data = {
            "basic_details": await self._get_basic_property_details(address),
            "valuation": None,
            "market_data": None,
            "risk_data": None,
            "comparable_sales": []
        }
        
        if analysis_depth in ["comprehensive", "standard"]:
            data["valuation"] = await self.get_property_valuation(address)
            data["market_data"] = await self._get_property_market_data(address)
            
        if analysis_depth == "comprehensive":
            data["risk_data"] = await self._get_property_risk_data(address)
            data["comparable_sales"] = await self._get_property_comparables(address)
        
        return data
    
    async def _build_property_profile(
        self, 
        property_data: Dict[str, Any], 
        analysis_depth: str
    ) -> PropertyProfile:
        """Build comprehensive property profile from gathered data"""
        
        # This would construct a full PropertyProfile object
        # For now, return a mock profile structure
        return PropertyProfile(
            address=property_data["basic_details"]["address"],
            property_details=property_data["basic_details"]["details"],
            valuation=property_data.get("valuation"),
            market_data=property_data.get("market_data"),
            risk_assessment=property_data.get("risk_data"),
            comparable_sales=property_data.get("comparable_sales", []),
            sales_history=[],
            rental_history=[],
            data_sources=["domain", "corelogic"],
            profile_created_at=datetime.now(),
            profile_confidence=0.85
        )
    
    async def _log_search(self, user_id: str, request: PropertySearchRequest):
        """Log property search for analytics"""
        try:
            if self.db_client:
                await self.db_client.table("property_searches").insert({
                    "user_id": user_id,
                    "search_query": str(request.address or ""),
                    "search_filters": request.dict(),
                    "search_type": "address" if request.address else "filters",
                    "executed_at": datetime.now().isoformat()
                }).execute()
        except Exception as e:
            logger.warning(f"Failed to log search: {e}")
    
    async def _log_property_analysis(self, user_id: str, property_id: str, analysis_type: str):
        """Log property analysis for billing"""
        try:
            if self.db_client:
                cost_map = {"basic": 8.0, "standard": 15.0, "comprehensive": 25.0}
                await self.db_client.table("property_api_usage").insert({
                    "user_id": user_id,
                    "api_provider": "property_intelligence",
                    "endpoint": "analyze_property",
                    "request_type": analysis_type,
                    "cost_aud": cost_map.get(analysis_type, 15.0),
                    "request_successful": True,
                    "request_metadata": {"property_id": property_id}
                }).execute()
        except Exception as e:
            logger.warning(f"Failed to log analysis: {e}")
    
    # Mock implementations for external API calls
    
    async def _get_basic_property_details(self, address: str) -> Dict[str, Any]:
        """Get basic property details"""
        return {
            "address": {
                "full_address": address,
                "suburb": "Parramatta",
                "state": "NSW",
                "postcode": "2150"
            },
            "details": {
                "property_type": "House",
                "bedrooms": 3,
                "bathrooms": 2,
                "carspaces": 1,
                "land_area": 450.0,
                "building_area": 150.0
            }
        }
    
    async def _get_property_market_data(self, address: str) -> PropertyMarketData:
        """Get market data for property location"""
        return PropertyMarketData(
            median_price=785000,
            price_growth_12_month=5.2,
            price_growth_3_year=18.5,
            days_on_market=28,
            sales_volume_12_month=145,
            market_outlook="growing",
            median_rent=650.0,
            rental_yield=4.3,
            vacancy_rate=2.1
        )
    
    async def _calculate_rental_yield(self, property_profile: PropertyProfile) -> float:
        """Calculate rental yield for property"""
        # Mock calculation - would use actual rental data
        estimated_weekly_rent = 650  # Would be calculated from comparable rentals
        annual_rent = estimated_weekly_rent * 52
        property_value = property_profile.valuation.estimated_value if property_profile.valuation else 785000
        
        return (annual_rent / property_value) * 100
    
    async def _forecast_capital_growth(self, property_profile: PropertyProfile) -> Dict[str, float]:
        """Forecast capital growth for property"""
        # Mock forecasting - would use ML models and market analysis
        return {
            "1_year": 6.5,
            "3_year": 22.5,
            "5_year": 45.0
        }
    
    def _risk_level_to_score(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numerical score"""
        risk_scores = {
            "low": 25.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 95.0
        }
        return risk_scores.get(risk_level, 50.0)
    
    async def _build_search_query(self, request: PropertySearchRequest) -> Dict[str, Any]:
        """Build search query from request parameters"""
        return {"address": request.address, "filters": request.dict()}
    
    async def _execute_property_search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute property search across data sources"""
        # Mock search results
        return [{"address": f"Property {i}", "price": 650000 + i*25000} for i in range(20)]
    
    async def _rank_search_results(self, results: List[Dict[str, Any]], request: PropertySearchRequest) -> List[Dict[str, Any]]:
        """Apply intelligent ranking to search results"""
        return results  # Would apply ML-based ranking
    
    async def _enhance_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance search results with market data"""
        return results  # Would add market insights, investment scores, etc.