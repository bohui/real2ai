"""
Progress-tracking variant of the ContractAnalysisWorkflow.

This workflow extends the base workflow with optional progress updates and resume support,
without requiring a separate workflow instance per execution.

Per-run values (session_id, contract_id, callbacks, resume step) are read from the state:
- state["notify_progress"]: Optional async callback(step: str, percent: int, desc: str)
- state["resume_from_step"]: Optional step name to resume from; steps prior to this are skipped
- state["session_id"], state["contract_id"]: Used for WebSocket progress via the parent service
"""

import logging
from typing import Any, Dict, Optional

from app.agents.contract_workflow import ContractAnalysisWorkflow

logger = logging.getLogger(__name__)


class ProgressTrackingWorkflow(ContractAnalysisWorkflow):
    """Workflow with built-in progress tracking and resume support.

    Reads per-run context from the state, so a single instance can serve multiple runs safely.
    """

    # Fixed order of primary steps per PRD for resume logic
    _STEP_ORDER = [
        "document_uploaded",  # 5% (emitted by service before workflow starts)
        "validate_input",  # 7%
        "process_document",  # 7-30%
        "validate_document_quality",  # 34%
        "extract_terms",  # 42%
        "validate_terms_completeness",  # 50%
        "analyze_compliance",  # 57%
        "assess_risks",  # 71%
        "generate_recommendations",  # 85%
        "compile_report",  # 98%
        "analysis_complete",  # 100%
    ]

    def __init__(self, parent_service: Any, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_service = parent_service

    # ---------- Helpers ----------
    def _get_resume_index(self, state: Dict[str, Any]) -> int:
        resume_from_step: Optional[str] = (state or {}).get("resume_from_step")
        if not resume_from_step:
            return 0
        # Handle failed suffix like "extract_terms_failed"
        clean_step = (
            resume_from_step[:-7]
            if resume_from_step.endswith("_failed")
            else resume_from_step
        )
        try:
            return self._STEP_ORDER.index(clean_step)
        except ValueError:
            logger.warning(
                f"Unknown resume step: {resume_from_step}; starting from beginning"
            )
            return 0

    def _should_skip(self, step_name: str, state: Dict[str, Any]) -> bool:
        try:
            step_idx = self._STEP_ORDER.index(step_name)
        except ValueError:
            return False
        return step_idx < self._get_resume_index(state)

    async def _persist_progress(
        self, state: Dict[str, Any], step: str, percent: int, desc: str
    ) -> None:
        # Best-effort async persistence callback from state
        notify = (state or {}).get("notify_progress")
        if notify:
            try:
                await notify(step, percent, desc)
            except Exception as persist_error:
                logger.debug(
                    f"[ProgressTracking] Persist callback failed: {persist_error}",
                    exc_info=False,
                )

    def _ws_progress(
        self, state: Dict[str, Any], step: str, percent: int, desc: str
    ) -> None:
        # Schedule WebSocket update via parent service (non-blocking)
        try:
            session_id = (state or {}).get("session_id")
            contract_id = (state or {}).get("contract_id") or session_id
            if session_id and contract_id:
                self.parent_service._schedule_progress_update(
                    session_id, contract_id, step, percent, desc
                )
        except Exception:
            pass

    # ---------- Step Overrides with Progress ----------
    async def validate_input(self, state):
        if self._should_skip("validate_input", state):
            return state

        # Mark session as processing when first step begins
        try:
            contract_id = (state or {}).get("contract_id")
            if contract_id in self.parent_service.active_analyses:
                self.parent_service.active_analyses[contract_id][
                    "status"
                ] = "processing"
        except Exception:
            pass

        result = super().validate_input(state)
        self._ws_progress(state, "validate_input", 7, "Initialize analysis")
        await self._persist_progress(state, "validate_input", 7, "Initialize analysis")
        return result

    async def process_document(self, state):
        if self._should_skip("process_document", state):
            return state

        self._ws_progress(state, "document_processing", 7, "Extract text & diagrams")
        result = super().process_document(state)
        await self._persist_progress(
            state, "document_processing", 30, "Extract text & diagrams"
        )
        return result

    async def validate_document_quality_step(self, state):
        if self._should_skip("validate_document_quality", state):
            return state

        # Optional feature flag from settings is handled in the node logic as well; we still send progress when run
        self._ws_progress(
            state,
            "validate_document_quality",
            34,
            "Validating document quality and readability",
        )
        await self._persist_progress(
            state,
            "validate_document_quality",
            34,
            "Validating document quality and readability",
        )
        return super().validate_document_quality_step(state)

    async def extract_contract_terms(self, state):
        if self._should_skip("extract_terms", state):
            return state

        self._ws_progress(
            state,
            "extract_terms",
            42,
            "Extracting key contract terms using Australian tools",
        )
        await self._persist_progress(
            state,
            "extract_terms",
            42,
            "Extracting key contract terms using Australian tools",
        )
        return super().extract_contract_terms(state)

    async def analyze_australian_compliance(self, state):
        if self._should_skip("analyze_compliance", state):
            return state

        self._ws_progress(
            state,
            "analyze_compliance",
            57,
            "Analyzing compliance with Australian property laws",
        )
        await self._persist_progress(
            state,
            "analyze_compliance",
            57,
            "Analyzing compliance with Australian property laws",
        )
        return super().analyze_australian_compliance(state)

    async def assess_contract_risks(self, state):
        if self._should_skip("assess_risks", state):
            return state

        self._ws_progress(
            state, "assess_risks", 71, "Assessing contract risks and potential issues"
        )
        await self._persist_progress(
            state, "assess_risks", 71, "Assessing contract risks and potential issues"
        )
        return super().assess_contract_risks(state)

    async def generate_recommendations(self, state):
        if self._should_skip("generate_recommendations", state):
            return state

        self._ws_progress(
            state,
            "generate_recommendations",
            85,
            "Generating actionable recommendations",
        )
        await self._persist_progress(
            state,
            "generate_recommendations",
            85,
            "Generating actionable recommendations",
        )
        return super().generate_recommendations(state)

    async def analyze_contract_diagrams(self, state):
        if self._should_skip("analyze_contract_diagrams", state):
            return state

        result = super().analyze_contract_diagrams(state)
        # Only send progress after successful completion (no error_state)
        if not (isinstance(result, dict) and result.get("error_state")):
            self._ws_progress(
                state,
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )
            await self._persist_progress(
                state,
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )
        return result

    async def validate_final_output_step(self, state):
        if self._should_skip("validate_final_output", state):
            return state

        result = super().validate_final_output_step(state)
        # Only send progress after successful completion (no error_state)
        if not (isinstance(result, dict) and result.get("error_state")):
            self._ws_progress(
                state,
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )
            await self._persist_progress(
                state,
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )
        return result

    # ---------- Conditional Edge Overrides to handle resume skip ----------
    def check_processing_success(self, state):
        if self._should_skip("process_document", state):
            return "success"
        return super().check_processing_success(state)

    def check_document_quality(self, state):
        if self._should_skip("validate_document_quality", state):
            return "quality_passed"
        return super().check_document_quality(state)

    def check_extraction_quality(self, state):
        if self._should_skip("extract_terms", state):
            # Only force high_confidence when contract_terms exist; otherwise, signal error to avoid invalid validation
            try:
                contract_terms = (
                    state.get("contract_terms") if isinstance(state, dict) else None
                )
            except Exception:
                contract_terms = None
            return "high_confidence" if contract_terms else "error"
        return super().check_extraction_quality(state)

    def check_terms_validation_success(self, state):
        # When resuming beyond validate_terms_completeness, treat as success to avoid unintended retries/errors
        if self._should_skip("validate_terms_completeness", state):
            return "success"
        return super().check_terms_validation_success(state)
