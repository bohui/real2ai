"""
Authentication utilities for Real2.AI
"""

import logging
from datetime import datetime, UTC
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client
from app.core.config import get_settings
from app.core.database import get_database_client

logger = logging.getLogger(__name__)

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


def verify_token(token: str) -> TokenData:
    """Verify and decode Supabase JWT token"""
    settings = get_settings()

    try:
        logger.info("Starting token verification")

        if not token:
            logger.error("No token provided for verification")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided"
            )

        # Create direct Supabase client for token verification
        supabase_client = create_client(
            settings.supabase_url, settings.supabase_anon_key
        )

        logger.info("Supabase client created, attempting to verify token")

        # Verify the token using Supabase's built-in verification
        user = supabase_client.auth.get_user(token)

        if not user or not user.user:
            logger.error("Token verification failed - no user returned")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        # Extract user information from Supabase user object
        user_id = user.user.id
        email = user.user.email

        if not user_id or not email:
            logger.error("Token verification failed - missing user_id or email")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        logger.info(f"Token verified successfully for user: {email}")

        # Get expiration from the user session if available
        exp_timestamp = getattr(user.user, "exp", None)
        if exp_timestamp:
            exp = datetime.fromtimestamp(exp_timestamp)
        else:
            # Default to 1 hour from now if no expiration found
            exp = datetime.now(UTC)

        return TokenData(user_id=user_id, email=email, exp=exp)

    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user"""

    try:
        token_data = verify_token(credentials.credentials)

        # Get user profile from database
        db_client = get_database_client()

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        result = (
            db_client.table("profiles")
            .select("*")
            .eq("id", token_data.user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        profile = result.data[0]

        return User(
            id=profile["id"],
            email=profile["email"],
            australian_state=profile["australian_state"],
            user_type=profile["user_type"],
            subscription_status=profile.get("subscription_status", "free"),
            credits_remaining=profile.get("credits_remaining", 0),
            preferences=profile.get("preferences", {}),
        )

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


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


async def get_current_user_ws(token: str) -> Optional[User]:
    """Get current authenticated user for WebSocket connections with enhanced validation"""

    try:
        logger.info("Starting WebSocket authentication")

        if not token or token.strip() == "":
            logger.error(
                "No token or empty token provided for WebSocket authentication"
            )
            return None

        # Remove any URL encoding if present
        if token.startswith("Bearer%20"):
            token = token.replace("Bearer%20", "")
        elif token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        token_data = verify_token(token)
        logger.info(f"Token verified successfully for user: {token_data.user_id}")

        # Get user profile from database
        db_client = get_database_client()

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        result = (
            db_client.table("profiles")
            .select("*")
            .eq("id", token_data.user_id)
            .execute()
        )

        if not result.data:
            logger.error(f"User profile not found for ID: {token_data.user_id}")
            return None

        profile = result.data[0]
        logger.info(f"User profile retrieved successfully: {profile['email']}")

        user = User(
            id=profile["id"],
            email=profile["email"],
            australian_state=profile["australian_state"],
            user_type=profile["user_type"],
            subscription_status=profile.get("subscription_status", "free"),
            credits_remaining=profile.get("credits_remaining", 0),
            preferences=profile.get("preferences", {}),
        )

        logger.info(f"WebSocket authentication completed for user: {user.email}")
        return user

    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None
