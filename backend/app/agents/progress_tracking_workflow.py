"""
Progress-tracking workflow that extends ContractAnalysisWorkflow with real-time progress updates.

This module provides a workflow implementation that sends progress updates
and manages resume functionality for contract analysis operations.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable, List

from app.agents.contract_workflow import ContractAnalysisWorkflow

logger = logging.getLogger(__name__)


class ProgressTrackingWorkflow(ContractAnalysisWorkflow):
    """
    Contract analysis workflow with integrated progress tracking and resume functionality.
    
    This workflow extends the base ContractAnalysisWorkflow to provide:
    - Real-time progress updates via WebSocket and external callbacks
    - Resume functionality from failed or interrupted steps
    - Enhanced error handling with progress state preservation
    """

    def __init__(
        self,
        parent_service,
        session_id: str,
        contract_id: str,
        progress_callback: Optional[Callable[[str, int, str], Awaitable[None]]] = None,
        resume_from_step: Optional[str] = None,
        *args,
        **kwargs
    ):
        """
        Initialize progress-tracking workflow.

        Args:
            parent_service: The ContractAnalysisService instance
            session_id: Unique session identifier for progress tracking
            contract_id: Contract identifier for WebSocket updates
            progress_callback: Optional callback for external progress persistence
            resume_from_step: Optional step name to resume from
            *args: Additional arguments passed to parent workflow
            **kwargs: Additional keyword arguments passed to parent workflow
        """
        super().__init__(*args, **kwargs)
        self.parent_service = parent_service
        self.session_id = session_id
        self.contract_id = contract_id
        self.progress_callback = progress_callback
        
        # Fixed order of primary steps for resume logic
        self._step_order: List[str] = [
            "validate_input",
            "process_document",
            "validate_document_quality",
            "extract_terms",
            "validate_terms_completeness",
            "analyze_compliance",
            "assess_risks",
            "analyze_contract_diagrams",
            "generate_recommendations",
            "validate_final_output",
            "compile_report",
        ]
        
        # Initialize resume logic
        self._resume_index = self._initialize_resume_logic(resume_from_step)

    def _initialize_resume_logic(self, resume_from_step: Optional[str]) -> int:
        """
        Initialize resume logic based on the provided step name.

        Args:
            resume_from_step: Step name to resume from (may include "_failed" suffix)

        Returns:
            Index in step order to resume from
        """
        if not resume_from_step:
            return 0

        try:
            # Handle both normal step names and failed step names (e.g., "extract_terms_failed")
            clean_step = resume_from_step
            if resume_from_step.endswith("_failed"):
                # Remove the "_failed" suffix to get the actual step name
                clean_step = resume_from_step[:-7]  # Remove "_failed" (7 chars)

            resume_index = self._step_order.index(clean_step)

            # If resuming from a failed step, we want to retry that step
            # so we don't skip it
            if resume_from_step.endswith("_failed"):
                logger.info(f"Resuming from failed step: {clean_step} (will retry)")
            else:
                logger.info(f"Resuming from step: {clean_step} (will skip completed steps)")
                
            return resume_index

        except ValueError:
            logger.warning(f"Unknown resume step: {resume_from_step}, starting from beginning")
            return 0

    def _should_skip(self, step_name: str) -> bool:
        """
        Determine if a step should be skipped based on resume logic.

        Args:
            step_name: Name of the step to check

        Returns:
            True if step should be skipped, False otherwise
        """
        try:
            idx = self._step_order.index(step_name)
        except ValueError:
            return False
        return idx < self._resume_index

    async def _schedule_persist(self, step: str, percent: int, description: str):
        """
        Persist progress update via external callback.

        Args:
            step: Step name
            percent: Progress percentage
            description: Human-readable description
        """
        if not self.progress_callback:
            return
        try:
            # Verify event loop stability before executing callback
            from app.core.async_utils import AsyncContextManager
            
            # Quick loop verification (lightweight check)
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
            logger.debug(f"[PROGRESS-STABILIZER] Executing callback for step '{step}' in loop {current_loop_id}")
            
            await self.progress_callback(step, percent, description)
        except Exception as e:
            # Log persistence errors but don't fail the workflow
            logger.warning(
                f"[ProgressTracking] Failed to persist progress: {e}",
                extra={
                    "step": step,
                    "percent": percent,
                    "description": (
                        description[:120]
                        if isinstance(description, str)
                        else str(description)
                    ),
                },
            )

    def _send_failure_progress(self, step: str, percent: int, error_msg: str):
        """
        Send failure progress update for step failures.
        
        Args:
            step: Step name that failed
            percent: Progress percentage at time of failure
            error_msg: Error message to display
        """
        try:
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                f"{step}_failed",
                percent,
                error_msg,
            )
        except Exception:
            # Don't let progress update failures crash the workflow
            pass

    # Step Implementations with Progress Tracking

    async def validate_input(self, state):
        """Validate input with progress tracking and resume support."""
        if self._should_skip("validate_input"):
            return state

        # Mark status as processing when first step begins
        try:
            if self.contract_id in self.parent_service.active_analyses:
                self.parent_service.active_analyses[self.contract_id]["status"] = "processing"
        except Exception:
            pass

        # Execute the step first
        try:
            result = super().validate_input(state)

            # Only send progress updates and persist checkpoints AFTER successful completion
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "validate_input",
                14,
                "Validating document and input parameters",
            )
            await self._schedule_persist(
                "validate_input", 14, "Validating document and input parameters"
            )

            return result
        except Exception as e:
            # Send failure progress for clarity
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "validate_input_failed",
                14,
                f"Input validation failed: {str(e)}",
            )
            # Re-raise the exception to maintain error handling
            raise

    async def process_document(self, state):
        """Process document with progress tracking."""
        if self._should_skip("process_document"):
            return state

        # Execute the step first
        result = super().process_document(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        self.parent_service._schedule_progress_update(
            self.session_id,
            self.contract_id,
            "process_document",
            28,
            "Processing document and extracting text content",
        )
        await self._schedule_persist(
            "process_document",
            28,
            "Processing document and extracting text content",
        )

        return result

    async def extract_contract_terms(self, state):
        """Extract contract terms with progress tracking."""
        if self._should_skip("extract_terms"):
            return state

        # Execute the step first
        try:
            result = super().extract_contract_terms(state)

            # Only send progress updates and persist checkpoints AFTER successful completion
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "extract_terms",
                42,
                "Extracting key contract terms using Australian tools",
            )
            await self._schedule_persist(
                "extract_terms",
                42,
                "Extracting key contract terms using Australian tools",
            )

            return result
        except Exception as e:
            # Send failure progress for clarity
            self._send_failure_progress(
                "extract_terms",
                42,
                f"Contract terms extraction failed: {str(e)}",
            )
            raise

    async def analyze_australian_compliance(self, state):
        """Analyze compliance with progress tracking."""
        if self._should_skip("analyze_compliance"):
            return state

        # Execute the step first
        result = super().analyze_australian_compliance(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        self.parent_service._schedule_progress_update(
            self.session_id,
            self.contract_id,
            "analyze_compliance",
            57,
            "Analyzing compliance with Australian property laws",
        )
        await self._schedule_persist(
            "analyze_compliance",
            57,
            "Analyzing compliance with Australian property laws",
        )

        return result

    async def assess_contract_risks(self, state):
        """Assess risks with progress tracking."""
        if self._should_skip("assess_risks"):
            return state

        # Execute the step first
        result = super().assess_contract_risks(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        self.parent_service._schedule_progress_update(
            self.session_id,
            self.contract_id,
            "assess_risks",
            71,
            "Assessing contract risks and potential issues",
        )
        await self._schedule_persist(
            "assess_risks", 71, "Assessing contract risks and potential issues"
        )

        return result

    async def generate_recommendations(self, state):
        """Generate recommendations with progress tracking."""
        if self._should_skip("generate_recommendations"):
            return state

        # Execute the step first
        result = super().generate_recommendations(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "generate_recommendations",
                85,
                "Generating actionable recommendations",
            )
            await self._schedule_persist(
                "generate_recommendations",
                85,
                "Generating actionable recommendations",
            )

        return result

    async def compile_analysis_report(self, state):
        """Compile report with progress tracking."""
        if self._should_skip("compile_report"):
            return state

        # Execute the step first
        result = super().compile_analysis_report(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "compile_report",
                98,
                "Compiling final analysis report",
            )
            await self._schedule_persist(
                "compile_report", 98, "Compiling final analysis report"
            )

        return result

    # Additional step overrides for complete resume coverage
    # Also override conditional checks to avoid triggering retries when skipping past steps

    def check_processing_success(self, state):
        """Override processing success check for resume logic."""
        # When resuming beyond process_document, force the success path
        if self._should_skip("process_document"):
            return "success"
        return super().check_processing_success(state)

    def check_document_quality(self, state):
        """Override document quality check for resume logic."""
        # When resuming beyond validate_document_quality, force quality_passed
        if self._should_skip("validate_document_quality"):
            return "quality_passed"
        return super().check_document_quality(state)

    def check_extraction_quality(self, state):
        """Override extraction quality check for resume logic."""
        # When resuming beyond extract_terms, force high_confidence
        if self._should_skip("extract_terms"):
            return "high_confidence"
        return super().check_extraction_quality(state)

    async def validate_document_quality_step(self, state):
        """Validate document quality with progress tracking."""
        if self._should_skip("validate_document_quality"):
            return state

        # Execute the step first
        result = super().validate_document_quality_step(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "validate_document_quality",
                18,
                "Validating document quality and readability",
            )
            await self._schedule_persist(
                "validate_document_quality",
                18,
                "Validating document quality and readability",
            )

        return result

    async def validate_terms_completeness_step(self, state):
        """Validate terms completeness with progress tracking."""
        if self._should_skip("validate_terms_completeness"):
            return state

        # Execute the step first
        result = super().validate_terms_completeness_step(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "validate_terms_completeness",
                50,
                "Validating completeness of extracted terms",
            )
            await self._schedule_persist(
                "validate_terms_completeness",
                50,
                "Validating completeness of extracted terms",
            )

        return result

    async def analyze_contract_diagrams(self, state):
        """Analyze contract diagrams with progress tracking."""
        if self._should_skip("analyze_contract_diagrams"):
            return state

        # Execute the step first
        result = super().analyze_contract_diagrams(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )
            await self._schedule_persist(
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )

        return result

    async def validate_final_output_step(self, state):
        """Validate final output with progress tracking."""
        if self._should_skip("validate_final_output"):
            return state

        # Execute the step first
        result = super().validate_final_output_step(state)

        # Only send progress updates and persist checkpoints AFTER successful completion
        if not (isinstance(result, dict) and result.get("error_state")):
            self.parent_service._schedule_progress_update(
                self.session_id,
                self.contract_id,
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )
            await self._schedule_persist(
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )

        return result