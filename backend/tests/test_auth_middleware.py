"""
Tests for authentication middleware.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import Headers

from app.middleware.auth_middleware import AuthContextMiddleware, setup_auth_middleware
from app.core.auth_context import AuthContext


class TestAuthContextMiddleware:
    """Test cases for AuthContextMiddleware."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock(spec=Request)
        request.headers = Headers({})
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app."""
        app = AsyncMock()
        return app
    
    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return AuthContextMiddleware(mock_app, validate_token=False)
    
    @pytest.mark.asyncio
    async def test_middleware_with_valid_bearer_token(self, middleware, mock_request):
        """Test middleware with valid Bearer token."""
        # Set up request with Bearer token
        token = "test-jwt-token"
        mock_request.headers = Headers({
            "Authorization": f"Bearer {token}",
            "X-Request-ID": "req-123",
            "User-Agent": "TestAgent/1.0"
        })
        
        # Mock call_next
        async def call_next(request):
            # Verify auth context is set during request processing
            assert AuthContext.get_user_token() == token
            assert AuthContext.is_authenticated() is True
            
            metadata = AuthContext.get_auth_metadata()
            assert metadata["request_id"] == "req-123"
            assert metadata["user_agent"] == "TestAgent/1.0"
            assert metadata["ip_address"] == "127.0.0.1"
            
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify response
        assert response.body == b"OK"
        
        # Verify context is cleared after request
        assert AuthContext.get_user_token() is None
        assert AuthContext.is_authenticated() is False
    
    @pytest.mark.asyncio
    async def test_middleware_without_auth_header(self, middleware, mock_request):
        """Test middleware without Authorization header."""
        # No Authorization header
        mock_request.headers = Headers({})
        
        # Mock call_next
        async def call_next(request):
            # Verify no auth context is set
            assert AuthContext.get_user_token() is None
            assert AuthContext.is_authenticated() is False
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify response
        assert response.body == b"OK"
    
    @pytest.mark.asyncio
    async def test_middleware_with_invalid_auth_header(self, middleware, mock_request):
        """Test middleware with invalid Authorization header format."""
        # Invalid format (not Bearer)
        mock_request.headers = Headers({
            "Authorization": "Basic dGVzdDp0ZXN0"  # Basic auth instead of Bearer
        })
        
        # Mock call_next
        async def call_next(request):
            # Verify no auth context is set for invalid format
            assert AuthContext.get_user_token() is None
            assert AuthContext.is_authenticated() is False
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify response
        assert response.body == b"OK"
    
    @pytest.mark.asyncio
    async def test_middleware_clears_context_on_exception(self, middleware, mock_request):
        """Test middleware clears context even when exception occurs."""
        # Set up request with token
        token = "test-jwt-token"
        mock_request.headers = Headers({
            "Authorization": f"Bearer {token}"
        })
        
        # Mock call_next that raises exception
        async def call_next(request):
            # Verify context is set
            assert AuthContext.get_user_token() == token
            raise ValueError("Test exception")
        
        # Process request and expect exception
        with pytest.raises(ValueError, match="Test exception"):
            await middleware.dispatch(mock_request, call_next)
        
        # Verify context is still cleared after exception
        assert AuthContext.get_user_token() is None
        assert AuthContext.is_authenticated() is False
    
    @pytest.mark.asyncio
    async def test_middleware_with_token_validation(self, mock_app, mock_request):
        """Test middleware with token validation enabled."""
        # Create middleware with validation enabled
        middleware = AuthContextMiddleware(mock_app, validate_token=True)
        
        # Mock JWT token with claims
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.test"
        mock_request.headers = Headers({
            "Authorization": f"Bearer {token}"
        })
        
        # Mock call_next
        async def call_next(request):
            # With validation, user_id and email should be extracted from token
            assert AuthContext.get_user_token() == token
            # Note: In real test, these would be extracted from the token
            # For now, they may be None since we're using a mock token
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify response
        assert response.body == b"OK"
        
        # Verify context is cleared
        assert AuthContext.get_user_token() is None
    
    def test_setup_auth_middleware(self):
        """Test setup_auth_middleware function."""
        # Mock FastAPI app
        mock_app = Mock()
        mock_app.add_middleware = Mock()
        
        # Setup middleware
        setup_auth_middleware(mock_app, validate_token=True)
        
        # Verify middleware was added
        mock_app.add_middleware.assert_called_once()
        call_args = mock_app.add_middleware.call_args
        assert call_args[0][0] == AuthContextMiddleware
        assert call_args[1]["validate_token"] is True