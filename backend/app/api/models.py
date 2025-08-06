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

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v):
        if v not in ["buyer", "investor", "agent"]:
            raise ValueError("User type must be buyer, investor, or agent")
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

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v):
        if v and v not in ["nsw", "vic", "qld", "wa", "sa", "tas", "act", "nt"]:
            raise ValueError("Invalid jurisdiction")
        return v

    @field_validator("practice_area")
    @classmethod
    def validate_practice_area(cls, v):
        valid_areas = [
            "property",
            "commercial",
            "employment",
            "corporate",
            "litigation",
            "family",
            "other",
        ]
        if v and v not in valid_areas:
            raise ValueError("Invalid practice area")
        return v

    @field_validator("firm_size")
    @classmethod
    def validate_firm_size(cls, v):
        valid_sizes = ["solo", "small", "medium", "large", "inhouse"]
        if v and v not in valid_sizes:
            raise ValueError("Invalid firm size")
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
        "recommendations",
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

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one document ID is required")
        if len(v) > 20:  # Limit batch size
            raise ValueError("Maximum 20 documents per batch")
        return v

    @field_validator("processing_priority")
    @classmethod
    def validate_priority(cls, v):
        if v not in ["standard", "priority", "express"]:
            raise ValueError("Priority must be standard, priority, or express")
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
    model_name: str = "gemini-2.5-flash"
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


# Property Profile Models - Domain API & CoreLogic Integration


class PropertyAddress(BaseModel):
    """Australian property address"""

    unit_number: Optional[str] = None
    street_number: str
    street_name: str
    street_type: str
    suburb: str
    state: AustralianState
    postcode: str
    full_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_certainty: Optional[int] = None

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Postcode must be 4 digits")
        return v


class PropertyDetails(BaseModel):
    """Property physical details"""

    property_type: str  # House, Unit, Townhouse, Villa, Land
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    carspaces: Optional[int] = None
    land_area: Optional[float] = None
    building_area: Optional[float] = None
    year_built: Optional[int] = None
    features: List[str] = []

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        valid_types = ["House", "Unit", "Townhouse", "Villa", "Land", "Apartment"]
        if v not in valid_types:
            raise ValueError(f"Property type must be one of: {', '.join(valid_types)}")
        return v


class PropertyValuation(BaseModel):
    """Property valuation data"""

    estimated_value: float
    valuation_range_lower: float
    valuation_range_upper: float
    confidence: float
    valuation_date: datetime
    valuation_source: str  # domain, corelogic, combined
    methodology: str
    currency: str = "AUD"


class PropertyMarketData(BaseModel):
    """Property market analytics"""

    median_price: float
    price_growth_12_month: float
    price_growth_3_year: float
    days_on_market: int
    sales_volume_12_month: int
    market_outlook: str
    median_rent: Optional[float] = None
    rental_yield: Optional[float] = None
    vacancy_rate: Optional[float] = None


class PropertyRiskAssessment(BaseModel):
    """Property investment risk assessment"""

    overall_risk: RiskLevel
    liquidity_risk: RiskLevel
    market_risk: RiskLevel
    structural_risk: RiskLevel
    risk_factors: List[str]
    confidence: float
    risk_score: Optional[float] = None  # 0-100 scale


class ComparableSale(BaseModel):
    """Comparable property sale"""

    address: str
    sale_date: datetime
    sale_price: float
    property_details: PropertyDetails
    similarity_score: float
    adjusted_price: Optional[float] = None
    adjustments: Optional[Dict[str, float]] = None


class PropertySalesHistory(BaseModel):
    """Property sales history record"""

    date: datetime
    price: float
    sale_type: str  # Sold, Auction, Private Sale, etc.
    days_on_market: Optional[int] = None


class PropertyRentalHistory(BaseModel):
    """Property rental history record"""

    date: datetime
    weekly_rent: float
    lease_type: str  # Leased, Relisted, etc.
    lease_duration: Optional[str] = None


class PropertyProfile(BaseModel):
    """Comprehensive property profile"""

    address: PropertyAddress
    property_details: PropertyDetails
    valuation: PropertyValuation
    market_data: PropertyMarketData
    risk_assessment: PropertyRiskAssessment
    comparable_sales: List[ComparableSale]
    sales_history: List[PropertySalesHistory]
    rental_history: List[PropertyRentalHistory]
    data_sources: List[str]
    profile_created_at: datetime
    profile_confidence: float
    cache_expires_at: Optional[datetime] = None


class PropertySearchRequest(BaseModel):
    """Property search request"""

    address: Optional[str] = None
    property_details: Optional[PropertyDetails] = None
    include_valuation: bool = True
    include_market_data: bool = True
    include_risk_assessment: bool = True
    include_comparables: bool = True
    include_sales_history: bool = True
    include_rental_history: bool = False
    force_refresh: bool = False
    max_comparables: int = 10

    @field_validator("max_comparables")
    @classmethod
    def validate_max_comparables(cls, v):
        if v < 1 or v > 20:
            raise ValueError("max_comparables must be between 1 and 20")
        return v


class PropertyProfileResponse(BaseModel):
    """Property profile API response"""

    property_profile: PropertyProfile
    processing_time: float
    data_freshness: Dict[str, datetime]
    api_usage: Dict[str, int]
    cached_data: bool = False
    warnings: List[str] = []


class PropertyValuationRequest(BaseModel):
    """Property valuation request"""

    address: str
    property_details: Optional[PropertyDetails] = None
    valuation_source: str = "both"  # domain, corelogic, both

    @field_validator("valuation_source")
    @classmethod
    def validate_valuation_source(cls, v):
        if v not in ["domain", "corelogic", "both"]:
            raise ValueError(
                "valuation_source must be 'domain', 'corelogic', or 'both'"
            )
        return v


class PropertyValuationResponse(BaseModel):
    """Property valuation response"""

    address: str
    valuations: Dict[str, PropertyValuation]  # keyed by source
    processing_time: float
    data_sources_used: List[str]
    confidence_score: float
    warnings: List[str] = []


class PropertySearchFilter(BaseModel):
    """Property search filters for listings"""

    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    max_bathrooms: Optional[int] = None
    property_types: List[str] = []
    suburbs: List[str] = []
    states: List[AustralianState] = []
    listing_type: str = "Sale"  # Sale, Rent, Sold

    @field_validator("listing_type")
    @classmethod
    def validate_listing_type(cls, v):
        if v not in ["Sale", "Rent", "Sold"]:
            raise ValueError("listing_type must be 'Sale', 'Rent', or 'Sold'")
        return v


class PropertyListing(BaseModel):
    """Property listing information"""

    listing_id: int
    address: PropertyAddress
    property_details: PropertyDetails
    price_details: Dict[str, Any]
    listing_date: datetime
    agent_info: Optional[Dict[str, Any]] = None
    media_urls: List[str] = []
    description: Optional[str] = None
    auction_date: Optional[datetime] = None


class PropertySearchResponse(BaseModel):
    """Property search response"""

    total_results: int
    results_returned: int
    listings: List[PropertyListing]
    search_filters: PropertySearchFilter
    processing_time: float
    page_number: int = 1
    page_size: int = 20


class PropertyAPIHealthStatus(BaseModel):
    """Property API health status"""

    domain_api: Dict[str, Any]
    corelogic_api: Dict[str, Any]
    overall_status: str
    last_checked: datetime
    rate_limits: Dict[str, Dict[str, Any]]


class PropertyDataValidationResult(BaseModel):
    """Property data validation result"""

    is_valid: bool
    validation_score: float
    issues: List[Dict[str, Any]]
    data_sources_compared: List[str]
    cross_validation_passed: bool
