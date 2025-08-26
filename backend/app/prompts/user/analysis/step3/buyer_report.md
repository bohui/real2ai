---
type: "user"
category: "instructions"
name: "step3_buyer_report"
version: "1.0.0"
description: "Step 3 - Buyer Report Synthesis"
fragment_orchestration: "step3_buyer_report"
required_variables:
  - "analysis_timestamp"
  - "australian_state"
  - "risk_summary_result"
  - "action_plan_result"
  - "compliance_summary_result"
  - "parties_property_result"
  - "financial_terms_result"
  - "conditions_result"
  - "warranties_result"
  - "default_termination_result"
  - "settlement_logistics_result"
  - "title_encumbrances_result"
  - "adjustments_outgoings_result"
  - "disclosure_compliance_result"
  - "special_risks_result"
optional_variables:
  - "retrieval_index_id"
  - "seed_snippets"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: BuyerReportResult
tags: ["step3", "buyer_report", "synthesis"]
---

# Buyer Report Synthesis (Step 3)

Consolidate Step 2 results with synthesized Step 3 outputs into a buyer-facing report.

Inputs:
- Risk summary: {{risk_summary_result | tojsonpretty}}
- Action plan: {{action_plan_result | tojsonpretty}}
- Compliance summary: {{compliance_summary_result | tojsonpretty}}
- All Step 2 results:
  - Parties & property: {{parties_property_result | tojsonpretty}}
  - Financial terms: {{financial_terms_result | tojsonpretty}}
  - Conditions: {{conditions_result | tojsonpretty}}
  - Warranties: {{warranties_result | tojsonpretty}}
  - Default & termination: {{default_termination_result | tojsonpretty}}
  - Settlement logistics: {{settlement_logistics_result | tojsonpretty}}
  - Title & encumbrances: {{title_encumbrances_result | tojsonpretty}}
  - Adjustments & outgoings: {{adjustments_outgoings_result | tojsonpretty}}
  - Disclosure compliance: {{disclosure_compliance_result | tojsonpretty}}
  - Special risks: {{special_risks_result | tojsonpretty}}

Seeds: {{ seed_snippets or [] | tojsonpretty }}

## Requirements
- Produce executive_summary, section_summaries, key_risks, action_plan_overview, evidence_refs
- Maintain consistent references and buyer-facing tone
- Ensure structure is ready for frontend rendering

Return a valid BuyerReportResult.