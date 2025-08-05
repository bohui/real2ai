"""
Gemini OCR Service V4 - Enhanced with Pydantic Output Parser Integration
Demonstrates the new structured output parsing capabilities
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.prompts.service_mixin import PromptEnabledService
from app.core.prompts.output_parser import create_parser, ParsingResult
from app.models.contract_state import ProcessingStatus, AustralianState, ContractType
from app.prompts.template.image_semantics_schema import ImageSemantics, ImageType
from app.clients import get_gemini_client
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


class GeminiOCRServiceV4(PromptEnabledService):
    """
    Advanced OCR service with integrated Pydantic output parsing
    
    This version demonstrates the new parser integration:
    - Automatic format instruction generation
    - Structured output validation
    - Graceful error handling and fallbacks
    - Improved reliability and maintainability
    """

    def __init__(self):
        super().__init__()
        
        self.settings = get_settings()
        self.gemini_client = None
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.supported_formats = {
            "pdf", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"
        }

    async def initialize(self):
        """Initialize Gemini OCR service"""
        try:
            self.gemini_client = await get_gemini_client()
            if hasattr(self.gemini_client, "ocr") and self.gemini_client.ocr:
                logger.info("Gemini OCR service V4 initialized with parser integration")
                return True
            else:
                logger.warning("GeminiClient does not have OCR capabilities")
                return False

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to Gemini service: {e}")
            raise HTTPException(
                status_code=503,
                detail="Gemini OCR service unavailable - connection failed",
            )

    async def extract_image_semantics_structured(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        image_type: Optional[ImageType] = None,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_focus: Optional[str] = None,
        risk_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract semantic meaning with structured output parsing
        
        This method demonstrates the new parser integration:
        1. Creates Pydantic parser for ImageSemantics
        2. Renders prompt with auto-generated format instructions  
        3. Parses AI response with validation and error handling
        4. Returns structured, validated results
        """
        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)
            
            # Auto-detect image type if needed
            if image_type is None:
                image_type = await self._detect_image_type(filename, contract_context)
            
            # Create Pydantic output parser
            semantic_parser = create_parser(ImageSemantics)
            
            # Prepare context for semantic analysis
            context = self.create_context(
                image_type=image_type.value if image_type else "unknown",
                contract_context=contract_context or {},
                analysis_focus=analysis_focus or "comprehensive",
                risk_categories=risk_categories or [],
                filename=filename,
                file_type=file_type
            )
            
            # Render prompt with automatic format instructions
            analysis_prompt = await self.render_with_parser(
                template_name="image_semantics",
                context=context,
                output_parser=semantic_parser,
                validate=True,
                use_cache=True
            )
            
            logger.debug(f"Generated structured prompt for {filename}")
            
            # Get AI response using Gemini client
            try:
                ai_response = await self.gemini_client.analyze_image_semantics(
                    content=file_content,
                    content_type=f"image/{file_type.lower()}" if file_type.lower() != 'pdf' else "application/pdf",
                    analysis_context={
                        "prompt": analysis_prompt,
                        "expects_structured_output": True,
                        "output_format": "json"
                    }
                )
                
                # Parse AI response using integrated parser
                parsing_result = await self.parse_ai_response(
                    template_name="image_semantics",
                    ai_response=ai_response.get("content", ""),
                    output_parser=semantic_parser,
                    use_retry=True
                )
                
                # Handle parsing results
                if parsing_result.success:
                    logger.info(f"Successfully parsed semantic analysis for {filename}")
                    
                    return {
                        "semantic_analysis": parsing_result.parsed_data.dict(),
                        "service": "GeminiOCRServiceV4",
                        "service_version": "v4_parser_integrated",
                        "parsing_success": True,
                        "parsing_confidence": parsing_result.confidence_score,
                        "file_processed": filename,
                        "image_type_detected": image_type.value if image_type else "unknown",
                        "analysis_timestamp": datetime.now(UTC).isoformat(),
                        "processing_metadata": {
                            "prompt_with_format_instructions": True,
                            "validation_errors": parsing_result.validation_errors,
                            "parsing_errors": parsing_result.parsing_errors
                        }
                    }
                else:
                    logger.warning(f"Failed to parse structured output for {filename}: {parsing_result.parsing_errors}")
                    
                    # Fallback: try to extract partial data or return raw response
                    fallback_result = await self._handle_parsing_failure(
                        ai_response, parsing_result, filename
                    )
                    
                    return fallback_result
                
            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded during semantic analysis: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="Semantic analysis quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during semantic analysis: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Semantic analysis failed: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during structured semantic analysis: {str(e)}")
            return {
                "semantic_analysis": None,
                "service": "GeminiOCRServiceV4",
                "service_version": "v4_parser_error",
                "parsing_success": False,
                "file_processed": filename,
                "error": str(e),
                "error_type": type(e).__name__,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

    async def _handle_parsing_failure(
        self, 
        ai_response: Dict[str, Any], 
        parsing_result: ParsingResult,
        filename: str
    ) -> Dict[str, Any]:
        """
        Handle parsing failures with graceful fallback strategies
        """
        logger.warning(f"Implementing fallback for parsing failure on {filename}")
        
        # Strategy 1: Try to extract partial structured data
        if parsing_result.raw_output and isinstance(parsing_result.raw_output, str):
            try:
                # Attempt manual structure extraction
                fallback_data = self._attempt_manual_structure_extraction(parsing_result.raw_output)
                if fallback_data:
                    logger.info(f"Recovered partial structured data for {filename}")
                    return {
                        "semantic_analysis": fallback_data,
                        "service": "GeminiOCRServiceV4",
                        "service_version": "v4_fallback_recovery",
                        "parsing_success": False,
                        "parsing_recovery": True,
                        "file_processed": filename,
                        "analysis_timestamp": datetime.now(UTC).isoformat(),
                        "processing_metadata": {
                            "parsing_errors": parsing_result.parsing_errors,
                            "validation_errors": parsing_result.validation_errors,
                            "recovery_method": "manual_extraction"
                        }
                    }
            except Exception as e:
                logger.warning(f"Manual structure extraction failed: {e}")
        
        # Strategy 2: Return raw response with error metadata
        return {
            "semantic_analysis": ai_response,
            "service": "GeminiOCRServiceV4",
            "service_version": "v4_raw_fallback",
            "parsing_success": False,
            "parsing_recovery": False,
            "file_processed": filename,
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "processing_metadata": {
                "parsing_errors": parsing_result.parsing_errors,
                "validation_errors": parsing_result.validation_errors,
                "fallback_reason": "Unable to parse or recover structured data"
            }
        }

    def _attempt_manual_structure_extraction(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to manually extract structure from raw AI output
        This is a fallback strategy when automatic parsing fails
        """
        import json
        import re
        
        try:
            # Try to find JSON-like structures in the text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, raw_output, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    # Basic validation: check if it has expected fields
                    if isinstance(data, dict) and any(
                        key in data for key in ['image_type', 'infrastructure_elements', 'environmental_factors']
                    ):
                        return data
                except json.JSONDecodeError:
                    continue
            
            # If JSON extraction fails, try to build basic structure from text
            basic_structure = {
                "image_type": "unknown",
                "infrastructure_elements": [],
                "environmental_factors": [],
                "boundary_information": {},
                "risk_assessment": {
                    "overall_risk_level": "unknown",
                    "risk_factors": []
                },
                "extracted_text": raw_output[:1000],  # First 1000 chars as fallback
                "analysis_quality": "low_confidence_fallback"
            }
            
            return basic_structure
            
        except Exception as e:
            logger.error(f"Manual structure extraction failed: {e}")
            return None

    async def _detect_image_type(
        self, 
        filename: str, 
        contract_context: Optional[Dict[str, Any]]
    ) -> ImageType:
        """Detect image type based on filename and context"""
        filename_lower = filename.lower()
        
        # Simple detection based on common patterns
        if "sewer" in filename_lower or "service" in filename_lower:
            return ImageType.SEWER_SERVICE_DIAGRAM
        elif "title" in filename_lower or "plan" in filename_lower:
            return ImageType.TITLE_PLAN
        elif "survey" in filename_lower:
            return ImageType.SURVEY_DIAGRAM
        elif "flood" in filename_lower:
            return ImageType.FLOOD_MAP
        elif "bushfire" in filename_lower or "fire" in filename_lower:
            return ImageType.BUSHFIRE_MAP
        else:
            return ImageType.SITE_PLAN  # Default fallback

    def _validate_file(self, file_content: bytes, file_type: str):
        """Validate file size and format"""
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.max_file_size / 1024 / 1024}MB",
            )

        if file_type.lower() not in self.supported_formats:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format: {file_type}"
            )

        if len(file_content) == 0:
            raise HTTPException(
                status_code=400, detail="Empty file cannot be processed"
            )

    # Comparison method to show the difference
    async def extract_image_semantics_legacy(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        image_type: Optional[ImageType] = None,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Legacy method without parser integration (for comparison)
        
        Problems with this approach:
        1. Manual JSON instructions in template
        2. Manual parsing with error-prone string manipulation  
        3. No validation of output structure
        4. Inconsistent error handling
        5. Schema duplication (Pydantic model + template instructions)
        """
        # ... legacy implementation would go here
        # This demonstrates the old way without parser integration
        pass


# Usage example and migration guide
async def example_usage():
    """Example showing how to use the new parser-integrated service"""
    
    # Initialize service
    service = GeminiOCRServiceV4()
    await service.initialize()
    
    # Example file content (would be real image bytes in practice)
    file_content = b"example_image_bytes"
    
    # Use new structured analysis
    result = await service.extract_image_semantics_structured(
        file_content=file_content,
        file_type="png",
        filename="sewer_service_plan.png",
        image_type=ImageType.SEWER_SERVICE_DIAGRAM,
        analysis_focus="infrastructure"
    )
    
    # Check if parsing was successful
    if result.get("parsing_success"):
        semantic_data = result["semantic_analysis"]
        print(f"Successfully parsed structured data: {semantic_data}")
        
        # Access structured fields (now guaranteed to exist and be typed)
        infrastructure = semantic_data.get("infrastructure_elements", [])
        risk_level = semantic_data.get("risk_assessment", {}).get("overall_risk_level")
        
    else:
        print(f"Parsing failed, using fallback: {result.get('processing_metadata', {})}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())