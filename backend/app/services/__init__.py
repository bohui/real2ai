from __future__ import annotations

"""
Application services
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Check if we're in a script context and should suppress warnings
_is_script_context = (
    "scripts/" in os.getcwd()
    or any("scripts" in arg for arg in __import__("sys").argv)
    or any("clear_data.py" in arg for arg in __import__("sys").argv)
)

# Core services (with optional imports for complex dependencies)
try:
    from .contract_analysis_service import (
        ContractAnalysisService,
        create_contract_analysis_service,
    )

    _CONTRACT_ANALYSIS_AVAILABLE = True
except ImportError:
    ContractAnalysisService = None
    create_contract_analysis_service = None
    _CONTRACT_ANALYSIS_AVAILABLE = False

# Core services with optional import handling
try:
    from .document_service import DocumentService

    _DOCUMENT_SERVICE_AVAILABLE = True
except ImportError as e:
    DocumentService = None
    _DOCUMENT_SERVICE_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"DocumentService not available: {e}")

try:
    from .evaluation_service import EvaluationOrchestrator as EvaluationService

    _EVALUATION_SERVICE_AVAILABLE = True
except ImportError as e:
    EvaluationService = None
    _EVALUATION_SERVICE_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"EvaluationService not available: {e}")

try:
    from .backend_token_service import BackendTokenService

    _BACKEND_TOKEN_SERVICE_AVAILABLE = True
except ImportError as e:
    BackendTokenService = None
    _BACKEND_TOKEN_SERVICE_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"BackendTokenService not available: {e}")

try:
    from .recovery_monitor import RecoveryMonitor

    _RECOVERY_MONITOR_AVAILABLE = True
except ImportError as e:
    RecoveryMonitor = None
    _RECOVERY_MONITOR_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"RecoveryMonitor not available: {e}")

try:
    from .ocr_performance_service import OCRPerformanceService

    _OCR_PERFORMANCE_SERVICE_AVAILABLE = True
except ImportError as e:
    OCRPerformanceService = None
    _OCR_PERFORMANCE_SERVICE_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"OCRPerformanceService not available: {e}")

# AI services with optional import handling
try:
    from .ai import (
        GeminiService,
        OpenAIService,
        GeminiOCRService,
        LLMService,
    )

    _AI_SERVICES_AVAILABLE = True
except ImportError as e:
    GeminiService = None
    OpenAIService = None
    GeminiOCRService = None
    LLMService = None
    _AI_SERVICES_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"AI services not available: {e}")

# Property services with optional import handling
try:
    from .property import (
        PropertyProfileService,
        PropertyValuationService,
        PropertyIntelligenceService,
        MarketAnalysisService,
        MarketIntelligenceService,
        ValuationComparisonService,
    )

    _PROPERTY_SERVICES_AVAILABLE = True
except ImportError as e:
    PropertyProfileService = None
    PropertyValuationService = None
    PropertyIntelligenceService = None
    MarketAnalysisService = None
    MarketIntelligenceService = None
    ValuationComparisonService = None
    _PROPERTY_SERVICES_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"Property services not available: {e}")

# Cache services with optional import handling
try:
    from .cache import (
        CacheService,
        get_cache_service,
        UnifiedCacheService,
        create_unified_cache_service,
    )

    _CACHE_SERVICES_AVAILABLE = True
except ImportError as e:
    CacheService = None
    get_cache_service = None
    UnifiedCacheService = None
    create_unified_cache_service = None
    _CACHE_SERVICES_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"Cache services not available: {e}")

# Communication services with optional import handling
try:
    from .communication import (
        WebSocketService,
        WebSocketManager,
        redis_pubsub_service,
    )

    _COMMUNICATION_SERVICES_AVAILABLE = True
except ImportError as e:
    WebSocketService = None
    WebSocketManager = None
    redis_pubsub_service = None
    _COMMUNICATION_SERVICES_AVAILABLE = False
    if not _is_script_context:
        logger.warning(f"Communication services not available: {e}")

# Note: Legacy `app.services.ocr_service` import removed to avoid noisy startup logs.

__all__ = [
    # Core services
    "ContractAnalysisService",
    "create_contract_analysis_service",
    "DocumentService",
    "EvaluationService",
    "BackendTokenService",
    "RecoveryMonitor",
    "OCRPerformanceService",
    # AI services
    "GeminiService",
    "OpenAIService",
    "GeminiOCRService",
    "LLMService",
    # Property services
    "PropertyProfileService",
    "PropertyValuationService",
    "PropertyIntelligenceService",
    "MarketAnalysisService",
    "MarketIntelligenceService",
    "ValuationComparisonService",
    # Cache services
    "CacheService",
    "get_cache_service",
    "UnifiedCacheService",
    "create_unified_cache_service",
    # Communication services
    "WebSocketService",
    "WebSocketManager",
    "redis_pubsub_service",
    # Legacy compatibility
    "get_ocr_service",
    # Factory functions
    "get_gemini_service",
    "get_openai_service",
    "get_llm_service",
    "get_document_service",
    "get_contract_analysis_service",
    "check_all_services_health",
]

# Service Factory Functions

# Service factory instance
_service_instances = {}


async def get_gemini_service(user_client=None):
    """
    Get initialized GeminiService instance.

    Args:
        user_client: Optional user client for dependency injection

    Returns:
        GeminiService instance
    """
    if not _AI_SERVICES_AVAILABLE or GeminiService is None:
        raise ImportError("GeminiService is not available due to missing dependencies")

    cache_key = f"gemini_{id(user_client) if user_client else 'default'}"

    if cache_key not in _service_instances:
        service = GeminiService(user_client=user_client)
        await service.initialize()
        _service_instances[cache_key] = service

    return _service_instances[cache_key]


async def get_openai_service(user_client=None):
    """
    Get initialized OpenAIService instance.

    Args:
        user_client: Optional user client for dependency injection

    Returns:
        OpenAIService instance
    """
    if not _AI_SERVICES_AVAILABLE or OpenAIService is None:
        raise ImportError("OpenAIService is not available due to missing dependencies")

    cache_key = f"openai_{id(user_client) if user_client else 'default'}"

    if cache_key not in _service_instances:
        service = OpenAIService(user_client=user_client)
        await service.initialize()
        _service_instances[cache_key] = service

    return _service_instances[cache_key]


async def get_llm_service(user_client=None):
    """
    Get initialized LLMService instance.

    Args:
        user_client: Optional user client for dependency injection

    Returns:
        LLMService instance
    """
    if not _AI_SERVICES_AVAILABLE or LLMService is None:
        raise ImportError("LLMService is not available due to missing dependencies")

    cache_key = f"llm_{id(user_client) if user_client else 'default'}"

    if cache_key not in _service_instances:
        service = LLMService(user_client=user_client)
        await service.initialize()
        _service_instances[cache_key] = service

    return _service_instances[cache_key]


async def get_ocr_service():
    """
    Get advanced OCR service instance with semantic analysis capabilities.

    This returns GeminiOCRService which provides:
    - Advanced OCR with semantic understanding
    - PromptManager integration for better context awareness
    - Performance optimization with OCRPerformanceService
    - Property document intelligence features

    Returns:
        Initialized GeminiOCRService instance
    """
    if not _AI_SERVICES_AVAILABLE or GeminiOCRService is None:
        raise ImportError(
            "GeminiOCRService is not available due to missing dependencies"
        )

    service = GeminiOCRService()
    await service.initialize()
    return service


async def get_document_service():
    """
    Get document service instance with client architecture.

    Returns:
        Initialized document service instance
    """
    if not _DOCUMENT_SERVICE_AVAILABLE or DocumentService is None:
        raise ImportError(
            "DocumentService is not available due to missing dependencies"
        )

    service = DocumentService(use_llm_document_processing=True)
    await service.initialize()
    return service


async def get_contract_analysis_service():
    """
    Get unified contract analysis service instance with enhanced features.

    Returns:
        Initialized unified contract analysis service instance
    """
    if not _CONTRACT_ANALYSIS_AVAILABLE:
        raise ImportError(
            "ContractAnalysisService is not available due to missing dependencies"
        )

    service = create_contract_analysis_service()
    # Initialize prompt manager if available
    if service.prompt_manager:
        await service.prompt_manager.initialize()
    return service


# Health Check for All Services


async def check_all_services_health() -> Dict[str, Dict[str, Any]]:
    """
    Check health of all available services.

    Returns:
        Dict containing health status of all services
    """
    health_results = {}

    # Gemini Service Health
    try:
        gemini_service = await get_gemini_service()
        health_results["gemini_service"] = await gemini_service.health_check()
    except Exception as e:
        health_results["gemini_service"] = {"status": "error", "error": str(e)}

    # OpenAI Service Health
    try:
        openai_service = await get_openai_service()
        health_results["openai_service"] = await openai_service.health_check()
    except Exception as e:
        health_results["openai_service"] = {"status": "error", "error": str(e)}

    # OCR Service Health
    try:
        ocr_service = await get_ocr_service()
        health_results["ocr_service"] = await ocr_service.health_check()
    except Exception as e:
        health_results["ocr_service"] = {"service_status": "error", "error": str(e)}

    # Document Service Health
    try:
        document_service = await get_document_service()
        health_results["document_service"] = await document_service.health_check()
    except Exception as e:
        health_results["document_service"] = {"status": "error", "error": str(e)}

    # Contract Analysis Service Health
    try:
        contract_service = await get_contract_analysis_service()
        health_results["contract_analysis_service"] = (
            await contract_service.get_service_health()
        )
    except Exception as e:
        health_results["contract_analysis_service"] = {
            "status": "error",
            "error": str(e),
        }

    return health_results
