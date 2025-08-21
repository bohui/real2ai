## Unified Analysis Progress Sequencing PRD

### Goal
Make progress steps consistent across backend and frontend, with clear early signals and incremental OCR/diagram updates.

### Scope
- Single source of truth: contract/session progress channel for UI. Do not surface UI progress via document channels.
- Persist progress using repository methods only.

### Backend

#### Events and percentages (final)
- 5% `document_uploaded`: Emit when upload completes and on resume/retry before any other step.
- 7% `validate_input`: After resolving retry vs initial call and loading init parameters.
- 7–30% `document_processing`: Incremental updates during OCR and diagram extraction based on total pages; round to integer; cap at 30% when subworkflow finishes.
- 40% `layout_summarise`: After successful layout analysis and contract information extraction.
- 42% `validate_document_quality` (conditional via flag).
- 45% `extract_terms`.
- 50% `validate_terms_completeness`.
- 57% `analyze_compliance`.
- 71% `assess_risks`.
- 85% `generate_recommendations`.
- 98% `compile_report`.
- 100% `analysis_complete`.

#### Implementation points
- Upload handler (`POST /api/documents/upload`): after successful upload, publish 5% `document_uploaded` on the contract/session channel. On retry/resume (e.g., WS reconnected) emit this if no newer progress exists.
- `ContractAnalysisService._execute_with_progress_tracking`:
  - Add explicit 7% emission within `validate_input`.
  - Adjust existing emissions to the percentages above.
  - Gate `validate_document_quality` 34% emission behind a config flag.
  - Ensure 100% only when workflow actually finishes successfully.
- Document processing subflow (OCR + diagrams):
  - Pass total page count from `DocumentService`/document metadata.
  - During `extract_text` and `detect_diagrams_with_ocr`, emit incremental progress mapped to 7–30% range, rounded, monotonic, capped at 30% on completion.
  - Do not broadcast OCR progress over document channel for UI; persist only for audit/internal consumers.
- Reconnect/Retry:
  - On WS reconnect/subscription, replay last persisted progress from `analysis_progress` so UI can draw current state.
  - First step on retry/resume: emit 5% if no newer record exists.

#### Data/Persistence
- Use `AnalysisProgressRepository.upsert_progress` for idempotent writes keyed by `(content_hash, user_id)`; only increase `progress_percent`.
- Fields: `current_step`, `progress_percent`, `step_description`, `status`, timestamps, metadata.

#### Messaging
- Contract/session WS event format:
  - `event_type`: `analysis_progress`
  - `data`: `{ session_id, contract_id, current_step, progress_percent, step_description, estimated_completion_minutes? }`
- Map page-based updates into the same event.

#### Monotonic Guard and Manual Force Restart
- Default (auto/system restart): enforce monotonic progress; skip emitting when `new_percent <= last_percent`.
- Manual restart via API: pass `user_preferences.force_restart: true`.
  - Optional `user_preferences.restart_from_step: <step_key>` allows replay starting from any prior successful/current failing step.
  - Baseline for replay uses step→percent mapping below; if omitted/unknown, baseline is from the beginning (allow full replay).
  - Auto/system restarts MUST NOT set `force_restart` and remain strictly monotonic.

Baseline mapping for manual restart:
`{"document_uploaded":5,"validate_input":7,"document_processing":7,"validate_document_quality":34,"extract_terms":42,"validate_terms_completeness":50,"analyze_compliance":57,"assess_risks":71,"generate_recommendations":85,"compile_report":98,"analysis_complete":100}`

### Frontend
- Update `AnalysisProgress` steps to include (and render conditionally as needed):
  - `document_uploaded` (title: "Upload document")
  - `validate_input` (title: "Initialize analysis")
  - `document_processing` (title: "Extract text & diagrams")
  - `validate_document_quality` (conditional)
  - `extract_terms`
  - `validate_terms_completeness`
  - `analyze_compliance`
  - `assess_risks`
  - `generate_recommendations`
  - `compile_report`
- Source `progress_percent` and `step_description` exclusively from contract/session stream; ensure monotonic percent.
- If UI connects mid-run: show last persisted progress; continue live updates.
- If `validate_document_quality` is skipped, jump from ≤30% to 42%.

### Config/Flags
- `ENABLE_DOCUMENT_QUALITY_VALIDATION` (default: true) gates 34% step.
- `ENABLE_PER_PAGE_PROGRESS` (default: true) enables page-based 7–30% updates on session channel.

### Testing/Acceptance
- Unit (backend):
  - Verify emissions occur at exact percentages per step.
  - Per-page mapping: N pages -> last page maps to 30%, rounded, strictly increasing.
  - Skipping validation by flag yields correct next-step percentage.
  - Manual restart: verify baseline replay from provided `restart_from_step` and strict monotonicity for auto restarts.
- Integration (backend):
  - Upload emits 5% immediately; reconnect replays last persisted progress; final 100% only on success.
- Frontend:
  - `AnalysisProgress` renders new steps, handles conditional validation, shows incremental progress correctly.
  - Update tests for new step titles and keys where applicable.

### Documentation
- Update `backend/ARCHITECTURE_DESIGN.md` progress table to match final sequence and percentages.
- Note that the contract/session channel is the sole UI progress source.

### Non-functional
- Idempotent, strictly increasing progress writes.
- No duplicate or out-of-order messages across channels.
- Robust to retries and WS reconnects.

### Deliverables
- Backend: upload handler emission, `contract_analysis_service.py` emissions, document processing subflow per-page emissions, WS/session replay, config flags, repository-based persistence.
- Frontend: `AnalysisProgress.tsx` step list/mapping updates.
- Tests: backend unit/integration and frontend unit updates.
- Docs updated.
