"""
Custom exceptions for external service clients.
"""

class ClientError(Exception):
    """Base exception for all client-related errors."""
    
    def __init__(self, message: str, client_name: str = None, original_error: Exception = None):
        self.message = message
        self.client_name = client_name
        self.original_error = original_error
        super().__init__(message)
    
    def __str__(self):
        error_msg = self.message
        if self.client_name:
            error_msg = f"[{self.client_name}] {error_msg}"
        if self.original_error:
            error_msg += f" (Original: {str(self.original_error)})"
        return error_msg


class ClientConnectionError(ClientError):
    """Raised when client cannot connect to external service."""
    pass


class ClientAuthenticationError(ClientError):
    """Raised when client authentication fails."""
    pass


class ClientRateLimitError(ClientError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class ClientTimeoutError(ClientError):
    """Raised when client request times out."""
    
    def __init__(self, message: str, timeout_duration: float = None, **kwargs):
        self.timeout_duration = timeout_duration
        super().__init__(message, **kwargs)


class ClientValidationError(ClientError):
    """Raised when client request validation fails."""
    
    def __init__(self, message: str, validation_errors: dict = None, **kwargs):
        self.validation_errors = validation_errors or {}
        super().__init__(message, **kwargs)


class ClientQuotaExceededError(ClientError):
    """Raised when API quota is exceeded."""
    
    def __init__(self, message: str, quota_limit: int = None, current_usage: int = None, **kwargs):
        self.quota_limit = quota_limit
        self.current_usage = current_usage
        super().__init__(message, **kwargs)


class ClientServiceUnavailableError(ClientError):
    """Raised when external service is unavailable."""
    pass


# Property-specific exceptions

class PropertyAPIError(ClientError):
    """Base exception for property API errors."""
    pass


class PropertyNotFoundError(PropertyAPIError):
    """Raised when property cannot be found."""
    
    def __init__(self, address: str, **kwargs):
        self.address = address
        message = f"Property not found: {address}"
        super().__init__(message, **kwargs)


class PropertyDataIncompleteError(PropertyAPIError):
    """Raised when property data is incomplete or insufficient."""
    
    def __init__(self, address: str, missing_fields: list = None, **kwargs):
        self.address = address
        self.missing_fields = missing_fields or []
        message = f"Incomplete property data for: {address}"
        if self.missing_fields:
            message += f" (Missing: {', '.join(self.missing_fields)})"
        super().__init__(message, **kwargs)


class PropertyValuationError(PropertyAPIError):
    """Raised when property valuation fails or is unavailable."""
    
    def __init__(self, address: str, reason: str = None, **kwargs):
        self.address = address
        self.reason = reason
        message = f"Property valuation failed for: {address}"
        if reason:
            message += f" (Reason: {reason})"
        super().__init__(message, **kwargs)


class InvalidPropertyAddressError(PropertyAPIError):
    """Raised when property address is invalid or cannot be geocoded."""
    
    def __init__(self, address: str, suggestion: str = None, **kwargs):
        self.address = address
        self.suggestion = suggestion
        message = f"Invalid property address: {address}"
        if suggestion:
            message += f" (Suggestion: {suggestion})"
        super().__init__(message, **kwargs)


class PropertyDataValidationError(PropertyAPIError):
    """Raised when property data fails validation checks."""
    
    def __init__(self, address: str, validation_issues: list = None, **kwargs):
        self.address = address
        self.validation_issues = validation_issues or []
        message = f"Property data validation failed for: {address}"
        if self.validation_issues:
            issues = ', '.join([issue['message'] for issue in self.validation_issues])
            message += f" (Issues: {issues})"
        super().__init__(message, **kwargs)


class DomainAPIError(PropertyAPIError):
    """Raised for Domain API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, **kwargs):
        self.status_code = status_code
        super().__init__(message, client_name="Domain API", **kwargs)


class CoreLogicAPIError(PropertyAPIError):
    """Raised for CoreLogic API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, **kwargs):
        self.status_code = status_code
        super().__init__(message, client_name="CoreLogic API", **kwargs)


class PropertyCacheError(PropertyAPIError):
    """Raised for property cache related errors."""
    pass


class PropertyRateLimitError(ClientRateLimitError):
    """Raised when property API rate limits are exceeded."""
    
    def __init__(self, api_name: str, message: str = None, **kwargs):
        self.api_name = api_name
        if not message:
            message = f"{api_name} rate limit exceeded"
        super().__init__(message, client_name=api_name, **kwargs)