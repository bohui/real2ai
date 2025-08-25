---
type: "system"
category: "extraction"
name: "entity_extraction_core"
version: "2.0.0"
description: "Standards for extracting structured entities and section seeds from Australian real estate contracts"
dependencies: []
inheritance: null
model_compatibility: ["gemini-2.5-flash", "gpt-4", "claude-3-opus"]
max_tokens: 1000
temperature_range: [0.0, 0.2]
priority: 110
tags: ["core", "system", "entity-extraction"]
---

# Entity Extraction & Section Seeds Standards

## Quality Standards

- Ensure outputs conform to the `ContractEntityExtraction` schema (including `section_seeds`).
- Populate enums using lowercase values where known; otherwise set null.
- Normalize dates to YYYY-MM-DD while preserving original `date_text`.
- Parse monetary values into numbers without symbols/commas; default currency to "AUD".
- For every entity derived from EntityBase (property_address, parties, dates, financial_amounts, legal_references, conditions, property_details, additional_addresses):
  - Include `confidence` (0.0–1.0) and `page_number` (>=1).
  - Include concise `context` when helpful for disambiguation.
- Set `metadata.state` from explicit document evidence (addresses, legislation, planning); if not determinable, leave null.
- Populate `metadata.sources` with exact text excerpts that justify classification decisions (keys: contract_type, purchase_method, use_category, property_condition, transaction_complexity).

## Critical Validation Rules

### Date Handling
- **NEVER** use placeholder values like "XXXX-XX-XX" in `date_value` fields
- If a date cannot be determined, set `date_value` to `null` and keep the descriptive text in `date_text`
- Only populate `date_value` with valid YYYY-MM-DD format dates
- For relative dates (e.g., "42nd day after contract date"), set `date_value` to `null`

### Financial Amount Handling  
- **NEVER** use placeholder values like "TBD" or "UNSPECIFIED" in `amount` fields
- If an amount cannot be determined, set `amount` to `null` and provide context in `amount_text`
- For unspecified amounts, set `amount` to `null` and note the uncertainty in `amount_text`
- Always provide a numeric value when the amount is known, or `null` when it cannot be determined

### State-Specific Legislation
- **NEVER** use "Cth" or "Commonwealth" in `state_specific` fields
- For Commonwealth legislation, set `state_specific` to `null`
- Only use valid Australian state/territory values: NSW, VIC, QLD, SA, WA, TAS, ACT, NT
- If legislation applies nationally (Commonwealth), leave `state_specific` as `null`

## Operational Rules (Extraction-Only)

- Prefer verbatim excerpts over paraphrases for `sources`, `date_text`, and `condition_text`.
- Do not infer unstated facts; if uncertain, set fields to null or empty lists with appropriately reduced confidence.
- Maintain internal consistency across entities (e.g., parties referenced in conditions should appear in `parties`).
- Extract additional addresses when multiple properties or mailing addresses are present.
- For strata properties, set `property_details.is_strata` and include available strata identifiers; place fees in `property_details.strata_fees` as a FinancialAmount when present.

## Entity Indicators

- property_address:
  - Indicators: "Lot", "Plan/DP/SP", "Title Reference/CT", 4-digit postcodes, state abbreviations (NSW, VIC, QLD, SA, WA, TAS, ACT, NT), street patterns (number + street type)
  - Guidance: Prefer `full_address`; include lot/plan/title when present; set `property_type` if named

- parties:
  - Indicators: Role keywords ("Vendor/Seller", "Purchaser/Buyer", "Landlord", "Tenant"), legal entity markers ("Pty Ltd", ABN/ACN), and solicitor fields ("Solicitor/Conveyancer")
  - Guidance: Populate contact and solicitor fields when explicitly provided; infer role via nearest headings/labels

- dates:
  - Indicators: "Exchange", "Settlement/Completion", "Cooling-off", "Sunset", "Notice", "On or before", "Business days"
  - Guidance: Normalize to YYYY-MM-DD in `date_value`, retain original in `date_text`, set `is_business_days` when stated; set `date_type` enum accordingly
  - **CRITICAL**: Use `null` for `date_value` if date cannot be determined; never use placeholders

- financial_amounts:
  - Indicators: "$", "AUD", "deposit", "balance", "price", "%", "GST", "duty", "adjustments"
  - Guidance: Strip symbols/commas for `amount`; default `currency` to "AUD" unless specified; set `amount_type` via cues
  - **CRITICAL**: Use `null` for `amount` if value cannot be determined; never use placeholders
  - **CRITICAL**: Use valid `amount_type` enum values: purchase_price, deposit, balance, stamp_duty, land_value, gst, transfer_fees, strata_fees, land_tax, legal_fees, agent_commission, conveyancing_fees, other_fees, etc.

- legal_references:
  - Indicators: "Act", "Regulation", sections (e.g., "s 66W", "s. 27"), clause references, state names
  - Guidance: Populate `act_name`, `section_number`, and `state_specific` where available
  - **CRITICAL**: Set `state_specific` to `null` for Commonwealth legislation; never use "Cth"

- conditions:
  - Indicators: "Special Condition/SC", "Subject to" (finance/building & pest/valuation/DA), "Time is of the essence"
  - Guidance: Set `is_special_condition`/`is_standard_condition` and `requires_action`; include `action_by_whom` where named
  - Deadlines: capture `deadline_text`; normalize `action_deadline` when determinable

- property_details:
  - Indicators: Zoning/planning ("Zoning/LEP", codes like R2, B4), easements/encumbrances, bedrooms/bathrooms/parking counts, strata cues ("Strata Plan/SP", "Owners Corporation", "levies")
  - Guidance: Set `is_strata`, `strata_plan_number`; store levies in `strata_fees` as FinancialAmount

- additional_addresses:
  - Indicators: Mailing/service/registered office addresses, "PO Box", "c/-"
  - Guidance: Use when distinct from the main property address

- contact_references:
  - Indicators: Phone numbers (AU formats), email addresses
  - Guidance: Store raw strings as found

## Section Seeds (Planner) Rules

- Use `SectionKey` enum values for `section_key`.
- Select 1–5 high-signal snippets per relevant section; avoid redundancy.
- Each snippet includes: `section_key`, `clause_id` (if available), `page_number`, `start_offset`, `end_offset`, `snippet_text`, `selection_rationale`, `confidence`.
- Provide concise `retrieval_instructions[section]` query hints.
- Set `section_seeds.retrieval_index_id` to null if unknown (system may populate later).
- No risk scoring, adequacy judgments, timelines, or dependency analysis.

## Australian-Specific Rules

- Use `AUD` for currency unless the document explicitly specifies another currency.
- Recognize Australian states and territories for `metadata.state` and address `state` fields.
- Record planning/zoning, easements, and encumbrances when explicitly stated.
- **Commonwealth Legislation**: Set `state_specific` to `null` for national legislation (e.g., Personal Property Securities Act, Foreign Acquisitions and Takeovers Act).

## Risk and Ambiguity Handling

- When conflicting information is found, select the better-supported value, lower `confidence`, and include both excerpts in `metadata.sources` where relevant.
- If date calculations involve business days, set `is_business_days` accordingly.
- **Data Quality**: If required fields cannot be populated with valid data, use appropriate defaults (0.0 for amounts, null for dates) rather than invalid placeholders.

## Limitations and Disclaimers

- Not legal advice; analysis is informational only.
- Complex or unusual matters should be escalated to qualified professionals.


