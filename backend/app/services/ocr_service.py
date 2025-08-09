"""
OCR Service - DEPRECATED AND REMOVED

This service has been superseded by GeminiOCRService.
Please use GeminiOCRService instead:
    from app.services.ai.gemini_ocr_service import GeminiOCRService

This file is kept only for import compatibility and will be removed in the next version.
"""

import warnings
from app.services.ai.gemini_ocr_service import GeminiOCRService

# Deprecation warning for any remaining imports
warnings.warn(
    "OCRService is deprecated and has been removed. Use GeminiOCRService instead.",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility alias - redirects to GeminiOCRService
OCRService = GeminiOCRService

# Compatibility function
async def get_ocr_service():
    """DEPRECATED: Use get_ocr_service from app.services instead."""
    warnings.warn(
        "get_ocr_service from ocr_service module is deprecated. "
        "Use 'from app.services import get_ocr_service' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from app.services import get_ocr_service as new_get_ocr_service
    return await new_get_ocr_service()



