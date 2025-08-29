---
type: "user"
category: "instructions"
name: "adjustments_analysis"
version: "2.0.0"
description: "Step 2.9 - Adjustments and Outgoings Calculator"
fragment_orchestration: "step2_adjustments"
required_variables:
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "financial_terms_result"
  - "settlement_logistics_result"
  - "legal_requirements_matrix"
  - "contract_type"
  - "seed_snippets"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: AdjustmentsAnalysisResult
tags: ["step2", "adjustments", "outgoings", "calculations"]
---

# Adjustments and Outgoings Calculator (Step 2.9)

Perform comprehensive analysis and calculation of all settlement adjustments, outgoings apportionments, and statutory charges in this Australian real estate contract, focusing on accuracy and compliance.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Adjustment Identification and Classification

**Identify all adjustment items:**
- Council rates and charges
- Water and sewerage rates
- Land tax assessments
- Strata levies and body corporate fees
- Rent (if property is tenanted)
- Insurance premiums
- Utility accounts and connections
- Other statutory charges

**For each adjustment, determine:**
- Current payment status and amounts owing
- Assessment periods and payment cycles
- Apportionment basis and calculation method
- Supporting documentation requirements
- Verification procedures and sources

### 2. Calculation Methodology Analysis

**Standard adjustment calculations:**
- Daily pro-rata calculations for rates and charges
- Monthly apportionments for regular payments
- Quarterly adjustments for body corporate levies
- Annual adjustments for insurance and land tax

**{{australian_state}} specific requirements:**
- State-specific calculation methods
- Statutory apportionment rules
- Local council rate calculation procedures
- Water authority charging methods

**Calculation verification:**
- Cross-check calculation methods with contract terms
- Verify apportionment dates and periods
- Confirm calculation accuracy and compliance
- Identify any unusual calculation provisions

### 3. Council Rates and Statutory Charges

**Council rates analysis:**
- Current assessment values and rate amounts
- Rate payment status and arrears
- Rate notice currency and validity
- Special rates and charges

**Land tax assessment:**
- Land tax liability determination
- Apportionment calculations and methods
- Exemption status verification
- Foreign buyer surcharge implications

**Other statutory charges:**
- Emergency services levy
- Fire services property levy
- Environmental improvement charges
- Special purpose charges

### 4. Strata and Body Corporate Adjustments

**Strata levy analysis:**
- Current levy amounts and payment status
- Administrative and sinking fund levies
- Special levy assessments and projects
- Levy increase notifications

**Body corporate financial health:**
- Body corporate financial statements
- Sinking fund adequacy
- Major maintenance planning
- Insurance coverage and adequacy

**Apportionment requirements:**
- Levy apportionment calculations
- Prepaid levy adjustments
- Outstanding levy obligations
- Future levy obligations

### 5. Utility and Services Adjustments

**Utility account analysis:**
- Current account status and amounts owing
- Account transfer procedures and requirements
- Final reading arrangements
- Security deposit requirements

**Service connection analysis:**
- New connection requirements and costs
- Service upgrade obligations
- Connection timing and procedures
- Authority approval requirements

**Apportionment calculations:**
- Usage-based apportionments
- Connection fee apportionments
- Service availability charges
- Meter reading adjustments

### 6. Tenancy and Rental Adjustments

**Rental income analysis (if applicable):**
- Current tenancy status and rent amounts
- Rent collection status and arrears
- Bond and security deposit status
- Lease assignment requirements

**Tenancy adjustments:**
- Rent apportionment calculations
- Bond transfer procedures
- Property management fee adjustments
- Tenant obligation transfers

### 7. Settlement Statement Preparation

**Statement compilation requirements:**
- All adjustment items and calculations
- Supporting documentation references
- Verification procedures completed
- Party approval processes

**Accuracy safeguards:**
- Calculation cross-checks and verifications
- Independent verification requirements
- Error correction procedures
- Dispute resolution mechanisms

## Dependency Analysis

{% if financial_terms_result %}
### Financial Terms Integration
Adjustments must align with financial obligations:
{{financial_terms_result | tojsonpretty}}
{% endif %}

{% if settlement_logistics_result %}
### Settlement Logistics Integration
Adjustment preparation must coordinate with settlement logistics:
{{settlement_logistics_result | tojsonpretty}}
{% endif %}

## Contract Text for Analysis
Not required; rely on Phase 1/2 outputs and targeted retrieval.

## Additional Context

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} adjustment requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions (Seeds + Retrieval + Phase Outputs)

1. **Comprehensive Identification**: Examine all contract sections for adjustment and outgoings provisions
2. **Accurate Calculations**: Apply correct calculation methods and apportionment rules
3. **State Compliance**: Use {{australian_state}} specific calculation requirements and procedures
4. **Verification Focus**: Identify all verification and documentation requirements
5. **Risk Assessment**: Evaluate calculation accuracy and dispute risks
6. **Practical Implementation**: Focus on practical settlement statement preparation
7. **Evidence Documentation**: Reference specific contract clauses and calculation methodologies
8. **Integration Analysis**: Consider financial terms and settlement logistics coordination

## Expected Output

Provide comprehensive adjustments analysis following the AdjustmentsAnalysisResult schema:

- Complete adjustment identification with accurate calculation methodology
- Detailed outgoings analysis with apportionment requirements
- Strata levy and body corporate adjustment analysis
- Utility and services adjustment coordination
- Tax and statutory charge apportionment
- Settlement statement preparation requirements with verification procedures
- Overall risk classification with accuracy and dispute assessment
- Practical recommendations for adjustment preparation and verification

**Critical Success Criteria (PRD 4.1.2.9):**
- 100% identification of all adjustment items and outgoings
- Accurate calculation methodology for each adjustment type
- Complete verification and documentation requirements
- Clear assessment of calculation risks and dispute potential