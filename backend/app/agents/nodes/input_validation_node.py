"""
Input Validation Node for Contract Analysis Workflow

This module contains the node responsible for validating input data before processing begins.
"""

import logging
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from .base import BaseNode

logger = logging.getLogger(__name__)


class InputValidationNode(BaseNode):
    """
    Node responsible for validating input data before processing begins.

    This node performs:
    - Input data structure validation
    - Required field verification
    - Data type and format validation
    - Early error detection and reporting
    """

    def __init__(self, workflow):
        super().__init__(workflow, "input_validation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Validate input data and prepare state for processing.

        Args:
            state: Initial workflow state with input data

        Returns:
            Updated state with validation results and progress initialization
        """
        try:
            self._log_step_debug("Starting input validation", state)

            # Initialize progress tracking
            state = self._initialize_progress_tracking(state)

            # Validate required input data
            validation_errors = []

            # Check for document data
            document_data = state.get("document_data")
            if not document_data:
                validation_errors.append("Missing document_data in input")
            else:
                # Validate document_data structure
                if not isinstance(document_data, dict):
                    validation_errors.append("document_data must be a dictionary")
                else:
                    document_id = document_data.get("document_id")
                    if not document_id:
                        validation_errors.append("Missing document_id in document_data")

            # Check for session identification
            session_id = state.get("session_id")
            if not session_id:
                validation_errors.append("Missing session_id in input")

            # Validate confidence scores structure
            if "confidence_scores" not in state:
                state["confidence_scores"] = {}

            # Initialize workflow metadata
            state["workflow_metadata"] = {
                "workflow_version": "2.0",
                "start_time": datetime.now(UTC).isoformat(),
                "node_execution_order": [],
                "validation_enabled": self.workflow.enable_validation,
                "quality_checks_enabled": self.workflow.enable_quality_checks,
            }

            if validation_errors:
                error_message = (
                    f"Input validation failed: {'; '.join(validation_errors)}"
                )
                return self._handle_node_error(
                    state,
                    Exception(error_message),
                    error_message,
                    {"validation_errors": validation_errors},
                )

            # Successful validation
            validation_data = {
                "validation_passed": True,
                "validation_errors": [],
                "input_structure_valid": True,
                "progress_initialized": True,
                "validation_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                "Input validation completed successfully",
                state,
                {
                    "session_id": session_id,
                    "document_id": document_data.get("document_id"),
                },
            )

            return self.update_state_step(
                state, "input_validation_passed", data=validation_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Input validation failed: {str(e)}",
                {"state_keys": list(state.keys()) if isinstance(state, dict) else []},
            )

    def _initialize_progress_tracking(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Initialize progress tracking for the workflow."""
        # Calculate total steps based on configuration
        base_steps = 8  # Core processing steps
        validation_steps = 3 if self.workflow.enable_validation else 0
        total_steps = base_steps + validation_steps

        # CRITICAL FIX: Don't overwrite the entire state, just set the progress field
        state["progress"] = {
            "current_step": 0,
            "total_steps": total_steps,
            "percentage": 0,
            "step_history": [],
            "started_at": datetime.now(UTC).isoformat(),
        }

        return state
