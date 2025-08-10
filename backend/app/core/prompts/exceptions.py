"""
Prompt Management System Exceptions
Comprehensive error handling for the prompt management system
"""

from typing import Dict, Any, Optional, List
from enum import Enum


class PromptErrorSeverity(Enum):
    """Error severity levels for prompt management"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptError(Exception):
    """Base exception for prompt management errors"""

    def __init__(
        self,
        message: str,
        prompt_id: str = None,
        severity: PromptErrorSeverity = PromptErrorSeverity.MEDIUM,
        details: Dict[str, Any] = None,
        recovery_suggestions: List[str] = None,
    ):
        self.message = message
        self.prompt_id = prompt_id
        self.severity = severity
        self.details = details or {}
        self.recovery_suggestions = recovery_suggestions or []

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "prompt_id": self.prompt_id,
            "severity": self.severity.value,
            "details": self.details,
            "recovery_suggestions": self.recovery_suggestions,
        }


class PromptNotFoundError(PromptError):
    """Raised when a requested prompt template is not found"""

    def __init__(
        self,
        message: str,
        prompt_id: str = None,
        available_prompts: List[str] = None,
        **kwargs,
    ):
        self.available_prompts = available_prompts or []

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Check template name spelling",
                "Verify template exists in prompts directory",
                "Use list_templates() to see available prompts",
            ]
            if available_prompts:
                recovery_suggestions.append(
                    f"Available templates: {', '.join(available_prompts[:5])}"
                )

        super().__init__(
            message=message,
            prompt_id=prompt_id,
            severity=PromptErrorSeverity.HIGH,
            recovery_suggestions=recovery_suggestions,
            **kwargs,
        )


class PromptValidationError(PromptError):
    """Raised when prompt validation fails"""

    def __init__(
        self,
        message: str,
        prompt_id: str = None,
        validation_errors: List[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.validation_errors = validation_errors or []

        details = kwargs.get("details", {})
        details["validation_errors"] = self.validation_errors

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Check template syntax and structure",
                "Verify all required variables are provided",
                "Review validation error details",
                "Use validate_template() to test before rendering",
            ]

        # Remove keys that are passed explicitly to avoid duplicates
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["details", "recovery_suggestions"]
        }

        super().__init__(
            message=message,
            prompt_id=prompt_id,
            severity=PromptErrorSeverity.HIGH,
            details=details,
            recovery_suggestions=recovery_suggestions,
            **filtered_kwargs,
        )


class PromptTemplateError(PromptError):
    """Raised when prompt template processing fails"""

    pass


class PromptVersionError(PromptError):
    """Raised when there are prompt version conflicts or issues"""

    def __init__(
        self,
        message: str,
        prompt_id: str = None,
        requested_version: str = None,
        available_versions: List[str] = None,
        **kwargs,
    ):
        self.requested_version = requested_version
        self.available_versions = available_versions or []

        details = kwargs.get("details", {})
        details.update(
            {
                "requested_version": requested_version,
                "available_versions": self.available_versions,
            }
        )

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Use latest version by omitting version parameter",
                "Check available versions with get_template_info()",
            ]
            if available_versions:
                recovery_suggestions.append(
                    f"Available versions: {', '.join(available_versions)}"
                )

        # Remove details from kwargs to avoid duplicate parameter
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["details", "recovery_suggestions"]
        }

        super().__init__(
            message=message,
            prompt_id=prompt_id,
            severity=PromptErrorSeverity.MEDIUM,
            details=details,
            recovery_suggestions=recovery_suggestions,
            **filtered_kwargs,
        )


class PromptLoadError(PromptError):
    """Raised when prompt loading fails"""

    pass


class PromptContextError(PromptError):
    """Raised when there are issues with prompt context"""

    def __init__(
        self,
        message: str,
        prompt_id: str = None,
        missing_variables: List[str] = None,
        invalid_variables: List[str] = None,
        **kwargs,
    ):
        self.missing_variables = missing_variables or []
        self.invalid_variables = invalid_variables or []

        details = kwargs.get("details", {})
        details.update(
            {
                "missing_variables": self.missing_variables,
                "invalid_variables": self.invalid_variables,
            }
        )

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Provide all required context variables",
                "Check variable types and formats",
                "Use create_context() helper methods",
            ]
            if missing_variables:
                recovery_suggestions.append(
                    f"Missing variables: {', '.join(missing_variables)}"
                )

        # Remove keys that are passed explicitly to avoid duplicates
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["details", "recovery_suggestions"]
        }

        super().__init__(
            message=message,
            prompt_id=prompt_id,
            severity=PromptErrorSeverity.HIGH,
            details=details,
            recovery_suggestions=recovery_suggestions,
            **filtered_kwargs,
        )


class PromptCompositionError(PromptError):
    """Raised when prompt composition fails"""

    def __init__(
        self,
        message: str,
        composition_name: str = None,
        failed_templates: List[str] = None,
        **kwargs,
    ):
        self.composition_name = composition_name
        self.failed_templates = failed_templates or []

        details = kwargs.get("details", {})
        details.update(
            {
                "composition_name": composition_name,
                "failed_templates": self.failed_templates,
            }
        )

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Check composition configuration",
                "Verify all referenced templates exist",
                "Use validate_composition() to test",
            ]
            if failed_templates:
                recovery_suggestions.append(
                    f"Failed templates: {', '.join(failed_templates)}"
                )

        # Remove keys that are passed explicitly to avoid duplicates
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["details", "recovery_suggestions"]
        }

        super().__init__(
            message=message,
            prompt_id=composition_name,
            severity=PromptErrorSeverity.HIGH,
            details=details,
            recovery_suggestions=recovery_suggestions,
            **filtered_kwargs,
        )


class PromptServiceError(PromptError):
    """Raised when service-level prompt operations fail"""

    def __init__(
        self,
        message: str,
        service_name: str = None,
        template_name: str = None,
        composition_name: str = None,
        **kwargs,
    ):
        self.service_name = service_name
        self.template_name = template_name
        self.composition_name = composition_name

        prompt_id = template_name or composition_name

        details = kwargs.get("details", {})
        details.update(
            {
                "service_name": service_name,
                "template_name": template_name,
                "composition_name": composition_name,
            }
        )

        recovery_suggestions = kwargs.get("recovery_suggestions", [])
        if not recovery_suggestions:
            recovery_suggestions = [
                "Check service configuration",
                "Verify PromptManager initialization",
                "Review service-specific prompt requirements",
                "Check service logs for detailed error information",
            ]

        # Remove details from kwargs to avoid duplicate parameter
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["details", "recovery_suggestions"]
        }

        super().__init__(
            message=message,
            prompt_id=prompt_id,
            severity=PromptErrorSeverity.MEDIUM,
            details=details,
            recovery_suggestions=recovery_suggestions,
            **filtered_kwargs,
        )


# Exception handler decorators and utilities


def handle_prompt_errors(func):
    """Decorator to standardize prompt error handling"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PromptError:
            # Re-raise prompt management errors as-is
            raise
        except Exception as e:
            # Convert other exceptions to PromptError
            raise PromptError(
                message=f"Unexpected error in {func.__name__}: {str(e)}",
                severity=PromptErrorSeverity.HIGH,
                details={"original_error": type(e).__name__},
            ) from e

    return wrapper


def create_error_context(
    error: PromptError, additional_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create standardized error context for logging and monitoring"""
    context = error.to_dict()

    if additional_context:
        context["additional_context"] = additional_context

    return context
