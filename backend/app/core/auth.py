"""
Migrated Authentication utilities using decoupled client architecture
This replaces direct Supabase client instantiation with the new client factory system
"""

import logging
from datetime import datetime, UTC
import json
from typing import Mapping
from uuid import UUID
from typing import Optional
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.clients.factory import get_supabase_client
from app.core.config import get_settings
from app.services.backend_token_service import BackendTokenService
from app.clients.base.interfaces import AuthOperations
from app.services.repositories.profiles_repository import ProfilesRepository
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
class CustomHTTPBearer(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403 for authentication issues."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException as e:
            # Convert 403 to 401 for authentication issues
            if e.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )
            raise


security = CustomHTTPBearer()


class User(BaseModel):
    """User model"""

    id: str
    email: str
    australian_state: str
    user_type: str
    user_role: str = "user"
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
            # Fetch user profile using repository pattern (asyncpg + RLS)
            repo = ProfilesRepository(user_id=UUID(token_data.user_id))
            profile = await repo.get_profile()

            if not profile:
                logger.warning(f"No profile found for user_id: {token_data.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated",
                )

            logger.info(
                f"Successfully loaded profile for user_id: {token_data.user_id}"
            )

            def _to_dict(value: object) -> dict:
                if value is None:
                    return {}
                if isinstance(value, Mapping):
                    return dict(value)
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return User(
                id=str(profile.id),
                email=profile.email,
                australian_state=profile.australian_state,
                user_type=profile.user_type,
                user_role=getattr(profile, "user_role", "user"),
                subscription_status=profile.subscription_status or "free",
                credits_remaining=profile.credits_remaining or 0,
                preferences=_to_dict(profile.preferences),
                onboarding_completed=profile.onboarding_completed,
                onboarding_completed_at=profile.onboarding_completed_at,
                onboarding_preferences=_to_dict(profile.onboarding_preferences),
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


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify they have admin privileges."""
    try:
        # Use service role to check profile role securely (bypasses RLS)
        client = await get_supabase_client(use_service_role=True)
        result = (
            client.supabase_client.table("profiles")
            .select("user_role")
            .eq("id", current_user.id)
            .limit(1)
            .execute()
        )

        role = None
        if result.data and len(result.data) > 0:
            role = result.data[0].get("user_role")

        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required. Please contact support if you need access.",
            )

        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify admin role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get current user's JWT token"""
    return credentials.credentials


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        CustomHTTPBearer(auto_error=False)
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
    """
    Get JWT secret and algorithm with secure fallback handling.

    Security Requirements:
    - Production MUST have JWT_SECRET_KEY set - no fallbacks allowed
    - Development can use generated secret with warning
    - Never use anon key as JWT secret (authentication bypass vulnerability)
    """
    import secrets

    settings = get_settings()
    secret = settings.jwt_secret_key
    alg = settings.jwt_algorithm or "HS256"

    if not secret:
        # Check if we're in production - FAIL HARD
        is_production = settings.environment.lower() in ("production", "prod", "live")

        if is_production:
            logger.critical(
                "CRITICAL SECURITY ERROR: JWT_SECRET_KEY not set in production environment. "
                "This is a mandatory security requirement. Application startup failed."
            )
            raise ValueError(
                "JWT_SECRET_KEY must be set in production environment. "
                "Cannot start application without proper JWT secret configuration."
            )

        # Development environment - generate secure secret with warning
        logger.warning(
            "JWT_SECRET_KEY not set in development environment. "
            "Generating secure random secret for this session. "
            "For production deployment, JWT_SECRET_KEY MUST be configured."
        )

        # Generate cryptographically secure random secret (256 bits)
        secret = secrets.token_urlsafe(32)

        logger.info(
            f"Generated secure JWT secret for development (length: {len(secret)} chars). "
            "This secret will change on each restart. Set JWT_SECRET_KEY for persistence."
        )
    else:
        # Validate secret strength in production
        is_production = settings.environment.lower() in ("production", "prod", "live")
        if is_production and len(secret) < 32:
            logger.warning(
                f"JWT secret is short ({len(secret)} chars) for production. "
                "Recommend at least 32 characters for security."
            )

        logger.info("Using configured JWT_SECRET_KEY for token signing")

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


def validate_jwt_configuration() -> dict[str, any]:
    """
    Validate JWT configuration on application startup.

    Returns validation results with status and recommendations.
    Should be called during application initialization.
    """
    try:
        settings = get_settings()
        is_production = settings.environment.lower() in ("production", "prod", "live")

        validation_result = {
            "status": "valid",
            "environment": settings.environment,
            "is_production": is_production,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Check JWT secret configuration
        if not settings.jwt_secret_key:
            if is_production:
                validation_result["status"] = "critical"
                validation_result["issues"].append(
                    "JWT_SECRET_KEY not configured in production environment"
                )
                validation_result["recommendations"].append(
                    "Set JWT_SECRET_KEY environment variable with at least 32 characters"
                )
            else:
                validation_result["warnings"].append(
                    "JWT_SECRET_KEY not set - will use generated secret in development"
                )
                validation_result["recommendations"].append(
                    "Set JWT_SECRET_KEY for consistent development sessions"
                )
        else:
            # Validate secret strength
            secret_length = len(settings.jwt_secret_key)
            if secret_length < 32:
                if is_production:
                    validation_result["status"] = "warning"
                    validation_result["warnings"].append(
                        f"JWT secret is short ({secret_length} chars) for production"
                    )
                    validation_result["recommendations"].append(
                        "Use at least 32 characters for JWT_SECRET_KEY in production"
                    )

            # Check if secret looks like anon key (potential misconfiguration)
            if settings.jwt_secret_key == settings.supabase_anon_key:
                validation_result["status"] = "critical"
                validation_result["issues"].append(
                    "JWT_SECRET_KEY appears to be set to Supabase anon key - security risk"
                )
                validation_result["recommendations"].append(
                    "Generate unique JWT_SECRET_KEY separate from Supabase keys"
                )

        # Check algorithm configuration
        if settings.jwt_algorithm not in ["HS256", "HS384", "HS512"]:
            validation_result["warnings"].append(
                f"Unusual JWT algorithm: {settings.jwt_algorithm}"
            )
            validation_result["recommendations"].append(
                "Consider using HS256, HS384, or HS512 for HMAC-based signing"
            )

        # Log validation results
        if validation_result["status"] == "critical":
            for issue in validation_result["issues"]:
                logger.critical(f"JWT Configuration Issue: {issue}")
        elif validation_result["status"] == "warning":
            for warning in validation_result["warnings"]:
                logger.warning(f"JWT Configuration Warning: {warning}")
        else:
            logger.info("JWT configuration validation passed")

        return validation_result

    except Exception as e:
        logger.error(f"JWT configuration validation failed: {str(e)}")
        return {
            "status": "error",
            "issues": [f"Validation failed: {str(e)}"],
            "recommendations": ["Check application configuration and logs"],
        }


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
