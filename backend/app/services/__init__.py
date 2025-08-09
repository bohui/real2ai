"""
Application services
"""

import logging
from typing import Optional, Dict, Any

from .contract_analysis_service import (
    ContractAnalysisService,
    create_contract_analysis_service,
)

# Service imports (refactored to use client architecture)
from .gemini_service import GeminiService
from .openai_service import OpenAIService
from .gemini_ocr_service import GeminiOCRService
from .document_service import DocumentService

__all__ = [
    "GeminiService",
    "OpenAIService",
    "DocumentService",
]

logger = logging.getLogger(__name__)

# Service Factory Functions

# Service factory instance
_service_instances = {}


async def get_gemini_service(user_client=None) -> GeminiService:
    """
    Get initialized GeminiService instance.

    Args:
        user_client: Optional user client for dependency injection

    Returns:
        GeminiService instance
    """
    cache_key = f"gemini_{id(user_client) if user_client else 'default'}"

    if cache_key not in _service_instances:
        service = GeminiService(user_client=user_client)
        await service.initialize()
        _service_instances[cache_key] = service

    return _service_instances[cache_key]


async def get_openai_service(user_client=None) -> OpenAIService:
    """
    Get initialized OpenAIService instance.

    Args:
        user_client: Optional user client for dependency injection

    Returns:
        OpenAIService instance
    """
    cache_key = f"openai_{id(user_client) if user_client else 'default'}"

    if cache_key not in _service_instances:
        service = OpenAIService(user_client=user_client)
        await service.initialize()
        _service_instances[cache_key] = service

    return _service_instances[cache_key]


async def get_ocr_service() -> GeminiOCRService:
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
    service = GeminiOCRService()
    await service.initialize()
    return service


async def get_document_service() -> DocumentService:
    """
    Get document service instance with client architecture.

    Returns:
        Initialized document service instance
    """
    service = DocumentService(use_llm_document_processing=True)
    await service.initialize()
    return service


async def get_contract_analysis_service() -> ContractAnalysisService:
    """
    Get unified contract analysis service instance with enhanced features.

    Returns:
        Initialized unified contract analysis service instance
    """
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


# Export commonly used services
__all__ = [
    # Services
    "GeminiService",
    "OpenAIService",
    "GeminiOCRService",
    "DocumentService",
    "ContractAnalysisService",
    # Factory functions
    "get_gemini_service",
    "get_openai_service",
    "get_ocr_service",
    "get_document_service",
    "get_contract_analysis_service",
    "create_contract_analysis_service",
    # Health utilities
    "check_all_services_health",
]
