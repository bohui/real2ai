"""User management schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class UsageStatsResponse(BaseModel):
    """User usage statistics response"""
    credits_remaining: int
    subscription_status: str
    total_contracts_analyzed: int
    current_month_usage: int
    recent_analyses: List[Dict[str, Any]]
    usage_trend: Optional[Dict[str, Any]] = None