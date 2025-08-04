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