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


# OCR Models

class OCRCapabilitiesResponse(BaseModel):
    """OCR service capabilities response"""
    service_available: bool
    model_name: Optional[str] = None
    supported_formats: List[str] = []
    max_file_size_mb: float = 0.0
    features: List[str] = []
    reason: Optional[str] = None  # If service unavailable


class OCRProcessingRequest(BaseModel):
    """OCR processing request"""
    document_id: str
    force_reprocess: bool = False
    australian_context: Optional[Dict[str, Any]] = None


class OCRProcessingResponse(BaseModel):
    """OCR processing response"""
    message: str
    document_id: str
    estimated_completion_minutes: int
    processing_started: bool = True


class OCRExtractionResult(BaseModel):
    """OCR text extraction result"""
    extracted_text: str
    extraction_method: str
    extraction_confidence: float
    character_count: int
    word_count: int
    extraction_timestamp: datetime
    file_processed: str
    processing_details: Optional[Dict[str, Any]] = None
    enhancements_applied: List[str] = []
    contract_terms_found: int = 0


class DocumentProcessingStatus(BaseModel):
    """Enhanced document processing status with OCR details"""
    document_id: str
    status: str  # uploaded, processing, processed, reprocessing_ocr, ocr_failed, failed
    extraction_confidence: float
    extraction_method: str
    ocr_recommended: bool = False
    ocr_available: bool = False
    processing_results: Optional[OCRExtractionResult] = None
    created_at: datetime
    updated_at: datetime


# Enhanced OCR Models for Gemini 2.5 Pro Integration

class BatchOCRRequest(BaseModel):
    """Batch OCR processing request"""
    document_ids: List[str]
    contract_type: Optional[ContractType] = ContractType.PURCHASE_AGREEMENT
    processing_priority: str = "standard"  # standard, priority
    include_analysis: bool = True
    batch_options: Optional[Dict[str, Any]] = None
    
    @field_validator('document_ids')
    @classmethod
    def validate_document_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one document ID is required')
        if len(v) > 20:  # Limit batch size
            raise ValueError('Maximum 20 documents per batch')
        return v
    
    @field_validator('processing_priority')
    @classmethod
    def validate_priority(cls, v):
        if v not in ['standard', 'priority', 'express']:
            raise ValueError('Priority must be standard, priority, or express')
        return v


class BatchOCRResponse(BaseModel):
    """Batch OCR processing response"""
    message: str
    batch_id: str
    documents_queued: int
    estimated_completion_minutes: int
    processing_features: List[str]
    queue_position: Optional[int] = None


class OCRStatusResponse(BaseModel):
    """Detailed OCR processing status response"""
    document_id: str
    filename: str
    status: str  # queued_for_ocr, processing_ocr, processed, ocr_failed
    processing_metrics: Dict[str, Any]
    ocr_features_used: List[str]
    last_updated: Optional[datetime] = None
    supports_reprocessing: bool = True
    task_id: Optional[str] = None
    progress_percent: Optional[int] = None
    current_step: Optional[str] = None
    estimated_time_remaining: Optional[int] = None


class EnhancedOCRCapabilities(BaseModel):
    """Enhanced OCR capabilities with Gemini 2.5 Pro features"""
    service_available: bool
    model_name: str = "gemini-2.5-pro"
    supported_formats: List[str]
    max_file_size_mb: float
    features: List[str]
    gemini_features: Dict[str, bool]
    processing_tiers: Dict[str, Dict[str, Any]]
    api_health: Dict[str, Any]
    queue_status: Optional[Dict[str, Any]] = None


class GeminiOCRResult(BaseModel):
    """Enhanced OCR result from Gemini 2.5 Pro"""
    extracted_text: str
    extraction_method: str = "gemini_2.5_pro_ocr"
    extraction_confidence: float
    document_type: str = "unknown"
    key_sections: Dict[str, str]
    australian_state_indicators: List[str]
    extraction_quality: Dict[str, Any]
    warnings: List[str]
    character_count: int
    word_count: int
    pages_processed: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    contract_analysis: Optional[Dict[str, Any]] = None
    priority_analysis: Optional[Dict[str, Any]] = None


class OCRQueueStatus(BaseModel):
    """OCR processing queue status"""
    queue_position: int
    estimated_wait_time_minutes: int
    active_workers: int
    queue_length: int
    user_priority: str  # standard, priority, express
    processing_capacity: Dict[str, Any]
    current_load: float  # 0.0 - 1.0


class OCRProcessingOptions(BaseModel):
    """Advanced OCR processing options"""
    priority: bool = False
    enhanced_quality: bool = True
    detailed_analysis: bool = False
    contract_specific: bool = True
    include_contract_analysis: bool = True
    australian_context: Optional[Dict[str, Any]] = None
    quality_threshold: float = 0.7
    retry_on_low_confidence: bool = True


class OCRCostEstimate(BaseModel):
    """OCR processing cost estimate"""
    estimated_cost_usd: float
    estimated_time_seconds: int
    complexity_factor: float
    file_size_mb: float
    processing_tier: str
    features_included: List[str]


class ContractAnalysisFromOCR(BaseModel):
    """Contract analysis results from OCR extraction"""
    document_id: str
    ocr_confidence: float
    contract_elements: Dict[str, List[str]]
    australian_compliance_indicators: List[str]
    risk_indicators: List[str]
    completeness_score: float
    quality_metrics: Dict[str, Any]
    recommendations: List[str]
    requires_manual_review: bool


# WebSocket Models for OCR Progress

class OCRProgressUpdate(BaseModel):
    """OCR processing progress update via WebSocket"""
    document_id: str
    task_id: Optional[str] = None
    current_step: str
    progress_percent: int
    step_description: str
    estimated_completion: Optional[str] = None
    processing_features: List[str]


class BatchOCRProgressUpdate(BaseModel):
    """Batch OCR processing progress update"""
    batch_id: str
    completed: int
    total: int
    progress_percent: int
    current_document: Optional[str] = None
    failed_count: int = 0
    estimated_completion: Optional[str] = None


class OCRCompletionNotification(BaseModel):
    """OCR processing completion notification"""
    document_id: str
    task_id: Optional[str] = None
    extraction_confidence: float
    character_count: int
    word_count: int
    processing_method: str
    quality_score: str
    contract_elements_found: int


class OCRErrorNotification(BaseModel):
    """OCR processing error notification"""
    document_id: str
    task_id: Optional[str] = None
    error_message: str
    error_type: str
    retry_available: bool
    support_contact: Optional[str] = None