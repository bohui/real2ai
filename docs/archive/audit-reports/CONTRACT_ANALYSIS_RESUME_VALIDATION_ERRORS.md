### Contract Analysis Resume/Validation Errors (2025-08-12)

#### Context
- Celery task resuming a contract analysis using checkpoints reported success steps like `compile_report` while upstream nodes lacked required state.
- Logs show premature checkpointing and missing prompt context enum leading to multiple node failures.

#### Symptoms (from logs)
- Resume selected: "Using checkpoint-based resume step: compile_report".
- Multiple node errors:
  - retry_processing: "No retry strategy available" (reason: no_progress_in_state)
  - document_quality_validation: "Document too short for analysis: 0 characters"
  - terms_validation: "No contract terms available for validation"
  - diagram_analysis: AttributeError: `'NoneType' object has no attribute 'get'` (on `document_metadata`)
  - final_validation: AttributeError: `ContextType` missing `VALIDATION` attribute
- Tracebacks include "RuntimeError: no running event loop" from `_run_async_node` (expected when falling back to `asyncio.run()` in Celery context; noise, not root cause).

#### Root Causes
1) Checkpoint timing is too early
   - Progress persistence and checkpoint creation occur before a step actually completes, so resume may jump to `compile_report` despite incomplete upstream state.

2) Resume skip list is incomplete
   - The progress-tracking wrapper only skips a subset of steps. Validation and diagram nodes are not included in its `_step_order`, so they still execute with empty state during resume.

3) Missing enum member in prompt context
   - `ContextType.VALIDATION` is referenced by validation nodes but not defined in `app/core/prompts/context.py`.

4) Unsafe state assumptions
   - `document_metadata` is initialized as `None` and read without coalescing to a dict in `DiagramAnalysisNode`.

#### Recommended Fixes
- Checkpointing/resume:
  - Move DB/registry progress persistence and checkpoint creation to after each step successfully returns, not before it runs.
  - Retain optional pre-step WS-only updates if desired, but ensure checkpoints are post-success.

- Expand resume skip coverage:
  - In the progress-tracking workflow wrapper, include and honor skip logic for:
    - `validate_document_quality`, `validate_terms_completeness`, `validate_final_output`, `analyze_contract_diagrams`.
  - Schedule persistence after `super().<step>(state)` returns successfully for each override.

- Prompt context enum:
  - Add `VALIDATION = "validation"` to `ContextType` in `backend/app/core/prompts/context.py`.

- Harden node/state handling:
  - Initialize `document_metadata` to `{}` (not `None`) in `ContractAnalysisService._create_initial_state`.
  - In `DiagramAnalysisNode.execute`, do `document_metadata = state.get("document_metadata") or {}` before `.get(...)` usage.

- Optional noise reduction:
  - Consider suppressing error-level logging for the expected `RuntimeError` in `_run_async_node` when falling back to `asyncio.run()`.

#### Files to Change
- `backend/app/services/contract_analysis_service.py`
  - In `_execute_with_progress_tracking()`: ProgressTrackingWorkflow
    - Extend `_step_order` to include validation/diagram nodes.
    - Override these methods to call persistence after `super()` completes.
  - In `_create_initial_state()`: set `"document_metadata": {}`.

- `backend/app/core/prompts/context.py`
  - Add `VALIDATION = "validation"` to `ContextType`.

- `backend/app/agents/nodes/diagram_analysis_node.py`
  - Coalesce `document_metadata` to `{}` before `.get(...)`.

- `backend/app/agents/contract_workflow.py` (optional)
  - Tweak `_run_async_node` logging level for the expected `RuntimeError` path.

#### Implementation Notes
- Keep repository pattern usage unchanged; adjustments are limited to service/workflow/nodes and prompt context.
- If pre-step UI updates are needed, separate them from checkpoint creation (pre-step WS; post-step DB/registry checkpoint).

#### Validation
- Unit/integration:
  - Simulate resume from `compile_report` with incomplete state; verify validation/diagram nodes are skipped and no exceptions are raised.
  - Verify `ContextType.VALIDATION` eliminates AttributeError in validation nodes.
  - Confirm `diagram_analysis` handles missing metadata without raising.

- Runtime behavior:
  - Ensure checkpoints correspond only to completed steps and resume consistently from last successful step.

#### Risks
- Changing when checkpoints are written affects retry semantics; verify idempotency and that UI progress remains responsive.


