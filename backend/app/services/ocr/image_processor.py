"""
Image processing for OCR operations.
"""

import io
from typing import Dict, Any
from PIL import Image
from google.genai.types import Content, Part

from app.clients.base.exceptions import ClientError
from .prompt_generator import PromptGenerator
from .confidence_calculator import ConfidenceCalculator
from .text_enhancer import TextEnhancer

# Constants
MIN_IMAGE_DIMENSION = 1000


class ImageProcessor:
    """Processes images for OCR operations."""

    def __init__(self, gemini_client):
        self.client = gemini_client
        self.prompt_generator = PromptGenerator()
        self.confidence_calculator = ConfidenceCalculator()
        self.text_enhancer = TextEnhancer()

    async def extract_from_image(
        self, image_content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Extract text from image using Gemini OCR."""
        try:
            # Enhance image if enabled
            config = kwargs.get("config", {})
            if config.get("enable_image_enhancement", False):
                enhanced_image = await self.enhance_image(image_content, content_type)
            else:
                enhanced_image = image_content

            # Create OCR prompt
            prompt = self.prompt_generator.create_ocr_prompt(
                1, is_single_image=True, **kwargs
            )

            # Create content with image
            mime_type = f"image/{content_type.replace('image/', '')}"
            content = Content(
                parts=[
                    Part.from_text(text=prompt),
                    Part.from_bytes(data=enhanced_image, mime_type=mime_type),
                ]
            )

            # Send to Gemini for OCR
            response = await self.client.generate_content(content)

            extracted_text = response.get("text", "") if response else ""
            confidence = self.confidence_calculator.calculate_confidence(extracted_text)

            # Apply text enhancement if enabled
            if config.get("enable_text_enhancement", False) and extracted_text:
                enhanced_text = await self.text_enhancer.enhance_extracted_text(
                    extracted_text, **kwargs
                )
                extracted_text = enhanced_text.get("text", extracted_text)

            return {
                "extracted_text": extracted_text,
                "extraction_method": "gemini_ocr_image",
                "extraction_confidence": confidence,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()) if extracted_text else 0,
                "processing_details": {
                    "image_enhanced": config.get("enable_image_enhancement", False),
                    "content_type": content_type,
                },
            }

        except Exception as e:
            raise ClientError(
                f"Image OCR processing failed: {str(e)}",
                client_name="ImageProcessor",
                original_error=e,
            )

    async def enhance_image(self, image_content: bytes, content_type: str) -> bytes:
        """Enhance image quality for better OCR results."""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Enhance image quality for OCR
            width, height = image.size
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                scale_factor = max(
                    MIN_IMAGE_DIMENSION / width, MIN_IMAGE_DIMENSION / height
                )
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save enhanced image
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="PNG", optimize=True)
            return output_buffer.getvalue()

        except Exception as e:
            # If enhancement fails, return original
            return image_content
