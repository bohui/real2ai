"""
Application services
"""

import logging
from typing import Optional, Dict, Any

# V2 Service imports (refactored to use client architecture)
from .gemini_ocr_service_v2 import GeminiOCRServiceV2
from .document_service_v2 import DocumentServiceV2
from .contract_analysis_service_v2 import ContractAnalysisServiceV2

# Legacy service imports (for backward compatibility)
try:
    from .gemini_ocr_service import GeminiOCRService
    LEGACY_OCR_AVAILABLE = True
except ImportError:
    LEGACY_OCR_AVAILABLE = False

try:
    from .document_service import DocumentService
    LEGACY_DOCUMENT_AVAILABLE = True
except ImportError:
    LEGACY_DOCUMENT_AVAILABLE = False

try:
    from .contract_analysis_service import ContractAnalysisService
    LEGACY_CONTRACT_AVAILABLE = True
except ImportError:
    LEGACY_CONTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Service Factory Functions for Smooth Migration

async def get_ocr_service(use_v2: bool = True) -> GeminiOCRServiceV2:
    """
    Get OCR service instance (defaults to V2 with service role auth).
    
    Args:
        use_v2: Whether to use the V2 service (recommended)
        
    Returns:
        Initialized OCR service instance
    """
    if use_v2:
        service = GeminiOCRServiceV2()
        await service.initialize()
        return service
    else:
        if not LEGACY_OCR_AVAILABLE:
            logger.warning("Legacy OCR service requested but not available, using V2")
            service = GeminiOCRServiceV2()
            await service.initialize()
            return service
        else:
            # Legacy service initialization
            from .gemini_ocr_service import GeminiOCRService
            service = GeminiOCRService()
            await service.initialize()
            return service

async def get_document_service(use_v2: bool = True) -> DocumentServiceV2:
    """
    Get document service instance (defaults to V2 with client architecture).
    
    Args:
        use_v2: Whether to use the V2 service (recommended)
        
    Returns:
        Initialized document service instance
    """
    if use_v2:
        service = DocumentServiceV2()
        await service.initialize()
        return service
    else:
        if not LEGACY_DOCUMENT_AVAILABLE:
            logger.warning("Legacy document service requested but not available, using V2")
            service = DocumentServiceV2()
            await service.initialize()
            return service
        else:
            # Legacy service initialization
            from .document_service import DocumentService
            service = DocumentService()
            await service.initialize()
            return service

async def get_contract_analysis_service(use_v2: bool = True) -> ContractAnalysisServiceV2:
    """
    Get contract analysis service instance (defaults to V2 with GeminiClient).
    
    Args:
        use_v2: Whether to use the V2 service (recommended)
        
    Returns:
        Initialized contract analysis service instance
    """
    if use_v2:
        service = ContractAnalysisServiceV2()
        await service.initialize()
        return service
    else:
        if not LEGACY_CONTRACT_AVAILABLE:
            logger.warning("Legacy contract analysis service requested but not available, using V2")
            service = ContractAnalysisServiceV2()
            await service.initialize()
            return service
        else:
            # Legacy service initialization
            from .contract_analysis_service import ContractAnalysisService
            service = ContractAnalysisService()
            await service.initialize()
            return service

# Health Check for All Services

async def check_all_services_health() -> Dict[str, Dict[str, Any]]:
    """
    Check health of all available services.
    
    Returns:
        Dict containing health status of all services
    """
    health_results = {}
    
    # V2 Services Health
    try:
        ocr_service = await get_ocr_service(use_v2=True)
        health_results["ocr_service_v2"] = await ocr_service.health_check()
    except Exception as e:
        health_results["ocr_service_v2"] = {
            "service_status": "error",
            "error": str(e)
        }
    
    try:
        document_service = await get_document_service(use_v2=True)
        health_results["document_service_v2"] = await document_service.health_check()
    except Exception as e:
        health_results["document_service_v2"] = {
            "status": "error",
            "error": str(e)
        }
    
    try:
        contract_service = await get_contract_analysis_service(use_v2=True)
        health_results["contract_analysis_service_v2"] = await contract_service.health_check()
    except Exception as e:
        health_results["contract_analysis_service_v2"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Legacy Services Health (if available)
    if LEGACY_OCR_AVAILABLE:
        try:
            legacy_ocr = await get_ocr_service(use_v2=False)
            health_results["ocr_service_legacy"] = await legacy_ocr.health_check()
        except Exception as e:
            health_results["ocr_service_legacy"] = {
                "service_status": "error",
                "error": str(e)
            }
    
    if LEGACY_DOCUMENT_AVAILABLE:
        try:
            legacy_document = await get_document_service(use_v2=False)
            health_results["document_service_legacy"] = await legacy_document.health_check()
        except Exception as e:
            health_results["document_service_legacy"] = {
                "status": "error", 
                "error": str(e)
            }
    
    if LEGACY_CONTRACT_AVAILABLE:
        try:
            legacy_contract = await get_contract_analysis_service(use_v2=False)
            health_results["contract_analysis_service_legacy"] = await legacy_contract.health_check()
        except Exception as e:
            health_results["contract_analysis_service_legacy"] = {
                "status": "error",
                "error": str(e)
            }
    
    return health_results

# Migration Utilities

def get_service_migration_status() -> Dict[str, Any]:
    """
    Get status of service migration from legacy to V2.
    
    Returns:
        Dict containing migration status information
    """
    return {
        "v2_services_available": True,
        "legacy_services_available": {
            "ocr": LEGACY_OCR_AVAILABLE,
            "document": LEGACY_DOCUMENT_AVAILABLE,
            "contract_analysis": LEGACY_CONTRACT_AVAILABLE,
        },
        "recommended_version": "v2",
        "migration_complete": not any([
            LEGACY_OCR_AVAILABLE,
            LEGACY_DOCUMENT_AVAILABLE, 
            LEGACY_CONTRACT_AVAILABLE
        ]),
        "benefits_v2": [
            "Service role authentication support",
            "Unified client architecture",
            "Better error handling",
            "Resource efficiency through shared clients",
            "Easier testing with mockable clients",
            "Consistent health reporting"
        ]
    }

# Export commonly used services
__all__ = [
    # V2 Services (recommended)
    "GeminiOCRServiceV2",
    "DocumentServiceV2", 
    "ContractAnalysisServiceV2",
    
    # Factory functions for easy migration
    "get_ocr_service",
    "get_document_service",
    "get_contract_analysis_service",
    
    # Health and migration utilities
    "check_all_services_health",
    "get_service_migration_status",
]