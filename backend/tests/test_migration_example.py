"""
Test examples demonstrating the improved testability of the decoupled client architecture
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from app.core.database_v2 import DatabaseService
from app.core.auth_v2 import AuthService, TokenData, User
from app.clients.base.exceptions import ClientError


class TestDatabaseServiceMigration:
    """Test the migrated database service with dependency injection"""
    
    @pytest.fixture
    async def mock_supabase_client(self):
        """Create a mock Supabase client for testing"""
        mock_client = AsyncMock()
        mock_client.database = AsyncMock()
        return mock_client
    
    @pytest.fixture  
    async def database_service(self, mock_supabase_client):
        """Create database service with injected mock client"""
        service = DatabaseService(supabase_client=mock_supabase_client)
        await service.initialize()
        return service, mock_supabase_client
    
    async def test_create_record_success(self, database_service):
        """Test successful record creation"""
        service, mock_client = database_service
        
        # Setup mock response
        expected_data = {"id": "123", "name": "Test User", "email": "test@example.com"}
        mock_client.database.create.return_value = expected_data
        
        # Test the operation
        result = await service.create_record("users", {"name": "Test User", "email": "test@example.com"})
        
        # Verify the result
        assert result == expected_data
        mock_client.database.create.assert_called_once_with("users", {"name": "Test User", "email": "test@example.com"})
    
    async def test_create_record_client_error(self, database_service):
        """Test handling of client errors during record creation"""
        service, mock_client = database_service
        
        # Setup mock to raise ClientError
        mock_client.database.create.side_effect = ClientError("Database connection failed")
        
        # Test that the error is properly handled
        with pytest.raises(ClientError, match="Database connection failed"):
            await service.create_record("users", {"name": "Test User"})
    
    async def test_read_records_with_filters(self, database_service):
        """Test reading records with filters"""
        service, mock_client = database_service
        
        # Setup mock response
        expected_records = [
            {"id": "1", "name": "User 1", "active": True},
            {"id": "2", "name": "User 2", "active": True}
        ]
        mock_client.database.read.return_value = expected_records
        
        # Test the operation
        result = await service.read_records("users", {"active": True}, 10)
        
        # Verify the result
        assert result == expected_records
        mock_client.database.read.assert_called_once_with("users", {"active": True}, 10)
    
    async def test_health_check_healthy(self, database_service):
        """Test health check when service is healthy"""
        service, mock_client = database_service
        
        # Setup mock for health check query
        mock_client.database.read.return_value = []
        
        # Test health check
        health = await service.health_check()
        
        # Verify healthy status
        assert health["status"] == "healthy"
        assert health["service"] == "database_service_v2"
        assert "dependency_injection" in health["features"]
    
    async def test_health_check_unhealthy(self, mock_supabase_client):
        """Test health check when service is not initialized"""
        service = DatabaseService(supabase_client=mock_supabase_client)
        # Don't initialize the service
        
        # Test health check
        health = await service.health_check()
        
        # Verify unhealthy status
        assert health["status"] == "unhealthy"
        assert "Service not initialized" in health["error"]


class TestAuthServiceMigration:
    """Test the migrated authentication service"""
    
    @pytest.fixture
    async def mock_auth_client(self):
        """Create a mock auth client for testing"""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    async def mock_db_service(self):
        """Create a mock database service for testing"""
        mock_service = AsyncMock()
        mock_service.is_initialized = True
        return mock_service
    
    @pytest.fixture
    async def auth_service(self, mock_auth_client, mock_db_service):
        """Create auth service with injected mock clients"""
        service = AuthService(auth_client=mock_auth_client, db_service=mock_db_service)
        await service.initialize()
        return service, mock_auth_client, mock_db_service
    
    async def test_verify_token_success(self, auth_service):
        """Test successful token verification"""
        service, mock_auth_client, mock_db_service = auth_service
        
        # Setup mock response
        mock_auth_client.authenticate_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "exp": 1234567890
        }
        
        # Test token verification
        token_data = await service.verify_token("valid-token")
        
        # Verify the result
        assert token_data.user_id == "user-123"  
        assert token_data.email == "test@example.com"
        assert isinstance(token_data.exp, datetime)
        mock_auth_client.authenticate_user.assert_called_once_with("valid-token")
    
    async def test_verify_token_invalid(self, auth_service):
        """Test token verification with invalid token"""
        service, mock_auth_client, mock_db_service = auth_service
        
        # Setup mock to raise ClientError
        mock_auth_client.authenticate_user.side_effect = ClientError("Invalid token")
        
        # Test that HTTPException is raised
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_token("invalid-token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)
    
    async def test_get_current_user_success(self, auth_service):
        """Test getting current user with valid token data"""
        service, mock_auth_client, mock_db_service = auth_service
        
        # Setup mock database response
        mock_db_service.read_records.return_value = [{
            "id": "user-123",
            "email": "test@example.com", 
            "australian_state": "NSW",
            "user_type": "individual",
            "subscription_status": "premium",
            "credits_remaining": 100,
            "preferences": {"theme": "dark"}
        }]
        
        # Create token data
        token_data = TokenData(
            user_id="user-123",
            email="test@example.com",
            exp=datetime.utcnow()
        )
        
        # Test getting user
        user = await service.get_current_user(token_data)
        
        # Verify the result
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.australian_state == "NSW"
        assert user.subscription_status == "premium"
        assert user.credits_remaining == 100
        mock_db_service.read_records.assert_called_once_with("profiles", {"id": "user-123"}, 1)
    
    async def test_get_current_user_not_found(self, auth_service):
        """Test getting current user when user doesn't exist"""
        service, mock_auth_client, mock_db_service = auth_service
        
        # Setup mock to return empty result
        mock_db_service.read_records.return_value = []
        
        # Create token data
        token_data = TokenData(
            user_id="nonexistent-user",
            email="test@example.com", 
            exp=datetime.utcnow()
        )
        
        # Test that HTTPException is raised
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.get_current_user(token_data)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)


class TestMigrationBenefits:
    """Test cases demonstrating the benefits of the migration"""
    
    async def test_easy_mocking_and_testing(self):
        """Demonstrate how easy it is to mock dependencies"""
        # Create service with mock dependencies
        mock_supabase = AsyncMock()
        mock_supabase.database.read.return_value = [{"id": "1", "name": "test"}]
        
        service = DatabaseService(supabase_client=mock_supabase)
        await service.initialize()
        
        # Test the service
        result = await service.read_records("users", {})
        
        # Easy verification
        assert len(result) == 1
        assert result[0]["name"] == "test"
        mock_supabase.database.read.assert_called_once()
    
    async def test_error_handling_consistency(self):
        """Demonstrate consistent error handling across services"""
        mock_client = AsyncMock()
        mock_client.database.create.side_effect = ClientError("Connection failed", retry_after=5)
        
        service = DatabaseService(supabase_client=mock_client)
        await service.initialize()
        
        # All client errors are handled consistently
        with pytest.raises(ClientError) as exc_info:
            await service.create_record("users", {"name": "test"})
        
        # Error includes retry information
        assert exc_info.value.retry_after == 5
        assert "Connection failed" in str(exc_info.value)
    
    async def test_configuration_isolation(self):
        """Demonstrate how configuration is isolated and testable"""
        # Different configurations for different environments
        mock_dev_client = AsyncMock()
        mock_prod_client = AsyncMock()
        
        dev_service = DatabaseService(supabase_client=mock_dev_client)
        prod_service = DatabaseService(supabase_client=mock_prod_client)
        
        await dev_service.initialize()
        await prod_service.initialize()
        
        # Services use different clients but same interface
        assert dev_service._supabase_client != prod_service._supabase_client
        assert hasattr(dev_service, 'database')
        assert hasattr(prod_service, 'database')


# Integration test example
class TestIntegrationAfterMigration:
    """Integration tests showing real client usage after migration"""
    
    @pytest.mark.integration
    async def test_full_auth_flow(self):
        """Test complete authentication flow with real clients"""
        # This would use real clients in integration environment
        from app.clients.factory import get_supabase_client
        
        # Get real client (configured for test environment)
        supabase_client = await get_supabase_client()
        
        # Create services with real client
        auth_service = AuthService(auth_client=supabase_client.auth)
        await auth_service.initialize()
        
        # Test with real client (requires test token)
        # This demonstrates that migration maintains full functionality
        health = await auth_service.health_check()
        assert health["status"] == "healthy"