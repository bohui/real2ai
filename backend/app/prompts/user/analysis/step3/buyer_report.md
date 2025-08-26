---
type: "user"
category: "instructions"
name: "step3_buyer_report"
version: "1.1.0"
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
model_compatibility: ["gemini-1.5-flash", "gpt-4"]
max_tokens: 8192
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
- `key_risks` must be a list of `KeyRisk` objects.
- `action_plan_overview` must be a list of `ActionPlanOverviewItem` objects.
- Produce `executive_summary`, `section_summaries`, `key_risks`, `action_plan_overview`, and `evidence_refs`.
- Maintain consistent references and a buyer-facing tone.
- Ensure the structure is ready for frontend rendering.

### Example Output Format:
```json
{
  "executive_summary": "This report summarizes the key findings of our analysis of the property contract. We have identified a high-risk issue related to an unregistered easement and a medium-risk issue concerning the short settlement period. We recommend you take immediate action to address these points.",
  "section_summaries": [
    {
      "name": "Title & Encumbrances",
      "summary": "The title is clear of registered encumbrances, but a potential unregistered easement was identified on the survey plan."
    },
    {
      "name": "Settlement Logistics",
      "summary": "The settlement period is 21 days, which is shorter than the standard 30-45 days."
    }
  ],
  "key_risks": [
    {
      "title": "Unregistered Easement",
      "description": "A potential unregistered easement for drainage at the rear of the property could impact your use and enjoyment of the property."
    },
    {
      "title": "Short Settlement Period",
      "description": "The 21-day settlement period may not be sufficient to complete all necessary checks and secure finance."
    }
  ],
  "action_plan_overview": [
    {
      "title": "Investigate Unregistered Easement",
      "owner": "solicitor"
    },
    {
      "title": "Negotiate Settlement Extension",
      "owner": "buyer"
    }
  ],
  "evidence_refs": ["title_encumbrances_result.unregistered_easements", "settlement_logistics_result.settlement_date"]
}
```

Return a valid `BuyerReportResult`.