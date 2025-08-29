---
type: "user"
category: "instructions"
name: "contract_entities_extraction"
version: "3.0.0"
description: "Entity extraction for Step 2 analysis (entities only, no section seeds)"
fragment_orchestration: "contract_analysis"
required_variables:
  - "contract_text"
optional_variables: []
# model_compatibility: ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free", "google/gemini-2.5-flash"]
model_compatibility: ["gemini-2.5-flash"]
max_tokens: 8000
temperature_range: [0.1, 0.4]
output_parser: ContractEntityExtraction
tags: ["contract", "extraction", "entities", "modular"]
---

# Step 1: Entity Extraction Instructions (Extraction-Only)

Extract structured entities from the provided Australian real estate contract. Do not extract section seeds here. Do not perform risk assessment, adequacy judgments, timeline mapping, or recommendations. Populate the `ContractEntityExtraction` schema only.

## EXTRACTION FOCUS

- Extract entities only - no section seeds, risk assessment, adequacy judgments, timeline mapping, or recommendations
- **Payment Terms**: If a due time is expressed as an event (e.g., "on completion", "on settlement") set `payment_due_event` to that keyword and leave `payment_due_date` null. Only populate `payment_due_date` with a real calendar date.

## 1) Metadata Extraction

Extract and classify the following metadata fields. For each, provide exact evidence in `metadata.sources` where applicable.

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

## 2) Core Entities to Extract

### Property Address (`property_address`)
- **Extract**: Full address; lot/plan/title; `property_type` if present
- **Indicators**: "Lot", "Plan/DP/SP", "Title Reference/CT", 4-digit postcodes, state abbreviations (NSW, VIC, QLD, SA, WA, TAS, ACT, NT), street patterns (number + street type)
- **Guidance**: Prefer `full_address`; include lot/plan/title when present; set `property_type` if named

### Parties (`parties`)
- **Extract**: Names, roles, contact details; solicitor info when present
- **Indicators**: Role keywords ("Vendor/Seller", "Purchaser/Buyer", "Landlord", "Tenant"), legal entity markers ("Pty Ltd", ABN/ACN), and solicitor fields ("Solicitor/Conveyancer")
- **Guidance**: Populate contact and solicitor fields when explicitly provided; infer role via nearest headings/labels

### Dates (`dates`)
- **Extract**: Normalize to YYYY-MM-DD in `date_value`; retain original `date_text`; set `is_business_days` where stated; set `date_type`
- **Indicators**: "Exchange", "Settlement/Completion", "Cooling-off", "Sunset", "Notice", "On or before", "Business days"
- **Guidance**: Normalize to YYYY-MM-DD in `date_value`, retain original in `date_text`, set `is_business_days` when stated; set `date_type` enum accordingly

### Financial Amounts (`financial_amounts`)
- **Extract**: Numeric `amount` (strip symbols/commas); `currency` default AUD; set `amount_type`
- **Indicators**: "$", "AUD", "deposit", "balance", "price", "%", "GST", "duty", "adjustments"
- **Guidance**: Strip symbols/commas for `amount`; default `currency` to "AUD" unless specified; set `amount_type` via cues

### Legal References (`legal_references`)
- **Extract**: Include `act_name`, `section_number`, `state_specific` when present
- **Indicators**: "Act", "Regulation", sections (e.g., "s 66W", "s. 27"), clause references, state names
- **Guidance**: Populate `act_name`, `section_number`, and `state_specific` where available

### Conditions (`conditions`)
- **Extract**: `clause_id` if available; `condition_text` (verbatim excerpt), optional `condition_summary`; if explicitly stated, set `is_special_condition`/`is_standard_condition`, `requires_action`, `action_by_whom`; record `deadline_text` and normalized `action_deadline` when determinable
- **Indicators**: "Special Condition/SC", "Subject to" (finance/building & pest/valuation/DA), "Time is of the essence"
- **Guidance**: Set `is_special_condition`/`is_standard_condition` and `requires_action`; include `action_by_whom` where named; capture `deadline_text`; normalize `action_deadline` when determinable

### Property Details (`property_details`)
- **Extract**: Zoning, easements/encumbrances, bedrooms/bathrooms/parking; strata flags and identifiers; levies under `strata_fees` when present
- **Indicators**: Zoning/planning ("Zoning/LEP", codes like R2, B4), easements/encumbrances, bedrooms/bathrooms/parking counts, strata cues ("Strata Plan/SP", "Owners Corporation", "levies")
- **Guidance**: Set `is_strata`, `strata_plan_number`; store levies in `strata_fees` as FinancialAmount

### Additional Addresses (`additional_addresses`)
- **Extract**: Mailing/service/registered office addresses
- **Indicators**: Mailing/service/registered office addresses, "PO Box", "c/-"
- **Guidance**: Use when distinct from the main property address

### Contact References (`contact_references`)
- **Extract**: Raw phone/email strings
- **Indicators**: Phone numbers (AU formats), email addresses
- **Guidance**: Store raw strings as found


## Text to process:
```
{{ contract_text }}
```