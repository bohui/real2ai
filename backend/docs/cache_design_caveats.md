## Cache, WebSocket, and Cache-Related Design Caveats

### Critical coupling issues
- **Separate WebSocket manager instances**: Router creates its own `WebSocketManager` while background tasks use the singleton. Messages from tasks may not reach connected clients.
  - Where: `backend/app/router/websockets.py` (`websocket_manager = WebSocketManager()`), vs `backend/app/services/websocket_singleton.py` (singleton `websocket_manager`).
  - Fix: Use the singleton everywhere in the app (import `websocket_manager` from `app/services/websocket_singleton.py`).

- **Inconsistent WebSocket session keys**: Router sessions are keyed by `document_id`, but background tasks publish to `user_id` or `contract_id`.
  - Impact: Clients connected under `document_id` do not receive updates sent to `user_id`/`contract_id`.
  - Fix: Standardize on a single session key (recommend `document_id`) and use it consistently across router and tasks.

- **Missing Redis→WebSocket bridge**: Background tasks publish progress to Redis channels; the WS layer does not subscribe/forward to connected clients.
  - Fix: Add a Redis subscriber in the API process that forwards task updates to the correct `websocket_manager` session(s).

### API/contract mismatches
- **Cache stats shape mismatch**
  - Service returns keys for `contract_analyses` and `property_data`, but router exposes `contracts` and `properties` with placeholder values; frontend expects `contracts`/`properties`.
  - Fix: Map `contract_analyses`→`contracts`, `property_data`→`properties`, and compute a real `last_updated`.

- **Cleanup response mismatch**
  - Service returns `{contracts_deleted, properties_deleted, total_deleted}` while frontend expects `{data: {contracts, properties}}`.
  - Fix: Adapt router to translate or update frontend types/consumers accordingly.

### Consistency and security concerns
- **Content hash generation is inconsistent**
  - Different flows hash raw bytes vs extracted text vs metadata. This can cause false cache misses/hits.
  - Fix: Standardize on a single `content_hash` (prefer raw file bytes) and ensure upload/processing paths set and reuse the same hash.

- **RLS vs cross-user cache semantics**
  - Cache checks in REST may use service role (cross-user), while WS checks use user client (RLS), leading to divergent results.
  - Fix: Decide policy (allow cross-user cache hits by hash or not) and enforce consistently (via secure RPCs or service role where intended).

- **Cancellation scope risk**
  - Cancelling by `content_hash` can affect shared analyses if RLS is relaxed or not consistently applied to `contract_analyses`.
  - Fix: Cancel only the current user’s progress/records, or use a retry/attach model rather than cancelling shared rows.

### Reliability and UX gaps
- **Stubbed health endpoints**
  - Cache health and stats include hardcoded values.
  - Fix: Wire to actual checks (Redis ping, DB connectivity, recent rows, queue depth, etc.).

- **Admin enforcement missing on cleanup**
  - Cleanup endpoint is not restricted.
  - Fix: Require admin role/permission.

- **RPC deployment risk**
  - Code depends on `upsert_contract_analysis` and `retry_contract_analysis`; ensure migrations are applied before relying on them.

- **Frontend metrics depend on incorrect backend stats**
  - Efficiency calculations use `contracts/properties` totals that aren’t populated correctly.
  - Fix: After backend stats mapping is corrected, revalidate the frontend metrics.

### Recommended fixes (summary)
- Use the singleton `websocket_manager` across router and tasks; remove local instances.
- Pick and standardize one WS session key (use `document_id`) and update all send sites.
- Add a Redis subscriber within the API to relay task pub/sub events to WS clients.
- Unify `content_hash` generation (raw bytes) and ensure all flows set and reuse it.
- Align cache stats/cleanup response shapes with frontend expectations or update the frontend accordingly.
- Make cross-user cache policy explicit and consistent; use service-role RPCs if sharing is intended.
- Scope cancellations to the requesting user’s records only.
- Replace stubbed health with real checks; restrict cleanup to admins.
- Ensure RPC/migration functions exist in Supabase before runtime.