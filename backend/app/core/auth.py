"""
Authentication utilities for Real2.AI
"""

from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings
from app.core.database import get_database_client

logger = logging.getLogger(__name__)
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


def create_access_token(user_id: str, email: str) -> str:
    """Create JWT access token"""
    settings = get_settings()
    
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(
        payload, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return TokenData(
            user_id=user_id,
            email=email,
            exp=datetime.fromtimestamp(payload.get("exp", 0))
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    
    try:
        token_data = verify_token(credentials.credentials)
        
        # Get user profile from database
        db_client = get_database_client()
        result = await db_client.table("profiles").select("*").eq("id", token_data.user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = result.data[0]
        
        return User(
            id=profile["id"],
            email=profile["email"],
            australian_state=profile["australian_state"],
            user_type=profile["user_type"],
            subscription_status=profile.get("subscription_status", "free"),
            credits_remaining=profile.get("credits_remaining", 0),
            preferences=profile.get("preferences", {})
        )
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None