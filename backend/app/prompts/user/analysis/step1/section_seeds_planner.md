---
type: "user"
category: "instructions"
name: "section_seeds_planner"
version: "1.0.1"
description: "High-signal snippet selection for Step 2 analyzers (no scoring)"
fragment_orchestration: "contract_analysis"
required_variables:
  - "contract_text"
optional_variables: []
model_compatibility: ["gemini-2.5-flash"]
max_tokens: 6000
temperature_range: [0.1, 0.4]
output_parser: SectionExtractionOutput
tags: ["contract", "section-seeds", "planner"]
---

# Section Seeds Planner (Extraction-Only)

Select high-signal snippets to seed further analysis. Do not perform risk scoring, adequacy judgments, timelines, or dependency analysis.

## RULES

- Sections: parties_property, financial_terms, conditions, warranties, default_termination, settlement_logistics, title_encumbrances, adjustments_outgoings, disclosure_compliance, special_risks.
- Select concise snippets per relevant section; avoid redundancy.
- For each snippet include: `clause_id` (if available), `page_number`, `start_offset`, `end_offset`, `snippet_text`, optional `selection_rationale`, and optional `confidence`.
- If the same snippet is relevant to multiple sections, it may be duplicated across sections.

Do not perform any risk scoring, adequacy judgments, or timeline/dependency analysis in seeds—only selection and rationale.

## Text to process:
```
{{ contract_text }}
```


