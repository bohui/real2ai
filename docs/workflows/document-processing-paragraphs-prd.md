### Document Processing: Paragraph Artifacts PRD and Implementation Plan

#### Objective

Introduce paragraph-level shared artifacts and per-user paragraph rows to enable stable, content-addressed paragraph references for analysis, citations, and UI annotations. Segment paragraphs after assembling full_text; support cross-page paragraphs via page_spans and offsets. Preserve full_text for global tasks while preferring paragraph/section-based chunking for retrieval, grounding, and citations.

#### Background

- Pages ≠ paragraphs. PyMuPDF returns page text; real paragraphs can span pages.
- Existing shared artifacts and per-user tables already exist:
  - Shared (service-role): `text_extraction_artifacts`, `artifact_pages`, `artifact_diagrams`, `artifact_paragraphs`.
  - User-scoped (RLS): `user_document_pages`, `user_document_diagrams`, `user_document_paragraphs`.
- Repos/utilities exist: `ArtifactsRepository` (paragraph methods), `UserDocsRepository` (upsert/get paragraphs), `ArtifactStorageService.upload_paragraph_text`.

#### Definitions

- content_hmac: Stable content address for a document.
- algorithm_version: Version of paragraphing algorithm.
- params_fingerprint: Hash of segmentation parameters/settings.
- page_spans: List of spans tying paragraph offsets back to source pages.
- features: JSON payload on artifacts; store `page_spans`, `start_offset`, `end_offset`, heuristics.

#### Scope

- In-scope
  - New nodes: `ParagraphSegmentationNode`, `SaveParagraphsNode`.
  - Persist shared paragraph artifacts; upsert user `user_document_paragraphs`.
  - Paragraph-aware chunking for downstream analysis (default).
  - Idempotent reuse by `(content_hmac, algorithm_version, params_fingerprint)`.
- Out-of-scope
  - Changing RLS policies (already correct).
  - Schema changes for `page_spans`/offset columns (use `features` JSON now; consider V2 later).

#### Functional Requirements

- Paragraph segmentation
  - Construct `full_text` by stitching pages (already done in `ExtractTextNode`).
  - Normalize whitespace; fix soft hyphenation; merge across page breaks when rules indicate continuity.
  - Determine boundaries using punctuation, capitalization, indentation, spacing; optionally sentence segmentation; optional LLM fallback for ambiguous runs (config-gated).
  - Emit paragraphs with:
    - `paragraph_index` (0-based per document)
    - `text`
    - `page_spans`: `[{page, start, end}]` mapping back to each page’s local offsets
    - `start_offset`/`end_offset` within global `full_text`

- Storage
  - For each paragraph:
    - Upload text via `ArtifactStorageService.upload_paragraph_text`.
    - Insert into `artifact_paragraphs` with `features` JSON including `page_spans` and offsets.
    - Uniqueness key (existing): `(content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index)`.
      - For cross-page paragraphs, set `page_number` to the first page in `page_spans`.
  - Upsert per-user `user_document_paragraphs` referencing the artifact id; conflict on `(document_id, page_number, paragraph_index)`.

- Idempotency and short-circuit
  - Before computing, query existing `artifact_paragraphs` by `(content_hmac, algorithm_version, params_fingerprint)`.
  - If present, skip segmentation and only upsert user rows.
  - On retries/cross-user duplicates: reuse shared artifacts; only upsert user rows.

- Analysis input defaults
  - Keep `full_text` for global summaries.
  - Default to paragraph/section chunks for retrieval prompts and citations; include artifact ids and page_spans for grounding.

- Subflow integration
  - Insert `ParagraphSegmentationNode` after `ExtractTextNode`.
  - Insert `SaveParagraphsNode` right after segmentation.
  - Downstream nodes can access `state['paragraphs']` (light structs) and `state['paragraph_artifacts']` (ids + meta).

#### Non-Functional Requirements

- Performance: O(n) in characters; no LLM calls by default; optional LLM disambiguation behind config.
- Observability: record counts, timings, reuse rates; link to run/step ids.
- Security: shared artifacts via service-role only; user rows through RLS (enforced by migrations).
- Reliability: deterministic segmentation given inputs; parameters baked into `params_fingerprint`.

#### Data Model (existing tables)

- `artifact_paragraphs`
  - Store in `features` JSON:
    - `page_spans`: array of `{page, start, end}`
    - `start_offset`, `end_offset`
    - `normalization`: `{hyphenation_fixed: bool, whitespace_normalized: bool}`
    - `boundary_signals`: optional diagnostics
- `user_document_paragraphs`
  - Reference `artifact_paragraphs.id`; `annotations` JSON for user flags/tags.

Example `features` JSON:

```json
{
  "page_spans": [{"page": 3, "start": 120, "end": 512}, {"page": 4, "start": 0, "end": 85}],
  "start_offset": 23145,
  "end_offset": 23742,
  "normalization": {"hyphenation_fixed": true, "whitespace_normalized": true}
}
```

#### Telemetry

- `paragraphs_count`, `avg_paragraph_len`, `segmentation_duration_ms`, `reuse_hit` (bool), `reused_paragraphs_count`.

#### Acceptance Criteria

- For a PDF that spans paragraphs across pages, artifacts created once and reused on rerun; user rows upserted.
- Downstream analysis consumes paragraph chunks with accurate citations to page ranges.
- End-to-end run shows added nodes and metrics; security policies hold.

---

## Implementation Plan

#### New Nodes

- `backend/app/agents/nodes/document_processing_subflow/paragraph_segmentation_node.py`
  - Inputs: `DocumentProcessingState` with `text_extraction_result.full_text`, `text_extraction_result.pages`, `content_hmac`.
  - Config: `PARAGRAPHS_ENABLED`, `PARAGRAPH_ALGO_VERSION`, `PARAGRAPH_PARAMS`, optional `PARAGRAPH_USE_LLM`.
  - Short-circuit: call `ArtifactsRepository.get_paragraph_artifacts(content_hmac, algorithm_version, params_fingerprint)`; if any exist, hydrate `state['paragraph_artifacts']` and a light `state['paragraphs']` (ids, indices, spans). Avoid downloading paragraph blobs unless needed.
  - Else:
    - Build global `full_text` and page offset map.
    - Segment into paragraphs; compute `page_spans`, offsets.
    - For each paragraph, upload text via `ArtifactStorageService.upload_paragraph_text`.
    - Insert artifacts via `ArtifactsRepository.insert_paragraph_artifact(..., features={page_spans, start_offset, end_offset, ...})`.
    - Set `state['paragraph_artifacts']` and `state['paragraphs']` (ids, indices, spans).

- `backend/app/agents/nodes/document_processing_subflow/save_paragraphs_node.py`
  - Inputs: `document_id`, `paragraph_artifacts`.
  - For each artifact, compute first page as `page_number` and call `UserDocsRepository.upsert_document_paragraph(document_id, page_number, paragraph_index, artifact_paragraph_id, annotations=None)`.
  - Idempotent; logs counts.

#### Subflow Wiring

- Edit `backend/app/agents/subflows/document_processing_workflow.py`:
  - Instantiate and add nodes: `paragraph_segmentation` and `save_paragraphs`.
  - Edges: `extract_text -> paragraph_segmentation -> save_paragraphs -> save_pages`.
  - Guard with config flag so feature can be toggled.
  - Ensure state carries `content_hmac` from earlier nodes; if missing, compute via `compute_content_hmac`.

#### Repos and Utils

- Use `ArtifactsRepository.get_paragraph_artifacts` and `insert_paragraph_artifact` (already present, supports `features`).
- Use `UserDocsRepository.upsert_document_paragraph` and `get_document_paragraphs`.
- Use `ArtifactStorageService.upload_paragraph_text`.
- Optional: add bulk insert helper for paragraph artifacts to reduce round-trips.

#### State Shape

- Extend `DocumentProcessingState` docstring to mention:
  - `paragraphs`: `List[{artifact_id, paragraph_index, page_spans, start_offset, end_offset}]`.
  - `paragraph_artifacts`: list of `ParagraphArtifact` metadata.

#### Config

- `backend/app/core/config.py` add:
  - `PARAGRAPHS_ENABLED: bool` (default True)
  - `PARAGRAPH_ALGO_VERSION: int` (e.g., 1)
  - `PARAGRAPH_PARAMS: dict` (hyphenation rules, min/max paragraph length, LLM toggle)
  - Use `compute_params_fingerprint(PARAGRAPH_PARAMS)`.

#### Analysis Consumption (follow-up)

- Downstream prompts default to paragraph chunks; include citations via `page_spans`.
- Keep switch to use `full_text` for holistic checks.

#### Metrics and Logging

- In `update_metrics_node`, optionally add `paragraph_count` and `avg_paragraph_length` if `state['paragraphs']` present.
- Log reuse events and counts.

#### Tests

- Unit
  - Segmentation: cross-page merges, hyphenation normalization, boundary heuristics.
  - Fingerprinting: stable segmentation given same params.
- Repository integration
  - Insert/get paragraph artifacts; re-run reuse; user upserts idempotency.
- E2E
  - End-to-end processing creates artifacts once; second run reuses; downstream analysis retrieves paragraph chunks.
- Security
  - Verify artifacts inaccessible via non-service-role; user rows enforce RLS.

#### Documentation

- Update `docs/workflows/langgraph-document-processing-workflow.md` to show new nodes.
- Add a note to `docs/cache-architecture.md` about paragraph artifacts caching and reuse.

#### Rollout

- Feature flag off-by-default in non-prod; run back-to-back tests on representative PDFs.
- Enable in prod gradually; monitor telemetry.

#### Risks & Mitigations

- Cross-page paragraph uniqueness: use first `page_number` in current schema; store full `page_spans` in `features` for fidelity.
- Memory/IO: avoid downloading all paragraph blobs when not needed; operate on metadata until text is required.
- LLM cost: keep disambiguation disabled by default.


