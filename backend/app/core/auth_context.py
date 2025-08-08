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
    async def get_authenticated_client(cls, require_auth: bool = True):
        """
        Get Supabase client with proper authentication.

        Args:
            require_auth: If True, raises exception when no token is present

        Returns:
            Authenticated Supabase client

        Raises:
            HTTPException: If authentication is required but no token is present
        """
        token = cls.get_user_token()

        if require_auth and not token:
            logger.warning("Authentication required but no token in context")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get base client
        client = await get_supabase_client()

        if token:
            # Set user token for RLS enforcement
            client.set_user_token(token)
            logger.debug(f"Created authenticated client for user: {cls.get_user_id()}")
        else:
            # No user token present; returning anon-key client (RLS enforced by default)
            logger.warning(
                "No user token in context; returning anon client (RLS enforced)"
            )

        return client

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
