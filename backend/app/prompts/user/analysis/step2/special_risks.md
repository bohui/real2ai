---
type: "user"
category: "instructions"
name: "special_risks_analysis"
version: "1.0.0"
description: "Step 2.11 - Special Risks Identification"
fragment_orchestration: "step2_special_risks"
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "entities_extraction_result"
  - "all_section_results"
  - "legal_requirements_matrix"
  - "contract_type"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: SpecialRisksAnalysisResult
tags: ["step2", "special-risks", "unusual-terms", "synthesis"]
---

# Special Risks Identification (Step 2.11)

Perform comprehensive identification and analysis of special risks, unusual contract terms, and buyer protection gaps in this Australian real estate contract, focusing on non-standard provisions and hidden risks.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Unusual Contract Terms Identification

**Identify non-standard provisions:**
- Pricing structures deviating from market norms
- Unusual timing or deadline requirements
- Non-standard condition formulations
- Atypical warranty or liability provisions
- Unusual procedural requirements

**For each unusual term, assess:**
- Degree of deviation from standard practice
- Commercial rationale or justification
- Party advantage/disadvantage created
- Enforceability under Australian law
- Consumer protection law implications

**Market comparison analysis:**
- Comparison to standard {{australian_state}} contract forms
- Industry practice benchmarking
- Legal precedent for similar terms
- Professional body guidance compliance

### 2. Hidden and Latent Risk Detection

**Property-specific risks:**
- Structural or engineering concerns not explicitly disclosed
- Environmental risks beyond standard disclosures
- Heritage or cultural significance implications
- Access and easement complications

**Legal and regulatory risks:**
- Pending legislative changes affecting property
- Zoning or planning changes in pipeline
- Infrastructure projects impacting property
- Regulatory compliance gaps

**Financial risks beyond standard analysis:**
- Hidden cost implications
- Tax treatment uncertainties
- Financing complications
- Market volatility exposure

### 3. Buyer Protection Gap Analysis

**Identify protection inadequacies:**
- Areas with insufficient buyer recourse
- Warranty limitations affecting protection
- Condition formulations favoring vendor
- Remedial provision inadequacies

**Consumer protection compliance:**
- Unfair contract terms provisions
- Consumer guarantee preservation
- Cooling-off period adequacy
- Disclosure obligation compliance

**Professional duty considerations:**
- Solicitor duty of care implications
- Professional indemnity coverage
- Client best interest obligations
- Risk disclosure requirements

### 4. Cross-Sectional Risk Integration

**Analyze risk interactions:**
- Cumulative effect of multiple risks
- Risk amplification or mitigation interactions
- Timeline coordination risks
- Resource allocation conflicts

**System risk assessment:**
- Overall contract risk profile
- Risk concentration areas
- Diversification opportunities
- Risk correlation analysis

### 5. Market and Economic Risk Assessment

**Market condition risks:**
- Property market volatility exposure
- Interest rate sensitivity
- Economic downturn implications
- Liquidity and resale considerations

**Timing and market risks:**
- Settlement timing market exposure
- Price protection inadequacies
- Market condition change implications
- Economic cycle positioning

### 6. Operational and Practical Risks

**Implementation risks:**
- Practical difficulty in meeting obligations
- Resource requirement uncertainties
- Coordination complexity risks
- Performance delivery challenges

**Post-settlement risks:**
- Ongoing obligation complexity
- Maintenance and management challenges
- Neighbor relationship risks
- Community integration issues

### 7. Regulatory and Compliance Risks

**Current regulatory risks:**
- Compliance with existing regulations
- Regulatory interpretation uncertainties
- Enforcement action risks
- Penalty and sanction exposure

**Future regulatory risks:**
- Pending regulatory changes
- Industry regulation evolution
- Government policy changes
- Compliance cost escalation

## Cross-Section Analysis Integration

{% if all_section_results %}
### Previous Section Analysis Results
Integration with all previous section analyses:
{{all_section_results | tojsonpretty}}

**Integration Requirements:**
- Identify risks emerging from section interaction
- Assess cumulative risk effects
- Evaluate risk mitigation strategies across sections
- Prioritize risks based on overall contract impact
{% endif %}

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction_result %}
### Entity Extraction Results
Previously extracted risk-related data:
{{entities_extraction_result | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} risk assessment requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Comprehensive Risk Scanning**: Examine entire contract for hidden, unusual, or special risks
2. **Cross-Section Integration**: Consider cumulative risks from all previous section analyses
3. **Market Context**: Apply {{australian_state}} market norms and professional standards
4. **Legal Analysis**: Assess unusual terms against consumer protection and unfair contract provisions
5. **Practical Focus**: Emphasize actionable risk management and mitigation strategies
6. **Professional Standards**: Apply solicitor duty of care and professional responsibility standards
7. **Evidence Documentation**: Reference specific contract provisions and risk indicators
8. **Strategic Thinking**: Provide strategic guidance for risk acceptance, mitigation, or avoidance

## Expected Output

Provide comprehensive special risks analysis following the SpecialRisksAnalysisResult schema:

- Complete special risk identification with probability and impact assessment
- Unusual contract terms analysis with market comparison and enforceability evaluation
- Hidden and latent risk detection with mitigation strategy development
- Buyer protection gap analysis with remediation recommendations
- Cross-sectional risk integration with cumulative effect assessment
- Market and regulatory risk evaluation with strategic guidance
- Risk prioritization with decision framework and professional advice requirements
- Comprehensive risk management roadmap with monitoring and mitigation strategies

**Critical Success Criteria (PRD 4.1.2.11):**
- 100% identification of special and unusual risks
- Accurate assessment of unusual terms and their implications
- Complete buyer protection gap analysis
- Clear prioritization and mitigation strategy development