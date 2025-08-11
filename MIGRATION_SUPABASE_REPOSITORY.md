## PRD: Migrate Database Access to Repository Pattern (asyncpg) and Deprecate Supabase PostgREST Client

### Background and Problem

The backend currently issues most database operations via a custom Supabase client wrapper around PostgREST (`app/clients/supabase`). This creates several issues:

- Tight coupling to the PostgREST API shape and its error semantics
- Token race conditions and RLS edge cases in concurrent tasks
- Reduced flexibility for transactions, advisory locks, batching, and custom SQL

We have introduced repository modules backed by `asyncpg` to directly access Postgres while maintaining Supabase RLS semantics through per-request authentication context. Early repositories include:

- `app/services/repositories/artifacts_repository.py` (service role, shared artifacts)
- `app/services/repositories/user_docs_repository.py` (user-scoped, RLS)
- `app/services/repositories/runs_repository.py` (user-scoped, RLS)

This PRD defines how to complete this migration, deprecate PostgREST-based DB access, and standardize all DB operations through repositories.

### Goals

- Use repository classes for all database access with `asyncpg`
- Preserve RLS behavior by applying per-request JWT context to DB sessions
- Support per-user session connection pools to isolate RLS state; make pool mode configurable (shared vs per-user) with sensible defaults
- Maintain Supabase SDK only for Storage (file operations) and selected RPCs where necessary

### Non-Goals

- Replacing Supabase Storage usage
- Large schema/RLS policy changes

### Current State (observed)

- Document service (`app/services/document_service.py`) performs many DB writes/reads via `user_client.database.*` (legacy PostgREST path)
- Contract analysis service (`app/services/contract_analysis_service.py`) still imports `SupabaseClient` and uses `.database.upsert/select` in helper functions
- Auth router (`app/router/auth.py`) uses service-role client (PostgREST) for `profiles` table operations during register/login/refresh
- Repositories exist and are used for processing artifacts, user document pages/diagrams/paragraphs, and run/step tracking
- Auth middleware (`app/middleware/auth_middleware.py`) sets `AuthContext` per request; connection layer currently does not apply JWT claims to DB session

### Target Architecture

 - Connection management (`app/database/connection.py`):
   - Pooling modes (configurable):
     - Shared-per-process pool (default in low-user environments): one service-role pool; apply per-request auth via session GUCs on acquisition; ensure immediate reset between requests.
     - Per-user session pools (strict isolation): maintain a small pool per active user session (keyed by `user_id` or session key) to prevent any possibility of cross-user state; LRU + TTL eviction to control resource usage.
   - In all modes, `get_user_connection(user_id)` sets session GUCs:
     - `set_config('request.jwt.claims', <claims_json>, false)`
     - `set_config('role', 'authenticated'|'anon', false)`
   - Claims derived from `AuthContext` token; fallback to minimal `{sub, role, aud}` claims.

- Repositories (`app/services/repositories/`):
  - Encapsulate SQL with typed dataclass models where useful
  - Provide user-scoped and service-role operations as appropriate
  - Support transactions (e.g., `async with conn.transaction(): ...`), advisory locks, batching via `UNNEST`, etc.

- Services and Routers:
  - Replace all `supabase.database.*` CRUD calls with repository methods
  - Keep Supabase SDK for Storage (upload/download/list/signed URLs)
  - Replace RPCs that query DB data with repository SQL when feasible; for truly admin functions, retain service-role paths

### Scope and Affected Components

- Replace in `app/services/document_service.py`:
  - `user_client.database.create/update/read/upsert/select` → `DocumentsRepository` (new), `UserDocsRepository`, `RunsRepository`
  - System metrics via RPC → system repository or direct SQL function calls using service-role connection

- Replace in `app/services/contract_analysis_service.py` helpers:
  - `ensure_contract` and `upsert_contract_analysis` to repository-based upserts/selects

- Replace in `app/router/auth.py`:
  - Continue using Supabase Auth SDK for authentication flows
  - For profile table operations, either:
    - Keep minimal service-role PostgREST usage (OK for bootstrap), or
    - Introduce a small `ProfilesRepository` with service-role connection

### Repository Additions

- DocumentsRepository (user-scoped):
  - create_document(document)
  - update_document_status(document_id, status, error_details?)
  - list_user_documents(limit)
  - update_document_metrics(document_id, aggregated_metrics)

- ContractsRepository (service-role for shared identity by content_hash; user-scoped only if RLS is desired):
  - upsert_contract_by_content_hash(content_hash, contract_type, australian_state)
  - get_contract_id_by_content_hash(content_hash)

- AnalysesRepository (user-scoped or shared depending on table RLS):
  - upsert_analysis(content_hash, agent_version, status, result)
  - get_analysis_by_content_hash(content_hash)

### Implementation Plan

Phase 0: Session auth for user connections
- Implement per-request JWT GUCs in `get_user_connection(user_id)` so RLS works over direct SQL
- Introduce pool mode selector and config:
  - `DB_POOL_MODE` = `shared` | `per_user` (default based on deployment profile)
  - For `per_user`, create/destroy pools keyed by `user_id` with LRU + idle TTL
  - Add metrics/logging for `active_user_pools`, `evictions`, `pool_hits`, `pool_misses`

Phase 1: Feature flag and deprecation
- Add configuration flag `DB_USE_REPOSITORIES` (default true)
- Mark `SupabaseDatabaseClient` as deprecated for CRUD

Phase 2: Service/Router migration
- DocumentService: replace all `user_client.database.*` calls with repositories
- ContractAnalysisService: switch helper functions to repositories
- Auth Router: keep Supabase Auth; move profile select/insert to repository (optional)

Phase 3: Testing and validation
- Unit tests for each repository (CRUD, RLS behavior)
- Integration tests for documents and contract analysis flows
- Performance tests focusing on connection reuse and throughput

Phase 4: Cleanup
- Remove PostgREST-based DB CRUD paths after usages drop to zero
- Keep Supabase SDK only for Storage; optionally extract a dedicated storage client wrapper

### Mapping: Legacy → Repository

- `user_client.database.create('documents', data)` → `DocumentsRepository.create_document(data)`
- `user_client.database.update('documents', id, data)` → `DocumentsRepository.update_document_status(...)` or specific update methods
- `user_client.database.read('documents', filters, limit)` → `DocumentsRepository.list_user_documents(limit)`
- `user_client.database.upsert('document_diagrams', ...)` → `UserDocsRepository` methods or a dedicated `DiagramsRepository`
- Artifact-related CRUD → already implemented in `ArtifactsRepository`
- Runs/steps tracking → already implemented in `RunsRepository`

### Risks and Mitigations

- RLS mismatch: Ensure session GUCs mirror Supabase PostgREST behavior; comprehensive tests for cross-user access denial
- Connection management:
  - Shared mode: enforce short-lived acquisitions and reset GUCs to avoid claim bleed-over
  - Per-user mode: risk of connection exhaustion with many concurrent users; mitigate via small pool sizes (min/max), global cap (`DB_MAX_ACTIVE_USER_POOLS`), LRU eviction, idle TTL, and backpressure
- Performance regressions: Use batched inserts (`UNNEST`), advisory locks, and transactions where appropriate
- RPC parity: If some RPCs embed complex logic, call functions directly via SQL or leave as RPC via Supabase client where justified

### Test Plan

- Unit tests per repository covering success/error paths and RLS enforcement
- Integration tests for document upload, status transitions, page/diagram persistence
- Contract analysis helpers: tests for ensure/upsert flows
- Load tests to validate latency and throughput vs. legacy path
- Pooling tests:
  - Shared mode: simulate rapid cross-user acquisitions; assert zero cross-user leakage
  - Per-user mode: simulate N users > `DB_MAX_ACTIVE_USER_POOLS`; assert evictions and graceful degradation

### Per-User Session Pooling Details

- Configuration:
  - `DB_POOL_MODE=per_user`
  - `DB_USER_POOL_MIN_SIZE` (default 1), `DB_USER_POOL_MAX_SIZE` (default 2–4)
  - `DB_MAX_ACTIVE_USER_POOLS` (global cap to prevent exhaustion)
  - `DB_USER_POOL_IDLE_TTL_SECONDS` (e.g., 300) for eviction of inactive pools
  - `DB_POOL_EVICTION_POLICY=LRU`

- Lifecycle:
  - On first request for `user_id`, create pool; store in `{user_id: pool}` with last-used timestamp
  - On acquisition, set/verify session GUCs; on release, return to pool
  - On idle TTL expiry or over-capacity, close and delete least-recently-used pools

- Observability:
  - Export counters and gauges: `active_user_pools`, `evictions`, `pool_hits`, `pool_misses`
  - Warn when nearing `DB_MAX_ACTIVE_USER_POOLS`; recommend scaling or switching modes

### Rollout and Rollback

- Rollout: Ship behind `DB_USE_REPOSITORIES` (true by default), monitor logs and metrics
- Rollback: Toggle flag to temporarily re-enable legacy PostgREST DB paths, if still wired

### Deliverables

- Session auth in connection layer for user-scoped connections
- New repositories (`DocumentsRepository`, `ContractsRepository`, `AnalysesRepository`)
- Service and router edits to remove PostgREST DB CRUD calls
- Test suites updated/added

### Notes

- Supabase Storage remains via SDK; moving it later is optional and orthogonal
- For background tasks, use a short-lived user-scoped connection with applied claims or service-role connection as appropriate


