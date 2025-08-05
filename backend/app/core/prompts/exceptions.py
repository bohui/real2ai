"""Custom exceptions for the prompt management system"""


class PromptError(Exception):
    """Base exception for prompt management errors"""
    
    def __init__(self, message: str, prompt_id: str = None, details: dict = None):
        super().__init__(message)
        self.prompt_id = prompt_id
        self.details = details or {}


class PromptNotFoundError(PromptError):
    """Raised when a requested prompt cannot be found"""
    pass


class PromptValidationError(PromptError):
    """Raised when prompt validation fails"""
    pass


class PromptTemplateError(PromptError):
    """Raised when prompt template processing fails"""
    pass


class PromptVersionError(PromptError):
    """Raised when prompt version is invalid or incompatible"""
    pass


class PromptLoadError(PromptError):
    """Raised when prompt loading fails"""
    pass


class PromptContextError(PromptError):
    """Raised when prompt context is invalid or incomplete"""
    pass


class PromptCompositionError(PromptError):
    """Raised when prompt composition fails"""
    
    def __init__(self, message: str, composition_name: str = None, details: dict = None):
        super().__init__(message, prompt_id=composition_name, details=details)
        self.composition_name = composition_name
