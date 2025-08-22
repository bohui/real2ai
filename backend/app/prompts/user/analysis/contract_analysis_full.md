---
type: "user"
category: "instructions"
name: "contract_analysis_full"
version: "2.0.0"
description: "Full contract analysis template that works with fragments"
fragment_orchestration: "contract_analysis"
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_type"
optional_variables:
  - "condition"
  - "user_experience_level"
  - "specific_concerns"
  - "contract_type"
  - "transaction_value"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.4]
output_parser: ContractAnalysisOutput
tags: ["contract", "analysis", "fragment-based", "modular"]
---

# Contract Analysis Instructions

Perform a comprehensive analysis of the provided Australian real estate contract using the following structured approach.

## Analysis Framework

### 1. Document Identification and Classification

**Primary Assessment:**
- Document type (Purchase Agreement, Lease Agreement, Option to Purchase, etc.)
- Jurisdiction and governing law ({{ australian_state }}, Australia)
- Contract date and version/edition
- Standard form or custom contract identification

**Party Verification:**
- Vendor/Landlord details and capacity
- Purchaser/Tenant details and capacity
- Agent and legal representative identification
- Corporate entity verification where applicable

### 2. Essential Terms Analysis

**Property Details:**
- Legal description and title information
- Physical address and property identification
- Zoning and land use classification
- Any strata or community title details

**Financial Terms:**
- Purchase price or rental amount: {% if transaction_value %}{{ transaction_value | currency }}{% else %}[Extract from contract]{% endif %}
- Deposit amount, timing, and holding arrangements
- Balance payment terms and settlement arrangements
- Any additional costs, fees, or outgoings

### 3. Conditions and Contingencies

**Standard Conditions:**
- Finance approval requirements and deadlines
- Building and pest inspection provisions
- Legal and planning searches and approvals
- Insurance requirements and responsibilities

**Special Conditions:**
- Customized terms specific to this transaction
- Variations to standard contract provisions
- Additional warranties or representations
- Sunset clauses and time-sensitive provisions

## State-Specific Legal Requirements

{{ state_requirements }}

## Consumer Protection Framework

{{ consumer_protection }}

## Contract Type Specific Analysis

{{ contract_types }}

## Experience Level Guidance

{{ user_experience }}

## Analysis Depth and Focus

{{ analysis_depth }}


### 4. Risk Assessment Framework

**Risk Evaluation Process:**
1. **Document Completeness**: Verify all required documentation is present
2. **Term Analysis**: Assess fairness and enforceability of key terms
3. **Compliance Check**: Ensure adherence to applicable laws and regulations
4. **Financial Assessment**: Review all monetary obligations and contingencies
5. **Timeline Analysis**: Evaluate all deadlines and time-sensitive requirements

**Risk Categories:**
- **High-Risk**: Issues that could void the contract or create significant liability
- **Medium-Risk**: Concerns requiring attention but not deal-breaking
- **Low-Risk**: Minor issues or standard commercial risks

### 5. Financial Analysis

**Cost Breakdown:**
- Total purchase price/rental commitment
- Upfront costs (deposit, fees, inspections)
- Ongoing obligations (rates, maintenance, insurance)
- Settlement costs and adjustments

**Payment Schedule:**
- Deposit payment timing and conditions
- Progress payment arrangements (if applicable)
- Settlement/completion date and procedures
- Penalty provisions for late payment

### 6. Legal Rights and Obligations

**Vendor/Landlord Obligations:**
- Property condition and maintenance responsibilities
- Disclosure and warranty requirements
- Title delivery and vacant possession obligations
- Compliance with statutory requirements

**Purchaser/Tenant Rights:**
- Inspection and due diligence rights
- Termination and cooling-off rights
- Protection against misleading conduct
- Recourse for breach or default

## Quality Assurance Standards

**Analysis Standards:**
- Support all conclusions with specific contract references
- Quantify risks and provide likelihood assessments where possible
- Include practical recommendations and next steps
- Maintain professional tone while ensuring accessibility
- Provide clear priority ranking for identified issues

**Validation Requirements:**
- Cross-reference all financial figures and dates
- Verify consistency across contract provisions
- Check compliance with state-specific requirements
- Ensure all critical terms have been addressed

Maintain clarity and accessibility while providing comprehensive legal analysis appropriate for the user's experience level.

## Input context:
- australian_state: {{ state }}
- analysis_type: {{ analysis_type or "comprehensive" }}

## Text to process:
```
{{ contract_text }}
```