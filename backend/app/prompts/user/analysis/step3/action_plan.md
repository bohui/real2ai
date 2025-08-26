---
type: "user"
category: "instructions"
name: "step3_action_plan"
version: "1.1.0"
description: "Step 3 - Recommended Actions & Timeline"
fragment_orchestration: "step3_action_plan"
required_variables:
  - "analysis_timestamp"
  - "australian_state"
  - "cross_section_validation_result"
  - "settlement_logistics_result"
  - "adjustments_outgoings_result"
  - "disclosure_compliance_result"
  - "conditions_result"
optional_variables:
  - "retrieval_index_id"
  - "seed_snippets"
model_compatibility: ["gemini-1.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: ActionPlanResult
tags: ["step3", "action_plan", "timeline"]
---

# Recommended Actions & Timeline (Step 3)

Convert findings into a sequenced action plan keyed to settlement and condition deadlines.

Inputs:
- Cross-section validation: {{cross_section_validation_result | tojsonpretty}}
- Settlement logistics: {{settlement_logistics_result | tojsonpretty}}
- Adjustments & outgoings: {{adjustments_outgoings_result | tojsonpretty}}
- Disclosure compliance: {{disclosure_compliance_result | tojsonpretty}}
- Conditions: {{conditions_result | tojsonpretty}}

Seeds: {{ seed_snippets or [] | tojsonpretty }}

## Requirements
- Actions must be instances of the `ActionItem` schema.
- `owner` must be one of the `ActionOwner` enum values.
- `due_by` must be a `DueDate` object.
- Every critical discrepancy from the inputs must map to an action.
- The action plan must be sequenced logically.

### Example Output Format:
```json
{
  "actions": [
    {
      "title": "Verify Finance Condition",
      "description": "Confirm with your lender that the finance condition has been satisfied and provide written confirmation to the vendor's solicitor.",
      "owner": "buyer",
      "due_by": {
        "relative_deadline": "3 days before finance condition expiry"
      },
      "dependencies": [],
      "blocking_risks": ["Finance not approved"]
    },
    {
      "title": "Arrange Building and Pest Inspection",
      "description": "Engage a qualified inspector to conduct a building and pest inspection of the property.",
      "owner": "buyer",
      "due_by": {
        "date": "2025-09-10"
      },
      "dependencies": [],
      "blocking_risks": ["Major building defects found"]
    }
  ],
  "timeline_summary": "The action plan is structured around the key dates of the contract, ensuring all conditions are met before settlement."
}
```

Return a valid `ActionPlanResult`.