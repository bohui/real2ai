---
type: "user"
category: "instructions"
name: "step3_risk_aggregation"
version: "1.0.0"
description: "Step 3 - Risk Aggregation and Prioritization"
fragment_orchestration: "step3_risk_aggregation"
required_variables:
  - "analysis_timestamp"
  - "australian_state"
  - "cross_section_validation_result"
  - "special_risks_result"
  - "disclosure_compliance_result"
  - "title_encumbrances_result"
  - "settlement_logistics_result"
optional_variables:
  - "retrieval_index_id"
  - "seed_snippets"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 6000
temperature_range: [0.1, 0.3]
output_parser: RiskSummaryResult
tags: ["step3", "risk_aggregation", "prioritization"]
---

# Risk Aggregation and Prioritization (Step 3)

Using only Step 2 outputs and the cross-section validation result, synthesize an overall buyer risk profile and prioritized list of top risks.

Inputs provided:
- Cross-section validation: {{cross_section_validation_result | tojsonpretty}}
- Special risks: {{special_risks_result | tojsonpretty}}
- Disclosure compliance: {{disclosure_compliance_result | tojsonpretty}}
- Title & encumbrances: {{title_encumbrances_result | tojsonpretty}}
- Settlement logistics: {{settlement_logistics_result | tojsonpretty}}

Seeds: {{ seed_snippets or [] | tojsonpretty }}

## Requirements
- Compute overall_risk_score (0-1), top_risks[], category_breakdown, rationale, confidence
- Top risks must reflect upstream issues and include evidence_refs
- Ensure stable scoring (±0.05) for identical inputs

Return a valid RiskSummaryResult.