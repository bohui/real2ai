## Document Processing Refactor Review (consolidated)

### Snapshot of current state

- Main flow: `fetch_document_record → already_processed_check → mark_processing_started → extract_text → detect_diagrams_with_ocr → save_pages → save_diagrams → update_metrics → mark_basic_complete → build_summary`.
- Paragraph artifacts removed. Unified artifacts in use:
  - `artifact_pages` with `content_type ∈ {text, markdown, json_metadata}`
  - `artifact_diagrams` with `artifact_type ∈ {diagram, image_jpg, image_png}`
- External OCR support nodes exist for saving MD/JPG/JSON and extracting diagrams from MD.
- `extract_text` uploads full text + per-page text; sets `content_hmac`, `algorithm_version`, `params_fingerprint` in state and inserts unified page artifacts.

### Outstanding review items

- Already processed check (fingerprint source): Logic now uses artifact presence with lowercase statuses, but it passes `documents.content_hash` into methods that expect `content_hmac`. Confirm these are identical; otherwise compute `content_hmac` here (cheap download + hash) or add a converter. Without alignment, short-circuit may produce false negatives.
- Diagram persistence path: Detections are stored in state, but `SaveDiagramsNode` only maps existing artifacts. Upsert missing `artifact_diagrams` from `diagram_detection_result` (or have detection node persist) before mapping user rows.
- Async client usage in OCR node: When initializing `GeminiOCRService`, await `get_user_client()` or let the service resolve the client internally. Also enforce retries/backoff and `max_diagram_pages` from config.
- Page JPGs vs detection rendering: Either persist per-page JPGs via `save_page_jpg` and reuse for detection, or persist the ad-hoc rendered JPGs as `artifact_type='image_jpg'` to avoid repeated work.
- Repo cleanup stubs: Remove or guard calls to `repo.close()` in nodes that define `cleanup()` but whose repos have no `close()` method.
- Metrics cleanup: Remove paragraph reads/writes from `UpdateMetricsNode`; compute strictly from pages and diagram results.
- Migration robustness: Fix any stray quotes in DO $$ EXECUTE strings in `20240101000002_document_content.sql` to ensure migrations apply cleanly.

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
  - AlreadyProcessedCheck: ensure fingerprint alignment (convert or compute `content_hmac` if needed) when querying artifacts.
  - DetectDiagramsWithOCR: await user client, enforce `max_diagram_pages` and retries/backoff, and either persist detections or emit a canonical `diagram_processing_result` consumed by `save_diagrams`.
  - SaveDiagrams: upsert missing diagram artifacts from detection results, then map user rows.
  - SavePages: keep null-safe annotations; remove repo `.close()` calls.
  - UpdateMetrics: remove paragraph fields; compute from pages + diagram results.

- Repos/migration
  - Remove deprecated JPG/JSON-specific methods or add the missing dataclasses if they must remain.
  - Fix DO $$ EXECUTE quoting in the migration file.

- Wiring
  - If persisting page JPGs centrally, wire `save_page_jpg` before detection; otherwise persist rendered JPGs inside the detection node.

### Acceptance checklist

- Re-runs short-circuit via unified artifacts; no paragraph references anywhere.
- Documents reach `basic_complete` with page text artifacts; diagram artifacts persisted and user mappings created when detections exist.
- Stable idempotency keys for pages and diagrams; costs bounded by config; migrations apply cleanly; RLS intact.


