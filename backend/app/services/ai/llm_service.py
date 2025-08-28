"""
Unified LLM Service that selects the underlying client (OpenAI or Gemini)
based on the model and provides a single generate_content method with
optional structured output parsing.
"""

import logging
import re
from typing import Any, Dict, Optional, List, Tuple, Union

from app.services.base.user_aware_service import UserAwareService
from app.clients import get_openai_client, get_gemini_client
from app.clients.openai.client import OpenAIClient
from app.clients.gemini.client import GeminiClient
from app.core.langsmith_config import log_trace_info, langsmith_trace
from app.clients.base.exceptions import (
    ClientError,
    ClientQuotaExceededError,
    ClientRateLimitError,
)
from app.core.prompts.parsers import (
    RetryingPydanticOutputParser as BaseOutputParser,
    ParsingResult,
)
from typing import Union


logger = logging.getLogger(__name__)


# Named constants
DEFAULT_MAX_OUTPUT_TOKENS: int = 65535
DEFAULT_TEMPERATURE: float = 0.1
DEFAULT_TOP_P: float = 1.0
DEFAULT_PARSE_GENERATION_MAX_ATTEMPTS: int = 3
# Max characters of raw model output to include in warning logs when parsing fails
PARSE_ERROR_OUTPUT_PREVIEW_CHARS: int = 256


class LLMService(UserAwareService):
    """
    Unified service for LLM operations across providers.

    - Picks the underlying client by model via a configurable mapping
    - Exposes a single, LangSmith-traced generate_content method
    - Supports optional structured parsing with automatic generation retries when parsing fails
    """

    def __init__(self, user_client=None):
        super().__init__(user_client=user_client)
        self._openai_client: Optional[OpenAIClient] = None
        self._gemini_client: Optional[GeminiClient] = None

        # Each tuple is (regex_pattern, client_key)
        # client_key must be one of: "openai", "gemini"
        # Hard-coded mapping (no environment overrides)
        self._model_client_rules: List[Tuple[str, str]] = (
            self._load_model_client_rules()
        )

    async def initialize(self) -> None:
        try:
            # Lazy-initialize clients on demand, but pre-warm both for reliability
            self._openai_client = await get_openai_client()
            self._gemini_client = await get_gemini_client()
            logger.info("LLMService initialized with OpenAI and Gemini clients")
        except Exception as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            raise

    @property
    def openai(self) -> OpenAIClient:
        if not self._openai_client:
            raise ClientError("OpenAI client not initialized", "LLMService")
        return self._openai_client

    @property
    def gemini(self) -> GeminiClient:
        if not self._gemini_client:
            raise ClientError("Gemini client not initialized", "LLMService")
        return self._gemini_client

    def _load_model_client_rules(self) -> List[Tuple[str, str]]:
        """Return hard-coded model->client rules (no env loading)."""
        # Common model name prefixes/patterns
        return [
            # OpenAI family
            (r"^(gpt-|o1|o3|text-|chatgpt|gpt4o|gpt-4o|gpt4\.\d|gpt-4\.\d)", "openai"),
            # Gemini family
            (r"^(gemini-|models/gemini-|learnlm)", "gemini"),
        ]

    def _resolve_client_key_for_model(self, model: Optional[str]) -> str:
        """Return client key (openai|gemini) for the requested model."""
        if model:
            for pattern, client_key in self._model_client_rules:
                try:
                    if re.match(pattern, model, flags=re.IGNORECASE):
                        return client_key
                except re.error:
                    # Ignore bad regex entries
                    continue

        # Fallback: prefer OpenAI if model unknown
        return "openai"

    def _build_client_kwargs(
        self,
        client_key: str,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        top_p: Optional[float],
        frequency_penalty: Optional[float],
        presence_penalty: Optional[float],
        system_message: Optional[str],
        extra_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Normalize common args; map to each client style
        common = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        # Remove None values early
        common = {k: v for k, v in common.items() if v is not None}

        if client_key == "openai":
            # OpenAI supports frequency/presence penalty and uses system_prompt
            if frequency_penalty is not None:
                common["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None:
                common["presence_penalty"] = presence_penalty
            if system_message:
                common["system_prompt"] = system_message
        else:
            # Gemini uses system_instruction via system_prompt key
            if system_message:
                common["system_prompt"] = system_message

        # Merge any extra kwargs, without overwriting explicit common keys
        for k, v in extra_kwargs.items():
            if k not in common and v is not None:
                common[k] = v

        return common

    # it is managed in client level
    # @langsmith_trace(name="llm_generate_content", run_type="llm")
    async def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = DEFAULT_MAX_OUTPUT_TOKENS,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        system_message: Optional[str] = None,
        output_parser: Optional[BaseOutputParser[Any]] = None,
        parse_generation_max_attempts: int = DEFAULT_PARSE_GENERATION_MAX_ATTEMPTS,
        **kwargs,
    ) -> Union[str, ParsingResult]:
        """
        Generate content using the appropriate client selected by model.

        If output_parser is provided, returns ParsingResult. On parsing failure,
        the method will retry the LLM generation up to parse_generation_max_attempts.
        Otherwise, returns raw string content.
        """
        try:
            client_key = self._resolve_client_key_for_model(model)
            client = self.openai if client_key == "openai" else self.gemini

            log_trace_info(
                "llm_generate_content",
                prompt_length=len(prompt),
                model=model or getattr(client.config, "model_name", None),
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                client=client_key,
                has_output_parser=bool(output_parser),
            )

            logger.debug(
                f"Generating content using {client_key} (no prompt preview logged)"
            )

            # Build kwargs for the specific client call
            client_kwargs = self._build_client_kwargs(
                client_key=client_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                system_message=system_message,
                extra_kwargs=kwargs,
            )

            # For Gemini with structured output, pass response_schema and strip
            # prompt-end format instructions (they are provided via schema instead)
            prompt_to_send = prompt
            if output_parser is not None and client_key == "gemini":
                try:
                    # Provide Pydantic model directly as response_schema
                    pyd_model = getattr(output_parser, "pydantic_model", None)
                    # Determine if schema should be embedded in prompt instead of response_schema
                    # this is due to gemini doesn't support complex response_schema
                    schema_in_prompt: bool = False
                    if pyd_model is not None:
                        schema_in_prompt = bool(
                            getattr(pyd_model, "schema_in_prompt", False)
                        )
                        if not schema_in_prompt:
                            client_kwargs["response_schema"] = pyd_model

                        # Strip trailing format instructions if they were appended to the prompt
                        try:
                            format_instructions = (
                                output_parser.get_format_instructions()
                            )
                        except Exception:
                            format_instructions = None
                        # Only strip format instructions when using response_schema; if schema is in prompt, keep them
                        if format_instructions and not schema_in_prompt:
                            # Remove optional header + instructions at the end of the prompt
                            header = "Format And Field Description Instructions:\n\n"
                            # Pattern removes either the exact instructions or header+instructions if present at end
                            pattern = (
                                r"(?:\n\n)?(?:"
                                + re.escape(header)
                                + r")?"
                                + re.escape(format_instructions)
                                + r"\s*$"
                            )
                            cleaned = re.sub(
                                pattern, "", prompt_to_send, flags=re.DOTALL
                            )
                            if cleaned != prompt_to_send:
                                logger.debug(
                                    "Stripped output parser format instructions from prompt for Gemini"
                                )
                                prompt_to_send = cleaned
                except Exception as strip_error:
                    logger.warning(
                        f"Failed Gemini structured-output preparation; proceeding with raw prompt: {strip_error}"
                    )

            # If no parser, single shot call
            if output_parser is None:
                response = await client.generate_content(prompt=prompt, **client_kwargs)
                logger.debug(f"Generated {len(response)} characters")
                return response

            # With parser: attempt generation+parse with retries on generation when parse fails
            last_result: Optional[ParsingResult] = None
            attempts = max(1, parse_generation_max_attempts + 1)

            for attempt in range(1, attempts + 1):
                response = await client.generate_content(
                    prompt=(prompt_to_send if client_key == "gemini" else prompt),
                    **client_kwargs,
                )
                logger.debug(
                    f"Attempt {attempt}: generated {len(response)} characters; parsing..."
                )

                parsing_result = output_parser.parse_with_retry(response)
                if parsing_result.success:
                    logger.debug("Parsing succeeded")
                    return parsing_result

                last_result = parsing_result
                # Collect rich diagnostics for easier troubleshooting
                validation_errors = (
                    getattr(parsing_result, "validation_errors", []) or []
                )
                parsing_errors = getattr(parsing_result, "parsing_errors", []) or []
                raw_preview = (response or "")[:PARSE_ERROR_OUTPUT_PREVIEW_CHARS]
                model_name = model or getattr(
                    getattr(client, "config", None), "model_name", None
                )

                logger.warning(
                    f"Parsing failed on attempt {attempt}/{attempts} "
                    f"(client={client_key}, model={model_name}). "
                    f"errors(validation={len(validation_errors)}, parsing={len(parsing_errors)}), "
                    f"confidence={parsing_result.confidence_score:.2f}, "
                    f"raw_len={len(response) if response is not None else 0}, "
                    f"raw_preview='{raw_preview.replace('\n', ' ')}' "
                    f"Will{' not' if attempt == attempts else ''} retry generation."
                )

            # Return the last parsing result (failed) so caller can inspect errors
            assert last_result is not None
            return last_result

        except (ClientRateLimitError, ClientQuotaExceededError):
            logger.error("LLM rate/quota limit exceeded during content generation")
            raise
        except Exception as e:
            logger.error(f"LLM content generation failed: {e}")
            raise ClientError(
                f"LLM content generation failed: {str(e)}",
                client_name="LLMService",
                original_error=e,
            )

    @langsmith_trace(name="generate_image_semantics", run_type="llm")
    async def generate_image_semantics(
        self,
        *,
        contents: List[Dict[str, Any]],
        analysis_prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        output_parser: Optional[BaseOutputParser[Any]] = None,
        parse_generation_max_attempts: int = DEFAULT_PARSE_GENERATION_MAX_ATTEMPTS,
    ) -> Union[str, ParsingResult]:
        """Generate image semantics for one or more images in a single LLM call.

        Expected contents format: list of {"content": bytes, "content_type": str, "filename": Optional[str]}.
        """
        try:
            # For now, route images to Gemini.
            ai_response = await self.gemini.analyze_image_semantics_batch(
                contents=contents,
                analysis_context={
                    "prompt": analysis_prompt,
                    "system_prompt": system_prompt,
                    "expects_structured_output": output_parser is not None,
                    "output_format": "json" if output_parser is not None else "text",
                    # also pass filenames list for traceability if provided
                    "filenames": [
                        c.get("filename")
                        for c in (contents or [])
                        if isinstance(c, dict)
                    ],
                },
            )

            if output_parser is None:
                return ai_response.get("content", "")

            return output_parser.parse_with_retry(ai_response.get("content", ""))
        except (ClientRateLimitError, ClientQuotaExceededError) as e:
            logger.warning(f"Image semantics quota/limit: {e}")
            raise
        except Exception as e:
            logger.error(f"generate_image_semantics failed: {e}")
            if output_parser is not None:
                return ParsingResult(
                    success=False,
                    parsed_data=None,
                    raw_output=str(e),
                    confidence_score=0.0,
                    validation_errors=[str(e)],
                    parsing_errors=[str(e)],
                )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check service health of both underlying clients."""
        try:
            openai_health = await self.openai.health_check()
        except Exception as e:
            openai_health = {"status": "unhealthy", "error": str(e)}

        try:
            gemini_health = await self.gemini.health_check()
        except Exception as e:
            gemini_health = {"status": "unhealthy", "error": str(e)}

        status = (
            "healthy"
            if openai_health.get("status") == "healthy"
            and gemini_health.get("status") == "healthy"
            else "degraded"
        )
        return {
            "service": "LLMService",
            "status": status,
            "openai": openai_health,
            "gemini": gemini_health,
        }

    async def cleanup(self) -> None:
        if self._openai_client:
            await self._openai_client.close()
            self._openai_client = None
        if self._gemini_client:
            await self._gemini_client.close()
            self._gemini_client = None
        await super().cleanup()
