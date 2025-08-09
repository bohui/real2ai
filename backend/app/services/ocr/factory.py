"""
Factory for creating OCR service instances with proper dependency injection.
"""

from app.clients import get_gemini_client
from app.clients.gemini.config import GeminiClientConfig
from .ocr_service import OCRService


async def create_ocr_service(config: GeminiClientConfig = None) -> OCRService:
    """
    Factory function to create OCR service with proper dependency injection.
    
    Args:
        config: Optional Gemini client configuration
        
    Returns:
        Configured OCR service instance
    """
    # Get or create Gemini client
    gemini_client = await get_gemini_client()
    
    # Use provided config or get from client
    if config is None:
        config = gemini_client.config
    
    # Create and return OCR service
    return OCRService(gemini_client.ocr, config)