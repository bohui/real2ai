"""Comprehensive prompt validation and quality assurance"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, UTC

from .template import PromptTemplate
from .context import PromptContext
from .exceptions import PromptValidationError

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue"""

    severity: ValidationSeverity
    code: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    context: Dict[str, Any] = None


@dataclass
class ValidationResult:
    """Result of prompt validation"""

    is_valid: bool
    issues: List[ValidationIssue]
    score: float  # 0.0 to 1.0
    metrics: Dict[str, Any]
    validated_at: datetime

    @property
    def has_errors(self) -> bool:
        """Check if result has any errors or critical issues"""
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )

    @property
    def has_warnings(self) -> bool:
        """Check if result has any warnings"""
        return any(
            issue.severity == ValidationSeverity.WARNING for issue in self.issues
        )


class PromptValidator:
    """Comprehensive prompt validator with quality scoring"""

    def __init__(self):
        # Quality thresholds
        self.min_description_length = 10
        self.max_template_length = 50000  # ~12.5K tokens
        self.min_template_length = 50
        self.max_variable_count = 50

        # Pattern validators
        self.security_patterns = [
            (r"eval\s*\(", "Potential code injection risk"),
            (r"exec\s*\(", "Potential code execution risk"),
            (r"import\s+os", "OS module import detected"),
            (r"__[a-zA-Z_]+__", "Python dunder methods detected"),
        ]

        self.quality_patterns = [
            (r"\b(please|kindly)\b", "Avoid politeness markers in system prompts"),
            (r"\b(um|uh|well)\b", "Remove filler words"),
            (r"(?i)\b(i think|i believe|maybe|perhaps)\b", "Use definitive language"),
            (r"\?{2,}", "Avoid multiple question marks"),
            (r"!{2,}", "Avoid multiple exclamation marks"),
        ]

        self.australian_legal_terms = [
            "vendor",
            "purchaser",
            "settlement",
            "completion",
            "exchange",
            "cooling-off",
            "rescission",
            "deposit",
            "title",
            "caveat",
            "encumbrance",
            "easement",
            "covenant",
            "strata",
            "body corporate",
        ]

        # Model-specific limits
        self.model_limits = {
            "gemini-2.5-flash": {"max_tokens": 32000, "context_window": 128000},
            "gpt-4": {"max_tokens": 8000, "context_window": 32000},
            "gpt-3.5-turbo": {"max_tokens": 4000, "context_window": 16000},
        }

    def validate_template(self, template: PromptTemplate) -> ValidationResult:
        """Comprehensive template validation"""
        issues = []
        metrics = {}

        # Basic structure validation
        issues.extend(self._validate_structure(template))

        # Metadata validation
        issues.extend(self._validate_metadata(template))

        # Content validation
        content_issues, content_metrics = self._validate_content(template)
        issues.extend(content_issues)
        metrics.update(content_metrics)

        # Template syntax validation
        issues.extend(self._validate_template_syntax(template))

        # Security validation
        issues.extend(self._validate_security(template))

        # Quality validation
        quality_issues, quality_metrics = self._validate_quality(template)
        issues.extend(quality_issues)
        metrics.update(quality_metrics)

        # Model compatibility
        issues.extend(self._validate_model_compatibility(template))

        # Calculate score
        score = self._calculate_score(issues, metrics)

        return ValidationResult(
            is_valid=not any(
                issue.severity
                in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                for issue in issues
            ),
            issues=issues,
            score=score,
            metrics=metrics,
            validated_at=datetime.now(UTC),
        )

    def validate_context(
        self, context: PromptContext, required_vars: List[str]
    ) -> ValidationResult:
        """Validate prompt context"""
        issues = []
        metrics = {}

        # Check required variables
        context_dict = context.to_dict()
        missing_vars = []

        for var in required_vars:
            if var not in context_dict or context_dict[var] is None:
                missing_vars.append(var)

        if missing_vars:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_VARIABLES",
                    message=f"Missing required variables: {', '.join(missing_vars)}",
                    context={"missing_variables": missing_vars},
                )
            )

        # Check variable types
        type_issues = self._validate_variable_types(context_dict)
        issues.extend(type_issues)

        # Australian context validation
        if context.australian_state or context.contract_type:
            au_issues = self._validate_australian_context(context)
            issues.extend(au_issues)

        # Context completeness score
        completeness = len([v for v in context_dict.values() if v is not None]) / max(
            len(required_vars), 1
        )
        metrics["context_completeness"] = completeness
        metrics["variable_count"] = len(context_dict)

        score = self._calculate_context_score(issues, metrics)

        return ValidationResult(
            is_valid=len(missing_vars) == 0,
            issues=issues,
            score=score,
            metrics=metrics,
            validated_at=datetime.now(UTC),
        )

    def validate_rendered_prompt(
        self, rendered_prompt: str, model: str = None
    ) -> ValidationResult:
        """Validate final rendered prompt"""
        issues = []
        metrics = {}

        # Length validation
        prompt_length = len(rendered_prompt)
        metrics["prompt_length"] = prompt_length
        metrics["estimated_tokens"] = prompt_length // 4  # Rough estimation

        if prompt_length < self.min_template_length:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="PROMPT_TOO_SHORT",
                    message=f"Prompt is very short ({prompt_length} chars)",
                    suggestion="Consider adding more context or instructions",
                )
            )

        if prompt_length > self.max_template_length:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PROMPT_TOO_LONG",
                    message=f"Prompt exceeds maximum length ({prompt_length} chars)",
                    suggestion="Consider breaking into smaller prompts or reducing content",
                )
            )

        # Model-specific validation
        if model and model in self.model_limits:
            model_limit = self.model_limits[model]
            estimated_tokens = metrics["estimated_tokens"]

            if estimated_tokens > model_limit["max_tokens"]:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="EXCEEDS_MODEL_LIMIT",
                        message=f"Prompt exceeds {model} token limit ({estimated_tokens} > {model_limit['max_tokens']})",
                        suggestion=f"Reduce prompt length or use a model with larger context window",
                    )
                )

        # Content quality checks
        quality_issues, quality_metrics = self._validate_rendered_content(
            rendered_prompt
        )
        issues.extend(quality_issues)
        metrics.update(quality_metrics)

        score = self._calculate_rendered_score(issues, metrics)

        return ValidationResult(
            is_valid=not any(
                issue.severity
                in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                for issue in issues
            ),
            issues=issues,
            score=score,
            metrics=metrics,
            validated_at=datetime.now(UTC),
        )

    def _validate_structure(self, template: PromptTemplate) -> List[ValidationIssue]:
        """Validate basic template structure"""
        issues = []

        if not template.content:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="EMPTY_TEMPLATE",
                    message="Template content is empty",
                )
            )

        if not template.metadata:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_METADATA",
                    message="Template metadata is missing",
                )
            )

        return issues

    def _validate_metadata(self, template: PromptTemplate) -> List[ValidationIssue]:
        """Validate template metadata"""
        issues = []
        metadata = template.metadata

        if not metadata.name:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_NAME",
                    message="Template name is required",
                )
            )

        if (
            not metadata.description
            or len(metadata.description) < self.min_description_length
        ):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INSUFFICIENT_DESCRIPTION",
                    message="Template description is missing or too short",
                    suggestion=f"Provide description with at least {self.min_description_length} characters",
                )
            )

        if not metadata.version:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_VERSION",
                    message="Template version is missing",
                    suggestion="Add semantic version (e.g., '1.0.0')",
                )
            )

        if not metadata.required_variables:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NO_REQUIRED_VARIABLES",
                    message="No required variables specified",
                    suggestion="Define required variables for better validation",
                )
            )

        return issues

    def _validate_content(
        self, template: PromptTemplate
    ) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """Validate template content"""
        issues = []
        metrics = {}

        content = template.content
        content_length = len(content)

        metrics["content_length"] = content_length
        metrics["line_count"] = content.count("\n") + 1

        # Length checks
        if content_length > self.max_template_length:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CONTENT_TOO_LONG",
                    message=f"Template content exceeds maximum length ({content_length} chars)",
                )
            )

        if content_length < self.min_template_length:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="CONTENT_TOO_SHORT",
                    message=f"Template content is very short ({content_length} chars)",
                )
            )

        # Check for Australian legal context if applicable
        legal_term_count = 0
        for term in self.australian_legal_terms:
            if term.lower() in content.lower():
                legal_term_count += 1

        metrics["legal_terms_found"] = legal_term_count

        if "australian" in content.lower() and legal_term_count == 0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="MISSING_LEGAL_TERMS",
                    message="Australian context detected but no legal terms found",
                    suggestion="Consider adding relevant Australian legal terminology",
                )
            )

        return issues, metrics

    def _validate_template_syntax(
        self, template: PromptTemplate
    ) -> List[ValidationIssue]:
        """Validate Jinja2 template syntax"""
        issues = []

        try:
            # Try to parse the template
            template.env.parse(template.content)
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="INVALID_SYNTAX",
                    message=f"Template syntax error: {str(e)}",
                    suggestion="Fix Jinja2 template syntax errors",
                )
            )

        # Check for undefined variables in template
        variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}"
        variables_used = set(re.findall(variable_pattern, template.content))

        if template.metadata.required_variables:
            required_set = set(template.metadata.required_variables)
            unused_required = required_set - variables_used

            if unused_required:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="UNUSED_REQUIRED_VARS",
                        message=f"Required variables not used in template: {', '.join(unused_required)}",
                        suggestion="Remove unused variables from required list or use them in template",
                    )
                )

        return issues

    def _validate_security(self, template: PromptTemplate) -> List[ValidationIssue]:
        """Validate template for security issues"""
        issues = []
        content = template.content.lower()

        for pattern, message in self.security_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="SECURITY_RISK",
                        message=message,
                        suggestion="Remove potentially dangerous code patterns",
                    )
                )

        # Check for prompt injection patterns
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+the\s+above",
            r"forget\s+everything",
            r"system\s*:\s*you\s+are\s+now",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="PROMPT_INJECTION_RISK",
                        message="Potential prompt injection pattern detected",
                        suggestion="Review and sanitize template content",
                    )
                )

        return issues

    def _validate_quality(
        self, template: PromptTemplate
    ) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """Validate template quality"""
        issues = []
        metrics = {}

        content = template.content

        # Quality pattern checks
        for pattern, message in self.quality_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="QUALITY_ISSUE",
                        message=f"{message} (found: {', '.join(matches)})",
                        suggestion="Improve prompt clarity and directness",
                    )
                )

        # Readability metrics
        sentence_count = len(re.findall(r"[.!?]+", content))
        word_count = len(content.split())

        metrics["sentence_count"] = sentence_count
        metrics["word_count"] = word_count
        metrics["avg_sentence_length"] = word_count / max(sentence_count, 1)

        # Check for overly long sentences
        sentences = re.split(r"[.!?]+", content)
        long_sentences = [s for s in sentences if len(s.split()) > 30]

        if long_sentences:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="LONG_SENTENCES",
                    message=f"Found {len(long_sentences)} sentences with >30 words",
                    suggestion="Break down complex sentences for better clarity",
                )
            )

        return issues, metrics

    def _validate_model_compatibility(
        self, template: PromptTemplate
    ) -> List[ValidationIssue]:
        """Validate model compatibility"""
        issues = []

        if not template.metadata.model_compatibility:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="NO_MODEL_COMPATIBILITY",
                    message="No model compatibility specified",
                    suggestion="Specify compatible AI models",
                )
            )

        # Check token limits for specified models
        if template.metadata.model_compatibility:
            estimated_tokens = len(template.content) // 4

            for model in template.metadata.model_compatibility:
                if model in self.model_limits:
                    limit = self.model_limits[model]["max_tokens"]
                    if estimated_tokens > limit:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                code="EXCEEDS_MODEL_TOKENS",
                                message=f"Template may exceed {model} token limit ({estimated_tokens} > {limit})",
                                suggestion=f"Optimize template length for {model}",
                            )
                        )

        return issues

    def _validate_variable_types(
        self, context_dict: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate variable types in context"""
        issues = []

        # Check for None values that might cause issues
        none_vars = [k for k, v in context_dict.items() if v is None]
        if none_vars:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NULL_VARIABLES",
                    message=f"Variables with null values: {', '.join(none_vars)}",
                    suggestion="Ensure all variables have meaningful values",
                )
            )

        # Check for overly long string values
        for key, value in context_dict.items():
            if isinstance(value, str) and len(value) > 10000:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="LONG_VARIABLE_VALUE",
                        message=f"Variable '{key}' has very long value ({len(value)} chars)",
                        suggestion="Consider truncating or summarizing long content",
                    )
                )

        return issues

    def _validate_australian_context(
        self, context: PromptContext
    ) -> List[ValidationIssue]:
        """Validate Australian-specific context"""
        issues = []

        if context.australian_state and context.contract_type:
            # This is good - both are specified
            pass
        elif context.australian_state and not context.contract_type:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INCOMPLETE_AU_CONTEXT",
                    message="Australian state specified but contract type missing",
                    suggestion="Specify contract type for complete Australian context",
                )
            )
        elif context.contract_type and not context.australian_state:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INCOMPLETE_AU_CONTEXT",
                    message="Contract type specified but Australian state missing",
                    suggestion="Specify Australian state for complete context",
                )
            )

        return issues

    def _validate_rendered_content(
        self, content: str
    ) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """Validate rendered prompt content"""
        issues = []
        metrics = {}

        # Check for template artifacts
        if "{{" in content or "}}" in content:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="UNRENDERED_VARIABLES",
                    message="Template variables not properly rendered",
                    suggestion="Check template syntax and variable availability",
                )
            )

        # Check for JSON structure if expected
        if "json" in content.lower() and ("{" in content or "[" in content):
            # Try to find JSON blocks
            json_blocks = re.findall(r"\{[^{}]*\}", content)
            metrics["json_blocks_found"] = len(json_blocks)

            if json_blocks:
                import json

                for i, block in enumerate(json_blocks[:5]):  # Check first 5 blocks
                    try:
                        json.loads(block)
                    except json.JSONDecodeError:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                code="INVALID_JSON",
                                message=f"JSON block {i+1} appears malformed",
                                suggestion="Validate JSON structure in template",
                            )
                        )

        return issues, metrics

    def _calculate_score(
        self, issues: List[ValidationIssue], metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score (0.0 to 1.0)"""
        base_score = 1.0

        # Deduct points for issues
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                base_score -= 0.3
            elif issue.severity == ValidationSeverity.ERROR:
                base_score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 0.1
            elif issue.severity == ValidationSeverity.INFO:
                base_score -= 0.05

        # Bonus points for quality metrics
        if metrics.get("legal_terms_found", 0) > 0:
            base_score += 0.05

        if metrics.get("content_length", 0) > self.min_template_length:
            base_score += 0.05

        return max(0.0, min(1.0, base_score))

    def _calculate_context_score(
        self, issues: List[ValidationIssue], metrics: Dict[str, Any]
    ) -> float:
        """Calculate context quality score"""
        base_score = metrics.get("context_completeness", 0.5)

        # Deduct for issues
        for issue in issues:
            if issue.severity in [
                ValidationSeverity.ERROR,
                ValidationSeverity.CRITICAL,
            ]:
                base_score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 0.1

        return max(0.0, min(1.0, base_score))

    def _calculate_rendered_score(
        self, issues: List[ValidationIssue], metrics: Dict[str, Any]
    ) -> float:
        """Calculate rendered prompt quality score"""
        base_score = 1.0

        # Deduct for issues
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                base_score -= 0.4
            elif issue.severity == ValidationSeverity.ERROR:
                base_score -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 0.1

        # Bonus for appropriate length
        prompt_length = metrics.get("prompt_length", 0)
        if 500 <= prompt_length <= 10000:  # Sweet spot
            base_score += 0.1

        return max(0.0, min(1.0, base_score))
