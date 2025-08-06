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
    ContractAnalysis,
    
    # Document Processing Models
    DocumentPage,
    DocumentEntity,
    DocumentDiagram,
    DocumentAnalysis,
    
    # Supporting Models
    PropertyData,
    SubscriptionPlan,
    UserSubscription,
    UsageLog,
    AnalysisProgress,
    
    # Enums
    AustralianState,
    UserType,
    SubscriptionStatus,
    ContractType,
    DocumentStatus,
    ContentType,
    DiagramType,
    EntityType,
    AnalysisStatus,
    
    # Base Classes and Helpers
    TimestampedBaseModel,
    SupabaseModelManager,
    create_model_with_timestamps,
    update_model_with_timestamps,
)

# Legacy aliases for backward compatibility
ProcessingStatus = DocumentStatus  # For existing code using ProcessingStatus

__all__ = [
    # Core Models
    "Profile",
    "Document",
    "Contract", 
    "ContractAnalysis",
    
    # Document Processing Models
    "DocumentPage",
    "DocumentEntity", 
    "DocumentDiagram",
    "DocumentAnalysis",
    
    # Supporting Models
    "PropertyData",
    "SubscriptionPlan",
    "UserSubscription", 
    "UsageLog",
    "AnalysisProgress",
    
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
    "AnalysisStatus",
    
    # Base Classes and Helpers
    "TimestampedBaseModel",
    "SupabaseModelManager",
    "create_model_with_timestamps",
    "update_model_with_timestamps",
]