"""
Gemini Service - Business Logic Layer for AI Operations

This service handles all AI operations using the Gemini client,
separating business logic from connection management.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from app.services.base.user_aware_service import UserAwareService
from app.clients import get_gemini_client
from app.clients.gemini.client import GeminiClient
from app.core.langsmith_config import langsmith_trace, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)

# Constants (no truncation of inputs)
CONTENT_PREVIEW_LENGTH = None
PROMPT_PREVIEW_LENGTH = None

# Default generation constants (avoid magic numbers)
DEFAULT_TEMPERATURE: float = 0.1
DEFAULT_TOP_P: float = 1.0
DEFAULT_MAX_OUTPUT_TOKENS: int = 65535
CLASSIFICATION_TEMPERATURE: float = 0.1
SUMMARY_TEMPERATURE: float = 0.3
SENTIMENT_TEMPERATURE: float = 0.1
LANGUAGE_DETECTION_TEMPERATURE: float = 0.0


class GeminiService(UserAwareService):
    """
    Service layer for Gemini AI operations.

    This service provides high-level AI operations using the Gemini client,
    handling business logic, error handling, and response processing.
    """

    def __init__(self, user_client=None):
        """Initialize Gemini service."""
        super().__init__(user_client=user_client)
        self._gemini_client: Optional[GeminiClient] = None

    async def initialize(self) -> None:
        """Initialize the Gemini service and underlying client."""
        try:
            # Get the Gemini client (connection layer)
            self._gemini_client = await get_gemini_client()

            if not self._gemini_client:
                raise ClientError("Failed to initialize Gemini client", "GeminiService")

            logger.info("Gemini service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            raise

    @property
    def gemini_client(self) -> GeminiClient:
        """Get the underlying Gemini client."""
        if not self._gemini_client:
            raise ClientError("Gemini client not initialized", "GeminiService")
        return self._gemini_client

    @langsmith_trace(name="gemini_generate_content", run_type="llm")
    async def generate_content(
        self,
        prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        max_tokens: Optional[int] = DEFAULT_MAX_OUTPUT_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate content based on a prompt.

        Args:
            prompt: The input prompt
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum output tokens
            **kwargs: Additional generation parameters

        Returns:
            Generated text content

        Raises:
            ClientError: If generation fails
            ClientQuotaExceededError: If quota is exceeded
        """
        try:
            log_trace_info(
                "gemini_generate_content",
                prompt_length=len(prompt),
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )

            logger.debug("Generating content for prompt (no truncation preview logged)")

            # Delegate to client for the actual API call
            response = await self.gemini_client.generate_content(
                prompt=prompt,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                **kwargs,
            )

            logger.debug(f"Successfully generated {len(response)} characters")
            return response

        except ClientQuotaExceededError:
            logger.error("Gemini quota exceeded during content generation")
            raise
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise ClientError(
                f"Content generation failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    @langsmith_trace(name="gemini_analyze_document", run_type="tool")
    async def analyze_document(
        self,
        content: bytes,
        content_type: str,
        extract_text: bool = True,
        extract_entities: bool = False,
        extract_structure: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analyze a document and extract information.

        Args:
            content: Document content as bytes
            content_type: MIME type of the document
            extract_text: Whether to extract text
            extract_entities: Whether to extract entities
            extract_structure: Whether to extract document structure
            **kwargs: Additional analysis parameters

        Returns:
            Analysis results with requested information
        """
        try:
            log_trace_info(
                "gemini_analyze_document",
                content_type=content_type,
                content_size=len(content),
                extract_text=extract_text,
                extract_entities=extract_entities,
                extract_structure=extract_structure,
            )

            logger.debug(f"Analyzing document of type: {content_type}")

            # Delegate to client's OCR capabilities
            result = await self.gemini_client.analyze_document(
                content=content, content_type=content_type, **kwargs
            )

            # Process and enhance the results based on requirements
            if extract_entities and "text" in result:
                result["entities"] = await self._extract_entities(result["text"])

            if extract_structure and "text" in result:
                result["structure"] = await self._analyze_structure(result["text"])

            logger.debug("Document analysis completed successfully")
            return result

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    @langsmith_trace(name="gemini_extract_text", run_type="tool")
    async def extract_text(
        self,
        content: bytes,
        content_type: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Extract text from a document using OCR.

        Args:
            content: Document content as bytes
            content_type: MIME type of the document
            language: Optional language hint for OCR
            **kwargs: Additional extraction parameters

        Returns:
            Extracted text and metadata
        """
        try:
            log_trace_info(
                "gemini_extract_text",
                content_type=content_type,
                content_size=len(content),
                language=language,
            )

            logger.debug(f"Extracting text from document of type: {content_type}")

            # Delegate to client
            result = await self.gemini_client.extract_text(
                content=content, content_type=content_type, **kwargs
            )

            # Add language detection if not specified
            if not language and "text" in result:
                result["detected_language"] = await self._detect_language(
                    result["text"]
                )

            logger.debug("Text extraction completed successfully")
            return result

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    @langsmith_trace(name="gemini_classify_content", run_type="llm")
    async def classify_content(
        self,
        content: str,
        categories: List[str],
        multi_label: bool = False,
        confidence_threshold: float = 0.7,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Classify content into predefined categories.

        Args:
            content: Content to classify
            categories: List of possible categories
            multi_label: Whether multiple categories can apply
            confidence_threshold: Minimum confidence for classification
            **kwargs: Additional classification parameters

        Returns:
            Classification results with confidence scores
        """
        try:
            log_trace_info(
                "gemini_classify_content",
                content_length=len(content),
                categories_count=len(categories),
                multi_label=multi_label,
            )

            logger.debug(f"Classifying content into {len(categories)} categories")

            # Create optimized classification prompt
            prompt = self._create_classification_prompt(
                content=content, categories=categories, multi_label=multi_label
            )

            # Get classification from model
            response = await self.generate_content(
                prompt, temperature=CLASSIFICATION_TEMPERATURE
            )

            # Parse and validate classification
            result = self._parse_classification_response(
                response=response,
                categories=categories,
                multi_label=multi_label,
                confidence_threshold=confidence_threshold,
            )

            logger.debug(f"Content classified: {result}")
            return result

        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            raise ClientError(
                f"Content classification failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    @langsmith_trace(name="gemini_summarize", run_type="llm")
    async def summarize_content(
        self,
        content: str,
        max_length: Optional[int] = None,
        style: str = "concise",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Summarize content with specified parameters.

        Args:
            content: Content to summarize
            max_length: Maximum summary length in words
            style: Summary style (concise, detailed, bullet_points)
            **kwargs: Additional parameters

        Returns:
            Summary and metadata
        """
        try:
            log_trace_info(
                "gemini_summarize",
                content_length=len(content),
                max_length=max_length,
                style=style,
            )

            prompt = self._create_summary_prompt(content, max_length, style)
            summary = await self.generate_content(
                prompt, temperature=SUMMARY_TEMPERATURE
            )

            return {
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(content) if content else 0,
                "style": style,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise ClientError(
                f"Summarization failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    @langsmith_trace(name="gemini_analyze_sentiment", run_type="llm")
    async def analyze_sentiment(
        self, content: str, granularity: str = "overall", **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of content.

        Args:
            content: Content to analyze
            granularity: Level of analysis (overall, sentence, aspect)
            **kwargs: Additional parameters

        Returns:
            Sentiment analysis results
        """
        try:
            log_trace_info(
                "gemini_analyze_sentiment",
                content_length=len(content),
                granularity=granularity,
            )

            prompt = self._create_sentiment_prompt(content, granularity)
            response = await self.generate_content(
                prompt, temperature=SENTIMENT_TEMPERATURE
            )

            return self._parse_sentiment_response(response, granularity)

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            raise ClientError(
                f"Sentiment analysis failed: {str(e)}",
                client_name="GeminiService",
                original_error=e,
            )

    # Helper methods for business logic

    def _create_classification_prompt(
        self, content: str, categories: List[str], multi_label: bool
    ) -> str:
        """Create an optimized classification prompt."""
        categories_text = ", ".join(categories)

        if multi_label:
            instruction = "Identify ALL categories that apply to this content."
        else:
            instruction = "Identify the SINGLE BEST category for this content."

        return f"""
        Classify the following content. {instruction}
        
        Available categories: {categories_text}
        
        Content:
        {content}
        
        Respond with the category name(s) and confidence score(s).
        Format: category:confidence (e.g., "technology:0.95" or for multiple: "technology:0.8, science:0.7")
        """

    def _parse_classification_response(
        self,
        response: str,
        categories: List[str],
        multi_label: bool,
        confidence_threshold: float,
    ) -> Dict[str, Any]:
        """Parse and validate classification response."""
        result = {
            "classifications": [],
            "raw_response": response,
            "multi_label": multi_label,
            "confidence_threshold": confidence_threshold,
        }

        # Parse response for category:confidence pairs
        import re

        pattern = r"(\w+):(\d*\.?\d+)"
        matches = re.findall(pattern, response)

        for category, confidence in matches:
            conf_value = float(confidence)
            if category in categories and conf_value >= confidence_threshold:
                result["classifications"].append(
                    {"category": category, "confidence": conf_value}
                )

        # If no valid classifications found, use fallback
        if not result["classifications"]:
            # Try to find any category mention
            response_lower = response.lower()
            for category in categories:
                if category.lower() in response_lower:
                    result["classifications"].append(
                        {
                            "category": category,
                            "confidence": confidence_threshold,  # Default confidence
                        }
                    )
                    if not multi_label:
                        break

        # Sort by confidence
        result["classifications"].sort(key=lambda x: x["confidence"], reverse=True)

        # For single-label, keep only the top classification
        if not multi_label and result["classifications"]:
            result["classifications"] = [result["classifications"][0]]

        return result

    def _create_summary_prompt(
        self, content: str, max_length: Optional[int], style: str
    ) -> str:
        """Create a summary prompt based on style."""
        length_instruction = f" (maximum {max_length} words)" if max_length else ""

        style_instructions = {
            "concise": f"Provide a concise summary{length_instruction}:",
            "detailed": f"Provide a detailed summary{length_instruction} covering all key points:",
            "bullet_points": f"Summarize in bullet points{length_instruction}:",
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        return f"""
        {instruction}
        
        Content:
        {content}
        
        Summary:
        """

    def _create_sentiment_prompt(self, content: str, granularity: str) -> str:
        """Create a sentiment analysis prompt."""
        instructions = {
            "overall": "Analyze the overall sentiment of this content.",
            "sentence": "Analyze the sentiment of each sentence.",
            "aspect": "Identify aspects/topics and their associated sentiments.",
        }

        return f"""
        {instructions.get(granularity, instructions["overall"])}
        
        Content:
        {content}
        
        Provide sentiment as: positive, negative, neutral, or mixed.
        Include confidence score (0-1) for each sentiment.
        """

    def _parse_sentiment_response(
        self, response: str, granularity: str
    ) -> Dict[str, Any]:
        """Parse sentiment analysis response."""
        result = {
            "granularity": granularity,
            "raw_response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Simple parsing for overall sentiment
        response_lower = response.lower()

        sentiments = {
            "positive": "positive" in response_lower,
            "negative": "negative" in response_lower,
            "neutral": "neutral" in response_lower,
            "mixed": "mixed" in response_lower,
        }

        # Find the dominant sentiment
        for sentiment, found in sentiments.items():
            if found:
                result["sentiment"] = sentiment
                break
        else:
            result["sentiment"] = "neutral"  # Default

        # Try to extract confidence
        import re

        confidence_match = re.search(r"(\d*\.?\d+)", response)
        if confidence_match:
            result["confidence"] = float(confidence_match.group(1))
        else:
            result["confidence"] = 0.7  # Default confidence

        return result

    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        prompt = f"""
        Extract all named entities (people, organizations, locations, dates, etc.) from this text:
        
        {text}
        
        Format: entity_type: entity_value
        """

        response = await self.generate_content(prompt, temperature=0.1)

        entities = []
        for line in response.split("\n"):
            if ":" in line:
                entity_type, entity_value = line.split(":", 1)
                entities.append(
                    {"type": entity_type.strip(), "value": entity_value.strip()}
                )

        return entities

    async def _analyze_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure."""
        prompt = f"""
        Analyze the structure of this document:
        
        {text}
        
        Identify: sections, headings, paragraphs, lists, etc.
        """

        response = await self.generate_content(prompt, temperature=0.1)

        return {
            "structure_analysis": response,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _detect_language(self, text: str) -> str:
        """Detect the language of text."""
        prompt = f"""
        Detect the language of this text:
        
        {text}
        
        Respond with just the language name (e.g., "English", "Spanish", etc.)
        """

        response = await self.generate_content(
            prompt, temperature=LANGUAGE_DETECTION_TEMPERATURE
        )
        return response.strip()

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            client_health = await self.gemini_client.health_check()

            return {
                "service": "GeminiService",
                "status": (
                    "healthy"
                    if client_health.get("status") == "healthy"
                    else "unhealthy"
                ),
                "client_status": client_health,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "service": "GeminiService",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def cleanup(self) -> None:
        """Clean up service resources."""
        if self._gemini_client:
            await self._gemini_client.close()
            self._gemini_client = None
        await super().cleanup()
