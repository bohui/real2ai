"""Legacy enums file - now imports from organized enum modules."""

# Import all enums from organized modules
from .enums.geographical import *
from .enums.user import *
from .enums.property import *
from .enums.market import *
from .enums.risk import *
from .enums.content import *
from .enums.diagrams import *
from .enums.entities import *
from .enums.quality import *
from .enums.recommendations import *
from .enums.workflow import *
from .enums.recovery import *
from .enums.cache import *
from .enums.evaluation import *
from .enums.errors import *
from .enums.context import *
from .enums.notifications import *
from .enums.alerts import *


# ============================================================================
# GEOGRAPHICAL & LOCATION ENUMS
# ============================================================================


class AustralianState(str, Enum):
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    NT = "NT"
    ACT = "ACT"


# ============================================================================
# USER & SUBSCRIPTION ENUMS
# ============================================================================


class UserType(str, Enum):
    BUYER = "buyer"
    INVESTOR = "investor"
    AGENT = "agent"


class SubscriptionStatus(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# ============================================================================
# PROPERTY & CONTRACT ENUMS
# ============================================================================


class PropertyType(str, Enum):
    HOUSE = "house"
    UNIT = "unit"
    TOWNHOUSE = "townhouse"
    APARTMENT = "apartment"
    VILLA = "villa"
    LAND = "land"
    ACREAGE = "acreage"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"
    OTHER = "other"


class ContractType(str, Enum):
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    OFF_PLAN = "off_plan"
    AUCTION = "auction"


# ============================================================================
# DOCUMENT & PROCESSING ENUMS
# ============================================================================


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    BASIC_COMPLETE = "basic_complete"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYSIS_COMPLETE = "analysis_complete"
    FAILED = "failed"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    CONTRACT = "contract"
    TITLE_DEED = "title_deed"
    SURVEY = "survey"
    PLANNING_DOCUMENT = "planning_document"
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    LEGAL_CONTRACT = "legal_contract"
    FINANCIAL_DOCUMENT = "financial_document"
    GENERAL_DOCUMENT = "general_document"
    OTHER = "other"


# ============================================================================
# VALUATION & MARKET ENUMS
# ============================================================================


class ValuationSource(str, Enum):
    DOMAIN = "domain"
    CORELOGIC = "corelogic"
    COMBINED = "combined"


class ValuationType(str, Enum):
    AVM = "avm"
    DESKTOP = "desktop"
    PROFESSIONAL = "professional"


class MarketOutlook(str, Enum):
    DECLINING = "declining"
    STABLE = "stable"
    GROWING = "growing"
    STRONG_GROWTH = "strong_growth"


class MarketTrend(Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class MarketSegment(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    LUXURY = "luxury"
    AFFORDABLE = "affordable"


class LiquidityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# RISK & ANALYSIS ENUMS
# ============================================================================


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class VarianceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ReliabilityRating(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


# ============================================================================
# INSIGHT & CONTENT ENUMS
# ============================================================================


class InsightType(str, Enum):
    TREND = "trend"
    FORECAST = "forecast"
    COMPARISON = "comparison"
    HOTSPOT = "hotspot"


class ViewSource(str, Enum):
    SEARCH = "search"
    BOOKMARK = "bookmark"
    ANALYSIS = "analysis"
    UPLOAD = "upload"
    CACHE_HIT = "cache_hit"
    SHARED = "shared"


class ContentType(str, Enum):
    TEXT = "text"
    DIAGRAM = "diagram"
    TABLE = "table"
    SIGNATURE = "signature"
    MIXED = "mixed"
    EMPTY = "empty"


# ============================================================================
# DIAGRAM & IMAGE ENUMS
# ============================================================================


class DiagramType(str, Enum):
    TITLE_PLAN = "title_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    STRATA_PLAN = "strata_plan"
    BODY_CORPORATE_PLAN = "body_corporate_plan"
    DEVELOPMENT_PLAN = "development_plan"
    SUBDIVISION_PLAN = "subdivision_plan"
    OFF_THE_PLAN_MARKETING = "off_the_plan_marketing"
    SITE_PLAN = "site_plan"
    SEWER_SERVICE_DIAGRAM = "sewer_service_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    ZONING_MAP = "zoning_map"
    ENVIRONMENTAL_OVERLAY = "environmental_overlay"
    HERITAGE_OVERLAY = "heritage_overlay"
    CONTOUR_MAP = "contour_map"
    DRAINAGE_PLAN = "drainage_plan"
    UTILITY_PLAN = "utility_plan"
    PARKING_PLAN = "parking_plan"
    LANDSCAPE_PLAN = "landscape_plan"
    BUILDING_ENVELOPE_PLAN = "building_envelope_plan"
    UNKNOWN = "unknown"


class ImageType(str, Enum):
    """Types of images/diagrams that can be analyzed"""

    SITE_PLAN = "site_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    SEWER_SERVICE_DIAGRAM = "sewer_service_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    ZONING_MAP = "zoning_map"
    ENVIRONMENTAL_OVERLAY = "environmental_overlay"
    CONTOUR_MAP = "contour_map"
    DRAINAGE_PLAN = "drainage_plan"
    UTILITY_PLAN = "utility_plan"
    BUILDING_ENVELOPE_PLAN = "building_envelope_plan"
    STRATA_PLAN = "strata_plan"
    AERIAL_VIEW = "aerial_view"
    CROSS_SECTION = "cross_section"
    ELEVATION_VIEW = "elevation_view"
    LANDSCAPE_PLAN = "landscape_plan"
    PARKING_PLAN = "parking_plan"
    UNKNOWN = "unknown"


# ============================================================================
# ENTITY EXTRACTION ENUMS
# ============================================================================


class EntityType(str, Enum):
    ADDRESS = "address"
    PROPERTY_REFERENCE = "property_reference"
    DATE = "date"
    FINANCIAL_AMOUNT = "financial_amount"
    PARTY_NAME = "party_name"
    LEGAL_REFERENCE = "legal_reference"
    CONTACT_INFO = "contact_info"
    PROPERTY_DETAILS = "property_details"


class PartyRole(str, Enum):
    VENDOR = "vendor"
    PURCHASER = "purchaser"
    LANDLORD = "landlord"
    TENANT = "tenant"
    AGENT = "agent"
    SOLICITOR = "solicitor"
    CONVEYANCER = "conveyancer"
    OTHER = "other"


class DateType(str, Enum):
    CONTRACT_DATE = "contract_date"
    SETTLEMENT_DATE = "settlement_date"
    INSPECTION_DATE = "inspection_date"
    EXPIRY_DATE = "expiry_date"
    OTHER = "other"


class FinancialType(str, Enum):
    PURCHASE_PRICE = "purchase_price"
    DEPOSIT = "deposit"
    STAMP_DUTY = "stamp_duty"
    LEGAL_FEES = "legal_fees"
    OTHER = "other"


# ============================================================================
# CONFIDENCE & QUALITY ENUMS
# ============================================================================


class ConfidenceLevel(str, Enum):
    """Confidence levels for semantic extraction"""

    HIGH = "high"  # >90% confidence
    MEDIUM = "medium"  # 70-90% confidence
    LOW = "low"  # 50-70% confidence
    UNCERTAIN = "uncertain"  # <50% confidence


class QualityTier(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


# ============================================================================
# RECOMMENDATION ENUMS
# ============================================================================


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCategory(str, Enum):
    LEGAL = "legal"
    FINANCIAL = "financial"
    PROPERTY = "property"
    MARKET = "market"
    RISK = "risk"
    OTHER = "other"


# ============================================================================
# WORKFLOW & PROCESSING ENUMS
# ============================================================================


class WorkflowStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskState(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    PROCESSING = "processing"
    CHECKPOINT = "checkpoint"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERING = "recovering"
    PARTIAL = "partial"
    ORPHANED = "orphaned"


class ProcessingPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# RECOVERY & RETRY ENUMS
# ============================================================================


class RecoveryMethod(str, Enum):
    RESUME_CHECKPOINT = "resume_checkpoint"
    RESTART_CLEAN = "restart_clean"
    VALIDATE_ONLY = "validate_only"
    MANUAL_INTERVENTION = "manual_intervention"


class RetryStrategy(str, Enum):
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"


# ============================================================================
# CACHE & PERFORMANCE ENUMS
# ============================================================================


class CacheStatus(str, Enum):
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"


class CachePolicy(Enum):
    NO_CACHE = "no_cache"
    CACHE_FIRST = "cache_first"
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"
    CACHE_ONLY = "cache_only"


class CachePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# EVALUATION & MONITORING ENUMS
# ============================================================================


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    OTHER = "other"


class EvaluationMode(Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"


# ============================================================================
# ERROR & VALIDATION ENUMS
# ============================================================================


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    EXTERNAL = "external"
    OTHER = "other"


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# CONTEXT & OUTPUT ENUMS
# ============================================================================


class ContextType(Enum):
    USER_PROFILE = "user_profile"
    PROPERTY_CONTEXT = "property_context"
    MARKET_CONTEXT = "market_context"
    DOCUMENT_CONTEXT = "document_context"
    SESSION_CONTEXT = "session_context"


class OutputFormat(str, Enum):
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"


# ============================================================================
# NOTIFICATION ENUMS
# ============================================================================


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# ALERT ENUMS
# ============================================================================


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
