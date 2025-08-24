---
type: "user"
category: "instructions"
name: "default_termination_analysis"
version: "1.0.0"
description: "Step 2.6 - Default and Termination Analysis"
fragment_orchestration: "step2_default_termination"
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
output_parser: DefaultTerminationAnalysisResult
tags: ["step2", "default", "termination", "remedies"]
---

# Default and Termination Analysis (Step 2.6)

Perform comprehensive analysis of default events, termination rights, remedy provisions, and enforcement mechanisms in this Australian real estate contract, focusing on risk assessment and party protection evaluation.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Default Event Identification

**Identify all potential default events:**
- Monetary defaults (payment failures, deposit shortfalls)
- Non-monetary defaults (breach of covenants, condition failures)
- Condition precedent failures
- Warranty and representation breaches
- Repudiation or anticipatory breach

**For each default event, analyze:**
- Precise definition and triggering conditions
- Notice requirements and procedural steps
- Cure periods and opportunities to remedy
- Consequences and available remedies
- Party responsible and fault allocation

**Default risk assessment:**
- Likelihood of occurrence for each default type
- Severity of consequences for each party
- Prevention measures and risk mitigation
- Ambiguities in default definitions

### 2. Termination Rights Analysis

**Identify all termination triggers:**
- Automatic termination events
- Discretionary termination rights
- Condition-based termination
- Material breach termination
- Frustration or impossibility

**For each termination right, evaluate:**
- Party who can exercise the right
- Procedural requirements (notice, cure periods)
- Conditions precedent to termination
- Effects on deposit and other obligations
- Reasonableness and enforceability

**Termination balance assessment:**
- Mutual vs unilateral termination rights
- Fairness of termination triggers
- Adequacy of notice and cure provisions
- Protection for non-defaulting party

### 3. Remedy Provisions Review

**Catalog all available remedies:**
- Specific performance rights
- Damages and compensation provisions
- Deposit forfeiture or retention
- Injunctive relief availability
- Alternative dispute resolution

**For each remedy, assess:**
- Scope and limitations of remedy
- Procedural requirements for enforcement
- Time limitations and deadlines
- Monetary caps or exclusions
- Practical enforceability

**Remedy adequacy evaluation:**
- Appropriateness of remedy to breach type
- Completeness of remedy coverage
- Balance between party interests
- Consumer protection compliance

### 4. Deposit Forfeiture Analysis

**Analyze deposit forfeiture provisions:**
- Circumstances triggering forfeiture
- Amount subject to forfeiture
- Procedural requirements for forfeiture
- Buyer protection mechanisms

**Enforceability assessment:**
- Penalty provisions analysis
- Proportionality to actual loss
- Consumer protection law compliance
- Unfair contract terms considerations

**Risk evaluation:**
- Probability of forfeiture scenarios
- Buyer strategies to avoid forfeiture
- Vendor enforcement likelihood
- Alternative outcomes assessment

### 5. Time of Essence Implications

**Identify time-critical obligations:**
- Deadlines with time of essence declarations
- Strict timing requirements
- Grace periods and extensions
- Notice periods for time-sensitive matters

**Risk assessment:**
- Consequences of timing failures
- Availability of relief for delays
- Practical compliance requirements
- Force majeure or frustration provisions

**Buyer protection evaluation:**
- Reasonableness of time requirements
- Adequacy of notice provisions
- Availability of extension mechanisms
- Risk mitigation strategies

### 6. Enforcement Mechanisms

**Analyze enforcement provisions:**
- Jurisdiction and governing law clauses
- Dispute resolution procedures
- Cost allocation for enforcement
- Security provisions and guarantees

**Practical enforcement assessment:**
- Ease of enforcement procedures
- Cost-effectiveness of remedies
- Likelihood of successful enforcement
- Barriers to remedy pursuit

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction %}
### Entity Extraction Results
Previously extracted default/termination data:
{{entities_extraction | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} default and termination requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Systematic Review**: Examine all contract sections for default, termination, and remedy provisions
2. **Legal Classification**: Categorize each provision by type and enforceability
3. **Risk Assessment**: Evaluate likelihood and consequences of each default scenario
4. **Fairness Analysis**: Assess balance of rights and remedies between parties
5. **Consumer Protection**: Apply {{australian_state}} unfair contract terms and consumer laws
6. **Practical Focus**: Emphasize actionable insights for risk management
7. **Evidence Documentation**: Reference specific contract clauses and legal precedents
8. **Enforcement Reality**: Consider practical enforceability and cost implications

## Expected Output

Provide comprehensive default and termination analysis following the DefaultTerminationAnalysisResult schema:

- Complete inventory of default events with risk and consequence assessment
- Detailed termination rights analysis with fairness and enforceability evaluation
- Comprehensive remedy provisions review with adequacy and practicality assessment
- Deposit forfeiture analysis with enforceability and risk evaluation
- Time of essence implications with compliance and risk assessment
- Overall risk classification with party vulnerability analysis
- Priority recommendations and risk mitigation strategies

**Critical Success Criteria (PRD 4.1.2.6):**
- 100% identification of all default and termination provisions
- Accurate risk assessment for each default scenario
- Complete remedy adequacy and enforceability analysis
- Clear evaluation of party vulnerability and protection levels