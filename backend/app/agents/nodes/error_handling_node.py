"""
Error Handling Node for Contract Analysis Workflow

This module contains the node responsible for handling workflow errors and failures.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from app.models.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from .base import BaseNode

logger = logging.getLogger(__name__)


class ErrorHandlingNode(BaseNode):
    """
    Node responsible for handling workflow errors and failures.

    This node performs:
    - Error categorization and analysis
    - Recovery strategy determination
    - Error reporting and logging
    - Graceful failure handling
    """

    def __init__(self, workflow):
        super().__init__(workflow, "error_handling")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Handle workflow errors and determine next steps.

        Args:
            state: Current workflow state with error information

        Returns:
            Updated state with error handling results
        """
        try:
            self._log_step_debug("Starting error handling", state)

            # Extract error information
            error_info = self._extract_error_info(state)
            
            # Categorize error
            error_category = self._categorize_error(error_info)
            
            # Determine recovery options
            recovery_options = self._determine_recovery_options(error_info, error_category)
            
            # Generate error report
            error_report = {
                "error_info": error_info,
                "error_category": error_category,
                "recovery_options": recovery_options,
                "error_handled_at": datetime.now(UTC).isoformat(),
                "recoverable": len(recovery_options) > 0,
            }

            # Update state
            state["error_report"] = error_report
            state["processing_status"] = ProcessingStatus.FAILED

            error_data = {
                "error_report": error_report,
                "error_category": error_category,
                "recoverable": error_report["recoverable"],
                "recovery_options_count": len(recovery_options),
            }

            self._log_step_debug(
                f"Error handling completed (category: {error_category}, recoverable: {error_report['recoverable']})",
                state,
                {"recovery_options": len(recovery_options)}
            )

            return self.update_state_step(
                state, "error_handling_completed", data=error_data
            )

        except Exception as e:
            # Error in error handling - critical failure
            return self._handle_node_error(
                state,
                e,
                f"Critical error in error handling: {str(e)}",
                {"original_error": state.get("error", "Unknown")}
            )

    def _extract_error_info(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Extract error information from state."""
        error_info = {
            "error_message": "Unknown error",
            "error_step": "unknown",
            "error_type": "system_error",
            "error_details": {},
            "session_id": state.get("session_id", "unknown"),
        }

        # Look for error information in progress history
        progress = state.get("progress", {})
        step_history = progress.get("step_history", [])
        
        if step_history:
            latest_step = step_history[-1]
            if latest_step.get("error"):
                error_info.update({
                    "error_message": latest_step["error"],
                    "error_step": latest_step.get("step", "unknown"),
                    "error_details": latest_step.get("data", {})
                })

        # Check for specific error fields
        if "error" in state:
            error_info["error_message"] = state["error"]
            
        return error_info

    def _categorize_error(self, error_info: Dict[str, Any]) -> str:
        """Categorize the error based on its characteristics."""
        error_message = error_info.get("error_message", "").lower()
        error_step = error_info.get("error_step", "").lower()

        # Document processing errors
        if "document" in error_message or "document" in error_step:
            if "missing" in error_message or "not found" in error_message:
                return "missing_document"
            elif "processing" in error_message:
                return "document_processing_error"
            else:
                return "document_error"

        # LLM/API errors
        if any(term in error_message for term in ["api", "llm", "openai", "gemini", "timeout"]):
            return "api_error"

        # Validation errors
        if "validation" in error_message or "validation" in error_step:
            return "validation_error"

        # Extraction errors
        if "extraction" in error_message or "terms" in error_message:
            return "extraction_error"

        # Configuration errors
        if "config" in error_message or "missing" in error_message:
            return "configuration_error"

        # Default category
        return "system_error"

    def _determine_recovery_options(
        self, error_info: Dict[str, Any], error_category: str
    ) -> List[Dict[str, Any]]:
        """Determine possible recovery options based on error category."""
        recovery_options = []

        if error_category == "missing_document":
            recovery_options.extend([
                {
                    "option": "request_document_reupload",
                    "description": "Request user to re-upload the document",
                    "feasibility": "high",
                    "action": "user_intervention_required"
                },
                {
                    "option": "check_document_id",
                    "description": "Verify document ID is correct",
                    "feasibility": "medium",
                    "action": "system_validation"
                }
            ])

        elif error_category == "api_error":
            recovery_options.extend([
                {
                    "option": "retry_with_backoff",
                    "description": "Retry API call with exponential backoff",
                    "feasibility": "high",
                    "action": "automatic_retry"
                },
                {
                    "option": "fallback_to_rule_based",
                    "description": "Use rule-based methods instead of LLM",
                    "feasibility": "high",
                    "action": "method_fallback"
                }
            ])

        elif error_category == "validation_error":
            recovery_options.extend([
                {
                    "option": "skip_validation",
                    "description": "Continue processing without validation",
                    "feasibility": "medium",
                    "action": "process_modification"
                },
                {
                    "option": "manual_validation",
                    "description": "Flag for manual validation",
                    "feasibility": "high",
                    "action": "manual_review"
                }
            ])

        elif error_category == "extraction_error":
            recovery_options.extend([
                {
                    "option": "retry_with_different_method",
                    "description": "Try alternative extraction method",
                    "feasibility": "high",
                    "action": "method_switch"
                },
                {
                    "option": "partial_extraction",
                    "description": "Continue with partial extraction results",
                    "feasibility": "medium",
                    "action": "accept_partial"
                }
            ])

        # Always include manual review as an option
        recovery_options.append({
            "option": "manual_review",
            "description": "Flag for manual review and intervention",
            "feasibility": "high",
            "action": "human_intervention"
        })

        return recovery_options