"""
CoreLogic API client implementation for Real2.AI platform.
Specializes in property valuations, market analytics, and risk assessment.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import aiohttp

from ..base.client import BaseClient, with_retry
from ..base.interfaces import RealEstateAPIOperations
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientRateLimitError,
    PropertyNotFoundError,
    PropertyValuationError,
    InvalidPropertyAddressError,
)
from .config import CoreLogicClientConfig
from .rate_limiter import CoreLogicRateLimitManager

logger = logging.getLogger(__name__)


class CoreLogicAuthenticationError(ClientAuthenticationError):
    """CoreLogic-specific authentication error."""

    pass


class CoreLogicValuationError(PropertyValuationError):
    """CoreLogic-specific valuation error."""

    pass


class CoreLogicBudgetExceededError(ClientError):
    """Budget limit exceeded error."""

    pass


class CoreLogicClient(BaseClient, RealEstateAPIOperations):
    """CoreLogic API client for property valuation and analytics operations."""

    def __init__(self, config: CoreLogicClientConfig):
        super().__init__(config, "CoreLogicClient")
        self.config: CoreLogicClientConfig = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_manager: Optional[CoreLogicRateLimitManager] = None

        # Authentication state
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._auth_lock = asyncio.Lock()

        # Validate configuration
        self.config.validate_config()

        # Update URLs based on environment
        env_config = self.config.environment_config
        self.config.base_url = env_config["base_url"]
        self.config.auth_url = env_config["auth_url"]

    async def initialize(self) -> None:
        """Initialize the client connection (BaseClient interface)."""
        await self.connect()
        self._initialized = True

    async def close(self) -> None:
        """Close the client connection (BaseClient interface)."""
        await self.disconnect()
        self._initialized = False

    async def health_check(self) -> Dict[str, Any]:
        """Health check implementation (BaseClient interface)."""
        return await self.check_api_health()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize the client connection."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=self.config.connect_timeout,
                sock_read=self.config.read_timeout,
            )

            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=self.config.keep_alive_timeout,
            )

            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)

            self._rate_limit_manager = CoreLogicRateLimitManager(self.config)

            # Authenticate
            await self._ensure_authenticated()

            self.logger.info("CoreLogic client connected")

    async def disconnect(self) -> None:
        """Close the client connection."""
        if self._session:
            await self._session.close()
            self._session = None
            self._rate_limit_manager = None
            self.logger.info("CoreLogic client disconnected")

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        async with self._auth_lock:
            now = datetime.now(timezone.utc)

            # Check if token is still valid (with buffer for refresh)
            if (
                self._access_token
                and self._token_expires_at
                and self._token_expires_at
                > now + timedelta(seconds=self.config.token_refresh_threshold)
            ):
                return

            # Authenticate or refresh token
            await self._authenticate()

    async def _authenticate(self) -> None:
        """Authenticate with CoreLogic API and get access token."""
        auth_url = f"{self.config.auth_url}/oauth2/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": "property_api",
        }

        try:
            async with self._session.post(
                auth_url, headers=self.config.auth_headers, data=data
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    self._access_token = auth_data["access_token"]
                    expires_in = auth_data.get("expires_in", 3600)
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=expires_in
                    )

                    self.logger.info("CoreLogic authentication successful")
                else:
                    error_text = await response.text()
                    raise CoreLogicAuthenticationError(
                        f"Authentication failed: {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise ClientConnectionError(f"Authentication connection failed: {e}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        operation: str = "general",
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make an authenticated API request with rate limiting and cost tracking."""
        await self._ensure_authenticated()

        # Check rate limits and budget
        if not await self._rate_limit_manager.acquire_request_slot(
            operation, estimated_cost
        ):
            wait_time = await self._rate_limit_manager.wait_for_rate_limit_reset()
            if wait_time > 0:
                self.logger.info(f"Rate limited, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                # Try again after waiting
                if not await self._rate_limit_manager.acquire_request_slot(
                    operation, estimated_cost
                ):
                    raise ClientRateLimitError("Rate limit exceeded after waiting")

        url = f"{self.config.full_base_url}/{endpoint.lstrip('/')}"
        headers = self.config.get_api_headers(self._access_token)

        # Add custom headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        start_time = time.time()
        actual_cost = estimated_cost  # Default to estimated cost

        try:
            self.logger.debug(f"Making {method} request to {url}")

            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                request_duration = time.time() - start_time

                # Extract actual cost from response headers if available
                cost_header = response.headers.get("X-API-Cost")
                if cost_header:
                    try:
                        actual_cost = float(cost_header)
                    except ValueError:
                        pass

                if response.status == 200:
                    data = await response.json()

                    # Record successful request cost
                    await self._rate_limit_manager.record_request_cost(
                        operation, actual_cost
                    )

                    self.logger.debug(
                        f"Request successful ({request_duration:.2f}s, ${actual_cost:.2f})"
                    )
                    return data

                elif response.status == 401:
                    # Token might be expired, try to refresh
                    self._access_token = None
                    raise CoreLogicAuthenticationError("Authentication token expired")

                elif response.status == 429:
                    # Rate limited by API
                    retry_after = response.headers.get("Retry-After", "60")
                    raise ClientRateLimitError(
                        f"API rate limit exceeded, retry after {retry_after}s"
                    )

                elif response.status == 402:
                    # Payment required - budget exceeded
                    error_text = await response.text()
                    raise CoreLogicBudgetExceededError(f"Budget exceeded: {error_text}")

                elif response.status == 404:
                    raise PropertyNotFoundError("Property not found")

                else:
                    error_text = await response.text()
                    raise ClientError(
                        f"API request failed: {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            # Record failure for circuit breaker
            await self._rate_limit_manager.record_request_failure(operation, e)
            raise ClientConnectionError(f"Request failed: {e}")

    # RealEstateAPIOperations implementation

    async def search_properties(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for properties based on criteria.
        Note: CoreLogic focuses more on analytics than listings.
        """
        if not self.config.is_feature_enabled("comparable_sales"):
            raise ClientError("Property search not available in current tier")

        # CoreLogic's search is primarily for finding properties for analysis
        endpoint = "properties/search"
        estimated_cost = self.config.get_operation_cost("comparable_sales")

        # Transform search parameters for CoreLogic format
        corelogic_params = self._transform_search_params(search_params)

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                operation="property_search",
                estimated_cost=estimated_cost,
                json=corelogic_params,
            )

            return self._transform_search_response(response)

        except Exception as e:
            self.logger.error(f"Property search failed: {e}")
            raise

    async def get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific property."""
        endpoint = f"properties/{property_id}"
        estimated_cost = self.config.get_operation_cost("comparable_sales", 1)

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="property_details",
                estimated_cost=estimated_cost,
            )

            return self._transform_property_details(response)

        except Exception as e:
            self.logger.error(f"Get property details failed for {property_id}: {e}")
            raise

    @with_retry(max_retries=2, backoff_factor=3.0)
    async def get_property_valuation(
        self, address: str, property_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get property valuation estimate with enhanced validation and error handling.
        This is CoreLogic's primary strength.
        """
        if not property_details:
            property_details = {}

        # Enhanced address validation
        if not address or not address.strip():
            raise InvalidPropertyAddressError("Address cannot be empty")

        cleaned_address = self._clean_and_validate_address(address)

        valuation_type = property_details.get(
            "valuation_type", self.config.default_valuation_type
        )

        if not self.config.is_feature_enabled(
            f"{valuation_type}_valuation" if valuation_type != "avm" else "avm"
        ):
            raise ClientError(
                f"Valuation type '{valuation_type}' not available in current tier"
            )

        # Pre-validation: Check cost budget
        estimated_cost = self.config.get_operation_cost(f"{valuation_type}_valuation")
        if not await self._check_budget_availability(estimated_cost):
            raise CoreLogicBudgetExceededError(
                f"Insufficient budget for {valuation_type} valuation (${estimated_cost:.2f})"
            )

        endpoint = f"valuations/{valuation_type}"

        # Enhanced valuation request with validation
        valuation_request = self._build_valuation_request(
            cleaned_address, property_details, valuation_type
        )

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                operation=f"{valuation_type}_valuation",
                estimated_cost=estimated_cost,
                json=valuation_request,
                timeout=aiohttp.ClientTimeout(total=self.config.valuation_timeout),
            )

            # Enhanced validation of response
            validation_result = self._validate_valuation_response(
                response, valuation_type
            )
            if not validation_result["is_valid"]:
                raise CoreLogicValuationError(
                    f"Valuation response validation failed: {validation_result['reason']}"
                )

            # Transform and enhance response
            transformed_response = self._transform_valuation_response(
                response, valuation_type
            )

            # Add quality assessment
            transformed_response["quality_assessment"] = self._assess_valuation_quality(
                response, valuation_type
            )

            # Add cost tracking information
            transformed_response["cost_information"] = {
                "estimated_cost": estimated_cost,
                "actual_cost": response.get("api_cost", estimated_cost),
                "valuation_type": valuation_type,
                "service_tier": self.config.service_tier,
            }

            return transformed_response

        except CoreLogicValuationError:
            raise
        except CoreLogicBudgetExceededError:
            raise
        except Exception as e:
            self.logger.error(f"Property valuation failed for {address}: {e}")
            if isinstance(e, (ClientAuthenticationError, ClientRateLimitError)):
                raise
            raise CoreLogicValuationError(f"Valuation failed: {e}")

    async def get_market_analytics(
        self, location: Dict[str, str], property_type: str = None
    ) -> Dict[str, Any]:
        """Get market analytics for a location."""
        if not self.config.is_feature_enabled("market_analytics"):
            raise ClientError("Market analytics not available in current tier")

        endpoint = "analytics/market"
        estimated_cost = self.config.get_operation_cost("market_analytics")

        analytics_request = {
            "location": location,
            "property_type": property_type or "all",
            "analysis_period": "12_months",
            "include_forecasts": True,
        }

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                operation="market_analytics",
                estimated_cost=estimated_cost,
                json=analytics_request,
            )

            return self._transform_market_analytics(response)

        except Exception as e:
            self.logger.error(f"Market analytics failed for {location}: {e}")
            raise

    async def get_comparable_sales(
        self, property_id: str, radius_km: float = 2.0
    ) -> Dict[str, Any]:
        """Get comparable sales data for a property."""
        if not self.config.is_feature_enabled("comparable_sales"):
            raise ClientError("Comparable sales not available in current tier")

        endpoint = f"properties/{property_id}/comparables"
        estimated_cost = self.config.get_operation_cost("comparable_sales")

        params = {
            "radius_km": radius_km,
            "max_age_months": self.config.data_quality_settings[
                "max_comparable_age_months"
            ],
            "min_confidence": self.config.data_quality_settings["min_confidence_score"],
        }

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="comparable_sales",
                estimated_cost=estimated_cost,
                params=params,
            )

            return self._transform_comparable_sales(response)

        except Exception as e:
            self.logger.error(f"Comparable sales failed for {property_id}: {e}")
            raise

    async def get_sales_history(self, property_id: str) -> List[Dict[str, Any]]:
        """Get sales history for a property."""
        endpoint = f"properties/{property_id}/sales-history"
        estimated_cost = self.config.get_operation_cost("comparable_sales", 0.5)

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="sales_history",
                estimated_cost=estimated_cost,
            )

            return self._transform_sales_history(response)

        except Exception as e:
            self.logger.error(f"Sales history failed for {property_id}: {e}")
            raise

    async def get_rental_history(self, property_id: str) -> List[Dict[str, Any]]:
        """Get rental history for a property."""
        endpoint = f"properties/{property_id}/rental-history"
        estimated_cost = self.config.get_operation_cost("comparable_sales", 0.5)

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="rental_history",
                estimated_cost=estimated_cost,
            )

            return self._transform_rental_history(response)

        except Exception as e:
            self.logger.error(f"Rental history failed for {property_id}: {e}")
            raise

    async def get_suburb_demographics(self, suburb: str, state: str) -> Dict[str, Any]:
        """Get demographic information for a suburb."""
        if not self.config.is_feature_enabled("market_analytics"):
            raise ClientError("Demographics not available in current tier")

        endpoint = "analytics/demographics"
        estimated_cost = self.config.get_operation_cost("market_analytics", 0.5)

        params = {"suburb": suburb, "state": state, "include_forecasts": True}

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="demographics",
                estimated_cost=estimated_cost,
                params=params,
            )

            return self._transform_demographics(response)

        except Exception as e:
            self.logger.error(f"Demographics failed for {suburb}, {state}: {e}")
            raise

    # CoreLogic-specific methods

    async def get_property_risk_assessment(
        self, property_id: str, assessment_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get detailed risk assessment for a property."""
        if not self.config.is_feature_enabled("risk_assessment"):
            raise ClientError("Risk assessment not available in current tier")

        endpoint = f"properties/{property_id}/risk-assessment"
        estimated_cost = self.config.get_operation_cost("risk_assessment")

        params = {
            "assessment_type": assessment_type,
            "include_environmental": True,
            "include_market_risk": True,
        }

        try:
            response = await self._make_request(
                "GET",
                endpoint,
                operation="risk_assessment",
                estimated_cost=estimated_cost,
                params=params,
            )

            return self._transform_risk_assessment(response)

        except Exception as e:
            self.logger.error(f"Risk assessment failed for {property_id}: {e}")
            raise

    async def calculate_investment_yield(
        self, property_id: str, purchase_price: float, rental_income: float
    ) -> Dict[str, Any]:
        """Calculate investment yield and metrics."""
        if not self.config.is_feature_enabled("yield_analysis"):
            raise ClientError("Yield analysis not available in current tier")

        endpoint = f"properties/{property_id}/yield-analysis"
        estimated_cost = self.config.get_operation_cost("market_analytics", 0.8)

        analysis_request = {
            "purchase_price": purchase_price,
            "annual_rental_income": rental_income,
            "include_expenses": True,
            "include_tax_implications": True,
        }

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                operation="yield_analysis",
                estimated_cost=estimated_cost,
                json=analysis_request,
            )

            return self._transform_yield_analysis(response)

        except Exception as e:
            self.logger.error(f"Yield analysis failed for {property_id}: {e}")
            raise

    async def bulk_valuation(
        self, addresses: List[str], valuation_type: str = "avm"
    ) -> List[Dict[str, Any]]:
        """Perform bulk valuations for multiple addresses."""
        if not self.config.is_feature_enabled("bulk_operations"):
            raise ClientError("Bulk operations not available in current tier")

        # Split into batches
        batch_size = self.config.bulk_valuation_batch_size
        batches = [
            addresses[i : i + batch_size] for i in range(0, len(addresses), batch_size)
        ]

        all_results = []

        for batch in batches:
            endpoint = f"valuations/{valuation_type}/bulk"
            estimated_cost = self.config.get_operation_cost(
                "bulk_valuation", len(batch)
            )

            bulk_request = {"addresses": batch, "valuation_type": valuation_type}

            try:
                response = await self._make_request(
                    "POST",
                    endpoint,
                    operation="bulk_valuation",
                    estimated_cost=estimated_cost,
                    json=bulk_request,
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.valuation_timeout * 2
                    ),
                )

                batch_results = self._transform_bulk_valuation(response)
                all_results.extend(batch_results)

            except Exception as e:
                self.logger.error(f"Bulk valuation batch failed: {e}")
                # Continue with other batches
                continue

        return all_results

    async def generate_property_report(
        self, property_id: str, report_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Generate a comprehensive property report."""
        if not self.config.is_feature_enabled("custom_reports"):
            raise ClientError("Custom reports not available in current tier")

        endpoint = f"properties/{property_id}/reports/{report_type}"
        estimated_cost = self.config.get_operation_cost("professional_valuation", 2.0)

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                operation="property_report",
                estimated_cost=estimated_cost,
                json={"include_all_data": True},
            )

            return self._transform_property_report(response)

        except Exception as e:
            self.logger.error(
                f"Property report generation failed for {property_id}: {e}"
            )
            raise

    # Health and status methods

    async def check_api_health(self) -> Dict[str, Any]:
        """Check API health and rate limit status."""
        try:
            # Simple health check endpoint
            response = await self._make_request(
                "GET", "health", operation="health_check", estimated_cost=0.0
            )

            # Get rate limit status
            rate_limits = await self._rate_limit_manager.get_current_limits()
            cost_summary = self._rate_limit_manager.get_cost_summary()

            return {
                "status": "healthy",
                "api_response": response,
                "rate_limits": rate_limits,
                "cost_summary": cost_summary,
                "service_tier": self.config.service_tier,
                "environment": self.config.environment,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_tier": self.config.service_tier,
                "environment": self.config.environment,
            }

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        if self._rate_limit_manager:
            return await self._rate_limit_manager.get_current_limits()
        return {"error": "Rate limit manager not initialized"}

    async def get_cost_summary(self) -> Dict[str, Any]:
        """Get current cost and usage summary."""
        if self._rate_limit_manager:
            return self._rate_limit_manager.get_cost_summary()
        return {"error": "Rate limit manager not initialized"}

    # Helper methods for data transformation and validation

    def _clean_and_validate_address(self, address: str) -> str:
        """Clean and validate address for CoreLogic API requirements."""
        if not address:
            raise InvalidPropertyAddressError("Address cannot be empty")

        # Remove extra whitespace and normalize
        cleaned = " ".join(address.strip().split())

        # Australian address validation
        if len(cleaned) < 10:
            raise InvalidPropertyAddressError(
                "Address appears to be too short for a valid Australian address"
            )

        # Check for Australian state
        australian_states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
        has_state = any(state in cleaned.upper() for state in australian_states)

        if not has_state:
            self.logger.warning(
                f"Address '{cleaned}' does not contain a recognizable Australian state"
            )

        # Basic postcode validation (Australian postcodes are 4 digits)
        import re

        postcode_match = re.search(r"\b\d{4}\b", cleaned)
        if not postcode_match:
            self.logger.warning(
                f"Address '{cleaned}' does not contain a valid 4-digit postcode"
            )

        return cleaned

    def _build_valuation_request(
        self, address: str, property_details: Dict[str, Any], valuation_type: str
    ) -> Dict[str, Any]:
        """Build enhanced valuation request with validation."""
        request = {
            "address": address,
            "property_type": property_details.get("property_type", "house"),
            "valuation_type": valuation_type,
        }

        # Add optional property characteristics if provided
        if property_details.get("bedrooms") is not None:
            request["bedrooms"] = max(0, int(property_details["bedrooms"]))

        if property_details.get("bathrooms") is not None:
            request["bathrooms"] = max(0, float(property_details["bathrooms"]))

        if property_details.get("land_area") is not None:
            request["land_area"] = max(0, float(property_details["land_area"]))

        if property_details.get("building_area") is not None:
            request["building_area"] = max(0, float(property_details["building_area"]))

        if property_details.get("car_spaces") is not None:
            request["car_spaces"] = max(0, int(property_details["car_spaces"]))

        # Add features if provided
        features = property_details.get("features", [])
        if features and isinstance(features, list):
            request["additional_features"] = features

        # Add valuation preferences for professional valuations
        if valuation_type in ["desktop", "professional"]:
            request["valuation_preferences"] = {
                "include_comparable_analysis": True,
                "include_market_trends": True,
                "include_risk_assessment": property_details.get(
                    "include_risk_assessment", False
                ),
            }

        return request

    async def _check_budget_availability(self, estimated_cost: float) -> bool:
        """Check if budget is available for the requested operation."""
        if not self.config.cost_management["enable_cost_tracking"]:
            return True

        if not self._rate_limit_manager:
            return True

        cost_summary = self._rate_limit_manager.get_cost_summary()
        daily_spent = cost_summary.get("daily_spent", 0.0)
        monthly_spent = cost_summary.get("monthly_spent", 0.0)

        daily_limit = self.config.cost_management["daily_budget_limit"]
        monthly_limit = self.config.cost_management["monthly_budget_limit"]

        # Check if operation would exceed limits
        if daily_spent + estimated_cost > daily_limit:
            self.logger.warning(
                f"Operation would exceed daily budget limit: ${daily_spent + estimated_cost:.2f} > ${daily_limit:.2f}"
            )
            return False

        if monthly_spent + estimated_cost > monthly_limit:
            self.logger.warning(
                f"Operation would exceed monthly budget limit: ${monthly_spent + estimated_cost:.2f} > ${monthly_limit:.2f}"
            )
            return False

        return True

    def _assess_valuation_quality(
        self, response: Dict[str, Any], valuation_type: str
    ) -> Dict[str, Any]:
        """Assess the quality of the valuation response."""
        quality_factors = []
        overall_score = 0.0
        warnings = []

        # Confidence score assessment
        confidence = response.get("confidence_score", 0.0)
        if confidence >= 0.8:
            quality_factors.append(("high_confidence", 0.3))
        elif confidence >= 0.6:
            quality_factors.append(("medium_confidence", 0.2))
        else:
            quality_factors.append(("low_confidence", 0.1))
            warnings.append(f"Low confidence score: {confidence:.1%}")

        # Comparables assessment
        comparables_count = response.get("comparables_count", 0)
        if comparables_count >= 5:
            quality_factors.append(("sufficient_comparables", 0.25))
        elif comparables_count >= 3:
            quality_factors.append(("adequate_comparables", 0.15))
        else:
            quality_factors.append(("limited_comparables", 0.05))
            warnings.append(
                f"Limited comparable sales data: {comparables_count} comparables"
            )

        # Market data currency
        market_conditions = response.get("market_conditions", {})
        data_age_days = market_conditions.get("data_age_days", 0)
        if data_age_days <= 30:
            quality_factors.append(("current_market_data", 0.2))
        elif data_age_days <= 90:
            quality_factors.append(("recent_market_data", 0.15))
        else:
            quality_factors.append(("dated_market_data", 0.05))
            warnings.append(f"Market data is {data_age_days} days old")

        # Valuation type quality multiplier
        type_multipliers = {"avm": 0.7, "desktop": 0.85, "professional": 1.0}
        type_multiplier = type_multipliers.get(valuation_type, 0.7)

        # Calculate overall score
        base_score = sum(score for _, score in quality_factors)
        overall_score = min(1.0, base_score * type_multiplier)

        # Determine quality rating
        if overall_score >= 0.8:
            quality_rating = "high"
        elif overall_score >= 0.6:
            quality_rating = "medium"
        else:
            quality_rating = "low"
            warnings.append(
                "Overall valuation quality is low - consider additional validation"
            )

        return {
            "quality_score": round(overall_score, 2),
            "quality_rating": quality_rating,
            "confidence_score": confidence,
            "comparables_count": comparables_count,
            "market_data_age_days": data_age_days,
            "valuation_type": valuation_type,
            "quality_factors": [factor for factor, _ in quality_factors],
            "warnings": warnings,
        }

    def _transform_search_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Transform search parameters to CoreLogic format."""
        # CoreLogic uses different parameter names
        return {
            "location": {
                "suburb": params.get("suburb"),
                "state": params.get("state", self.config.default_state),
                "postcode": params.get("postcode"),
            },
            "property_types": params.get("property_types", ["house"]),
            "price_range": {
                "min": params.get("min_price"),
                "max": params.get("max_price"),
            },
            "bedrooms": {
                "min": params.get("min_bedrooms"),
                "max": params.get("max_bedrooms"),
            },
            "limit": min(params.get("limit", 50), 100),
        }

    def _transform_search_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic search response to standard format."""
        return {
            "total_results": response.get("total_count", 0),
            "results": [
                self._transform_property_listing(prop)
                for prop in response.get("properties", [])
            ],
            "search_metadata": {
                "provider": "corelogic",
                "search_time": response.get("search_time"),
                "data_freshness": response.get("data_date"),
            },
        }

    def _transform_property_listing(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic property listing to standard format."""
        return {
            "id": prop.get("property_id"),
            "address": prop.get("address"),
            "property_type": prop.get("property_type"),
            "bedrooms": prop.get("bedrooms"),
            "bathrooms": prop.get("bathrooms"),
            "land_area": prop.get("land_area_sqm"),
            "estimated_value": prop.get("estimated_value"),
            "confidence_score": prop.get("valuation_confidence"),
            "last_sale_date": prop.get("last_sale_date"),
            "last_sale_price": prop.get("last_sale_price"),
        }

    def _transform_property_details(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic property details to standard format."""
        return {
            "property_id": response.get("property_id"),
            "address": response.get("address"),
            "property_characteristics": {
                "property_type": response.get("property_type"),
                "bedrooms": response.get("bedrooms"),
                "bathrooms": response.get("bathrooms"),
                "parking_spaces": response.get("parking_spaces"),
                "land_area": response.get("land_area_sqm"),
                "building_area": response.get("building_area_sqm"),
            },
            "valuation_data": {
                "current_estimate": response.get("current_avm"),
                "confidence_score": response.get("confidence_score"),
                "estimate_date": response.get("estimate_date"),
            },
            "market_context": {
                "suburb_median": response.get("suburb_median"),
                "growth_rate": response.get("annual_growth_rate"),
            },
        }

    def _validate_valuation_response(
        self, response: Dict[str, Any], valuation_type: str = None
    ) -> Dict[str, Any]:
        """Enhanced validation of CoreLogic valuation response."""
        validation_result = {"is_valid": True, "reason": "", "warnings": []}

        # Check for valuation amount
        if not response.get("valuation_amount"):
            validation_result["is_valid"] = False
            validation_result["reason"] = "Missing valuation amount in response"
            return validation_result

        valuation_amount = response.get("valuation_amount", 0)
        if valuation_amount <= 0:
            validation_result["is_valid"] = False
            validation_result["reason"] = (
                f"Invalid valuation amount: {valuation_amount}"
            )
            return validation_result

        # Validate confidence score if required
        confidence = response.get("confidence_score", 0)
        min_confidence = self.config.data_quality_settings.get(
            "min_confidence_score", 0.6
        )

        if self.config.data_quality_settings.get("require_valuation_confidence", True):
            if confidence < min_confidence:
                validation_result["is_valid"] = False
                validation_result["reason"] = (
                    f"Confidence score {confidence:.1%} below minimum {min_confidence:.1%}"
                )
                return validation_result

        # Validate valuation range if present
        value_range = response.get("value_range", {})
        if value_range:
            range_low = value_range.get("low", 0)
            range_high = value_range.get("high", 0)

            if range_low > 0 and range_high > 0:
                if range_low >= range_high:
                    validation_result["warnings"].append(
                        "Invalid value range: low >= high"
                    )

                # Check if valuation is within reasonable range
                range_width = (range_high - range_low) / valuation_amount
                if range_width > 0.5:  # Range wider than 50% of valuation
                    validation_result["warnings"].append(
                        f"Wide valuation range: {range_width:.1%} of valuation"
                    )

        # Validate comparables data if present
        comparables_count = response.get("comparables_count", 0)
        min_comparables = self.config.data_quality_settings.get(
            "min_comparable_count", 3
        )

        if comparables_count < min_comparables:
            validation_result["warnings"].append(
                f"Limited comparable data: {comparables_count} < {min_comparables}"
            )

        # Validate market conditions data
        market_conditions = response.get("market_conditions", {})
        if market_conditions:
            data_age_days = market_conditions.get("data_age_days", 0)
            if data_age_days > 180:  # 6 months
                validation_result["warnings"].append(
                    f"Market data is {data_age_days} days old"
                )

        # Valuation type specific validation
        if valuation_type:
            if valuation_type in ["desktop", "professional"]:
                # Higher-tier valuations should have more detailed data
                if not response.get("methodology"):
                    validation_result["warnings"].append(
                        f"{valuation_type} valuation missing methodology details"
                    )

                if not response.get("risk_factors"):
                    validation_result["warnings"].append(
                        f"{valuation_type} valuation missing risk factor analysis"
                    )

        # Reasonable valuation amount validation (Australian property market)
        if valuation_amount < 50000:
            validation_result["warnings"].append(
                f"Unusually low valuation amount: ${valuation_amount:,.0f}"
            )
        elif valuation_amount > 50000000:  # $50M
            validation_result["warnings"].append(
                f"Unusually high valuation amount: ${valuation_amount:,.0f}"
            )

        return validation_result

    def _transform_valuation_response(
        self, response: Dict[str, Any], valuation_type: str
    ) -> Dict[str, Any]:
        """Transform CoreLogic valuation response to standard format."""
        return {
            "valuation_amount": response.get("valuation_amount"),
            "valuation_type": valuation_type,
            "confidence_score": response.get("confidence_score"),
            "valuation_date": response.get("valuation_date"),
            "methodology": response.get("methodology"),
            "comparables_used": response.get("comparables_count", 0),
            "value_range": {
                "low": response.get("value_range_low"),
                "high": response.get("value_range_high"),
            },
            "market_conditions": response.get("market_conditions"),
            "risk_factors": response.get("risk_factors", []),
            "provider_metadata": {
                "provider": "corelogic",
                "report_id": response.get("report_id"),
                "cost": response.get("api_cost"),
            },
        }

    def _transform_market_analytics(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic market analytics to standard format."""
        return {
            "location": response.get("location"),
            "market_metrics": {
                "median_price": response.get("median_price"),
                "price_growth_1yr": response.get("price_growth_12m"),
                "price_growth_5yr": response.get("price_growth_5y"),
                "sales_volume": response.get("sales_volume"),
                "days_on_market": response.get("average_days_on_market"),
            },
            "market_forecasts": response.get("forecasts", {}),
            "risk_indicators": response.get("risk_metrics", {}),
            "data_quality": {
                "confidence": response.get("data_confidence"),
                "sample_size": response.get("sample_size"),
                "data_date": response.get("data_date"),
            },
        }

    def _transform_comparable_sales(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic comparable sales to standard format."""
        return {
            "comparable_count": len(response.get("comparables", [])),
            "comparables": [
                {
                    "address": comp.get("address"),
                    "sale_price": comp.get("sale_price"),
                    "sale_date": comp.get("sale_date"),
                    "property_type": comp.get("property_type"),
                    "similarity_score": comp.get("similarity_score"),
                    "distance_km": comp.get("distance_km"),
                }
                for comp in response.get("comparables", [])
            ],
            "analysis_summary": {
                "median_price": response.get("median_comparable_price"),
                "price_range": response.get("price_range"),
                "average_similarity": response.get("average_similarity_score"),
            },
        }

    def _transform_sales_history(
        self, response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform CoreLogic sales history to standard format."""
        return [
            {
                "sale_date": sale.get("sale_date"),
                "sale_price": sale.get("sale_price"),
                "sale_type": sale.get("sale_type"),
                "days_on_market": sale.get("days_on_market"),
                "agent": sale.get("selling_agent"),
            }
            for sale in response.get("sales", [])
        ]

    def _transform_rental_history(
        self, response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform CoreLogic rental history to standard format."""
        return [
            {
                "lease_start": rental.get("lease_start_date"),
                "lease_end": rental.get("lease_end_date"),
                "weekly_rent": rental.get("weekly_rent"),
                "lease_type": rental.get("lease_type"),
                "yield": rental.get("rental_yield"),
            }
            for rental in response.get("rentals", [])
        ]

    def _transform_demographics(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic demographics to standard format."""
        return {
            "location": response.get("location"),
            "population": response.get("population_data", {}),
            "housing": response.get("housing_data", {}),
            "economic": response.get("economic_data", {}),
            "lifestyle": response.get("lifestyle_indicators", {}),
            "trends": response.get("demographic_trends", {}),
        }

    def _transform_risk_assessment(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic risk assessment to standard format."""
        return {
            "overall_risk_score": response.get("overall_risk_score"),
            "risk_level": response.get("risk_level"),
            "risk_factors": {
                "market_risk": response.get("market_risk", {}),
                "environmental_risk": response.get("environmental_risk", {}),
                "structural_risk": response.get("structural_risk", {}),
                "location_risk": response.get("location_risk", {}),
            },
            "recommendations": response.get("risk_mitigation_recommendations", []),
            "assessment_date": response.get("assessment_date"),
        }

    def _transform_yield_analysis(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic yield analysis to standard format."""
        return {
            "gross_yield": response.get("gross_rental_yield"),
            "net_yield": response.get("net_rental_yield"),
            "cash_flow": response.get("annual_cash_flow"),
            "roi_metrics": {
                "cap_rate": response.get("capitalization_rate"),
                "total_return": response.get("total_return_projection"),
                "payback_period": response.get("payback_period_years"),
            },
            "expense_breakdown": response.get("expense_analysis", {}),
            "tax_implications": response.get("tax_analysis", {}),
        }

    def _transform_bulk_valuation(
        self, response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform CoreLogic bulk valuation response to standard format."""
        return [
            {
                "address": val.get("address"),
                "valuation_amount": val.get("valuation_amount"),
                "confidence_score": val.get("confidence_score"),
                "status": val.get("valuation_status"),
                "error": val.get("error_message"),
            }
            for val in response.get("valuations", [])
        ]

    def _transform_property_report(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CoreLogic property report to standard format."""
        return {
            "report_id": response.get("report_id"),
            "property_summary": response.get("property_summary", {}),
            "valuation_details": response.get("valuation_analysis", {}),
            "market_analysis": response.get("market_context", {}),
            "risk_assessment": response.get("risk_evaluation", {}),
            "investment_analysis": response.get("investment_metrics", {}),
            "report_url": response.get("report_download_url"),
            "generation_cost": response.get("report_cost"),
        }
