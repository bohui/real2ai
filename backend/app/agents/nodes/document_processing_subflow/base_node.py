"""
Base Node for Document Processing Subflow

This module provides the base class for all document processing subflow nodes.
It includes common functionality like user authentication, error handling, and metrics.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
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
            "average_duration": 0.0,
        }

        # Progress tracking
        self.progress_callback = None

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

    def _ensure_user_context(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
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
                "context_type": "user_authenticated",
            }

            self._log_debug(
                f"User context validated for user {user_context.user_id}",
                user_id=user_context.user_id,
            )

            return state

        except Exception as e:
            self.logger.error(f"User context validation failed: {e}", exc_info=True)
            # Return state with error instead of raising to allow graceful handling
            state = state.copy()
            state["auth_error"] = f"User authentication required: {str(e)}"
            return state

    def _handle_error(
        self,
        state: DocumentProcessingState,
        error: Exception,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if context:
            error_details["context"] = context

        # Check if this is an authentication error
        is_auth_error = (
            "authentication" in str(error).lower()
            or "user context" in str(error).lower()
            or "unauthorized" in str(error).lower()
            or isinstance(error, (PermissionError, ValueError))
            and "auth" in str(error).lower()
        )

        # Extract root cause and exception chain for better debugging
        root_cause = self._extract_root_cause(error)
        exception_chain = self._format_exception_chain(error)

        # Add root cause information to error details
        error_details.update(
            {
                "root_cause_type": type(root_cause).__name__,
                "root_cause_message": str(root_cause),
                "exception_chain": exception_chain,
                "node_location": f"{self.__class__.__module__}.{self.__class__.__name__}",
            }
        )

        if is_auth_error:
            error_details["error_category"] = "authentication"
            self.logger.error(
                f"[{self.node_name}] AUTHENTICATION ERROR - {error_message}: {error}\nRoot cause: {root_cause}",
                exc_info=True,
                extra={
                    "context": context,
                    "auth_error": True,
                    "root_cause": str(root_cause),
                    "exception_chain": exception_chain,
                },
            )
        else:
            self.logger.error(
                f"[{self.node_name}] {error_message}: {error}\nRoot cause: {root_cause}",
                exc_info=True,
                extra={
                    "context": context,
                    "root_cause": str(root_cause),
                    "exception_chain": exception_chain,
                },
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
            "average_duration": 0.0,
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

    def _log_error(self, message: str, **kwargs):
        """Log error message with node context. Supports exc_info via kwarg."""
        exc_info = kwargs.pop("exc_info", False)
        self.logger.error(
            f"[{self.node_name}] {message}", extra=kwargs, exc_info=exc_info
        )

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
                self._log_warning(
                    "Processing prerequisites failed: authentication error"
                )
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

    def _should_continue_after_error(
        self, error: Exception, state: DocumentProcessingState
    ) -> bool:
        """
        Determine if workflow should continue after an error or fail completely.

        Args:
            error: The exception that occurred
            state: Current processing state

        Returns:
            bool: True if workflow should continue with degraded functionality
        """
        # Authentication errors should generally stop the workflow
        if (
            "authentication" in str(error).lower()
            or "unauthorized" in str(error).lower()
        ):
            return False

        # Critical system errors should stop the workflow
        if isinstance(error, (MemoryError, SystemExit, KeyboardInterrupt)):
            return False

        # Document not found or access errors should stop workflow
        if (
            "document not found" in str(error).lower()
            or "access denied" in str(error).lower()
        ):
            return False

        # For other errors, allow workflow to continue with degraded functionality
        return True

    def _create_fallback_state(
        self, state: DocumentProcessingState, error: Exception
    ) -> DocumentProcessingState:
        """
        Create a fallback state that allows workflow to continue despite errors.

        Args:
            state: Current processing state
            error: The exception that occurred

        Returns:
            Updated state with fallback values
        """
        fallback_state = state.copy()

        # Mark as degraded processing
        fallback_state["degraded_processing"] = True
        fallback_state["degradation_reason"] = str(error)
        fallback_state["degraded_nodes"] = fallback_state.get("degraded_nodes", []) + [
            self.node_name
        ]

        # Provide minimal fallback data based on node type
        if "extract" in self.node_name.lower():
            # Text extraction failed - provide empty but valid structure
            from app.schema.document import TextExtractionResult

            fallback_state["text_extraction_result"] = TextExtractionResult(
                success=False,
                error=f"Text extraction failed: {str(error)}",
                full_text="[Text extraction failed - document processing continued with reduced functionality]",
                pages=[],
                total_pages=0,
                extraction_methods=["fallback"],
                overall_confidence=0.0,
                processing_time=0.0,
            )
        elif "validation" in self.node_name.lower():
            # Validation failed - mark as low quality but continue
            fallback_state["quality_validation_result"] = {
                "passed": False,
                "score": 0.0,
                "reason": f"Validation failed: {str(error)}",
                "fallback": True,
            }
        elif "analysis" in self.node_name.lower():
            # Analysis failed - provide empty analysis
            fallback_state["analysis_result"] = {
                "success": False,
                "error": str(error),
                "results": {},
                "fallback": True,
            }

        self._log_warning(
            f"Created fallback state for failed node {self.node_name}: {error}"
        )
        return fallback_state

    def _handle_error_with_graceful_degradation(
        self,
        state: DocumentProcessingState,
        error: Exception,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DocumentProcessingState:
        """
        Handle errors with graceful degradation - allows workflow to continue when possible.

        Args:
            state: Current state
            error: Exception that occurred
            error_message: Human-readable error description
            context: Additional error context

        Returns:
            Updated state with error information and possible fallback data
        """
        # First, handle the error normally
        error_state = self._handle_error(state, error, error_message, context)

        # Then determine if we should try to continue
        if self._should_continue_after_error(error, state):
            try:
                # Create fallback state to allow workflow continuation
                fallback_state = self._create_fallback_state(error_state, error)

                # Clear the processing_failed flag to allow continuation
                fallback_state["processing_failed"] = False
                fallback_state["node_failed"] = (
                    self.node_name
                )  # Track which node failed

                self._log_info(
                    f"Graceful degradation: workflow will continue despite {self.node_name} failure",
                    extra={
                        "error": str(error),
                        "degraded_nodes": fallback_state.get("degraded_nodes", []),
                    },
                )

                return fallback_state

            except Exception as fallback_error:
                self._log_warning(f"Fallback creation failed: {fallback_error}")
                # Return the original error state if fallback fails
                return error_state
        else:
            self._log_info(
                f"Critical error in {self.node_name}, workflow cannot continue"
            )
            return error_state

    def __repr__(self) -> str:
        """String representation of the node."""
        return f"{self.__class__.__name__}(node_name='{self.node_name}')"

    def _extract_root_cause(self, exception: Exception) -> Exception:
        """
        Extract the root cause from an exception chain.

        Args:
            exception: The exception to analyze

        Returns:
            The root cause exception (the original exception that started the chain)
        """
        current = exception
        while hasattr(current, "__cause__") and current.__cause__ is not None:
            current = current.__cause__

        # Also check for __context__ which is used for implicit exception chaining
        while hasattr(current, "__context__") and current.__context__ is not None:
            if not hasattr(current, "__cause__") or current.__cause__ is None:
                # Only follow __context__ if there's no explicit __cause__
                current = current.__context__
            else:
                break

        return current

    def _format_exception_chain(self, exception: Exception) -> List[str]:
        """
        Format the full exception chain as a list of strings for logging.

        Args:
            exception: The exception to format

        Returns:
            List of formatted exception strings showing the full chain
        """
        chain = []
        current = exception
        seen = set()  # Prevent infinite loops in circular references

        while current is not None:
            # Prevent infinite loops
            exception_id = id(current)
            if exception_id in seen:
                break
            seen.add(exception_id)

            # Format current exception
            exc_info = {
                "type": type(current).__name__,
                "message": str(current),
                "module": getattr(type(current), "__module__", "unknown"),
            }

            # Add file and line info if available
            if hasattr(current, "__traceback__") and current.__traceback__:
                tb = current.__traceback__
                while tb.tb_next:
                    tb = tb.tb_next  # Get the deepest traceback
                exc_info["file"] = tb.tb_frame.f_code.co_filename
                exc_info["line"] = tb.tb_lineno
                exc_info["function"] = tb.tb_frame.f_code.co_name

            chain.append(
                f"{exc_info['type']}: {exc_info['message']} (in {exc_info.get('function', 'unknown')} at {exc_info.get('file', 'unknown')}:{exc_info.get('line', 'unknown')})"
            )

            # Move to the next exception in the chain
            if hasattr(current, "__cause__") and current.__cause__ is not None:
                current = current.__cause__
            elif hasattr(current, "__context__") and current.__context__ is not None:
                current = current.__context__
            else:
                break

        return chain

    def set_progress_callback(self, callback):
        """Set progress callback for emitting incremental progress updates."""
        self.progress_callback = callback

    async def emit_page_progress(
        self,
        current_page: int,
        total_pages: int,
        description: str = "Processing pages",
        progress_range: tuple[int, int] = (7, 30),
    ):
        """
        Emit incremental progress updates for page-based processing via contract/session channel.
        Maps page progress to the specified range.

        Args:
            current_page: Current page being processed (1-based)
            total_pages: Total number of pages to process
            description: Description of the processing step
            progress_range: Tuple of (start_percent, end_percent) for progress mapping
        """
        if not self.progress_callback:
            return

        try:
            start_progress, end_progress = progress_range
            progress_range_size = end_progress - start_progress

            # Calculate progress percentage within the range
            if total_pages > 0:
                page_progress = (current_page / total_pages) * progress_range_size
                final_progress = min(end_progress, start_progress + int(page_progress))
            else:
                final_progress = start_progress

            # Emit progress directly via contract analysis service broadcasting
            await self.progress_callback(
                "document_processing",
                final_progress,
                f"{description} (page {current_page}/{total_pages})",
            )

            self._log_debug(
                f"Emitted page progress to contract/session channel: {current_page}/{total_pages} -> {final_progress}%",
                current_page=current_page,
                total_pages=total_pages,
                progress_percent=final_progress,
            )

        except Exception as e:
            # Don't fail processing if progress emission fails
            self._log_warning(f"Failed to emit page progress: {e}")

    # async def emit_progress_via_session_channel(
    #     self,
    #     session_id: str,
    #     contract_id: str,
    #     step: str,
    #     progress_percent: int,
    #     description: str,
    # ):
    #     """
    #     Emit progress directly via session channel for real-time UI updates.
    #     This bypasses document-specific channels and uses the contract analysis service's broadcasting.

    #     Args:
    #         session_id: Session ID for WebSocket routing
    #         contract_id: Contract UUID for identification
    #         step: Current processing step
    #         progress_percent: Progress percentage (7-30% for document processing)
    #         description: Step description
    #     """
    #     try:
    #         from app.services.communication.redis_pubsub import publish_progress_sync
    #         from datetime import datetime

    #         message = {
    #             "event_type": "analysis_progress",
    #             "timestamp": datetime.now().isoformat(),
    #             "data": {
    #                 "contract_id": contract_id,
    #                 "current_step": step,
    #                 "progress_percent": progress_percent,
    #                 "step_description": description,
    #             },
    #         }

    #         # Publish to session channel for UI consumption
    #         if session_id:
    #             publish_progress_sync(session_id, message)

    #         self._log_debug(
    #             f"Emitted progress to session channel {session_id}: {step} -> {progress_percent}%",
    #             session_id=session_id,
    #             contract_id=contract_id,
    #             step=step,
    #             progress_percent=progress_percent,
    #         )

    #     except Exception as e:
    #         self._log_warning(f"Failed to emit progress via session channel: {e}")
