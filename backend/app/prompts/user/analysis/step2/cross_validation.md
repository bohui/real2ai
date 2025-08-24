---
type: "user"
category: "instructions"
name: "cross_validation_analysis"
version: "1.0.0"
description: "Step 2.12 - Cross-Section Validation and Consistency Checks"
fragment_orchestration: "step2_cross_validation"
required_variables:
  - "contract_text"
  - "all_section_results"
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "entities_extraction"
  - "legal_requirements_matrix"
  - "contract_type"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 10000
temperature_range: [0.1, 0.3]
output_parser: CrossValidationResult
tags: ["step2", "cross-validation", "consistency", "synthesis"]
---

# Cross-Section Validation and Consistency Checks (Step 2.12)

Perform comprehensive cross-section validation, consistency verification, and synthesis analysis across all Step 2 section analyses, focusing on data integrity, logical consistency, and strategic guidance synthesis.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Previous Section Results for Validation

All previous section analysis results for cross-validation:
{{all_section_results | tojsonpretty}}

## Validation Requirements

### 1. Cross-Section Data Consistency

**Financial terms validation:**
- Purchase price consistency across all sections
- Deposit amount verification and settlement calculation alignment
- Payment timeline coordination with conditions and settlement
- GST treatment consistency across financial and adjustment sections

**Date and timeline validation:**
- Settlement date consistency across sections
- Condition deadlines logical sequencing
- Timeline feasibility across all obligations
- Business day calculations consistency

**Party information validation:**
- Party name and detail consistency
- Authority and capacity verification alignment
- Contact information consistency
- Signature authority validation

**Property description validation:**
- Property address and legal description consistency
- Title reference alignment across sections
- Boundary and survey plan consistency
- Inclusions/exclusions alignment

### 2. Logical Consistency Verification

**Condition interdependency validation:**
- Finance condition alignment with purchase price
- Inspection timing coordination with settlement
- Planning approval coordination with development intentions
- Condition satisfaction logical sequencing

**Risk assessment consistency:**
- Risk level alignment across related sections
- Risk mitigation strategy consistency
- Risk timeline coordination
- Overall risk profile coherence

**Legal obligation consistency:**
- Warranty provisions alignment with disclosure obligations
- Default provisions consistency with remedy availability
- Termination rights logical correlation
- Obligation timeline coordination

### 3. Mathematical and Calculation Verification

**Financial calculation cross-checks:**
- Purchase price and deposit calculation accuracy
- Adjustment calculations mathematical verification
- Settlement statement component reconciliation
- Tax and duty calculation coordination

**Timeline calculation verification:**
- Business day calculations consistency
- Deadline coordination and feasibility
- Buffer period adequacy assessment
- Critical path timeline validation

**Proportionality and ratio verification:**
- Deposit percentage calculations
- Adjustment apportionment accuracy
- Fee and cost allocation proportionality
- Risk/reward ratio assessment

### 4. Legal and Regulatory Consistency

**Legislative compliance coordination:**
- {{australian_state}} law compliance across sections
- Regulatory requirement consistency
- Consumer protection law alignment
- Professional standard compliance

**Legal precedent consistency:**
- Case law application consistency
- Professional guidance alignment
- Industry standard compliance
- Best practice adherence

### 5. Risk Profile Integration and Synthesis

**Cumulative risk assessment:**
- Individual section risks aggregation
- Risk interaction and amplification analysis
- Risk correlation identification
- Overall risk profile synthesis

**Risk mitigation coordination:**
- Mitigation strategy consistency across sections
- Resource allocation for risk management
- Timeline coordination for mitigation actions
- Cost-benefit analysis of mitigation options

**Risk prioritization synthesis:**
- Critical risk identification across sections
- Risk urgency and impact assessment
- Resource allocation priorities
- Risk acceptance/mitigation decisions

### 6. Commercial and Practical Feasibility

**Commercial logic validation:**
- Deal structure commercial sensibility
- Market norm compliance assessment
- Practical implementation feasibility
- Resource requirement realism

**Execution feasibility assessment:**
- Timeline realism and achievability
- Resource availability and coordination
- Professional service coordination
- Practical completion probability

### 7. Strategic Synthesis and Guidance

**Overall contract assessment:**
- Contract quality and completeness
- Market positioning and competitiveness
- Buyer protection adequacy
- Strategic value proposition

**Decision framework development:**
- Proceed/negotiate/withdraw criteria
- Key negotiation priorities
- Professional advice requirements
- Risk tolerance considerations

**Implementation roadmap:**
- Priority action sequence
- Resource allocation strategy
- Timeline and milestone planning
- Success criteria definition

## Validation Methodology

### Data Integrity Checks
1. **Cross-Reference Validation**: Verify all cross-references between sections
2. **Calculation Verification**: Mathematical accuracy of all calculations
3. **Date Logic Checking**: Logical consistency of all dates and timelines
4. **Legal Consistency**: Compliance and legal requirement alignment

### Consistency Analysis
1. **Information Correlation**: Ensure consistent information across sections
2. **Risk Level Alignment**: Verify consistent risk assessments
3. **Recommendation Coherence**: Ensure recommendations don't contradict
4. **Strategic Alignment**: Verify strategic guidance consistency

### Quality Assurance
1. **Completeness Verification**: Ensure all required analysis is complete
2. **Accuracy Assessment**: Verify accuracy of findings and calculations
3. **Evidence Validation**: Confirm evidence supports conclusions
4. **Professional Standards**: Ensure professional standard compliance

## Contract Text for Reference

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction %}
### Entity Extraction Results
Original entity extraction for cross-validation:
{{entities_extraction | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} legal requirements for validation:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Systematic Cross-Validation**: Systematically validate consistency across all section analyses
2. **Mathematical Verification**: Verify all calculations and numerical consistency
3. **Legal Coherence**: Ensure legal analysis consistency and compliance
4. **Risk Integration**: Synthesize risk assessments into coherent overall profile
5. **Strategic Synthesis**: Develop strategic guidance from comprehensive analysis
6. **Quality Assurance**: Apply rigorous quality checks to all findings
7. **Evidence Correlation**: Verify evidence supports all conclusions
8. **Professional Standards**: Ensure analysis meets professional practice standards

## Expected Output

Provide comprehensive cross-validation analysis following the CrossValidationResult schema:

- Complete section validation with quality assessment and consistency verification
- Cross-section consistency analysis with discrepancy identification and resolution
- Data integrity verification with accuracy assessment and improvement recommendations
- Comprehensive synthesis with strategic guidance and decision framework
- Overall validation status with critical findings and action priorities
- Risk integration with cumulative assessment and mitigation roadmap
- Professional guidance requirements with specialization priorities
- Strategic recommendations with implementation roadmap and success criteria

**Critical Success Criteria (PRD 4.1.2.12):**
- 100% cross-section consistency validation
- Complete data integrity verification with accuracy assessment
- Comprehensive synthesis with strategic guidance
- Clear overall validation status with actionable recommendations