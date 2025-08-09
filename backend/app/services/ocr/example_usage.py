"""
Example usage of the refactored OCR architecture.
"""

import asyncio
from app.services.ocr import create_ocr_service


async def example_usage():
    """
    Example showing how to use the new OCR service architecture.
    
    This demonstrates the proper layered architecture:
    1. Thin Gemini client (connection only)
    2. OCR service (orchestration)  
    3. Specialized processors (business logic)
    """
    
    # Create OCR service using factory (with proper dependency injection)
    ocr_service = await create_ocr_service()
    
    # Example file content (would be real image/PDF bytes in practice)
    example_image = b"example_image_bytes"
    example_pdf = b"example_pdf_bytes"
    
    # Extract text from image
    try:
        image_result = await ocr_service.extract_text(
            content=example_image,
            content_type="image/png"
        )
        print("Image OCR result:", image_result)
    except Exception as e:
        print(f"Image OCR failed: {e}")
    
    # Extract text from PDF
    try:
        pdf_result = await ocr_service.extract_text(
            content=example_pdf,
            content_type="application/pdf"
        )
        print("PDF OCR result:", pdf_result)
    except Exception as e:
        print(f"PDF OCR failed: {e}")
    
    # Analyze document
    try:
        analysis_result = await ocr_service.analyze_document(
            content=example_pdf,
            content_type="application/pdf",
            contract_context={
                "australian_state": "NSW",
                "contract_type": "purchase_agreement"
            }
        )
        print("Document analysis result:", analysis_result)
    except Exception as e:
        print(f"Document analysis failed: {e}")
    
    # Check service health
    health = await ocr_service.health_check()
    print("Service health:", health)


if __name__ == "__main__":
    asyncio.run(example_usage())