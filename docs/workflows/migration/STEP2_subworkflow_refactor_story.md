### Refactor Story: Step 2 Sub-Workflow replacing ContractTermsExtractionNode

#### Context
- Replace `ContractTermsExtractionNode` with a LangGraph-powered Step 2 sub-workflow that performs section-by-section analysis.
- Aligns with PRD 4.1.2 and `docs/workflows/step_assessment_architect_dependencies.md` for dependency-driven execution.
- Inputs include `full_text`, Step 1 `entities_extraction`, and relevant `RealEstateAgentState` context (`australian_state`, `contract_type`, `purchase_method`, `use_category`, `property_condition`), plus uploaded diagrams/overlays where available.

#### Objectives
- Improve accuracy and explainability by decomposing monolithic extraction into 10 specialist analyzers with cross-validation.
- Execute Phase 1 analyzers concurrently, then orchestrate dependent/synthesis phases deterministically.
- Integrate comprehensive diagram analysis into Title & Encumbrances.

#### Design Overview
- Orchestration: `Step2AnalysisWorkflow` (LangGraph) with three phases:
  - Phase 1 (parallel): Parties & Property, Financial Terms, Conditions, Warranties, Default & Termination
  - Phase 2 (dependent): Settlement Logistics (depends on Conditions + Financial), Title & Encumbrances (depends on Parties/Property + diagrams/overlays)
  - Phase 3 (synthesis): Adjustments & Outgoings (depends on Financial + Settlement), Disclosure Compliance (ALL_PREVIOUS + legal matrix), Special Risks (synthesis over all)
- State: Write per-section outputs to `analysis_results.step2` with `confidence`, `risk_indicators`, and `evidence_refs`, plus a cross-section validation report.
- Concurrency: `asyncio.gather` for Phase 1; explicit dependency checks in Phases 2–3.
- Caching: Clause-level and cross-reference caches to reduce tokens and speed re-runs.

#### Inputs & Context
- `full_text` from processing or repository fetch.
- `ContractEntityExtraction` output from Step 1.
- Context from state when present (jurisdiction and taxonomy hints).
- Optional resources: `uploaded_diagrams`, planning overlays, legal requirements matrix.

#### Outputs
- Structured results per section aligned to PRD 4.1.2 success criteria:
  - `findings`, `issues`, `confidence`, `risk_indicators`, `evidence_refs`.
- Cross-section validation covering date consistency, financial cross-refs, condition dependencies, and legal matrix checks.
- Aggregated `analysis_results.step2` consumable by Step 3 risk engine.

#### Dependencies & Execution Model
- High dependencies:
  - Conditions → Settlement (deadlines, finance/inspection windows)
  - Financial → Adjustments (purchase price, fees, settlement date)
  - Parties/Property → Title (legal description, owners) + diagrams/overlays
- Moderate dependencies:
  - Disclosure compliance (metadata, conditions, financial, property class, settlement method)
  - Special risks (synthesis across sections)
- Low dependencies:
  - Warranties & Representations; Default & Termination

#### Prompts & Parsers Plan
- System prompt: `backend/app/prompts/system/step2_section_analysis.md` (new) for section modularity and cross-validation rules.
- User prompts under `backend/app/prompts/user/analysis/step2/`:
  - `parties_property.md`, `financial_terms.md`, `conditions.md`, `warranties.md`, `default_termination.md`,
    `settlement_logistics.md`, `title_encumbrances_diagrams.md`, `adjustments_outgoings.md`, `disclosure_compliance.md`, `special_risks.md`, `cross_section_validation.md`.
- Schemas: Pydantic output models per section in `backend/app/prompts/schema/step2/` for structured parsing.
- Config updates: registry entries and composition rules per analyzer with model metadata and parser bindings.

#### Error Handling & Fallbacks
- Non-critical analyzer failures degrade gracefully with low-confidence fallback outputs and explicit `skipped_reason` when applicable.
- Critical dependency failures prevent dependent analyzers; skipped analyzers surface in validation output.
- Per-analyzer timeouts and up to 2 retries with exponential backoff.

#### Logging & Monitoring
- Structured logs per analyzer: inputs summary, dependency satisfaction, duration, confidence, issues, skipped reasons.
- Metrics: per-node durations/completions, error/skipped counts, diagram processing success rate (Title analyzer), total Step 2 duration.

#### Performance & Token Strategy
- Clause-level context slicing per section to control token usage.
- Parallel diagram processing with consolidated constraints fed into prompts.
- Cache by content hash for clause analyses and cross-references.

#### Integration & Migration Plan
- Introduce `SectionAnalysisNode` that invokes `Step2AnalysisWorkflow` and route from `ContractAnalysisWorkflow.extract_terms`.
- Maintain compatibility by populating minimal `contract_terms` when required, but prefer `analysis_results.step2` for downstream consumers.
- Feature flag rollout to toggle between legacy and new flow.

#### Testing Strategy
- Unit tests for schemas and parsers per section.
- Prompt golden tests with seeded inputs.
- Integration tests for dependency gating and synthesis correctness.
- End-to-end Step 2 execution tests verifying PRD success criteria and timing targets.

#### Acceptance Criteria
- All section outputs present with confidence and risk indicators; cross-section validation included.
- Title analyzer integrates diagram constraints with target accuracy on curated sets.
- End-to-end Step 2 completes within target duration; retries within configured limits.
- Step 3 consumes Step 2 outputs without regression.

#### Rollout Plan
- Phase A: Shadow mode (compute Step 2 alongside legacy; no replacement).
- Phase B: Dual-run with comparison; alert on drift beyond thresholds.
- Phase C: Make Step 2 default; retain legacy fallback for two releases.

#### References
- PRD: `docs/workflows/step_assessment_workflow-prd.md` (4.1.2)
- Architecture & Dependencies: `docs/workflows/step_assessment_architect_dependencies.md`
- Epic: `docs/workflows/epics/STEP2_SECTION_ANALYSIS_EPIC.md`
- Stories: `docs/workflows/stories/STEP2_section_stories.md`
