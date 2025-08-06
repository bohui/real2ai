"""
Supabase Database Models with Automatic Timestamps
Models that correspond to your existing Supabase migration schema
Automatic created_at/updated_at handled by database triggers
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


# Enum definitions matching your database schema
class AustralianState(str, Enum):
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    NT = "NT"
    ACT = "ACT"


class UserType(str, Enum):
    BUYER = "buyer"
    INVESTOR = "investor"
    AGENT = "agent"


class SubscriptionStatus(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ContractType(str, Enum):
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    OFF_PLAN = "off_plan"
    AUCTION = "auction"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    BASIC_COMPLETE = "basic_complete"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYSIS_COMPLETE = "analysis_complete"
    FAILED = "failed"


class ContentType(str, Enum):
    TEXT = "text"
    DIAGRAM = "diagram"
    TABLE = "table"
    SIGNATURE = "signature"
    MIXED = "mixed"
    EMPTY = "empty"


class DiagramType(str, Enum):
    SITE_PLAN = "site_plan"
    SEWER_DIAGRAM = "sewer_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    TITLE_PLAN = "title_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    ADDRESS = "address"
    PROPERTY_REFERENCE = "property_reference"
    DATE = "date"
    FINANCIAL_AMOUNT = "financial_amount"
    PARTY_NAME = "party_name"
    LEGAL_REFERENCE = "legal_reference"
    CONTACT_INFO = "contact_info"
    PROPERTY_DETAILS = "property_details"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Base Model with Automatic Timestamps
class TimestampedBaseModel(BaseModel):
    """
    Base model with automatic timestamp fields
    
    Note: created_at and updated_at are managed by database triggers
    - created_at: Set automatically on INSERT with DEFAULT NOW()
    - updated_at: Set automatically on UPDATE by trigger function
    """
    created_at: Optional[datetime] = Field(None, description="Managed by database DEFAULT NOW()")
    updated_at: Optional[datetime] = Field(None, description="Managed by database trigger")

    class Config:
        # Allow population by field name (for database results)
        populate_by_name = True
        # Enable JSON serialization
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
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

    class Config:
        from_attributes = True  # For SQLAlchemy compatibility


class Document(TimestampedBaseModel):
    """Documents table for file management"""
    
    id: UUID = Field(..., description="Document UUID")
    user_id: UUID = Field(..., description="Reference to profiles.id")
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


class Contract(TimestampedBaseModel):
    """Contracts table for contract metadata"""
    
    id: UUID = Field(..., description="Contract UUID")
    document_id: UUID = Field(..., description="Reference to documents.id")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    contract_type: ContractType = ContractType.PURCHASE_AGREEMENT
    australian_state: AustralianState = AustralianState.NSW
    contract_terms: Dict[str, Any] = Field(default_factory=dict)
    raw_text: Optional[str] = None


class ContractAnalysis(TimestampedBaseModel):
    """Contract analyses table for AI analysis results"""
    
    id: UUID = Field(..., description="Analysis UUID")
    contract_id: UUID = Field(..., description="Reference to contracts.id")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    agent_version: str = "1.0"
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    # Analysis results structure
    analysis_result: Dict[str, Any] = Field(default_factory=dict)
    executive_summary: Dict[str, Any] = Field(default_factory=dict)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    compliance_check: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metrics
    risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    overall_risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_level: float = Field(default=0.0, ge=0.0, le=1.0)
    processing_time: float = Field(default=0.0, ge=0.0)
    processing_time_seconds: float = Field(default=0.0, ge=0.0)
    
    # Metadata
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)
    error_details: Dict[str, Any] = Field(default_factory=dict)
    analysis_timestamp: Optional[datetime] = None


class DocumentPage(TimestampedBaseModel):
    """Document pages table for page-level analysis"""
    
    id: UUID = Field(..., description="Page UUID")
    document_id: UUID = Field(..., description="Reference to documents.id")
    page_number: int = Field(..., ge=1)
    
    # Content analysis
    content_summary: Optional[str] = None
    text_content: Optional[str] = None
    text_length: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    
    # Content classification
    content_types: List[str] = Field(default_factory=list)
    primary_content_type: ContentType = ContentType.EMPTY
    
    # Quality metrics
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    content_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Layout analysis
    has_header: bool = False
    has_footer: bool = False
    has_signatures: bool = False
    has_handwriting: bool = False
    has_diagrams: bool = False
    has_tables: bool = False
    
    # Processing metadata
    processed_at: Optional[datetime] = None
    processing_method: Optional[str] = Field(None, max_length=100)


class DocumentEntity(TimestampedBaseModel):
    """Document entities table for extracted entities"""
    
    id: UUID = Field(..., description="Entity UUID")
    document_id: UUID = Field(..., description="Reference to documents.id")
    page_id: Optional[UUID] = Field(None, description="Reference to document_pages.id")
    page_number: int = Field(..., ge=1)
    
    # Entity data
    entity_type: EntityType
    entity_value: str
    normalized_value: Optional[str] = None
    
    # Context and quality
    context: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: Optional[str] = Field(None, max_length=100)
    
    # Location metadata
    position_data: Optional[Dict[str, Any]] = None
    
    # Processing metadata
    extracted_at: Optional[datetime] = None


class DocumentDiagram(TimestampedBaseModel):
    """Document diagrams table for diagram analysis"""
    
    id: UUID = Field(..., description="Diagram UUID")
    document_id: UUID = Field(..., description="Reference to documents.id")
    page_id: Optional[UUID] = Field(None, description="Reference to document_pages.id")
    page_number: int = Field(..., ge=1)
    
    # Classification
    diagram_type: DiagramType = DiagramType.UNKNOWN
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Storage and processing
    extracted_image_path: Optional[str] = Field(None, max_length=1024)
    basic_analysis_completed: bool = False
    detailed_analysis_completed: bool = False
    
    # Analysis results
    basic_analysis: Optional[Dict[str, Any]] = None
    
    # Quality metrics
    image_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    clarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Metadata
    detected_at: Optional[datetime] = None
    basic_analysis_at: Optional[datetime] = None


class DocumentAnalysis(TimestampedBaseModel):
    """Document analyses table for comprehensive document analysis"""
    
    id: UUID = Field(..., description="Analysis UUID")
    document_id: UUID = Field(..., description="Reference to documents.id")
    
    # Analysis metadata
    analysis_type: str = Field(default="contract_analysis", max_length=100)
    analysis_version: str = Field(default="v1.0", max_length=50)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Analysis status
    status: str = Field(default="pending", max_length=50)
    progress_percentage: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = Field(None, max_length=100)
    
    # Results
    detailed_entities: Optional[Dict[str, Any]] = None
    diagram_analyses: Optional[Dict[str, Any]] = None
    compliance_results: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    
    # Quality and confidence
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Processing metadata
    processing_time_seconds: float = Field(default=0.0, ge=0.0)
    langgraph_workflow_id: Optional[str] = Field(None, max_length=255)
    
    # Errors and issues
    analysis_errors: Optional[Dict[str, Any]] = None
    analysis_warnings: Optional[Dict[str, Any]] = None


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
    class Config:
        fields = {"created_at": "timestamp"}


class PropertyData(TimestampedBaseModel):
    """Property data table for enhanced property analysis"""
    
    id: UUID = Field(..., description="Property data UUID")
    contract_id: Optional[UUID] = Field(None, description="Reference to contracts.id")
    user_id: UUID = Field(..., description="Reference to profiles.id")
    
    # Property details
    address: str = Field(..., max_length=255)
    suburb: Optional[str] = Field(None, max_length=100)
    state: Optional[AustralianState] = None
    postcode: Optional[str] = Field(None, max_length=10)
    property_type: Optional[str] = Field(None, max_length=50)
    
    # Property features
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    car_spaces: Optional[int] = Field(None, ge=0)
    land_size: Optional[float] = Field(None, ge=0)
    building_size: Optional[float] = Field(None, ge=0)
    
    # Financial data
    purchase_price: Optional[float] = Field(None, ge=0)
    market_value: Optional[float] = Field(None, ge=0)
    
    # Analysis data
    market_analysis: Dict[str, Any] = Field(default_factory=dict)
    property_insights: Dict[str, Any] = Field(default_factory=dict)


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
    status: str = Field(..., max_length=50)  # active, cancelled, past_due, unpaid, trialing
    trial_end: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    cancelled_at: Optional[datetime] = None


class AnalysisProgress(TimestampedBaseModel):
    """Analysis progress tracking for real-time updates"""
    
    id: UUID = Field(..., description="Progress UUID")
    contract_id: UUID = Field(..., description="Reference to contracts.id")
    analysis_id: UUID = Field(..., description="Reference to contract_analyses.id")
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
    status: str = Field(default="in_progress", max_length=50)  # in_progress, completed, failed, cancelled
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    data.pop('created_at', None)
    data.pop('updated_at', None)
    
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
    data.pop('created_at', None)
    data.pop('updated_at', None)
    
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
    
    async def update_record(self, table_name: str, record_id: str, model_class, **data) -> dict:
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
        
        result = (self.client.table(table_name)
                 .update(clean_data)
                 .eq('id', record_id)
                 .execute())
        return result.data[0] if result.data else None
    
    async def get_record(self, table_name: str, record_id: str) -> dict:
        """Get a record by ID"""
        result = (self.client.table(table_name)
                 .select("*")
                 .eq('id', record_id)
                 .execute())
        return result.data[0] if result.data else None
    
    async def list_records(self, table_name: str, **filters) -> List[dict]:
        """List records with optional filters"""
        query = self.client.table(table_name).select("*")
        
        for field, value in filters.items():
            query = query.eq(field, value)
            
        result = query.execute()
        return result.data or []