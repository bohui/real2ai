"""
Base Node Class for Contract Analysis Workflow

This module provides the base class that all workflow nodes inherit from,
containing common functionality, logging, error handling, and state management.
"""

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Dict, Any, Optional, TYPE_CHECKING
import json
import logging
from datetime import UTC, datetime

from app.agents.states.base import LangGraphBaseState
from app.agents.states.contract_state import (
    RealEstateAgentState,
    update_state_step,
)
from app.core.config import get_settings
from app.clients.base.exceptions import ClientError

if TYPE_CHECKING:
    # Avoid circular imports during type checking
    pass

logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """
    Base class for all workflow nodes in the ContractAnalysisWorkflow.

    This class provides common functionality that all workflow nodes need:
    - Error logging and exception handling
    - State management and progress tracking
    - Environment-aware logging
    - Configuration access
    - Performance metrics tracking

    Args:
        workflow: Reference to the parent ContractAnalysisWorkflow instance
        node_name: Name of the node for logging and tracking purposes

    Example:
        ```python
        class MyCustomNode(BaseNode):
            def __init__(self, workflow: 'ContractAnalysisWorkflow'):
                super().__init__(workflow, "my_custom_node")

            async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
                try:
                    self._log_step_debug("Starting custom processing", state)

                    # Your node processing logic here
                    result = await self._process_with_logging(state)

                    return self.update_state_step(
                        state,
                        "custom_processing_complete",
                        data={"result": result}
                    )

                except Exception as e:
                    return self._handle_node_error(state, e, "Custom processing failed")
        ```

    Methods:
        execute(): Abstract method that must be implemented by each node
        _log_exception(): Log exceptions with context and environment awareness
        _log_step_debug(): Log debug information when verbose logging is enabled
        _handle_node_error(): Standard error handling for node failures
        update_state_step(): Update workflow state with progress information
        _get_progress_update(): Calculate progress updates based on current state
    """

    def __init__(
        self, workflow: any, node_name: str, progress_range: tuple[int, int] = (0, 100)
    ):
        """
        Initialize base node with workflow reference and configuration.

        Args:
            workflow: Parent ContractAnalysisWorkflow instance
            node_name: Name of this node for logging and identification
        """
        self.workflow = workflow
        self.node_name = node_name

        # # Access workflow configuration
        # self.extraction_config = workflow.extraction_config
        # self.use_llm_config = workflow.use_llm_config
        # self.enable_validation = workflow.enable_validation
        # self.enable_quality_checks = workflow.enable_quality_checks
        # self.enable_fallbacks = workflow.enable_fallbacks

        # Access workflow clients and managers
        self.openai_client = None  # Will be set during workflow initialization
        self.gemini_client = None  # Will be set during workflow initialization
        self.prompt_manager = workflow.prompt_manager
        # self.structured_parsers = workflow.structured_parsers

        # Structured parsers configured at workflow level

        # Environment and logging configuration
        self._settings = get_settings()
        self._is_production = self._settings.environment.lower() in (
            "production",
            "prod",
            "live",
        )
        self._verbose_logging = bool(
            self._settings.enhanced_workflow_detailed_logging
            and not self._is_production
        )

        # Node-specific metrics
        self._node_metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "average_duration": 0.0,
            "total_duration": 0.0,
        }

        # Helper to safely access state dicts from subclasses
        # Avoids KeyError/AttributeError in nodes when state is not a plain dict
        self.workflow_state_safe_get = (
            lambda s, k, d=None: (s.get(k) if isinstance(s, dict) else d) or d
        )

        self.logger = logging.getLogger(f"{__name__}.{node_name}")
        self.progress_range = progress_range or (0, 100)
        self.progress_callback: Optional[Callable[[str, int, str], Awaitable[None]]] = (
            None
        )

    def get_parser(self, parser_type: str) -> Any:
        """Return the configured structured parser for a given type."""
        return self.structured_parsers.get(parser_type)

    @abstractmethod
    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Execute the node's processing logic.

        This method must be implemented by each concrete node class.
        It should contain the main processing logic for the node.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state

        Raises:
            Exception: Any processing errors that occur during execution
        """
        pass

    def _log_exception(
        self,
        error: Exception,
        state: Optional[RealEstateAgentState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log exceptions with appropriate detail level based on environment.

        Provides consistent exception logging across all nodes with:
        - Environment-aware detail levels (verbose in dev, minimal in prod)
        - Structured logging format for monitoring systems
        - PII-safe logging (user_id only in development)
        - Contextual information for debugging

        Args:
            error: Exception that occurred
            state: Current workflow state (optional)
            context: Additional context information (optional)

        Example:
            ```python
            try:
                result = await some_processing()
            except ValueError as e:
                self._log_exception(e, state, {"input_data": data})
                raise
            ```
        """
        base: Dict[str, Any] = {
            "node": self.node_name,
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        if state:
            base["session_id"] = state.get("session_id")
            # Only include user_id when verbose logging is enabled (avoid PII in prod)
            if self._verbose_logging:
                base["user_id"] = state.get("user_id")

        if context:
            base["context"] = context

        # Update node metrics
        self._node_metrics["failures"] += 1

        if self._verbose_logging:
            logger.exception(
                f"[{self.node_name}] Error occurred | data={json.dumps(base, default=str)}"
            )
        else:
            minimal = {
                k: base.get(k)
                for k in ("node", "error_type", "message", "session_id", "timestamp")
                if k in base
            }
            logger.error(
                f"[{self.node_name}] {base['error_type']}: {base['message']} | "
                f"session_id={base.get('session_id', 'unknown')}"
            )

    def _log_step_debug(
        self,
        message: str,
        state: Optional[RealEstateAgentState] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log debug information when verbose logging is enabled.

        Provides detailed logging for development and troubleshooting:
        - Only logs when verbose logging is enabled
        - Includes session context and workflow progress
        - Structured format for log analysis
        - Performance-conscious (early return in production)

        Args:
            message: Debug message to log
            state: Current workflow state (optional)
            details: Additional details to include (optional)

        Example:
            ```python
            self._log_step_debug(
                "Starting terms extraction",
                state,
                {"confidence_threshold": 0.8, "method": "llm_structured"}
            )
            ```
        """
        if not self._verbose_logging:
            return

        safe_state = {}
        try:
            if state:
                safe_state = {
                    "session_id": state.get("session_id"),
                    "user_id": state.get("user_id"),
                    "progress": state.get("progress", {}).get("current_step"),
                }
        except Exception:
            safe_state = {}

        log_data = {
            "node": self.node_name,
            "message": message,
            "state": safe_state,
            "timestamp": datetime.now().isoformat(),
        }

        if details:
            log_data["details"] = details

        logger.debug(
            f"[{self.node_name}] {message} | data={json.dumps(log_data, default=str)}"
        )

    def _log_warning(self, message: str, **kwargs) -> None:
        """
        Log warning messages with node context.

        Compatible with existing calls that pass `extra=...` for structured logging.
        """
        try:
            extra = kwargs.get("extra")
            if extra is not None:
                logger.warning(f"[{self.node_name}] {message}", extra=extra)
            else:
                logger.warning(f"[{self.node_name}] {message}")
        except Exception:
            # Fallback to simple warning without extras if logging fails
            logger.warning(f"[{self.node_name}] {message}")

    def _handle_node_error(
        self,
        state: RealEstateAgentState,
        error: Exception,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RealEstateAgentState:
        """
        Handle node execution errors with consistent error state management.

        Provides standardized error handling across all nodes:
        - Logs the error with full context
        - Updates workflow state with error information
        - Maintains error tracking for debugging
        - Returns properly formatted error state

        Args:
            state: Current workflow state
            error: Exception that occurred
            error_message: Human-readable error description
            context: Additional error context (optional)

        Returns:
            Updated state with error information

        Example:
            ```python
            try:
                result = await self._process_data(data)
            except ValidationError as e:
                return self._handle_node_error(
                    state,
                    e,
                    "Data validation failed",
                    {"data_type": type(data).__name__}
                )
            ```
        """
        # Handle case where state is None
        if state is None:
            logger.error(
                f"Node {self.node_name} error handling called with None state: {error_message}",
                extra={"error": str(error), "context": context},
            )
            # Create a minimal error state since we can't update None
            from app.agents.states.contract_state import create_initial_state

            minimal_state = create_initial_state(
                user_id="unknown",
                australian_state="NSW",  # Default state
                user_type="buyer",
            )
            minimal_state["error_state"] = (
                f"Critical error in {self.node_name}: {error_message}"
            )
            from app.schema.enums import ProcessingStatus

            minimal_state["progress"] = {
                "status": ProcessingStatus.FAILED,
                "error": error_message,
                "step_name": f"{self.node_name}_error",
                "current_step": 0,
                "total_steps": 0,
                "percentage": 0,
                "step_history": [],
            }
            return minimal_state

        self._log_exception(error, state, context)

        error_step_name = f"{self.node_name}_error"
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "node": self.node_name,
            "timestamp": datetime.now().isoformat(),
        }

        if context:
            error_details["context"] = context

        # Include a top-level 'error' field for tests and downstream consumers
        enriched_details = {"error": error_message, **error_details}
        return update_state_step(
            state, error_step_name, error=error_message, data=enriched_details
        )

    def update_state_step(
        self,
        state: RealEstateAgentState,
        step_name: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> RealEstateAgentState:
        """
        Update workflow state with step completion information.

        Wrapper around the global update_state_step function that provides:
        - Consistent state update format across all nodes
        - Progress tracking and percentage calculation
        - Error state management
        - Node-specific step naming

        Args:
            state: Current workflow state
            step_name: Name of the completed step
            data: Step completion data (optional)
            error: Error message if step failed (optional)

        Returns:
            Updated workflow state

        Example:
            ```python
            return self.update_state_step(
                state,
                "terms_extracted",
                data={
                    "terms_count": len(terms),
                    "confidence": confidence_score,
                    "method": extraction_method
                }
            )
            ```
        """
        # Update node metrics on successful completion
        if not error:
            self._node_metrics["successes"] += 1

        self._node_metrics["executions"] += 1

        # CRITICAL FIX: Get the state update and merge it with existing state
        # instead of returning minimal updates that lose data
        state_update = update_state_step(state, step_name, data=data, error=error)

        # Merge the update with the existing state to preserve all original data
        if isinstance(state_update, dict):
            # Create a copy of the state to avoid modifying the original
            updated_state = dict(state)
            updated_state.update(state_update)
            return updated_state

        # Fallback: return original state if update is invalid
        return state

    def _get_progress_update(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Calculate progress update based on current workflow state.

        Args:
            state: Current workflow state

        Returns:
            Progress update dictionary with current step and percentage
        """
        progress_update = {}
        if "progress" in state and state["progress"]:
            current_step_num = state["progress"]["current_step"] + 1
            total_steps = state["progress"]["total_steps"]
            progress_update["progress"] = {
                **state["progress"],
                "current_step": current_step_num,
                "percentage": int((current_step_num / total_steps) * 100),
            }
        return progress_update

    def get_node_metrics(self) -> Dict[str, Any]:
        """
        Get current node performance metrics.

        Returns:
            Dictionary containing node execution metrics
        """
        if self._node_metrics["executions"] > 0:
            success_rate = (
                self._node_metrics["successes"] / self._node_metrics["executions"]
            )
            self._node_metrics["success_rate"] = success_rate

        return self._node_metrics.copy()

    def reset_node_metrics(self) -> None:
        """Reset node performance metrics."""
        self._node_metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "average_duration": 0.0,
            "total_duration": 0.0,
        }

    async def _generate_content_with_fallback(
        self,
        prompt: str,
        use_gemini_fallback: bool = True,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate content with client fallback logic.

        This method attempts to generate content using available clients with fallback:
        1. Try OpenAI client first
        2. Fall back to Gemini client if OpenAI fails and fallback is enabled
        3. Return None if no clients produce valid responses and fallbacks are enabled
        4. Raise ClientError if no valid response is generated from available clients and fallbacks are disabled

        Args:
            prompt: The prompt to send to the LLM
            use_gemini_fallback: Whether to use Gemini as fallback (default: True)
            system_prompt: Optional system prompt to guide the model (default: None)

        Returns:
            Generated content string or None if fallbacks fail

        Raises:
            ClientError: If no valid response is generated from available clients and fallbacks are disabled
        """
        # Check if clients are available
        if not self.openai_client and not self.gemini_client:
            error_msg = f"No AI clients available in {self.node_name}. Workflow may not be properly initialized."
            logger.error(error_msg)
            if not self.enable_fallbacks:
                raise ClientError(error_msg)
            return None

        # Try OpenAI client first
        openai_failed = False
        gemini_failed = False
        last_error = None

        if self.openai_client:
            try:
                # Pass system prompt if provided
                kwargs = {}
                if system_prompt:
                    kwargs["system_message"] = system_prompt

                response = await self.openai_client.generate_content(prompt, **kwargs)
                if response and response.strip():
                    return response
            except Exception as e:
                openai_failed = True
                last_error = e
                # Check for authentication errors which suggest misconfiguration
                if (
                    "401" in str(e)
                    or "Unauthorized" in str(e)
                    or "No auth credentials" in str(e)
                ):
                    logger.warning(
                        f"OpenAI client authentication failed in {self.node_name}: {e}"
                    )
                    logger.info(f"Falling back to Gemini client for {self.node_name}")
                else:
                    logger.warning(f"OpenAI client failed in {self.node_name}: {e}")

        # Fall back to Gemini client if enabled
        if use_gemini_fallback and self.gemini_client:
            try:
                # Pass system prompt if provided
                kwargs = {}
                if system_prompt:
                    kwargs["system_prompt"] = system_prompt

                response = await self.gemini_client.generate_content(prompt, **kwargs)
                if response and response.strip():
                    return response
            except Exception as e:
                gemini_failed = True
                last_error = e
                logger.warning(f"Gemini client failed in {self.node_name}: {e}")

        # If we get here, no clients produced valid responses
        if not self.enable_fallbacks:
            if not self.openai_client and not self.gemini_client:
                raise ClientError(
                    f"No AI clients available in {self.node_name}. Workflow may not be properly initialized."
                )
            elif last_error:
                raise ClientError(
                    f"No valid response from available clients. Last error: {last_error}"
                )
            else:
                raise ClientError("No valid response from available clients")

        # Log a more informative error message
        error_details = []
        if openai_failed:
            error_details.append("OpenAI failed")
        if gemini_failed:
            error_details.append("Gemini failed")

        if not error_details:
            error_details.append("No clients available")

        logger.error(
            f"Content generation failed in {self.node_name}: {', '.join(error_details)}. "
            f"Last error: {last_error if last_error else 'No specific error'}"
        )
        return None

    def _safe_json_parse(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse JSON response with error handling.

        Args:
            response: JSON string to parse

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed in {self.node_name}: {e}")
            return None

    async def emit_progress(self, state: LangGraphBaseState, percent: int, desc: str):
        try:
            notify = (state or {}).get("notify_progress")
            if notify and callable(notify):
                await notify(self.node_name, percent, desc)
        except Exception as e:
            self.logger.debug(f"Progress emit failed: {e}")

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _error_update(self, message: str) -> Dict[str, Any]:
        return {"processing_errors": [message]}

    def __repr__(self) -> str:
        """String representation of the node."""
        return f"{self.__class__.__name__}(node_name='{self.node_name}')"
