---
type: "user"
category: "instructions"
name: "step3_compliance_score"
version: "1.0.0"
description: "Step 3 - Compliance Readiness Score"
fragment_orchestration: "step3_compliance_score"
required_variables:
  - "analysis_timestamp"
  - "australian_state"
  - "cross_section_validation_result"
  - "disclosure_compliance_result"
  - "conditions_result"
  - "settlement_logistics_result"
optional_variables:
  - "retrieval_index_id"
  - "seed_snippets"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 6000
temperature_range: [0.1, 0.3]
output_parser: ComplianceSummaryResult
tags: ["step3", "compliance", "scoring"]
---

# Compliance Readiness Score (Step 3)

Summarize compliance health vs statutory and contract obligations.

Inputs:
- Cross-section validation: {{cross_section_validation_result | tojsonpretty}}
- Disclosure compliance: {{disclosure_compliance_result | tojsonpretty}}
- Conditions: {{conditions_result | tojsonpretty}}
- Settlement logistics: {{settlement_logistics_result | tojsonpretty}}

Seeds: {{ seed_snippets or [] | tojsonpretty }}

## Requirements
- Provide score (0-1), gaps[], remediation_readiness, key_dependencies
- Score must respond predictably to input changes

Return a valid ComplianceSummaryResult.