---
type: "user"
category: "instructions"
name: "step3_risk_aggregation"
version: "1.1.0"
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
model_compatibility: ["gemini-1.5-flash", "gpt-4"]
max_tokens: 8000
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
- `top_risks` must be a list of `RiskItem` objects.
- `category` must be one of the `RiskCategory` enum values.
- `severity` must be one of the `SeverityLevel` enum values.
- Compute `overall_risk_score` (0-1), `top_risks`[], `category_breakdown`, `rationale`, and `confidence`.
- Top risks must reflect upstream issues and include `evidence_refs`.
- Ensure stable scoring (±0.05) for identical inputs.

### Example Output Format:
```json
{
  "overall_risk_score": 0.75,
  "top_risks": [
    {
      "title": "Unregistered Easement",
      "description": "A review of the survey plan indicates a potential unregistered easement for drainage at the rear of the property, which is not disclosed in the title documents.",
      "category": "title",
      "severity": "high",
      "likelihood": 0.8,
      "impact": 0.9,
      "evidence_refs": ["title_encumbrances_result.unregistered_easements"]
    },
    {
      "title": "Short Settlement Period",
      "description": "The settlement period of 21 days is shorter than the standard 30-45 days, which may not be sufficient to complete all necessary checks and secure finance.",
      "category": "settlement",
      "severity": "medium",
      "likelihood": 0.9,
      "impact": 0.6,
      "evidence_refs": ["settlement_logistics_result.settlement_date"]
    }
  ],
  "category_breakdown": {
    "title": 0.9,
    "settlement": 0.6,
    "financial": 0.2
  },
  "rationale": "The overall risk score is high due to the potential impact of the unregistered easement on the property's value and use. The short settlement period also adds significant pressure.",
  "confidence": 0.95
}
```

Return a valid `RiskSummaryResult`.