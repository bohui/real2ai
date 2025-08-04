"""Onboarding schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response"""
    onboarding_completed: bool
    onboarding_completed_at: Optional[datetime] = None
    onboarding_preferences: Dict[str, Any] = {}


class OnboardingPreferencesRequest(BaseModel):
    """Onboarding preferences update request"""
    practice_area: Optional[str] = None
    jurisdiction: Optional[str] = None
    firm_size: Optional[str] = None
    primary_contract_types: List[str] = []
    
    @field_validator('jurisdiction')
    @classmethod
    def validate_jurisdiction(cls, v):
        if v and v not in ['nsw', 'vic', 'qld', 'wa', 'sa', 'tas', 'act', 'nt']:
            raise ValueError('Invalid jurisdiction')
        return v
    
    @field_validator('practice_area')
    @classmethod
    def validate_practice_area(cls, v):
        valid_areas = ['property', 'commercial', 'employment', 'corporate', 'litigation', 'family', 'other']
        if v and v not in valid_areas:
            raise ValueError('Invalid practice area')
        return v
    
    @field_validator('firm_size')
    @classmethod
    def validate_firm_size(cls, v):
        valid_sizes = ['solo', 'small', 'medium', 'large', 'inhouse']
        if v and v not in valid_sizes:
            raise ValueError('Invalid firm size')
        return v


class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding request"""
    onboarding_preferences: OnboardingPreferencesRequest