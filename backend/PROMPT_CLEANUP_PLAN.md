### Prompt System Cleanup Plan (LangGraph-Orchestrated, Single-Use Renders)

#### Remaining work (by area)
1) Config (composition-first, no internal workflows)
- `composition_rules.yaml`:
  - Remove all `workflow_steps` blocks.
  - Create single-use compositions with `user_prompts` only (examples):
    - `structure_analysis_only` → ["analysis/contract_structure"]
    - `compliance_check_only` → ["analysis/compliance_check"]
    - `financial_analysis_only` → ["analysis/financial_analysis"]
    - `risk_assessment_only` → ["workflow/contract_risk_assessment"]
    - `ocr_whole_document_extraction` → ["ocr/whole_document_extraction"]
    - `ocr_text_diagram_insight` → ["ocr/text_diagram_insight"]
  - Remove redundant `ocr_to_analysis` (overlaps with the above) and keep only necessary compositions.
- `prompt_registry.yaml`:
  - Ensure all names used by new compositions resolve to `user/...` or `system/...` paths.
- `service_mappings.yaml`:
  - Point services to the new single-use compositions.

2) Core code alignment
- `PromptManager.render_composed`:
  - Stop calling `render()` on composed outputs; use `PromptComposer` results directly:
    - Return `{ system_prompt: composed.system_content, user_prompt: composed.user_content, metadata }`.
  - If `output_parser` is provided, ensure format instructions are injected into the user prompt (keep parser limited to user-side).
- Remove internal workflow engine usage:
  - Delete `workflow_engine.py` and `PromptManager.execute_workflow(...)` and related APIs/metrics.
- `PromptComposer` and `ConfigurationManager`:
  - Remove `output_template`/`validation_template` fields and handling.

3) Services / Nodes
- Switch any remaining `.render(...)` calls to `.render_composed(...)` with a specific single-use composition.
- For nodes currently using `complete_contract_analysis` just to get a phase (e.g., structure):
  - Migrate to the corresponding `*_only` composition once defined (e.g., `structure_analysis_only`).

4) Templates & fragments
- Remove all Jinja conditionals from user templates; rely on orchestrators and context-precomputed values.
- Ensure orchestrator-referenced fragments exist (OCR `standard_processing.md`, `fast_processing.md` if referenced).

5) Tests / Docs / Scripts
- Update tests to use `render_composed` with the new compositions; remove workflow-based tests.
- Update docs to reflect LangGraph-driven orchestration and single-use compositions.
- Keep `validate_prompt.py` for template validation; optionally add a composition validator.

#### Acceptance criteria
- No references remain to `workflow_steps`, internal workflow engine, `output_template`, or `validation_template`.
- `render_composed` returns correct `system_prompt`/`user_prompt` without re-calling `render()`.
- All services/nodes call `render_composed` with single-use compositions.
- Orchestrators inject correct fragments based on context; templates contain no inline logic.

#### Notes
- Today there is a mismatch: `PromptComposer.ComposedPrompt` exposes `system_content`/`user_content`, but `PromptManager.render_composed` tries to use `composed.system_template`/`user_template`. Fixing this is part of the Remaining Work (2).
