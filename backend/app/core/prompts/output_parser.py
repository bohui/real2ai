"""
Advanced Output Parsing System for PromptManager
Provides structured output parsing with Pydantic validation and automatic format instruction generation
"""

import json
import re
import logging
from typing import TypeVar, Generic, Dict, Any, Type, Optional, Union, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

from .exceptions import PromptTemplateError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OutputFormat(str, Enum):
    """Supported output formats"""

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


class BaseOutputParser(Generic[T], ABC):
    """Base class for structured output parsing with automatic format instruction generation"""

    def __init__(
        self,
        pydantic_model: Type[T],
        output_format: OutputFormat = OutputFormat.JSON,
        strict_mode: bool = True,
        retry_on_failure: bool = True,
        max_retries: int = 2,
    ):
        self.pydantic_model = pydantic_model
        self.output_format = output_format
        self.strict_mode = strict_mode
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries

        # Cache format instructions for performance
        self._cached_instructions: Optional[str] = None

        logger.debug(
            f"Initialized {self.__class__.__name__} for {pydantic_model.__name__}"
        )

    def get_format_instructions(self) -> str:
        """Generate format instructions from Pydantic schema

        Returns:
            Human-readable format instructions for AI models
        """
        if self._cached_instructions is None:
            self._cached_instructions = self._generate_format_instructions()

        return self._cached_instructions

    @abstractmethod
    def parse(self, text: str) -> ParsingResult:
        """Parse AI output into Pydantic model

        Args:
            text: Raw AI output text

        Returns:
            ParsingResult with parsed data or error information
        """
        pass

    def parse_with_retry(self, text: str) -> ParsingResult:
        """Parse with automatic retry on failure

        Args:
            text: Raw AI output text

        Returns:
            ParsingResult with final parsing attempt
        """
        result = self.parse(text)

        if not result.success and self.retry_on_failure:
            # Try to fix common parsing issues
            for attempt in range(self.max_retries):
                try:
                    fixed_text = self._attempt_text_fix(text, attempt + 1)
                    if fixed_text != text:
                        logger.debug(
                            f"Retry attempt {attempt + 1}: applying text fixes"
                        )
                        result = self.parse(fixed_text)
                        if result.success:
                            break
                except Exception as e:
                    logger.warning(f"Retry attempt {attempt + 1} failed: {e}")

        return result

    def _generate_format_instructions(self) -> str:
        """Generate human-readable format instructions from Pydantic schema"""
        schema = self.pydantic_model.model_json_schema()

        if self.output_format == OutputFormat.JSON:
            return self._generate_json_instructions(schema)
        elif self.output_format == OutputFormat.YAML:
            return self._generate_yaml_instructions(schema)
        else:
            return self._generate_generic_instructions(schema)

    def _generate_json_instructions(self, schema: Dict[str, Any]) -> str:
        """Generate JSON-specific format instructions"""
        model_name = self.pydantic_model.__name__

        instructions = [
            f"# Output Format Instructions",
            f"",
            f"You must return your response as a valid JSON object that follows the {model_name} schema.",
            f"",
            f"## Required Format:",
            f"```json",
            self._schema_to_example_json(schema),
            f"```",
            f"",
            f"## Schema Requirements:",
        ]

        # Add field descriptions
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        for field_name, field_schema in properties.items():
            is_required = field_name in required_fields
            field_type = field_schema.get("type", "unknown")
            description = field_schema.get("description", "No description provided")

            status = "REQUIRED" if is_required else "OPTIONAL"
            instructions.append(
                f"- `{field_name}` ({field_type}) - [{status}] {description}"
            )

        instructions.extend(
            [
                f"",
                f"## Important Rules:",
                f"- Return ONLY the JSON object, no additional text or explanation",
                f"- Ensure all required fields are present",
                f"- Use proper JSON syntax with double quotes for strings",
                f"- Do not include comments or trailing commas",
                f"- Validate that your response is parseable JSON",
            ]
        )

        if not self.strict_mode:
            instructions.append("- Additional fields beyond the schema are allowed")

        return "\n".join(instructions)

    def _generate_yaml_instructions(self, schema: Dict[str, Any]) -> str:
        """Generate YAML-specific format instructions"""
        # Similar to JSON but for YAML format
        return f"Return response as valid YAML following {self.pydantic_model.__name__} schema"

    def _generate_generic_instructions(self, schema: Dict[str, Any]) -> str:
        """Generate generic format instructions"""
        return f"Return structured data following {self.pydantic_model.__name__} schema"

    def _schema_to_example_json(self, schema: Dict[str, Any]) -> str:
        """Convert JSON schema to example JSON"""
        try:
            example = self._generate_example_from_schema(schema)
            return json.dumps(example, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to generate example JSON: {e}")
            return '{"error": "Could not generate example"}'

    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate example data structure from JSON schema"""
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        example = {}

        for field_name, field_schema in properties.items():
            field_type = field_schema.get("type")
            field_description = field_schema.get("description", "")

            if field_type == "string":
                if "date" in field_name.lower() or "timestamp" in field_name.lower():
                    example[field_name] = "2024-01-01T00:00:00Z"
                elif field_description:
                    example[field_name] = (
                        f"<{field_description.lower().replace(' ', '_')}>"
                    )
                else:
                    example[field_name] = f"<{field_name}>"

            elif field_type == "integer":
                example[field_name] = 0

            elif field_type == "number":
                example[field_name] = 0.0

            elif field_type == "boolean":
                example[field_name] = False

            elif field_type == "array":
                items_schema = field_schema.get("items", {})
                if items_schema.get("type") == "string":
                    example[field_name] = ["<example_item>"]
                elif items_schema.get("type") == "object":
                    example[field_name] = [
                        self._generate_example_from_schema(items_schema)
                    ]
                else:
                    example[field_name] = []

            elif field_type == "object":
                if "properties" in field_schema:
                    example[field_name] = self._generate_example_from_schema(
                        field_schema
                    )
                else:
                    example[field_name] = {}

            else:
                example[field_name] = None

        return example

    def _attempt_text_fix(self, text: str, attempt: int) -> str:
        """Attempt to fix common parsing issues in AI output"""
        fixed_text = text

        if attempt == 1:
            # Remove common prefixes/suffixes
            fixed_text = re.sub(
                r"^.*?```json\s*", "", fixed_text, flags=re.MULTILINE | re.DOTALL
            )
            fixed_text = re.sub(
                r"```\s*$", "", fixed_text, flags=re.MULTILINE | re.DOTALL
            )
            fixed_text = fixed_text.strip()

        elif attempt == 2:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_match:
                fixed_text = json_match.group(1)

        return fixed_text


class PydanticOutputParser(BaseOutputParser[T]):
    """JSON-based Pydantic output parser with robust error handling"""

    def parse(self, text: str) -> ParsingResult:
        """Parse JSON output into Pydantic model

        Args:
            text: Raw AI output containing JSON

        Returns:
            ParsingResult with parsed model or error details
        """
        result = ParsingResult(success=False, raw_output=text)

        try:
            # Extract JSON from text
            json_data = self._extract_json(text)

            if json_data is None:
                result.parsing_errors.append("No valid JSON found in output")
                return result

            # Validate with Pydantic
            try:
                parsed_model = self.pydantic_model(**json_data)
                result.success = True
                result.parsed_data = parsed_model
                result.confidence_score = self._calculate_confidence_score(json_data)

                logger.debug(f"Successfully parsed {self.pydantic_model.__name__}")

            except ValidationError as e:
                result.validation_errors = [str(error) for error in e.errors()]
                logger.warning(
                    f"Validation failed for {self.pydantic_model.__name__}: {result.validation_errors}"
                )

                if not self.strict_mode:
                    # Try partial parsing in non-strict mode
                    try:
                        partial_data = self._attempt_partial_parsing(json_data, e)
                        if partial_data:
                            result.parsed_data = partial_data
                            result.success = True
                            result.confidence_score = (
                                0.5  # Lower confidence for partial parsing
                            )
                    except Exception as partial_error:
                        result.parsing_errors.append(
                            f"Partial parsing failed: {partial_error}"
                        )

        except Exception as e:
            result.parsing_errors.append(f"Unexpected parsing error: {str(e)}")
            logger.error(
                f"Unexpected error parsing {self.pydantic_model.__name__}: {e}"
            )

        return result

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from text with multiple strategies"""
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from code blocks
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find JSON-like structures
        brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(brace_pattern, text, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Strategy 4: Clean and retry
        cleaned_text = self._clean_json_text(text)
        if cleaned_text != text:
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass

        return None

    def _clean_json_text(self, text: str) -> str:
        """Clean common JSON formatting issues"""
        # Remove common prefixes and suffixes
        text = re.sub(r"^[^{]*", "", text)
        text = re.sub(r"[^}]*$", "", text)

        # Fix trailing commas
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        # Fix quote issues
        text = re.sub(
            r"'([^']*)':", r'"\1":', text
        )  # Single quotes to double quotes for keys

        return text.strip()

    def _calculate_confidence_score(self, json_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on parsed data completeness"""
        schema = self.pydantic_model.model_json_schema()
        required_fields = set(schema.get("required", []))
        properties = schema.get("properties", {})

        if not required_fields:
            return 1.0

        present_required = sum(
            1 for field in required_fields if json_data.get(field) is not None
        )
        total_fields = len(properties)
        present_fields = sum(
            1 for field in properties if json_data.get(field) is not None
        )

        # Weight required fields more heavily
        required_score = (
            present_required / len(required_fields) if required_fields else 1.0
        )
        completeness_score = present_fields / total_fields if total_fields else 1.0

        return required_score * 0.8 + completeness_score * 0.2

    def _attempt_partial_parsing(
        self, json_data: Dict[str, Any], validation_error: ValidationError
    ) -> Optional[T]:
        """Attempt to create partial model with available valid data"""
        schema = self.pydantic_model.model_json_schema()
        required_fields = set(schema.get("required", []))

        # Filter out invalid fields
        valid_data = {}
        for field_name, value in json_data.items():
            if field_name in schema.get("properties", {}):
                valid_data[field_name] = value

        # Add default values for missing required fields
        for field_name in required_fields:
            if field_name not in valid_data:
                field_info = schema["properties"].get(field_name, {})
                field_type = field_info.get("type")

                if field_type == "string":
                    valid_data[field_name] = ""
                elif field_type == "integer":
                    valid_data[field_name] = 0
                elif field_type == "number":
                    valid_data[field_name] = 0.0
                elif field_type == "boolean":
                    valid_data[field_name] = False
                elif field_type == "array":
                    valid_data[field_name] = []
                elif field_type == "object":
                    valid_data[field_name] = {}

        try:
            return self.pydantic_model(**valid_data)
        except ValidationError:
            return None


class StreamingOutputParser(PydanticOutputParser[T]):
    """Parser for streaming/incremental output parsing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer = ""
        self._partial_results: List[ParsingResult] = []

    def parse_chunk(self, chunk: str) -> Optional[ParsingResult]:
        """Parse incremental chunk of streaming output"""
        self._buffer += chunk

        # Try to parse if we have what looks like complete JSON
        if self._buffer.count("{") > 0 and self._buffer.count(
            "{"
        ) == self._buffer.count("}"):
            result = self.parse(self._buffer)
            if result.success:
                self._partial_results.append(result)
                return result

        return None

    def finalize(self) -> ParsingResult:
        """Finalize parsing and return best result"""
        if self._partial_results:
            # Return the result with highest confidence
            return max(self._partial_results, key=lambda r: r.confidence_score)

        # Try final parse with full buffer
        return self.parse(self._buffer)

    def reset(self):
        """Reset parser state for reuse"""
        self._buffer = ""
        self._partial_results.clear()


# Factory functions for easy parser creation
def create_parser(
    pydantic_model: Type[T],
    output_format: OutputFormat = OutputFormat.JSON,
    streaming: bool = False,
    **kwargs,
) -> BaseOutputParser[T]:
    """Factory function to create appropriate parser"""
    if streaming:
        return StreamingOutputParser(pydantic_model, output_format, **kwargs)
    else:
        return PydanticOutputParser(pydantic_model, output_format, **kwargs)


# Export main classes and functions
__all__ = [
    "BaseOutputParser",
    "PydanticOutputParser",
    "StreamingOutputParser",
    "ParsingResult",
    "OutputFormat",
    "create_parser",
]

# Import state-aware parser for convenience
try:
    from .state_aware_parser import (
        StateAwareParser,
        StateAwareParserFactory,
        create_state_aware_parser,
    )

    __all__.extend(
        ["StateAwareParser", "StateAwareParserFactory", "create_state_aware_parser"]
    )
except ImportError:
    # State-aware parser not available
    pass
