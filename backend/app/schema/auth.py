"""Authentication schemas."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

from app.schema.enums import AustralianState


class UserRegistrationRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    australian_state: AustralianState
    user_type: str = "buyer"  # buyer, investor, agent
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @field_validator('user_type')
    @classmethod
    def validate_user_type(cls, v):
        if v not in ['buyer', 'investor', 'agent']:
            raise ValueError('User type must be buyer, investor, or agent')
        return v


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User profile response"""
    id: str
    email: str
    australian_state: AustralianState
    user_type: str
    subscription_status: str = "free"
    credits_remaining: int = 0
    preferences: Dict[str, Any] = {}
    onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None
    onboarding_preferences: Dict[str, Any] = {}
    created_at: Optional[datetime] = None