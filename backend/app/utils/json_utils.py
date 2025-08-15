"""
JSON utility functions for safe parsing and handling of JSON data.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def safe_json_loads(value: Any, default: Optional[Any] = None) -> Optional[Any]:
    """
    Safely parse JSON string to Python object with fallback to default.
    
    Args:
        value: The value to parse (can be string, dict, or None)
        default: Default value to return if parsing fails
        
    Returns:
        Parsed JSON object, original dict if already parsed, or default value
    """
    if value is None:
        return default
    if isinstance(value, dict):
        return value  # Already a dict, return as-is
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON string: {value}")
            return default
    return default
