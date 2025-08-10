"""
Authentication Middleware for FastAPI

This middleware extracts authentication tokens from incoming requests
and sets them in the auth context for proper RLS enforcement.
"""

import logging
from typing import Optional, Tuple
import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.auth_context import AuthContext
from app.core.config import get_settings
from app.services.backend_token_service import BackendTokenService

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract authentication tokens and set auth context.

    This middleware:
    1. Extracts JWT tokens from Authorization headers
    2. Validates token format (optional validation)
    3. Sets auth context for the request lifecycle
    4. Clears context after request completion
    """

    def __init__(self, app: ASGIApp, validate_token: bool = False):
        super().__init__(app)
        self.validate_token = validate_token
        self.settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request and set auth context with token coordination.

        Args:
            request: FastAPI request object
            call_next: Next middleware or endpoint

        Returns:
            Response from the endpoint
        """
        # Extract token from request
        token, user_id, user_email = self._extract_auth_info(request)
        new_token_header = None  # Track if we need to send a new token to frontend

        # Debug: Log token type
        if token:
            logger.info(f"Processing token for user: {user_id} (token length: {len(token)}, first 20 chars: {token[:20]}...)")
            is_backend_token = BackendTokenService.is_backend_token(token)
            logger.info(f"Token type check - is_backend_token: {is_backend_token}")
        
        # If backend-issued token, check for near expiry and coordinate refresh
        if token and BackendTokenService.is_backend_token(token):
            logger.info(f"Backend token detected for user: {user_id}")
            
            # Check if backend token is near expiry (10 minutes threshold)
            if BackendTokenService.is_near_expiry(token, threshold_minutes=10):
                logger.info(f"Backend token near expiry for user: {user_id}, attempting coordinated refresh")
                
                # Attempt to refresh both tokens in coordination
                refreshed_token = await BackendTokenService.refresh_coordinated_tokens(token)
                if refreshed_token:
                    logger.info(f"Successfully refreshed coordinated tokens for user: {user_id}")
                    # Use the new backend token for this request
                    token = refreshed_token
                    # Mark that we need to send the new token to frontend
                    new_token_header = refreshed_token
                else:
                    logger.warning(f"Failed to refresh coordinated tokens for user: {user_id}")
            
            # Exchange backend token for Supabase access token for RLS
            exchanged = await BackendTokenService.ensure_supabase_access_token(token)
            if exchanged:
                # Replace token with Supabase access token so DB ops are RLS-authenticated
                logger.info(f"Successfully exchanged backend token for Supabase token (length: {len(exchanged)})")
                token = exchanged
            else:
                logger.warning(f"Failed to exchange backend token for Supabase token for user: {user_id}")
        else:
            if token:
                logger.info(f"Using Supabase token directly (not a backend token)")

        # Set auth context if token is present
        if token:
            AuthContext.set_auth_context(
                token=token,
                user_id=user_id,
                user_email=user_email,
                metadata={
                    "request_id": request.headers.get("X-Request-ID"),
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.client.host if request.client else None,
                },
            )
            logger.debug(f"Auth context set for user: {user_id or 'unknown'}")

        try:
            # Process the request
            response = await call_next(request)
            
            # If we have a new token from coordinated refresh, add it to response headers
            if new_token_header:
                response.headers["X-New-Token"] = new_token_header
                logger.info(f"Sending new coordinated token to frontend for user: {user_id}")
            
            return response
        finally:
            # Always clear auth context after request
            AuthContext.clear_auth_context()

    def _extract_auth_info(
        self, request: Request
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract authentication information from request.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (token, user_id, user_email)
        """
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None, None, None

        # Extract Bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid authorization header format")
            return None, None, None

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Optionally validate and extract claims from token
        user_id = None
        user_email = None

        if self.validate_token:
            try:
                # Note: In production, you'd validate with Supabase's JWT secret
                # For now, we'll just decode without verification to extract claims
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},  # Only for claim extraction
                )

                # Extract user information from JWT claims
                user_id = payload.get("sub")  # Standard JWT subject claim
                user_email = payload.get("email")

                # Log token metadata (without sensitive data)
                logger.info(f"Token claims extracted for user: {user_id}, email: {user_email}")

            except InvalidTokenError as e:
                logger.warning(f"Invalid token format: {str(e)}")
                # Still pass the token through - let Supabase validate it

        return token, user_id, user_email


def setup_auth_middleware(app: ASGIApp, validate_token: bool = False) -> None:
    """
    Setup authentication middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        validate_token: Whether to validate JWT tokens (default: False)
    """
    app.add_middleware(AuthContextMiddleware, validate_token=validate_token)
    logger.info("Authentication middleware configured")


# Additional middleware for specific auth scenarios


class ServiceRoleMiddleware(BaseHTTPMiddleware):
    """
    Middleware for endpoints that require service role access.

    This middleware temporarily elevates permissions for specific
    administrative endpoints while maintaining audit trails.
    """

    def __init__(self, app: ASGIApp, allowed_paths: list[str] = None):
        super().__init__(app)
        self.allowed_paths = allowed_paths or []

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Check if request path requires service role elevation.
        """
        # Check if current path needs service role
        if any(request.url.path.startswith(path) for path in self.allowed_paths):
            # Log service role usage
            logger.warning(
                f"Service role access for path: {request.url.path}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "ip_address": request.client.host if request.client else None,
                },
            )

        return await call_next(request)
