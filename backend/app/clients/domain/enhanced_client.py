"""
Enhanced Domain API client with caching and additional features.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .client import DomainClient
from .config import DomainClientConfig
from .cache import InMemoryCache, PropertyDataCache
from ..base.exceptions import ClientError, PropertyNotFoundError
from ...schema import (
    PropertyAddress,
    PropertyDetails,
    PropertyValuation,
    PropertyMarketData,
    PropertyRiskAssessment,
    ComparableSale,
    PropertySalesHistory,
    PropertyRentalHistory,
    PropertyProfile,
    PropertySearchRequest,
    PropertyProfileResponse,
    PropertyValuationRequest,
    PropertyValuationResponse,
    PropertySearchResponse,
)

logger = logging.getLogger(__name__)


class EnhancedDomainClient(DomainClient):
    """Enhanced Domain API client with caching and advanced features."""

    def __init__(self, config: DomainClientConfig):
        super().__init__(config)

        # Initialize caching if enabled
        self._cache: Optional[PropertyDataCache] = None
        if config.enable_caching:
            self._setup_caching()

        # Performance metrics
        self._metrics = {
            "requests_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_response_time": 0.0,
            "error_count": 0,
        }

    def _setup_caching(self) -> None:
        """Initialize caching system."""
        try:
            memory_cache = InMemoryCache(
                max_size_mb=100,  # 100MB cache
                default_ttl_seconds=self.config.cache_ttl_seconds,
                max_entries=10000,
            )

            self._cache = PropertyDataCache(
                cache=memory_cache,
                property_ttl=self.config.cache_ttl_seconds,
                market_data_ttl=self.config.market_data_cache_ttl,
                search_results_ttl=1800,  # 30 minutes for search results
                valuation_ttl=7200,  # 2 hours for valuations
            )

            logger.info("Property data caching initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize caching: {e}")
            self._cache = None

    async def get_property_profile(
        self, request: PropertySearchRequest
    ) -> PropertyProfileResponse:
        """Get comprehensive property profile with caching."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache first if enabled
            if self._cache and request.address:
                cached_profile = await self._cache.get_property_profile(request.address)
                if cached_profile and not request.force_refresh:
                    self._metrics["cache_hits"] += 1
                    logger.debug(f"Cache hit for property profile: {request.address}")

                    return PropertyProfileResponse(
                        property_profile=PropertyProfile(**cached_profile),
                        processing_time=asyncio.get_event_loop().time() - start_time,
                        data_freshness=cached_profile.get("data_freshness", {}),
                        api_usage={"cached": True},
                        cached_data=True,
                    )

            if self._cache:
                self._metrics["cache_misses"] += 1

            # Build comprehensive property profile
            profile_data = await self._build_property_profile(request)

            # Cache the result if caching is enabled
            if self._cache and request.address:
                await self._cache.cache_property_profile(request.address, profile_data)

            processing_time = asyncio.get_event_loop().time() - start_time
            self._metrics["requests_made"] += 1
            self._update_response_time(processing_time)

            return PropertyProfileResponse(
                property_profile=PropertyProfile(**profile_data),
                processing_time=processing_time,
                data_freshness=self._get_data_freshness_info(),
                api_usage=self._get_api_usage_info(),
                cached_data=False,
            )

        except Exception as e:
            self._metrics["error_count"] += 1
            logger.error(f"Property profile request failed: {e}")
            raise

    async def _build_property_profile(
        self, request: PropertySearchRequest
    ) -> Dict[str, Any]:
        """Build comprehensive property profile from multiple API calls."""
        profile_data = {
            "address": None,
            "property_details": None,
            "valuation": None,
            "market_data": None,
            "risk_assessment": None,
            "comparable_sales": [],
            "sales_history": [],
            "rental_history": [],
            "data_sources": ["domain"],
            "profile_created_at": datetime.now(timezone.utc),
            "profile_confidence": 0.0,
        }

        warnings = []

        try:
            # Step 1: Property search to get basic info
            if request.address:
                search_params = {
                    "address": request.address,
                    "listing_type": "Sale",
                    "page_size": 1,
                }

                search_results = await self.search_properties(search_params)

                if search_results.get("listings"):
                    property_listing = search_results["listings"][0]
                    profile_data["address"] = property_listing.get("address")
                    profile_data["property_details"] = property_listing.get(
                        "property_details"
                    )

                    property_id = property_listing.get("listing_id")

                    # Step 2: Get detailed property information
                    if property_id and request.include_valuation:
                        try:
                            detailed_info = await self.get_property_details(
                                str(property_id)
                            )
                            profile_data["property_details"].update(
                                detailed_info.get("property_details", {})
                            )
                        except Exception as e:
                            warnings.append(
                                f"Failed to get detailed property info: {str(e)}"
                            )

                    # Step 3: Get valuation if requested
                    if request.include_valuation:
                        try:
                            valuation_data = await self.get_property_valuation(
                                request.address
                            )
                            profile_data["valuation"] = valuation_data.get(
                                "valuations", {}
                            ).get("domain")
                        except Exception as e:
                            warnings.append(f"Valuation unavailable: {str(e)}")

                    # Step 4: Get market data if requested
                    if request.include_market_data and profile_data["address"]:
                        try:
                            location = {
                                "suburb": profile_data["address"]["suburb"],
                                "state": profile_data["address"]["state"],
                            }
                            market_data = await self.get_market_analytics(location)
                            profile_data["market_data"] = market_data
                        except Exception as e:
                            warnings.append(f"Market data unavailable: {str(e)}")

                    # Step 5: Get comparable sales if requested
                    if request.include_comparables and property_id:
                        try:
                            comparables = await self.get_comparable_sales(
                                str(property_id), radius_km=2.0
                            )
                            profile_data["comparable_sales"] = comparables.get(
                                "comparable_sales", []
                            )
                        except Exception as e:
                            warnings.append(f"Comparable sales unavailable: {str(e)}")

                    # Step 6: Get sales history if requested
                    if request.include_sales_history and property_id:
                        try:
                            sales_history = await self.get_sales_history(
                                str(property_id)
                            )
                            profile_data["sales_history"] = sales_history
                        except Exception as e:
                            warnings.append(f"Sales history unavailable: {str(e)}")

                    # Step 7: Get rental history if requested
                    if request.include_rental_history and property_id:
                        try:
                            rental_history = await self.get_rental_history(
                                str(property_id)
                            )
                            profile_data["rental_history"] = rental_history
                        except Exception as e:
                            warnings.append(f"Rental history unavailable: {str(e)}")

                    # Step 8: Assess risk if requested
                    if request.include_risk_assessment:
                        profile_data["risk_assessment"] = self._assess_property_risk(
                            profile_data
                        )

                else:
                    raise PropertyNotFoundError(request.address or "Unknown address")

        except PropertyNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error building property profile: {e}")
            raise ClientError(f"Failed to build property profile: {str(e)}")

        # Calculate overall confidence
        profile_data["profile_confidence"] = self._calculate_profile_confidence(
            profile_data
        )
        profile_data["warnings"] = warnings

        return profile_data

    def _assess_property_risk(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess property investment risk based on available data."""
        from ...schema import RiskLevel

        risk_factors = []
        overall_risk = RiskLevel.MEDIUM
        confidence = 0.6

        # Analyze market data for risk indicators
        market_data = profile_data.get("market_data")
        if market_data:
            # Price growth analysis
            price_growth = market_data.get("price_growth_12_month", 0)
            if price_growth < -5:
                risk_factors.append("Declining market prices")
                overall_risk = RiskLevel.HIGH
            elif price_growth > 15:
                risk_factors.append("Rapid price appreciation - bubble risk")
                overall_risk = RiskLevel.MEDIUM

            # Market activity analysis
            sales_volume = market_data.get("sales_volume_12_month", 0)
            if sales_volume < 10:
                risk_factors.append("Low market liquidity")

        # Analyze property details for risk
        property_details = profile_data.get("property_details")
        if property_details:
            year_built = property_details.get("year_built")
            if year_built and year_built < 1970:
                risk_factors.append("Older property - potential maintenance issues")

        # Analyze valuation confidence
        valuation = profile_data.get("valuation")
        if valuation:
            val_confidence = valuation.get("confidence", 0)
            if val_confidence < 0.6:
                risk_factors.append("Low valuation confidence")

        return {
            "overall_risk": overall_risk,
            "liquidity_risk": RiskLevel.MEDIUM,
            "market_risk": RiskLevel.MEDIUM,
            "structural_risk": RiskLevel.LOW,
            "risk_factors": risk_factors,
            "confidence": confidence,
            "risk_score": self._calculate_risk_score(risk_factors, overall_risk),
        }

    def _calculate_risk_score(
        self, risk_factors: List[str], overall_risk: RiskLevel
    ) -> float:
        """Calculate numerical risk score (0-100)."""
        base_score = {RiskLevel.LOW: 25, RiskLevel.MEDIUM: 50, RiskLevel.HIGH: 75}.get(
            overall_risk, 50
        )

        # Adjust based on number of risk factors
        factor_adjustment = len(risk_factors) * 5

        return min(100, base_score + factor_adjustment)

    def _calculate_profile_confidence(self, profile_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the property profile."""
        confidence_factors = []

        # Address confidence
        if profile_data.get("address"):
            confidence_factors.append(
                0.9 if profile_data["address"].get("latitude") else 0.7
            )

        # Property details confidence
        if profile_data.get("property_details"):
            details = profile_data["property_details"]
            detail_completeness = (
                sum(
                    [
                        1
                        for field in [
                            "bedrooms",
                            "bathrooms",
                            "property_type",
                            "land_area",
                        ]
                        if details.get(field) is not None
                    ]
                )
                / 4
            )
            confidence_factors.append(detail_completeness)

        # Valuation confidence
        if profile_data.get("valuation"):
            val_confidence = profile_data["valuation"].get("confidence", 0.5)
            confidence_factors.append(val_confidence)

        # Market data confidence
        if profile_data.get("market_data"):
            confidence_factors.append(0.8)

        # Calculate weighted average
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.3  # Low confidence if minimal data

    def _get_data_freshness_info(self) -> Dict[str, datetime]:
        """Get data freshness information."""
        current_time = datetime.now(timezone.utc)
        return {
            "property_details": current_time,
            "market_data": current_time,
            "valuations": current_time,
        }

    def _get_api_usage_info(self) -> Dict[str, int]:
        """Get API usage information."""
        return {"domain_api_calls": 1, "cached_responses": 0}

    def _update_response_time(self, response_time: float) -> None:
        """Update average response time metric."""
        current_avg = self._metrics["average_response_time"]
        total_requests = self._metrics["requests_made"]

        if total_requests > 1:
            self._metrics["average_response_time"] = (
                current_avg * (total_requests - 1) + response_time
            ) / total_requests
        else:
            self._metrics["average_response_time"] = response_time

    async def get_enhanced_valuation(
        self, request: PropertyValuationRequest
    ) -> PropertyValuationResponse:
        """Get enhanced property valuation with additional analysis."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache first
            if self._cache:
                cached_valuation = await self._cache.get_valuation(
                    request.address,
                    (
                        request.property_details.dict()
                        if request.property_details
                        else None
                    ),
                )
                if cached_valuation:
                    self._metrics["cache_hits"] += 1
                    return PropertyValuationResponse(**cached_valuation)

            if self._cache:
                self._metrics["cache_misses"] += 1

            # Get base valuation
            base_valuation = await self.get_property_valuation(
                request.address,
                request.property_details.dict() if request.property_details else None,
            )

            # Enhance with additional analysis
            enhanced_response = self._enhance_valuation_response(
                base_valuation, request
            )

            # Cache the result
            if self._cache:
                await self._cache.cache_valuation(
                    request.address,
                    request.property_details.dict() if request.property_details else {},
                    enhanced_response.dict(),
                )

            processing_time = asyncio.get_event_loop().time() - start_time
            enhanced_response.processing_time = processing_time

            self._metrics["requests_made"] += 1
            self._update_response_time(processing_time)

            return enhanced_response

        except Exception as e:
            self._metrics["error_count"] += 1
            logger.error(f"Enhanced valuation request failed: {e}")
            raise

    def _enhance_valuation_response(
        self, base_valuation: Dict[str, Any], request: PropertyValuationRequest
    ) -> PropertyValuationResponse:
        """Enhance basic valuation with additional insights."""
        # Add confidence bands and market context
        warnings = []

        # Analyze valuation confidence
        domain_valuation = base_valuation.get("valuations", {}).get("domain")
        if domain_valuation:
            confidence = domain_valuation.get("confidence", 0.5)
            if confidence < 0.6:
                warnings.append("Low valuation confidence - limited comparable data")
            elif confidence > 0.9:
                warnings.append(
                    "High confidence valuation based on strong comparable data"
                )

        # Add market context warnings
        if base_valuation.get("data_sources_used", []):
            if len(base_valuation["data_sources_used"]) == 1:
                warnings.append(
                    "Valuation based on single data source - consider additional validation"
                )

        enhanced_response = PropertyValuationResponse(
            address=base_valuation["address"],
            valuations=base_valuation["valuations"],
            processing_time=base_valuation.get("processing_time", 0.0),
            data_sources_used=base_valuation.get("data_sources_used", []),
            confidence_score=base_valuation.get("confidence_score", 0.5),
            warnings=warnings,
        )

        return enhanced_response

    async def warm_cache_for_suburb(
        self, suburb: str, state: str, property_types: List[str] = None
    ) -> Dict[str, Any]:
        """Warm cache for a suburb with common property searches."""
        if not self._cache:
            return {"error": "Caching not enabled"}

        return await self._cache.warm_cache_for_area(suburb, state, self)

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get caching and performance statistics."""
        cache_stats = {}
        if self._cache:
            cache_stats = await self._cache.get_cache_stats()

        return {
            "caching": cache_stats,
            "performance": self._metrics,
            "client_info": {
                "service_tier": self.config.service_tier,
                "rate_limiting": await self.get_rate_limit_status(),
            },
        }

    async def invalidate_property_cache(self, address: str) -> bool:
        """Invalidate cached data for a specific property."""
        if not self._cache:
            return False

        count = await self._cache.invalidate_property_data(address)
        logger.info(f"Invalidated {count} cache entries for property: {address}")
        return count > 0

    async def close(self) -> None:
        """Close client and clean up resources."""
        try:
            # Clear cache if present
            if self._cache:
                await self._cache.cache.clear()

            # Call parent close
            await super().close()

        except Exception as e:
            logger.error(f"Error closing enhanced Domain client: {e}")
            raise
