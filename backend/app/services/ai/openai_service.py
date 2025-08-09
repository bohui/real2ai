"""
OpenAI Service - Business Logic Layer for OpenAI AI Operations

This service handles all AI operations using the OpenAI client,
separating business logic from connection management.
"""

import json
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from app.services.base.user_aware_service import UserAwareService
from app.clients import get_openai_client
from app.clients.openai.client import OpenAIClient
from app.core.langsmith_config import langsmith_trace, log_trace_info
from app.clients.base.exceptions import (
    ClientError,
    ClientRateLimitError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)

# Constants
CONTENT_PREVIEW_LENGTH = 2000
PROMPT_PREVIEW_LENGTH = 100
ANALYSIS_CONTENT_LENGTH = 4000


class OpenAIService(UserAwareService):
    """
    Service layer for OpenAI AI operations.
    
    This service provides high-level AI operations using the OpenAI client,
    handling business logic, error handling, and response processing.
    """
    
    def __init__(self, user_client=None):
        """Initialize OpenAI service."""
        super().__init__(user_client=user_client)
        self._openai_client: Optional[OpenAIClient] = None
        
    async def initialize(self) -> None:
        """Initialize the OpenAI service and underlying client."""
        try:
            # Get the OpenAI client (connection layer)
            self._openai_client = await get_openai_client()
            
            if not self._openai_client:
                raise ClientError("Failed to initialize OpenAI client", "OpenAIService")
                
            logger.info("OpenAI service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            raise
    
    @property
    def openai_client(self) -> OpenAIClient:
        """Get the underlying OpenAI client."""
        if not self._openai_client:
            raise ClientError("OpenAI client not initialized", "OpenAIService")
        return self._openai_client
    
    @langsmith_trace(name="openai_generate_content", run_type="llm")
    async def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        top_p: float = None,
        frequency_penalty: float = None,
        presence_penalty: float = None,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate content based on a prompt.
        
        Args:
            prompt: The input prompt
            model: Model to use (overrides default)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum output tokens
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            system_message: Optional system message to set context
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text content
            
        Raises:
            ClientError: If generation fails
            ClientRateLimitError: If rate limit is exceeded
            ClientQuotaExceededError: If quota is exceeded
        """
        try:
            log_trace_info(
                "openai_generate_content",
                prompt_length=len(prompt),
                model=model or self.openai_client.config.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            logger.debug(
                f"Generating content for prompt: {prompt[:PROMPT_PREVIEW_LENGTH]}..."
            )
            
            # Build messages with optional system message
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare generation parameters
            generation_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                **kwargs
            }
            
            # Remove None values
            generation_params = {k: v for k, v in generation_params.items() if v is not None}
            
            # Delegate to client for the actual API call
            response = await self.openai_client.generate_content(
                prompt=prompt,
                **generation_params
            )
            
            logger.debug(f"Successfully generated {len(response)} characters")
            return response
            
        except (ClientRateLimitError, ClientQuotaExceededError):
            logger.error("OpenAI rate/quota limit exceeded during content generation")
            raise
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise ClientError(
                f"Content generation failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    @langsmith_trace(name="openai_analyze_document", run_type="tool")
    async def analyze_document(
        self,
        content: bytes,
        content_type: str,
        analysis_type: str = "comprehensive",
        custom_instructions: Optional[str] = None,
        include_entities: bool = True,
        include_summary: bool = True,
        include_topics: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze a document and extract information.
        
        Args:
            content: Document content as bytes
            content_type: MIME type of the document
            analysis_type: Type of analysis (comprehensive, quick, custom)
            custom_instructions: Custom analysis instructions
            include_entities: Whether to extract entities
            include_summary: Whether to generate summary
            include_topics: Whether to identify topics
            **kwargs: Additional analysis parameters
            
        Returns:
            Analysis results with requested information
        """
        try:
            log_trace_info(
                "openai_analyze_document",
                content_type=content_type,
                content_size=len(content),
                analysis_type=analysis_type,
            )
            
            logger.debug(f"Analyzing document of type: {content_type}")
            
            # Convert document to text (OpenAI doesn't do OCR directly)
            if content_type == "text/plain":
                text_content = content.decode("utf-8")
            else:
                # For other formats, we'd need OCR service integration
                raise ClientError(
                    f"Document type {content_type} not supported for direct analysis. "
                    f"Use OCR service first to extract text.",
                    client_name="OpenAIService",
                )
            
            # Create analysis prompt based on requirements
            analysis_prompt = self._create_document_analysis_prompt(
                text_content=text_content[:ANALYSIS_CONTENT_LENGTH],
                analysis_type=analysis_type,
                custom_instructions=custom_instructions,
                include_entities=include_entities,
                include_summary=include_summary,
                include_topics=include_topics
            )
            
            # Generate analysis
            analysis_result = await self.generate_content(
                prompt=analysis_prompt,
                temperature=0.1,  # Low temperature for consistent analysis
                **kwargs
            )
            
            # Parse and structure the analysis
            structured_analysis = self._parse_document_analysis(
                analysis_result,
                include_entities=include_entities,
                include_summary=include_summary,
                include_topics=include_topics
            )
            
            result = {
                "analysis": structured_analysis,
                "content_type": content_type,
                "content_length": len(content),
                "text_length": len(text_content),
                "analysis_method": "openai_text_analysis",
                "analysis_type": analysis_type,
                "model_used": kwargs.get("model", self.openai_client.config.model_name),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            logger.debug("Document analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    @langsmith_trace(name="openai_extract_text", run_type="tool")
    async def extract_text(
        self,
        content: bytes,
        content_type: str,
        enhance_with_ai: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from a document.
        
        Args:
            content: Document content as bytes
            content_type: MIME type of the document
            enhance_with_ai: Whether to enhance extraction with AI
            **kwargs: Additional extraction parameters
            
        Returns:
            Extracted text and metadata
        """
        try:
            log_trace_info(
                "openai_extract_text",
                content_type=content_type,
                content_size=len(content),
                enhance_with_ai=enhance_with_ai,
            )
            
            logger.debug(f"Extracting text from document of type: {content_type}")
            
            # OpenAI doesn't provide OCR services directly
            if content_type == "text/plain":
                extracted_text = content.decode("utf-8")
                confidence = 1.0
                method = "direct_text_extraction"
                
                # Optionally enhance with AI processing
                if enhance_with_ai:
                    enhanced_text = await self._enhance_extracted_text(extracted_text)
                    extracted_text = enhanced_text
                    method = "ai_enhanced_extraction"
                    
            else:
                raise ClientError(
                    f"Text extraction from {content_type} requires OCR service. "
                    f"OpenAI service only supports plain text directly.",
                    client_name="OpenAIService",
                )
            
            # Calculate text metrics
            text_metrics = self._calculate_text_metrics(extracted_text)
            
            result = {
                "extracted_text": extracted_text,
                "extraction_method": method,
                "extraction_confidence": confidence,
                "content_type": content_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **text_metrics,
            }
            
            logger.debug("Text extraction completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    @langsmith_trace(name="openai_classify_content", run_type="llm")
    async def classify_content(
        self,
        content: str,
        categories: List[str],
        multi_label: bool = False,
        confidence_threshold: float = 0.7,
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Classify content into predefined categories.
        
        Args:
            content: Content to classify
            categories: List of possible categories
            multi_label: Whether multiple categories can apply
            confidence_threshold: Minimum confidence for classification
            include_reasoning: Whether to include reasoning in response
            **kwargs: Additional classification parameters
            
        Returns:
            Classification results with confidence scores
        """
        try:
            log_trace_info(
                "openai_classify_content",
                content_length=len(content),
                categories_count=len(categories),
                multi_label=multi_label,
            )
            
            logger.debug(f"Classifying content into {len(categories)} categories")
            
            # Create optimized classification prompt
            classification_prompt = self._create_classification_prompt(
                content=content,
                categories=categories,
                multi_label=multi_label,
                include_reasoning=include_reasoning
            )
            
            # Generate classification
            classification_result = await self.generate_content(
                prompt=classification_prompt,
                temperature=0.1,  # Low temperature for consistent classification
                **kwargs
            )
            
            # Parse and validate classification
            result = self._parse_classification_response(
                response=classification_result,
                categories=categories,
                multi_label=multi_label,
                confidence_threshold=confidence_threshold,
                include_reasoning=include_reasoning
            )
            
            # Add metadata
            result.update({
                "content_length": len(content),
                "model_used": kwargs.get("model", self.openai_client.config.model_name),
                "multi_label": multi_label,
                "confidence_threshold": confidence_threshold,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            logger.debug(f"Content classified: {result.get('classifications', [])}")
            return result
            
        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            raise ClientError(
                f"Content classification failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    @langsmith_trace(name="openai_summarize", run_type="llm")
    async def summarize_content(
        self,
        content: str,
        max_length: Optional[int] = None,
        style: str = "concise",
        focus_areas: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Summarize content with specified parameters.
        
        Args:
            content: Content to summarize
            max_length: Maximum summary length in words
            style: Summary style (concise, detailed, bullet_points, executive)
            focus_areas: Specific areas to focus on in summary
            **kwargs: Additional parameters
            
        Returns:
            Summary and metadata
        """
        try:
            log_trace_info(
                "openai_summarize",
                content_length=len(content),
                max_length=max_length,
                style=style,
            )
            
            # Create summary prompt
            summary_prompt = self._create_summary_prompt(
                content=content,
                max_length=max_length,
                style=style,
                focus_areas=focus_areas
            )
            
            # Generate summary
            summary = await self.generate_content(
                prompt=summary_prompt,
                temperature=0.3,  # Slightly higher temperature for variety
                **kwargs
            )
            
            # Calculate metrics
            compression_ratio = len(summary) / len(content) if content else 0
            
            return {
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "compression_ratio": compression_ratio,
                "style": style,
                "focus_areas": focus_areas,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise ClientError(
                f"Summarization failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    @langsmith_trace(name="openai_chat_completion", run_type="llm")
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete a chat conversation.
        
        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            stream: Whether to stream response
            **kwargs: Additional parameters
            
        Returns:
            Chat completion response
        """
        try:
            # Validate messages format
            self._validate_chat_messages(messages)
            
            # For non-streaming, we can use the existing generate_content
            if not stream:
                # Convert to single prompt format for generate_content
                user_message = messages[-1]["content"]
                system_message = None
                
                # Extract system message if present
                if messages and messages[0]["role"] == "system":
                    system_message = messages[0]["content"]
                
                response = await self.generate_content(
                    prompt=user_message,
                    system_message=system_message,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                return {
                    "response": response,
                    "message_count": len(messages),
                    "model_used": model or self.openai_client.config.model_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Streaming would require additional implementation
                raise ClientError(
                    "Streaming chat completion not yet implemented",
                    client_name="OpenAIService"
                )
                
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise ClientError(
                f"Chat completion failed: {str(e)}",
                client_name="OpenAIService",
                original_error=e,
            )
    
    # Helper methods for business logic
    
    def _create_document_analysis_prompt(
        self,
        text_content: str,
        analysis_type: str,
        custom_instructions: Optional[str],
        include_entities: bool,
        include_summary: bool,
        include_topics: bool
    ) -> str:
        """Create a document analysis prompt based on requirements."""
        
        base_prompt = "Analyze the following document and provide a structured analysis:\n\n"
        base_prompt += f"Document content:\n{text_content}\n\n"
        
        # Add analysis requirements
        requirements = []
        if include_entities:
            requirements.append("Important entities (names, dates, amounts, locations)")
        if include_summary:
            requirements.append("Summary of key points")
        if include_topics:
            requirements.append("Main topics and themes")
        
        if analysis_type == "comprehensive":
            requirements.extend([
                "Document type and purpose",
                "Key insights and conclusions",
                "Action items or recommendations"
            ])
        elif analysis_type == "quick":
            requirements = ["Brief summary", "Document type"]
        
        if custom_instructions:
            requirements.append(f"Custom analysis: {custom_instructions}")
        
        base_prompt += "Please provide:\n"
        for i, req in enumerate(requirements, 1):
            base_prompt += f"{i}. {req}\n"
        
        base_prompt += "\nFormat your response as JSON with clear sections."
        
        return base_prompt
    
    def _parse_document_analysis(
        self,
        analysis_result: str,
        include_entities: bool,
        include_summary: bool,
        include_topics: bool
    ) -> Dict[str, Any]:
        """Parse and structure document analysis results."""
        try:
            # Try to parse as JSON first
            parsed = json.loads(analysis_result)
            return parsed
        except json.JSONDecodeError:
            # Fallback to text parsing
            structured = {
                "analysis_text": analysis_result,
                "format": "text",
                "parsed_sections": self._extract_sections_from_text(analysis_result)
            }
            return structured
    
    def _create_classification_prompt(
        self,
        content: str,
        categories: List[str],
        multi_label: bool,
        include_reasoning: bool
    ) -> str:
        """Create an optimized classification prompt."""
        categories_text = ", ".join(categories)
        
        if multi_label:
            instruction = "Identify ALL categories that apply to this content."
        else:
            instruction = "Identify the SINGLE BEST category for this content."
        
        prompt = f"""
        Classify the following content. {instruction}
        
        Available categories: {categories_text}
        
        Content:
        {content[:CONTENT_PREVIEW_LENGTH]}...
        """
        
        if include_reasoning:
            prompt += "\n\nProvide your reasoning for the classification."
        
        format_instruction = """
        
        Respond in JSON format:
        {
            "classifications": [
                {"category": "category_name", "confidence": 0.95}
            ]"""
        
        if include_reasoning:
            format_instruction += ',\n            "reasoning": "explanation here"'
        
        format_instruction += """
        }
        """
        
        return prompt + format_instruction
    
    def _parse_classification_response(
        self,
        response: str,
        categories: List[str],
        multi_label: bool,
        confidence_threshold: float,
        include_reasoning: bool
    ) -> Dict[str, Any]:
        """Parse and validate classification response."""
        try:
            # Try JSON parsing first
            parsed = json.loads(response)
            classifications = parsed.get("classifications", [])
            
            # Validate classifications
            valid_classifications = []
            for cls in classifications:
                if (cls.get("category") in categories and 
                    cls.get("confidence", 0) >= confidence_threshold):
                    valid_classifications.append(cls)
            
            # For single-label, keep only the highest confidence
            if not multi_label and valid_classifications:
                valid_classifications = [max(valid_classifications, 
                                           key=lambda x: x.get("confidence", 0))]
            
            result = {
                "classifications": valid_classifications,
                "raw_response": response,
            }
            
            if include_reasoning and "reasoning" in parsed:
                result["reasoning"] = parsed["reasoning"]
                
            return result
            
        except json.JSONDecodeError:
            # Fallback parsing
            return self._fallback_parse_classification(
                response, categories, multi_label, confidence_threshold
            )
    
    def _create_summary_prompt(
        self,
        content: str,
        max_length: Optional[int],
        style: str,
        focus_areas: Optional[List[str]]
    ) -> str:
        """Create a summary prompt based on style and requirements."""
        length_instruction = f" (maximum {max_length} words)" if max_length else ""
        
        style_instructions = {
            "concise": f"Provide a concise summary{length_instruction}:",
            "detailed": f"Provide a detailed summary{length_instruction} covering all key points:",
            "bullet_points": f"Summarize in bullet points{length_instruction}:",
            "executive": f"Provide an executive summary{length_instruction} for leadership:",
        }
        
        instruction = style_instructions.get(style, style_instructions["concise"])
        
        prompt = f"{instruction}\n\nContent:\n{content}\n"
        
        if focus_areas:
            prompt += f"\nFocus particularly on: {', '.join(focus_areas)}\n"
        
        prompt += "\nSummary:"
        
        return prompt
    
    def _calculate_text_metrics(self, text: str) -> Dict[str, Any]:
        """Calculate metrics for extracted text."""
        words = text.split() if text else []
        lines = text.splitlines() if text else []
        
        return {
            "character_count": len(text),
            "word_count": len(words),
            "line_count": len(lines),
            "average_word_length": (
                sum(len(word.strip(".,!?:;()")) for word in words) / len(words)
                if words else 0
            ),
        }
    
    def _validate_chat_messages(self, messages: List[Dict[str, str]]) -> None:
        """Validate chat messages format."""
        if not messages:
            raise ClientError("Messages list cannot be empty", "OpenAIService")
        
        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise ClientError("Invalid message format", "OpenAIService")
            
            if msg["role"] not in ["system", "user", "assistant"]:
                raise ClientError(f"Invalid role: {msg['role']}", "OpenAIService")
    
    def _extract_sections_from_text(self, text: str) -> Dict[str, str]:
        """Extract sections from unstructured text analysis."""
        sections = {}
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Look for numbered sections or headers
            if (line.endswith(':') and len(line) < 50) or line.startswith(('1.', '2.', '3.')):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.rstrip(':')
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _fallback_parse_classification(
        self,
        response: str,
        categories: List[str],
        multi_label: bool,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Fallback classification parsing for non-JSON responses."""
        classifications = []
        response_lower = response.lower()
        
        # Look for category mentions
        for category in categories:
            if category.lower() in response_lower:
                classifications.append({
                    "category": category,
                    "confidence": confidence_threshold  # Default confidence
                })
                if not multi_label:
                    break
        
        # If no matches, use first category as fallback
        if not classifications:
            classifications.append({
                "category": categories[0],
                "confidence": 0.5  # Low confidence for fallback
            })
        
        return {
            "classifications": classifications,
            "raw_response": response,
            "parsing_method": "fallback"
        }
    
    async def _enhance_extracted_text(self, text: str) -> str:
        """Enhance extracted text using AI processing."""
        enhancement_prompt = f"""
        Clean up and enhance the following extracted text for better readability:
        
        Original text:
        {text[:2000]}...
        
        Please:
        1. Fix any obvious OCR errors
        2. Improve formatting and structure
        3. Maintain the original meaning
        4. Return only the enhanced text
        """
        
        enhanced = await self.generate_content(
            prompt=enhancement_prompt,
            temperature=0.1
        )
        
        return enhanced
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            client_health = await self.openai_client.health_check()
            
            return {
                "service": "OpenAIService",
                "status": "healthy" if client_health.get("status") == "healthy" else "unhealthy",
                "client_status": client_health,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "service": "OpenAIService",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    async def cleanup(self) -> None:
        """Clean up service resources."""
        if self._openai_client:
            await self._openai_client.close()
            self._openai_client = None
        await super().cleanup()