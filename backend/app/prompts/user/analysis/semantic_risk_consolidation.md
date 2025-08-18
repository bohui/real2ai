---
type: "user"
category: "analysis"
name: "semantic_risk_consolidation"
version: "1.0.0"
description: "Consolidate risks across multiple semantic analyses of property diagrams"
required_variables:
  - "semantic_analyses"
  - "contract_context"
  - "australian_state"
optional_variables:
  - "property_address"
  - "total_diagrams"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 15000
temperature_range: [0.1, 0.3]
tags: ["semantic", "risk", "consolidation", "multi-diagram"]
---

# Semantic Risk Consolidation Instructions

Consolidate and prioritize risks identified across multiple property diagrams to provide comprehensive property risk assessment.

## Consolidation Context

- **Australian State**: {{ australian_state }}
- **Contract Type**: {{ contract_context.contract_type }}
- **User Profile**: {{ contract_context.user_type }} ({{ contract_context.user_experience_level }})
- **Total Diagrams**: {{ total_diagrams | default(semantic_analyses | length) }}
- **Property Address**: {{ property_address | default("Not specified") }}
- **Analysis Date**: {{ contract_context.analysis_timestamp }}

## Individual Diagram Analyses Summary

{% for analysis in semantic_analyses %}
### Diagram {{ loop.index }}: {{ analysis.filename | default("Unknown") }}
- **Image Type**: {{ analysis.semantic_analysis.image_type | default("Unknown") }}
- **Infrastructure Elements**: {{ analysis.semantic_analysis.infrastructure_elements | length | default(0) }}
- **Environmental Elements**: {{ analysis.semantic_analysis.environmental_elements | length | default(0) }}
- **Risk Indicators**: {{ analysis.semantic_analysis.risk_indicators | length | default(0) }}
- **Key Findings**: {{ analysis.semantic_analysis.key_findings | join("; ") | default("None specified") }}
- **Areas of Concern**: {{ analysis.semantic_analysis.areas_of_concern | join("; ") | default("None specified") }}

{% endfor %}

## Risk Consolidation Framework

### 1. Risk Deduplication and Prioritization
- Identify unique risks across all diagrams
- Consolidate similar risks from multiple sources
- Escalate risk severity when supported by multiple diagrams
- Create comprehensive evidence base for each consolidated risk

### 2. Risk Interdependency Analysis
- Identify risks that compound or interact with each other
- Assess cumulative impact of multiple related risks
- Evaluate systemic risks affecting entire property
- Consider sequential risk dependencies and triggers

### 3. Professional Consultation Matrix

**Immediate Consultation Required:**
- **Structural Engineer**: Foundation design conflicts, infrastructure impacts
- **Environmental Consultant**: Multiple environmental hazards, cumulative impacts
- **Licensed Surveyor**: Boundary disputes, easement conflicts, access issues
- **Property Lawyer**: High-risk legal implications, multiple compliance failures

**Recommended Professional Reviews:**
- **Geotechnical Engineer**: Soil conditions, drainage, slope stability
- **Planning Consultant**: Development approval pathways, zoning compliance
- **Insurance Specialist**: Coverage implications, risk mitigation requirements
- **Building Consultant**: Construction feasibility, design constraint analysis

### 4. State-Specific Compliance Framework

#### {{ australian_state.upper() }} Requirements
{{ state_compliance_fragments }}

## Consolidation Output Structure

### Executive Risk Summary
- **Overall Risk Level**: [Critical/High/Medium/Low]
- **Total Unique Risks Identified**: [Number]
- **Risk Distribution**: Critical: X, High: Y, Medium: Z, Low: W
- **Compounding Risk Factors**: [List of risk interactions]
- **Proceed Recommendation**: [Proceed/Proceed with Caution/Do Not Proceed/Seek Professional Advice]

### Consolidated Risk Register

For each unique risk, provide:

```jsonc
{
  "risk_category": "infrastructure|environmental|boundary|development|compliance",
  "risk_description": "Specific consolidated risk description",
  "severity": "critical|high|medium|low",
  "confidence_level": 0.0-1.0,
  "affected_diagrams": ["list of source diagrams"],
  "consolidated_evidence": "Evidence from multiple diagrams",
  "professional_consultation": "Required professional expertise",
  "timeline_requirement": "immediate|before_exchange|before_settlement|ongoing",
  "estimated_cost_range": "Cost estimate for resolution/investigation",
  "consequence_of_inaction": "What happens if risk is not addressed"
}
```

### Prioritized Action Plan

#### Phase 1: Immediate Actions (Before Contract Exchange)
- [List critical actions that must be completed immediately]
- [Include professional consultations with urgent timelines]
- [Specify evidence gathering and verification requirements]

#### Phase 2: Pre-Settlement Investigations
- [List investigations and reports needed before settlement]
- [Include professional assessments and approvals required]
- [Specify contingency planning for identified risks]

#### Phase 3: Long-term Property Management
- [List ongoing obligations and maintenance requirements]
- [Include insurance and compliance monitoring needs]
- [Specify future development consideration factors]

### Financial Impact Assessment

**Immediate Costs:**
- Professional consultation fees: $[Range]
- Investigation and report costs: $[Range]
- Emergency remediation (if required): $[Range]

**Potential Future Costs:**
- Development constraint impacts: $[Range]
- Insurance premium adjustments: $[Range]
- Ongoing compliance costs: $[Range]

**Risk Mitigation Investment:**
- Preventive measures: $[Range]
- Professional indemnity considerations: $[Range]
- Property value protection: $[Range]

### Final Recommendation Matrix

Based on consolidated analysis:

**Risk Tolerance Assessment:**
- **Conservative** (Novice users): Recommend comprehensive professional review
- **Moderate** (Intermediate users): Focus on high and critical risks only
- **Aggressive** (Expert users): Accept medium risks with appropriate contingencies

**Decision Framework:**
- **Proceed**: Low overall risk, manageable issues, clear resolution paths
- **Proceed with Caution**: Medium risk, professional consultation required
- **Do Not Proceed**: High/critical unresolvable risks, safety concerns
- **Seek Professional Advice**: Complex risk profile requiring expert assessment

## Quality Assurance Requirements

- Cross-reference all risk assessments against source diagrams
- Verify professional consultation recommendations align with identified risks
- Ensure cost estimates reflect current {{ australian_state }} market rates
- Confirm timeline recommendations allow adequate due diligence
- Validate risk prioritization matches user experience level and risk tolerance

Provide comprehensive, actionable guidance that protects the {{ contract_context.user_type }}'s interests in this {{ australian_state }} property transaction while maintaining appropriate risk management standards.

