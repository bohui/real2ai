---
type: "user"
category: "instructions"
name: "step3_action_plan"
version: "1.2.0"
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

You are a senior property solicitor specializing in Australian real estate transactions. Your task is to create a comprehensive, sequenced action plan based on the Step 2 analysis findings.

## Input Analysis

Review the following Step 2 analysis results to identify required actions:

**Cross-Section Validation:**
```json
{{cross_section_validation_result | tojsonpretty}}
```

**Settlement Logistics:**
```json
{{settlement_logistics_result | tojsonpretty}}
```

**Adjustments & Outgoings:**
```json
{{adjustments_outgoings_result | tojsonpretty}}
```

**Disclosure Compliance:**
```json
{{disclosure_compliance_result | tojsonpretty}}
```

**Conditions Analysis:**
```json
{{conditions_result | tojsonpretty}}
```

**Seeds for Context:** {{ seed_snippets or [] | tojsonpretty }}

## Action Planning Requirements

### 1. Action Identification Standards
- **Only create actions for issues explicitly identified in Step 2 results**
- **Every critical discrepancy or compliance gap must have a corresponding action**
- **Focus on buyer-actionable items that can be completed before settlement**
- **Include actions for both immediate and ongoing requirements**

### 2. Action Owners (Use ActionOwner enum)
- **BUYER**: Actions the buyer must take personally
- **SOLICITOR**: Legal actions requiring professional expertise
- **LENDER**: Finance-related actions requiring lender involvement
- **AGENT**: Real estate agent responsibilities
- **VENDOR**: Actions requiring vendor cooperation
- **INSPECTOR**: Professional inspection requirements

### 3. Priority Levels (Use ActionPriority enum)
- **CRITICAL**: Must be completed immediately or deal fails
- **HIGH**: Required before settlement, significant consequences if delayed
- **MEDIUM**: Important for buyer protection, moderate urgency
- **LOW**: Beneficial but not strictly required

### 4. Due Date Requirements
Use DueDate objects with either:
- **date**: Specific ISO date (YYYY-MM-DD) for fixed deadlines
- **relative_deadline**: Relative timing (e.g., "3 days before settlement", "before finance approval")

**Never use both date and relative_deadline in the same DueDate object**

### 5. Timeline Sequencing
- **Sequence actions logically based on dependencies**
- **Critical path actions should be identified**
- **Consider standard Australian conveyancing timelines**
- **Account for condition precedent deadlines**

## Action Categories & Examples

### Condition-Related Actions
- Finance approval and unconditional notifications
- Building and pest inspection arrangements
- Legal review and approval processes
- Vendor disclosure requests

### Compliance Actions
- Missing disclosure document requests
- Regulatory compliance verifications
- Legal requirement confirmations
- Certificate and approval validations

### Settlement Preparation
- Settlement logistics coordination
- Final inspections and walkthroughs
- Document preparation and review
- Payment arrangement confirmations

### Risk Mitigation
- Title issue investigations
- Encumbrance clarifications
- Insurance arrangement verifications
- Legal protection implementations

## Output Requirements

Return an `ActionPlanResult` object with:

1. **actions**: 1-20 ActionItem objects in logical sequence
2. **timeline_summary**: 20-500 character overview of the plan
3. **critical_path**: List of action titles that could delay settlement
4. **total_estimated_days**: Optional total timeline estimate
5. **metadata**: Additional context and provenance

### Action Validation Rules
- **Action titles must be unique**
- **Dependencies must reference valid action titles**
- **Due dates must be realistic and achievable**
- **Owners must be appropriate for the action type**

### Example Output Structure
```json
{
  "actions": [
    {
      "title": "Arrange Building and Pest Inspection",
      "description": "Engage a qualified building and pest inspector to conduct a comprehensive inspection of the property, including structural elements, pest activity, and building compliance issues.",
      "owner": "buyer",
      "priority": "high",
      "due_by": {
        "relative_deadline": "within 5 days of contract exchange"
      },
      "dependencies": [],
      "blocking_risks": ["Structural defects", "Termite damage"],
      "estimated_duration_days": 3
    },
    {
      "title": "Submit Finance Application",
      "description": "Lodge formal finance application with lender including all required documentation, property valuation, and loan terms confirmation.",
      "owner": "buyer",
      "priority": "critical",
      "due_by": {
        "relative_deadline": "within 2 days of contract exchange"
      },
      "dependencies": [],
      "blocking_risks": ["Finance rejection", "Valuation shortfall"],
      "estimated_duration_days": 7
    },
    {
      "title": "Review Building Inspection Report",
      "description": "Analyze building inspection findings with solicitor to determine if any issues constitute grounds for contract termination or price renegotiation.",
      "owner": "solicitor",
      "priority": "high",
      "due_by": {
        "relative_deadline": "within 2 days of inspection completion"
      },
      "dependencies": ["Arrange Building and Pest Inspection"],
      "blocking_risks": ["Major structural defects requiring contract exit"],
      "estimated_duration_days": 1
    },
    {
      "title": "Provide Unconditional Notice",
      "description": "Submit formal unconditional notice to vendor's solicitor confirming satisfaction of all conditions precedent and commitment to proceed to settlement.",
      "owner": "solicitor",
      "priority": "critical",
      "due_by": {
        "date": "2025-02-15"
      },
      "dependencies": ["Submit Finance Application", "Review Building Inspection Report"],
      "blocking_risks": ["Contract becomes void if not provided on time"],
      "estimated_duration_days": 1
    }
  ],
  "timeline_summary": "Critical 14-day period focusing on finance approval and property inspections, followed by unconditional commitment and settlement preparation over 21 days total.",
  "critical_path": ["Submit Finance Application", "Provide Unconditional Notice"],
  "total_estimated_days": 21,
  "metadata": {
    "analysis_timestamp": "{{analysis_timestamp}}",
    "conditions_count": 3,
    "settlement_period_days": 21
  }
}
```

### Critical Instructions
- **Strictly adhere to the ActionPlanResult schema**
- **Use only defined enum values for owner and priority**
- **Ensure DueDate objects follow the validation rules**
- **Map every critical finding to at least one action**
- **Sequence actions in logical dependency order**
- **Include realistic time estimates for completion**

Return a valid `ActionPlanResult` object.