---
type: "user"
category: "instructions"
name: "step3_buyer_report"
version: "1.2.0"
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

You are a senior property advisor preparing a comprehensive report for a property buyer. Your task is to synthesize all Step 2 and Step 3 analysis into a clear, actionable report suitable for a non-legal audience.

## Complete Analysis Input

Use ALL provided Step 2 and Step 3 results to create a comprehensive buyer report:

**Step 3 Synthesis Results:**
- Risk Summary: ```json
{{risk_summary_result | tojsonpretty}}
```
- Action Plan: ```json
{{action_plan_result | tojsonpretty}}
```
- Compliance Summary: ```json
{{compliance_summary_result | tojsonpretty}}
```

**Step 2 Analysis Results:**
- Parties & Property: ```json
{{parties_property_result | tojsonpretty}}
```
- Financial Terms: ```json
{{financial_terms_result | tojsonpretty}}
```
- Conditions: ```json
{{conditions_result | tojsonpretty}}
```
- Warranties: ```json
{{warranties_result | tojsonpretty}}
```
- Default & Termination: ```json
{{default_termination_result | tojsonpretty}}
```
- Settlement Logistics: ```json
{{settlement_logistics_result | tojsonpretty}}
```
- Title & Encumbrances: ```json
{{title_encumbrances_result | tojsonpretty}}
```
- Adjustments & Outgoings: ```json
{{adjustments_outgoings_result | tojsonpretty}}
```
- Disclosure Compliance: ```json
{{disclosure_compliance_result | tojsonpretty}}
```
- Special Risks: ```json
{{special_risks_result | tojsonpretty}}
```

**Seeds for Context:** {{ seed_snippets or [] | tojsonpretty }}

## Report Structure Requirements

### 1. Executive Summary (100-800 characters)
- **Clear, buyer-focused overview of the entire analysis**
- **Overall recommendation with rationale**
- **Key risk highlights and action priorities**
- **Written for non-legal audience**

### 2. Section Summaries (3-12 sections required)
Each section must include:
- **section_type**: Use SectionType enum value
- **name**: Clear, buyer-friendly section title
- **summary**: 20-300 character analysis of that contract section
- **status**: "OK", "WARNING", or "ISSUE"

Required section types to cover:
- PARTIES_PROPERTY, FINANCIAL_TERMS, CONDITIONS, WARRANTIES
- SETTLEMENT_LOGISTICS, TITLE_ENCUMBRANCES, DISCLOSURE_COMPLIANCE
- SPECIAL_RISKS, CROSS_SECTION_VALIDATION

### 3. Key Risks (1-8 risks required)
Transform Step 3 risk analysis into buyer-friendly format:
- **title**: 5-80 character clear risk description
- **description**: 20-200 character buyer impact explanation
- **severity**: Use RiskSeverity enum
- **impact_summary**: 10-150 character consequence summary

### 4. Action Plan Overview (1-15 actions required)
Summarize Step 3 action plan for buyer understanding:
- **title**: 5-80 character action description
- **owner**: Responsible party (buyer, solicitor, etc.)
- **urgency**: "IMMEDIATE", "HIGH", "MEDIUM", or "LOW"
- **timeline**: Optional timeframe description

### 5. Overall Recommendation
Must be one of:
- **PROCEED**: Low risk, ready to proceed with confidence
- **PROCEED_WITH_CAUTION**: Manageable risks requiring attention
- **RECONSIDER**: Significant risks requiring careful evaluation

## Writing Guidelines

### Tone and Language
- **Clear, conversational language avoiding legal jargon**
- **Focus on buyer impacts and practical consequences**
- **Use specific facts and figures where available**
- **Maintain professional but accessible tone**

### Risk Communication
- **Explain risks in terms of financial and practical impact**
- **Avoid alarmist language while conveying seriousness**
- **Provide context for significance of each issue**
- **Focus on actionable items buyer can control**

### Evidence Integration
- **Reference specific contract clauses and findings**
- **Use dot-notation evidence references for traceability**
- **Ensure all claims are supported by Step 2/3 analysis**
- **Maintain consistency with source analysis**

## Output Requirements

Return a `BuyerReportResult` object with:

1. **executive_summary**: Comprehensive overview
2. **section_summaries**: Analysis of all major contract sections
3. **key_risks**: Priority risks sorted by severity
4. **action_plan_overview**: Essential actions sorted by urgency
5. **evidence_refs**: Source references for traceability
6. **overall_recommendation**: Final recommendation
7. **confidence_level**: Analysis confidence (0.7-1.0)

### Example Output Structure
```json
{
  "executive_summary": "Our analysis of this NSW residential property contract reveals several important considerations requiring your attention. While the property and financial terms are generally favorable, we've identified a potential unregistered easement issue that requires immediate investigation and a compressed settlement timeline that may challenge your preparation time. We recommend proceeding with caution while addressing these specific concerns through the outlined action plan.",
  "section_summaries": [
    {
      "section_type": "title_encumbrances",
      "name": "Title & Encumbrances",
      "summary": "Title is clear of major encumbrances, but survey indicates potential unregistered drainage easement affecting rear boundary requiring investigation.",
      "status": "WARNING"
    },
    {
      "section_type": "settlement_logistics",
      "name": "Settlement Process",
      "summary": "21-day settlement period is achievable but requires immediate action on finance approval and inspections to meet deadlines.",
      "status": "WARNING"
    },
    {
      "section_type": "financial_terms",
      "name": "Financial Terms",
      "summary": "Purchase price is market-appropriate with standard deposit terms and clear GST treatment. No significant financial concerns identified.",
      "status": "OK"
    },
    {
      "section_type": "conditions",
      "name": "Contract Conditions",
      "summary": "Standard finance and building inspection conditions provide adequate buyer protection with reasonable timeframes for completion.",
      "status": "OK"
    }
  ],
  "key_risks": [
    {
      "title": "Unregistered Drainage Easement",
      "description": "Survey plan indicates potential drainage easement across rear boundary not shown on title, which could limit property use and affect value.",
      "severity": "high",
      "impact_summary": "May restrict development options and reduce property value by 5-10%"
    },
    {
      "title": "Compressed Settlement Timeline",
      "description": "21-day settlement period leaves minimal time for due diligence, finance approval, and issue resolution.",
      "severity": "medium",
      "impact_summary": "Risk of delayed settlement penalties or contract termination if deadlines not met"
    }
  ],
  "action_plan_overview": [
    {
      "title": "Investigate Potential Easement",
      "owner": "solicitor",
      "urgency": "HIGH",
      "timeline": "within 5 days"
    },
    {
      "title": "Expedite Finance Application",
      "owner": "buyer",
      "urgency": "IMMEDIATE",
      "timeline": "within 2 days"
    },
    {
      "title": "Arrange Building Inspection",
      "owner": "buyer",
      "urgency": "HIGH",
      "timeline": "within 3 days"
    }
  ],
  "evidence_refs": [
    "title_encumbrances_result.survey_analysis.potential_easements",
    "settlement_logistics_result.timeline_analysis.settlement_period",
    "risk_summary_result.top_risks",
    "action_plan_result.critical_path"
  ],
  "overall_recommendation": "PROCEED_WITH_CAUTION",
  "confidence_level": 0.88,
  "metadata": {
    "analysis_timestamp": "{{analysis_timestamp}}",
    "jurisdiction": "{{australian_state}}",
    "total_risks_identified": 2,
    "critical_actions": 3,
    "report_version": "1.2.0"
  }
}
```

### Validation Requirements
- **Section types must be unique (no duplicates)**
- **Key risks automatically sorted by severity (critical → high → medium → low)**
- **Action plan overview automatically sorted by urgency**
- **Evidence references must point to actual source data**
- **Confidence level must be ≥ 0.7**

### Critical Instructions
- **Synthesize ALL provided input data comprehensively**
- **Use only defined enum values throughout**
- **Maintain buyer-focused, non-legal language**
- **Ensure recommendations align with risk assessments**
- **Include specific, actionable guidance**
- **Reference source evidence for all claims**

Return a valid `BuyerReportResult` object.