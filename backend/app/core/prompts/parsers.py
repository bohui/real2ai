"""
Adapters around LangChain's PydanticOutputParser to provide retry parsing
and a stable ParsingResult interface for consumers.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError, PrivateAttr
from langchain_core.output_parsers import PydanticOutputParser as LCPydanticOutputParser


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OutputFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    MARKDOWN = "markdown"


@dataclass
class ParsingResult:
    """Result of output parsing operation"""

    success: bool
    parsed_data: Optional[Any] = None
    raw_output: Optional[str] = None
    validation_errors: List[str] = None
    parsing_errors: List[str] = None
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.parsing_errors is None:
            self.parsing_errors = []


class RetryingPydanticOutputParser(LCPydanticOutputParser):
    """
    Child class of LangChain's PydanticOutputParser that adds:
    - parse() returning a ParsingResult
    - parse_with_retry() with light-weight text cleanup attempts
    - confidence scoring based on required field presence
    """

    # Private attributes to avoid Pydantic BaseModel __setattr__ restrictions
    _model: Type[BaseModel] = PrivateAttr()
    _strict_mode: bool = PrivateAttr(default=True)
    _retry_on_failure: bool = PrivateAttr(default=True)
    _max_retries: int = PrivateAttr(default=2)
    _pydantic_model: Type[BaseModel] = PrivateAttr()
    _output_format: "OutputFormat" = PrivateAttr(default=None)  # set in __init__
    _cached_instructions: Optional[str] = PrivateAttr(default=None)

    def __init__(
        self,
        pydantic_object: Type[BaseModel],
        strict_mode: bool = True,
        retry_on_failure: bool = True,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(pydantic_object=pydantic_object)
        self._model = pydantic_object
        self._strict_mode = strict_mode
        self._retry_on_failure = retry_on_failure
        self._max_retries = max_retries
        # Compatibility: expose pydantic_model and output_format via properties
        self._pydantic_model = pydantic_object
        output_format = kwargs.get("output_format")

        if isinstance(output_format, OutputFormat):
            self._output_format = output_format
        elif isinstance(output_format, str):
            try:
                self._output_format = OutputFormat(output_format.lower())
            except Exception:
                self._output_format = OutputFormat.JSON
        else:
            self._output_format = OutputFormat.JSON

    # Properties for safe access/mutation of private attributes
    @property
    def strict_mode(self) -> bool:
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, value: bool) -> None:
        self._strict_mode = bool(value)

    @property
    def retry_on_failure(self) -> bool:
        return self._retry_on_failure

    @retry_on_failure.setter
    def retry_on_failure(self, value: bool) -> None:
        self._retry_on_failure = bool(value)

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value: int) -> None:
        self._max_retries = int(value)

    @property
    def pydantic_model(self) -> Type[BaseModel]:
        return self._pydantic_model

    @property
    def output_format(self) -> OutputFormat:
        # Default lazily if not set
        return self._output_format or OutputFormat.JSON

    # Keep consumer contract: parse(text) -> ParsingResult
    def parse(self, text: str) -> ParsingResult:  # type: ignore[override]
        result = ParsingResult(success=False, raw_output=text)
        candidates: List[Dict[str, Any]] = []
        # Prefer our robust JSON extraction path first to maintain predictable behavior
        try:
            # Try all JSON candidates and pick the first that validates
            candidates = self._extract_all_json_candidates(text)
            if not candidates:
                logger.warning(
                    f"No valid JSON found in output for model {self._model.__name__}: {text}"
                )
                result.parsing_errors.append("No valid JSON found in output")
            else:
                for idx, json_data in enumerate(candidates):
                    try:
                        parsed_model = self._model(**json_data)
                        result.success = True
                        result.parsed_data = parsed_model
                        result.confidence_score = self._calculate_confidence_score(
                            parsed_model
                        )
                        return result
                    except ValidationError as ve:
                        result.validation_errors = [str(error) for error in ve.errors()]
                        # Log warning for first 5 validation failures
                        if idx < 5:
                            logger.warning(
                                f"Validation failed for model {self._model.__name__} on candidate {idx + 1}/{len(candidates)}: {ve.errors()}"
                            )
                        if not self.strict_mode:
                            partial = self._attempt_partial_parsing(json_data)
                            if partial is not None:
                                result.success = True
                                result.parsed_data = partial
                                result.confidence_score = 0.5
                                return result
        except Exception as cleanup_error:
            logger.warning(f"Cleanup parsing error: {cleanup_error}")
            result.parsing_errors.append(f"Cleanup parsing error: {cleanup_error}")

        # If our extraction didn't yield a valid parse, optionally fall back to LangChain's parser
        # Only allow fallback when there is evidence of proper JSON blocks (e.g., fenced blocks)
        if not result.success:
            allow_fallback = ("```" in text) or bool(candidates)
            if allow_fallback:
                try:
                    model_instance = super().parse(text)
                    result.success = True
                    result.parsed_data = model_instance
                    result.confidence_score = self._calculate_confidence_score(
                        model_instance
                    )
                    return result
                except Exception as lc_error:
                    logger.warning(
                        f"LangChain parsing error for model [{self._model.__name__}]: {lc_error}"
                    )
                    result.parsing_errors.append(f"LangChain parsing error: {lc_error}")
        return result

    def parse_with_retry(self, text: str) -> ParsingResult:
        result = self.parse(text)
        if result.success or not self.retry_on_failure:
            return result

        working_text = text
        for attempt in range(1, max(self.max_retries, 0) + 1):
            try:
                fixed = self._attempt_text_fix(working_text, attempt)
                if not fixed or fixed == working_text:
                    continue
                attempt_result = self.parse(fixed)
                if attempt_result.success:
                    return attempt_result
                working_text = fixed
            except Exception as e:
                logger.warning(f"Retry attempt {attempt} failed: {e}")
        return result

    # Utilities
    def _attempt_text_fix(self, text: str, attempt: int) -> str:
        cleaned = text
        if attempt == 1:
            # Strip markdown code fences
            cleaned = re.sub(
                r"^.*?```json\s*", "", cleaned, flags=re.MULTILINE | re.DOTALL
            )
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE | re.DOTALL)
            return cleaned.strip()
        if attempt == 2:
            # Extract JSON within code block
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                return m.group(1)
        if attempt == 3:
            # Remove text before first '{' and after last '}'
            cleaned = re.sub(r"^[^{]*", "", cleaned)
            cleaned = re.sub(r"[^}]*$", "", cleaned)
            # Fix trailing commas
            cleaned = re.sub(r",\s*\}", "}", cleaned)
            cleaned = re.sub(r",\s*\]", "]", cleaned)
            return cleaned.strip()
        return text

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        # Strategy 1: direct
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Strategy 2: fenced block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Strategy 3: first balanced braces snippet
        brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for candidate in matches:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        # Strategy 4: cleanup
        cleaned = self._attempt_text_fix(text, 3)
        if cleaned and cleaned != text:
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
        return None

    def _extract_all_json_candidates(self, text: str) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        # 1) direct
        try:
            obj = json.loads(text.strip())
            if isinstance(obj, dict):
                candidates.append(obj)
        except json.JSONDecodeError:
            pass
        # 2) all fenced blocks (in order of appearance)
        for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
            try:
                obj = json.loads(m.group(1))
                if isinstance(obj, dict):
                    candidates.append(obj)
            except json.JSONDecodeError:
                continue
        # 3) all balanced JSON-like blocks
        brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        for candidate in re.findall(brace_pattern, text, re.DOTALL):
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except json.JSONDecodeError:
                continue
        # 4) cleaned variant
        cleaned = self._attempt_text_fix(text, 3)
        if cleaned and cleaned != text:
            try:
                obj = json.loads(cleaned)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except json.JSONDecodeError:
                pass
        # Prefer later candidates as they are more likely to be the final result
        # but maintain stable order: earlier ones first, later ones last.
        return candidates

    def _attempt_partial_parsing(
        self, json_data: Dict[str, Any]
    ) -> Optional[BaseModel]:
        try:
            schema = self._model.model_json_schema()
            required_fields = set(schema.get("required", []))
            properties = set(schema.get("properties", {}).keys())

            valid_data: Dict[str, Any] = {
                k: v for k, v in json_data.items() if k in properties
            }
            for field in required_fields:
                if field not in valid_data:
                    # Fill conservative defaults
                    valid_data[field] = None
            return self._model(**valid_data)
        except Exception:
            return None

    def _calculate_confidence_score(self, model_instance: BaseModel) -> float:
        try:
            schema = self._model.model_json_schema()
            required_fields = set(schema.get("required", []))
            if not required_fields:
                return 1.0
            present_required = sum(
                1
                for f in required_fields
                if getattr(model_instance, f, None) is not None
            )
            return present_required / max(len(required_fields), 1)
        except Exception:
            return 0.0

    def get_format_instructions(self) -> str:  # type: ignore[override]
        # Cached for performance
        if self._cached_instructions is not None:
            return self._cached_instructions

        instructions = super().get_format_instructions()
        self._cached_instructions = instructions
        return instructions


class StreamingOutputParser(RetryingPydanticOutputParser):
    """Compatibility wrapper for streaming mode with simple chunked parsing."""

    _buffer: str = PrivateAttr(default="")
    _partial_results: List[ParsingResult] = PrivateAttr(default_factory=list)  # type: ignore[type-arg]

    def parse_chunk(self, chunk: str) -> Optional[ParsingResult]:
        self._buffer += chunk
        # Try to detect if buffer contains a complete JSON object
        try:
            data = self._extract_json(self._buffer)
            if data is None:
                return None
            # If valid JSON for our model, parse it
            result = super().parse(json.dumps(data))
            if result.success:
                self._partial_results.append(result)
                # Reset buffer after successful parse to allow subsequent messages
                self._buffer = ""
                return result
        except Exception:
            return None
        return None

    def finalize(self) -> ParsingResult:
        # If we have previous successful results and no buffer, return the last one
        if not self._buffer and self._partial_results:
            return self._partial_results[-1]
        # Attempt to parse whatever is currently in the buffer
        if not self._buffer:
            return ParsingResult(success=False, raw_output="")
        return self.parse_with_retry(self._buffer)

    def reset(self) -> None:
        self._buffer = ""
        self._partial_results.clear()


def create_parser(
    pydantic_model: Type[BaseModel], streaming: bool = False, **kwargs: Any
) -> RetryingPydanticOutputParser:
    """Factory to create our retrying parser; also returns streaming-compatible parser."""
    if streaming:
        return StreamingOutputParser(pydantic_object=pydantic_model, **kwargs)
    return RetryingPydanticOutputParser(pydantic_object=pydantic_model, **kwargs)


__all__ = [
    "ParsingResult",
    "RetryingPydanticOutputParser",
    "StreamingOutputParser",
    "OutputFormat",
    "create_parser",
]
