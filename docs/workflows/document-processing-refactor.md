## Document Processing Refactor Review (consolidated)

### Snapshot of current state

- Main flow: `fetch_document_record → already_processed_check → mark_processing_started → extract_text → detect_diagrams_with_ocr → save_pages → save_diagrams → update_metrics → mark_basic_complete → build_summary`.
- Paragraph artifacts removed. Unified artifacts in use:
  - `artifact_pages` with `content_type ∈ {text, markdown, json_metadata}`
  - `artifact_diagrams` with `artifact_type ∈ {diagram, image_jpg, image_png}`
- External OCR support nodes exist for saving MD/JPG/JSON and extracting diagrams from MD.
- `extract_text` uploads full text + per-page text; sets `content_hmac`, `algorithm_version`, `params_fingerprint` in state and inserts unified page artifacts.

### Outstanding need-to-fix items

- Already processed check

- Diagram artifacts
  - Keep deterministic `diagram_key` (`diagram_page_{page}_{type}_{seq}`) when upserting from `diagram_processing_result` to ensure idempotency across re-runs.

- OCR node caps
  - Ensure `max_diagram_pages` limit and retries/backoff are enforced in per-page detection to control costs and transient failures.

- Page JPG persistence strategy
  - Either wire a `save_page_jpg` step before detection and reuse those images, or persist in-node rendered JPGs as `artifact_type='image_jpg'` to avoid re-rendering on re-runs.

- Repo cleanup calls
  - Remove/guard any `repo.close()` calls in nodes since repos don’t expose `close()`.

- Migration validation
  - Apply migration on staging to confirm DO $$ EXECUTE quoting and constraints behave as expected.

### Medium priority

- Consistent `text_extraction_result` usage: Standardize on the typed object with attribute access across nodes; remove dict `.get(...)` patterns where not needed.
- Page JPGs vs detection rendering: Design says MuPDF saves page JPGs. Currently the OCR node renders JPGs on the fly and doesn’t persist them. Either wire `save_page_jpg` before detection and reuse stored JPGs, or persist the rendered JPGs as `artifact_type='image_jpg'` to avoid repeat work.
- Diagram key idempotency: Adopt a stable key format for OCR detections (e.g., `diagram_page_{page}_{type}_{seq}`) to enable ON CONFLICT semantics.
- Null-safe annotations in `SavePagesNode`: Guard nested fields like `page.content_analysis.layout_features` before dict conversion.
- Remove deprecated repo methods or reintroduce missing dataclasses (`PageJPGArtifact`, `PageJSONArtifact`) referenced by legacy methods to prevent NameError if used.
- Centralize status values: Use `supabase_models.DocumentStatus` to avoid string casing drift.

### Low priority

- Observability: Add counters/timers for per-page OCR (selected vs processed), skipped reasons, and backoff metrics.
- Storage DPI: Document fixed zoom/DPI for page renders; keep consistent for reproducibility.
- Docs: Update `docs/workflows/document-processing-workflow.md` to reflect new edges and remove paragraph nodes; link external OCR workflow doc.
- Tests: Add unit tests for short-circuit behavior with unified artifacts and for diagram persistence/mapping paths.

### Actionable fixes (checklist)

- Nodes
  - AlreadyProcessedCheck: align fingerprint (compute/convert to `content_hmac`) before artifact queries.
  - DetectDiagramsWithOCR: enforce `max_diagram_pages` and retries/backoff from config; persist rendered JPGs if not using a separate `save_page_jpg` step.
  - SaveDiagrams: ensure deterministic `diagram_key` and upsert artifacts when missing, then map user rows.
  - SavePages: keep null-safe annotations; remove/guard repo `.close()` calls.
  - UpdateMetrics: paragraph-free metrics only.

- Repos/migration
  - Remove deprecated JPG/JSON-specific methods or add the missing dataclasses if they must remain.
  - Fix DO $$ EXECUTE quoting in the migration file.

- Wiring
  - If persisting page JPGs centrally, wire `save_page_jpg` before detection; otherwise persist rendered JPGs inside the detection node.

### Acceptance checklist

- Re-runs short-circuit via unified artifacts; no paragraph references anywhere.
- Documents reach `basic_complete` with page text artifacts; diagram artifacts persisted and user mappings created when detections exist.
- Stable idempotency keys for pages and diagrams; costs bounded by config; migrations apply cleanly; RLS intact.


