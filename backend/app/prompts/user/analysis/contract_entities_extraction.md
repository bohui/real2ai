---
type: "user"
category: "instructions"
name: "contract_analysis_base"
version: "2.0.0"
description: "Base contract analysis template that works with fragments"
fragment_orchestration: "contract_analysis"
required_variables:
  - "contract_text"
optional_variables: []
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.4]
output_parser: ContractEntityExtraction
tags: ["contract", "analysis", "fragment-based", "modular"]
---

# Contract Analysis Instructions

Perform a comprehensive analysis of the provided Australian real estate contract using the following structured approach.

## Metadata Extraction

Extract and classify the following metadata fields, recording specific evidence for each decision.

### Contract State (metadata.state)
- Indicators:
  - State named in addresses, title documents, planning certificates, legislation references
  - Abbreviations (NSW, VIC, QLD, SA, WA, TAS, ACT, NT)
- Rules:
  - Prefer explicit contract references; if ambiguous and not supported by the document, leave null
- Evidence to capture:
  - Exact text excerpt naming the state or jurisdiction

### Contract Type (metadata.contract_type)
- Indicators:
  - Phrases such as Contract for Sale, Lease Agreement, Licence, Option Deed, Assignment, Deed of Variation
  - Header/title pages, execution blocks, or standard form identifiers
- Rules:
  - Choose the best supported type; if mixed, select primary instrument and lower confidence
- Evidence to capture:
  - Title/header or clause excerpts naming the instrument

### Purchase Method (metadata.purchase_method)
- Indicators:
  - Auction terms (reserve price, bidding, auction date), private treaty, tender, expression of interest
- Rules:
  - If unstated, set null; do not infer from context alone
- Evidence to capture:
  - Clauses or schedules specifying sale method

### Use Category (metadata.use_category)
- Indicators:
  - Residential, commercial, industrial, rural/agricultural descriptors
  - Zoning labels and planning certificate classifications
- Rules:
  - Use explicit statements over assumptions (e.g., tenancy alone does not imply commercial)
- Evidence to capture:
  - Zoning/planning or descriptive excerpts

### Property Condition (metadata.property_condition)
- Indicators:
  - References to new construction, off-the-plan, occupation certificates, builder warranties
  - Recent building work within 6–7 years, renovation disclosures
  - Absence of construction references for standard existing property
- Rules:
  - Classify into: new/off-the-plan, existing with recent building work, standard existing
- Evidence to capture:
  - Clauses noting construction status, certificates, or work history

### Transaction Complexity (metadata.transaction_complexity)
- Indicators:
  - Strata/community title, multiple lots, easements/encumbrances, commercial parties, rural uses
  - Extensive special conditions or bespoke terms
- Rules:
  - Rate complexity considering structural features and bespoke provisions
- Evidence to capture:
  - Clauses showing strata, multi-lot arrangements, or complex special conditions

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

**Source Documentation Requirements:**
- For each classification decision (contract_type, purchase_method, use_category, property_condition, transaction_complexity), provide the specific text excerpt from the contract that supports your conclusion
- Include relevant contract clauses, descriptions, or statements that justify each classification
- Use the `sources` field to map each decision to its supporting evidence
- Ensure all conclusions are traceable back to specific contract language

Maintain clarity and accessibility while providing comprehensive legal analysis appropriate for the user's experience level.

## Text to process:
```
{{ contract_text }}
```