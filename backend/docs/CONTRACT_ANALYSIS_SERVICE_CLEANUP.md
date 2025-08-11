## ContractAnalysisService Cleanup Plan

This plan outlines targeted refactors to simplify `app/services/contract_analysis_service.py`, clarify boundaries, and align with the repository-based data layer and WebSocket progress patterns.

### Goals
- Reduce responsibilities and coupling in `ContractAnalysisService`.
- Extract database helpers to repositories; remove `SupabaseClient` dependencies from the service layer.
- Decouple WebSocket details via an injected progress publisher interface.
- Normalize configuration, error handling, and response creation.
- Preserve public API and test compatibility while enabling incremental migration.

### Current Observations
- The service handles multiple concerns in one module:
  - Workflow orchestration and configuration resolution
  - PromptManager initialization
  - WebSocket progress tracking and fallback to Redis
  - Service health/metrics aggregation
  - Database helpers (`ensure_contract`, `upsert_contract_analysis`) that import `SupabaseClient`
  - Factory function and exports
- Progress tracking uses an inner subclass `ProgressTrackingWorkflow` with hard-coded step mapping.
- Configuration/model defaults are resolved directly (OpenAI model name), rather than via a central client/service config.
- Mixed typing in the workflow state and response fields leads to conversions and conditionals (e.g., `progress` dict vs state fields).

Relevant references:

```1:50:backend/app/services/contract_analysis_service.py
class ContractAnalysisService:
    """
    Unified contract analysis service with real-time progress tracking and enhanced features
    ...
``` 

```1138:1218:backend/app/services/contract_analysis_service.py
async def ensure_contract(...)
async def upsert_contract_analysis(...)
```

```1200:1267:backend/app/router/websockets.py
# uses ensure_contract and upsert_contract_analysis helpers
```

See `MIGRATION_SUPABASE_REPOSITORY.md` for the repo migration strategy.

### Design Principles
- Separation of concerns: service orchestrates the workflow and composes collaborators; it does not own persistence or transport mechanics.
- Stable interface: maintain `ContractAnalysisService` public methods and exports.
- Dependency injection: accept collaborators (progress publisher, repositories) via constructor or factory.
- Thin compatibility shims: keep `start_analysis` as a delegated alias to avoid breaking callers.

### Target Architecture
- `ContractAnalysisService` focuses on:
  - Validating inputs
  - Creating initial workflow state
  - Invoking the workflow
  - Emitting progress via an injected `ProgressPublisher` interface
  - Producing typed responses and service metrics

- New interfaces/modules:
  - `app/services/interfaces.py`
    - `class ProgressPublisher: async def publish(self, session_id, event) -> None`
    - `class IContractAnalyzer` (if not already defined; tests reference it)
  - `app/services/progress/websocket_publisher.py` (adapter around `WebSocketManager`)
  - `app/services/repositories/contracts_repository.py`
    - `async def upsert_by_content_hash(content_hash, contract_type, australian_state) -> str`
  - `app/services/repositories/analyses_repository.py`
    - `async def upsert(content_hash, agent_version, status, result) -> str`

### Cleanup Tasks (Incremental)
1) Extract DB helpers to repositories
   - Move `ensure_contract` to `ContractsRepository` (service-role connection).
   - Move `upsert_contract_analysis` to `AnalysesRepository` (user-scoped connection; implement RPC-first then upsert fallback).
   - Update `backend/app/router/websockets.py` to use repositories directly.
   - Remove `SupabaseClient` import from the service file.

2) Introduce `ProgressPublisher` adapter
   - Create an adapter that wraps `WebSocketManager` and exposes a simple `publish_progress`/`publish_event` API.
   - Change `ContractAnalysisService` to depend on `ProgressPublisher` (optional), not on `WebSocketManager` directly.
   - Keep current behavior via factory wiring a WebSocket-based publisher.

3) Normalize config and model resolution
   - Centralize default model selection (OpenAI model) in a dedicated config utility; inject via factory.
   - Simplify `__init__`: pass `EnhancedWorkflowConfig`, validate once, and log summary.

4) Flatten progress tracking logic
   - Extract `ProgressTrackingWorkflow` into a small helper module (or accept a `progress_callback` passed into the workflow).
   - Keep the ordered step list in one place; accept `resume_from_step` consistently (strip `_failed`).
   - Ensure cancellation hooks can short-circuit future steps (optional; non-breaking addition).

5) Response and metrics cleanup
   - Consolidate success determination and service metrics update in one place.
   - Ensure `workflow_metadata.progress_percentage`, `steps_completed`, and `total_steps` are consistently derived.
   - Keep `StartAnalysisResponse` shim intact.

6) Type safety and schema alignment
   - Use consistent enum parsing for `AustralianState` with a strict resolver.
   - Ensure state shape matches typed expectations (avoid list vs scalar mismatches); use clear `state["progress"]` schema.

7) Logging and error normalization
   - Standardize error messages and include `session_id` and elapsed time.
   - Downgrade noisy logs to `debug`; keep user-actionable problems at `warning`.

### Proposed Public API (unchanged)
- Keep:
  - `analyze_contract(...) -> ContractAnalysisServiceResponse`
  - `start_analysis(...) -> StartAnalysisResponse` (delegates)
  - `get_service_health()`, `get_service_metrics()`
  - `reload_configuration()`
  - Factory: `create_contract_analysis_service(...)`

### File/Code Moves
- Remove from `contract_analysis_service.py`:
  - `ensure_contract`, `upsert_contract_analysis` (moved to repositories)
  - Direct `SupabaseClient` import
- Add:
  - `app/services/progress/progress_publisher.py` (interface)
  - `app/services/progress/websocket_progress_publisher.py` (adapter)
  - `app/services/repositories/contracts_repository.py`
  - `app/services/repositories/analyses_repository.py`
  - Optional: `app/services/workflow/progress_tracking.py` (wrapper or callbacks)

### Step-by-Step Implementation Plan
Phase 1: Non-functional reorganizations
- Add progress publisher interface and WebSocket adapter.
- Update service to use publisher if provided; fall back to no-op.
- Extract inner `ProgressTrackingWorkflow` to a helper without behavior changes.

Phase 2: Repository migration (aligns with `MIGRATION_SUPABASE_REPOSITORY.md`)
- Implement `ContractsRepository` and `AnalysesRepository` with `asyncpg`.
- Update `router/websockets.py` to use repositories for ensure/upsert flows.
- Delete DB helpers from the service file; remove `SupabaseClient` import.

Phase 3: API consistency and typing cleanup
- Add `AustralianState` resolver util and update usage.
- Normalize `progress` structure and response derivation.
- Consolidate metrics and success calculation.

Phase 4: Tests and docs
- Update/extend unit tests in `tests/unit/services/test_contract_analysis_service.py` for:
  - Progress publisher injection
  - Resume logic edge cases (`_failed` suffix handling)
  - Health/metrics consistency
- Add repository unit tests; update integration tests that touched helpers.

### Acceptance Criteria
- Service file sheds DB helpers and direct WebSocket coupling; depends on injected adapters.
- All existing tests pass; new repository tests added.
- `router/websockets.py` uses repositories for ensure/upsert; behavior unchanged.
- No change in public `ContractAnalysisService` methods and exports.

### Quick Wins
- Replace Australian state parsing with a strict resolver and clearer error message.
- Simplify model selection to one utility call.
- Reduce log noise and unify error paths in `analyze_contract`.

### Risk & Rollback
- Repository migration is behind existing feature flags/config; if issues arise, revert router usage to helpers temporarily (kept behind a shim during the transition).
- Keep adapter-based progress publishing to avoid breaking WebSocket flows.

### Actionable Task Checklist
- [ ] Add `ProgressPublisher` interface and WebSocket adapter.
- [ ] Extract `ProgressTrackingWorkflow` into helper module.
- [ ] Introduce `AustralianState` resolver util and replace ad-hoc parsing.
- [ ] Move `ensure_contract` → `ContractsRepository` and update router usage.
- [ ] Move `upsert_contract_analysis` → `AnalysesRepository` and update router usage.
- [ ] Remove `SupabaseClient` import from service.
- [ ] Consolidate response/metrics creation into single helper.
- [ ] Update and expand unit/integration tests.

