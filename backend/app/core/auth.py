"""
Migrated Authentication utilities using decoupled client architecture
This replaces direct Supabase client instantiation with the new client factory system
"""

import logging
from datetime import datetime, UTC
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.clients.factory import get_supabase_client
from app.clients.base.interfaces import AuthOperations, DatabaseOperations
from app.clients.base.exceptions import ClientError

logger = logging.getLogger(__name__)


def is_jwt_expired_error(error: Exception) -> bool:
    """Check if the error indicates JWT expiration."""
    error_str = str(error).lower()
    error_details = getattr(error, 'details', None) or getattr(error, 'message', None)
    
    # Check main error message
    jwt_indicators = [
        'jwt expired',
        'pgrst301',
        'token expired',
        'unauthorized',
        'invalid_token',
        'expired'
    ]
    
    if any(indicator in error_str for indicator in jwt_indicators):
        return True
    
    # Check error details/message if available
    if error_details:
        details_str = str(error_details).lower()
        if any(indicator in details_str for indicator in jwt_indicators):
            return True
    
    # Check if error has original_error with JWT indicators
    original_error = getattr(error, 'original_error', None)
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
        """Verify and decode JWT token using decoupled client"""
        if not self._initialized:
            await self.initialize()

        try:
            # Use the decoupled auth client
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
                    detail="Token has expired. Please log in again."
                )
            
            # For other authentication errors
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    async def get_current_user(self, token_data: TokenData) -> User:
        """Get current authenticated user using decoupled database client"""
        if not self._initialized:
            await self.initialize()

        try:
            # Get user profile from database using decoupled client
            result = await self._db_service.read(
                "profiles", {"id": token_data.user_id}, 1
            )

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            profile = result[0]

            return User(
                id=profile["id"],
                email=profile["email"],
                australian_state=profile["australian_state"],
                user_type=profile["user_type"],
                subscription_status=profile.get("subscription_status", "free"),
                credits_remaining=profile.get("credits_remaining", 0),
                preferences=profile.get("preferences", {}),
            )

        except ClientError as e:
            logger.error(f"Database error getting user: {str(e)}")
            
            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                logger.info(f"JWT expiration detected for user {token_data.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired. Please log in again.",
                )
            
            # For other database errors, return 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve user data",
            )
        except HTTPException:
            # Re-raise HTTP exceptions as-is
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
