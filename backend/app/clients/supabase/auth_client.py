"""
Supabase authentication client implementation.
"""

import logging
from typing import Any, Dict, Optional
from supabase import Client
from gotrue.errors import AuthError

from ..base.client import with_retry
from ..base.interfaces import AuthOperations
from ..base.exceptions import (
    ClientError,
    ClientAuthenticationError,
    ClientConnectionError,
)
from .config import SupabaseClientConfig

logger = logging.getLogger(__name__)


class SupabaseAuthClient(AuthOperations):
    """Supabase authentication operations client."""

    def __init__(self, supabase_client: Client, config: SupabaseClientConfig):
        self.supabase_client = supabase_client
        self.config = config
        self.client_name = "SupabaseAuthClient"
        self.logger = logging.getLogger(f"{__name__}.{self.client_name}")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize auth client."""
        try:
            # Test auth service availability
            await self._test_auth_connection()
            self._initialized = True
            self.logger.info("Auth client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize auth client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize auth client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def _test_auth_connection(self) -> None:
        """Test auth service connection."""
        try:
            # Simple test of auth service - get current session (will be None if no user)
            session = self.supabase_client.auth.get_session()
            self.logger.debug(f"Auth connection test successful")
        except Exception as e:
            raise ClientConnectionError(
                f"Auth connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def authenticate_user(self, token: str) -> Dict[str, Any]:
        """Authenticate a user using their token."""
        try:
            self.logger.debug("Authenticating user with token")

            # Get user from JWT token
            user_response = self.supabase_client.auth.get_user(token)

            if not user_response.user:
                raise ClientAuthenticationError(
                    "Invalid token or user not found", client_name=self.client_name
                )

            user_data = {
                "id": user_response.user.id,
                "email": user_response.user.email,
                "phone": user_response.user.phone,
                "user_metadata": user_response.user.user_metadata or {},
                "app_metadata": user_response.user.app_metadata or {},
                "created_at": user_response.user.created_at,
                "updated_at": user_response.user.updated_at,
                "email_confirmed_at": user_response.user.email_confirmed_at,
                "phone_confirmed_at": user_response.user.phone_confirmed_at,
            }

            self.logger.debug(f"Successfully authenticated user: {user_data['id']}")
            return user_data

        except AuthError as e:
            self.logger.error(f"Auth error authenticating user: {e}")
            
            # Check if this is a JWT expiration error
            error_str = str(e).lower()
            if 'expired' in error_str or 'invalid_token' in error_str or 'jwt' in error_str:
                self.logger.info("JWT expiration or invalid token detected in auth client")
                raise ClientAuthenticationError(
                    f"Token expired or invalid: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            
            # For other auth errors
            raise ClientAuthenticationError(
                f"Authentication failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error authenticating user: {e}")
            raise ClientError(
                f"Unexpected authentication error: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information by ID."""
        try:
            self.logger.debug(f"Getting user by ID: {user_id}")

            # Note: Supabase admin API would be needed to get user by ID
            # For now, we'll query the profiles table or use auth admin API if available

            # Using service role client would be better for this operation
            result = (
                self.supabase_client.table("profiles")
                .select("*")
                .eq("id", user_id)
                .execute()
            )

            if not result.data or len(result.data) == 0:
                raise ClientError(
                    f"User not found: {user_id}", client_name=self.client_name
                )

            user_data = result.data[0]
            self.logger.debug(f"Successfully retrieved user: {user_id}")
            return user_data

        except Exception as e:
            self.logger.error(f"Error getting user {user_id}: {e}")
            raise ClientError(
                f"Failed to get user {user_id}: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user account."""
        try:
            self.logger.debug(
                f"Creating user account: {user_data.get('email', 'no-email')}"
            )

            # Extract required fields
            email = user_data.get("email")
            password = user_data.get("password")

            if not email or not password:
                raise ClientError(
                    "Email and password are required for user creation",
                    client_name=self.client_name,
                )

            # Create user with Supabase auth
            auth_response = self.supabase_client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": user_data.get("user_metadata", {})},
                }
            )

            if not auth_response.user:
                raise ClientError(
                    "Failed to create user account", client_name=self.client_name
                )

            created_user = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "phone": auth_response.user.phone,
                "user_metadata": auth_response.user.user_metadata or {},
                "created_at": auth_response.user.created_at,
                "email_confirmed_at": auth_response.user.email_confirmed_at,
            }

            self.logger.debug(f"Successfully created user: {created_user['id']}")
            return created_user

        except AuthError as e:
            self.logger.error(f"Auth error creating user: {e}")
            raise ClientError(
                f"Failed to create user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error creating user: {e}")
            raise ClientError(
                f"Unexpected error creating user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def sign_up(self, user_data: Dict[str, Any]):
        """Sign up a new user (synchronous wrapper for create_user)."""
        try:
            self.logger.debug(f"Signing up user: {user_data.get('email', 'no-email')}")

            # Extract required fields
            email = user_data.get("email")
            password = user_data.get("password")
            options = user_data.get("options", {})

            if not email or not password:
                raise ClientError(
                    "Email and password are required for user sign up",
                    client_name=self.client_name,
                )

            # Create user with Supabase auth
            auth_response = self.supabase_client.auth.sign_up(
                {"email": email, "password": password, "options": options}
            )

            self.logger.debug(
                f"Successfully signed up user: {auth_response.user.id if auth_response.user else 'unknown'}"
            )
            return auth_response

        except AuthError as e:
            self.logger.error(f"Auth error signing up user: {e}")
            raise ClientError(
                f"Failed to sign up user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error signing up user: {e}")
            raise ClientError(
                f"Unexpected error signing up user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def sign_in_with_password(self, credentials: Dict[str, Any]):
        """Sign in a user with email and password."""
        try:
            self.logger.debug(
                f"Signing in user: {credentials.get('email', 'no-email')}"
            )

            # Extract required fields
            email = credentials.get("email")
            password = credentials.get("password")

            if not email or not password:
                raise ClientError(
                    "Email and password are required for user sign in",
                    client_name=self.client_name,
                )

            # Sign in user with Supabase auth
            auth_response = self.supabase_client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            self.logger.debug(
                f"Successfully signed in user: {auth_response.user.id if auth_response.user else 'unknown'}"
            )
            return auth_response

        except AuthError as e:
            self.logger.error(f"Auth error signing in user: {e}")
            raise ClientError(
                f"Failed to sign in user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error signing in user: {e}")
            raise ClientError(
                f"Unexpected error signing in user: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def update_user(
        self, user_id: str, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user information."""
        try:
            self.logger.debug(f"Updating user: {user_id}")

            # For profile data, update the profiles table
            profile_data = {
                k: v
                for k, v in user_data.items()
                if k not in ["email", "password", "phone"]
            }

            if profile_data:
                result = (
                    self.supabase_client.table("profiles")
                    .update(profile_data)
                    .eq("id", user_id)
                    .execute()
                )

                if result.data and len(result.data) > 0:
                    updated_user = result.data[0]
                    self.logger.debug(f"Successfully updated user profile: {user_id}")
                    return updated_user

            # For auth data (email, password, phone), would need admin API
            # This is a simplified implementation
            return {"id": user_id, "updated": True}

        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {e}")
            raise ClientError(
                f"Failed to update user {user_id}: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user account."""
        try:
            self.logger.debug(f"Deleting user: {user_id}")

            # Note: This would require admin API access in production
            # For now, we'll just mark the profile as deleted
            result = (
                self.supabase_client.table("profiles")
                .update({"deleted_at": "now()", "status": "deleted"})
                .eq("id", user_id)
                .execute()
            )

            success = result.data is not None and len(result.data) > 0
            if success:
                self.logger.debug(f"Successfully marked user as deleted: {user_id}")
            else:
                self.logger.warning(f"User not found for deletion: {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {e}")
            raise ClientError(
                f"Failed to delete user {user_id}: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def reset_password(self, email: str) -> bool:
        """Initiate password reset for a user."""
        try:
            self.logger.debug(f"Initiating password reset for: {email}")

            # Send password reset email
            self.supabase_client.auth.reset_password_email(email)

            self.logger.debug(f"Successfully initiated password reset for: {email}")
            return True

        except AuthError as e:
            self.logger.error(f"Auth error resetting password for {email}: {e}")
            raise ClientError(
                f"Failed to reset password for {email}: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error resetting password for {email}: {e}")
            raise ClientError(
                f"Unexpected error resetting password for {email}: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check auth client health."""
        try:
            await self._test_auth_connection()
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "connection": "ok",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """Close auth client."""
        self._initialized = False
        self.logger.info("Auth client closed successfully")
