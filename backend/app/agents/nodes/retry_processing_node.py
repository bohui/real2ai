"""
Retry Processing Node for Contract Analysis Workflow

This module contains the node responsible for retrying failed processing steps.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class RetryProcessingNode(BaseNode):
    """
    Node responsible for retrying failed processing steps.

    This node performs:
    - Retry logic for failed steps
    - Exponential backoff implementation
    - Alternative method selection
    - Retry limit enforcement
    """

    def __init__(self, workflow):
        super().__init__(workflow, "retry_processing")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Retry failed processing step with appropriate strategy.

        Args:
            state: Current workflow state with retry information

        Returns:
            Updated state with retry results
        """
        try:
            self._log_step_debug("Starting retry processing", state)

            # Determine what step failed and needs retry
            retry_info = self._determine_retry_strategy(state)

            if not retry_info.get("can_retry", False):
                # Add targeted diagnostics to understand why retrying is not possible
                try:
                    progress = (
                        state.get("progress") if isinstance(state, dict) else None
                    )
                    step_history = (
                        (progress or {}).get("step_history", []) if progress else []
                    )
                    last_step = step_history[-1] if step_history else {}
                    self._log_step_debug(
                        "Retry not possible; logging diagnostic context",
                        state,
                        {
                            "reason": retry_info.get("reason"),
                            "has_progress": progress is not None,
                            "step_history_len": len(step_history),
                            "last_step": last_step.get("step"),
                            "state_keys": (
                                list(state.keys()) if isinstance(state, dict) else []
                            ),
                        },
                    )
                except Exception:
                    pass
                return self._handle_node_error(
                    state,
                    Exception("No retry strategy available"),
                    "Step cannot be retried",
                    {"retry_info": retry_info},
                )

            # Execute retry strategy
            retry_result = await self._execute_retry_strategy(state, retry_info)

            # Update state with retry results
            state["retry_result"] = retry_result

            # CRITICAL FIX: Ensure retry result has all required fields for workflow routing
            retry_data = {
                "retry_result": retry_result,
                "retry_strategy": retry_info.get("strategy", "unknown"),
                "retry_successful": retry_result.get("success", False),
                "retry_timestamp": datetime.now(UTC).isoformat(),
                # Add routing information for workflow
                "routing_target": retry_result.get("restart_target")
                or retry_result.get("target_step"),
                "strategy_executed": retry_result.get("strategy_executed", "unknown"),
            }

            if retry_result.get("success", False):
                step_name = "retry_processing_successful"
                # Log successful retry with routing info
                self._log_step_debug(
                    f"Retry processing successful - routing to: {retry_data.get('routing_target', 'unknown')}",
                    state,
                    {
                        "strategy": retry_info.get("strategy", "unknown"),
                        "routing_target": retry_data.get("routing_target"),
                        "strategy_executed": retry_result.get("strategy_executed"),
                    },
                )
            else:
                step_name = "retry_processing_failed"
                self._log_step_debug(
                    f"Retry processing failed - strategy: {retry_info.get('strategy', 'unknown')}",
                    state,
                    {"strategy": retry_info.get("strategy", "unknown")},
                )

            return self.update_state_step(state, step_name, data=retry_data)

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Retry processing failed: {str(e)}",
                {"retry_attempts": state.get("retry_attempts", 0)},
            )

    def _determine_retry_strategy(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Determine the appropriate retry strategy."""
        # Get retry count
        retry_count = state.get("retry_attempts", 0)
        max_retries = 3  # Maximum retry attempts

        if retry_count >= max_retries:
            return {"can_retry": False, "reason": "max_retries_exceeded"}

        # Determine failed step
        progress = state.get("progress")
        if progress is None:
            # Diagnostic log when progress is missing
            self._log_step_debug(
                "Progress missing during retry strategy determination",
                state,
                {"state_keys": list(state.keys()) if isinstance(state, dict) else []},
            )
            return {"can_retry": False, "reason": "no_progress_in_state"}

        step_history = progress.get("step_history", [])

        if not step_history:
            # Provide more detail when step history is empty
            self._log_step_debug(
                "Step history empty during retry strategy determination",
                state,
                {"progress_keys": list(progress.keys()) if progress else []},
            )
            return {"can_retry": False, "reason": "no_step_history"}

        # CRITICAL FIX: Check if we're trying to resume from a step that requires
        # document processing artifacts, but document processing failed
        current_step = progress.get("current_step", "unknown")
        if current_step in ["compile_report", "report_compilation", "final_validation"]:
            # Check if we have the required artifacts for these steps
            has_artifacts = self._check_required_artifacts(state)
            if not has_artifacts:
                # Document processing failed - we need to restart from the beginning
                self._log_step_debug(
                    f"Resuming from {current_step} but missing required artifacts - restarting from beginning",
                    state,
                    {"current_step": current_step, "has_artifacts": has_artifacts},
                )
                return {
                    "can_retry": True,
                    "reason": "restart_from_beginning",
                    "strategy": "restart_workflow",
                    "target_step": "validate_input",
                }

        # Get the last completed step
        last_step = step_history[-1] if step_history else {}
        last_step_name = last_step.get("step", "unknown")

        # Determine retry strategy based on the failed step
        if last_step_name.endswith("_failed"):
            # Extract the base step name (remove "_failed" suffix)
            base_step = last_step_name[:-7]  # Remove "_failed" (7 chars)

            # Check if we can retry this specific step
            if base_step in ["process_document", "extract_terms", "analyze_compliance"]:
                return {
                    "can_retry": True,
                    "reason": "step_specific_retry",
                    "strategy": "retry_step",
                    "target_step": base_step,
                    "retry_count": retry_count,
                }
            else:
                return {
                    "can_retry": False,
                    "reason": "step_not_retryable",
                    "failed_step": base_step,
                }

        # If we're here, we can retry the current step
        return {
            "can_retry": True,
            "reason": "general_retry",
            "strategy": "retry_current",
            "target_step": current_step,
            "retry_count": retry_count,
        }

    def _check_required_artifacts(self, state: RealEstateAgentState) -> bool:
        """Check if required artifacts exist for report compilation steps."""
        # Check for document processing artifacts
        document_data = state.get("document_data", {})
        extracted_text = document_data.get("content", "")

        # Check for contract analysis artifacts
        contract_terms = state.get("contract_terms")
        compliance_analysis = state.get("compliance_analysis")
        risk_assessment = state.get("risk_assessment")

        # Basic validation - we need at least some extracted text and basic analysis results
        has_text = bool(extracted_text and len(extracted_text.strip()) > 50)
        has_analysis = bool(contract_terms or compliance_analysis or risk_assessment)

        return has_text and has_analysis

    async def _execute_retry_strategy(
        self, state: RealEstateAgentState, retry_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the determined retry strategy."""
        strategy = retry_info.get("strategy", "generic_retry")
        retry_count = retry_info.get("retry_count", 0)

        # Update retry count
        state["retry_attempts"] = retry_count + 1

        try:
            if strategy == "restart_workflow":
                # CRITICAL FIX: Restart workflow from beginning when document processing failed
                # This happens when we're trying to resume from compile_report but have no artifacts
                self._log_step_debug(
                    "Executing workflow restart strategy - clearing failed state and restarting",
                    state,
                    {
                        "strategy": strategy,
                        "target_step": retry_info.get("target_step"),
                    },
                )

                # Clear error state and reset to initial state
                state["error_state"] = None
                state["parsing_status"] = None
                state["current_step"] = ["validate_input"]  # Reset to beginning

                # Clear any failed step indicators
                if "progress" in state and state["progress"]:
                    state["progress"]["current_step"] = "validate_input"
                    state["progress"]["percentage"] = 5  # Reset to initial progress

                # Mark retry as successful since we're restarting
                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "message": "Workflow restarted from beginning due to missing artifacts",
                    "restart_target": "validate_input",
                    "cleared_error_state": True,
                }

            elif strategy == "retry_step":
                # Retry a specific failed step
                target_step = retry_info.get("target_step", "unknown")
                self._log_step_debug(
                    f"Executing step retry strategy for: {target_step}",
                    state,
                    {"strategy": strategy, "target_step": target_step},
                )

                # Clear error state for the specific step
                if state.get("error_state"):
                    state["error_state"] = None

                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "target_step": target_step,
                    "message": f"Step {target_step} marked for retry",
                }

            elif strategy == "retry_current":
                # Retry the current step
                current_step = retry_info.get("target_step", "unknown")
                self._log_step_debug(
                    f"Executing current step retry strategy for: {current_step}",
                    state,
                    {"strategy": strategy, "target_step": current_step},
                )

                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "target_step": current_step,
                    "message": f"Current step {current_step} marked for retry",
                }

            elif strategy == "api_retry_with_backoff":
                # Implement exponential backoff
                import asyncio

                backoff_time = min(2**retry_count, 30)  # Max 30 seconds
                await asyncio.sleep(backoff_time)

                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "backoff_time": backoff_time,
                    "message": "API retry with backoff completed",
                }

            else:
                # Generic retry strategy
                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "message": "Generic retry completed",
                }

        except Exception as e:
            self._log_step_error(
                f"Retry strategy execution failed: {str(e)}",
                state,
                {"strategy": strategy, "error": str(e)},
            )
            return {
                "success": False,
                "strategy_executed": strategy,
                "error": str(e),
                "message": f"Retry strategy failed: {str(e)}",
            }
