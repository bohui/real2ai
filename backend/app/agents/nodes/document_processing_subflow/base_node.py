"""
Base Node for Document Processing Subflow

This module provides the base class for all document processing subflow nodes.
It includes common functionality like user authentication, error handling, and metrics.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.auth_context import AuthContext
from app.agents.subflows.document_processing_workflow import DocumentProcessingState

logger = logging.getLogger(__name__)


class DocumentProcessingNodeBase(ABC):
    """
    Base class for all document processing subflow nodes.
    
    Provides common functionality:
    - User authentication context management
    - Standardized error handling
    - Performance metrics tracking
    - Logging and debugging utilities
    """
    
    def __init__(self, node_name: str):
        """
        Initialize the base node.
        
        Args:
            node_name: Name of the node for logging and metrics
        """
        self.node_name = node_name
        self.logger = logging.getLogger(f"{__name__}.{node_name}")
        
        # Performance metrics
        self._metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0.0,
            "average_duration": 0.0
        }
    
    @abstractmethod
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Execute the node's processing logic.
        
        Args:
            state: Current document processing state
            
        Returns:
            Updated state
        """
        pass
    
    async def get_user_client(self):
        """Get authenticated user client for database operations."""
        return await AuthContext.get_authenticated_client(isolated=True)
    
    async def get_user_context(self):
        """Get user context for authentication and authorization."""
        try:
            return AuthContext.get_current_context()
        except Exception as e:
            self.logger.warning(f"Failed to get user context: {e}")
            raise ValueError("User authentication required") from e
    
    def _ensure_user_context(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Ensure user context is available and valid.
        
        This method checks that the user context is properly set and accessible
        for all database operations that require RLS (Row Level Security).
        
        Args:
            state: Current document processing state
            
        Returns:
            Updated state with user context validation
            
        Raises:
            ValueError: If user context is not available or invalid
        """
        try:
            # Verify user context is available
            user_context = AuthContext.get_current_context()
            if not user_context or not user_context.user_id:
                raise ValueError("No user context available - authentication required")
            
            # Store user context in state for downstream nodes
            state = state.copy()
            state["user_context"] = {
                "user_id": user_context.user_id,
                "authenticated": True,
                "context_type": "user_authenticated"
            }
            
            self._log_debug(
                f"User context validated for user {user_context.user_id}",
                user_id=user_context.user_id
            )
            
            return state
            
        except Exception as e:
            self.logger.error(
                f"User context validation failed: {e}",
                exc_info=True
            )
            # Return state with error instead of raising to allow graceful handling
            state = state.copy()
            state["auth_error"] = f"User authentication required: {str(e)}"
            return state
    
    def _handle_error(
        self,
        state: DocumentProcessingState,
        error: Exception,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DocumentProcessingState:
        """
        Handle node execution errors with consistent error state management.
        
        Args:
            state: Current state
            error: Exception that occurred
            error_message: Human-readable error description
            context: Additional error context
            
        Returns:
            Updated state with error information
        """
        self._metrics["failures"] += 1
        
        error_details = {
            "node": self.node_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if context:
            error_details["context"] = context
            
        # Check if this is an authentication error
        is_auth_error = (
            "authentication" in str(error).lower() or
            "user context" in str(error).lower() or
            "unauthorized" in str(error).lower() or
            isinstance(error, (PermissionError, ValueError)) and "auth" in str(error).lower()
        )
        
        if is_auth_error:
            error_details["error_category"] = "authentication"
            self.logger.error(
                f"[{self.node_name}] AUTHENTICATION ERROR - {error_message}: {error}",
                exc_info=True,
                extra={"context": context, "auth_error": True}
            )
        else:
            self.logger.error(
                f"[{self.node_name}] {error_message}: {error}",
                exc_info=True,
                extra={"context": context}
            )
        
        # Update state with error
        state = state.copy()
        state["error"] = error_message
        state["error_details"] = error_details
        state["processing_failed"] = True
        
        # Mark authentication errors specifically
        if is_auth_error:
            state["auth_failed"] = True
        
        return state
    
    def _record_success(self, duration: float = 0.0):
        """Record successful execution metrics."""
        self._metrics["executions"] += 1
        self._metrics["successes"] += 1
        self._metrics["total_duration"] += duration
        
        if self._metrics["executions"] > 0:
            self._metrics["average_duration"] = (
                self._metrics["total_duration"] / self._metrics["executions"]
            )
    
    def _record_execution(self):
        """Record node execution attempt."""
        self._metrics["executions"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get node performance metrics."""
        metrics = self._metrics.copy()
        
        if metrics["executions"] > 0:
            metrics["success_rate"] = metrics["successes"] / metrics["executions"]
        else:
            metrics["success_rate"] = 0.0
            
        return metrics
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self._metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0.0,
            "average_duration": 0.0
        }
    
    def _log_info(self, message: str, **kwargs):
        """Log info message with node context."""
        self.logger.info(f"[{self.node_name}] {message}", extra=kwargs)
    
    def _log_debug(self, message: str, **kwargs):
        """Log debug message with node context.""" 
        self.logger.debug(f"[{self.node_name}] {message}", extra=kwargs)
    
    def _log_warning(self, message: str, **kwargs):
        """Log warning message with node context."""
        self.logger.warning(f"[{self.node_name}] {message}", extra=kwargs)
        
    def _check_processing_prerequisites(self, state: DocumentProcessingState) -> bool:
        """
        Check if all prerequisites for processing are met.
        
        This includes user authentication, document availability, and required state.
        
        Args:
            state: Current document processing state
            
        Returns:
            bool: True if prerequisites are met, False otherwise
        """
        try:
            # Check for authentication error in state
            if state.get("auth_error") or state.get("auth_failed"):
                self._log_warning("Processing prerequisites failed: authentication error")
                return False
            
            # Check for user context
            user_context = state.get("user_context")
            if not user_context or not user_context.get("authenticated"):
                self._log_warning("Processing prerequisites failed: no user context")
                return False
            
            # Check for document ID
            document_id = state.get("document_id")
            if not document_id:
                self._log_warning("Processing prerequisites failed: no document_id")
                return False
            
            return True
            
        except Exception as e:
            self._log_warning(f"Error checking prerequisites: {e}")
            return False
    
    def __repr__(self) -> str:
        """String representation of the node."""
        return f"{self.__class__.__name__}(node_name='{self.node_name}')"