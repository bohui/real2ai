---
type: "user"
category: "instructions"
name: "step3_action_plan"
version: "1.0.0"
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
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 7000
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
- Actions[] include title, description, owner, due_by, dependencies, blocking_risks
- Due dates align with settlement/condition deadlines
- Every critical discrepancy maps to an action

Return a valid ActionPlanResult.