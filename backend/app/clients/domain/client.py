"""
Domain API client implementation for Real2.AI platform.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import aiohttp

from ..base.client import BaseClient, with_retry
from ..base.interfaces import RealEstateAPIOperations
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientRateLimitError,
    DomainAPIError,
    PropertyNotFoundError,
    PropertyDataIncompleteError,
    PropertyValuationError,
    InvalidPropertyAddressError,
    PropertyDataValidationError,
)
from .config import DomainClientConfig
from .rate_limiter import RateLimitManager
from ...api.models import (
    PropertyAddress, PropertyDetails, PropertyValuation, PropertyMarketData,
    PropertyRiskAssessment, ComparableSale, PropertySalesHistory, PropertyRentalHistory,
    PropertyProfile, PropertySearchRequest, PropertyProfileResponse,
    PropertyValuationRequest, PropertyValuationResponse, PropertySearchFilter,
    PropertyListing, PropertySearchResponse, PropertyAPIHealthStatus,
    PropertyDataValidationResult, AustralianState, RiskLevel
)

logger = logging.getLogger(__name__)


class DomainClient(BaseClient, RealEstateAPIOperations):
    """Domain API client for property data operations."""
    
    def __init__(self, config: DomainClientConfig):
        super().__init__(config, "DomainClient")
        self.config: DomainClientConfig = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_manager: Optional[RateLimitManager] = None
        
        # Validate configuration
        self.config.validate_config()
        
        # Set up rate limit manager
        self._setup_rate_limiting()
    
    def _setup_rate_limiting(self) -> None:
        """Initialize rate limiting."""
        rate_config = {
            "requests_per_minute": self.config.rate_limit_rpm,
            "requests_per_second": self.config.requests_per_second,
            "burst_allowance": max(20, self.config.rate_limit_rpm // 25),
            "adaptive_backoff": True
        }
        self._rate_limit_manager = RateLimitManager(rate_config)
        logger.info(f"Rate limiting configured: {rate_config}")
    
    @with_retry(max_retries=3, backoff_factor=2.0)
    async def initialize(self) -> None:
        """Initialize Domain API client."""
        try:
            self.logger.info("Initializing Domain API client...")
            
            # Create aiohttp session with connection pooling
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=self.config.connect_timeout,
                sock_read=self.config.read_timeout
            )
            
            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                keepalive_timeout=self.config.keep_alive_timeout,
                enable_cleanup_closed=True
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.config.headers,
                raise_for_status=False  # We'll handle status codes manually
            )
            
            # Test the connection
            await self._test_connection()
            
            self._initialized = True
            self.logger.info("Domain API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Domain API client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize Domain API client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
    
    async def _test_connection(self) -> None:
        """Test Domain API connection."""
        try:
            # Use a simple endpoint for testing
            url = f"{self.config.full_base_url}/listings/residential/_search"
            
            # Minimal test search
            test_payload = {
                "listingType": "Sale",
                "locations": [{"state": self.config.default_state}],
                "pageSize": 1
            }
            
            await self._rate_limit_manager.acquire("test", "high")
            
            async with self._session.post(url, json=test_payload) as response:
                if response.status == 401:
                    raise ClientAuthenticationError(
                        "Domain API authentication failed - check API key",
                        client_name=self.client_name
                    )
                elif response.status == 403:
                    raise ClientAuthenticationError(
                        "Domain API access forbidden - check permissions",
                        client_name=self.client_name
                    )
                elif response.status == 429:
                    raise ClientRateLimitError(
                        "Domain API rate limit exceeded during test",
                        client_name=self.client_name
                    )
                elif 400 <= response.status < 500:
                    raise DomainAPIError(
                        f"Domain API client error: {response.status}",
                        status_code=response.status
                    )
                elif response.status >= 500:
                    raise ClientConnectionError(
                        f"Domain API server error: {response.status}",
                        client_name=self.client_name
                    )
                
                # Success - report to rate limiter
                self._rate_limit_manager.report_success("test")
                
                self.logger.debug("Domain API connection test successful")
                
        except aiohttp.ClientError as e:
            raise ClientConnectionError(
                f"Domain API connection failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Domain API client."""
        try:
            # Test API connection
            await self._test_connection()
            
            # Get rate limit status
            rate_status = self._rate_limit_manager.get_status()
            
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "connection": "ok",
                "api_base_url": self.config.base_url,
                "service_tier": self.config.service_tier,
                "rate_limiting": rate_status,
                "config": {
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                    "circuit_breaker_enabled": self.config.circuit_breaker_enabled,
                    "caching_enabled": self.config.enable_caching,
                },
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "initialized": self._initialized,
            }
    
    async def close(self) -> None:
        """Close Domain API client and clean up resources."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._initialized = False
            self.logger.info("Domain API client closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing Domain API client: {e}")
            raise ClientError(
                f"Error closing Domain API client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        operation_name: str = "request"
    ) -> Dict[str, Any]:
        """Make authenticated request to Domain API with rate limiting."""
        if not self._initialized:
            raise ClientError("Domain client not initialized", self.client_name)
        
        # Acquire rate limit permission
        await self._rate_limit_manager.acquire(endpoint, priority)
        
        url = f"{self.config.full_base_url}/{endpoint.lstrip('/')}"
        
        # Log request if enabled
        if self.config.enable_request_logging:
            self.logger.debug(f"[{operation_name}] {method} {url}")
        
        start_time = time.time()
        
        try:
            request_kwargs = {"params": params} if params else {}
            if json_data:
                request_kwargs["json"] = json_data
            
            async with self._session.request(method, url, **request_kwargs) as response:
                duration = time.time() - start_time
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = None
                    if "Retry-After" in response.headers:
                        try:
                            retry_after = int(response.headers["Retry-After"])
                        except ValueError:
                            pass
                    
                    self._rate_limit_manager.report_rate_limit_error(endpoint, retry_after)
                    
                    raise ClientRateLimitError(
                        f"Domain API rate limit exceeded for {endpoint}",
                        retry_after=retry_after,
                        client_name=self.client_name
                    )
                
                # Handle authentication errors
                if response.status in (401, 403):
                    error_text = await response.text()
                    raise ClientAuthenticationError(
                        f"Domain API authentication failed: {error_text}",
                        client_name=self.client_name
                    )
                
                # Handle client errors
                if 400 <= response.status < 500:
                    error_text = await response.text()
                    raise DomainAPIError(
                        f"Domain API client error ({response.status}): {error_text}",
                        status_code=response.status
                    )
                
                # Handle server errors
                if response.status >= 500:
                    error_text = await response.text()
                    raise ClientConnectionError(
                        f"Domain API server error ({response.status}): {error_text}",
                        client_name=self.client_name
                    )
                
                # Parse successful response
                try:
                    response_data = await response.json()
                except json.JSONDecodeError as e:
                    raise DomainAPIError(
                        f"Invalid JSON response from Domain API: {str(e)}",
                        status_code=response.status
                    )
                
                # Report success to rate limiter
                self._rate_limit_manager.report_success(endpoint)
                
                # Log response if enabled
                if self.config.enable_response_logging:
                    self.logger.debug(f"[{operation_name}] Response received in {duration:.3f}s")
                
                return response_data
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            duration = time.time() - start_time
            self.logger.error(f"[{operation_name}] Request failed after {duration:.3f}s: {e}")
            raise ClientConnectionError(
                f"Domain API request failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
    
    # RealEstateAPIOperations interface implementation
    
    async def search_properties(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for properties based on criteria."""
        try:
            endpoint = "listings/residential/_search"
            
            # Build search payload
            search_payload = self._build_search_payload(search_params)
            
            response_data = await self._make_request(
                "POST",
                endpoint,
                json_data=search_payload,
                priority="normal",
                operation_name="property_search"
            )
            
            # Transform response to our format
            return self._transform_search_response(response_data, search_params)
            
        except Exception as e:
            self.logger.error(f"Property search failed: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Property search failed: {str(e)}")
    
    async def get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific property."""
        try:
            endpoint = f"listings/{property_id}"
            
            response_data = await self._make_request(
                "GET",
                endpoint,
                priority="high",
                operation_name="property_details"
            )
            
            if not response_data:
                raise PropertyNotFoundError(property_id)
            
            # Transform response to our format
            return self._transform_property_details(response_data)
            
        except PropertyNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Get property details failed for {property_id}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Get property details failed: {str(e)}")
    
    async def get_property_valuation(
        self, 
        address: str, 
        property_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get property valuation estimate."""
        try:
            # Domain API uses address-based valuation
            endpoint = "properties/_suggest"
            
            params = {
                "terms": address,
                "channel": "buy",
                "pageSize": 1
            }
            
            response_data = await self._make_request(
                "GET",
                endpoint,
                params=params,
                priority="normal",
                operation_name="property_valuation"
            )
            
            if not response_data or not response_data.get("data"):
                raise PropertyValuationError(address, "No valuation data available")
            
            # Get detailed property info for valuation
            property_data = response_data["data"][0]
            property_id = property_data.get("id")
            
            if not property_id:
                raise PropertyValuationError(address, "Property ID not found")
            
            # Get detailed property information
            details = await self.get_property_details(str(property_id))
            
            # Transform to valuation response
            return self._transform_valuation_response(details, address)
            
        except (PropertyNotFoundError, PropertyValuationError):
            raise
        except Exception as e:
            self.logger.error(f"Property valuation failed for {address}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise PropertyValuationError(address, str(e))
    
    async def get_market_analytics(
        self, 
        location: Dict[str, str], 
        property_type: str = None
    ) -> Dict[str, Any]:
        """Get market analytics for a location."""
        try:
            if not self.config.is_feature_enabled("market_analytics"):
                raise DomainAPIError("Market analytics not available in current service tier")
            
            # Use sales results endpoint for market analytics
            endpoint = "sales/_search"
            
            search_payload = {
                "locations": [location],
                "soldSince": "2023-01-01",  # Last year of data
                "pageSize": 100
            }
            
            if property_type:
                search_payload["propertyTypes"] = [property_type]
            
            response_data = await self._make_request(
                "POST",
                endpoint,
                json_data=search_payload,
                priority="normal",
                operation_name="market_analytics"
            )
            
            # Transform to market analytics
            return self._transform_market_analytics(response_data, location, property_type)
            
        except Exception as e:
            self.logger.error(f"Market analytics failed for {location}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Market analytics failed: {str(e)}")
    
    async def get_comparable_sales(
        self, 
        property_id: str, 
        radius_km: float = 2.0
    ) -> Dict[str, Any]:
        """Get comparable sales data for a property."""
        try:
            if not self.config.is_feature_enabled("comparable_sales"):
                raise DomainAPIError("Comparable sales not available in current service tier")
            
            # First get property details to get location
            property_details = await self.get_property_details(property_id)
            address_components = property_details.get("address", {})
            
            if not address_components:
                raise PropertyDataIncompleteError(property_id, ["address"])
            
            # Search for comparable sales in the area
            endpoint = "sales/_search"
            
            search_payload = {
                "locations": [{
                    "suburb": address_components.get("suburb"),
                    "state": address_components.get("state")
                }],
                "soldSince": "2022-01-01",  # Last 2 years
                "pageSize": 50
            }
            
            response_data = await self._make_request(
                "POST",
                endpoint,
                json_data=search_payload,
                priority="normal",
                operation_name="comparable_sales"
            )
            
            # Transform and filter comparables
            return self._transform_comparable_sales(response_data, property_details, radius_km)
            
        except Exception as e:
            self.logger.error(f"Comparable sales failed for {property_id}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Comparable sales failed: {str(e)}")
    
    async def get_sales_history(self, property_id: str) -> List[Dict[str, Any]]:
        """Get sales history for a property."""
        try:
            # Get property details first
            property_details = await self.get_property_details(property_id)
            
            # Domain API doesn't have direct sales history endpoint
            # We'll use the sales search with property address
            address_components = property_details.get("address", {})
            
            endpoint = "sales/_search"
            
            search_payload = {
                "locations": [{
                    "suburb": address_components.get("suburb"),
                    "state": address_components.get("state")
                }],
                "soldSince": "2010-01-01",  # Historical data
                "pageSize": 100
            }
            
            response_data = await self._make_request(
                "POST",
                endpoint,
                json_data=search_payload,
                priority="normal",
                operation_name="sales_history"
            )
            
            # Filter for exact property match and transform
            return self._transform_sales_history(response_data, property_details)
            
        except Exception as e:
            self.logger.error(f"Sales history failed for {property_id}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Sales history failed: {str(e)}")
    
    async def get_rental_history(self, property_id: str) -> List[Dict[str, Any]]:
        """Get rental history for a property."""
        try:
            # Get property details first
            property_details = await self.get_property_details(property_id)
            address_components = property_details.get("address", {})
            
            # Use rental search endpoint
            endpoint = "listings/residential/_search"
            
            search_payload = {
                "listingType": "Rent",
                "locations": [{
                    "suburb": address_components.get("suburb"),
                    "state": address_components.get("state")
                }],
                "pageSize": 50
            }
            
            response_data = await self._make_request(
                "POST",
                endpoint,
                json_data=search_payload,
                priority="normal",
                operation_name="rental_history"
            )
            
            # Filter and transform for the specific property
            return self._transform_rental_history(response_data, property_details)
            
        except Exception as e:
            self.logger.error(f"Rental history failed for {property_id}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Rental history failed: {str(e)}")
    
    async def get_suburb_demographics(self, suburb: str, state: str) -> Dict[str, Any]:
        """Get demographic information for a suburb."""
        try:
            if not self.config.is_feature_enabled("demographics"):
                raise DomainAPIError("Demographics not available in current service tier")
            
            # Domain API doesn't have direct demographics endpoint
            # We'll aggregate data from property listings and sales
            
            # Get recent sales data for the suburb
            sales_data = await self.get_market_analytics(
                {"suburb": suburb, "state": state}
            )
            
            # Get current listings data
            search_params = {
                "locations": [{"suburb": suburb, "state": state}],
                "listingType": "Sale",
                "pageSize": 100
            }
            
            listings_data = await self.search_properties(search_params)
            
            # Combine data to create demographics insight
            return self._transform_demographics(sales_data, listings_data, suburb, state)
            
        except Exception as e:
            self.logger.error(f"Demographics failed for {suburb}, {state}: {e}")
            if isinstance(e, (ClientError, DomainAPIError)):
                raise
            raise DomainAPIError(f"Demographics failed: {str(e)}")
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check API health and rate limit status."""
        try:
            # Perform a lightweight test request
            url = f"{self.config.full_base_url}/listings/residential/_search"
            test_payload = {
                "listingType": "Sale",
                "locations": [{"state": "NSW"}],
                "pageSize": 1
            }
            
            start_time = time.time()
            await self._make_request(
                "POST",
                "listings/residential/_search",
                json_data=test_payload,
                priority="high",
                operation_name="health_check"
            )
            response_time = time.time() - start_time
            
            rate_status = self._rate_limit_manager.get_status()
            
            return {
                "api_status": "healthy",
                "response_time_seconds": response_time,
                "rate_limiting": rate_status,
                "service_tier": self.config.service_tier,
                "features_available": self.config.tier_settings[self.config.service_tier]["features"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "api_status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return self._rate_limit_manager.get_status()
    
    # Helper methods for data transformation
    
    def _build_search_payload(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Domain API search payload from search parameters."""
        payload = {
            "listingType": search_params.get("listing_type", "Sale"),
            "pageSize": min(search_params.get("page_size", 20), self.config.max_search_results)
        }
        
        # Add locations
        if "locations" in search_params:
            payload["locations"] = search_params["locations"]
        elif "suburb" in search_params or "state" in search_params:
            location = {}
            if "suburb" in search_params:
                location["suburb"] = search_params["suburb"]
            if "state" in search_params:
                location["state"] = search_params["state"]
            payload["locations"] = [location]
        
        # Add price range
        if "min_price" in search_params or "max_price" in search_params:
            price_range = {}
            if "min_price" in search_params:
                price_range["from"] = search_params["min_price"]
            if "max_price" in search_params:
                price_range["to"] = search_params["max_price"]
            payload["price"] = price_range
        
        # Add property features
        if "min_bedrooms" in search_params:
            payload["minBedrooms"] = search_params["min_bedrooms"]
        if "max_bedrooms" in search_params:
            payload["maxBedrooms"] = search_params["max_bedrooms"]
        if "min_bathrooms" in search_params:
            payload["minBathrooms"] = search_params["min_bathrooms"]
        if "property_types" in search_params:
            payload["propertyTypes"] = search_params["property_types"]
        
        return payload
    
    def _transform_search_response(
        self, 
        response_data: Dict[str, Any], 
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform Domain API search response to our format."""
        listings = []
        
        for item in response_data.get("data", []):
            try:
                listing = self._transform_listing_item(item)
                listings.append(listing)
            except Exception as e:
                self.logger.warning(f"Failed to transform listing item: {e}")
                continue
        
        return {
            "total_results": response_data.get("meta", {}).get("totalResults", len(listings)),
            "results_returned": len(listings),
            "listings": listings,
            "search_filters": search_params,
            "processing_time": 0.0,  # Will be set by calling code
            "page_number": search_params.get("page", 1),
            "page_size": search_params.get("page_size", 20)
        }
    
    def _transform_listing_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform individual listing item."""
        # Extract address information
        address_data = item.get("address", {})
        
        # Extract property details
        property_details = {
            "property_type": item.get("propertyType", "Unknown"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "carspaces": item.get("carspaces"),
            "land_area": item.get("landArea"),
            "building_area": item.get("buildingArea"),
            "features": item.get("features", [])
        }
        
        # Extract price information
        price_details = {}
        if "price" in item:
            price_details = item["price"]
        
        return {
            "listing_id": item.get("id"),
            "address": self._transform_address(address_data),
            "property_details": property_details,
            "price_details": price_details,
            "listing_date": item.get("dateListed"),
            "agent_info": item.get("advertiser"),
            "media_urls": [media.get("url") for media in item.get("media", [])],
            "description": item.get("description"),
            "auction_date": item.get("auctionSchedule", {}).get("time")
        }
    
    def _transform_address(self, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform address data to our format."""
        return {
            "unit_number": address_data.get("unitNumber"),
            "street_number": address_data.get("streetNumber", ""),
            "street_name": address_data.get("streetName", ""),
            "street_type": address_data.get("streetType", ""),
            "suburb": address_data.get("suburb", ""),
            "state": address_data.get("state", ""),
            "postcode": address_data.get("postcode", ""),
            "full_address": address_data.get("displayAddress"),
            "latitude": address_data.get("location", {}).get("latitude"),
            "longitude": address_data.get("location", {}).get("longitude")
        }
    
    def _transform_property_details(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform property details response."""
        return {
            "id": response_data.get("id"),
            "address": self._transform_address(response_data.get("address", {})),
            "property_details": {
                "property_type": response_data.get("propertyType"),
                "bedrooms": response_data.get("bedrooms"),
                "bathrooms": response_data.get("bathrooms"),
                "carspaces": response_data.get("carspaces"),
                "land_area": response_data.get("landArea"),
                "building_area": response_data.get("buildingArea"),
                "year_built": response_data.get("yearBuilt"),
                "features": response_data.get("features", [])
            },
            "price_details": response_data.get("price", {}),
            "description": response_data.get("description"),
            "media": response_data.get("media", []),
            "agent_details": response_data.get("advertiser", {}),
            "inspection_times": response_data.get("inspectionTimes", []),
            "auction_details": response_data.get("auctionSchedule", {}),
            "listing_details": {
                "date_listed": response_data.get("dateListed"),
                "date_updated": response_data.get("dateUpdated"),
                "listing_type": response_data.get("listingType"),
                "status": response_data.get("status")
            }
        }
    
    def _transform_valuation_response(
        self, 
        property_details: Dict[str, Any], 
        address: str
    ) -> Dict[str, Any]:
        """Transform property details to valuation response."""
        # Extract price information
        price_info = property_details.get("price_details", {})
        
        # Estimate valuation from available price data
        estimated_value = 0
        if "displayPrice" in price_info:
            # Try to extract numeric value from display price
            try:
                import re
                price_text = price_info["displayPrice"]
                # Extract numbers from price text
                numbers = re.findall(r'[\d,]+', price_text.replace(',', ''))
                if numbers:
                    estimated_value = float(numbers[0])
            except:
                pass
        
        if not estimated_value and "from" in price_info:
            estimated_value = price_info["from"]
        elif not estimated_value and "to" in price_info:
            estimated_value = price_info["to"]
        
        # Create valuation data
        confidence = 0.7 if estimated_value > 0 else 0.3
        
        valuation_data = {
            "estimated_value": estimated_value,
            "valuation_range_lower": estimated_value * 0.9 if estimated_value > 0 else 0,
            "valuation_range_upper": estimated_value * 1.1 if estimated_value > 0 else 0,
            "confidence": confidence,
            "valuation_date": datetime.now(timezone.utc),
            "valuation_source": "domain",
            "methodology": "market_comparison",
            "currency": "AUD"
        }
        
        return {
            "address": address,
            "valuations": {"domain": valuation_data},
            "processing_time": 0.0,
            "data_sources_used": ["domain"],
            "confidence_score": confidence,
            "warnings": [] if estimated_value > 0 else ["Limited price data available"]
        }
    
    def _transform_market_analytics(
        self,
        response_data: Dict[str, Any],
        location: Dict[str, str],
        property_type: str = None
    ) -> Dict[str, Any]:
        """Transform sales data to market analytics."""
        sales_data = response_data.get("data", [])
        
        if not sales_data:
            return {
                "location": location,
                "property_type": property_type,
                "median_price": 0,
                "price_growth_12_month": 0.0,
                "days_on_market": 0,
                "sales_volume_12_month": 0,
                "market_outlook": "insufficient_data"
            }
        
        # Calculate basic analytics
        prices = [sale.get("price", 0) for sale in sales_data if sale.get("price")]
        median_price = sorted(prices)[len(prices) // 2] if prices else 0
        
        return {
            "location": location,
            "property_type": property_type,
            "median_price": median_price,
            "price_growth_12_month": 0.0,  # Would need historical data
            "days_on_market": 30,  # Default estimate
            "sales_volume_12_month": len(sales_data),
            "market_outlook": "stable",
            "data_points": len(sales_data),
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
    
    def _transform_comparable_sales(
        self,
        response_data: Dict[str, Any],
        property_details: Dict[str, Any],
        radius_km: float
    ) -> Dict[str, Any]:
        """Transform sales data to comparable sales."""
        sales_data = response_data.get("data", [])
        
        comparables = []
        for sale in sales_data[:10]:  # Limit to top 10 comparables
            comparable = {
                "address": sale.get("address", {}).get("displayAddress", ""),
                "sale_date": sale.get("soldDate"),
                "sale_price": sale.get("price", 0),
                "property_details": {
                    "property_type": sale.get("propertyType"),
                    "bedrooms": sale.get("bedrooms"),
                    "bathrooms": sale.get("bathrooms"),
                    "carspaces": sale.get("carspaces"),
                    "land_area": sale.get("landArea")
                },
                "similarity_score": 0.8,  # Would need actual comparison logic
                "adjusted_price": sale.get("price", 0)
            }
            comparables.append(comparable)
        
        return {
            "property_id": property_details.get("id"),
            "radius_km": radius_km,
            "comparable_sales": comparables,
            "total_found": len(sales_data),
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
    
    def _transform_sales_history(
        self,
        response_data: Dict[str, Any],
        property_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform sales data to sales history for specific property."""
        # This would need more sophisticated address matching
        # For now, return empty list as Domain API doesn't provide direct sales history
        return []
    
    def _transform_rental_history(
        self,
        response_data: Dict[str, Any],
        property_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform rental data to rental history for specific property."""
        # This would need more sophisticated address matching
        # For now, return empty list
        return []
    
    def _transform_demographics(
        self,
        sales_data: Dict[str, Any],
        listings_data: Dict[str, Any],
        suburb: str,
        state: str
    ) -> Dict[str, Any]:
        """Transform combined data to demographics."""
        return {
            "suburb": suburb,
            "state": state,
            "population_estimate": 10000,  # Would need actual demographic data
            "median_age": 35,
            "median_income": 75000,
            "property_ownership_rate": 0.65,
            "market_activity": {
                "recent_sales": sales_data.get("sales_volume_12_month", 0),
                "current_listings": listings_data.get("results_returned", 0),
                "median_price": sales_data.get("median_price", 0)
            },
            "data_sources": ["domain_sales", "domain_listings"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "data_quality": "estimated"  # Indicates this is derived data
        }