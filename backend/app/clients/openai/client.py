"""
Main OpenAI client implementation.
"""

import logging
from typing import Any, Dict, Optional, List
from openai import OpenAI
from openai import RateLimitError, APIError, AuthenticationError

from ..base.client import BaseClient, with_retry
from ..base.interfaces import AIOperations
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
    ClientQuotaExceededError,
    ClientRateLimitError,
)
from .config import OpenAIClientConfig
from ...core.langsmith_config import langsmith_trace, log_trace_info

logger = logging.getLogger(__name__)


class OpenAIClient(BaseClient, AIOperations):
    """OpenAI client wrapper providing AI operations."""

    def __init__(self, config: OpenAIClientConfig):
        super().__init__(config, "OpenAIClient")
        self.config: OpenAIClientConfig = config
        self._openai_client: Optional[OpenAI] = None

    @property
    def openai_client(self) -> OpenAI:
        """Get the underlying OpenAI client."""
        if not self._openai_client:
            raise ClientError("OpenAI client not initialized", self.client_name)
        return self._openai_client

    @with_retry(max_retries=3, backoff_factor=2.0)
    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            self.logger.info("Initializing OpenAI client...")

            # Create OpenAI client
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            }

            if self.config.api_base:
                client_kwargs["base_url"] = self.config.api_base

            if self.config.organization:
                client_kwargs["organization"] = self.config.organization

            self._openai_client = OpenAI(**client_kwargs)

            # Test the connection
            await self._test_connection()

            self._initialized = True
            self.logger.info("OpenAI client initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize OpenAI client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def _test_connection(self) -> None:
        """Test OpenAI API connection."""
        try:
            # Simple test with a minimal completion
            response = self._openai_client.completions.create(
                model=self.config.model_name, prompt="Test", max_tokens=1
            )

            if not response.choices:
                raise ClientConnectionError(
                    "OpenAI API test failed: No response received",
                    client_name=self.client_name,
                )

            self.logger.debug("OpenAI API connection test successful")

        except AuthenticationError as e:
            raise ClientAuthenticationError(
                f"OpenAI API authentication failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except RateLimitError as e:
            raise ClientRateLimitError(
                f"OpenAI API rate limit exceeded: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except APIError as e:
            if "quota" in str(e).lower():
                raise ClientQuotaExceededError(
                    f"OpenAI API quota exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            else:
                raise ClientConnectionError(
                    f"OpenAI API connection test failed: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
        except Exception as e:
            raise ClientConnectionError(
                f"OpenAI API connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on OpenAI client."""
        try:
            # Test API connection
            await self._test_connection()

            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "model_name": self.config.model_name,
                "connection": "ok",
                "config": {
                    "model_name": self.config.model_name,
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                    "temperature": self.config.temperature,
                    "api_base": self.config.api_base or "https://api.openai.com/v1",
                },
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """Close OpenAI client and clean up resources."""
        try:
            if self._openai_client:
                # OpenAI client doesn't require explicit closing
                self._openai_client = None

            self._initialized = False
            self.logger.info("OpenAI client closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing OpenAI client: {e}")
            raise ClientError(
                f"Error closing OpenAI client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    # AIOperations interface implementation

    @with_retry(max_retries=3, backoff_factor=2.0)
    @langsmith_trace(name="openai_generate_content", run_type="llm")
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content based on a prompt."""
        try:
            log_trace_info(
                "openai_generate_content",
                prompt_length=len(prompt),
                model=kwargs.get("model", self.config.model_name),
            )
            self.logger.debug(f"Generating content for prompt: {prompt[:100]}...")

            # Use chat completions API
            messages = [{"role": "user", "content": prompt}]

            # Prepare parameters
            params = {
                "model": kwargs.get("model", self.config.model_name),
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty", self.config.frequency_penalty
                ),
                "presence_penalty": kwargs.get(
                    "presence_penalty", self.config.presence_penalty
                ),
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            # Execute in thread pool to avoid blocking
            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.openai_client.chat.completions.create(**params)
            )

            if not response.choices or not response.choices[0].message.content:
                raise ClientError(
                    "No content generated from OpenAI", client_name=self.client_name
                )

            content = response.choices[0].message.content
            self.logger.debug(f"Successfully generated {len(content)} characters")
            return content

        except (RateLimitError, APIError) as e:
            self.logger.error(f"OpenAI API error: {e}")
            if isinstance(e, RateLimitError):
                raise ClientRateLimitError(
                    f"OpenAI rate limit exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            elif "quota" in str(e).lower():
                raise ClientQuotaExceededError(
                    f"OpenAI quota exceeded: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
            else:
                raise ClientError(
                    f"OpenAI API error: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise ClientError(
                f"Content generation failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="openai_analyze_document", run_type="tool")
    async def analyze_document(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Analyze a document and extract information."""
        try:
            log_trace_info(
                "openai_analyze_document",
                content_type=content_type,
                content_size=len(content),
            )
            self.logger.debug(f"Analyzing document of type: {content_type}")

            # For OpenAI, we need to convert document to text first
            # This is a simplified implementation - in practice, you'd use OCR or other methods
            if content_type == "text/plain":
                text_content = content.decode("utf-8")
            else:
                # For other formats, we'd need to extract text first
                # This is where you'd integrate with OCR services
                raise ClientError(
                    f"Document type {content_type} not supported for direct analysis",
                    client_name=self.client_name,
                )

            # Analyze the text content
            analysis_prompt = f"""
            Analyze the following document and provide a structured analysis:
            
            Document content:
            {text_content[:4000]}...
            
            Please provide:
            1. Document type
            2. Key topics
            3. Summary
            4. Important entities (names, dates, amounts)
            
            Format your response as JSON.
            """

            analysis_result = await self.generate_content(analysis_prompt, **kwargs)

            # Try to parse as JSON, fallback to text analysis
            try:
                import json

                parsed_analysis = json.loads(analysis_result)
            except json.JSONDecodeError:
                parsed_analysis = {"analysis_text": analysis_result, "format": "text"}

            result = {
                "analysis": parsed_analysis,
                "content_type": content_type,
                "content_length": len(content),
                "analysis_method": "openai_text_analysis",
                "model_used": kwargs.get("model", self.config.model_name),
            }

            self.logger.debug("Document analysis completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            raise ClientError(
                f"Document analysis failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="openai_extract_text", run_type="tool")
    async def extract_text(
        self, content: bytes, content_type: str, **kwargs
    ) -> Dict[str, Any]:
        """Extract text from a document."""
        try:
            log_trace_info(
                "openai_extract_text",
                content_type=content_type,
                content_size=len(content),
            )
            self.logger.debug(f"Extracting text from document of type: {content_type}")

            # OpenAI doesn't provide OCR services directly
            # This would typically be handled by a separate OCR service
            if content_type == "text/plain":
                extracted_text = content.decode("utf-8")
                confidence = 1.0
                method = "direct_text_extraction"
            else:
                raise ClientError(
                    f"Text extraction from {content_type} requires OCR service",
                    client_name=self.client_name,
                )

            result = {
                "extracted_text": extracted_text,
                "extraction_method": method,
                "extraction_confidence": confidence,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "content_type": content_type,
            }

            self.logger.debug("Text extraction completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise ClientError(
                f"Text extraction failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @langsmith_trace(name="openai_classify_content", run_type="llm")
    async def classify_content(
        self, content: str, categories: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Classify content into predefined categories."""
        try:
            log_trace_info(
                "openai_classify_content",
                content_length=len(content),
                categories_count=len(categories),
            )
            self.logger.debug(f"Classifying content into {len(categories)} categories")

            # Create classification prompt
            categories_text = ", ".join(categories)
            classification_prompt = f"""
            Classify the following content into one of these categories: {categories_text}
            
            Content:
            {content[:2000]}...
            
            Respond with only the category name that best fits this content.
            If you're unsure, provide your best guess along with a confidence score.
            
            Format: Category: [category_name], Confidence: [0.0-1.0]
            """

            classification_result = await self.generate_content(
                classification_prompt, **kwargs
            )

            # Parse the result
            classification = classification_result.strip()
            confidence = 0.8  # Default confidence

            # Try to extract confidence if provided
            if "Confidence:" in classification:
                parts = classification.split("Confidence:")
                if len(parts) == 2:
                    try:
                        confidence = float(parts[1].strip())
                        classification = parts[0].replace("Category:", "").strip()
                    except ValueError:
                        pass

            # Clean up classification
            classification = classification.replace("Category:", "").strip()

            # Validate classification is in categories
            if classification not in categories:
                # Try to find partial match
                classification_lower = classification.lower()
                for category in categories:
                    if (
                        category.lower() in classification_lower
                        or classification_lower in category.lower()
                    ):
                        classification = category
                        break
                else:
                    # Use first category as fallback
                    classification = categories[0]
                    confidence = 0.5  # Lower confidence for fallback

            result = {
                "classification": classification,
                "confidence": confidence,
                "categories": categories,
                "content_length": len(content),
                "model_used": kwargs.get("model", self.config.model_name),
            }

            self.logger.debug(
                f"Content classified as: {classification} (confidence: {confidence})"
            )
            return result

        except Exception as e:
            self.logger.error(f"Content classification failed: {e}")
            raise ClientError(
                f"Content classification failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
