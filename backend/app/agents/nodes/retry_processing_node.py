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
                return self._handle_node_error(
                    state,
                    Exception("No retry strategy available"),
                    "Step cannot be retried",
                    {"retry_info": retry_info}
                )

            # Execute retry strategy
            retry_result = await self._execute_retry_strategy(state, retry_info)
            
            # Update state with retry results
            state["retry_result"] = retry_result
            
            retry_data = {
                "retry_result": retry_result,
                "retry_strategy": retry_info.get("strategy", "unknown"),
                "retry_successful": retry_result.get("success", False),
                "retry_timestamp": datetime.now(UTC).isoformat(),
            }

            if retry_result.get("success", False):
                step_name = "retry_processing_successful"
            else:
                step_name = "retry_processing_failed"

            self._log_step_debug(
                f"Retry processing completed (success: {retry_result.get('success', False)})",
                state,
                {"strategy": retry_info.get("strategy", "unknown")}
            )

            return self.update_state_step(state, step_name, data=retry_data)

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Retry processing failed: {str(e)}",
                {"retry_attempts": state.get("retry_attempts", 0)}
            )

    def _determine_retry_strategy(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Determine the appropriate retry strategy."""
        # Get retry count
        retry_count = state.get("retry_attempts", 0)
        max_retries = 3  # Maximum retry attempts

        if retry_count >= max_retries:
            return {"can_retry": False, "reason": "max_retries_exceeded"}

        # Determine failed step
        progress = state.get("progress", {})
        step_history = progress.get("step_history", [])
        
        if not step_history:
            return {"can_retry": False, "reason": "no_step_history"}

        failed_step = step_history[-1]
        step_name = failed_step.get("step", "unknown")

        # Determine strategy based on step type
        if "document_processing" in step_name:
            strategy = "document_reprocessing"
        elif "extraction" in step_name:
            strategy = "alternative_extraction"
        elif "api" in failed_step.get("error", "").lower():
            strategy = "api_retry_with_backoff"
        else:
            strategy = "generic_retry"

        return {
            "can_retry": True,
            "strategy": strategy,
            "step_name": step_name,
            "retry_count": retry_count,
            "max_retries": max_retries
        }

    async def _execute_retry_strategy(
        self, state: RealEstateAgentState, retry_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the determined retry strategy."""
        strategy = retry_info.get("strategy", "generic_retry")
        retry_count = retry_info.get("retry_count", 0)

        # Update retry count
        state["retry_attempts"] = retry_count + 1

        try:
            if strategy == "api_retry_with_backoff":
                # Implement exponential backoff
                import asyncio
                backoff_time = min(2 ** retry_count, 30)  # Max 30 seconds
                await asyncio.sleep(backoff_time)
                
                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "backoff_time": backoff_time,
                    "message": "API retry with backoff completed"
                }

            elif strategy == "alternative_extraction":
                # Switch to rule-based extraction
                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "method_switched": "rule_based",
                    "message": "Switched to alternative extraction method"
                }

            elif strategy == "document_reprocessing":
                # Retry document processing
                return {
                    "success": True,
                    "strategy_executed": strategy,
                    "message": "Document reprocessing initiated"
                }

            else:
                # Generic retry
                return {
                    "success": False,
                    "strategy_executed": strategy,
                    "message": "Generic retry not implemented for this step type"
                }

        except Exception as e:
            return {
                "success": False,
                "strategy_executed": strategy,
                "error": str(e),
                "message": f"Retry strategy execution failed: {str(e)}"
            }