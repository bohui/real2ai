### Epic: Step 2 Section-by-Section Analysis Sub-Workflow (LangGraph)

#### Summary
- **Goal**: Replace `ContractTermsExtractionNode` with a new LangGraph-powered Step 2 sub-workflow that performs concurrent, specialist analyses of 10 contract sections with explicit dependency management and cross-section validation.
- **Scope**: Implements Phase 1 (foundation parallel analyses), Phase 2 (dependent analyses), Phase 3 (synthesis), comprehensive diagram integration, and cross-section checks as defined in PRD 4.1.2 and dependencies architecture.
- **References**:
  - PRD: `docs/workflows/step_assessment_workflow-prd.md` (see 4.1.2)
  - Dependencies & Architecture: `docs/workflows/step_assessment_architect_dependencies.md`

#### Objectives
- **Accuracy**: Meet or exceed PRD success criteria for each section, including enhanced title/encumbrance analysis with diagrams.
- **Performance**: Achieve end-to-end Step 2 execution within 4.5–6.5 minutes with resilient retries.
- **Reliability**: Robust error handling, partial failures tolerated for non-critical analyzers, and dependency-aware fallbacks.
- **Interoperability**: Clean inputs from Step 1 entities and clean outputs for Step 3 risk engine.

#### Non-Goals
- Changing Step 1 entity extraction or Step 3 risk prioritization algorithms.
- UI redesign; only provide structured outputs consumable by existing/report layers.

#### Success Metrics (mapped to PRD 6.x)
- **Accuracy**: ≥95% on critical dependencies and visual analysis; section-specific acceptance in each story.
- **Completion rate**: ≥99.5% with retries (LangGraph orchestration).
- **Performance**: Total Step 2 ≤ 390 seconds median.
- **Diagram processing**: ≥95% success across 20+ types; ≥98% utility/infrastructure identification; ≥92% environmental overlay interpretation.

#### High-Level Architecture
- **LangGraph Sub-Workflow**: `Step2AnalysisWorkflow` with three phases:
  - Phase 1 (parallel): Parties & Property, Financial Terms, Conditions, Warranties, Default & Termination.
  - Phase 2 (dependent): Settlement Logistics (depends on Conditions + Financial), Title & Encumbrances (depends on Parties/Property + diagrams/overlays).
  - Phase 3 (synthesis): Adjustments & Outgoings (depends on Financial + Settlement), Disclosure Compliance (ALL_PREVIOUS + legal matrix), Special Risks (synthesis over all).
- **State**: Dedicated Step 2 state slice in `RealEstateAgentState.analysis_results.step2` with per-section outputs, confidences, and risk flags.
- **Concurrency**: `asyncio.gather` in Phase 1; gated execution with dependency checks in Phases 2–3.
- **Caching**: Clause-level and cross-reference cache for re-runs; section idempotence via content hashing.
- **Diagram Integration**: Comprehensive processors over 20+ diagram types feeding Title analysis and cross-section constraints.

#### Inputs
- **Required**: `full_text`, `entities_extraction_result` (per Step 1), `australian_state`, `contract_type`, `purchase_method`, `use_category`, `property_condition` (if available), uploaded diagrams/context (if present), legal requirements matrix.

#### Outputs
- Per-section structured results with confidence and risk flags.
- Cross-section validation report (dates, finance cross-refs, condition dependencies, legal matrix checks).
- Aggregated `analysis_results.step2` with telemetry suitable for Step 3 risk engine.

#### Dependencies (see architecture doc)
- **High**:
  - Conditions → Settlement (deadlines, finance/inspection windows)
  - Financial → Adjustments (purchase price, fees, settlement date)
  - Parties/Property → Title (legal description, owners) + diagrams/overlays
- **Moderate**:
  - Multi-input Disclosure Compliance (metadata, conditions, financial, property class, settlement method)
  - Special Risks synthesis over all prior results
- **Low**:
  - Warranties & Representations
  - Default & Termination

#### Deliverables
- Documentation (this epic + per-section stories).
- New sub-workflow orchestration design and integration plan.
- Schema plan for per-section outputs under `backend/app/prompts/schema`.
- Prompt plan (system + user) and composition entries.
- Migration plan to switch `ContractTermsExtractionNode` to Step 2 sub-workflow entry.

#### Milestones
- M1: Stories approved; orchestration interface and state schema finalized.
- M2: Phase 1 analyzers implemented with parsers/prompts and tests.
- M3: Phase 2 analyzers with diagram integration and dependency gating.
- M4: Phase 3 synthesis, cross-section checks, and final validation.
- M5: Integration with Step 3, rollout, monitoring.

#### Risks & Mitigations
- **Token pressure**: Use section-scoped prompts, context slicing, and caching; cap inputs with clause selection.
- **Dependency failures**: Graceful degradation for non-critical analyzers; skip-with-reason and fallback data flows.
- **Diagram variability**: Retry on per-type processors; heuristics for low-quality images; surface diagnostics.
- **Latency**: Enforce timeouts per story; short-circuit synthesis if dependencies not met.

#### Acceptance Criteria
- All section stories’ acceptance tests pass and meet PRD success criteria.
- End-to-end Step 2 output is consumable by Step 3 with required metadata.
- Logs include dependency and cross-check diagnostics without PII in production.


