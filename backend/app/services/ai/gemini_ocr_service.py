"""
Gemini OCR Service V4 - Enhanced with Pydantic Output Parser Integration
Demonstrates the new structured output parsing capabilities
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.prompts.service_mixin import PromptEnabledService
from app.core.langsmith_config import langsmith_trace
from app.core.prompts.output_parser import create_parser, ParsingResult
from app.services.base.user_aware_service import UserAwareService
from app.models.contract_state import ProcessingStatus, AustralianState, ContractType
from app.prompts.schema.image_semantics_schema import ImageSemantics, ImageType
from app.services.ai.gemini_service import GeminiService
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)
from google.genai.types import Content, Part, GenerateContentConfig
import asyncio

logger = logging.getLogger(__name__)


class GeminiOCRService(PromptEnabledService, UserAwareService):
    """
    Advanced OCR service with integrated Pydantic output parsing

    This version demonstrates the new parser integration:
    - Automatic format instruction generation
    - Structured output validation
    - Graceful error handling and fallbacks
    - Improved reliability and maintainability
    """

    def __init__(self, user_client=None):
        PromptEnabledService.__init__(self)
        UserAwareService.__init__(self, user_client=user_client)

        self.settings = get_settings()
        self.gemini_service = None
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.supported_formats = {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "bmp",
            "tiff",
        }

    async def initialize(self):
        """Initialize Gemini OCR service"""
        try:
            self.gemini_service = GeminiService(user_client=self._user_client)
            await self.gemini_service.initialize()
            logger.info("Gemini OCR service initialized with PromptManager integration")
            return True

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to Gemini service: {e}")
            raise HTTPException(
                status_code=503,
                detail="Gemini OCR service unavailable - connection failed",
            )

    async def generate_ocr_prompt(
        self,
        document_type: Optional[str] = None,
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        page_number: int = 1,
        is_multi_page: bool = False,
        **kwargs,
    ) -> str:
        """Generate context-aware OCR prompt using PromptManager"""

        # Build context for prompt rendering
        context = {
            "document_type": document_type or "general",
            "australian_state": australian_state,
            "contract_type": contract_type,
            "page_number": page_number,
            "is_multi_page": is_multi_page,
            "is_single_image": not is_multi_page,
            **kwargs,
        }

        # Select appropriate template based on context
        template_name = self._select_ocr_template(
            document_type, contract_type, australian_state
        )

        try:
            # Render prompt using PromptManager
            ocr_prompt = await self.render_prompt(
                template_name=template_name, context=context
            )

            logger.debug(
                f"Generated OCR prompt using template '{template_name}' for {document_type}"
            )
            return ocr_prompt

        except Exception as e:
            logger.warning(
                f"Failed to render OCR prompt template '{template_name}': {e}"
            )
            # Fallback to basic OCR prompt
            return self._create_fallback_ocr_prompt(context)

    def _select_ocr_template(
        self,
        document_type: Optional[str],
        contract_type: Optional[str],
        australian_state: Optional[str],
    ) -> str:
        """Select appropriate OCR template based on context"""

        # Priority order: contract_type > australian_state > document_type > general
        if contract_type == "purchase_agreement":
            return "ocr/purchase_agreement_extraction"
        elif contract_type == "lease_agreement":
            return "ocr/lease_agreement_extraction"
        elif australian_state and australian_state.upper() in [
            "NSW",
            "VIC",
            "QLD",
            "WA",
            "SA",
            "TAS",
            "ACT",
            "NT",
        ]:
            return f"ocr/state_specific/{australian_state.lower()}_contract_ocr"
        elif document_type == "legal_contract":
            return "ocr/legal_contract_extraction"
        elif document_type == "financial_document":
            return "ocr/financial_document_extraction"
        else:
            return "ocr/general_document_extraction"

    def _create_fallback_ocr_prompt(self, context: Dict[str, Any]) -> str:
        """Create fallback OCR prompt when template rendering fails"""
        base_prompt = """You are an expert OCR system. Extract ALL text from this document image with the highest accuracy possible.

Instructions:
- Extract every word, number, and symbol visible in the image
- Maintain the original document structure and formatting where possible
- If text is unclear, provide your best interpretation
- Include all headers, subheadings, and section numbers
- Preserve tables and lists with appropriate formatting
- Don't add any explanations or comments - just the extracted text

Focus on accuracy and completeness. Extract all visible text content."""

        # Add context-specific instructions
        if context.get("australian_state"):
            base_prompt += f"\nNote: This appears to be an Australian document from {context['australian_state']}."
        if context.get("contract_type"):
            base_prompt += f"\nDocument type: {context['contract_type']}"
        if context.get("is_multi_page") and not context.get("is_single_image"):
            base_prompt += (
                f"\nThis is page {context['page_number']} of a multi-page document."
            )

        base_prompt += "\n\nExtracted text:"
        return base_prompt

    async def extract_structured_ocr(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        document_type: Optional[str] = None,
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        use_quick_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Extract structured OCR data from entire document with page references

        Args:
            file_content: Document file content as bytes
            file_type: File type (pdf, png, jpg, etc.)
            filename: Original filename
            document_type: Type of document for optimization
            australian_state: Australian state for legal context
            contract_type: Specific contract type
            use_quick_mode: Use simplified extraction schema
            **kwargs: Additional context

        Returns:
            Structured OCR extraction result with page references
        """
        if not self.gemini_service:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Import the schema
            from app.prompts.schema.ocr_extraction_schema import (
                OCRExtractionResult,
                QuickOCRResult,
            )

            # Choose schema based on mode
            schema_class = QuickOCRResult if use_quick_mode else OCRExtractionResult

            # Create Pydantic output parser
            ocr_parser = create_parser(schema_class)

            # Build context for prompt rendering
            context = {
                "document_type": document_type or "general",
                "australian_state": australian_state,
                "contract_type": contract_type,
                "filename": filename,
                "file_type": file_type,
                "use_quick_mode": use_quick_mode,
                "process_entire_document": True,
                **kwargs,
            }

            # Generate context-aware OCR prompt with structured output
            ocr_prompt = await self.generate_ocr_prompt(
                document_type=document_type,
                australian_state=australian_state,
                contract_type=contract_type,
                is_multi_page=False,  # Processing entire document at once
                **kwargs,
            )

            # Render prompt with automatic format instructions for structured output
            structured_prompt = await self.render_with_parser(
                template_name="ocr/whole_document_extraction",
                context=context,
                output_parser=ocr_parser,
                validate=True,
                use_cache=True,
            )

            logger.debug(
                f"Generated structured OCR prompt for entire document: {filename}"
            )

            # Process with Gemini client
            try:
                # Create content based on file type
                if file_type.lower() == "pdf":
                    content_type = "application/pdf"
                else:
                    content_type = f"image/{file_type.lower()}"

                # Use the service's analyze method for structured output
                ai_response = (
                    await self.gemini_service.gemini_client.analyze_image_semantics(
                        content=file_content,
                        content_type=content_type,
                        analysis_context={
                            "prompt": structured_prompt,
                            "expects_structured_output": True,
                            "output_format": "json",
                            "schema_type": schema_class.__name__,
                        },
                    )
                )

                # Parse AI response using integrated parser
                parsing_result = await self.parse_ai_response(
                    template_name="ocr/whole_document_extraction",
                    ai_response=ai_response.get("content", ""),
                    output_parser=ocr_parser,
                    use_retry=True,
                )

                # Handle parsing results
                if parsing_result.success:
                    logger.info(
                        f"Successfully extracted structured OCR data from {filename}"
                    )

                    return {
                        "ocr_extraction": parsing_result.parsed_data.dict(),
                        "service": "GeminiOCRService",
                        "service_version": "v4_structured_ocr",
                        "parsing_success": True,
                        "parsing_confidence": parsing_result.confidence_score,
                        "file_processed": filename,
                        "extraction_mode": (
                            "quick" if use_quick_mode else "comprehensive"
                        ),
                        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "entire_document_processed": True,
                            "validation_errors": parsing_result.validation_errors,
                            "parsing_errors": parsing_result.parsing_errors,
                        },
                    }
                else:
                    logger.warning(
                        f"Failed to parse structured OCR output for {filename}: {parsing_result.parsing_errors}"
                    )

                    # Fallback: try to extract basic text
                    fallback_result = await self._handle_ocr_parsing_failure(
                        ai_response, parsing_result, filename
                    )

                    return fallback_result

            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded during OCR extraction: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="OCR extraction quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during OCR extraction: {e}")
                raise HTTPException(
                    status_code=500, detail=f"OCR extraction failed: {str(e)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during structured OCR extraction: {str(e)}")
            return {
                "ocr_extraction": None,
                "service": "GeminiOCRService",
                "service_version": "v4_structured_ocr_error",
                "parsing_success": False,
                "file_processed": filename,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _handle_ocr_parsing_failure(
        self,
        ai_response: Dict[str, Any],
        parsing_result: "ParsingResult",
        filename: str,
    ) -> Dict[str, Any]:
        """Handle OCR parsing failures with graceful fallback"""
        logger.warning(f"Implementing OCR parsing fallback for {filename}")

        # Try to extract basic text structure
        if parsing_result.raw_output and isinstance(parsing_result.raw_output, str):
            try:
                # Attempt to create basic OCR structure
                basic_ocr_data = self._create_basic_ocr_structure(
                    parsing_result.raw_output, filename
                )
                if basic_ocr_data:
                    logger.info(f"Recovered basic OCR data for {filename}")
                    return {
                        "ocr_extraction": basic_ocr_data,
                        "service": "GeminiOCRService",
                        "service_version": "v4_ocr_fallback_recovery",
                        "parsing_success": False,
                        "parsing_recovery": True,
                        "file_processed": filename,
                        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "parsing_errors": parsing_result.parsing_errors,
                            "validation_errors": parsing_result.validation_errors,
                            "recovery_method": "basic_structure_extraction",
                        },
                    }
            except Exception as e:
                logger.warning(f"Basic OCR structure extraction failed: {e}")

        # Return raw response as last resort
        return {
            "ocr_extraction": {
                "full_text": ai_response.get("content", ""),
                "extraction_note": "Raw AI response due to parsing failure",
            },
            "service": "GeminiOCRService",
            "service_version": "v4_ocr_raw_fallback",
            "parsing_success": False,
            "parsing_recovery": False,
            "file_processed": filename,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_metadata": {
                "parsing_errors": parsing_result.parsing_errors,
                "validation_errors": parsing_result.validation_errors,
                "fallback_reason": "Unable to parse or recover structured OCR data",
            },
        }

    def _create_basic_ocr_structure(
        self, raw_text: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """Create basic OCR structure from raw text when parsing fails"""
        try:
            import re

            # Count apparent pages (look for page breaks, headers, footers)
            page_indicators = re.findall(r"page\s+(\d+)", raw_text.lower())
            estimated_pages = (
                max([int(p) for p in page_indicators]) if page_indicators else 1
            )

            # Extract potential financial amounts
            money_pattern = r"\$[\d,]+(?:\.\d{2})?"
            financial_amounts = re.findall(money_pattern, raw_text)

            # Extract potential dates
            date_patterns = [
                r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
                r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}",
            ]
            dates = []
            for pattern in date_patterns:
                dates.extend(re.findall(pattern, raw_text, re.IGNORECASE))

            # Create basic structure
            basic_structure = {
                "full_text": raw_text,
                "estimated_page_count": estimated_pages,
                "financial_amounts_found": list(set(financial_amounts)),
                "dates_found": list(set(dates)),
                "text_length": len(raw_text),
                "word_count": len(raw_text.split()),
                "extraction_method": "basic_fallback",
                "confidence": 0.5,  # Low confidence for fallback
            }

            return basic_structure

        except Exception as e:
            logger.error(f"Failed to create basic OCR structure: {e}")
            return None

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
        if not self.gemini_service:
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
                file_type=file_type,
            )

            # Render prompt with automatic format instructions
            analysis_prompt = await self.render_with_parser(
                template_name="image_semantics",
                context=context,
                output_parser=semantic_parser,
                validate=True,
                use_cache=True,
            )

            logger.debug(f"Generated structured prompt for {filename}")

            # Get AI response using Gemini service
            try:
                ai_response = (
                    await self.gemini_service.gemini_client.analyze_image_semantics(
                        content=file_content,
                        content_type=(
                            f"image/{file_type.lower()}"
                            if file_type.lower() != "pdf"
                            else "application/pdf"
                        ),
                        analysis_context={
                            "prompt": analysis_prompt,
                            "expects_structured_output": True,
                            "output_format": "json",
                        },
                    )
                )

                # Parse AI response using integrated parser
                parsing_result = await self.parse_ai_response(
                    template_name="image_semantics",
                    ai_response=ai_response.get("content", ""),
                    output_parser=semantic_parser,
                    use_retry=True,
                )

                # Handle parsing results
                if parsing_result.success:
                    logger.info(f"Successfully parsed semantic analysis for {filename}")

                    return {
                        "semantic_analysis": parsing_result.parsed_data.dict(),
                        "service": "GeminiOCRService",
                        "service_version": "v4_parser_integrated",
                        "parsing_success": True,
                        "parsing_confidence": parsing_result.confidence_score,
                        "file_processed": filename,
                        "image_type_detected": (
                            image_type.value if image_type else "unknown"
                        ),
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "prompt_with_format_instructions": True,
                            "validation_errors": parsing_result.validation_errors,
                            "parsing_errors": parsing_result.parsing_errors,
                        },
                    }
                else:
                    logger.warning(
                        f"Failed to parse structured output for {filename}: {parsing_result.parsing_errors}"
                    )

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
            logger.error(
                f"Unexpected error during structured semantic analysis: {str(e)}"
            )
            return {
                "semantic_analysis": None,
                "service": "GeminiOCRService",
                "service_version": "v4_parser_error",
                "parsing_success": False,
                "file_processed": filename,
                "error": str(e),
                "error_type": type(e).__name__,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @langsmith_trace(name="gemini_text_diagram_insight", run_type="llm")
    async def extract_text_diagram_insight(
        self,
        *,
        file_content: bytes,
        file_type: str,
        filename: str,
        analysis_focus: str = "diagram_detection",
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lightweight helper to get OCR text and diagram type (if applicable) via a single LLM call.

        Returns a dict with keys:
        - text: str
        - confidence: float
        - diagram_hint: { is_diagram: bool, diagram_type: str | None }
        """
        if not self.gemini_service:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate input quickly
            self._validate_file(file_content, file_type)

            # Use centralized schema for structured output
            from app.prompts.schema.text_diagram_insight_schema import (
                TextDiagramInsight,
            )

            parser = create_parser(TextDiagramInsight)

            # Render prompt using PromptManager with format instructions
            rendered_prompt = await self.render_with_parser(
                template_name="ocr/text_diagram_insight",
                context={
                    "filename": filename,
                    "file_type": file_type,
                    "analysis_focus": analysis_focus,
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                    "document_type": document_type,
                },
                output_parser=parser,
                validate=True,
                use_cache=True,
            )

            # Build multimodal content (prompt + image)
            mime_type = (
                "application/pdf"
                if file_type.lower() == "pdf"
                else f"image/{file_type.lower()}"
            )
            content = Content(
                role="user",
                parts=[
                    Part.from_text(text=rendered_prompt),
                    Part.from_bytes(data=file_content, mime_type=mime_type),
                ],
            )

            # Execute model call (single LLM call)
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_service.gemini_client.client.models.generate_content(
                    model=self.gemini_service.gemini_client.config.model_name,
                    contents=[content],
                    config=GenerateContentConfig(),
                ),
            )

            ai_text = (
                response.candidates[0].content.parts[0].text
                if response
                and response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
                else ""
            )

            # Parse structured output
            parsing_result = await self.parse_ai_response(
                template_name="ocr/text_diagram_insight",
                ai_response=ai_text,
                output_parser=parser,
                use_retry=True,
            )

            if parsing_result.success and parsing_result.parsed_data:
                model: TextDiagramInsight = parsing_result.parsed_data
                return {
                    "text": (model.text or "").strip(),
                    "confidence": float(model.confidence or 0.0),
                    "diagram_hint": {
                        "is_diagram": bool(model.is_diagram),
                        "diagram_type": model.diagram_type,
                    },
                }

            # Fallback on parse failure
            raw = parsing_result.raw_output or ""
            return {
                "text": raw if isinstance(raw, str) else "",
                "confidence": 0.0,
                "diagram_hint": {"is_diagram": False, "diagram_type": None},
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"extract_text_diagram_insight failed for {filename}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "diagram_hint": {"is_diagram": False, "diagram_type": None},
            }

    async def _handle_parsing_failure(
        self, ai_response: Dict[str, Any], parsing_result: ParsingResult, filename: str
    ) -> Dict[str, Any]:
        """
        Handle parsing failures with graceful fallback strategies
        """
        logger.warning(f"Implementing fallback for parsing failure on {filename}")

        # Strategy 1: Try to extract partial structured data
        if parsing_result.raw_output and isinstance(parsing_result.raw_output, str):
            try:
                # Attempt manual structure extraction
                fallback_data = self._attempt_manual_structure_extraction(
                    parsing_result.raw_output
                )
                if fallback_data:
                    logger.info(f"Recovered partial structured data for {filename}")
                    return {
                        "semantic_analysis": fallback_data,
                        "service": "GeminiOCRService",
                        "service_version": "v4_fallback_recovery",
                        "parsing_success": False,
                        "parsing_recovery": True,
                        "file_processed": filename,
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "parsing_errors": parsing_result.parsing_errors,
                            "validation_errors": parsing_result.validation_errors,
                            "recovery_method": "manual_extraction",
                        },
                    }
            except Exception as e:
                logger.warning(f"Manual structure extraction failed: {e}")

        # Strategy 2: Return raw response with error metadata
        return {
            "semantic_analysis": ai_response,
            "service": "GeminiOCRService",
            "service_version": "v4_raw_fallback",
            "parsing_success": False,
            "parsing_recovery": False,
            "file_processed": filename,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_metadata": {
                "parsing_errors": parsing_result.parsing_errors,
                "validation_errors": parsing_result.validation_errors,
                "fallback_reason": "Unable to parse or recover structured data",
            },
        }

    def _attempt_manual_structure_extraction(
        self, raw_output: str
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to manually extract structure from raw AI output
        This is a fallback strategy when automatic parsing fails
        """
        import json
        import re

        try:
            # Try to find JSON-like structures in the text
            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            matches = re.findall(json_pattern, raw_output, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    # Basic validation: check if it has expected fields
                    if isinstance(data, dict) and any(
                        key in data
                        for key in [
                            "image_type",
                            "infrastructure_elements",
                            "environmental_factors",
                        ]
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
                    "risk_factors": [],
                },
                "extracted_text": raw_output[:1000],  # First 1000 chars as fallback
                "analysis_quality": "low_confidence_fallback",
            }

            return basic_structure

        except Exception as e:
            logger.error(f"Manual structure extraction failed: {e}")
            return None

    async def _detect_image_type(
        self, filename: str, contract_context: Optional[Dict[str, Any]]
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

    def _calculate_confidence_score(self, extracted_text: str) -> float:
        """Calculate confidence score based on text quality indicators"""
        if not extracted_text or len(extracted_text.strip()) == 0:
            return 0.0

        # Initialize confidence
        confidence = 1.0

        # Text length factor (very short text gets lower confidence)
        if len(extracted_text) < 50:
            confidence *= 0.7
        elif len(extracted_text) < 10:
            confidence *= 0.4

        # Count quality indicators
        total_chars = len(extracted_text)
        if total_chars == 0:
            return 0.0

        # Count problematic patterns
        import re

        # Numbers where letters should be (like "1" instead of "I")
        substitution_errors = len(
            re.findall(r"\b\d[a-zA-Z]+|\b[a-zA-Z]*\d[a-zA-Z]*\b", extracted_text)
        )

        # Excessive special characters
        special_char_ratio = (
            len(re.findall(r"[^\w\s.,!?:;()-]", extracted_text)) / total_chars
        )

        # Very short "words" (likely OCR artifacts)
        short_words = len(
            [
                word
                for word in extracted_text.split()
                if len(word) == 1 and word.isalpha()
            ]
        )

        # Apply penalties
        if substitution_errors > total_chars * 0.1:  # More than 10% substitution errors
            confidence *= 0.6
        if special_char_ratio > 0.15:  # More than 15% special characters
            confidence *= 0.7
        if (
            short_words > len(extracted_text.split()) * 0.3
        ):  # More than 30% single-char words
            confidence *= 0.8

        # Bonus for good indicators
        sentences = len(re.findall(r"[.!?]+", extracted_text))
        words = len(extracted_text.split())
        if sentences > 0 and words > 0:
            avg_words_per_sentence = words / sentences
            if 5 <= avg_words_per_sentence <= 25:  # Reasonable sentence length
                confidence *= 1.1

        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))

    def _extract_text_metrics(self, text: str) -> Dict[str, Any]:
        """Extract metrics from text content"""
        if not text:
            return {
                "character_count": 0,
                "word_count": 0,
                "line_count": 0,
                "average_word_length": 0.0,
            }

        # Basic counts
        character_count = len(text)
        words = text.split()
        word_count = len(words)
        lines = text.splitlines()
        line_count = len(lines)

        # Calculate average word length
        if word_count > 0:
            total_word_length = sum(len(word.strip(".,!?:;()")) for word in words)
            average_word_length = total_word_length / word_count
        else:
            average_word_length = 0.0

        return {
            "character_count": character_count,
            "word_count": word_count,
            "line_count": line_count,
            "average_word_length": round(average_word_length, 2),
        }


# Usage example and migration guide
async def example_usage():
    """Example showing how to use the new parser-integrated service"""

    # Initialize service
    service = GeminiOCRService()
    await service.initialize()

    # Example file content (would be real image bytes in practice)
    file_content = b"example_image_bytes"

    # Use new structured analysis
    result = await service.extract_image_semantics_structured(
        file_content=file_content,
        file_type="png",
        filename="sewer_service_plan.png",
        image_type=ImageType.SEWER_SERVICE_DIAGRAM,
        analysis_focus="infrastructure",
    )

    # Check if parsing was successful
    if result.get("parsing_success"):
        semantic_data = result["semantic_analysis"]
        print(f"Successfully parsed structured data: {semantic_data}")

        # Access structured fields (now guaranteed to exist and be typed)
        infrastructure = semantic_data.get("infrastructure_elements", [])
        risk_level = semantic_data.get("risk_assessment", {}).get("overall_risk_level")

    else:
        print(
            f"Parsing failed, using fallback: {result.get('processing_metadata', {})}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
