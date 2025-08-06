"""
External Service Clients Package

This package provides a clean, decoupled architecture for all external service integrations.
Follows SOLID principles and provides consistent interfaces for testing and maintainability.
"""

from .factory import ClientFactory, get_client_factory, get_supabase_client, get_service_supabase_client, get_gemini_client, get_openai_client
from .base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientAuthenticationError,
    ClientRateLimitError,
    ClientTimeoutError,
    ClientValidationError,
)

__all__ = [
    "ClientFactory",
    "get_client_factory",
    "get_supabase_client",
    "get_service_supabase_client",
    "get_gemini_client", 
    "get_openai_client",
    "ClientError",
    "ClientConnectionError", 
    "ClientAuthenticationError",
    "ClientRateLimitError",
    "ClientTimeoutError",
    "ClientValidationError",
]