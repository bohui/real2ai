"""
Unit tests for authentication context.
"""
from datetime import datetime
from unittest.mock import MagicMock
import pytest

from app.core.auth_context import AuthContext
from app.schema.auth import User


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        user_id="user-123",
        email="test@example.com", 
        is_active=True,
        subscription_tier="premium",
        credits_remaining=100,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestAuthContext:
    """Test cases for AuthContext."""

    def test_set_current_user(self, sample_user):
        """Test setting current user in context."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        auth_context.set_current_user(sample_user)
        
        # Assert
        assert auth_context.current_user == sample_user
        assert auth_context.user_id == "user-123"
        assert auth_context.is_authenticated is True

    def test_clear_user(self, sample_user):
        """Test clearing user from context."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        auth_context.clear_user()
        
        # Assert
        assert auth_context.current_user is None
        assert auth_context.user_id is None
        assert auth_context.is_authenticated is False

    def test_get_user_id_when_authenticated(self, sample_user):
        """Test getting user ID when authenticated."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        user_id = auth_context.user_id
        
        # Assert
        assert user_id == "user-123"

    def test_get_user_id_when_not_authenticated(self):
        """Test getting user ID when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        user_id = auth_context.user_id
        
        # Assert
        assert user_id is None

    def test_is_authenticated_property(self, sample_user):
        """Test is_authenticated property."""
        # Arrange
        auth_context = AuthContext()
        
        # Act & Assert - Not authenticated initially
        assert auth_context.is_authenticated is False
        
        # Set user
        auth_context.set_current_user(sample_user)
        assert auth_context.is_authenticated is True
        
        # Clear user
        auth_context.clear_user()
        assert auth_context.is_authenticated is False

    def test_has_subscription_premium(self, sample_user):
        """Test subscription check for premium user."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        has_premium = auth_context.has_subscription("premium")
        
        # Assert
        assert has_premium is True

    def test_has_subscription_different_tier(self, sample_user):
        """Test subscription check for different tier."""
        # Arrange
        auth_context = AuthContext()
        sample_user.subscription_tier = "basic"
        auth_context.set_current_user(sample_user)
        
        # Act
        has_premium = auth_context.has_subscription("premium")
        
        # Assert
        assert has_premium is False

    def test_has_subscription_unauthenticated(self):
        """Test subscription check when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        has_premium = auth_context.has_subscription("premium")
        
        # Assert
        assert has_premium is False

    def test_has_credits_sufficient(self, sample_user):
        """Test credit check with sufficient credits."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        has_credits = auth_context.has_credits(50)
        
        # Assert
        assert has_credits is True

    def test_has_credits_insufficient(self, sample_user):
        """Test credit check with insufficient credits."""
        # Arrange
        auth_context = AuthContext()
        sample_user.credits_remaining = 10
        auth_context.set_current_user(sample_user)
        
        # Act
        has_credits = auth_context.has_credits(50)
        
        # Assert
        assert has_credits is False

    def test_has_credits_unauthenticated(self):
        """Test credit check when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        has_credits = auth_context.has_credits(50)
        
        # Assert
        assert has_credits is False

    def test_consume_credits_success(self, sample_user):
        """Test successful credit consumption."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        initial_credits = sample_user.credits_remaining
        
        # Act
        success = auth_context.consume_credits(25)
        
        # Assert
        assert success is True
        assert sample_user.credits_remaining == initial_credits - 25

    def test_consume_credits_insufficient(self, sample_user):
        """Test credit consumption with insufficient credits."""
        # Arrange
        auth_context = AuthContext()
        sample_user.credits_remaining = 10
        auth_context.set_current_user(sample_user)
        initial_credits = sample_user.credits_remaining
        
        # Act
        success = auth_context.consume_credits(50)
        
        # Assert
        assert success is False
        assert sample_user.credits_remaining == initial_credits  # Unchanged

    def test_consume_credits_unauthenticated(self):
        """Test credit consumption when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        success = auth_context.consume_credits(25)
        
        # Assert
        assert success is False

    def test_get_user_context_authenticated(self, sample_user):
        """Test getting user context when authenticated."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        context = auth_context.get_user_context()
        
        # Assert
        assert context["user_id"] == "user-123"
        assert context["email"] == "test@example.com"
        assert context["subscription_tier"] == "premium"
        assert context["credits_remaining"] == 100
        assert context["is_active"] is True

    def test_get_user_context_unauthenticated(self):
        """Test getting user context when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        context = auth_context.get_user_context()
        
        # Assert
        assert context == {}

    def test_user_state_persistence(self, sample_user):
        """Test that user state changes persist in context."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act - Modify user state
        auth_context.current_user.credits_remaining = 75
        auth_context.current_user.subscription_tier = "basic"
        
        # Assert - Changes are reflected
        assert auth_context.current_user.credits_remaining == 75
        assert auth_context.current_user.subscription_tier == "basic"
        assert auth_context.has_subscription("basic") is True
        assert auth_context.has_subscription("premium") is False

    def test_context_isolation(self, sample_user):
        """Test that different context instances are isolated."""
        # Arrange
        auth_context1 = AuthContext()
        auth_context2 = AuthContext()
        
        # Act
        auth_context1.set_current_user(sample_user)
        
        # Assert - Contexts are isolated
        assert auth_context1.is_authenticated is True
        assert auth_context2.is_authenticated is False
        assert auth_context1.user_id == "user-123"
        assert auth_context2.user_id is None

    def test_user_activity_tracking(self, sample_user):
        """Test user activity tracking functionality."""
        # Arrange
        auth_context = AuthContext()
        auth_context.set_current_user(sample_user)
        
        # Act
        auth_context.update_last_activity()
        
        # Assert
        assert auth_context.current_user.last_activity is not None
        assert isinstance(auth_context.current_user.last_activity, datetime)

    def test_permission_check_with_permissions(self, sample_user):
        """Test permission checking with user permissions."""
        # Arrange
        auth_context = AuthContext()
        sample_user.permissions = ["read_contracts", "write_contracts", "admin"]
        auth_context.set_current_user(sample_user)
        
        # Act & Assert
        assert auth_context.has_permission("read_contracts") is True
        assert auth_context.has_permission("write_contracts") is True
        assert auth_context.has_permission("admin") is True
        assert auth_context.has_permission("super_admin") is False

    def test_permission_check_unauthenticated(self):
        """Test permission checking when not authenticated."""
        # Arrange
        auth_context = AuthContext()
        
        # Act
        has_permission = auth_context.has_permission("read_contracts")
        
        # Assert
        assert has_permission is False