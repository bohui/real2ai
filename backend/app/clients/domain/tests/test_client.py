"""
Unit tests for Domain API client.
"""

import pytest
from unittest.mock import AsyncMock, patch

from ..client import DomainClient
from ..config import DomainClientConfig
from ...base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    PropertyNotFoundError,
    PropertyValuationError,
)


@pytest.fixture
def domain_config():
    """Create test Domain API configuration."""
    config = DomainClientConfig(
        api_key="test_api_key",
        base_url="https://api.domain.com.au",
        timeout=30,
        service_tier="standard",
        enable_caching=False,  # Disable caching for tests
        enable_request_logging=False
    )
    return config


@pytest.fixture
async def domain_client(domain_config):
    """Create Domain API client for testing."""
    client = DomainClient(domain_config)
    
    # Mock the aiohttp session
    mock_session = AsyncMock()
    client._session = mock_session
    client._initialized = True
    
    yield client
    
    # Cleanup
    await client.close()


@pytest.mark.asyncio
class TestDomainClient:
    """Test cases for Domain API client."""
    
    async def test_initialization(self, domain_config):
        """Test client initialization."""
        client = DomainClient(domain_config)
        
        assert client.client_name == "DomainClient"
        assert client.config == domain_config
        assert not client.is_initialized
        assert client._rate_limit_manager is not None
    
    async def test_invalid_config(self):
        """Test initialization with invalid configuration."""
        with pytest.raises(ValueError, match="Domain API key is required"):
            config = DomainClientConfig(api_key="")
            DomainClient(config)
    
    @patch('aiohttp.ClientSession')
    async def test_successful_initialization(self, mock_session_class, domain_config):
        """Test successful client initialization."""
        # Mock successful session creation and test connection
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"data": []}
        
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = DomainClient(domain_config)
        await client.initialize()
        
        assert client.is_initialized
        mock_session_class.assert_called_once()
    
    async def test_authentication_error_during_init(self, domain_config):
        """Test authentication error during initialization."""
        client = DomainClient(domain_config)
        
        # Mock session that returns 401
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 401
        
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ClientAuthenticationError):
                await client.initialize()
    
    async def test_health_check_success(self, domain_client):
        """Test successful health check."""
        # Mock successful test connection
        domain_client._test_connection = AsyncMock()
        
        health_status = await domain_client.health_check()
        
        assert health_status["status"] == "healthy"
        assert health_status["client_name"] == "DomainClient"
        assert health_status["initialized"] is True
        assert "rate_limiting" in health_status
        assert "config" in health_status
    
    async def test_health_check_failure(self, domain_client):
        """Test health check failure."""
        # Mock failed test connection
        domain_client._test_connection = AsyncMock(
            side_effect=ClientConnectionError("Connection failed")
        )
        
        health_status = await domain_client.health_check()
        
        assert health_status["status"] == "unhealthy"
        assert "error" in health_status
        assert health_status["error_type"] == "ClientConnectionError"
    
    async def test_make_request_success(self, domain_client):
        """Test successful API request."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"result": "success"}
        
        domain_client._session.request.return_value.__aenter__.return_value = mock_response
        
        result = await domain_client._make_request(
            "GET",
            "test-endpoint",
            priority="normal",
            operation_name="test"
        )
        
        assert result == {"result": "success"}
        domain_client._session.request.assert_called_once()
    
    async def test_make_request_rate_limit(self, domain_client):
        """Test rate limit handling."""
        # Mock rate limit response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        
        domain_client._session.request.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(ClientRateLimitError) as exc_info:
            await domain_client._make_request(
                "GET",
                "test-endpoint",
                operation_name="test"
            )
        
        assert exc_info.value.retry_after == 60
    
    async def test_make_request_authentication_error(self, domain_client):
        """Test authentication error handling."""
        # Mock authentication error response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text.return_value = "Unauthorized"
        
        domain_client._session.request.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(ClientAuthenticationError):
            await domain_client._make_request(
                "GET",
                "test-endpoint",
                operation_name="test"
            )
    
    async def test_search_properties_success(self, domain_client):
        """Test successful property search."""
        # Mock search response
        search_response = {
            "data": [
                {
                    "id": 123456,
                    "propertyType": "House",
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "address": {
                        "streetNumber": "123",
                        "streetName": "Test",
                        "streetType": "Street",
                        "suburb": "Testville",
                        "state": "NSW",
                        "postcode": "2000"
                    },
                    "price": {"displayPrice": "$800,000"}
                }
            ],
            "meta": {"totalResults": 1}
        }
        
        domain_client._make_request = AsyncMock(return_value=search_response)
        
        search_params = {
            "suburb": "Testville",
            "state": "NSW",
            "listing_type": "Sale"
        }
        
        result = await domain_client.search_properties(search_params)
        
        assert result["total_results"] == 1
        assert len(result["listings"]) == 1
        assert result["listings"][0]["listing_id"] == 123456
        assert result["listings"][0]["property_details"]["property_type"] == "House"
    
    async def test_get_property_details_success(self, domain_client):
        """Test successful property details retrieval."""
        # Mock property details response
        details_response = {
            "id": 123456,
            "propertyType": "House",
            "bedrooms": 3,
            "bathrooms": 2,
            "address": {
                "streetNumber": "123",
                "streetName": "Test",
                "streetType": "Street",
                "suburb": "Testville",
                "state": "NSW",
                "postcode": "2000"
            },
            "price": {"displayPrice": "$800,000"},
            "description": "Beautiful family home"
        }
        
        domain_client._make_request = AsyncMock(return_value=details_response)
        
        result = await domain_client.get_property_details("123456")
        
        assert result["id"] == 123456
        assert result["property_details"]["property_type"] == "House"
        assert result["address"]["suburb"] == "Testville"
        assert result["description"] == "Beautiful family home"
    
    async def test_get_property_details_not_found(self, domain_client):
        """Test property not found error."""
        domain_client._make_request = AsyncMock(return_value=None)
        
        with pytest.raises(PropertyNotFoundError) as exc_info:
            await domain_client.get_property_details("999999")
        
        assert exc_info.value.address == "999999"
    
    async def test_get_property_valuation_success(self, domain_client):
        """Test successful property valuation."""
        # Mock property suggestion response
        suggest_response = {
            "data": [
                {
                    "id": 123456,
                    "address": {
                        "displayAddress": "123 Test Street, Testville NSW 2000"
                    }
                }
            ]
        }
        
        # Mock property details response
        details_response = {
            "id": 123456,
            "address": {
                "suburb": "Testville",
                "state": "NSW"
            },
            "price": {"displayPrice": "$800,000"}
        }
        
        domain_client._make_request = AsyncMock(
            side_effect=[suggest_response, details_response]
        )
        
        result = await domain_client.get_property_valuation("123 Test Street, Testville NSW 2000")
        
        assert "valuations" in result
        assert "domain" in result["valuations"]
        assert result["address"] == "123 Test Street, Testville NSW 2000"
    
    async def test_get_property_valuation_no_data(self, domain_client):
        """Test valuation with no data available."""
        domain_client._make_request = AsyncMock(return_value={"data": []})
        
        with pytest.raises(PropertyValuationError) as exc_info:
            await domain_client.get_property_valuation("123 Test Street")
        
        assert "No valuation data available" in str(exc_info.value)
    
    async def test_build_search_payload(self, domain_client):
        """Test search payload building."""
        search_params = {
            "suburb": "Testville",
            "state": "NSW",
            "listing_type": "Sale",
            "min_price": 500000,
            "max_price": 1000000,
            "min_bedrooms": 2,
            "property_types": ["House", "Townhouse"]
        }
        
        payload = domain_client._build_search_payload(search_params)
        
        assert payload["listingType"] == "Sale"
        assert payload["locations"] == [{"suburb": "Testville", "state": "NSW"}]
        assert payload["price"] == {"from": 500000, "to": 1000000}
        assert payload["minBedrooms"] == 2
        assert payload["propertyTypes"] == ["House", "Townhouse"]
    
    async def test_transform_address(self, domain_client):
        """Test address transformation."""
        address_data = {
            "unitNumber": "2",
            "streetNumber": "123",
            "streetName": "Test",
            "streetType": "Street",
            "suburb": "Testville",
            "state": "NSW",
            "postcode": "2000",
            "displayAddress": "2/123 Test Street, Testville NSW 2000",
            "location": {"latitude": -33.8688, "longitude": 151.2093}
        }
        
        result = domain_client._transform_address(address_data)
        
        assert result["unit_number"] == "2"
        assert result["street_number"] == "123"
        assert result["street_name"] == "Test"
        assert result["street_type"] == "Street"
        assert result["suburb"] == "Testville"
        assert result["state"] == "NSW"
        assert result["postcode"] == "2000"
        assert result["full_address"] == "2/123 Test Street, Testville NSW 2000"
        assert result["latitude"] == -33.8688
        assert result["longitude"] == 151.2093
    
    async def test_check_api_health_success(self, domain_client):
        """Test successful API health check."""
        domain_client._make_request = AsyncMock(return_value={"data": []})
        
        result = await domain_client.check_api_health()
        
        assert result["api_status"] == "healthy"
        assert "response_time_seconds" in result
        assert "rate_limiting" in result
        assert result["service_tier"] == "standard"
    
    async def test_check_api_health_failure(self, domain_client):
        """Test API health check failure."""
        domain_client._make_request = AsyncMock(
            side_effect=ClientConnectionError("Connection failed")
        )
        
        result = await domain_client.check_api_health()
        
        assert result["api_status"] == "unhealthy"
        assert "error" in result
        assert result["error_type"] == "ClientConnectionError"
    
    async def test_rate_limit_status(self, domain_client):
        """Test rate limit status retrieval."""
        status = await domain_client.get_rate_limit_status()
        
        assert "global" in status
        assert "endpoints" in status
        assert "requests_in_window" in status["global"]
        assert "requests_per_minute_limit" in status["global"]
    
    async def test_close_client(self, domain_client):
        """Test client cleanup."""
        # Ensure session is closed
        await domain_client.close()
        
        assert not domain_client.is_initialized
        domain_client._session.close.assert_called_once()


@pytest.mark.asyncio
class TestDomainClientIntegration:
    """Integration test cases for Domain API client."""
    
    @pytest.mark.skip(reason="Requires actual API key and network access")
    async def test_real_property_search(self):
        """Test real property search (requires valid API key)."""
        config = DomainClientConfig(
            api_key="your_real_api_key_here",
            service_tier="standard"
        )
        
        async with DomainClient(config) as client:
            await client.initialize()
            
            search_params = {
                "suburb": "Sydney",
                "state": "NSW",
                "listing_type": "Sale",
                "page_size": 5
            }
            
            result = await client.search_properties(search_params)
            
            assert "listings" in result
            assert isinstance(result["listings"], list)
            assert result["total_results"] >= 0
    
    @pytest.mark.skip(reason="Requires actual API key and network access")
    async def test_real_health_check(self):
        """Test real health check (requires valid API key)."""
        config = DomainClientConfig(
            api_key="your_real_api_key_here"
        )
        
        async with DomainClient(config) as client:
            await client.initialize()
            
            health_status = await client.health_check()
            
            assert health_status["status"] == "healthy"
            assert health_status["initialized"] is True