"""
Basic unit tests for database connection module.
"""

import pytest
from unittest.mock import AsyncMock, patch
import asyncpg

from app.database.connection import _setup_user_session


class TestDatabaseConnectionBasic:
    """Basic tests for database connection functionality."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = AsyncMock(spec=asyncpg.Connection)
        mock_conn.execute = AsyncMock()
        return mock_conn

    @pytest.mark.asyncio
    async def test_setup_user_session_no_user_id(self, mock_connection):
        """Test setting up session with no user ID (anonymous role)."""
        await _setup_user_session(mock_connection, None)

        # Should set anonymous role
        mock_connection.execute.assert_called_once_with(
            "SELECT set_config('role', $1, false)", "anon"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_no_token(self, mock_connection):
        """Test setting up session when no user token is available."""
        with patch("app.database.connection.AuthContext") as mock_auth:
            mock_auth.get_user_token.return_value = None

            await _setup_user_session(mock_connection, "test-user-id")

        # Should set anonymous role and log warning
        mock_connection.execute.assert_called_once_with(
            "SELECT set_config('role', $1, false)", "anon"
        )

    @pytest.mark.asyncio
    async def test_setup_user_session_jwt_import_failure(self, mock_connection):
        """Test handling when JWT library is not available."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'jwt'")
        ):
            with pytest.raises(ValueError, match="JWT verification not available"):
                await _setup_user_session(mock_connection, "test-user-id")

    @pytest.mark.asyncio
    async def test_setup_user_session_connection_error(self, mock_connection):
        """Test handling of connection-level errors."""
        mock_connection.execute.side_effect = asyncpg.InterfaceError("Connection lost")

        with pytest.raises(asyncpg.InterfaceError):
            await _setup_user_session(mock_connection, "test-user-id")
