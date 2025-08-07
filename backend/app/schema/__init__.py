"""Schema module for request/response models."""

# Authentication schemas
from .auth import UserRegistrationRequest, UserLoginRequest, UserResponse

# Common schemas
from .common import (
    ErrorResponse,
    ValidationError,
    ValidationErrorResponse,
    HealthCheckResponse,
    WebSocketMessage,
    SystemStatsResponse,
)

# Contract schemas
from .contract import (
    AnalysisOptions,
    ContractAnalysisRequest,
    ContractAnalysisResponse,
    RiskFactorResponse,
    RecommendationResponse,
    StampDutyResponse,
    ComplianceCheckResponse,
    ContractAnalysisResult,
    StampDutyCalculationRequest,
    PropertyFinancialSummary,
    WebSocketProgressUpdate,
    ContractAnalysisFromOCR,
)

# Document schemas
from .document import (
    DocumentUploadResponse,
    DocumentDetails,
    DocumentProcessingStatus,
    ReportGenerationRequest,
    ReportResponse,
)

# OCR schemas
from .ocr import (
    OCRCapabilitiesResponse,
    OCRProcessingRequest,
    OCRProcessingResponse,
    OCRExtractionResult,
    BatchOCRRequest,
    BatchOCRResponse,
    OCRStatusResponse,
    EnhancedOCRCapabilities,
    GeminiOCRResult,
    OCRQueueStatus,
    OCRProcessingOptions,
    OCRCostEstimate,
    OCRProgressUpdate,
    BatchOCRProgressUpdate,
    OCRCompletionNotification,
    OCRErrorNotification,
)

# Onboarding schemas
from .onboarding import (
    OnboardingStatusResponse,
    OnboardingPreferencesRequest,
    OnboardingCompleteRequest,
)

# User schemas
from .user import UsageStatsResponse

# Property schemas
from .property import (
    PropertyProfileRequestModel,
    PropertyComparisonRequestModel,
    PropertySearchFilters,
    PropertyAddress,
    PropertyDetails,
    PropertyValuation,
    PropertyMarketData,
    PropertyRiskAssessment,
    ComparableSale,
    PropertySalesHistory,
    PropertyRentalHistory,
    PropertyProfile,
    PropertySearchRequest,
    PropertyProfileResponse,
    PropertyValuationRequest,
    PropertyValuationResponse,
    PropertyAPIHealthStatus,
    PropertyAnalysisDepth,
    MarketInsightRequest,
    PropertySearchFilter,
    PropertyListing,
    PropertySearchResponse,
    PropertyDataValidationResult,
)

# Evaluation schemas
from .evaluation import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    TestDatasetCreate,
    TestDatasetResponse,
    TestCaseCreate,
    TestCaseResponse,
    ModelConfig,
    MetricsConfig,
    EvaluationJobCreate,
    EvaluationJobResponse,
    EvaluationResultResponse,
    ABTestCreate,
    ABTestResponse,
    ModelComparisonResponse,
    JobSummaryResponse,
)

# Enum exports
from .enums import *

__all__ = [
    # Auth
    "UserRegistrationRequest",
    "UserLoginRequest",
    "UserResponse",
    # Common
    "ErrorResponse",
    "ValidationError",
    "ValidationErrorResponse",
    "HealthCheckResponse",
    "WebSocketMessage",
    "SystemStatsResponse",
    # Contract
    "AnalysisOptions",
    "ContractAnalysisRequest",
    "ContractAnalysisResponse",
    "RiskFactorResponse",
    "RecommendationResponse",
    "StampDutyResponse",
    "ComplianceCheckResponse",
    "ContractAnalysisResult",
    "StampDutyCalculationRequest",
    "PropertyFinancialSummary",
    "WebSocketProgressUpdate",
    "ContractAnalysisFromOCR",
    # Document
    "DocumentUploadResponse",
    "DocumentDetails",
    "DocumentProcessingStatus",
    "ReportGenerationRequest",
    "ReportResponse",
    # OCR
    "OCRCapabilitiesResponse",
    "OCRProcessingRequest",
    "OCRProcessingResponse",
    "OCRExtractionResult",
    "BatchOCRRequest",
    "BatchOCRResponse",
    "OCRStatusResponse",
    "EnhancedOCRCapabilities",
    "GeminiOCRResult",
    "OCRQueueStatus",
    "OCRProcessingOptions",
    "OCRCostEstimate",
    "OCRProgressUpdate",
    "BatchOCRProgressUpdate",
    "OCRCompletionNotification",
    "OCRErrorNotification",
    # Onboarding
    "OnboardingStatusResponse",
    "OnboardingPreferencesRequest",
    "OnboardingCompleteRequest",
    # User
    "UsageStatsResponse",
    # Property
    "PropertyProfileRequestModel",
    "PropertyComparisonRequestModel",
    "PropertySearchFilters",
    "PropertyAddress",
    "PropertyDetails",
    "PropertyValuation",
    "PropertyMarketData",
    "PropertyRiskAssessment",
    "ComparableSale",
    "PropertySalesHistory",
    "PropertyRentalHistory",
    "PropertyProfile",
    "PropertySearchRequest",
    "PropertyProfileResponse",
    "PropertyValuationRequest",
    "PropertyValuationResponse",
    "PropertyAPIHealthStatus",
    "PropertyAnalysisDepth",
    "MarketInsightRequest",
    "PropertySearchFilter",
    "PropertyListing",
    "PropertySearchResponse",
    "PropertyDataValidationResult",
    # Evaluation
    "PromptTemplateCreate",
    "PromptTemplateUpdate",
    "PromptTemplateResponse",
    "TestDatasetCreate",
    "TestDatasetResponse",
    "TestCaseCreate",
    "TestCaseResponse",
    "ModelConfig",
    "MetricsConfig",
    "EvaluationJobCreate",
    "EvaluationJobResponse",
    "EvaluationResultResponse",
    "ABTestCreate",
    "ABTestResponse",
    "ModelComparisonResponse",
    "JobSummaryResponse",
]
