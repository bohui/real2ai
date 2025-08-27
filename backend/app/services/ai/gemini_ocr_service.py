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
from app.core.langsmith_config import langsmith_trace, get_langsmith_config
from langsmith.run_helpers import trace
from app.core.prompts.parsers import create_parser, ParsingResult
from app.services.base.user_aware_service import UserAwareService
from backend.app.prompts.schema.diagram_analysis.image_semantics_schema import DiagramSemanticsBase, DiagramType
from app.services.ai.gemini_service import GeminiService
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)
from google.genai.types import Content, Part, GenerateContentConfig, SafetySetting
import asyncio

from app.prompts.schema.text_diagram_insight_schema import TextDiagramInsightList

logger = logging.getLogger(__name__)


# Module-level constants to avoid magic numbers
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
SUPPORTED_FORMATS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
    "bmp",
    "tiff",
}

DEFAULT_PAGE_NUMBER = 1

# Generation config defaults
GENERATION_TEMPERATURE = 0.2
GENERATION_TOP_P = 1
GENERATION_SEED = 0
GENERATION_MAX_OUTPUT_TOKENS = 65535

# Truncation behavior disabled per requirements
PROMPT_INPUT_TRUNCATE_LENGTH = None
RESPONSE_PREVIEW_TRUNCATE_LENGTH = None
RAW_TEXT_FALLBACK_TRUNCATE_LENGTH = None

# Other defaults
ESTIMATED_PAGES_DEFAULT = 1

# HTTP status codes
HTTP_503_SERVICE_UNAVAILABLE = 503
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_400_BAD_REQUEST = 400

# Confidence scoring parameters
CONFIDENCE_INITIAL = 1.0
SHORT_TEXT_LENGTH_THRESHOLD = 50
VERY_SHORT_TEXT_LENGTH_THRESHOLD = 10
SHORT_TEXT_PENALTY = 0.7
VERY_SHORT_TEXT_PENALTY = 0.4
SUBSTITUTION_ERROR_THRESHOLD_RATIO = 0.1
SUBSTITUTION_ERROR_PENALTY = 0.6
SPECIAL_CHAR_RATIO_THRESHOLD = 0.15
SPECIAL_CHAR_PENALTY = 0.7
SHORT_WORDS_RATIO_THRESHOLD = 0.3
SHORT_WORDS_PENALTY = 0.8
SENTENCE_LENGTH_GOOD_MIN = 5
SENTENCE_LENGTH_GOOD_MAX = 25
GOOD_SENTENCE_BONUS_MULTIPLIER = 1.1

# Fallback defaults
FALLBACK_CONFIDENCE = 0.5


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
        self.max_file_size = MAX_FILE_SIZE_BYTES
        self.supported_formats = SUPPORTED_FORMATS

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
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini OCR service unavailable - connection failed",
            )

    async def generate_ocr_prompt(
        self,
        document_type: Optional[str] = None,
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        page_number: int = DEFAULT_PAGE_NUMBER,
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
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini OCR service not initialized",
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

            # Use composition for OCR with structured output
            composition_result = await self.render_composed(
                composition_name="ocr_whole_document_extraction",
                context=context,
                output_parser=ocr_parser,
            )
            structured_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")

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

                # Use the unified LLMService for structured output
                from app.services import get_llm_service

                llm_service = await get_llm_service()
                parsing_result = await llm_service.generate_image_semantics(
                    content=file_content,
                    content_type=content_type,
                    filename=filename,
                    composition_name="image_semantics_only",
                    context_variables={
                        "ocr_mode": "whole_document",
                        "schema_type": schema_class.__name__,
                        **(context.variables if hasattr(context, "variables") else {}),
                    },
                    output_parser=ocr_parser,
                )

                # Handle parsing results
                if getattr(parsing_result, "success", False):
                    logger.info(
                        f"Successfully extracted structured OCR data from {filename}"
                    )

                    parsed = getattr(parsing_result, "parsed_data", None)
                    payload = parsed.dict() if hasattr(parsed, "dict") else parsed
                    return {
                        "ocr_extraction": payload,
                        "service": "GeminiOCRService",
                        "service_version": "v4_structured_ocr",
                        "parsing_success": True,
                        "parsing_confidence": getattr(
                            parsing_result, "confidence_score", 0.0
                        ),
                        "file_processed": filename,
                        "extraction_mode": (
                            "quick" if use_quick_mode else "comprehensive"
                        ),
                        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "entire_document_processed": True,
                            "validation_errors": getattr(
                                parsing_result, "validation_errors", []
                            ),
                            "parsing_errors": getattr(
                                parsing_result, "parsing_errors", []
                            ),
                        },
                    }
                else:
                    logger.warning(
                        f"Failed to parse structured OCR output for {filename}: {getattr(parsing_result, 'parsing_errors', [])}"
                    )

                    # Fallback: try to extract basic text
                    fallback_result = await self._handle_ocr_parsing_failure(
                        {"content": ""}, parsing_result, filename
                    )

                    return fallback_result

            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded during OCR extraction: {e}")
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail="OCR extraction quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during OCR extraction: {e}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OCR extraction failed: {str(e)}",
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
                max([int(p) for p in page_indicators])
                if page_indicators
                else ESTIMATED_PAGES_DEFAULT
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
                "confidence": FALLBACK_CONFIDENCE,  # Low confidence for fallback
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
        image_type: Optional[DiagramType] = None,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_focus: Optional[str] = None,
        risk_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract semantic meaning with structured output parsing

        This method demonstrates the new parser integration:
        1. Creates Pydantic parser for DiagramSemanticsBase
        2. Renders prompt with auto-generated format instructions
        3. Parses AI response with validation and error handling
        4. Returns structured, validated results
        """
        if not self.gemini_service:
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini OCR service not initialized",
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Auto-detect image type if needed
            if image_type is None:
                image_type = await self._detect_image_type(filename, contract_context)

            # Create Pydantic output parser
            semantic_parser = create_parser(DiagramSemanticsBase)

            # Prepare context for semantic analysis
            context = self.create_context(
                image_type=image_type.value if image_type else "unknown",
                contract_context=contract_context or {},
                analysis_focus=analysis_focus or "comprehensive",
                risk_categories=risk_categories or [],
                filename=filename,
                file_type=file_type,
            )

            # Use unified LLMService image semantics
            from app.services import get_llm_service

            llm_service = await get_llm_service()
            try:
                parsing_result = await llm_service.generate_image_semantics(
                    content=file_content,
                    content_type=(
                        f"image/{file_type.lower()}"
                        if file_type.lower() != "pdf"
                        else "application/pdf"
                    ),
                    filename=filename,
                    composition_name="image_semantics_only",
                    context_variables=(
                        context.variables if hasattr(context, "variables") else {}
                    ),
                    output_parser=semantic_parser,
                )

                # Handle parsing results
                if getattr(parsing_result, "success", False):
                    logger.info(f"Successfully parsed semantic analysis for {filename}")

                    parsed = getattr(parsing_result, "parsed_data", None)
                    payload = parsed.dict() if hasattr(parsed, "dict") else parsed
                    return {
                        "semantic_analysis": payload,
                        "service": "GeminiOCRService",
                        "service_version": "v4_parser_integrated",
                        "parsing_success": True,
                        "parsing_confidence": getattr(
                            parsing_result, "confidence_score", 0.0
                        ),
                        "file_processed": filename,
                        "image_type_detected": (
                            image_type.value if image_type else "unknown"
                        ),
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "prompt_with_format_instructions": True,
                            "validation_errors": getattr(
                                parsing_result, "validation_errors", []
                            ),
                            "parsing_errors": getattr(
                                parsing_result, "parsing_errors", []
                            ),
                        },
                    }
                else:
                    logger.warning(
                        f"Failed to parse structured output for {filename}: {getattr(parsing_result, 'parsing_errors', [])}"
                    )
                    # Fallback path is not directly available via LLMService route; return minimal info
                    return {
                        "semantic_analysis": None,
                        "service": "GeminiOCRService",
                        "service_version": "v4_parser_integrated",
                        "parsing_success": False,
                        "file_processed": filename,
                        "image_type_detected": (
                            image_type.value if image_type else "unknown"
                        ),
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                        "processing_metadata": {
                            "prompt_with_format_instructions": True,
                            "validation_errors": getattr(
                                parsing_result, "validation_errors", []
                            ),
                            "parsing_errors": getattr(
                                parsing_result, "parsing_errors", []
                            ),
                        },
                    }

            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded during semantic analysis: {e}")
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail="Semantic analysis quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during semantic analysis: {e}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Semantic analysis failed: {str(e)}",
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
    ) -> TextDiagramInsightList:
        """Lightweight helper to get OCR text and diagram types via a single LLM call."""
        if not self.gemini_service:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate input quickly
            self._validate_file(file_content, file_type)

            # Use centralized schema for structured output
            from app.prompts.schema.text_diagram_insight_schema import (
                TextDiagramInsightList,
            )

            parser = create_parser(TextDiagramInsightList)

            # Ensure latest templates (frontmatter/required vars) are loaded
            try:
                await self.prompt_manager.reload_templates()
            except Exception:
                pass

            # Use composition for text + diagram insight analysis
            composition_result = await self.render_composed(
                composition_name="ocr_text_diagram_insight",
                context={
                    "filename": filename,
                    "file_type": file_type,
                    "analysis_focus": analysis_focus,
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                    "document_type": document_type,
                },
                output_parser=parser,
            )
            rendered_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")

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
            generate_config = GenerateContentConfig(
                temperature=GENERATION_TEMPERATURE,
                top_p=GENERATION_TOP_P,
                seed=GENERATION_SEED,
                max_output_tokens=GENERATION_MAX_OUTPUT_TOKENS,
                safety_settings=[
                    SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                    ),
                    SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                    ),
                    SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                    ),
                    SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
                ],
                response_mime_type="application/json",
                response_schema=TextDiagramInsightList,
                system_instruction=system_prompt if system_prompt else None,
            )

            # Execute model call (single LLM call) with detailed LangSmith nested trace
            config = get_langsmith_config()
            model_name = self.gemini_service.gemini_client.config.model_name
            if config.enabled:
                with trace(
                    name="gemini_generate_content",
                    run_type="llm",
                    project_name=config.project_name,
                    metadata={
                        "function": "extract_text_diagram_insight",
                        "module": __name__,
                        "client_name": "GeminiClient",
                    },
                ) as llm_run:
                    # Record critical inputs
                    llm_run.inputs = {
                        "model": model_name,
                        "prompt": rendered_prompt,
                        "mime_type": mime_type,
                        "generation_config": {
                            "temperature": generate_config.temperature,
                            "top_p": generate_config.top_p,
                            "max_output_tokens": generate_config.max_output_tokens,
                            "seed": generate_config.seed,
                            "response_mime_type": generate_config.response_mime_type,
                            "response_schema": (
                                getattr(
                                    generate_config, "response_schema", None
                                ).__name__
                                if getattr(generate_config, "response_schema", None)
                                else None
                            ),
                        },
                    }

                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.gemini_service.gemini_client.client.models.generate_content(
                            model=model_name,
                            contents=[content],
                            config=generate_config,
                        ),
                    )

                    # Extract usage metadata if present
                    usage = getattr(response, "usage_metadata", None) or getattr(
                        response, "usageMetadata", None
                    )
                    usage_dict = None
                    if usage is not None:
                        # Try attribute or dict access patterns
                        prompt_tokens = (
                            getattr(usage, "prompt_token_count", None)
                            or usage.get("prompt_token_count", None)
                            if hasattr(usage, "get")
                            else getattr(usage, "prompt_token_count", None)
                        )
                        candidates_tokens = getattr(
                            usage, "candidates_token_count", None
                        ) or (
                            usage.get("candidates_token_count", None)
                            if hasattr(usage, "get")
                            else None
                        )
                        total_tokens = getattr(usage, "total_token_count", None) or (
                            usage.get("total_token_count", None)
                            if hasattr(usage, "get")
                            else None
                        )
                        usage_dict = {
                            "prompt_token_count": prompt_tokens,
                            "candidates_token_count": candidates_tokens,
                            "total_token_count": total_tokens,
                        }
                    # We'll fill outputs after parsing text below using ai_text
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.gemini_service.gemini_client.client.models.generate_content(
                        model=model_name,
                        contents=[content],
                        config=generate_config,
                    ),
                )

            # Safely extract text from response; avoid direct indexing
            def _safe_extract_text(resp: Any) -> str:
                try:
                    text_attr = getattr(resp, "text", None)
                    if isinstance(text_attr, str) and text_attr.strip():
                        return text_attr
                    candidates = getattr(resp, "candidates", None) or []
                    for cand in candidates:
                        content_obj = getattr(cand, "content", None)
                        if not content_obj:
                            continue
                        parts = getattr(content_obj, "parts", None) or []
                        texts: list[str] = []
                        for p in parts:
                            t = getattr(p, "text", None)
                            if isinstance(t, str) and t:
                                texts.append(t)
                        if texts:
                            return "\n".join(texts)
                    return ""
                except Exception:
                    return ""

            ai_text = _safe_extract_text(response)

            # Parse structured output
            parsing_result = await self.parse_ai_response(
                template_name="user/ocr/text_diagram_insight",
                ai_response=ai_text,
                output_parser=parser,
                use_retry=True,
            )

            # If we opened a nested run, record outputs now
            if "llm_run" in locals():
                try:
                    llm_run.outputs = {
                        "response_length": len(ai_text or ""),
                        "response_preview": ai_text or "",
                        **(
                            {"usage": usage_dict}
                            if "usage_dict" in locals() and usage_dict
                            else {}
                        ),
                    }
                except Exception:
                    # Avoid disrupting main flow if tracing output fails
                    pass

            if parsing_result.success and parsing_result.parsed_data:
                model: TextDiagramInsightList = parsing_result.parsed_data
                # Ensure defaults
                model.text = (model.text or "").strip()
                model.text_confidence = float(model.text_confidence or 0.0)
                model.diagrams = list(model.diagrams or [])
                model.diagrams_confidence = float(model.diagrams_confidence or 0.0)
                return model

            # Fallback on parse failure
            raw = parsing_result.raw_output or ""
            return TextDiagramInsightList(
                text=raw if isinstance(raw, str) else "",
                text_confidence=0.0,
                diagrams=[],
                diagrams_confidence=0.0,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"extract_text_diagram_insight failed for {filename}: {e}")
            return TextDiagramInsightList(
                text="",
                text_confidence=0.0,
                diagrams=[],
                diagrams_confidence=0.0,
            )

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
                "extracted_text": raw_output,
                "analysis_quality": "low_confidence_fallback",
            }

            return basic_structure

        except Exception as e:
            logger.error(f"Manual structure extraction failed: {e}")
            return None

    async def _detect_image_type(
        self, filename: str, contract_context: Optional[Dict[str, Any]]
    ) -> DiagramType:
        """Detect image type based on filename and context"""
        filename_lower = filename.lower()

        # Simple detection based on common patterns
        if "sewer" in filename_lower or "service" in filename_lower:
            return DiagramType.SEWER_SERVICE_DIAGRAM
        elif "title" in filename_lower or "plan" in filename_lower:
            return DiagramType.TITLE_PLAN
        elif "survey" in filename_lower:
            return DiagramType.SURVEY_DIAGRAM
        elif "flood" in filename_lower:
            return DiagramType.FLOOD_MAP
        elif "bushfire" in filename_lower or "fire" in filename_lower:
            return DiagramType.BUSHFIRE_MAP
        else:
            return DiagramType.SITE_PLAN  # Default fallback

    def _validate_file(self, file_content: bytes, file_type: str):
        """Validate file size and format"""
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {self.max_file_size / 1024 / 1024}MB",
            )

        if file_type.lower() not in self.supported_formats:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_type}",
            )

        if len(file_content) == 0:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Empty file cannot be processed",
            )

    def _calculate_confidence_score(self, extracted_text: str) -> float:
        """Calculate confidence score based on text quality indicators"""
        if not extracted_text or len(extracted_text.strip()) == 0:
            return 0.0

        # Initialize confidence
        confidence = CONFIDENCE_INITIAL

        # Text length factor (very short text gets lower confidence)
        if len(extracted_text) < SHORT_TEXT_LENGTH_THRESHOLD:
            confidence *= SHORT_TEXT_PENALTY
        elif len(extracted_text) < VERY_SHORT_TEXT_LENGTH_THRESHOLD:
            confidence *= VERY_SHORT_TEXT_PENALTY

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
        if substitution_errors > total_chars * SUBSTITUTION_ERROR_THRESHOLD_RATIO:
            confidence *= SUBSTITUTION_ERROR_PENALTY
        if special_char_ratio > SPECIAL_CHAR_RATIO_THRESHOLD:
            confidence *= SPECIAL_CHAR_PENALTY
        if short_words > len(extracted_text.split()) * SHORT_WORDS_RATIO_THRESHOLD:
            confidence *= SHORT_WORDS_PENALTY

        # Bonus for good indicators
        sentences = len(re.findall(r"[.!?]+", extracted_text))
        words = len(extracted_text.split())
        if sentences > 0 and words > 0:
            avg_words_per_sentence = words / sentences
            if (
                SENTENCE_LENGTH_GOOD_MIN
                <= avg_words_per_sentence
                <= SENTENCE_LENGTH_GOOD_MAX
            ):
                confidence *= GOOD_SENTENCE_BONUS_MULTIPLIER

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
        image_type=DiagramType.SEWER_SERVICE_DIAGRAM,
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
