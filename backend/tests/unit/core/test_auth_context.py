"""
Unit tests for authentication context.

Note: The main AuthContext tests are located in tests/test_auth_context.py.
These are additional unit tests for specific edge cases.
"""
import pytest
from app.core.auth_context import AuthContext


class TestAuthContextUnit:
    """Unit tests for AuthContext specific scenarios."""
    
    @pytest.mark.unit
    def test_auth_context_exists(self):
        """Test that AuthContext class exists and has expected methods."""
        # Basic smoke test to ensure class is properly imported
        assert hasattr(AuthContext, 'set_auth_context')
        assert hasattr(AuthContext, 'clear_auth_context')
        assert hasattr(AuthContext, 'get_user_token')
        assert hasattr(AuthContext, 'get_user_id')
        assert hasattr(AuthContext, 'is_authenticated')
    
    @pytest.mark.unit
    def test_initial_state(self):
        """Test AuthContext initial state."""
        # Clear any existing context
        AuthContext.clear_auth_context()
        
        # Verify initial state
        assert AuthContext.get_user_token() is None
        assert AuthContext.get_user_id() is None
        assert AuthContext.get_user_email() is None
        assert AuthContext.get_auth_metadata() is None
        assert AuthContext.is_authenticated() is False

    @pytest.mark.unit
    def test_basic_context_operations(self):
        """Test basic context set and clear operations."""
        # Set context
        AuthContext.set_auth_context(
            token="test-token",
            user_id="test-user",
            user_email="test@example.com"
        )
        
        # Verify context is set
        assert AuthContext.get_user_token() == "test-token"
        assert AuthContext.get_user_id() == "test-user"
        assert AuthContext.get_user_email() == "test@example.com"
        assert AuthContext.is_authenticated() is True
        
        # Clear context
        AuthContext.clear_auth_context()
        
        # Verify context is cleared
        assert AuthContext.get_user_token() is None
        assert AuthContext.get_user_id() is None
        assert AuthContext.get_user_email() is None
        assert AuthContext.is_authenticated() is False