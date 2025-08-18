"""
Simplified unit tests for database connection module.

Tests cover basic user session setup and error handling scenarios.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncpg

from app.database.connection import _setup_user_session


class TestDatabaseConnectionSimple:
    """Test database connection functionality with simplified mocking."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = AsyncMock(spec=asyncpg.Connection)
        mock_conn.execute = AsyncMock()
        return mock_conn

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
                "exp": 9999999999,  # Far future expiration
                "supa_exp": 9999999999,
                "sub": "test-user-id",
            }
            mock_service.refresh_coordinated_tokens = AsyncMock(
                return_value="refreshed-token"
            )
            yield mock_service

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        with patch("app.database.connection.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.supabase_jwt_secret = "test-secret-key"
            mock_get_settings.return_value = mock_settings
            yield mock_settings

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
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test setting up session with a healthy backend token."""
        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

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
            "exp": 0,  # Expired
            "supa_exp": 9999999999,
            "sub": "test-user-id",
        }

        # The function should raise an exception when the backend token is expired
        with pytest.raises(ValueError, match="Backend token is expired"):
            await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_backend_token_expires_soon(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test setting up session with a backend token that expires soon."""
        mock_backend_service.verify_backend_token.return_value = {
            "exp": 120,  # Expires in 2 minutes
            "supa_exp": 9999999999,
            "sub": "test-user-id",
        }

        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

            await _setup_user_session(mock_connection, "test-user-id")

        # Should attempt to refresh the token
        mock_backend_service.refresh_coordinated_tokens.assert_called_once_with(
            "mock-token"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_supabase_token(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test setting up session with a Supabase token."""
        mock_backend_service.is_backend_token.return_value = False

        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

            await _setup_user_session(mock_connection, "test-user-id")

        # Should analyze Supabase token
        mock_backend_service.is_backend_token.assert_called_once_with("mock-token")

        # Should set RLS context
        assert mock_connection.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_setup_user_session_supabase_token_expired(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test setting up session with an expired Supabase token."""
        mock_backend_service.is_backend_token.return_value = False

        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.decode.return_value = {"exp": 0}  # Expired
            mock_import.return_value = mock_jwt

            with pytest.raises(ValueError, match="Supabase token is expired"):
                await _setup_user_session(mock_connection, "test-user-id")

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
    async def test_setup_user_session_rls_context_setup(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test RLS context setup."""
        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

            await _setup_user_session(mock_connection, "test-user-id")

        # Should set all required RLS context variables
        expected_calls = [
            (
                "SELECT set_config('request.jwt.claims', $1, false)",
                '{"sub": "test-user-id", "role": "authenticated", "exp": 9999999999}',
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
    async def test_setup_user_session_jwt_import_failure(self, mock_connection):
        """Test handling when JWT library is not available."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'jwt'")
        ):
            with pytest.raises(ValueError, match="JWT verification not available"):
                await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_settings_missing_jwt_secret(
        self, mock_connection, mock_auth_context, mock_backend_service
    ):
        """Test handling when JWT secret is not configured."""
        with patch("app.database.connection.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.supabase_jwt_secret = None
            mock_get_settings.return_value = mock_settings

            # Mock JWT import to avoid import errors
            with patch("builtins.__import__") as mock_import:
                mock_jwt = Mock()
                mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
                mock_jwt.decode.side_effect = Exception("Invalid signature")
                mock_import.return_value = mock_jwt

                # Should still attempt to verify but fail appropriately
                with pytest.raises(ValueError, match="Invalid token"):
                    await _setup_user_session(mock_connection, "test-user-id")


class TestDatabaseConnectionIntegrationSimple:
    """Integration tests for database connection functionality."""

    @pytest.mark.asyncio
    async def test_full_session_setup_flow(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test the complete session setup flow."""
        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

            # Execute session setup
            await _setup_user_session(mock_connection, "test-user-id")

        # Verify all components were called
        mock_auth_context.get_user_token.assert_called_once()
        mock_backend_service.is_backend_token.assert_called_once()
        mock_backend_service.verify_backend_token.assert_called_once()

        # Verify RLS context was set
        assert mock_connection.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_session_setup_with_token_refresh_flow(
        self, mock_connection, mock_auth_context, mock_backend_service, mock_settings
    ):
        """Test session setup that triggers token refresh."""
        # Setup token that needs refresh
        mock_backend_service.verify_backend_token.return_value = {
            "exp": 120,  # Expires in 2 minutes
            "supa_exp": 9999999999,
            "sub": "test-user-id",
        }
        mock_backend_service.refresh_coordinated_tokens.return_value = "new-token"

        # Mock JWT import to avoid import errors
        with patch("builtins.__import__") as mock_import:
            mock_jwt = Mock()
            mock_jwt.get_unverified_header.return_value = {"alg": "HS256"}
            mock_jwt.decode.return_value = {
                "sub": "test-user-id",
                "role": "authenticated",
                "exp": 9999999999,
            }
            mock_import.return_value = mock_jwt

            # Execute session setup
            await _setup_user_session(mock_connection, "test-user-id")

        # Verify refresh was attempted
        mock_backend_service.refresh_coordinated_tokens.assert_called_once()

        # Verify session was still set up successfully
        assert mock_connection.execute.call_count >= 3
