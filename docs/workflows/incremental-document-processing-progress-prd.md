## Incremental Document Processing Progress PRD

### Objective
Implement deterministic, monotonic analysis progress updates aligned to the PRD, including per-page increments during document processing and clear session-scoped events that the UI can render reliably.

### Event Sequence (and UI expectations)
- 0% when session connection is established (analysis initialized). UI: show "Upload document" as current (blue), others grey.
- 5% immediately after contract analysis workflow starts: `document_uploaded` ("Upload document"). UI: Upload document becomes green; "Initialize analysis" becomes current (blue).
- 7% after validate input completes: `validate_input` ("Initialize analysis"). UI: Initialize analysis green; "Extract text & diagrams" becomes current (blue).
- 8%–30% incremental per-page updates while extracting text/diagrams: `document_processing` ("Extract text & diagrams"). Each page completion advances percent by about 23/total_pages (rounded), strictly increasing, capped at 30%.
- 30% at extract-text node completion. UI: Extract text green; "Layout analysis" becomes current (blue).
- 30–50% during layout summarisation: `layout_summarise` ("Layout analysis"). UI: Progress advances within this range; on completion should reach 50%.
- 52% after document quality validation: `validate_document_quality` ("Document quality validation"). UI: Document quality validation green; "Identifying Terms" current (blue).
- 59% after terms extraction: `extract_terms` ("Identifying Terms"). UI: Terms extraction green; "Terms validation" current (blue).
- Subsequent fixed steps per PRD: 60% validate_terms_completeness, 68% analyze_compliance, 75% assess_risks, 85% generate_recommendations, 98% compile_report, 100% analysis_complete.

### Channel and Identifiers
- Use the contract/session channel exclusively for UI-facing progress (`event_type: analysis_progress`).
- Include identifiers: `{ session_id, contract_id }` (UUIDs). Never substitute `content_hash` into `contract_id`.
- Document-channel events (OCR) are allowed for audit but must not drive the UI.

### Monotonic Guard, Retry and Manual Force Restart
- Default behavior (auto/system restart, resume): enforce monotonic progress; skip emits when `new_percent <= last_percent`.
- Manual restart (explicit API): `user_preferences.force_restart: true`.
  - Optional `user_preferences.restart_from_step: <step_key>` allows baseline replay from any chosen prior step.
  - Baseline mapping (step → percent) used for replay: `{"document_uploaded":5,"validate_input":7,"document_processing":7,"layout_summarise":50,"validate_document_quality":52,"extract_terms":59,"validate_terms_completeness":60,"analyze_compliance":68,"assess_risks":75,"generate_recommendations":85,"compile_report":98,"analysis_complete":100}`.
  - If omitted/unknown, treat baseline as from the beginning (-1), allowing full replay (0/5/7...).

### Monotonic Guard and Persistence
- Before persisting/broadcasting: load last persisted or in-memory progress; apply the rules above.
- Persist via repository only (e.g., `AnalysisProgressRepository.upsert_progress`) to comply with repository pattern.
- Always broadcast the accepted update on the session topic after persistence.

### Document Processing Increments (7% → 30%)
- In `backend/app/agents/nodes/document_processing_subflow/extract_text_node.py`:
  - Extend `_extract_pdf_text_hybrid(...)` to accept an optional `notify_progress: Callable[[int, str, str], Awaitable[None]]`.
  - Track `total_pages` and `pages_processed`.
  - After each page completes:
    - Compute `next_percent = 7 + round((pages_processed / total_pages) * 23)`; clamp `[8..30]`.
    - Only emit if strictly greater than last emitted percent.
  - On node completion, ensure a final 30% emit (idempotent via monotonic guard).

### Layout Summarisation Progress (30–50%)
- In `backend/app/agents/nodes/document_processing_subflow/layout_summarise_node.py`:
  - Emit chunked progress within 30–50% range; ensure final 50% after successful completion of layout analysis
  - This provides granular progress tracking and ensures progress is only updated on success
  - Progress is emitted via the progress_callback when the node completes successfully

### Workflow Integration
- In `ContractAnalysisService`:
  - Emit 0% at session connection (or via replay on subscribe).
  - Emit 5% `document_uploaded` when workflow starts.
  - Emit 7% after `validate_input`.
  - Pass `notify_progress` into the document processing subflow so `_extract_pdf_text_hybrid` can call back.
  - Emit each subsequent fixed step at the defined percentages.

### Replay / Reconnect Behavior
- When a client (re)subscribes to the session channel, replay the last persisted progress so the UI can redraw current state.
- Do not emit any event if `progress_percent` would be lower than the stored value (unless manual restart baseline permits replay).

### Event Payload Shape
- `event_type: "analysis_progress"`
- `data: { session_id, contract_id, current_step, progress_percent, step_description, estimated_completion_minutes? }`
- Steps/percent targets (authoritative): see mapping above.

### Frontend Notes (for reference)
- Treat each incoming `analysis_progress` as: previous step completed; next step becomes active.
- After 0%: current is "Upload document". After 5%: mark Upload document done; current is "Initialize analysis". After 7%: mark Initialize done; current is "Extract text & diagrams". Then animate bar with 8–30%.

### Testing Plan
- Unit (backend):
  - Monotonic guard: lower/equal percentages are skipped for auto/system restarts.
  - Manual restart baseline: verify replay from provided `restart_from_step`.
  - Per-page mapping correctness for N pages (last page == 30%).
  - Exact emissions at 5%, 7%, 30%, and all fixed downstream steps.
  - Flag gating for 52%.
- Integration:
  - Full run: 0% → 5% → 7% → page stream (8–30%) → 30–50% → 52% → 59% → 60% → 68% → 75% → 85% → 98% → 100%.
  - Retry/resume mid-processing: no regressions (no backward updates), replay on reconnect.

### Acceptance Criteria
- UI shows the expected step transitions and incremental progress without duplicates or regressions.
- All progress updates are session-scoped, include correct UUIDs, and follow monotonic/force-restart rules.
- Repository-based persistence and broadcast are used consistently.
