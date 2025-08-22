"""
Supabase Database Models with Automatic Timestamps
Models that correspond to your existing Supabase migration schema
Automatic created_at/updated_at handled by database triggers
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


# Import enums from central location
from app.schema.enums import (
    AustralianState,
    UserType,
    SubscriptionStatus,
    ContractType,
    PurchaseMethod,
    UseCategory,
    DocumentStatus,
    PropertyType,
    ValuationSource,
    ValuationType,
    RiskLevel,
    MarketOutlook,
    InsightType,
    ViewSource,
    ContentType,
    DiagramType,
    EntityType,
)


# Base Model with Automatic Timestamps
class TimestampedBaseModel(BaseModel):
    """
    Base model with automatic timestamp fields

    Note: created_at and updated_at are managed by database triggers
    - created_at: Set automatically on INSERT with DEFAULT NOW()
    - updated_at: Set automatically on UPDATE by trigger function
    """

    created_at: Optional[datetime] = Field(
        None, description="Managed by database DEFAULT NOW()"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Managed by database trigger"
    )

    model_config = {
        # Allow population by field name (for database results)
        "populate_by_name": True,
        # Enable JSON serialization
        "json_encoders": {datetime: lambda v: v.isoformat() if v else None},
    }


# Core Models
class Profile(TimestampedBaseModel):
    """User profiles table (extends auth.users)"""

    id: UUID = Field(..., description="User ID from auth.users")
    email: str = Field(..., max_length=255)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    australian_state: AustralianState = AustralianState.NSW
    user_type: UserType = UserType.BUYER
    subscription_status: SubscriptionStatus = SubscriptionStatus.FREE
    credits_remaining: int = Field(default=1, ge=0)
    organization: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None
    onboarding_preferences: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}  # For SQLAlchemy compatibility


class Document(TimestampedBaseModel):
    """Documents table for file management"""

    id: UUID = Field(..., description="Document UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    content_hash: Optional[str] = Field(
        None, description="SHA-256 hash of document content for caching"
    )
    original_filename: str = Field(..., max_length=512)
    storage_path: str = Field(..., max_length=1024)
    file_type: str = Field(..., max_length=50)
    file_size: int = Field(..., gt=0)
    processing_status: str = DocumentStatus.UPLOADED.value
    upload_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_results: Dict[str, Any] = Field(default_factory=dict)

    # Processing timing
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None

    # Quality and extraction metrics
    overall_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    text_extraction_method: Optional[str] = Field(None, max_length=100)

    # Document content metrics
    total_pages: int = Field(default=0, ge=0)
    total_text_length: int = Field(default=0, ge=0)
    total_word_count: int = Field(default=0, ge=0)
    has_diagrams: bool = False
    diagram_count: int = Field(default=0, ge=0)

    # Classification
    document_type: Optional[str] = Field(None, max_length=100)
    australian_state: Optional[str] = Field(None, max_length=10)
    contract_type: Optional[str] = Field(None, max_length=100)

    # Processing metadata
    processing_errors: Optional[Dict[str, Any]] = None
    processing_notes: Optional[str] = None

    # Artifact reference (added via ALTER TABLE in migration)
    artifact_text_id: Optional[UUID] = Field(
        None, description="Reference to full text artifact"
    )


class Contract(TimestampedBaseModel):
    """Contracts table for contract metadata (shared resource using content_hash)"""

    id: UUID = Field(..., description="Contract UUID")
    content_hash: str = Field(
        ..., description="SHA-256 hash of document content for caching"
    )
    contract_type: ContractType = ContractType.UNKNOWN
    purchase_method: Optional[PurchaseMethod] = Field(
        None, description="OCR-inferred purchase method for purchase agreements"
    )
    use_category: Optional[UseCategory] = Field(
        None,
        description="OCR-inferred property use category for purchase and lease agreements",
    )
    ocr_confidence: Dict[str, float] = Field(
        default_factory=dict, description="Confidence scores for OCR-inferred fields"
    )
    state: AustralianState = AustralianState.NSW
    contract_terms: Dict[str, Any] = Field(default_factory=dict)
    extracted_entity: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete ContractEntityExtraction payload (for reference)",
    )
    raw_text: Optional[str] = None
    property_address: Optional[str] = None
    updated_by: Optional[str] = Field(
        None, description="Workflow node that made the last update"
    )


class Analysis(TimestampedBaseModel):
    """Analysis table for tracking analysis operations with flexible scoping"""

    id: UUID = Field(..., description="Analysis UUID")
    content_hash: str = Field(
        ..., description="SHA-256 hash of document content for caching"
    )
    agent_version: str = Field(default="1.0", max_length=50)
    status: str = Field(default="pending", max_length=20)
    result: Optional[Dict[str, Any]] = Field(
        None, description="Analysis result in JSON format"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Error details if analysis failed"
    )
    started_at: Optional[datetime] = Field(None, description="Analysis start time")
    completed_at: Optional[datetime] = Field(
        None, description="Analysis completion time"
    )
    user_id: Optional[UUID] = Field(
        None, description="User who initiated analysis, null for shared analyses"
    )


# Artifact Models (Content-Addressed Cache System)
class FullTextArtifact(BaseModel):
    """Full text artifacts for content-addressed caching"""

    id: UUID = Field(..., description="Artifact UUID")
    content_hmac: str = Field(
        ..., description="Content HMAC for content-addressed storage"
    )
    algorithm_version: int = Field(..., description="Algorithm version used")
    params_fingerprint: str = Field(..., description="Parameter fingerprint")
    full_text_uri: str = Field(..., description="URI to full text storage")
    full_text_sha256: str = Field(..., description="SHA256 hash of full text")
    total_pages: int = Field(..., description="Total number of pages")
    total_words: int = Field(..., description="Total word count")
    methods: Dict[str, Any] = Field(..., description="Extraction methods used")
    timings: Optional[Dict[str, Any]] = Field(
        None, description="Processing timing information"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class ArtifactPage(BaseModel):
    """Page-level artifacts for content-addressed caching"""

    id: UUID = Field(..., description="Page artifact UUID")
    content_hmac: str = Field(..., description="Content HMAC")
    algorithm_version: int = Field(..., description="Algorithm version")
    params_fingerprint: str = Field(..., description="Parameter fingerprint")
    page_number: int = Field(..., description="Page number")
    page_text_uri: str = Field(..., description="URI to page text storage")
    page_text_sha256: str = Field(..., description="SHA256 hash of page text")
    layout: Optional[Dict[str, Any]] = Field(
        None, description="Page layout information"
    )
    metrics: Optional[Dict[str, Any]] = Field(None, description="Page metrics")
    content_type: str = Field(
        default="text", description="Type of content (text, markdown, json_metadata)"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class ArtifactDiagram(BaseModel):
    """Diagram artifacts for content-addressed caching"""

    id: UUID = Field(..., description="Diagram artifact UUID")
    content_hmac: str = Field(..., description="Content HMAC")
    algorithm_version: int = Field(..., description="Algorithm version")
    params_fingerprint: str = Field(..., description="Parameter fingerprint")
    page_number: int = Field(..., description="Page number")
    diagram_key: str = Field(..., description="Diagram identifier key")
    diagram_meta: Dict[str, Any] = Field(..., description="Diagram metadata")
    artifact_type: str = Field(
        default="diagram",
        description="Type of artifact (diagram, image_jpg, image_png)",
    )
    image_uri: Optional[str] = Field(None, description="URI for image artifacts")
    image_sha256: Optional[str] = Field(
        None, description="SHA256 hash for image artifacts"
    )
    image_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadata for image artifacts"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


# User-Document Association Models
class UserDocumentPage(TimestampedBaseModel):
    """User-specific document page associations"""

    document_id: UUID = Field(..., description="Reference to documents.id")
    page_number: int = Field(..., description="Page number")
    artifact_page_id: UUID = Field(..., description="Reference to artifact_pages.id")
    annotations: Optional[Dict[str, Any]] = Field(None, description="User annotations")
    flags: Optional[Dict[str, Any]] = Field(None, description="User flags")


class UserDocumentDiagram(TimestampedBaseModel):
    """User-specific document diagram associations"""

    document_id: UUID = Field(..., description="Reference to documents.id")
    page_number: int = Field(..., description="Page number")
    diagram_key: str = Field(..., description="Diagram identifier")
    artifact_diagram_id: UUID = Field(
        ..., description="Reference to artifact_diagrams.id"
    )
    annotations: Optional[Dict[str, Any]] = Field(None, description="User annotations")


class UsageLog(TimestampedBaseModel):
    """Usage logs for tracking and billing"""

    id: UUID = Field(..., description="Usage log UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    action_type: str = Field(..., max_length=100)
    credits_used: int = Field(default=0, ge=0)
    credits_remaining: int = Field(default=0, ge=0)
    resource_used: Optional[str] = Field(None, max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None

    # Override field name for this model since it uses 'timestamp' instead of 'created_at'
    # Note: In Pydantic V2, field aliases are handled differently
    model_config = {"from_attributes": True}


# User Tracking Models
class UserContractView(TimestampedBaseModel):
    """User contract view tracking for RLS and access history"""

    id: UUID = Field(..., description="View record UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    content_hash: str = Field(..., description="Contract content hash")
    property_address: Optional[str] = Field(None, description="Property address")
    analysis_id: Optional[UUID] = Field(None, description="Analysis ID if applicable")
    viewed_at: datetime = Field(..., description="When user viewed this contract")
    source: ViewSource = Field(..., description="How user accessed this contract")


class UserPropertyView(TimestampedBaseModel):
    """User property view tracking for RLS and search history"""

    id: UUID = Field(..., description="View record UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    property_hash: str = Field(..., description="Property hash for identification")
    property_address: str = Field(..., description="Property address")
    source: ViewSource = Field(
        default=ViewSource.SEARCH, description="How user found this property"
    )
    viewed_at: datetime = Field(..., description="When user viewed this property")


class SubscriptionPlan(BaseModel):
    """Subscription plans table"""

    id: UUID = Field(..., description="Plan UUID")
    name: str = Field(..., max_length=100, unique=True)
    slug: str = Field(..., max_length=100, unique=True)
    description: Optional[str] = None
    price_monthly: float = Field(..., ge=0)
    price_annually: Optional[float] = Field(None, ge=0)
    credits_per_month: int = Field(..., ge=0)
    max_file_size_mb: int = Field(default=50, ge=1)
    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    sort_order: int = 0
    created_at: Optional[datetime] = None  # Only created_at for this table


class UserSubscription(TimestampedBaseModel):
    """User subscriptions table"""

    id: UUID = Field(..., description="Subscription UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    plan_id: UUID = Field(..., description="Reference to subscription_plans.id")
    stripe_subscription_id: Optional[str] = Field(None, max_length=100)
    stripe_customer_id: Optional[str] = Field(None, max_length=100)
    status: str = Field(
        ..., max_length=50
    )  # active, cancelled, past_due, unpaid, trialing
    trial_end: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    cancelled_at: Optional[datetime] = None


class AnalysisProgress(TimestampedBaseModel):
    """Analysis progress tracking for real-time updates"""

    id: UUID = Field(..., description="Progress UUID")
    content_hash: str = Field(..., description="Content hash identifying the contract")
    user_id: UUID = Field(..., description="Reference to profiles.id")

    # Progress tracking
    current_step: str = Field(..., max_length=100)
    progress_percent: int = Field(default=0, ge=0, le=100)
    step_description: Optional[str] = None
    estimated_completion_minutes: Optional[int] = Field(None, ge=0)

    # Timing information
    step_started_at: Optional[datetime] = None
    step_completed_at: Optional[datetime] = None
    total_elapsed_seconds: int = Field(default=0, ge=0)

    # Status and metadata
    status: str = Field(
        default="in_progress", max_length=50
    )  # in_progress, completed, failed, cancelled
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Property(TimestampedBaseModel):
    """Properties table for Australian property data"""

    id: UUID = Field(..., description="Property UUID")
    property_hash: Optional[str] = Field(
        None, description="Hash of normalized address for caching"
    )
    address_full: str = Field(..., max_length=500, description="Complete address")
    street_number: Optional[str] = Field(None, max_length=20)
    street_name: Optional[str] = Field(None, max_length=200)
    suburb: Optional[str] = Field(None, max_length=100)
    state: Optional[AustralianState] = None
    postcode: Optional[str] = Field(None, max_length=10)
    property_type: Optional[PropertyType] = None

    # Location data
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Property features
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    car_spaces: Optional[int] = Field(None, ge=0)
    land_size: Optional[float] = Field(None, ge=0, description="Land size in sqm")
    building_size: Optional[float] = Field(
        None, ge=0, description="Building size in sqm"
    )
    year_built: Optional[int] = Field(None, ge=1800, le=2030)

    # Property identifiers
    lot_number: Optional[str] = Field(None, max_length=20)
    plan_number: Optional[str] = Field(None, max_length=50)
    title_reference: Optional[str] = Field(None, max_length=100)
    council_property_id: Optional[str] = Field(None, max_length=100)

    # Data quality and verification
    address_verified: bool = False
    coordinates_verified: bool = False
    property_features_verified: bool = False
    data_source: Optional[str] = Field(None, max_length=100)
    last_updated_source: Optional[str] = Field(None, max_length=100)

    # Metadata
    property_metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyValuation(TimestampedBaseModel):
    """Property valuations from various sources"""

    id: UUID = Field(..., description="Valuation UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    valuation_source: ValuationSource
    valuation_type: ValuationType
    estimated_value: float = Field(..., ge=0)
    valuation_range_lower: Optional[float] = Field(None, ge=0)
    valuation_range_upper: Optional[float] = Field(None, ge=0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    methodology: Optional[str] = None
    valuation_date: datetime
    expires_at: Optional[datetime] = None
    api_response: Dict[str, Any] = Field(default_factory=dict)


class PropertyMarketData(TimestampedBaseModel):
    """Market data and analytics for properties"""

    id: UUID = Field(..., description="Market data UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    suburb: str = Field(..., max_length=100)
    state: AustralianState
    data_source: ValuationSource
    median_price: Optional[float] = Field(None, ge=0)
    price_growth_12_month: Optional[float] = Field(
        None, description="Percentage growth"
    )
    price_growth_3_year: Optional[float] = Field(None, description="Percentage growth")
    days_on_market: Optional[int] = Field(None, ge=0)
    sales_volume_12_month: Optional[int] = Field(None, ge=0)
    market_outlook: Optional[MarketOutlook] = None
    median_rent: Optional[float] = Field(None, ge=0, description="Weekly rent")
    rental_yield: Optional[float] = Field(None, ge=0, description="Percentage yield")
    vacancy_rate: Optional[float] = Field(None, ge=0, description="Percentage vacancy")
    data_date: datetime
    expires_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class PropertyRiskAssessment(TimestampedBaseModel):
    """Risk assessment data for properties"""

    id: UUID = Field(..., description="Risk assessment UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    overall_risk: RiskLevel
    liquidity_risk: RiskLevel
    market_risk: RiskLevel
    structural_risk: RiskLevel
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    assessment_date: datetime
    expires_at: Optional[datetime] = None
    assessment_methodology: Optional[str] = None
    mitigation_strategies: List[Dict[str, Any]] = Field(default_factory=list)


class ComparableSale(TimestampedBaseModel):
    """Comparable sales data for property analysis"""

    id: UUID = Field(..., description="Comparable sale UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    comparable_address: str = Field(..., max_length=500)
    sale_price: float = Field(..., ge=0)
    sale_date: datetime
    days_on_market: Optional[int] = Field(None, ge=0)

    # Property comparison features
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    car_spaces: Optional[int] = Field(None, ge=0)
    land_size: Optional[float] = Field(None, ge=0)
    building_size: Optional[float] = Field(None, ge=0)

    # Similarity metrics
    distance_km: Optional[float] = Field(None, ge=0)
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    price_per_sqm: Optional[float] = Field(None, ge=0)

    # Data source and verification
    data_source: ValuationSource
    verified: bool = False
    sale_metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertySalesHistory(TimestampedBaseModel):
    """Historical sales data for properties"""

    id: UUID = Field(..., description="Sales history UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    sale_price: float = Field(..., ge=0)
    sale_date: datetime
    sale_type: Optional[str] = Field(None, max_length=50)
    days_on_market: Optional[int] = Field(None, ge=0)

    # Market conditions at time of sale
    median_suburb_price: Optional[float] = Field(None, ge=0)
    price_vs_median: Optional[float] = Field(None, description="Percentage vs median")

    # Data source
    data_source: ValuationSource
    verified: bool = False
    sale_metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyRentalHistory(TimestampedBaseModel):
    """Rental history data for properties"""

    id: UUID = Field(..., description="Rental history UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    weekly_rent: float = Field(..., ge=0)
    lease_date: datetime
    lease_duration_months: Optional[int] = Field(None, ge=1)

    # Rental analysis
    rental_yield: Optional[float] = Field(None, ge=0)
    rent_vs_median: Optional[float] = Field(None, description="Percentage vs median")

    # Data source
    data_source: ValuationSource
    verified: bool = False
    rental_metadata: Dict[str, Any] = Field(default_factory=dict)


class UserSavedProperty(TimestampedBaseModel):
    """User saved properties"""

    id: UUID = Field(..., description="Saved property UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    property_id: UUID = Field(..., description="Reference to properties.id")
    is_favorite: bool = False
    notes: Optional[str] = None
    saved_at: datetime
    alert_enabled: bool = False
    alert_criteria: Dict[str, Any] = Field(default_factory=dict)


class PropertySearch(TimestampedBaseModel):
    """User property search history"""

    id: UUID = Field(..., description="Property search UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    search_criteria: Dict[str, Any] = Field(default_factory=dict)
    results_count: int = Field(default=0, ge=0)
    executed_at: datetime
    search_metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyReport(TimestampedBaseModel):
    """Generated property reports"""

    id: UUID = Field(..., description="Property report UUID")
    property_id: UUID = Field(..., description="Reference to properties.id")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    report_type: str = Field(..., max_length=100)
    report_data: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    expires_at: Optional[datetime] = None
    report_version: str = Field(default="1.0", max_length=50)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyAPIUsage(TimestampedBaseModel):
    """Track API usage for billing"""

    id: UUID = Field(..., description="API usage UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    api_provider: str = Field(..., max_length=100)
    endpoint: str = Field(..., max_length=200)
    request_type: str = Field(..., max_length=100)
    cost_aud: Optional[float] = Field(None, ge=0)
    response_time_ms: Optional[int] = Field(None, ge=0)
    request_successful: bool
    error_message: Optional[str] = None
    request_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    # Override field name for this model since it uses 'timestamp' instead of 'created_at'
    # Note: In Pydantic V2, field aliases are handled differently
    model_config = {"from_attributes": True}


class MarketInsight(TimestampedBaseModel):
    """Market insights and trends cache"""

    id: UUID = Field(..., description="Market insight UUID")
    suburb: str = Field(..., max_length=100)
    state: AustralianState
    property_type: Optional[PropertyType] = None
    insight_type: InsightType
    insight_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_sources: List[str] = Field(default_factory=list)
    valid_from: datetime
    valid_until: datetime


# View Models (Read-only database views)
class AnalysisProgressDetailed(BaseModel):
    """Detailed analysis progress view combining multiple tables"""

    analysis_id: UUID
    contract_id: UUID
    user_id: UUID
    current_step: str
    progress_percent: int
    step_description: Optional[str] = None
    step_started_at: Optional[datetime] = None
    step_completed_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None

    # From analyses
    analysis_status: str
    agent_version: str
    result: Optional[Dict[str, Any]] = None

    # From contracts
    contract_type: ContractType
    state: AustralianState

    # From documents
    original_filename: str
    file_type: str
    processing_status: str

    model_config = {"from_attributes": True}


# Import enums from central location
from app.schema.enums import TaskState, RecoveryMethod


class TaskRegistry(TimestampedBaseModel):
    id: UUID
    task_id: str
    task_name: str
    user_id: UUID
    task_args: Dict[str, Any] = Field(default_factory=dict)
    task_kwargs: Dict[str, Any] = Field(default_factory=dict)
    context_key: Optional[str] = None
    current_state: TaskState = TaskState.QUEUED
    previous_state: Optional[TaskState] = None
    state_history: List[Dict[str, Any]] = Field(default_factory=list)
    progress_percent: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = None
    checkpoint_data: Dict[str, Any] = Field(default_factory=dict)
    last_heartbeat: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    recovery_priority: int = 0
    auto_recovery_enabled: bool = True
    result_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None


class TaskCheckpoint(TimestampedBaseModel):
    id: UUID
    task_registry_id: UUID
    checkpoint_name: str
    progress_percent: int
    step_description: Optional[str] = None
    recoverable_data: Dict[str, Any] = Field(default_factory=dict)
    database_state: Dict[str, Any] = Field(default_factory=dict)
    file_state: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_hash: Optional[str] = None
    is_valid: bool = True


class RecoveryQueue(TimestampedBaseModel):
    id: UUID
    task_registry_id: UUID
    recovery_method: RecoveryMethod = RecoveryMethod.RESUME_CHECKPOINT
    recovery_priority: int = 0
    scheduled_for: Optional[datetime] = None
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = 3
    recovery_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class UserContractHistory(BaseModel):
    """User contract history view combining views with analysis data"""

    # From user_contract_views
    id: UUID
    user_id: UUID
    content_hash: str
    property_address: Optional[str] = None
    analysis_id: Optional[UUID] = None
    viewed_at: datetime
    source: ViewSource
    created_at: Optional[datetime] = None

    # From analyses
    result: Optional[Dict[str, Any]] = None
    analysis_status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # From documents
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = {"from_attributes": True}


class UserPropertyHistory(BaseModel):
    """User property search history view"""

    # From user_property_views
    id: UUID
    user_id: UUID
    property_hash: str
    property_address: str
    viewed_at: datetime
    source: ViewSource
    created_at: Optional[datetime] = None

    # From property_data table
    analysis_result: Optional[Dict[str, Any]] = None
    access_count: Optional[int] = None

    model_config = {"from_attributes": True}


# Helper functions for model operations
def create_model_with_timestamps(model_class, **kwargs) -> dict:
    """
    Create model data dict, excluding timestamp fields that are managed by database

    Args:
        model_class: The Pydantic model class
        **kwargs: Model field values

    Returns:
        Dictionary with model data, excluding managed timestamp fields
    """
    model = model_class(**kwargs)
    data = model.model_dump(exclude_unset=True)

    # Remove timestamp fields that are managed by database
    data.pop("created_at", None)
    data.pop("updated_at", None)

    return data


def update_model_with_timestamps(model_class, **kwargs) -> dict:
    """
    Create update data dict, excluding created_at and updated_at

    Args:
        model_class: The Pydantic model class
        **kwargs: Model field values to update

    Returns:
        Dictionary with update data, excluding timestamp fields
    """
    model = model_class(**kwargs)
    data = model.model_dump(exclude_unset=True)

    # Remove timestamp fields that are managed by database
    data.pop("created_at", None)
    data.pop("updated_at", None)

    return data


# Database connection helper (for direct Supabase operations)
class SupabaseModelManager:
    """
    Helper class for Supabase model operations with automatic timestamp handling
    """

    def __init__(self, supabase_client):
        self.client = supabase_client

    async def create_record(self, table_name: str, model_class, **data) -> dict:
        """
        Create a new record with automatic timestamp handling

        Args:
            table_name: Database table name
            model_class: Pydantic model class
            **data: Record data

        Returns:
            Created record from database (includes auto-generated timestamps)
        """
        # Remove timestamp fields - they're handled by database
        clean_data = create_model_with_timestamps(model_class, **data)

        result = self.client.table(table_name).insert(clean_data).execute()
        return result.data[0] if result.data else None

    async def update_record(
        self, table_name: str, record_id: str, model_class, **data
    ) -> dict:
        """
        Update a record with automatic timestamp handling

        Args:
            table_name: Database table name
            record_id: ID of record to update
            model_class: Pydantic model class
            **data: Update data

        Returns:
            Updated record from database (includes auto-updated timestamps)
        """
        # Remove timestamp fields - updated_at is handled by trigger
        clean_data = update_model_with_timestamps(model_class, **data)

        result = (
            self.client.table(table_name)
            .update(clean_data)
            .eq("id", record_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_record(self, table_name: str, record_id: str) -> dict:
        """Get a record by ID"""
        result = self.client.table(table_name).select("*").eq("id", record_id).execute()
        return result.data[0] if result.data else None

    async def list_records(self, table_name: str, **filters) -> List[dict]:
        """List records with optional filters"""
        query = self.client.table(table_name).select("*")

        for field, value in filters.items():
            query = query.eq(field, value)

        result = query.execute()
        return result.data or []
