"""
Authentication Context Management for Supabase RLS

This module provides thread-safe context management for user authentication tokens,
enabling proper Row Level Security (RLS) enforcement in Supabase operations.

Key Features:
- Thread-safe token storage using contextvars
- Automatic token propagation through request lifecycle
- Support for both user tokens and service role operations
- Clean separation between authentication and business logic
"""

from contextvars import ContextVar
from typing import Optional, Dict, Any
from datetime import datetime, UTC
import logging
from functools import wraps

from fastapi import HTTPException, status
from app.clients import get_supabase_client

logger = logging.getLogger(__name__)

# Thread-safe context variables
_user_token: ContextVar[Optional[str]] = ContextVar("user_token", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_user_email: ContextVar[Optional[str]] = ContextVar("user_email", default=None)
_auth_metadata: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "auth_metadata", default=None
)
_refresh_token: ContextVar[Optional[str]] = ContextVar("refresh_token", default=None)


class AuthContext:
    """
    Authentication context manager for secure token propagation.

    This class provides methods to manage authentication context throughout
    the request lifecycle, ensuring proper RLS enforcement and token security.
    """

    @classmethod
    def set_auth_context(
        cls,
        token: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        refresh_token: Optional[str] = None,
    ) -> None:
        """
        Set authentication context for the current request.

        Args:
            token: JWT token from Supabase auth
            user_id: Optional user ID (extracted from token if not provided)
            user_email: Optional user email
            metadata: Optional additional metadata
        """
        _user_token.set(token)
        _refresh_token.set(refresh_token)

        if user_id:
            _user_id.set(user_id)

        if user_email:
            _user_email.set(user_email)

        if metadata:
            _auth_metadata.set(metadata)

        logger.debug(f"Auth context set for user: {user_id or 'unknown'}")

    @classmethod
    def clear_auth_context(cls) -> None:
        """Clear all authentication context variables."""
        _user_token.set(None)
        _user_id.set(None)
        _user_email.set(None)
        _auth_metadata.set(None)
        _refresh_token.set(None)

        logger.debug("Auth context cleared")

    @classmethod
    def get_user_token(cls) -> Optional[str]:
        """Get current user token from context."""
        return _user_token.get()

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get current user ID from context."""
        return _user_id.get()

    @classmethod
    def get_user_email(cls) -> Optional[str]:
        """Get current user email from context."""
        return _user_email.get()

    @classmethod
    def get_auth_metadata(cls) -> Optional[Dict[str, Any]]:
        """Get current auth metadata from context."""
        return _auth_metadata.get()

    @classmethod
    def get_refresh_token(cls) -> Optional[str]:
        """Get current refresh token from context."""
        return _refresh_token.get()

    @classmethod
    def get_current_context(cls):
        """
        Get current authentication context as object.

        Returns:
            SimpleNamespace: Object containing current auth context with attributes:
                - user_id: Current user ID
                - user_email: Current user email
                - token: Current JWT token
                - metadata: Current auth metadata
                - refresh_token: Current refresh token
                - is_authenticated: Boolean indicating if user is authenticated
        """
        from types import SimpleNamespace

        return SimpleNamespace(
            user_id=cls.get_user_id(),
            user_email=cls.get_user_email(),
            token=cls.get_user_token(),
            metadata=cls.get_auth_metadata(),
            refresh_token=cls.get_refresh_token(),
            is_authenticated=cls.is_authenticated(),
        )

    @classmethod
    async def get_authenticated_client(
        cls, require_auth: bool = True, isolated: bool = False
    ):
        """
        Get Supabase client with proper authentication.

        Args:
            require_auth: If True, raises exception when no token is present
            isolated: If True, creates isolated client to avoid token race conditions

        Returns:
            Authenticated Supabase client

        Raises:
            HTTPException: If authentication is required but no token is present
        """
        token = cls.get_user_token()
        refresh_token = cls.get_refresh_token()

        if require_auth and not token:
            logger.warning("Authentication required but no token in context")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if isolated:
            # Create isolated client instance to avoid token mutation race conditions
            client = await cls._create_isolated_client()
        else:
            # Get base client (shared factory instance)
            client = await get_supabase_client()

        if token:
            # Ensure we always use a Supabase access token for DB ops (not backend API tokens)
            try:
                # Lazy import to avoid circular dependency at module import time
                from app.services.backend_token_service import (
                    BackendTokenService as _BackendTokenService,
                )

                if _BackendTokenService.is_backend_token(token):
                    exchanged = await _BackendTokenService.ensure_supabase_access_token(
                        token
                    )
                    if exchanged:
                        token = exchanged
                        # If we don't have a refresh token yet, try to pull from mapping
                        if not refresh_token:
                            mapping = (
                                _BackendTokenService.get_mapping(cls.get_user_token())
                                or {}
                            )
                            refresh_token = mapping.get("supabase_refresh_token")
                        logger.info(
                            "Exchanged backend token for Supabase token in authenticated client"
                        )
                    else:
                        logger.warning(
                            "Failed to exchange backend token for Supabase token in authenticated client"
                        )
            except Exception as exchange_error:
                logger.debug(f"Token exchange skipped due to error: {exchange_error}")
            # Add JWT timing diagnostics
            # try:
            #     from app.utils.jwt_diagnostics import log_jwt_timing_issue
            #     log_jwt_timing_issue(token, f"AuthContext.get_authenticated_client(isolated={isolated})")
            # except Exception as diag_error:
            #     logger.debug(f"JWT diagnostics failed: {diag_error}")

            # Set user token for RLS enforcement
            client.set_user_token(token, refresh_token)
            logger.info(
                f"Created {'isolated ' if isolated else ''}authenticated client for user: {cls.get_user_id()}, token length: {len(token) if token else 0}"
            )
        else:
            # No user token present; returning anon-key client (RLS enforced by default)
            logger.warning(
                "No user token in context; returning anon client (RLS enforced)"
            )

        return client

    @classmethod
    async def _create_isolated_client(cls):
        """
        Create a new isolated Supabase client instance.

        This avoids token mutation race conditions in concurrent background tasks
        by ensuring each task gets its own client instance.
        """
        from app.clients.factory import get_client_factory
        from app.clients.supabase import SupabaseClient
        from supabase import create_client
        from app.clients.supabase.auth_client import SupabaseAuthClient
        from app.clients.supabase.database_client import SupabaseDatabaseClient

        # Get config from factory but create new instance
        factory = get_client_factory()
        base_client = factory.get_client("supabase")
        if not base_client.is_initialized:
            await factory.initialize_client("supabase")

        # Create new isolated client with same config
        raw_client = create_client(base_client.config.url, base_client.config.anon_key)

        isolated_client = SupabaseClient(base_client.config)
        isolated_client._supabase_client = raw_client
        isolated_client._auth_client = SupabaseAuthClient(
            raw_client, base_client.config
        )
        isolated_client._db_client = SupabaseDatabaseClient(
            raw_client, base_client.config
        )
        await isolated_client._db_client.initialize()
        isolated_client._initialized = True

        logger.debug("Created isolated Supabase client instance")
        return isolated_client

    @classmethod
    async def get_isolated_authenticated_client(cls, require_auth: bool = True):
        """
        Get an isolated Supabase client instance for background tasks.

        This creates a new client instance to prevent token mutation race conditions
        that occur when multiple concurrent tasks share the same client.

        Args:
            require_auth: If True, raises exception when no token is present

        Returns:
            Isolated authenticated Supabase client
        """
        return await cls.get_authenticated_client(
            require_auth=require_auth, isolated=True
        )

    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if user is authenticated."""
        return cls.get_user_token() is not None

    @classmethod
    def require_auth(cls, func):
        """
        Decorator to require authentication for a function.

        Usage:
            @AuthContext.require_auth
            async def protected_function():
                # Function will only execute if user is authenticated
                pass
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cls.is_authenticated():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            return await func(*args, **kwargs)

        return wrapper

    @classmethod
    def create_task_context(cls) -> Dict[str, Any]:
        """
        Create serializable context for background tasks.

        Returns:
            Dictionary containing auth context that can be stored/transmitted
        """
        return {
            "user_token": cls.get_user_token(),
            "user_id": cls.get_user_id(),
            "user_email": cls.get_user_email(),
            "auth_metadata": cls.get_auth_metadata(),
            "refresh_token": cls.get_refresh_token(),
            "created_at": datetime.now(UTC).isoformat(),
        }

    @classmethod
    def restore_task_context(cls, task_context: Dict[str, Any]) -> None:
        """
        Restore auth context from task context dictionary.

        Args:
            task_context: Context dictionary from create_task_context()
        """
        cls.set_auth_context(
            token=task_context.get("user_token"),
            user_id=task_context.get("user_id"),
            user_email=task_context.get("user_email"),
            metadata=task_context.get("auth_metadata", {}),
            refresh_token=task_context.get("refresh_token"),
        )

        logger.debug(
            f"Restored task context for user: {task_context.get('user_id', 'unknown')}"
        )

    @classmethod
    def log_auth_action(
        cls, action: str, resource_type: str, resource_id: Optional[str] = None
    ) -> None:
        """
        Log authentication-related actions for audit trail.

        Args:
            action: Action being performed (e.g., "create", "read", "update", "delete")
            resource_type: Type of resource being accessed
            resource_id: Optional ID of specific resource
        """
        user_id = cls.get_user_id() or "anonymous"
        user_email = cls.get_user_email() or "unknown"

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "authenticated": cls.is_authenticated(),
        }

        logger.info(f"Auth action: {action} on {resource_type}", extra=log_entry)


def with_auth_context(token: str, user_id: Optional[str] = None):
    """
    Context manager for temporary auth context.

    Usage:
        async with with_auth_context(token, user_id):
            # Perform authenticated operations
            client = await AuthContext.get_authenticated_client()
    """

    class AuthContextManager:
        def __init__(self, token: str, user_id: Optional[str] = None):
            self.token = token
            self.user_id = user_id
            self.previous_token = None
            self.previous_user_id = None

        def __enter__(self):
            # Save current context
            self.previous_token = AuthContext.get_user_token()
            self.previous_user_id = AuthContext.get_user_id()

            # Set new context
            AuthContext.set_auth_context(self.token, self.user_id)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore previous context
            if self.previous_token:
                AuthContext.set_auth_context(self.previous_token, self.previous_user_id)
            else:
                AuthContext.clear_auth_context()

    return AuthContextManager(token, user_id)


# Convenience function for background tasks
async def get_isolated_authenticated_client(require_auth: bool = True):
    """
    Convenience function to get an isolated authenticated client.

    This is the recommended way to get clients in background tasks to avoid
    JWT token race conditions from shared client state.
    """
    return await AuthContext.get_isolated_authenticated_client(
        require_auth=require_auth
    )
