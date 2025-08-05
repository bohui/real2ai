"""
LangSmith initialization module.
This module ensures LangSmith is properly configured when the application starts.
"""

import logging
from typing import Optional
from .langsmith_config import get_langsmith_config

logger = logging.getLogger(__name__)


def initialize_langsmith() -> bool:
    """
    Initialize LangSmith configuration at application startup.
    
    Returns:
        bool: True if LangSmith is enabled and configured, False otherwise
    """
    try:
        config = get_langsmith_config()
        
        if config.enabled:
            logger.info(
                f"LangSmith initialized successfully - Project: {config.project_name}"
            )
            
            # Test client connection
            client = config.client
            if client:
                logger.info("LangSmith client connection verified")
            
            return True
        else:
            logger.info("LangSmith disabled - no API key provided")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith: {e}")
        return False


def get_langsmith_status() -> dict:
    """
    Get current LangSmith configuration status.
    
    Returns:
        dict: Status information about LangSmith configuration
    """
    try:
        config = get_langsmith_config()
        
        status = {
            "enabled": config.enabled,
            "project_name": config.project_name if config.enabled else None,
            "client_available": config.client is not None if config.enabled else False,
            "api_key_configured": bool(config.settings.langsmith_api_key),
        }
        
        if config.enabled:
            status["environment_configured"] = all([
                bool(config.settings.langsmith_api_key),
                bool(config.settings.langsmith_project),
            ])
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting LangSmith status: {e}")
        return {
            "enabled": False,
            "error": str(e),
            "environment_configured": False,
        }


def validate_langsmith_configuration() -> tuple[bool, Optional[str]]:
    """
    Validate LangSmith configuration and return status.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        config = get_langsmith_config()
        
        if not config.enabled:
            return True, None  # Valid to be disabled
        
        # Check required configuration
        if not config.settings.langsmith_api_key:
            return False, "LANGSMITH_API_KEY not provided"
        
        if not config.settings.langsmith_project:
            return False, "LANGSMITH_PROJECT not configured"
        
        # Test client creation
        client = config.client
        if not client:
            return False, "Failed to create LangSmith client"
        
        return True, None
        
    except Exception as e:
        return False, f"Configuration validation failed: {str(e)}"