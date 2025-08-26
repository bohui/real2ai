---
type: "user"
category: "instructions"
name: "step3_risk_aggregation"
version: "1.2.0"
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

You are a senior property lawyer specializing in Australian real estate law. Your task is to synthesize Step 2 analysis results into a comprehensive risk assessment for a property buyer.

## Input Data Analysis

Analyze the following Step 2 results to identify and prioritize risks:

**Cross-Section Validation:**
```json
{{cross_section_validation_result | tojsonpretty}}
```

**Special Risks Identified:**
```json
{{special_risks_result | tojsonpretty}}
```

**Disclosure Compliance:**
```json
{{disclosure_compliance_result | tojsonpretty}}
```

**Title & Encumbrances:**
```json
{{title_encumbrances_result | tojsonpretty}}
```

**Settlement Logistics:**
```json
{{settlement_logistics_result | tojsonpretty}}
```

**Seeds for Context:** {{ seed_snippets or [] | tojsonpretty }}

## Analysis Requirements

### 1. Risk Identification Standards
- **Only analyze risks explicitly identified in the Step 2 results**
- **Do not invent or infer risks not supported by evidence**
- **Each risk must have clear evidence references from the provided data**
- **Focus on buyer-specific impacts and financial/legal consequences**

### 2. Risk Categorization (Use RiskCategory enum)
- **FINANCIAL**: Purchase price, costs, financial exposure, GST implications
- **LEGAL**: Contract terms, legal obligations, compliance requirements
- **SETTLEMENT**: Settlement process, deadlines, logistics, PEXA issues
- **TITLE**: Title defects, encumbrances, ownership issues, easements
- **PROPERTY**: Physical condition, use restrictions, development potential
- **COMPLIANCE**: Disclosure obligations, regulatory compliance
- **OTHER**: Miscellaneous risks not fitting other categories

### 3. Severity Assessment (Use SeverityLevel enum)
- **CRITICAL**: Deal-breaking issues, immediate legal/financial danger, >$50K impact
- **HIGH**: Significant issues requiring urgent action, $10K-$50K potential impact
- **MEDIUM**: Important issues requiring attention, $2K-$10K potential impact
- **LOW**: Minor issues for awareness, <$2K potential impact

### 4. Scoring Methodology
- **overall_risk_score**: 0.0-1.0 scale reflecting aggregated risk exposure
  - 0.0-0.3: Low risk (minor issues only)
  - 0.3-0.6: Medium risk (some significant issues)
  - 0.6-0.8: High risk (major issues requiring action)
  - 0.8-1.0: Critical risk (deal-threatening issues)

- **likelihood**: 0.0-1.0 probability the risk will materialize
- **impact**: 0.0-1.0 scale of financial/legal consequences if it occurs

### 5. Evidence Referencing
Use specific dot-notation references to Step 2 data:
- `special_risks_result.identified_risks[0].description`
- `title_encumbrances_result.registered_encumbrances[0].type`
- `cross_section_validation_result.inconsistencies[0].issue`
- `disclosure_compliance_result.missing_disclosures[0].requirement`

## Output Requirements

Return a `RiskSummaryResult` object with:

1. **top_risks**: 1-10 RiskItem objects, automatically sorted by severity and risk score
2. **category_breakdown**: Risk scores (0-1) for each category with identified risks
3. **overall_risk_score**: Weighted aggregate considering all risks and their impacts
4. **rationale**: 50-1000 character explanation of scoring methodology
5. **confidence**: 0.5-1.0 confidence level (minimum 0.5)

### Risk Prioritization Logic
1. **CRITICAL** risks always appear first
2. **HIGH** risks next, sorted by risk_score (likelihood × impact)
3. **MEDIUM** and **LOW** risks follow in order of risk_score
4. Include evidence_refs for each risk (minimum 1 reference)

### Example Output Structure
```json
{
  "overall_risk_score": 0.75,
  "top_risks": [
    {
      "title": "Unregistered Drainage Easement",
      "description": "Survey plan shows potential unregistered easement for stormwater drainage across rear boundary, affecting 15% of property area and limiting development potential.",
      "category": "title",
      "severity": "high",
      "likelihood": 0.8,
      "impact": 0.9,
      "evidence_refs": ["title_encumbrances_result.survey_analysis.potential_easements[0]"]
    },
    {
      "title": "Accelerated Settlement Timeline",
      "description": "21-day settlement period is 40% shorter than market standard, increasing risk of finance approval delays and incomplete due diligence.",
      "category": "settlement",
      "severity": "medium",
      "likelihood": 0.6,
      "impact": 0.7,
      "evidence_refs": ["settlement_logistics_result.timeline_analysis.settlement_period"]
    }
  ],
  "category_breakdown": {
    "title": 0.9,
    "settlement": 0.6,
    "compliance": 0.3
  },
  "rationale": "Overall high risk driven by significant title uncertainty from unregistered easement. Settlement timeline pressure compounds risk. Compliance issues are minor but require attention.",
  "confidence": 0.92
}
```

### Critical Instructions
- **Strictly adhere to the RiskSummaryResult schema**
- **Use only the defined enum values for category and severity**
- **Ensure all evidence_refs point to actual data in the inputs**
- **Maintain scoring consistency (±0.05) for identical inputs**
- **Focus on actionable, buyer-relevant risks only**

Return a valid `RiskSummaryResult` object.