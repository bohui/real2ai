## Cache, WebSocket, and Cache-Related Design Caveats

### Critical coupling issues
- **Separate WebSocket manager instances**: RESOLVED. The app now imports the shared singleton everywhere.
  - Now: Import `websocket_manager` from `app/services/websocket_singleton.py` in routers, tasks, and `main.py`.
  - Benefit: A single connection/session map ensures background task messages reach connected clients.

- **Inconsistent WebSocket session keys**: RESOLVED. All WS sends and Redis publications now use `document_id` as the session key, and the WS router bridges legacy `contract_id`/`content_hash` channels to `document_id`.

- **Missing Redis→WebSocket bridge**: RESOLVED. WS router subscribes to Redis channels for `document_id` and also bridges `contract_id` and `content_hash` to the same session.

### API/contract mismatches
- **Cache stats shape mismatch**: RESOLVED. Router maps `contract_analyses`/`property_data` to `contracts`/`properties` and sets `last_updated`.

- **Cleanup response mismatch**: RESOLVED. Router translates to `{contracts, properties}`.

### Consistency and security concerns
- **Content hash generation is inconsistent**: PARTIALLY ADDRESSED. REST hashing uses raw bytes; WS fallback remains for legacy docs. Future: ensure upload pipeline always sets raw-byte `content_hash`.

- **RLS vs cross-user cache semantics**: RESOLVED. WS checks read shared tables via service-role client to match REST behavior.

- **Cancellation scope risk**: IMPROVED. Cancellation only updates user-scoped `analysis_progress` and uses a safe RPC `cancel_user_contract_analysis`; avoids direct mutation of shared `contract_analyses`.

### Reliability and UX gaps
- **Stubbed health endpoints**: RESOLVED. Cache health pings Redis, reports service status, returns live stats and health score.

- **Admin enforcement missing on cleanup**: RESOLVED. Cleanup is admin-only.

- **RPC deployment risk**
  - Code depends on `upsert_contract_analysis` and `retry_contract_analysis`; ensure migrations are applied before relying on them.

- **Frontend metrics depend on incorrect backend stats**: RESOLVED. Frontend now guards zero/undefined and uses corrected backend mapping.

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