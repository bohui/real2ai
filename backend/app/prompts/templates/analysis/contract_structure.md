---
type: "user"
name: "contract_structure_analysis"
version: "1.0.0"
description: "Analyze and extract structured information from Australian real estate contracts"
required_variables:
  - "extracted_text"
  - "australian_state"
  - "contract_type"
  - "user_type"
  - "user_experience_level"
optional_variables:
  - "complexity"
  - "analysis_depth"
  - "focus_areas"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 15000
temperature_range: [0.1, 0.3]
tags: ["analysis", "contract", "structure", "australian", "legal"]
---

# Contract Structure Analysis - {{ australian_state }} {{ contract_type }}

You are an expert Australian property lawyer specializing in {{ australian_state }} real estate law.
Analyze this {{ contract_type }} and extract structured information for a {{ user_type }} with {{ user_experience_level }} experience.

## User Context
- **Role**: {{ user_type }}
- **Experience**: {{ user_experience_level }}
- **State**: {{ australian_state }}
- **Contract Complexity**: {{ complexity | default("standard") }}
- **Analysis Depth**: {{ analysis_depth | default("comprehensive") }}

## Contract Text
```
{{ extracted_text}}
```

## Extraction Schema

Extract the following information as structured JSON:

```jsonc
{
  "document_metadata": {
    "contract_type": "{{ contract_type }}",
    "state_jurisdiction": "{{ australian_state }}",
    "document_date": "date if identifiable or null",
    "page_count": "estimated pages",
    "document_quality": "assess text clarity: excellent/good/fair/poor",
    "extraction_confidence": "confidence level 0.0-1.0"
  },
  "parties": {
    "vendor": {
      "name": "full legal name or entity name",
      "address": "registered address if provided",
      "solicitor": {
        "name": "solicitor/law firm name",
        "address": "solicitor address",
        "contact": "phone/email if provided"
      },
      "abn_acn": "ABN or ACN if business entity",
      "entity_type": "individual/company/trust/other"
    },
    "purchaser": {
      "name": "full legal name(s)",
      "address": "address if provided",
      "solicitor": {
        "name": "solicitor/law firm name",
        "address": "solicitor address", 
        "contact": "phone/email if provided"
      },
      "capacity": "individual/joint_tenants/tenants_in_common/company"
    }
  },
  "property_details": {
    "address": "complete property address including postcode",
    "legal_description": "lot/plan details or title reference",
    "property_type": "house/unit/townhouse/land/commercial/industrial",
    "land_size": "area in square meters if mentioned",
    "building_area": "floor area if mentioned", 
    "zoning": "zoning classification if mentioned",
    "title_details": {
      "title_reference": "certificate of title number",
      "registered_proprietor": "current owner on title",
      "encumbrances": ["list any registered encumbrances"],
      "easements": ["list any easements mentioned"]
    },
    "strata_details": {
      "applicable": true/false,
      "strata_plan": "strata plan number if applicable",
      "unit_entitlement": "unit entitlement if strata",
      "body_corporate_name": "body corporate entity name",
      "management_rights": "details if mentioned"
    }
  },
  "financial_terms": {
    "purchase_price": "numeric value only (remove $ and commas)",
    "deposit": {
      "amount": "numeric value only",
      "percentage": "calculated percentage of purchase price",
      "due_date": "when deposit is payable",
      "method": "cash/bank_cheque/bank_guarantee/other",
      "holder": "who holds the deposit (agent/solicitor/trust account)"
    },
    "balance": "calculated balance amount (purchase_price - deposit)",
    "gst": {
      "applicable": true/false,
      "amount": "GST amount if applicable",
      "vendor_registered": "whether vendor is GST registered"
    },
    "adjustments": {
      "rates": "council rates adjustment details",
      "water": "water rates adjustment details", 
      "rent": "rental adjustment details if applicable",
      "other": ["other adjustments mentioned"]
    }
  },
  "settlement_terms": {
    "settlement_date": "specific settlement date if fixed",
    "settlement_period": "number of days from exchange to settlement",
    "place_of_settlement": "settlement location if specified",
    "time_of_settlement": "settlement time if specified",
    "settlement_agent": "who conducts settlement"
  },
  "conditions_and_warranties": {
    "cooling_off_period": {
      "applicable": true/false,
      "duration": "number of business days",
      "exclusions": ["circumstances where cooling-off doesn't apply"],
      "waiver": "whether waiver has been signed"
    },
    "finance_clause": {
      "applicable": true/false,
      "loan_amount": "maximum loan amount if specified",
      "approval_period": "days for finance approval",
      "lender": "preferred lender if specified",
      "interest_rate": "maximum interest rate if specified",
      "loan_type": "home loan/investment loan/commercial"
    },
    "building_inspection": {
      "required": true/false,
      "period": "inspection period in days",
      "type": "building_only/building_and_pest/structural",
      "cost_responsibility": "who pays for inspection"
    },
    "pest_inspection": {
      "required": true/false,
      "period": "inspection period in days",
      "scope": "pest only/pest_and_building",
      "cost_responsibility": "who pays for inspection"
    },
    "strata_inspection": {
      "required": true/false,
      "documents_required": ["list required strata documents"],
      "period": "review period in days"
    }
  },
  "special_conditions": {
    "conditions_list": ["extract all numbered special conditions"],
    "vendor_warranties": ["list all vendor warranties and representations"],
    "purchaser_obligations": ["list specific purchaser obligations"],
    "non_standard_clauses": ["identify any unusual or non-standard terms"]
  },
  "legal_and_compliance": {
    "governing_law": "{{ australian_state }}",
    "consumer_protection": {
      "fair_trading_act": "applicable provisions mentioned",
      "consumer_guarantees": "whether consumer guarantees apply",
      "disclosure_requirements": ["required disclosures mentioned"]
    },
    "foreign_investment": {
      "firb_approval": "whether FIRB approval required/obtained",
      "foreign_buyer_duty": "applicable foreign buyer duties"
    },
    "stamp_duty": {
      "purchaser_responsibility": true/false,
      "concessions_mentioned": ["any stamp duty concessions referenced"],
      "calculation_basis": "how stamp duty is calculated"
    }
  }
}
```

{% if australian_state == "NSW" %}
## NSW Specific Requirements

### Additional NSW Information to Extract:
- **Section 149 Certificate**: Planning certificate details and expiry
- **Home Building Act**: Warranty insurance details and coverage
- **Conveyancing Act**: Compliance with NSW conveyancing requirements
- **Vendor Disclosure**: Required property disclosures under NSW law
- **Consumer Guarantees**: Australian Consumer Law protections

### NSW Legal Context:
- Standard cooling-off period: 5 business days (unless waived)
- Vendor must provide all required disclosures before exchange
- Building insurance and warranty requirements for residential properties
- Specific consumer protection provisions under Fair Trading Act

{% elif australian_state == "VIC" %}
## VIC Specific Requirements

### Additional VIC Information to Extract:
- **Section 32 Statement**: Vendor statement details and compliance
- **Owners Corporation**: Owners corporation details for strata properties
- **Planning Permits**: Building and planning permit information
- **Sale of Land Act**: Compliance requirements and consumer rights
- **Building Permits**: Current building permit status and compliance

### VIC Legal Context:
- Standard cooling-off period: 3 business days (except auctions)
- Section 32 statement must be provided before signing
- Specific disclosure requirements for strata properties
- Consumer protection under Australian Consumer Law

{% elif australian_state == "QLD" %}
## QLD Specific Requirements

### Additional QLD Information to Extract:
- **Form 1**: Property disclosure statement details
- **Body Corporate**: Body corporate information and levies
- **QBCC Licensing**: Building work licensing requirements
- **Community Titles**: Community titles scheme information
- **Disclosure Requirements**: Required property disclosures

### QLD Legal Context:
- Standard cooling-off period: 5 business days (unless waived)
- Form 1 disclosure required for residential properties
- QBCC licensing requirements for building work
- Specific body corporate disclosure requirements

{% endif %}

## Analysis Guidelines

### Data Extraction Principles:
1. **Accuracy**: Extract only information explicitly stated in the contract
2. **Completeness**: Include all relevant financial and legal details
3. **Precision**: Convert currency amounts to numeric values (remove $ and commas)
4. **Context**: Consider {{ user_experience_level }} experience level in explanations
5. **State Law**: Apply {{ australian_state }}-specific legal requirements

### Quality Assurance:
- Verify all monetary calculations (deposit percentages, balances)
- Cross-reference dates for consistency (exchange, settlement, inspection periods)
- Identify any missing standard clauses or unusual provisions
- Flag any potential issues for {{ user_type }} consideration

### Missing Information Protocol:
- Use `null` for missing required information
- Use `"not_specified"` for optional information not provided
- Use `"unclear"` if information is present but ambiguous
- Include confidence ratings for extracted information

{% if user_experience_level == "novice" %}
### Novice User Considerations:
- Highlight critical dates and deadlines
- Identify standard vs. non-standard clauses
- Flag any terms that require professional advice
- Explain significance of key financial terms
{% elif user_experience_level == "intermediate" %}
### Intermediate User Focus:
- Emphasize risk factors and contingencies
- Compare terms against standard market practice
- Identify negotiation opportunities
- Highlight compliance requirements
{% elif user_experience_level == "expert" %}
### Expert User Analysis:
- Focus on legal nuances and edge cases
- Identify sophisticated structuring elements
- Analyze risk allocation between parties
- Note strategic commercial considerations
{% endif %}

## Output Requirements

Return ONLY the JSON structure with all extracted information. Do not include:
- Commentary or explanations outside the JSON
- Legal advice or recommendations
- Assumptions about missing information
- Formatting or markdown outside the JSON structure

Ensure all numeric values are properly formatted as numbers (not strings) and all dates follow ISO format where possible (YYYY-MM-DD).