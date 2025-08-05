"""
Unit tests for CoreLogic API client.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from ..client import CoreLogicClient, CoreLogicAuthenticationError, CoreLogicValuationError
from ..config import CoreLogicClientConfig
from ..rate_limiter import CoreLogicRateLimitManager


class TestCoreLogicClient:
    """Test cases for CoreLogic API client."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CoreLogicClientConfig(
            api_key="test_api_key",
            client_id="test_client_id",
            client_secret="test_client_secret",
            environment="sandbox",
            service_tier="professional",
            enable_caching=False  # Disable caching for tests
        )
    
    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return CoreLogicClient(config)
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client, config):
        """Test client initialization."""
        assert client.config == config
        assert client._session is None
        assert client._access_token is None
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, client):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_token",
            "expires_in": 3600
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await client._authenticate()
            
            assert client._access_token == "test_token"
            assert client._token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, client):
        """Test authentication failure."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid credentials")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(CoreLogicAuthenticationError):
                await client._authenticate()
    
    @pytest.mark.asyncio
    async def test_property_valuation_success(self, client):
        """Test successful property valuation."""
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter
        client._rate_limit_manager = MagicMock()
        client._rate_limit_manager.acquire_request_slot = AsyncMock(return_value=True)
        client._rate_limit_manager.record_request_cost = AsyncMock()
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"X-API-Cost": "5.00"}
        mock_response.json = AsyncMock(return_value={
            "valuation_amount": 850000,
            "confidence_score": 0.85,
            "valuation_date": "2024-08-05",
            "methodology": "AVM",
            "comparables_count": 8
        })
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_property_valuation(
                "123 Test Street, Sydney NSW 2000",
                {"valuation_type": "avm"}
            )
            
            assert result["valuation_amount"] == 850000
            assert result["confidence_score"] == 0.85
            assert result["valuation_type"] == "avm"
    
    @pytest.mark.asyncio
    async def test_property_valuation_low_confidence(self, client):
        """Test property valuation with low confidence score."""
        # Set strict validation
        client.config.data_quality_settings["min_confidence_score"] = 0.8
        client.config.data_quality_settings["require_valuation_confidence"] = True
        
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter
        client._rate_limit_manager = MagicMock()
        client._rate_limit_manager.acquire_request_slot = AsyncMock(return_value=True)
        client._rate_limit_manager.record_request_cost = AsyncMock()
        
        # Mock API response with low confidence
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={
            "valuation_amount": 850000,
            "confidence_score": 0.5,  # Below threshold
            "valuation_date": "2024-08-05"
        })
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(CoreLogicValuationError):
                await client.get_property_valuation(
                    "123 Test Street, Sydney NSW 2000",
                    {"valuation_type": "avm"}
                )
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting behavior."""
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter that denies request
        client._rate_limit_manager = MagicMock()
        client._rate_limit_manager.acquire_request_slot = AsyncMock(return_value=False)
        client._rate_limit_manager.wait_for_rate_limit_reset = AsyncMock(return_value=0.5)
        
        with patch('asyncio.sleep') as mock_sleep:
            # Second call should succeed
            client._rate_limit_manager.acquire_request_slot.side_effect = [False, True]
            client._rate_limit_manager.record_request_cost = AsyncMock()
            
            # Mock API response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_request.return_value.__aenter__.return_value = mock_response
                
                result = await client._make_request("GET", "test", "test_op", 1.0)
                
                # Should have slept due to rate limiting
                mock_sleep.assert_called_once_with(0.5)
                assert result["result"] == "success"
    
    @pytest.mark.asyncio
    async def test_bulk_valuation(self, client):
        """Test bulk valuation functionality."""
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter
        client._rate_limit_manager = MagicMock()
        client._rate_limit_manager.acquire_request_slot = AsyncMock(return_value=True)
        client._rate_limit_manager.record_request_cost = AsyncMock()
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={
            "valuations": [
                {
                    "address": "123 Test St",
                    "valuation_amount": 850000,
                    "confidence_score": 0.85,
                    "valuation_status": "success"
                },
                {
                    "address": "456 Test Ave",
                    "valuation_amount": 720000,
                    "confidence_score": 0.78,
                    "valuation_status": "success"
                }
            ]
        })
        
        addresses = ["123 Test St", "456 Test Ave"]
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            results = await client.bulk_valuation(addresses, "avm")
            
            assert len(results) == 2
            assert results[0]["address"] == "123 Test St"
            assert results[0]["valuation_amount"] == 850000
            assert results[1]["address"] == "456 Test Ave"
    
    @pytest.mark.asyncio
    async def test_market_analytics(self, client):
        """Test market analytics functionality."""
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter
        client._rate_limit_manager = MagicMock()
        client._rate_limit_manager.acquire_request_slot = AsyncMock(return_value=True)
        client._rate_limit_manager.record_request_cost = AsyncMock()
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={
            "location": {"suburb": "Sydney", "state": "NSW"},
            "median_price": 1200000,
            "price_growth_12m": 8.5,
            "price_growth_5y": 45.2,
            "sales_volume": 156,
            "average_days_on_market": 32,
            "forecasts": {"next_12m_growth": 5.5},
            "data_confidence": 0.92,
            "sample_size": 156,
            "data_date": "2024-08-01"
        })
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_market_analytics(
                {"suburb": "Sydney", "state": "NSW"},
                "house"
            )
            
            assert result["market_metrics"]["median_price"] == 1200000
            assert result["market_metrics"]["price_growth_1yr"] == 8.5
            assert result["data_quality"]["confidence"] == 0.92
    
    @pytest.mark.asyncio
    async def test_cost_summary(self, client):
        """Test cost summary functionality."""
        # Mock rate limiter with cost data
        mock_rate_limiter = MagicMock()
        mock_rate_limiter.get_cost_summary.return_value = {
            "daily_cost": 45.50,
            "monthly_cost": 1250.75,
            "total_requests": 23,
            "valuation_count": 15,
            "average_cost_per_request": 1.98
        }
        
        client._rate_limit_manager = mock_rate_limiter
        
        result = await client.get_cost_summary()
        
        assert result["daily_cost"] == 45.50
        assert result["monthly_cost"] == 1250.75
        assert result["valuation_count"] == 15
    
    @pytest.mark.asyncio
    async def test_api_health_check(self, client):
        """Test API health check."""
        # Mock authentication
        client._access_token = "test_token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock rate limiter
        mock_rate_limiter = MagicMock()
        mock_rate_limiter.acquire_request_slot = AsyncMock(return_value=True)
        mock_rate_limiter.record_request_cost = AsyncMock()
        mock_rate_limiter.get_current_limits = AsyncMock(return_value={
            "hourly_requests_used": 45,
            "hourly_requests_limit": 500
        })
        mock_rate_limiter.get_cost_summary.return_value = {
            "daily_cost": 25.00
        }
        
        client._rate_limit_manager = mock_rate_limiter
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.check_api_health()
            
            assert result["status"] == "healthy"
            assert result["service_tier"] == "professional" 
            assert result["environment"] == "sandbox"
            assert "rate_limits" in result
            assert "cost_summary" in result


class TestCoreLogicRateLimitManager:
    """Test cases for CoreLogic rate limit manager."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CoreLogicClientConfig(
            api_key="test_key",
            client_id="test_id", 
            client_secret="test_secret",
            rate_limit_rph=100,
            requests_per_second=0.1,
            cost_management={
                "enable_cost_tracking": True,
                "daily_budget_limit": 100.0,
                "monthly_budget_limit": 2000.0,
                "auto_suspend_on_budget_exceeded": True
            }
        )
    
    @pytest.fixture
    def rate_manager(self, config):
        """Create test rate limit manager."""
        return CoreLogicRateLimitManager(config)
    
    @pytest.mark.asyncio
    async def test_request_slot_acquisition(self, rate_manager):
        """Test basic request slot acquisition."""
        result = await rate_manager.acquire_request_slot("test_operation", 1.0)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, rate_manager):
        """Test cost tracking functionality."""
        # Acquire slot and record cost
        await rate_manager.acquire_request_slot("avm_valuation", 5.0)
        await rate_manager.record_request_cost("avm_valuation", 5.0)
        
        limits = await rate_manager.get_current_limits()
        assert limits["daily_cost"] == 5.0
        
        summary = rate_manager.get_cost_summary()
        assert summary["daily_cost"] == 5.0
        assert summary["valuation_count"] == 1
    
    @pytest.mark.asyncio
    async def test_budget_limit_exceeded(self, rate_manager):
        """Test budget limit enforcement."""
        # Try to acquire slot that would exceed daily budget
        result = await rate_manager.acquire_request_slot("test_operation", 150.0)  # Exceeds $100 limit
        assert result is False  # Should be rejected
    
    @pytest.mark.asyncio
    async def test_hourly_rate_limit(self, rate_manager):
        """Test hourly rate limiting."""
        # Simulate reaching hourly limit
        rate_manager._hourly_request_count = 100  # At limit
        
        result = await rate_manager.acquire_request_slot("test_operation", 1.0)
        assert result is False  # Should be rejected
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, rate_manager):
        """Test circuit breaker functionality."""
        # Record multiple failures
        for _ in range(3):  # Config has failure_threshold = 3
            await rate_manager.record_request_failure("test_op", Exception("Test error"))
        
        # Circuit should be open now
        result = await rate_manager.acquire_request_slot("test_operation", 1.0)
        assert result is False  # Should be rejected due to circuit breaker