### Real2.AI Deep Codebase Cleanup Report

Last updated: 2025-08-11

This report identifies deprecated/unused code, noisy debug logs, stale tests/docs, and refactor targets. It includes “keep for now” items and an actionable checklist.

---

## Executive summary

- Deprecated/legacy compatibility layers are still in-tree (OCR, legacy Supabase client, legacy DB connection release). Propose removal or isolation behind feature flags with a one-release deprecation window.
- Multiple test configurations conflict with actual test file layout. Many tests won’t run due to `testpaths = ["tests"]` while numerous `test_*.py` live outside `backend/tests/`.
- Excessive `console.log` debug output in the frontend (WebSocket and stores) should be gated or stripped from production builds.
- Duplicated/legacy packaging: `pyproject.toml` coexists with `requirements*.txt`. Decide the source of truth; recommend `pyproject.toml` with `uv` and generate lockfiles for deployments.
- Sensitive artifacts present (e.g., `backend/gcp_key.json`). Ensure they are not tracked and rotate if exposed.
- Documentation has archived/outdated TODOs and audit files. Consolidate and move to a clear `docs/archive/`.

---

## High-impact actions (top 10)

1) Remove or quarantine deprecated OCR shim
   - File: `backend/app/services/ocr_service.py` (kept for import compatibility). Replace imports across code, then remove after one release.

2) Retire legacy PostgREST client
   - File: `backend/app/clients/supabase/database_client.py` (explicitly deprecated). Migrate all usages to repository + asyncpg; then delete.

3) Remove legacy DB connection release helper
   - File: `backend/app/database/connection.py` function `release_connection(...)` (deprecated). Confirm no references and remove.

4) Unify pytest config and test layout
   - Config: `backend/pyproject.toml` defines `testpaths=["tests"]` and pytest options; there are also `backend/pytest.ini` and `backend/pytest-ci.ini`.
   - Action: Move all backend tests under `backend/tests/` (or broaden `testpaths`). Remove redundant configs; keep a single source of truth.

5) Strip frontend debug logs in production
   - Files: `frontend/src/services/api.ts`, `frontend/src/store/analysisStore.ts`, `frontend/src/App.tsx`, WebSocket service classes.
   - Action: Guard logs behind `import.meta.env.DEV` and enable bundler remove of `console.*` in prod.

6) Secure secrets and keys
   - File present: `backend/gcp_key.json`.
   - Action: Ensure it’s not tracked; move to secret manager or `.env`/mounted secret. Rotate if previously committed.

7) Consolidate Python dependency management
   - Files: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/requirements-test.txt`, `backend/uv.lock`.
   - Action: Use `pyproject.toml` + `uv.lock` as canonical; auto-generate `requirements*.txt` only if needed for deploy.

8) Clean unused/temporary scripts and examples
   - Files (examples): `backend/example_semantic_analysis.py`, `backend/integration_example.py`, `backend/workflow_integration_example.py`, `backend/security_demo.py`, `backend/validate_security.py`.
   - Action: Move to `backend/examples/` or `scripts/`; mark clearly or remove.

9) Archive or remove outdated documentation
   - Outdated/TODO style documents under `docs/archive/temporary/` and root audit files; consolidate under `docs/archive/`.

10) Track and apply pending DB migration
   - Untracked: `supabase/migrations/20241211000001_add_contracts_metadata_column.sql`. Validate and commit.

---

## Detailed findings

### A. Deprecated and legacy code

- OCR service shim (compatibility only)

```1:34:backend/app/services/ocr_service.py
"""
OCR Service - DEPRECATED AND REMOVED
...
This file is kept only for import compatibility and will be removed in the next version.
"""
...
warnings.warn(
    "OCRService is deprecated and has been removed. Use GeminiOCRService instead.",
    DeprecationWarning,
)
```

- Legacy PostgREST-based client

```1:18:backend/app/clients/supabase/database_client.py
"""
DEPRECATED: This PostgREST-based database client is deprecated in favor of
the repository pattern with direct asyncpg connections.
"""
...
class SupabaseDatabaseClient(DatabaseOperations):
    """
    DEPRECATED: This PostgREST-based client is deprecated in favor of
    repository pattern with asyncpg. Use repository classes instead.
    """
```

- Deprecated DB connection helper

```420:448:backend/app/database/connection.py
# Legacy compatibility functions (deprecated)
async def release_connection(...):
    """
    Legacy connection release function (deprecated).
    IMPORTANT: This function should not be used. Use context managers instead.
    """
```

- Legacy method placeholder in Gemini OCR

```941:961:backend/app/services/ai/gemini_ocr_service.py
async def extract_image_semantics_legacy(...):
    """Legacy method without parser integration (for comparison)"""
    pass
```

Recommendations
- Replace all imports of `OCRService` with `GeminiOCRService` and remove the shim next release.
- Locate and replace any implementations consuming the PostgREST client; delete client module once clear.
- Delete `release_connection` and prefer context managers exclusively.
- Remove legacy OCR method or guard with `if False:` only for docs; prefer deleting.

### B. Test configuration and layout mismatches

- Config in `backend/pyproject.toml` sets:

```96:113:backend/pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
...
```

- Additional configs present:
  - `backend/pytest-ci.ini` (CI-focused)
  - `backend/pytest.ini` (present; content not listed here)

- Numerous tests live outside `backend/tests/`, e.g. at backend root and repository root:
  - `backend/test_domain_client.py`, `backend/test_workflow.py`, `backend/simple_test.py`, many others listed in the backend root
  - Root-level: `test_jwt_diagnostics.py`

Impact
- Many tests are likely not collected by `pytest` due to `testpaths=["tests"]`.

Recommendations
- Choose one: move all backend tests under `backend/tests/`, or broaden `testpaths` to include `.` or explicit directories.
- Keep a single config (recommend `pyproject.toml`), and remove `pytest.ini`/`pytest-ci.ini` duplication by merging their options.

### C. Noisy logging and debug statements (frontend)

- Extensive `console.log` in:
  - `frontend/src/services/api.ts`
  - `frontend/src/store/analysisStore.ts`
  - `frontend/src/App.tsx`
  - WebSocket service class files

Examples

```708:746:frontend/src/services/api.ts
console.log('Received coordinated token refresh from backend');
...
console.log('Proactive token refresh successful');
...
console.log('Backend token near expiry, will receive new token on next API call');
```

```739:749:frontend/src/services/api.ts
console.log("🏗️ Creating WebSocket service for document:", documentId);
...
console.log("🔍 WebSocket service configuration:", { ... })
```

Recommendations
- Guard logs with `if (import.meta.env.DEV) console.log(...)` or a `logger.debug` wrapper.
- Configure Vite/Rollup/Terser to drop `console.*` in production builds.

### D. Security hygiene

- Sensitive file present: `backend/gcp_key.json`.
  - Ensure it is ignored by Git and moved to secret storage; rotate keys if committed historically.
- Verify `.env` handling; settings reference many environment variables in `backend/app/core/config.py`.

### E. Documentation cleanup

- Outdated TODOs and audit docs
  - `docs/archive/temporary/IMPLEMENTATION_PRIORITY_TODO.md` (outdated; kept for history)
  - `docs/archive/temporary/DOCUMENTATION_CLEANUP.md`
  - Multiple audit reports at repo root: `AUDIT_REPORT.md`, `AI_ARCHITECTURE_AUDIT_REPORT.md`, `ANALYSIS_RETRY_STATE_FIX.md`, etc.

Recommendations
- Consolidate older audit/TODO documents under `docs/archive/` with a single index.
- Keep current, canonical docs under `docs/` and remove duplicated summaries.

### F. Dependency and packaging consistency (Python)

- `backend/pyproject.toml` defines dev/test/docs extras and pytest/coverage settings; `backend/uv.lock` is present.
- Legacy/parallel files: `backend/requirements.txt`, `backend/requirements-test.txt`.

Recommendations
- Use `pyproject.toml` + `uv.lock` as the source of truth.
- If deploy targets require `requirements.txt`, auto-generate them from the lock in CI/CD.

### G. Tests marked `@pytest.mark.skip`

- Intentional external-integration skips, e.g. Domain client tests require API keys.

```390:431:backend/app/clients/domain/tests/test_client.py
@pytest.mark.skip(reason="Requires actual API key and network access")
async def test_real_property_search(...):
...
@pytest.mark.skip(reason="Requires actual API key and network access")
async def test_real_health_check(...):
```

Recommendation
- Keep these as integration tests; run only in an environment with real credentials.

### H. Coverage suppressions

- `pragma: no cover` used for type-checking/optional import paths. This is acceptable; keep sparing usage.

```25:28:backend/app/clients/openai/task_queue.py
except Exception:  # pragma: no cover - optional import
    RateLimitError = None
```

### I. Unused/temporary scripts and examples

- Candidates to move under `backend/scripts/` or `backend/examples/`:
  - `backend/example_semantic_analysis.py`
  - `backend/integration_example.py`
  - `backend/workflow_integration_example.py`
  - `backend/security_demo.py`
  - `backend/validate_security.py`

### J. Pending/untracked DB migration

- `supabase/migrations/20241211000001_add_contracts_metadata_column.sql` is untracked per `git status`.
- Action: Review, test locally, and commit as part of a migrations batch.

---

## Keep-for-now (intentional legacy with exit plan)

- `backend/app/services/ocr_service.py` (compatibility alias) — remove next release after verifying no external imports.
- `backend/app/clients/supabase/database_client.py` — retained only until repository pattern adoption is complete.
- Skipped integration tests requiring API keys — keep skipped in default CI; run in secure environments.

---

## Actionable checklist

Short term (1–2 days)
- Remove unused debug logs in frontend or guard behind `DEV` checks.
- Commit and apply pending Supabase migration after local verification.
- Move stray backend tests into `backend/tests/` so they are collected.
- Ensure `backend/gcp_key.json` is excluded and rotate credentials if needed.

Medium term (1 week)
- Remove OCR shim and update imports to `GeminiOCRService`.
- Migrate or delete legacy PostgREST client and remove the toggle path.
- Delete deprecated `release_connection` helper after confirming no usages.
- Unify pytest configuration; prefer a single configuration file.
- Consolidate docs; archive historical reports under `docs/archive/`.

Longer term (2–3 weeks)
- Consolidate Python dependency management under `pyproject.toml` + `uv.lock`; script generation of `requirements.txt` for deploy if needed.
- Move examples/demos under `backend/examples/` and document their usage.
- Add a CI job that fails on stray `console.*` and `pdb.set_trace` in non-test code.

---

## Suggested automation commands

Identify deprecated markers

```bash
rg -n --ignore-case "deprecated|@deprecated" backend/ | sed -n '1,200p'
```

Find debug statements

```bash
rg -n "pdb\.set_trace|ipdb\.set_trace|breakpoint\(" backend/ frontend/
rg -n "console\.log\(" frontend/src | sed -n '1,200p'
```

Enforce no console in production (Vite/Rollup)

- Add Terser options in `vite.config.ts`:

```ts
build: {
  terserOptions: {
    compress: { drop_console: true, drop_debugger: true },
  },
}
```

Pytest collection check

```bash
cd backend && uv run pytest --collect-only -q | sed -n '1,200p'
```

---

## Notes and caveats

- `backend/app/core/config.py` contains numerous feature flags. Audit which are truly used by runtime paths and remove dead toggles to simplify configuration.
- Several top-level audit and summary markdowns exist; keep a single, updated source and archive the rest.


