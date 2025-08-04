"""
Migrated Authentication utilities using decoupled client architecture
This replaces direct Supabase client instantiation with the new client factory system
"""

import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.clients.factory import get_supabase_client
from app.clients.base.interfaces import AuthOperations, DatabaseOperations
from app.clients.base.exceptions import ClientError
from app.core.database_v2 import get_database_service

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


class AuthService:
    """Authentication service using decoupled client architecture"""
    
    def __init__(self, auth_client: AuthOperations = None, db_service = None):
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
                self._db_service = get_database_service()
                if not self._db_service.is_initialized:
                    await self._db_service.initialize()
            
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
            
            if not user_data or 'id' not in user_data or 'email' not in user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Extract user information
            user_id = user_data['id']
            email = user_data['email']
            
            # Get expiration from token data if available
            exp_timestamp = user_data.get('exp')
            if exp_timestamp:
                if isinstance(exp_timestamp, (int, float)):
                    exp = datetime.fromtimestamp(exp_timestamp)
                else:
                    exp = datetime.utcnow()
            else:
                # Default to current time if no expiration found
                exp = datetime.utcnow()
            
            return TokenData(
                user_id=user_id,
                email=email,
                exp=exp
            )
            
        except ClientError as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def get_current_user(self, token_data: TokenData) -> User:
        """Get current authenticated user using decoupled database client"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get user profile from database using decoupled client
            result = await self._db_service.read_records(
                "profiles", 
                {"id": token_data.user_id},
                1
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            profile = result[0]
            
            return User(
                id=profile["id"],
                email=profile["email"],
                australian_state=profile["australian_state"],
                user_type=profile["user_type"],
                subscription_status=profile.get("subscription_status", "free"),
                credits_remaining=profile.get("credits_remaining", 0),
                preferences=profile.get("preferences", {})
            )
            
        except ClientError as e:
            logger.error(f"Database error getting user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve user data"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    async def health_check(self) -> dict:
        """Perform health check on authentication service"""
        try:
            if not self._initialized:
                return {
                    "status": "unhealthy",
                    "error": "Service not initialized"
                }
            
            return {
                "status": "healthy",
                "service": "auth_service_v2", 
                "client_architecture": "decoupled",
                "features": [
                    "dependency_injection",
                    "error_handling",
                    "automatic_retries", 
                    "circuit_breakers"
                ]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


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
    credentials: HTTPAuthorizationCredentials = Depends(security)
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


# Backward compatibility functions
def verify_token(token: str) -> TokenData:
    """Backward compatibility: Synchronous token verification"""
    import asyncio
    auth_service = get_auth_service()
    return asyncio.run(auth_service.verify_token(token))