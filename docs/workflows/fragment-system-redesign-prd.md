## Fragment System Redesign PRD

### Author
Legal AI Platform — Prompt Architecture

### Status
Proposed — Ready to implement

### Problem Statement
- Fragment rendering relies on implicit/implicit mappings between fragment categories, orchestrator rule names, and template placeholders, creating drift and empty sections in composed prompts.
- Code-level alias mappings added to bridge naming mismatches are brittle and non-maintainable.
- Fragment metadata is inconsistent across files, with overlapping notions of category/state/contract type and no unified context model.

### Goals
- Remove the need for any code or config mapping between fragments and template placeholders.
- Make the folder structure the single source of truth for grouping and template variable names.
- Use a simple, generic context model (with wildcard support) that fragments declare and the composer evaluates without hardcoded keys.
- Simplify base templates to reference group names directly.
- Provide validation and documentation to prevent regressions.

### Non-Goals
- Changing the content of existing fragments beyond metadata normalization.
- Coupling fragment selection to LLM vendor/model.

### High-Level Design

1) Folder-Structure-Driven Grouping (no domain, no group metadata)

```
backend/app/prompts/fragments/
  state_requirements/            -> {{ state_requirements }}
    NSW/
    VIC/
    QLD/
  contract_types/               -> {{ contract_types }}
    purchase/
    lease/
    option/
  user_experience/              -> {{ user_experience }}
    novice/
    intermediate/
    expert/
  analysis_depth/               -> {{ analysis_depth }}
    comprehensive/
    quick/
    focused/
  consumer_protection/          -> {{ consumer_protection }}
    cooling_off/
    statutory_warranties/
    unfair_terms/
  risk_factors/                 -> {{ risk_factors }}
  shared/                       # Optional shared content
```

- The first-level folder under `fragments/` is the group name and must match the template variable name used by consumers (e.g., base templates).
- Deeper subfolders are for organization only (e.g., by state, or subtype) and impose no logic by themselves.

2) Fragment Metadata Schema (minimal, consistent)

- Remove `group` and `domain` from metadata.
- Use a single `context` object to define applicability. Each key supports: exact value, list of values (any-match), or wildcard `"*"`.

```yaml
---
category: "legal_requirement"          # free-form, optional taxonomy
context:
  state: "NSW"                        # or "*"; case-insensitive string match
  contract_type: "purchase"            # or "*" or ["purchase","option"]
  user_experience: "*"                 # or "novice" | "intermediate" | "expert"
  analysis_depth: "*"                  # or "comprehensive" | "quick" | "focused"
priority: 80
version: "1.0.0"
description: "NSW Section 149 planning certificate requirements"
tags: ["nsw", "planning", "certificates", "section-149"]
---

### NSW Section 149 Planning Certificates
... content ...
```

3) Generic Context Matching (no hardcoded keys)

Behavior:
- For each key in `fragment.context`:
  - `"*"` always matches
  - If value is a list → match if runtime value is in the list (case-insensitive for strings)
  - If value is a scalar → match on equality (case-insensitive for strings)
  - If runtime context lacks the key and fragment value is not `"*"` → no match

Pseudocode:

```python
def matches_context(fragment_context: dict, runtime_context: dict) -> bool:
    if not fragment_context:
        return True

    for key, required in fragment_context.items():
        # wildcard matches anything
        if required == "*":
            continue

        actual = runtime_context.get(key)
        if actual is None:
            return False

        # normalize strings for CI comparison
        def norm(v):
            return v.lower() if isinstance(v, str) else v

        if isinstance(required, list):
            if norm(actual) not in [norm(x) for x in required]:
                return False
        else:
            if norm(actual) != norm(required):
                return False

    return True
```

4) Composition Output Variables

- Composer collects all matched fragments per group (= first-level folder).
- For each group, set a template variable with the exact same name as the folder to the concatenated content (joined by two newlines).
- Provide empty string for any group referenced by the template but with no matches.

Example base template consumption:

```markdown
## State-Specific Legal Requirements
{{ state_requirements }}

## Contract Type Specific Analysis
{{ contract_types }}

## Experience Level Guidance
{{ user_experience }}

## Analysis Depth and Focus
{{ analysis_depth }}

## Consumer Protection Framework
{{ consumer_protection }}
```

5) Orchestration Configuration

- Keep orchestrator for non-fragment concerns (e.g., selecting base template, caching, performance settings, quality toggles).
- Deprecate fragment mapping in orchestrators; the file system structure and generic context matching supersede it.

### Validation & Tooling (all enabled)

- Folder structure validator:
  - Ensures first-level folders have valid names (letters, digits, underscore).
  - Warns if a base template references a variable that has no corresponding folder.
  - Optional: repository-level registry of allowed group names to catch typos (validation-only; not used at runtime).

- Metadata validator:
  - Checks frontmatter is valid YAML.
  - Ensures `context` keys are strings and values are `str | list[str] | "*"`.
  - Warns if deprecated keys `group` or `domain` are found.

- Unit tests:
  - Generic context matching (wildcards, lists, case-insensitivity).
  - Group derivation from folder structure.
  - Rendering behavior when a group has zero matches (empty string injection).

- README in `backend/app/prompts/fragments/` documenting:
  - Valid group naming rules.
  - Metadata schema.
  - How template variables relate to folders.

### Deprecations and Removals

- Remove any code-level alias or mapping of fragment categories → template variables.
- Remove orchestrator fragment-mapping sections; they are replaced by folder-structure-driven selection.
- Remove reliance on `domain`/`group` fields in fragment metadata. If present, they are ignored and flagged by validator.
- Keep caching and logging as-is; extend logs to include derived `group` and context-matching decisions for traceability.

### Migration Plan

1) Create first-level folders for groups listed above and move existing fragments accordingly:
   - From `fragments/nsw/*` → `fragments/state_requirements/NSW/*`
   - From `fragments/vic/*` → `fragments/state_requirements/VIC/*`
   - From `fragments/purchase/*` → `fragments/contract_types/purchase/*`
   - From `fragments/lease/*` → `fragments/contract_types/lease/*`
   - From `fragments/option/*` → `fragments/contract_types/option/*`
   - From `fragments/analysis/*` → distribute into `user_experience/*` vs `analysis_depth/*` as appropriate
   - From `fragments/common/*` → `fragments/consumer_protection/*` or `fragments/shared/*` depending on content

2) Normalize fragment metadata to the new schema:
   - Remove `group` and `domain` if present
   - Add `context` block with `"*"` defaults where appropriate

3) Update composer implementation:
   - Derive `group` from the first-level folder name under `fragments/`
   - Apply generic `matches_context()` logic
   - Publish variables named exactly as the group
   - Provide empty strings for missing groups to avoid undefined variables

4) Update base templates:
   - Replace complex placeholders with group names (e.g., `{{ state_requirements }}` instead of `{{ state_legal_requirements_fragments }}`)

5) Remove deprecated logic:
   - Delete alias/mapping code and orchestrator fragment mapping sections
   - Add validators and tests described above

6) Documentation:
   - Add README under `fragments/`
   - Update architecture docs to reflect new flow

### Runtime Context Model

- Compose runtime context by merging these logically separate concerns:
  - `state` (jurisdiction)
  - `contract_type` (purchase | lease | option | other)
  - `user_experience` (novice | intermediate | expert)
  - `analysis_depth` (comprehensive | quick | focused)
  - Additional keys can be added later without code changes.

- Note on type safety: Services that build context should use distinct classes internally (e.g., `JurisdictionContext`, `PurchaseContractContext`, `LeaseContractContext`, `OptionContractContext`, `UserContext`, `AnalysisContext`) and flatten to a dict before composition. The fragment system remains key/value and generic.

### Acceptance Criteria
- Base templates render populated sections using only folder-driven groups without any code/config mapping.
- Fragments apply correctly based on `context` with wildcard/list support.
- Validators pass and block structurally invalid fragments.
- All orchestrator fragment mapping references are removed.
- Unit tests cover context matching, grouping, and empty-group behavior.

### Risks & Mitigations
- Risk: Temporary content gaps during migration
  - Mitigation: Migrate in phases and keep a fallback composition path until all templates are updated.
- Risk: Template variables drift from folder names
  - Mitigation: Validator checks for referenced-but-missing groups and missing-but-present folders.

### Observability
- Log derived `group`, fragment path, and match decision (with reasons) for each considered fragment.
- Export simple metrics: number of matched fragments per group, composition time, and cache hit rate.

### Example End-to-End

1) Runtime context:

```json
{
  "state": "NSW",
  "contract_type": "purchase",
  "user_experience": "novice",
  "analysis_depth": "comprehensive"
}
```

2) Composer scans `backend/app/prompts/fragments/` and:
   - For `state_requirements/NSW/*` matches context → include
   - For `contract_types/purchase/*` matches context → include
   - For `user_experience/novice/*` matches context → include
   - For `analysis_depth/comprehensive/*` matches context → include
   - For `consumer_protection/*` (context "*") → include

3) Template variables provided:

```json
{
  "state_requirements": "...joined content...",
  "contract_types": "...joined content...",
  "user_experience": "...joined content...",
  "analysis_depth": "...joined content...",
  "consumer_protection": "...joined content..."
}
```

4) Base template uses the exact group names:

```markdown
## State-Specific Legal Requirements
{{ state_requirements }}

## Consumer Protection Framework
{{ consumer_protection }}
```


