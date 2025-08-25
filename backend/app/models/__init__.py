"""
Data models and schemas for Real2.AI

This module provides database models with automatic timestamp management.
All models use Supabase with automatic created_at/updated_at handling.
"""

# Import all models from supabase_models for easy access
from .supabase_models import (
    # Core Models
    Profile,
    Document,
    Contract,
    Analysis,
    # Artifact Models
    FullTextArtifact,
    ArtifactPage,
    ArtifactDiagram,
    # User Document Models
    UserDocumentPage,
    UserDocumentDiagram,
    # User Tracking Models
    UserContractView,
    UserPropertyView,
    # Property Models
    Property,
    PropertyValuation,
    PropertyMarketData,
    PropertyRiskAssessment,
    ComparableSale,
    PropertySalesHistory,
    PropertyRentalHistory,
    UserSavedProperty,
    PropertySearch,
    PropertyReport,
    PropertyAPIUsage,
    MarketInsight,
    # Supporting Models
    SubscriptionPlan,
    UserSubscription,
    UsageLog,
    AnalysisProgress,
    AnalysisProgressDetailed,
    # Task Management Models
    TaskRegistry,
    TaskCheckpoint,
    RecoveryQueue,
    # History Models
    UserContractHistory,
    UserPropertyHistory,
    # Base Classes and Helpers
    TimestampedBaseModel,
    SupabaseModelManager,
    create_model_with_timestamps,
    update_model_with_timestamps,
)

# Import enums from central enums package (source of truth)
from app.schema.enums import (
    AustralianState,
    UserType,
    SubscriptionStatus,
    ContractType,
    DocumentStatus,
    ContentType,
    DiagramType,
    EntityType,
)

# Legacy aliases for backward compatibility
ProcessingStatus = DocumentStatus  # For existing code using ProcessingStatus

__all__ = [
    # Core Models
    "Profile",
    "Document",
    "Contract",
    "Analysis",
    # Artifact Models
    "FullTextArtifact",
    "ArtifactPage",
    "ArtifactDiagram",
    # User Document Models
    "UserDocumentPage",
    "UserDocumentDiagram",
    # User Tracking Models
    "UserContractView",
    "UserPropertyView",
    # Property Models
    "Property",
    "PropertyValuation",
    "PropertyMarketData",
    "PropertyRiskAssessment",
    "ComparableSale",
    "PropertySalesHistory",
    "PropertyRentalHistory",
    "UserSavedProperty",
    "PropertySearch",
    "PropertyReport",
    "PropertyAPIUsage",
    "MarketInsight",
    # Supporting Models
    "SubscriptionPlan",
    "UserSubscription",
    "UsageLog",
    "AnalysisProgress",
    "AnalysisProgressDetailed",
    # Task Management Models
    "TaskRegistry",
    "TaskCheckpoint",
    "RecoveryQueue",
    # History Models
    "UserContractHistory",
    "UserPropertyHistory",
    # Enums
    "AustralianState",
    "UserType",
    "SubscriptionStatus",
    "ContractType",
    "DocumentStatus",
    "ProcessingStatus",  # Legacy alias
    "ContentType",
    "DiagramType",
    "EntityType",
    # Base Classes and Helpers
    "TimestampedBaseModel",
    "SupabaseModelManager",
    "create_model_with_timestamps",
    "update_model_with_timestamps",
]
