## Fragment System Migration Delta Plan

- Scope:
  - `backend/app/core/prompts/fragment_manager.py`
  - `backend/app/core/prompts/composer.py`
  - `backend/app/prompts/fragments/**`
  - `backend/app/prompts/user/instructions/contract_analysis_base.md`
  - `backend/app/prompts/config/contract_analysis_orchestrator.yaml`
  - Tests under `backend/tests/unit/core/prompts/**`
  - Docs under `docs/workflows/**`

### Phase 1 — New engine (behind internal sequencing, no feature flag)
- Implement generic context matcher (wildcards, lists, case-insensitive) — no hardcoded keys.
- Implement folder-driven grouping: first-level folder under `fragments/` becomes the template variable name; provide empty strings for missing groups.
- Keep legacy orchestrator usage for fragment discovery until migration finishes, but remove any in-code aliasing.

### Phase 2 — Prepare folder layout
- Create first-level groups under `backend/app/prompts/fragments/`:
  - `state_requirements/`, `contract_types/` (with `purchase/`, `lease/`, `option/`), `user_experience/` (with `novice/`, `intermediate/`, `expert/`), `analysis_depth/` (with `comprehensive/`, `quick/`, `focused/`), `consumer_protection/`, `risk_factors/`, `shared/`.
- Move files by group in small PRs, verifying rendering after each move.

### Phase 3 — Metadata normalization
- Remove deprecated metadata (`group`, `domain`).
- Add minimal `context` block per fragment with `state`, `contract_type`, `user_experience`, `analysis_depth` using exact values, lists, or `"*"`.

### Phase 4 — Update templates
- Update base templates to use group names directly:
  - `{{ state_requirements }}`
  - `{{ consumer_protection }}`
  - `{{ contract_types }}`
  - `{{ user_experience }}`
  - `{{ analysis_depth }}`

### Phase 5 — Orchestrator cleanup
- Retain `base_template`, quality/performance/testing settings.
- Remove fragment mapping sections; discovery is folder + context-driven.

### Phase 6 — Logging, validation, tests
- Logging: For each fragment considered, log derived group, path, and match decision.
- Validators:
  - Folder validator for first-level group names and referenced-but-missing groups.
  - Metadata validator for `context` schema and deprecated keys.
- Tests:
  - Unit: context matcher cases; group derivation; empty group handling.
  - Integration: end-to-end rendering with new placeholders.

### Phase 7 — Rollout and cleanup
- Remove any remaining alias maps and hardcoded expected placeholder lists.
- Remove orchestrator fragment mappings and code paths that depend on them.
- Update architecture docs and `fragments/` README with folder rules and examples.

### Acceptance criteria
- Templates render sections using folder-driven variables with no code/config mapping.
- Fragments apply via generic context matching (including `*` and lists).
- Orchestrator fragment mappings are removed.
- Validators and tests pass; logs are sufficiently detailed for debugging.

