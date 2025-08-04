"""
Base client infrastructure for external service integrations.
"""

from .client import BaseClient, ClientConfig
from .exceptions import (
    ClientError,
    ClientConnectionError,
    ClientAuthenticationError,
    ClientRateLimitError,
    ClientTimeoutError,
    ClientValidationError,
)
from .interfaces import DatabaseOperations, AIOperations, AuthOperations

__all__ = [
    "BaseClient",
    "ClientConfig", 
    "DatabaseOperations",
    "AIOperations",
    "AuthOperations",
    "ClientError",
    "ClientConnectionError",
    "ClientAuthenticationError", 
    "ClientRateLimitError",
    "ClientTimeoutError",
    "ClientValidationError",
]