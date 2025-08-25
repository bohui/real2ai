---
type: "user"
category: "instructions"
name: "conditions_analysis"
version: "2.0.0"
description: "Step 2.4 - Conditions Risk Assessment Analysis"
fragment_orchestration: "step2_conditions"
required_variables:
  - "analysis_timestamp"
optional_variables:
  - "entities_extraction"
  - "legal_requirements_matrix"
  - "contract_type"
  - "australian_state"
  - "retrieval_index_id"
  - "seed_snippets"
model_compatibility: [ "moonshotai/kimi-k2:free"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: ConditionsAnalysisResult
tags: ["step2", "conditions", "risk-assessment", "timelines"]
---

# Conditions Risk Assessment Analysis (Step 2.4)

Perform comprehensive analysis of all contract conditions with systematic risk assessment, timeline mapping, and dependency analysis.

## Contract Context
{% set meta = (entities_extraction or {}).get('metadata') or {} %}
- **State**: {{ australian_state or meta.get('state') or 'unknown' }}
- **Contract Type**: {{ contract_type or meta.get('contract_type') or 'unknown' }}
- **Purchase Method**: {{ meta.get('purchase_method') or 'unknown' }}
- **Use Category**: {{ meta.get('use_category') or 'unknown' }}
- **Property Condition**: {{ meta.get('property_condition') or 'unknown' }}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Condition Classification and Inventory

**Identify and classify all conditions:**
- Standard conditions (finance, inspection, legal searches)
- Special conditions (customized or non-standard terms)
- Conditions precedent vs conditions subsequent
- Mandatory vs optional conditions

**For each condition, determine:**
- Full description and purpose
- Classification type and category
- Party responsible for satisfaction
- Evidence or documentation required
- Deadline or timeframe requirements

### 2. Finance Condition Analysis

**Finance approval requirements:**
- Loan amount and percentage of purchase price
- Approval timeframe and business day calculations
- Interest rate specifications or market rate references
- Lender restrictions or requirements

**Adequacy assessment:**
- Whether timeframe is realistic for loan type
- Quality of escape clause provisions
- Level of buyer protection
- Unusual or restrictive finance terms

**Risk evaluation:**
- Finance approval probability assessment
- Consequences of finance condition failure
- Impact on settlement timeline
- Alternative financing considerations

### 3. Inspection Condition Analysis

**Inspection requirements:**
- Types of inspections required (building, pest, strata, etc.)
- Timeframe for completion
- Scope and standards specifications
- Access arrangements and limitations

**Adequacy assessment:**
- Whether timeframe allows proper inspections
- Comprehensiveness of inspection scope
- Action requirements based on results
- Defect threshold or materiality clauses

**Risk evaluation:**
- Inspection access risks
- Scope limitation risks
- Action requirement clarity
- Cost and responsibility allocation

### 4. Special Condition Assessment

**Analyze each special condition:**
- Purpose and commercial rationale
- Risk allocation between parties
- Enforceability and clarity concerns
- Unusual or seller-favoring aspects

**Specific analyses for common special conditions:**

**Sunset Clauses (off-plan contracts):**
- Sunset date adequacy and developer rights
- Extension provisions and buyer protection
- Compensation arrangements for delays
- Risk of project cancellation

**Subject-to-Sale Conditions:**
- Sale property requirements and timeline
- Buyer protection mechanisms
- Market risk allocation
- Escape clause provisions

**Development Approval Conditions:**
- Approval requirements and responsibility
- Timeline for obtaining approvals
- Risk allocation for approval failure
- Impact on settlement timing

### 5. Timeline Analysis and Dependencies

**Deadline mapping:**
- Chronological order of all condition deadlines
- Business day calculations and holiday impacts
- Buffer periods and timing adequacy
- Critical path analysis for condition satisfaction

**Dependency identification:**
- Sequential dependencies between conditions
- Parallel condition requirements
- Potential timeline conflicts or impossibilities
- Resource allocation conflicts

**Risk assessment:**
- Unrealistic timeline combinations
- Insufficient buffer periods
- Holiday period impacts
- Market timing risks

### 6. Overall Risk Assessment

**Condition risk evaluation:**
- Individual condition risk levels
- Cumulative risk assessment
- Buyer vs seller risk allocation
- Unusual or onerous requirements

**Buyer protection analysis:**
- Adequacy of escape clauses
- Fairness of condition terms
- Protection against market changes
- Recourse for condition failures

## Seed Snippets (Primary Context)

{% if seed_snippets %}
Use these high-signal condition snippets as primary context:
{{seed_snippets | tojsonpretty}}
{% else %}
No seed snippets provided.
{% endif %}

## Additional Context

{% if entities_extraction %}
### Entity Extraction Results (Baseline)
Previously extracted condition data (use as baseline; verify and reconcile):
{{entities_extraction | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} condition requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions (Seeds + Retrieval + Metadata Scoping)

1. Use `entities_extraction.conditions` and `metadata` as the baseline. Verify and enrich using `seed_snippets` as primary evidence.
2. If baseline + seeds are insufficient, perform targeted retrieval from `retrieval_index_id` for specific condition types (finance, inspection, special conditions) and deadlines (business days vs calendar).
3. Classify each condition (standard/special, precedent/subsequent), identify responsible parties, requirements, deadlines, and dependencies.
4. Compute or verify deadlines (use business day calculations where applicable) and map dependencies chronologically.
5. Assess buyer protection and risk levels (high/medium/low). Provide clause citations for all findings.
6. Record whether retrieval was used and how many additional snippets were incorporated.

## Expected Output

Provide comprehensive conditions analysis following the ConditionsAnalysisResult schema:

- Complete condition inventory with classification and risk assessment
- Detailed finance condition analysis with timeframe adequacy evaluation
- Comprehensive inspection condition review with scope validation
- Special condition assessment with risk allocation analysis
- Timeline dependency mapping with conflict identification
- Overall risk classification with buyer protection assessment
- Priority recommendations and negotiation points

**Critical Success Criteria (PRD 4.1.2.4):**
- 100% identification of all conditions
- Accurate risk scoring for each condition type
- Complete mapping of condition timelines and dependencies
- Clear assessment of buyer protection levels