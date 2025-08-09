"""Common schemas used across the API."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone


class SchemaBaseModel(BaseModel):
    """Base model that provides dict-like access compatibility.

    This allows legacy code using result["field"] while we migrate to strong types.
    """

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    # Pydantic v2 compatibility helpers for dict-like behavior
    def keys(self):
        try:
            return self.model_dump().keys()  # pydantic v2
        except Exception:
            return self.dict().keys()  # fallback

    def items(self):
        try:
            return self.model_dump().items()
        except Exception:
            return self.dict().items()

    def __iter__(self):
        try:
            return iter(self.model_dump().keys())
        except Exception:
            return iter(self.dict().keys())

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


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
