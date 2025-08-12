"""
Tests for authentication context management.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from contextvars import copy_context

from app.core.auth_context import AuthContext, with_auth_context
from app.clients.supabase.client import SupabaseClient
from fastapi import HTTPException


class TestAuthContext:
    """Test cases for AuthContext functionality."""
    
    def test_set_and_get_auth_context(self):
        """Test setting and getting auth context."""
        # Set auth context
        token = "test-jwt-token"
        user_id = "test-user-id"
        user_email = "test@example.com"
        metadata = {"role": "user", "org_id": "org-123"}
        
        AuthContext.set_auth_context(
            token=token,
            user_id=user_id,
            user_email=user_email,
            metadata=metadata
        )
        
        # Verify values are set correctly
        assert AuthContext.get_user_token() == token
        assert AuthContext.get_user_id() == user_id
        assert AuthContext.get_user_email() == user_email
        assert AuthContext.get_auth_metadata() == metadata
        assert AuthContext.is_authenticated() is True
    
    def test_clear_auth_context(self):
        """Test clearing auth context."""
        # Set some values
        AuthContext.set_auth_context(
            token="test-token",
            user_id="test-id"
        )
        
        # Clear context
        AuthContext.clear_auth_context()
        
        # Verify all values are cleared
        assert AuthContext.get_user_token() is None
        assert AuthContext.get_user_id() is None
        assert AuthContext.get_user_email() is None
        assert AuthContext.get_auth_metadata() is None
        assert AuthContext.is_authenticated() is False
    
    @pytest.mark.asyncio
    async def test_get_authenticated_client_with_token(self):
        """Test getting authenticated client with token in context."""
        # Mock the get_supabase_client function
        mock_client = Mock(spec=SupabaseClient)
        mock_client.set_user_token = Mock()
        
        with patch('app.core.auth_context.get_supabase_client', new_callable=AsyncMock) as mock_get_client:
            mock_get_client.return_value = mock_client
            
            # Set auth context
            token = "test-jwt-token"
            AuthContext.set_auth_context(token=token)
            
            # Get authenticated client
            client = await AuthContext.get_authenticated_client()
            
            # Verify client methods were called
            mock_get_client.assert_called_once()
            # set_user_token now accepts 2 parameters: token and refresh_token
            mock_client.set_user_token.assert_called_once_with(token, None)
            assert client == mock_client
    
    @pytest.mark.asyncio
    async def test_get_authenticated_client_without_token_required(self):
        """Test getting authenticated client without token when auth is required."""
        # Clear any existing context
        AuthContext.clear_auth_context()
        
        # Should raise HTTPException when auth is required but no token
        with pytest.raises(HTTPException) as exc_info:
            await AuthContext.get_authenticated_client(require_auth=True)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
    
    @pytest.mark.asyncio
    async def test_get_authenticated_client_without_token_not_required(self):
        """Test getting authenticated client without token when auth is not required."""
        # Mock the get_supabase_client function
        mock_client = Mock(spec=SupabaseClient)
        
        with patch('app.core.auth_context.get_supabase_client', new_callable=AsyncMock) as mock_get_client:
            mock_get_client.return_value = mock_client
            
            # Clear any existing context
            AuthContext.clear_auth_context()
            
            # Get client without requiring auth
            client = await AuthContext.get_authenticated_client(require_auth=False)
            
            # Verify client was returned without setting token
            mock_get_client.assert_called_once()
            assert client == mock_client
            # set_user_token should not have been called
            assert not hasattr(mock_client.set_user_token, 'called') or not mock_client.set_user_token.called
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator_with_token(self):
        """Test require_auth decorator with valid token."""
        # Set auth context
        AuthContext.set_auth_context(token="test-token")
        
        # Define a protected function
        @AuthContext.require_auth
        async def protected_function():
            return "success"
        
        # Should execute successfully
        result = await protected_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator_without_token(self):
        """Test require_auth decorator without token."""
        # Clear auth context
        AuthContext.clear_auth_context()
        
        # Define a protected function
        @AuthContext.require_auth
        async def protected_function():
            return "success"
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await protected_function()
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
    
    def test_log_auth_action(self, caplog):
        """Test logging auth actions."""
        # Set auth context
        AuthContext.set_auth_context(
            token="test-token",
            user_id="user-123",
            user_email="test@example.com"
        )
        
        # Log an action
        AuthContext.log_auth_action(
            action="create",
            resource_type="document",
            resource_id="doc-456"
        )
        
        # Verify log was created - check for the actual log message format
        log_records = [record for record in caplog.records if record.name == "app.core.auth_context"]
        assert len(log_records) > 0
        # Check the log message contains the expected information
        log_message = log_records[-1].message
        assert "Auth action: create on document" in log_message
    
    def test_context_isolation_between_async_tasks(self):
        """Test that auth context is isolated between async tasks."""
        async def task1():
            AuthContext.set_auth_context(token="token1", user_id="user1")
            await asyncio.sleep(0.01)  # Simulate some async work
            assert AuthContext.get_user_token() == "token1"
            assert AuthContext.get_user_id() == "user1"
        
        async def task2():
            AuthContext.set_auth_context(token="token2", user_id="user2")
            await asyncio.sleep(0.01)  # Simulate some async work
            assert AuthContext.get_user_token() == "token2"
            assert AuthContext.get_user_id() == "user2"
        
        async def run_tasks():
            # Run tasks concurrently
            await asyncio.gather(task1(), task2())
        
        # Run in event loop
        asyncio.run(run_tasks())
    
    def test_with_auth_context_manager(self):
        """Test the with_auth_context context manager."""
        # Set initial context
        AuthContext.set_auth_context(token="original-token", user_id="original-user")
        
        # Use context manager
        with with_auth_context(token="temp-token", user_id="temp-user"):
            # Inside context, should have temp values
            assert AuthContext.get_user_token() == "temp-token"
            assert AuthContext.get_user_id() == "temp-user"
        
        # Outside context, should restore original values
        assert AuthContext.get_user_token() == "original-token"
        assert AuthContext.get_user_id() == "original-user"
    
    def test_with_auth_context_manager_no_previous(self):
        """Test context manager when no previous context exists."""
        # Clear any existing context
        AuthContext.clear_auth_context()
        
        # Use context manager
        with with_auth_context(token="temp-token", user_id="temp-user"):
            assert AuthContext.get_user_token() == "temp-token"
            assert AuthContext.get_user_id() == "temp-user"
        
        # Outside context, should be cleared
        assert AuthContext.get_user_token() is None
        assert AuthContext.get_user_id() is None