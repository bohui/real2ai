"""
Migrated Authentication utilities using decoupled client architecture
This replaces direct Supabase client instantiation with the new client factory system
"""

import logging
from datetime import datetime, UTC
from typing import Optional
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.clients.factory import get_supabase_client
from app.core.auth_context import AuthContext
from app.core.config import get_settings
from app.services.backend_token_service import BackendTokenService
from app.clients.base.interfaces import AuthOperations, DatabaseOperations
from app.clients.base.exceptions import ClientError

logger = logging.getLogger(__name__)


def is_jwt_expired_error(error: Exception) -> bool:
    """Check if the error indicates JWT expiration."""
    error_str = str(error).lower()
    error_details = getattr(error, "details", None) or getattr(error, "message", None)

    # Check main error message
    jwt_indicators = [
        "jwt expired",
        "pgrst301",
        "token expired",
        "unauthorized",
        "invalid_token",
        "expired",
    ]

    if any(indicator in error_str for indicator in jwt_indicators):
        return True

    # Check error details/message if available
    if error_details:
        details_str = str(error_details).lower()
        if any(indicator in details_str for indicator in jwt_indicators):
            return True

    # Check if error has original_error with JWT indicators
    original_error = getattr(error, "original_error", None)
    if original_error:
        return is_jwt_expired_error(original_error)

    return False


# Security scheme for JWT tokens
security = HTTPBearer()


class User(BaseModel):
    """User model"""

    id: str
    email: str
    australian_state: str
    user_type: str
    subscription_status: str = "free"
    credits_remaining: int = 0
    preferences: dict = {}
    onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None
    onboarding_preferences: dict = {}


class TokenData(BaseModel):
    """Token payload model"""

    user_id: str
    email: str
    exp: datetime


class AuthService:
    """Authentication service using decoupled client architecture"""

    def __init__(self, auth_client: AuthOperations = None, db_service=None):
        """Initialize with optional dependency injection for testing"""
        self._auth_client = auth_client
        self._db_service = db_service
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize authentication service"""
        try:
            if not self._auth_client:
                supabase_client = await get_supabase_client()
                self._auth_client = supabase_client.auth

            if not self._db_service:
                supabase_client = await get_supabase_client()
                self._db_service = supabase_client.database

            self._initialized = True
            logger.info("Authentication service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {str(e)}")
            raise

    async def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token using decoupled client.

        Supports both Supabase user tokens and backend-issued API tokens.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # If this is a backend token, extract identity and bypass Supabase verify here
            if BackendTokenService.is_backend_token(token):
                identity = BackendTokenService.get_identity(token)
                if not identity:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                    )
                user_id, email = identity
                exp = datetime.now(UTC)
                return TokenData(user_id=user_id, email=email, exp=exp)

            # Otherwise, use Supabase auth to authenticate user token
            user_data = await self._auth_client.authenticate_user(token)

            if not user_data or "id" not in user_data or "email" not in user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

            # Extract user information
            user_id = user_data["id"]
            email = user_data["email"]

            # Get expiration from token data if available
            exp_timestamp = user_data.get("exp")
            if exp_timestamp:
                if isinstance(exp_timestamp, (int, float)):
                    exp = datetime.fromtimestamp(exp_timestamp)
                else:
                    exp = datetime.now(UTC)
            else:
                # Default to current time if no expiration found
                exp = datetime.now(UTC)

            return TokenData(user_id=user_id, email=email, exp=exp)

        except ClientError as e:
            logger.error(f"Token verification error: {str(e)}")

            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                logger.info("JWT expiration detected during token verification")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired. Please log in again.",
                )

            # For other authentication errors
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    async def get_current_user(self, token_data: TokenData) -> User:
        """Get current authenticated user using user-authenticated client for RLS."""
        if not self._initialized:
            await self.initialize()

        try:
            # Get user profile from database using decoupled client
            profile_result = await self._db_service.read(
                "profiles", {"id": token_data.user_id}, 1
            )

            logger.debug(
                f"Profile result type: {type(profile_result)}, has_data: {hasattr(profile_result, 'data')}"
            )

            # Handle both list and result object responses
            if hasattr(profile_result, "data"):
                # Result object with .data attribute
                profiles = profile_result.data
                logger.debug(
                    f"Using result.data, profiles count: {len(profiles) if profiles else 0}"
                )
            else:
                # Direct list response
                profiles = profile_result
                logger.debug(
                    f"Using direct result, profiles count: {len(profiles) if profiles else 0}"
                )

            if not profiles or len(profiles) == 0:
                logger.warning(f"No profile found for user_id: {token_data.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            profile = profiles[0]
            logger.info(
                f"Successfully loaded profile for user_id: {token_data.user_id}"
            )

            return User(
                id=profile["id"],
                email=profile["email"],
                australian_state=profile["australian_state"],
                user_type=profile["user_type"],
                subscription_status=profile.get("subscription_status", "free"),
                credits_remaining=profile.get("credits_remaining", 0),
                preferences=profile.get("preferences", {}),
                onboarding_completed=profile.get("onboarding_completed", False),
                onboarding_completed_at=profile.get("onboarding_completed_at"),
                onboarding_preferences=profile.get("onboarding_preferences", {}),
            )

        except ClientError as e:
            logger.error(f"Database error getting user: {str(e)}")

            if is_jwt_expired_error(e):
                logger.info(f"JWT expiration detected for user {token_data.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired. Please log in again.",
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve user data",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    async def health_check(self) -> dict:
        """Perform health check on authentication service"""
        try:
            if not self._initialized:
                return {"status": "unhealthy", "error": "Service not initialized"}

            return {
                "status": "healthy",
                "service": "auth_service_v2",
                "client_architecture": "decoupled",
                "features": [
                    "dependency_injection",
                    "error_handling",
                    "automatic_retries",
                    "circuit_breakers",
                ],
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get authentication service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# FastAPI dependency functions using decoupled architecture
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user using decoupled auth service"""
    try:
        auth_service = get_auth_service()
        if not auth_service._initialized:
            await auth_service.initialize()

        token_data = await auth_service.verify_token(credentials.credentials)
        return await auth_service.get_current_user(token_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication dependency error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get current user's JWT token"""
    return credentials.credentials


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""

    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# WebSocket Authentication Functions
async def get_current_user_ws(token: str) -> Optional[User]:
    """Get current authenticated user for WebSocket connections"""
    try:
        if not token or token.strip() == "":
            logger.error("No token provided for WebSocket authentication")
            return None

        # Clean token format
        if token.startswith("Bearer%20"):
            token = token.replace("Bearer%20", "")
        elif token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        # If this is a backend API token, resolve identity and fetch profile via service-role
        if BackendTokenService.is_backend_token(token):
            identity = BackendTokenService.get_identity(token)
            if not identity:
                logger.error("Invalid backend token for WebSocket authentication")
                return None
            user_id, email = identity

            # Bypass RLS to resolve the user profile
            user = await get_user_by_id_service(user_id)
            if not user:
                logger.error("User not found for backend token during WebSocket auth")
                return None

            logger.info(f"WebSocket authenticated via backend token for user {user_id}")
            return user

        auth_service = get_auth_service()
        if not auth_service._initialized:
            await auth_service.initialize()

        token_data = await auth_service.verify_token(token)
        return await auth_service.get_current_user(token_data)

    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None


# Backward compatibility functions
def verify_token(token: str) -> TokenData:
    """Backward compatibility: Synchronous token verification"""
    import asyncio

    auth_service = get_auth_service()
    return asyncio.run(auth_service.verify_token(token))


# ----------------------------
# WebSocket token utilities
# ----------------------------


def _get_jwt_secret_and_alg() -> tuple[str, str]:
    settings = get_settings()
    secret = settings.jwt_secret_key
    if not secret:
        # Fall back to anon key to avoid hard failure in dev; strongly recommend setting JWT_SECRET_KEY
        secret = settings.supabase_anon_key
    alg = settings.jwt_algorithm or "HS256"
    return secret, alg


def generate_ws_token(user_id: str, expires_in_seconds: int = 120) -> str:
    """Generate a short-lived server-signed token for WebSocket handshakes."""
    secret, alg = _get_jwt_secret_and_alg()
    payload = {
        "sub": user_id,
        "type": "ws",
        "exp": int(datetime.now(UTC).timestamp()) + int(expires_in_seconds),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=alg)


def verify_ws_token(token: str) -> Optional[str]:
    """Verify server-signed WS token and return user_id if valid."""
    try:
        secret, alg = _get_jwt_secret_and_alg()
        payload = jwt.decode(token, secret, algorithms=[alg])
        if payload.get("type") != "ws":
            return None
        return payload.get("sub")
    except Exception:
        return None


async def get_user_by_id_service(user_id: str) -> Optional[User]:
    """Fetch user profile using service-role client (bypasses RLS for identity resolution)."""
    try:
        # Get service role client
        client = await get_supabase_client(use_service_role=True)

        # Use the raw Supabase client directly to bypass auth context issues
        # This bypasses the database client's auth context application entirely
        result = (
            client.supabase_client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if result.data and len(result.data) > 0:
            profile = result.data[0]
            return User(
                id=profile["id"],
                email=profile["email"],
                australian_state=profile["australian_state"],
                user_type=profile["user_type"],
                subscription_status=profile.get("subscription_status", "free"),
                credits_remaining=profile.get("credits_remaining", 0),
                preferences=profile.get("preferences", {}),
                onboarding_completed=profile.get("onboarding_completed", False),
                onboarding_completed_at=profile.get("onboarding_completed_at"),
                onboarding_preferences=profile.get("onboarding_preferences", {}),
            )
        return None
    except Exception as e:
        logger.error(f"Error fetching user by ID {user_id}: {str(e)}")
        return None
