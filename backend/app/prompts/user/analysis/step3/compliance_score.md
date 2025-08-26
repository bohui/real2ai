---
type: "user"
category: "instructions"
name: "step3_compliance_score"
version: "1.1.0"
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
model_compatibility: ["gemini-1.5-flash", "gpt-4"]
max_tokens: 8000
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
- `gaps` must be a list of `ComplianceGap` objects.
- `severity` must be one of the `SeverityLevel` enum values.
- Provide `score` (0-1), `gaps`[], `remediation_readiness`, and `key_dependencies`.
- Score must respond predictably to input changes.

### Example Output Format:
```json
{
  "score": 0.85,
  "gaps": [
    {
      "name": "Missing Flood Zone Disclosure",
      "description": "The vendor has not provided a flood zone disclosure, which is mandatory in this state.",
      "severity": "high",
      "remediation": "Request the vendor to provide the flood zone disclosure immediately."
    },
    {
      "name": "Incomplete Strata Report",
      "description": "The provided strata report is missing the last two years of financial statements.",
      "severity": "medium",
      "remediation": "Request the vendor to provide a complete strata report, including all financial statements."
    }
  ],
  "remediation_readiness": "The identified gaps can be remediated by requesting the missing information from the vendor.",
  "key_dependencies": ["vendor_disclosure"]
}
```

Return a valid `ComplianceSummaryResult`.