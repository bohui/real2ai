### TODO: Document Processing — Paragraphs Enhancements

#### Current status (post-fix review)

- No critical blockers detected.
- SaveParagraphsNode
  - Uses `AuthContext.get_user_id()` and instantiates `UserDocsRepository(UUID(user_id))`.
  - Batch upsert with annotations and fallback to individual upserts implemented.
- ParagraphSegmentationNode
  - Uses `text_content`, accounts for "--- Page N ---" headers, normalizes text, and builds a normalized page offset map.
  - Stores `offsets_normalized` and `document_paragraph_index` in artifact `features`.
  - Sets `paragraph_params_fingerprint` in `state` and guards HMAC fallback.
- Repositories
  - Paragraph artifacts use advisory lock on insert; user paragraph batch upsert matches schema and return mapping aligns to `DocumentParagraph`.

#### Minor follow-ups (non-blocking)

- Workflow hardening
  - Add a conditional edge after `paragraph_segmentation` to route to `error_handling` when `state['error']` is present (parity with `extract_text`).

- Throughput control for large docs
  - Add a bounded semaphore in `ParagraphSegmentationNode` for upload/insert concurrency to avoid saturating storage/DB.
  - Consider processing segments in batches for very large documents.

#### Enablement

- With the current fixes, `paragraphs_enabled` can remain ON; functions should work as expected.


