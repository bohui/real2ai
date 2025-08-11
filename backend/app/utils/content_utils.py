"""
Content processing utilities for document artifacts
"""

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

from app.core.config import get_settings


def compute_content_hmac(file_bytes: bytes, secret_key: Optional[str] = None) -> str:
    """
    Compute HMAC-SHA256 over raw file bytes for content addressing.
    
    Args:
        file_bytes: Raw file bytes
        secret_key: HMAC secret key (uses config default if not provided)
        
    Returns:
        Hexadecimal HMAC-SHA256 string
        
    Raises:
        ValueError: If secret key is not configured or provided
    """
    if secret_key is None:
        settings = get_settings()
        secret_key = settings.document_hmac_secret
        
    if not secret_key:
        raise ValueError(
            "Document HMAC secret not configured. Set DOCUMENT_HMAC_SECRET environment variable."
        )
    
    return hmac.new(
        secret_key.encode('utf-8'),
        file_bytes,
        hashlib.sha256
    ).hexdigest()


def compute_params_fingerprint(params: Dict[str, Any]) -> str:
    """
    Compute deterministic fingerprint of processing parameters.
    
    Args:
        params: Processing parameters dictionary
        
    Returns:
        SHA256 hash of sorted JSON representation
    """
    # Sort keys recursively to ensure deterministic ordering
    def sort_dict(obj):
        if isinstance(obj, dict):
            return {k: sort_dict(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [sort_dict(item) for item in obj]
        else:
            return obj
    
    sorted_params = sort_dict(params)
    params_json = json.dumps(sorted_params, separators=(',', ':'), ensure_ascii=True)
    
    return hashlib.sha256(params_json.encode('utf-8')).hexdigest()


def get_artifact_key(
    content_hmac: str, 
    algorithm_version: int, 
    params_fingerprint: str
) -> tuple[str, int, str]:
    """
    Get complete artifact key tuple.
    
    Args:
        content_hmac: Content HMAC
        algorithm_version: Processing algorithm version
        params_fingerprint: Processing parameters fingerprint
        
    Returns:
        Tuple of (content_hmac, algorithm_version, params_fingerprint)
    """
    return (content_hmac, algorithm_version, params_fingerprint)


def validate_content_hmac(content_hmac: str) -> bool:
    """
    Validate that content HMAC is properly formatted.
    
    Args:
        content_hmac: HMAC string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not content_hmac or not isinstance(content_hmac, str):
        return False
        
    # HMAC-SHA256 produces 64 character hex string
    if len(content_hmac) != 64:
        return False
        
    # Check if all characters are valid hexadecimal
    try:
        int(content_hmac, 16)
        return True
    except ValueError:
        return False


def validate_params_fingerprint(params_fingerprint: str) -> bool:
    """
    Validate that params fingerprint is properly formatted.
    
    Args:
        params_fingerprint: Fingerprint string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not params_fingerprint or not isinstance(params_fingerprint, str):
        return False
        
    # SHA256 produces 64 character hex string
    if len(params_fingerprint) != 64:
        return False
        
    # Check if all characters are valid hexadecimal
    try:
        int(params_fingerprint, 16)
        return True
    except ValueError:
        return False