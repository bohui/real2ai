# Document Processing Artifacts PRD

## 1. Summary
This PRD specifies a robust, idempotent, and secure design for sharing derived document-processing results (text, per-page content, diagrams, paragraphs) across users and sessions via content-addressed artifacts, while keeping user-scoped tables protected under RLS. The design supports:
- Fast short-circuit for duplicate documents uploaded by different users
- Per-step idempotency and retries (automatic and manual)
- Strict privacy and access control
- Versioned artifacts to allow safe reprocessing without overwriting previous results

## 2. Goals
- Reuse compute across users for identical documents, minimizing cost and latency
- Ensure every node in the LangGraph document-processing subflow is idempotent
- Support automatic transient retries and manual user-triggered retries
- Preserve multi-tenant isolation and privacy via RLS and service-role artifact access
- Provide clear observability and progress semantics without persisting large step-state blobs

## 3. Non-Goals
- Exposing artifact storage directly to clients
- User-specific transforms (annotations, redactions) as shared artifacts
- Replacing existing contract analysis flow; focus is on document processing subflow only

## 4. Users and Scenarios
- End users uploading identical contract files independently should experience fast processing after the first compute.
- Operators can safely re-run or upgrade processing (new OCR/LLM version) without data loss.
- System can recover from partial failures and retries without duplications.

## 5. Architecture Overview
### 5.1 Content Identity
- Compute server-side HMAC-SHA256 over raw file bytes: `content_hmac = HMAC(secret_key, file_bytes)`
- Use `content_hmac` as the artifact key (not raw SHA-256) to reduce existence oracle risk.
- Store `algorithm_version` and `params_fingerprint` to distinguish different processing variants.

### 5.2 Storage Layers
- Shared artifacts (service-role only):
  - `artifacts_full_text`: keyed by `(content_hmac, algorithm_version, params_fingerprint)`
  - `artifact_pages`: keyed by `(content_hmac, algorithm_version, params_fingerprint, page_number)`
  - `artifact_paragraphs`: keyed by `(content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index)`
  - `artifact_diagrams`: keyed by `(content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key)`
  - Large text blobs are stored in object storage; DB rows store URIs and hashes.
- User-scoped (RLS protected):
  - `documents`: references `artifact_text_id`; copies safe aggregates (pages, words)
  - `document_pages`: upsert by `(document_id, page_number)`, references `artifact_page_id`
  - `document_paragraphs`: upsert by `(document_id, page_number, paragraph_index)`, references `artifact_paragraph_id`
  - `document_diagrams`: upsert by `(document_id, page_number, diagram_key)`, references `artifact_diagram_id`
  - `analysis_progress` and processing runs: per user/run for UX, optional for correctness

### 5.3 Idempotency Strategy
- Nodes are idempotent using lookup-then-upsert with unique constraints.
- Existence of an artifact implies completion of compute; nodes can skip compute and hydrate user tables.
- User table upserts are keyed on natural keys per resource to make reruns safe no-ops.

### 5.4 Retry Strategy
- Automatic: LangGraph per-node retry for transient errors (timeouts, 429/5xx). Nodes must be safe to re-execute.
- Manual: User can retry the workflow. Nodes reuse artifacts; only missing user rows are upserted.
- Force reprocess: bump `algorithm_version` or change `params_fingerprint` to generate new artifacts, without deleting old ones.

### 5.5 Access Control
- Artifacts accessible only by backend with service role. No direct client access or querying by `content_hmac`.
- User tables enforce RLS, never expose cross-tenant data.

### 5.6 Observability
- Minimal progress records per run/step for UX and resume pointers.
- Tracing per node; include `run_id`, `document_id`, `content_hmac`.

## 6. Data Model
### 6.1 Shared Artifact Tables (service-role)
```sql
CREATE TABLE artifacts_full_text (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hmac text NOT NULL,
  algorithm_version int NOT NULL,
  params_fingerprint text NOT NULL,
  full_text_uri text NOT NULL,
  full_text_sha256 text NOT NULL,
  total_pages int NOT NULL,
  total_words int NOT NULL,
  methods jsonb NOT NULL,
  timings jsonb,
  created_at timestamptz DEFAULT now(),
  UNIQUE (content_hmac, algorithm_version, params_fingerprint)
);

CREATE TABLE artifact_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hmac text NOT NULL,
  algorithm_version int NOT NULL,
  params_fingerprint text NOT NULL,
  page_number int NOT NULL,
  page_text_uri text NOT NULL,
  page_text_sha256 text NOT NULL,
  layout jsonb,
  metrics jsonb,
  created_at timestamptz DEFAULT now(),
  UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number)
);

CREATE TABLE artifact_diagrams (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hmac text NOT NULL,
  algorithm_version int NOT NULL,
  params_fingerprint text NOT NULL,
  page_number int NOT NULL,
  diagram_key text NOT NULL,
  diagram_meta jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key)
);

-- Optional
CREATE TABLE artifact_paragraphs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hmac text NOT NULL,
  algorithm_version int NOT NULL,
  params_fingerprint text NOT NULL,
  page_number int NOT NULL,
  paragraph_index int NOT NULL,
  paragraph_text_uri text NOT NULL,
  paragraph_text_sha256 text NOT NULL,
  features jsonb,
  created_at timestamptz DEFAULT now(),
  UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index)
);
```

### 6.2 User-Scoped Tables (RLS)
```sql
-- documents: already exists. Add columns if missing.
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS artifact_text_id uuid,
  ADD COLUMN IF NOT EXISTS total_pages int,
  ADD COLUMN IF NOT EXISTS total_word_count int;

CREATE TABLE IF NOT EXISTS document_pages (
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  artifact_page_id uuid NOT NULL,
  annotations jsonb,
  flags jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  PRIMARY KEY (document_id, page_number)
);

CREATE TABLE IF NOT EXISTS document_diagrams (
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  diagram_key text NOT NULL,
  artifact_diagram_id uuid NOT NULL,
  annotations jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  PRIMARY KEY (document_id, page_number, diagram_key)
);

-- Optional
CREATE TABLE IF NOT EXISTS document_paragraphs (
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  paragraph_index int NOT NULL,
  artifact_paragraph_id uuid NOT NULL,
  annotations jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  PRIMARY KEY (document_id, page_number, paragraph_index)
);
```

### 6.3 Progress and Runs (RLS)
```sql
CREATE TABLE IF NOT EXISTS document_processing_runs (
  run_id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES profiles(id),
  status text NOT NULL CHECK (status IN ('queued','in_progress','completed','failed')),
  last_step text,
  error jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_processing_steps (
  run_id uuid NOT NULL REFERENCES document_processing_runs(run_id) ON DELETE CASCADE,
  step_name text NOT NULL,
  status text NOT NULL CHECK (status IN ('started','success','failed','skipped')),
  state_snapshot jsonb,
  error jsonb,
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  PRIMARY KEY (run_id, step_name)
);
```

## 7. Node Behavior (Idempotent)
- FetchDocumentRecordNode
  - Read document (storage_path, file_type, content_hmac or compute on demand using service), store to state.
- AlreadyProcessedCheckNode
  - If document has artifact_text_id and processing_status ∈ {basic_complete, analysis_complete}, short-circuit.
- MarkProcessingStartedNode
  - Set processing_status='processing' if not in a terminal state; set processing_started_at if null.
- ExtractTextNode
  - Lookup artifacts_full_text by (content_hmac, algorithm_version, params_fingerprint).
  - If exists: reuse; else compute and insert; use advisory lock on content_hmac to reduce stampede.
  - Materialize page artifacts similarly (compute missing pages only).
- SavePagesNode
  - Upsert (document_id, page_number) with artifact_page_id. No overwrite of annotations.
- AggregateDiagramsNode
  - Compute or reuse diagram artifacts; insert missing.
- SaveDiagramsNode
  - Upsert (document_id, page_number, diagram_key) with artifact_diagram_id.
- UpdateMetricsNode
  - Deterministically update documents.total_pages, total_word_count, text_extraction_method, etc.
- MarkBasicCompleteNode
  - Promote processing_status to 'basic_complete' and set processing_completed_at.
- BuildSummaryNode
  - Assemble ProcessedDocumentSummary from document + artifacts; no writes.
- ErrorHandlingNode
  - Mark run failed and document.processing_status='failed' with processing_errors.

All nodes write a small progress record: steps(status, minimal state ids) for UX; correctness relies on artifacts/user upserts.

## 8. Security and Privacy
- Artifacts: service-role only, encrypted at rest; strict audit logs; never exposed to clients.
- Use HMAC(secret, file_bytes) for artifact key to reduce content existence oracle.
- RLS on user tables; no cross-user reads. Clients never query by content_hmac.
- Optional tenant isolation: per-tenant HMAC secret to prevent cross-tenant dedup.

## 9. Versioning & Lifecycle
- `algorithm_version` denotes OCR/LLM pipeline version; `params_fingerprint` denotes config variations.
- Never overwrite artifacts; always insert new rows on version bump.
- GC policy: periodically remove artifacts with no referencing user documents for N days.

## 10. Implementation Plan (Detailed)
1) Config & Utilities
   - Add secret key to config: `DOCUMENT_HMAC_SECRET`
   - Utility: `compute_content_hmac(file_bytes) -> str`
   - Utility: `params_fingerprint(config) -> str`
2) Schema
   - Create SQL migrations for 6.1, 6.2, 6.3 tables. Add RLS policies for user tables; keep artifacts service-role only.
3) Repository Layer
   - `app/services/repositories/artifacts_repository.py`:
     - `get_full_text_artifact(key)`
     - `insert_full_text_artifact(...)` with ON CONFLICT DO NOTHING then SELECT
     - same for pages/diagrams/paragraphs
   - `app/services/repositories/user_docs_repository.py`:
     - `upsert_document_page(document_id, page_number, artifact_page_id)`
     - `upsert_document_diagram(document_id, page_number, diagram_key, artifact_diagram_id)`
     - `update_document_metrics(...)`, status helpers
   - `app/services/repositories/runs_repository.py`:
     - `create_run`, `upsert_step_status`, `mark_run_status`
4) ExtractTextNode Changes
   - Before compute: lookup text artifact; if found, set state and skip compute
   - If not found: compute full text and per-page, write object storage blobs, insert artifacts (text then pages)
   - After artifact resolve: hydrate state with artifact ids and minimal metrics
5) SavePagesNode & SaveDiagramsNode
   - Map artifact ids to user document upserts; do not store raw text
6) AggregateDiagramsNode
   - Compute page-level diagram metadata; insert artifact_diagrams with ON CONFLICT DO NOTHING
7) Metrics & Status Nodes
   - Update document aggregates and promote status idempotently
8) Progress Repository
   - On each node entry: upsert step started; on success/failure: update
   - Optional: derive resume step from artifacts if progress rows are missing
9) Retry Setup
   - Configure per-node retry policy (e.g., 3 attempts, exponential backoff) for transient exceptions
   - Manual retry API: accepts document_id, optional force flags and algorithm_version override
10) Observability
   - Add tracing spans per node including keys: run_id, document_id, content_hmac, algorithm_version
   - Emit metrics: hits vs. computes for artifacts; latencies per node

## 11. Testing Plan
- Unit
  - Artifact repository insert/select; ON CONFLICT races
  - User upserts idempotency
- Node-level
  - ExtractTextNode: reuse existing artifacts vs compute-and-insert path
  - Save* nodes: multiple invocations do not duplicate
- Subflow
  - Happy path from upload to basic_complete; short-circuit on second user
  - Failure in ExtractTextNode → retry, then manual retry
- Security
  - RLS tests: user cannot read other users' `document_*` rows
  - Artifact tables inaccessible without service role

## 12. Rollout
- Ship schema migrations
- Deploy code with feature flag: `enable_artifacts = true`
- Monitor artifact compute hit-rate and latency
- Add GC job after 2 weeks

## 13. Risks & Mitigations
- Stampede on first compute: advisory locks + ON CONFLICT + re-read
- Privacy concerns: use HMAC key, keep artifacts service-role only
- Storage growth: GC unreferenced artifacts, compress text blobs
- OCR nondeterminism: versioning isolates runs; params_fingerprint captures config

## 14. Open Questions
- Do we store page text in user tables for faster read? Default: no; rely on artifacts + caching.
- Tenant isolation requirement? If yes, scope HMAC secret per tenant.
- Exact retry policy per node (time budgets)? To be finalized with SRE.

## 15. Appendix: Pseudocode for ExtractTextNode
```python
# Pseudocode
artifact = artifacts_repo.get_full_text_artifact(content_hmac, algo_ver, params_fp)
if not artifact:
    with acquire_advisory_lock(content_hmac):
        artifact = artifacts_repo.get_full_text_artifact(content_hmac, algo_ver, params_fp)
        if not artifact:
            result = compute_text_and_pages(file_bytes, config)
            text_uri, page_uris = store_to_object_storage(result)
            artifact = artifacts_repo.insert_full_text_artifact(..., text_uri, ...)
            for page in result.pages:
                artifacts_repo.insert_page_artifact(...)
# hydrate user tables
for page in artifacts_repo.list_page_artifacts(content_hmac, algo_ver, params_fp):
    user_docs_repo.upsert_document_page(document_id, page.number, page.id)
```
