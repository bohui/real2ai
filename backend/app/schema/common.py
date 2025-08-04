"""Common schemas used across the API."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now(timezone.utc)


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    invalid_value: Any


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "Validation Error"
    detail: str
    validation_errors: List[ValidationError]
    timestamp: datetime = datetime.now(timezone.utc)


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = datetime.now(timezone.utc)
    version: str = "1.0.0"
    environment: str
    services: Dict[str, str] = {}


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]


class SystemStatsResponse(BaseModel):
    """System statistics response"""
    total_documents_processed: int
    total_analyses_completed: int
    average_processing_time: float
    success_rate: float
    active_users: int