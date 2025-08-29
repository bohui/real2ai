---
type: "user"
category: "instructions"
name: "disclosure_analysis"
version: "2.0.0"
description: "Step 2.10 - Disclosure Compliance Check"
fragment_orchestration: "step2_disclosure"
required_variables:
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "legal_requirements_matrix"
  - "contract_type"
  - "seed_snippets"
  - "settlement_logistics_result"
  - "title_encumbrances_result"
  - "warranties_result"
  - "default_termination_result"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: DisclosureAnalysisResult
tags: ["step2", "disclosure", "compliance", "regulations"]
---

# Disclosure Compliance Check (Step 2.10)

Perform comprehensive analysis of mandatory disclosure compliance, vendor statement adequacy, and regulatory requirement verification in this Australian real estate contract, focusing on legal compliance and buyer protection.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. {{australian_state}} Mandatory Disclosure Requirements

**State-specific vendor statement requirements:**
- Section 32 Vendor Statement (Victoria)
- Section 66W Certificate (NSW)
- Form 1 Disclosure Statement (Queensland)
- Vendor Disclosure Statement (South Australia)
- {{australian_state}} equivalent disclosure documents

**Legislative compliance verification:**
- Sale of Land Act requirements
- Property Law Act disclosures
- Consumer protection law obligations
- Local government disclosure requirements

**Completeness assessment:**
- All required sections present
- Information currency and accuracy
- Professional preparation standards
- Statutory declaration adequacy

### 2. Building Safety and Compliance Disclosures

**Building approval disclosures:**
- Building permits and approvals
- Occupancy permits and certificates
- Compliance with building codes
- Outstanding building orders or notices

**Safety compliance verification:**
- Fire safety compliance
- Pool safety compliance (if applicable)
- Asbestos disclosure requirements
- Lead paint disclosure (pre-1970 buildings)

**Structural and engineering disclosures:**
- Structural defects or issues
- Engineering reports and assessments
- Subsidence or movement issues
- Foundation or structural concerns

### 3. Environmental and Contamination Disclosures

**Contamination disclosure requirements:**
- Soil contamination history
- Industrial use history
- Hazardous materials presence
- Environmental site assessments

**Environmental impact disclosures:**
- Flooding risk and history
- Environmental protection zones
- Vegetation protection orders
- Wildlife corridor restrictions

**Regulatory environmental requirements:**
- EPA notifications or orders
- Environmental management plans
- Contaminated land register listings
- Groundwater protection requirements

### 4. Planning and Development Disclosures

**Planning approval disclosures:**
- Current planning permits
- Development approvals and conditions
- Planning scheme amendments
- Heritage listing or protection

**Development restriction disclosures:**
- Zoning restrictions and overlays
- Building height and setback limits
- Parking and access requirements
- Affordable housing contributions

**Future development impacts:**
- Planned infrastructure projects
- Rezoning proposals or studies
- Compulsory acquisition risks
- Major development approvals nearby

### 5. Infrastructure and Services Disclosures

**Infrastructure condition disclosures:**
- Road and footpath conditions
- Drainage and flooding issues
- Public transport accessibility
- Utility service adequacy

**Service availability disclosures:**
- Internet and telecommunications
- Gas and electricity supply
- Water and sewer services
- Waste collection services

**Infrastructure levy disclosures:**
- Development contribution plans
- Infrastructure charges and levies
- Special rate schemes
- Betterment levies

### 6. Strata and Community Disclosures

**Strata scheme disclosures (if applicable):**
- Body corporate financial position
- Special levy assessments
- Major maintenance planning
- Insurance adequacy and claims

**Community obligations:**
- Homeowner association requirements
- Community facility obligations
- Maintenance responsibilities
- Architectural controls and covenants

### 7. Tenancy and Rental Disclosures

**Tenancy disclosures (if applicable):**
- Current tenancy agreements
- Rent amounts and review mechanisms
- Tenant rights and obligations
- Bond and security arrangements

**Property management disclosures:**
- Property management agreements
- Commission and fee structures
- Maintenance responsibilities
- Tenant dispute history

### 8. Compliance Gap Analysis

**Identify compliance gaps:**
- Missing mandatory disclosures
- Inadequate disclosure content
- Out-of-date information
- Unclear or ambiguous disclosures

**Risk assessment of gaps:**
- Legal consequences for vendor
- Buyer protection implications
- Transaction completion risks
- Potential remedy availability

**Remediation requirements:**
- Steps to achieve full compliance
- Timeline for compliance completion
- Professional assistance needed
- Cost implications of compliance

## Contract Text for Analysis
Not required; rely on Phase 1/2 outputs and targeted retrieval.

## Additional Context

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} disclosure requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Comprehensive Compliance Check**: Verify all {{australian_state}} mandatory disclosure requirements
2. **Gap Analysis**: Identify all missing or inadequate disclosures
3. **Risk Assessment**: Evaluate compliance risks and buyer protection implications
4. **Legal Accuracy**: Apply current {{australian_state}} disclosure legislation and regulations
5. **Professional Standards**: Assess compliance with professional preparation standards
6. **Buyer Protection Focus**: Emphasize buyer protection and informed decision-making
7. **Evidence Documentation**: Reference specific legal requirements and disclosure documents
8. **Practical Remediation**: Provide actionable steps for achieving compliance

## Expected Output

Provide comprehensive disclosure compliance analysis following the DisclosureAnalysisResult schema:

- Complete mandatory disclosure requirement verification with compliance assessment
- Detailed vendor statement analysis with adequacy and gap evaluation
- Environmental and contamination disclosure review with risk assessment
- Planning and development disclosure analysis with restriction evaluation
- Building safety and compliance disclosure check with verification requirements
- Infrastructure and services disclosure review with adequacy assessment
- Overall compliance classification with remediation requirements
- Priority recommendations for achieving full disclosure compliance

**Critical Success Criteria (PRD 4.1.2.10):**
- 100% verification of {{australian_state}} mandatory disclosure requirements
- Accurate compliance status assessment for each requirement
- Complete gap analysis with remediation roadmap
- Clear evaluation of buyer protection adequacy