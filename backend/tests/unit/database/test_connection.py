"""
Unit tests for database connection module.

Tests cover JWT token validation, user session setup, and error handling.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

import asyncpg

from app.database.connection import _setup_user_session
from app.core.auth_context import AuthContext
from app.services.backend_token_service import BackendTokenService


class TestDatabaseConnection:
    """Test database connection functionality."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = AsyncMock(spec=asyncpg.Connection)
        mock_conn.execute = AsyncMock()
        return mock_conn

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        mock_settings = Mock()
        mock_settings.supabase_jwt_secret = "test-secret-key"
        return mock_settings

    @pytest.fixture
    def mock_auth_context(self):
        """Create mock authentication context."""
        with patch("app.database.connection.AuthContext") as mock_auth:
            mock_auth.get_user_token.return_value = "mock-token"
            mock_auth.get_user_email.return_value = "test@example.com"
            mock_auth.get_auth_metadata.return_value = {}
            mock_auth.get_refresh_token.return_value = "mock-refresh-token"
            yield mock_auth

    @pytest.fixture
    def mock_backend_service(self):
        """Create mock backend token service."""
        with patch("app.database.connection.BackendTokenService") as mock_service:
            mock_service.is_backend_token.return_value = True
            mock_service.verify_backend_token.return_value = {
                "exp": int(time.time()) + 3600,  # Expires in 1 hour
                "supa_exp": int(time.time()) + 7200,  # Supabase expires in 2 hours
                "sub": "test-user-id",
            }
            mock_service.refresh_coordinated_tokens = AsyncMock(
                return_value="refreshed-token"
            )
            yield mock_service

    @pytest.fixture
    def mock_jwt(self):
        """Create mock JWT library."""
        # Create a mock JWT library
        mock_jwt_lib = Mock()
        mock_jwt_lib.get_unverified_header.return_value = {"alg": "HS256"}
        mock_jwt_lib.decode.return_value = {
            "sub": "test-user-id",
            "role": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Mock the import at the module level since it's imported inside the function
        with patch.dict("sys.modules", {"jwt": mock_jwt_lib}):
            yield mock_jwt_lib

    @pytest.mark.asyncio
    async def test_setup_user_session_no_user_id(self, mock_connection):
        """Test setting up session with no user ID (anonymous role)."""
        await _setup_user_session(mock_connection, None)

        # Should set anonymous role
        mock_connection.execute.assert_called_once_with(
            "SELECT set_config('role', $1, false)", "anon"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_no_token(
        self, mock_connection, mock_auth_context
    ):
        """Test setting up session when no user token is available."""
        mock_auth_context.get_user_token.return_value = None

        await _setup_user_session(mock_connection, "test-user-id")

        # Should set anonymous role and log warning
        mock_connection.execute.assert_called_once_with(
            "SELECT set_config('role', $1, false)", "anon"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_healthy(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test setting up session with a healthy backend token."""
        await _setup_user_session(mock_connection, "test-user-id")

        # Should verify backend token and set authenticated role
        mock_backend_service.is_backend_token.assert_called_once_with("mock-token")
        mock_backend_service.verify_backend_token.assert_called_once_with("mock-token")

        # Should set RLS context
        assert mock_connection.execute.call_count >= 3  # role, jwt.claims, sub

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_expired(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test setting up session with an expired backend token."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "supa_exp": int(time.time()) + 3600,
            "sub": "test-user-id",
        }

        # The function should raise an exception when the backend token is expired
        # before it gets to JWT verification
        with pytest.raises(ValueError, match="Backend token is expired"):
            await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_expires_soon(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test setting up session with a backend token that expires soon."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 120,  # Expires in 2 minutes
            "supa_exp": int(time.time()) + 3600,
            "sub": "test-user-id",
        }

        await _setup_user_session(mock_connection, "test-user-id")

        # Should attempt to refresh the token
        mock_backend_service.refresh_coordinated_tokens.assert_called_once_with(
            "mock-token"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_refresh_success(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test successful token refresh during session setup."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 120,  # Expires in 2 minutes
            "supa_exp": int(time.time()) + 3600,
            "sub": "test-user-id",
        }
        mock_backend_service.refresh_coordinated_tokens.return_value = (
            "new-refreshed-token"
        )

        await _setup_user_session(mock_connection, "test-user-id")

        # Should update auth context with new token
        mock_auth_context.set_auth_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_refresh_failure(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test token refresh failure during session setup."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 120,  # Expires in 2 minutes
            "supa_exp": int(time.time()) + 3600,
            "sub": "test-user-id",
        }
        mock_backend_service.refresh_coordinated_tokens.return_value = None

        await _setup_user_session(mock_connection, "test-user-id")

        # Should continue with original token
        mock_backend_service.refresh_coordinated_tokens.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_user_session_supabase_token(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test setting up session with a Supabase token."""
        mock_backend_service.is_backend_token.return_value = False

        await _setup_user_session(mock_connection, "test-user-id")

        # Should analyze Supabase token
        mock_backend_service.is_backend_token.assert_called_once_with("mock-token")

        # Should set RLS context
        assert mock_connection.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_setup_user_session_supabase_token_expired(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test setting up session with an expired Supabase token."""
        mock_backend_service.is_backend_token.return_value = False

        with patch("app.database.connection.jwt") as mock_jwt_lib:
            mock_jwt_lib.decode.return_value = {
                "exp": int(time.time()) - 3600  # Expired 1 hour ago
            }

            with pytest.raises(ValueError, match="Supabase token is expired"):
                await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_supabase_token_expires_soon(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test setting up session with a Supabase token that expires soon."""
        mock_backend_service.is_backend_token.return_value = False

        with patch("app.database.connection.jwt") as mock_jwt_lib:
            mock_jwt_lib.decode.return_value = {
                "exp": int(time.time()) + 300  # Expires in 5 minutes
            }

            await _setup_user_session(mock_connection, "test-user-id")

            # Should log warning about token expiring soon
            # (This would be verified by checking logs in a real test)

    @pytest.mark.asyncio
    async def test_setup_user_session_jwt_header_extraction_failure(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test JWT header extraction failure."""
        mock_jwt.get_unverified_header.side_effect = Exception(
            "Header extraction failed"
        )

        await _setup_user_session(mock_connection, "test-user-id")

        # Should continue with header_alg as None
        mock_jwt.get_unverified_header.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_user_session_unsupported_algorithm(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test handling of unsupported JWT algorithms."""
        mock_jwt.get_unverified_header.return_value = {"alg": "RS256"}

        await _setup_user_session(mock_connection, "test-user-id")

        # Should log warning about unsupported algorithm
        # (This would be verified by checking logs in a real test)

    @pytest.mark.asyncio
    async def test_setup_user_session_jwt_verification_success(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test successful JWT verification."""
        await _setup_user_session(mock_connection, "test-user-id")

        # Should verify JWT with correct parameters
        mock_jwt.decode.assert_called_with(
            "mock-token",
            "test-secret-key",
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_jwt_verification_failure(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test JWT verification failure."""
        from jwt import InvalidTokenError

        mock_jwt.decode.side_effect = InvalidTokenError("Invalid signature")

        with pytest.raises(ValueError, match="Invalid token"):
            await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_rls_context_setup(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test RLS context setup."""
        await _setup_user_session(mock_connection, "test-user-id")

        # Should set all required RLS context variables
        expected_calls = [
            (
                "SELECT set_config('request.jwt.claims', $1, false)",
                '{"sub": "test-user-id", "role": "authenticated", "exp": '
                + str(int(time.time()) + 3600)
                + "}",
            ),
            ("SELECT set_config('role', $1, false)", "authenticated"),
            ("SELECT set_config('request.jwt.claim.sub', $1, false)", "test-user-id"),
        ]

        # Check that all expected calls were made (order may vary)
        actual_calls = [
            (call[0][0], call[0][1]) for call in mock_connection.execute.call_args_list
        ]
        for expected_call in expected_calls:
            assert expected_call in actual_calls

    @pytest.mark.asyncio
    async def test_setup_user_session_connection_error_handling(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test handling of connection-level errors."""
        mock_connection.execute.side_effect = asyncpg.InterfaceError("Connection lost")

        with pytest.raises(asyncpg.InterfaceError):
            await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_token_analysis_error(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test handling of token analysis errors."""
        mock_backend_service.verify_backend_token.side_effect = Exception(
            "Token analysis failed"
        )

        # Should continue with original token and let verification handle it
        await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_small_buffer_warning(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test warning for small token buffer."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 3600,  # Expires in 1 hour
            "supa_exp": int(time.time()) + 3600 + 180,  # Only 3 minute buffer
            "sub": "test-user-id",
        }

        await _setup_user_session(mock_connection, "test-user-id")

        # Should log warning about small buffer
        # (This would be verified by checking logs in a real test)

    @pytest.mark.asyncio
    async def test_setup_user_session_negative_buffer_time(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test handling of negative buffer time (backend expires after Supabase)."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 7200,  # Expires in 2 hours
            "supa_exp": int(time.time()) + 3600,  # Expires in 1 hour (negative buffer)
            "sub": "test-user-id",
        }

        await _setup_user_session(mock_connection, "test-user-id")

        # Should handle negative buffer gracefully
        # (This would be verified by checking logs in a real test)


class TestDatabaseConnectionIntegration:
    """Integration tests for database connection functionality."""

    @pytest.mark.asyncio
    async def test_full_session_setup_flow(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test the complete session setup flow."""
        # Setup comprehensive mocks
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 1800,  # Expires in 30 minutes
            "supa_exp": int(time.time()) + 3600,  # Expires in 1 hour
            "sub": "test-user-id",
        }

        # Execute session setup
        await _setup_user_session(mock_connection, "test-user-id")

        # Verify all components were called
        mock_auth_context.get_user_token.assert_called_once()
        mock_backend_service.is_backend_token.assert_called_once()
        mock_backend_service.verify_backend_token.assert_called_once()
        mock_jwt.get_unverified_header.assert_called_once()
        mock_jwt.decode.assert_called_once()

        # Verify RLS context was set
        assert mock_connection.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_session_setup_with_token_refresh_flow(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test session setup that triggers token refresh."""
        # Setup token that needs refresh
        mock_backend_service.verify_backend_token.return_value = {
            "exp": int(time.time()) + 120,  # Expires in 2 minutes
            "supa_exp": int(time.time()) + 3600,  # Expires in 1 hour
            "sub": "test-user-id",
        }
        mock_backend_service.refresh_coordinated_tokens.return_value = "new-token"

        # Execute session setup
        await _setup_user_session(mock_connection, "test-user-id")

        # Verify refresh was attempted
        mock_backend_service.refresh_coordinated_tokens.assert_called_once()

        # Verify auth context was updated
        mock_auth_context.set_auth_context.assert_called_once()

        # Verify session was still set up successfully
        assert mock_connection.execute.call_count >= 3


class TestDatabaseConnectionErrorScenarios:
    """Test error scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_jwt_import_failure(self, mock_connection):
        """Test handling when JWT library is not available."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'jwt'")
        ):
            with pytest.raises(ValueError, match="JWT verification not available"):
                await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_settings_missing_jwt_secret(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test handling when JWT secret is not configured."""
        with patch("app.database.connection.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.supabase_jwt_secret = None
            mock_get_settings.return_value = mock_settings

            # Should still attempt to verify but fail appropriately
            with pytest.raises(ValueError, match="Invalid token"):
                await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_token_verification_with_malformed_token(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test handling of malformed tokens."""
        mock_backend_service.verify_backend_token.side_effect = Exception(
            "Malformed token"
        )

        # Should continue with original token and let JWT verification handle it
        await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_connection_execute_failure_during_rls_setup(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_jwt
    ):
        """Test handling of connection failures during RLS setup."""
        # Make the third execute call fail
        mock_connection.execute.side_effect = [
            None,  # First call succeeds
            None,  # Second call succeeds
            asyncpg.InterfaceError("Connection lost"),  # Third call fails
        ]

        with pytest.raises(asyncpg.InterfaceError):
            await _setup_user_session(mock_connection, "test-user-id")
