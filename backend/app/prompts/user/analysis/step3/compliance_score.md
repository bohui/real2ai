---
type: "user"
category: "instructions"
name: "step3_compliance_score"
version: "1.2.0"
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

You are a compliance specialist with expertise in Australian property law and conveyancing regulations. Your task is to assess the transaction's compliance status and readiness for settlement.

## Input Analysis

Analyze the following Step 2 results to evaluate compliance status:

**Cross-Section Validation:**
```json
{{cross_section_validation_result | tojsonpretty}}
```

**Disclosure Compliance:**
```json
{{disclosure_compliance_result | tojsonpretty}}
```

**Conditions Analysis:**
```json
{{conditions_result | tojsonpretty}}
```

**Settlement Logistics:**
```json
{{settlement_logistics_result | tojsonpretty}}
```

**Seeds for Context:** {{ seed_snippets or [] | tojsonpretty }}

## Compliance Assessment Framework

### 1. Compliance Categories to Evaluate

#### Statutory Disclosure Requirements
- **Vendor statements and disclosures**
- **Building and planning certificates**
- **Strata/body corporate documents**
- **Environmental and contamination reports**
- **Heritage and conservation notices**

#### Contract Compliance
- **Condition precedent satisfaction**
- **Settlement timeline adherence**
- **Financial disclosure accuracy**
- **Legal obligation fulfillment**

#### Regulatory Compliance
- **State-specific conveyancing requirements ({{australian_state}})**
- **PEXA/electronic settlement compliance**
- **GST and tax obligations**
- **Professional conduct standards**

### 2. Scoring Methodology

**Compliance Score Range: 0.0-1.0**
- **0.9-1.0**: Fully compliant, ready for settlement
- **0.8-0.9**: Substantially compliant, minor gaps
- **0.6-0.8**: Partially compliant, significant gaps requiring action
- **0.4-0.6**: Non-compliant, major issues requiring remediation
- **0.0-0.4**: Critically non-compliant, settlement at risk

### 3. Gap Assessment (Use SeverityLevel enum)

**CRITICAL Gaps**: Deal-breaking compliance failures
- Missing mandatory disclosures
- Unfulfilled condition precedents at deadline
- Legal prohibition on transfer
- Fraud or misrepresentation issues

**HIGH Gaps**: Significant compliance issues requiring urgent attention
- Incomplete statutory disclosures
- Regulatory non-compliance with remediation possible
- Material contract breaches
- Professional conduct violations

**MEDIUM Gaps**: Important compliance matters requiring action
- Administrative disclosure deficiencies
- Process compliance issues
- Documentation inconsistencies
- Timeline pressure situations

**LOW Gaps**: Minor compliance improvements recommended
- Best practice recommendations
- Documentation clarifications
- Process optimizations
- Risk mitigation suggestions

### 4. Status Classification (Use ComplianceStatus enum)

- **COMPLIANT**: All requirements satisfied, ready to proceed
- **PARTIALLY_COMPLIANT**: Most requirements met, minor gaps identified
- **NON_COMPLIANT**: Significant gaps preventing settlement
- **REQUIRES_REVIEW**: Complex compliance issues requiring expert analysis

## Output Requirements

Return a `ComplianceSummaryResult` object with:

1. **score**: 0.0-1.0 compliance assessment
2. **status**: Overall compliance status from enum
3. **gaps**: List of ComplianceGap objects (0-15 maximum)
4. **remediation_readiness**: Assessment of remediation feasibility
5. **key_dependencies**: External factors affecting compliance
6. **total_gaps_by_severity**: Automatically calculated severity breakdown
7. **estimated_remediation_timeline**: Days to achieve compliance

### Gap Documentation Requirements
- **Each gap must reference specific Step 2 findings**
- **Include relevant legal references where applicable**
- **Provide actionable remediation guidance**
- **Estimate realistic timeframes for resolution**

### Example Output Structure
```json
{
  "score": 0.75,
  "status": "partially_compliant",
  "gaps": [
    {
      "name": "Missing Building Compliance Certificate",
      "description": "The vendor has not provided a current building compliance certificate as required under section 32 vendor statement obligations for this jurisdiction.",
      "severity": "high",
      "remediation": "Request vendor to obtain compliance certificate from local council. If unavailable, seek legal advice on alternative compliance pathways or risk mitigation.",
      "legal_reference": "Conveyancing Act 1919 (NSW) s32, Property Law Act 1958 (VIC) s32",
      "estimated_remediation_days": 14
    },
    {
      "name": "Incomplete Strata Financial Statements",
      "description": "Strata plan financial statements provided are missing the most recent quarterly report and do not include capital works fund details.",
      "severity": "medium",
      "remediation": "Contact strata manager to obtain complete financial records including capital works fund statements and recent levy notices.",
      "legal_reference": "Strata Schemes Management Act 2015 (NSW) Schedule 3",
      "estimated_remediation_days": 7
    },
    {
      "name": "Settlement Timeline Pressure",
      "description": "The 21-day settlement period may not provide sufficient time for standard due diligence and compliance verification processes.",
      "severity": "medium",
      "remediation": "Negotiate settlement extension with vendor or implement accelerated due diligence timeline with increased resource allocation.",
      "estimated_remediation_days": 3
    }
  ],
  "remediation_readiness": "Most identified gaps can be remediated through vendor cooperation and standard processes. Timeline pressure requires immediate attention to resource allocation.",
  "key_dependencies": ["vendor_cooperation", "council_responsiveness", "strata_manager_availability"],
  "total_gaps_by_severity": {
    "high": 1,
    "medium": 2,
    "low": 0,
    "critical": 0
  },
  "estimated_remediation_timeline": 14,
  "metadata": {
    "analysis_timestamp": "{{analysis_timestamp}}",
    "jurisdiction": "{{australian_state}}",
    "total_disclosures_reviewed": 8,
    "missing_disclosure_count": 2
  }
}
```

### Scoring Consistency Rules
- **Critical gaps**: Score cannot exceed 0.5
- **Multiple critical gaps**: Score cannot exceed 0.3
- **High severity gaps**: Reduce score by 0.1-0.2 per gap
- **Medium severity gaps**: Reduce score by 0.05-0.1 per gap
- **Low severity gaps**: Reduce score by 0.01-0.05 per gap

### Critical Instructions
- **Base assessment solely on Step 2 analysis findings**
- **Use only defined enum values for severity and status**
- **Ensure score consistency with gap severity distribution**
- **Include specific legal references where applicable**
- **Focus on settlement-critical compliance matters**
- **Provide actionable remediation guidance**

Return a valid `ComplianceSummaryResult` object.