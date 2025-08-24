---
type: "user"
category: "instructions"
name: "warranties_analysis"
version: "1.0.0"
description: "Step 2.5 - Warranties and Representations Analysis"
fragment_orchestration: "step2_warranties"
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "entities_extraction"
  - "legal_requirements_matrix"
  - "contract_type"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: WarrantiesAnalysisResult
tags: ["step2", "warranties", "representations", "disclosures"]
---

# Warranties and Representations Analysis (Step 2.5)

Perform comprehensive analysis of all warranties, representations, vendor disclosures, and buyer acknowledgments in this Australian real estate contract, focusing on enforceability, buyer protection, and risk assessment.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Express Warranties and Representations

**Identify all express warranties:**
- Vendor warranties about property condition, title, and compliance
- Specific representations about property characteristics
- Performance warranties for fixtures, appliances, or systems
- Build quality warranties (for new properties)

**For each express warranty, analyze:**
- Precise scope and coverage details
- Duration and survival after settlement
- Conditions or limitations on warranty
- Evidence or documentation requirements
- Enforceability and clarity assessment

**Assess warranty adequacy:**
- Comprehensiveness of coverage
- Reasonableness of limitations
- Buyer protection level
- Comparison to market standards

### 2. Implied Warranties Assessment

**Identify potential implied warranties:**
- Fitness for purpose implications
- Merchantable quality standards
- Compliance with building codes
- Habitability warranties (residential properties)

**Statutory warranty analysis:**
- {{australian_state}} statutory warranty requirements
- Home Building Act implications (if applicable)
- Consumer protection law warranties
- Whether statutory warranties are preserved or excluded

**Exclusion attempts assessment:**
- Validity of attempted exclusions
- Enforceability under consumer protection laws
- Effectiveness of limitation clauses
- Buyer protection implications

### 3. Vendor Disclosures Review

**Categorize all vendor disclosures:**
- Structural defects and building issues
- Environmental concerns and contamination
- Planning and development restrictions
- Neighborhood disputes or issues
- Services and utilities limitations

**For each disclosure, evaluate:**
- Completeness and adequacy of description
- Severity and impact on property value/use
- Whether remediation is required or possible
- Cost implications for buyer
- Risk of undisclosed issues

**Disclosure compliance assessment:**
- {{australian_state}} mandatory disclosure requirements
- Vendor statement compliance
- Section 32 vendor statement adequacy (Victoria)
- Contract disclosure obligations

### 4. Buyer Acknowledgments Analysis

**Identify all buyer acknowledgments:**
- Acknowledgment of property condition
- Acceptance of disclosed defects
- Waiver of inspection rights
- Acknowledgment of restrictions or limitations

**Risk assessment for each acknowledgment:**
- Rights being waived or limited
- Fairness and reasonableness assessment
- Potential for buyer disadvantage
- Enforceability considerations

**Buyer protection evaluation:**
- Whether acknowledgments are properly informed
- Adequacy of disclosure before acknowledgment
- Reasonableness of waiver scope
- Consumer protection law implications

### 5. Warranty Limitation and Exclusion Analysis

**Identify all limitations and exclusions:**
- Time limitations on warranty claims
- Scope limitations and carve-outs
- Procedural requirements for claims
- Monetary limitations on liability

**Enforceability assessment:**
- Validity under Australian consumer protection laws
- Unfair contract terms provisions
- Reasonableness of limitations
- Clarity and prominence requirements

**Buyer impact evaluation:**
- Practical effect on buyer protection
- Availability of alternative remedies
- Consumer guarantee preservation
- Overall fairness assessment

### 6. Overall Risk Assessment

**Warranty coverage evaluation:**
- Adequacy of warranty protection
- Significant gaps in coverage
- Balance between vendor and buyer interests
- Comparison to market standards

**Enforcement risk assessment:**
- Likelihood of successful warranty claims
- Practical barriers to enforcement
- Cost and complexity of pursuing claims
- Alternative dispute resolution provisions

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction %}
### Entity Extraction Results
Previously extracted warranty data:
{{entities_extraction | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} warranty requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Comprehensive Review**: Examine all contract sections for warranties, representations, and disclosures
2. **Classification**: Categorize each warranty by type, scope, and enforceability
3. **Risk Assessment**: Evaluate buyer protection and enforcement risks
4. **Statutory Compliance**: Apply {{australian_state}} consumer protection and disclosure laws
5. **Practical Focus**: Emphasize actionable insights for buyer decision-making
6. **Evidence Documentation**: Reference specific contract clauses and legal requirements
7. **Market Context**: Compare to standard market practices in {{australian_state}}
8. **Consumer Protection**: Apply unfair contract terms and consumer guarantee provisions

## Expected Output

Provide comprehensive warranties analysis following the WarrantiesAnalysisResult schema:

- Complete inventory of all warranties with enforceability assessment
- Detailed vendor disclosure analysis with risk and cost implications
- Buyer acknowledgment review with fairness and protection evaluation
- Statutory warranty analysis with exclusion validity assessment
- Overall risk classification with buyer protection level determination
- Priority recommendations and negotiation points
- Evidence references and compliance assessment

**Critical Success Criteria (PRD 4.1.2.5):**
- 100% identification of all warranties and representations
- Accurate assessment of enforceability and buyer protection
- Complete disclosure compliance review
- Clear evaluation of warranty limitations and exclusions