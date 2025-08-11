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
            
        self.logger.error(
            f"[{self.node_name}] {error_message}: {error}",
            exc_info=True,
            extra={"context": context}
        )
        
        # Update state with error
        state = state.copy()
        state["error"] = error_message
        state["error_details"] = error_details
        
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
        
    def __repr__(self) -> str:
        """String representation of the node."""
        return f"{self.__class__.__name__}(node_name='{self.node_name}')"