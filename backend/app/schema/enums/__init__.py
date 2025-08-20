"""
Central enum package for the application.
Import all enums from their respective category modules.
"""

# Geographical & Location Enums
from .geographical import AustralianState

# User & Subscription Enums
from .user import UserType, SubscriptionStatus

# Property & Contract Enums
from .property import (
    PropertyType,
    ContractType,
    DocumentType,
    DocumentStatus,
    ProcessingStatus,
    PurchaseMethod,
    UseCategory,
)

# Valuation & Market Enums
from .market import (
    ValuationSource,
    ValuationType,
    MarketOutlook,
    MarketTrend,
    MarketSegment,
    LiquidityLevel,
)

# Risk & Analysis Enums
from .risk import RiskLevel, RiskSeverity, VarianceLevel, ReliabilityRating

# Insight & Content Enums
from .content import InsightType, ViewSource, ContentType

# Diagram & Image Enums
from .diagrams import DiagramType, ImageType

# Entity Extraction Enums
from .entities import EntityType, PartyRole, DateType, FinancialType

# Confidence & Quality Enums
from .quality import ConfidenceLevel, QualityTier

# Recommendation Enums
from .recommendations import RecommendationPriority, RecommendationCategory

# Workflow & Processing Enums
from .workflow import (
    WorkflowStepStatus,
    RunStatus,
    StepStatus,
    TaskState,
    ProcessingPriority,
)

# Recovery & Retry Enums
from .recovery import RecoveryMethod, RetryStrategy

# Cache & Performance Enums
from .cache import CacheStatus, CachePolicy, CachePriority

# Evaluation & Monitoring Enums
from .evaluation import EvaluationStatus, MetricType, EvaluationMode

# Error & Validation Enums
from .errors import (
    ErrorCategory,
    ErrorSeverity,
    PromptErrorSeverity,
    ValidationSeverity,
)

# Context & Output Enums
from .context import ContextType, OutputFormat

# Notification Enums
from .notifications import NotificationType, NotificationPriority

# Alert Enums
from .alerts import AlertSeverity

__all__ = [
    # Geographical
    "AustralianState",
    # User & Subscription
    "UserType",
    "SubscriptionStatus",
    # Property & Contract
    "PropertyType",
    "ContractType",
    "DocumentType",
    "DocumentStatus",
    "ProcessingStatus",
    "PurchaseMethod",
    "UseCategory",
    # Valuation & Market
    "ValuationSource",
    "ValuationType",
    "MarketOutlook",
    "MarketTrend",
    "MarketSegment",
    "LiquidityLevel",
    # Risk & Analysis
    "RiskLevel",
    "RiskSeverity",
    "VarianceLevel",
    "ReliabilityRating",
    # Insight & Content
    "InsightType",
    "ViewSource",
    "ContentType",
    # Diagram & Image
    "DiagramType",
    "ImageType",
    # Entity Extraction
    "EntityType",
    "PartyRole",
    "DateType",
    "FinancialType",
    # Confidence & Quality
    "ConfidenceLevel",
    "QualityTier",
    # Recommendation
    "RecommendationPriority",
    "RecommendationCategory",
    # Workflow & Processing
    "WorkflowStepStatus",
    "RunStatus",
    "StepStatus",
    "TaskState",
    "ProcessingPriority",
    # Recovery & Retry
    "RecoveryMethod",
    "RetryStrategy",
    # Cache & Performance
    "CacheStatus",
    "CachePolicy",
    "CachePriority",
    # Evaluation & Monitoring
    "EvaluationStatus",
    "MetricType",
    "EvaluationMode",
    # Error & Validation
    "ErrorCategory",
    "ErrorSeverity",
    "PromptErrorSeverity",
    "ValidationSeverity",
    # Context & Output
    "ContextType",
    "OutputFormat",
    # Notification
    "NotificationType",
    "NotificationPriority",
    # Alert
    "AlertSeverity",
]
