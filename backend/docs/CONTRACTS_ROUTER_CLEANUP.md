## Contracts Router Cleanup Plan

This document describes how to clean up `backend/app/router/contracts.py` by removing unused logic and updating outdated behavior to match current frontend usage and services.

### Goals
- Remove unused endpoints and dead pathways.
- Align responses and behaviors with the frontend (`frontend/src/services/api.ts`, `frontend/src/services/cacheService.ts`).
- Keep cache-first analysis flow intact.
- Minimize breaking changes by adding a thin alias for enhanced analysis.

## Endpoints to keep (no breaking changes)
- POST `/api/contracts/analyze`
- POST `/api/contracts/check-cache`
- GET `/api/contracts/history`
- POST `/api/contracts/bulk-analyze`
- GET `/api/contracts/{contract_id}/analysis`
- DELETE `/api/contracts/{contract_id}`
- GET `/api/contracts/{contract_id}/report` (update behavior; see below)

## Endpoints to add
- POST `/api/contracts/analyze-enhanced`
  - Purpose: Backward-compatibility with frontend `cacheService.startEnhancedContractAnalysis`.
  - Implementation: Thin alias calling `start_contract_analysis` with the same arguments.

Example:

```python
@router.post("/analyze-enhanced", response_model=ContractAnalysisResponse)
async def start_contract_analysis_enhanced(
    background_tasks: BackgroundTasks,
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_user_document_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> ContractAnalysisResponse:
    return await start_contract_analysis(
        background_tasks, request, user, document_service, cache_service
    )
```

## Endpoints to remove (not referenced by frontend/tests)
- GET `/api/contracts/performance-report`
- GET `/api/contracts/{contract_id}/status`
- GET `/api/contracts/{contract_id}/progress`
- GET `/api/contracts/notifications`
- POST `/api/contracts/notifications/{notification_id}/dismiss`
- GET `/api/contracts/debug/document/{document_id}`

Notes:
- These are not used by current frontend (`grep` shows no `/api/...` references) and add maintenance surface area.
- The notification system remains in use for emitting events; only the retrieval/dismiss endpoints are removed.

## Endpoint updates

### GET `/api/contracts/{contract_id}/report`
- Current: Returns analysis data or raw PDF (via a separate `/report/pdf`).
- Update: Return a JSON payload with a time-limited `download_url` (signed URL) to match `ApiService.downloadReport` expectations.
- Steps:
  1) Get analysis data by reusing `get_contract_analysis(contract_id)`.
  2) Generate PDF bytes via `generate_pdf_report` (background task already implemented).
  3) Upload PDF to storage (bucket `documents`) at `reports/{contract_id}/{analysis_id}.pdf`.
  4) Return `{ "download_url": signed_url, "format": "pdf" }`.

This also allows removing the separate `/report/pdf` raw-bytes endpoint.

### DB access consistency
- Unify database access in `get_contract_analysis` to use `await db_client.database.select(...)` (async helpers), replacing the direct `.table(...).select().eq().execute()` usage for:
  - `user_contract_views`
  - `documents`
  - `contract_analyses`

This mirrors the style used elsewhere in the router and clarifies RLS-enforced user-scoped operations.

### Logger duplication
- Remove the duplicate `logger = logging.getLogger(__name__)` declaration (there are two).

## Frontend alignment notes
- Frontend expects `download_url` from `GET /api/contracts/{id}/report?format=pdf`.
- Frontend calls `POST /api/contracts/analyze-enhanced`; add the alias route above.
- Frontend contains a `prepareContract` call to `/api/contracts/prepare` which is not implemented server-side. If unused in UI flows, remove the frontend method; otherwise, implement a minimal stub later.

## Implementation checklist (edits in `backend/app/router/contracts.py`)
- [ ] Add alias endpoint: `/api/contracts/analyze-enhanced` → calls `start_contract_analysis`.
- [ ] Update `/api/contracts/{contract_id}/report` to return a signed download URL; remove `/report/pdf`.
- [ ] Remove unused endpoints: `performance-report`, `{contract_id}/status`, `{contract_id}/progress`, `notifications` list/dismiss, `debug/document/{document_id}`.
- [ ] Unify DB access in `get_contract_analysis` (use `db_client.database.select` pattern).
- [ ] Remove duplicate `logger` declaration.

## Example response for updated report endpoint
```json
{
  "download_url": "https://.../signed-url",
  "format": "pdf"
}
```

## Risk and rollback
- Changes remove unused endpoints only; primary user flows remain intact.
- The new alias prevents breaking calls to `analyze-enhanced`.
- Keep a branch with removals so endpoints can be restored quickly if needed.

## Testing
- Verify frontend flows:
  - Start analysis
  - Check cache
  - History
  - Bulk analyze
  - Fetch analysis result
  - Delete analysis
  - Download report (assert `download_url` returned and usable)
- Ensure no frontend references to removed endpoints.


