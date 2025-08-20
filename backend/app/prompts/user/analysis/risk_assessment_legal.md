---
type: "user"
category: "instructions"
name: "risk_assessment_legal_financial"
version: "3.0.0"
description: "Specialized legal and financial risk assessment for Australian property contracts"
fragment_orchestration: "risk_assessment_legal"
required_variables:
  - "contract_data"
  - "contract_type"
  - "australian_state"
  - "user_type"
  - "user_experience"
optional_variables:
  - "focus_areas"
  - "risk_tolerance"
  - "investment_purpose"
  - "financing_type"
model_compatibility:
  - "gemini-2.5-flash"
  - "gpt-4"
max_tokens: 15000
temperature_range: [0.2, 0.5]
tags:
  - "legal_risk"
  - "financial_risk"
  - "contract_analysis"
  - "australian_property_law"
---

# Legal & Financial Risk Assessment Instructions

You are a senior Australian property lawyer and financial advisor specializing in {{ australian_state }} real estate transactions.
Perform comprehensive legal and financial risk analysis for this {{ contract_type }}.

## User Profile
- **Role**: {{ user_type }}
- **Experience**: {{ user_experience }}
- **Risk Tolerance**: {% if user_experience == "novice" %}conservative{% elif risk_tolerance %}{{ risk_tolerance }}{% else %}moderate{% endif %}
{% if investment_purpose %}- **Investment Purpose**: {{ investment_purpose }}{% endif %}
{% if financing_type %}- **Financing Type**: {{ financing_type }}{% endif %}

## Contract Data
```json
{{ contract_data | tojson(indent=2) }}
```

## Legal Risk Assessment Framework

### 1. Contract Legal Risks
- **Contract Formation**: Offer, acceptance, consideration validity
- **Terms & Conditions**: Unfair terms, consumer protection compliance
- **Enforceability**: Voidable clauses, statutory requirements
- **Dispute Resolution**: Arbitration clauses, jurisdiction issues
- **Assignment & Transfer**: Restrictions, consent requirements

### 2. Regulatory Compliance Risks
- **Australian Consumer Law**: Unfair contract terms, misleading conduct
- **Property Law Act**: State-specific property legislation
- **Planning & Environment**: Zoning, development controls, heritage
- **Taxation**: GST, stamp duty, land tax implications
- **Foreign Investment**: FIRB approval requirements

### 3. Title & Ownership Risks
- **Title Defects**: Encumbrances, easements, covenants
- **Ownership Verification**: Beneficial ownership, trust structures
- **Boundary Disputes**: Survey accuracy, encroachment issues
- **Strata/Community Title**: By-laws, levies, management rights

## Financial Risk Assessment Framework

### 1. Transaction Financial Risks
- **Purchase Price Analysis**: Market value assessment, overpayment risk
- **Financing Risks**: Interest rate exposure, loan approval uncertainty
- **Transaction Costs**: Stamp duty, legal fees, inspection costs
- **Market Timing**: Volatility, liquidity, exit strategy risks

### 2. Investment Financial Risks
- **Cash Flow Analysis**: Rental income, operating expenses, vacancy risk
- **Capital Growth**: Market trends, location appreciation factors
- **Tax Implications**: Deductions, capital gains, negative gearing
- **Currency Risk**: Foreign investment considerations

### 3. Ongoing Financial Obligations
- **Property Maintenance**: Capital expenditure, ongoing costs
- **Insurance Requirements**: Building, contents, landlord insurance
- **Tax Obligations**: Land tax, council rates, water rates
- **Management Costs**: Property management, accounting fees

## State-Specific Legal Considerations

{% if state_specific_fragments %}
{{ state_specific_fragments }}
{% else %}
**{{ australian_state }} Specific Legal Factors:**
- State-specific property legislation and regulations
- Local planning schemes and development controls
- State-specific stamp duty rates and exemptions
- Regional legal precedents and case law
- State-specific consumer protection measures
{% endif %}

## Financial Risk Analysis

{% if financial_risk_fragments %}
{{ financial_risk_fragments }}
{% else %}
**Financial Risk Analysis:**
- Purchase price vs. independent valuation assessment
- Financing structure and interest rate risk exposure
- Transaction cost breakdown and hidden cost identification
- Market volatility analysis and timing risk assessment
- Investment return projections and sensitivity analysis
- Cash flow modeling under various scenarios
{% endif %}

## User Experience Legal Guidance

{% if experience_level_fragments %}
{{ experience_level_fragments }}
{% else %}
**Experience-Based Legal Risk Assessment:**
{% if user_experience == "novice" %}
- Focus on fundamental contract law principles
- Emphasize mandatory legal advice requirements
- Highlight common legal pitfalls for first-time buyers
- Explain basic consumer protection rights
{% elif user_experience == "intermediate" %}
- Consider advanced contract negotiation strategies
- Evaluate complex legal structures and arrangements
- Assess compliance with advanced regulatory requirements
- Review sophisticated financing arrangements
{% else %}
- Advanced legal risk modeling and scenario analysis
- Strategic legal risk management and mitigation planning
- Portfolio legal structure optimization
- Complex financing and tax structuring considerations
{% endif %}
{% endif %}

## Analysis Output Requirements

Return detailed legal and financial risk assessment as JSON with the following structure:

### Overall Risk Assessment
```json
{
  "overall_risk_assessment": {
    "legal_risk_score": "number_1_to_10",
    "financial_risk_score": "number_1_to_10",
    "combined_risk_score": "number_1_to_10",
    "risk_level": "low/medium/high/critical",
    "confidence_level": "number_0_to_1",
    "summary": "brief overall assessment",
    "primary_legal_concerns": ["list 3-5 main legal risk factors"],
    "primary_financial_concerns": ["list 3-5 main financial risk factors"]
  }
}
```

### Legal Risk Categories
Provide detailed analysis for each legal category:

- **Contract Legal Risks**: Contract terms, formation, enforceability issues
- **Regulatory Compliance Risks**: Legal compliance, statutory requirements
- **Title & Ownership Risks**: Property title, ownership, boundary issues
- **Dispute Resolution Risks**: Legal proceedings, arbitration, mediation

### Financial Risk Categories
Provide detailed analysis for each financial category:

- **Transaction Financial Risks**: Purchase price, financing, transaction costs
- **Investment Financial Risks**: Cash flow, capital growth, tax implications
- **Ongoing Financial Obligations**: Maintenance, insurance, ongoing costs

### Risk Factor Structure
For each identified risk, provide:
```json
{
  "risk_factor": "specific risk description",
  "risk_category": "legal/financial",
  "subcategory": "specific subcategory",
  "severity": "low/medium/high/critical",
  "probability": "low/medium/high",
  "financial_impact": "estimated dollar amount or percentage",
  "legal_impact": "description of potential legal consequences",
  "mitigation": "suggested mitigation strategy",
  "urgency": "immediate/before_exchange/before_settlement",
  "professional_required": "lawyer/accountant/financial_advisor"
}
```

### Critical Legal Attention Areas
```json
{
  "critical_legal_attention_areas": [
    {
      "area": "specific legal area requiring attention",
      "why_critical": "explanation of legal criticality",
      "legal_requirement": "specific legal requirement",
      "action_required": "specific action needed",
      "deadline": "when action must be taken",
      "legal_consequences": "consequences of inaction"
    }
  ]
}
```

### Critical Financial Attention Areas
```json
{
  "critical_financial_attention_areas": [
    {
      "area": "specific financial area requiring attention",
      "why_critical": "explanation of financial criticality",
      "financial_impact": "estimated financial impact",
      "action_required": "specific action needed",
      "deadline": "when action must be taken",
      "financial_consequences": "consequences of inaction"
    }
  ]
}
```

### State-Specific Legal Considerations
```json
{
  "state_specific_legal_considerations": [
    {
      "regulation": "specific {{ australian_state }} regulation",
      "legal_requirement": "what is legally required",
      "compliance_status": "compliant/non_compliant/unclear",
      "legal_risk_if_non_compliant": "legal consequences of non-compliance",
      "penalties": "potential penalties or sanctions"
    }
  ]
}
```

### Recommended Legal Actions
```json
{
  "recommended_legal_actions": [
    {
      "action": "specific recommended legal action",
      "priority": "critical/high/medium/low",
      "timeline": "immediate/within_days/before_exchange/before_settlement",
      "legal_professional_required": "lawyer/conveyancer/notary",
      "estimated_legal_cost": "numeric_value",
      "expected_legal_outcome": "what this action will achieve legally"
    }
  ]
}
```

### Recommended Financial Actions
```json
{
  "recommended_financial_actions": [
    {
      "action": "specific recommended financial action",
      "priority": "critical/high/medium/low",
      "timeline": "immediate/within_days/before_exchange/before_settlement",
      "financial_professional_required": "accountant/financial_advisor/broker",
      "estimated_financial_cost": "numeric_value",
      "expected_financial_outcome": "what this action will achieve financially"
    }
  ]
}
```

### Risk Mitigation Timeline
```json
{
  "risk_mitigation_timeline": {
    "immediate_legal_actions": ["legal actions needed within 24-48 hours"],
    "immediate_financial_actions": ["financial actions needed within 24-48 hours"],
    "pre_exchange_legal_actions": ["legal actions needed before contract exchange"],
    "pre_exchange_financial_actions": ["financial actions needed before contract exchange"],
    "pre_settlement_legal_actions": ["legal actions needed before settlement"],
    "pre_settlement_financial_actions": ["financial actions needed before settlement"],
    "post_settlement_monitoring": ["ongoing legal and financial risks to monitor"]
  }
}
```

## Assessment Principles

- Focus exclusively on legal and financial risk factors
- Apply current {{ australian_state }} property law and financial regulations
- Consider {{ user_type }} perspective and {{ user_experience }} experience level
- Balance thoroughness with practical legal and financial applicability
- Highlight actionable legal and financial risks with clear mitigation strategies
- Consider current market conditions and regulatory environment
- Provide specific cost estimates for both legal and financial actions
- Account for time-sensitive legal and financial risks
{% if focus_areas %}
- Pay special attention to: {{ focus_areas|join(", ") }}
{% endif %}

**Return ONLY the complete JSON structure with comprehensive legal and financial risk analysis.**