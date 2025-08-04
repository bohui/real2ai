"""
API request/response models for Real2.AI
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timezone

from app.models.contract_state import AustralianState, ContractType, RiskLevel


# Authentication Models

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


# Document Models

class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    document_id: str
    filename: str
    file_size: int
    upload_status: str = "uploaded"
    processing_time: float = 0.0


class DocumentDetails(BaseModel):
    """Document details response"""
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    status: str  # uploaded, processing, processed, failed
    storage_path: str
    upload_timestamp: datetime
    processing_results: Optional[Dict[str, Any]] = None


# Contract Analysis Models

class AnalysisOptions(BaseModel):
    """Contract analysis options"""
    include_financial_analysis: bool = True
    include_risk_assessment: bool = True
    include_compliance_check: bool = True
    include_recommendations: bool = True
    priority_analysis: Optional[str] = None  # speed, accuracy, comprehensive


class ContractAnalysisRequest(BaseModel):
    """Contract analysis request"""
    document_id: str
    analysis_options: AnalysisOptions = AnalysisOptions()
    user_notes: Optional[str] = None


class ContractAnalysisResponse(BaseModel):
    """Contract analysis response"""
    contract_id: str
    analysis_id: str
    status: str = "pending"
    estimated_completion_minutes: int = 2


class RiskFactorResponse(BaseModel):
    """Risk factor in analysis response"""
    factor: str
    severity: RiskLevel
    description: str
    impact: str
    mitigation: str
    australian_specific: bool
    confidence: float


class RecommendationResponse(BaseModel):
    """Recommendation in analysis response"""
    priority: RiskLevel
    category: str  # legal, financial, practical
    recommendation: str
    action_required: bool
    australian_context: str
    estimated_cost: Optional[float] = None
    confidence: float


class StampDutyResponse(BaseModel):
    """Stamp duty calculation response"""
    state: AustralianState
    purchase_price: float
    base_duty: float
    exemptions: float
    surcharges: float
    total_duty: float
    is_first_home_buyer: bool
    is_foreign_buyer: bool
    breakdown: Dict[str, float]


class ComplianceCheckResponse(BaseModel):
    """Compliance check response"""
    state_compliance: bool
    compliance_issues: List[str]
    cooling_off_compliance: bool
    cooling_off_details: Dict[str, Any]
    stamp_duty_calculation: Optional[StampDutyResponse] = None
    mandatory_disclosures: List[str]
    warnings: List[str]
    legal_references: List[str]


class ContractAnalysisResult(BaseModel):
    """Complete contract analysis result"""
    contract_id: str
    analysis_id: str
    analysis_timestamp: datetime
    user_id: str
    australian_state: AustralianState
    
    # Analysis Results
    contract_terms: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    compliance_check: ComplianceCheckResponse
    recommendations: List[RecommendationResponse]
    
    # Analysis Metadata
    confidence_scores: Dict[str, float]
    overall_confidence: float
    processing_time: float
    analysis_version: str
    
    # Summary
    executive_summary: Dict[str, Any]


# Financial Models

class StampDutyCalculationRequest(BaseModel):
    """Stamp duty calculation request"""
    purchase_price: float
    state: AustralianState
    is_first_home_buyer: bool = False
    is_foreign_buyer: bool = False
    is_investment_property: bool = False


class PropertyFinancialSummary(BaseModel):
    """Property financial summary"""
    purchase_price: float
    stamp_duty: StampDutyResponse
    legal_costs: Optional[float] = None
    inspection_costs: Optional[float] = None
    total_upfront_costs: float
    ongoing_costs: Optional[Dict[str, float]] = None


# Usage and Statistics Models

class UsageStatsResponse(BaseModel):
    """User usage statistics response"""
    credits_remaining: int
    subscription_status: str
    total_contracts_analyzed: int
    current_month_usage: int
    recent_analyses: List[Dict[str, Any]]
    usage_trend: Optional[Dict[str, Any]] = None


class SystemStatsResponse(BaseModel):
    """System statistics response"""
    total_documents_processed: int
    total_analyses_completed: int
    average_processing_time: float
    success_rate: float
    active_users: int


# Error Models

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now(timezone.utc)


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    invalid_value: Any


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "Validation Error"
    detail: str
    validation_errors: List[ValidationError]
    timestamp: datetime = datetime.now(timezone.utc)


# WebSocket Models

class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]


class WebSocketProgressUpdate(BaseModel):
    """WebSocket progress update"""
    contract_id: str
    current_step: str
    progress_percent: int
    step_description: Optional[str] = None
    estimated_time_remaining: Optional[int] = None


# Onboarding Models

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


# Health Check Models

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = datetime.now(timezone.utc)
    version: str = "1.0.0"
    environment: str
    services: Dict[str, str] = {}


# Report Models

class ReportGenerationRequest(BaseModel):
    """Report generation request"""
    contract_id: str
    format: str = "pdf"  # pdf, html, json
    include_sections: List[str] = [
        "executive_summary", 
        "risk_assessment", 
        "compliance_check", 
        "recommendations"
    ]
    custom_branding: bool = False


class ReportResponse(BaseModel):
    """Report response"""
    report_id: str
    download_url: str
    format: str
    file_size: int
    expires_at: datetime