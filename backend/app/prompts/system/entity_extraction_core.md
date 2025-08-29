---
type: "system"
category: "extraction"
name: "entity_extraction_core"
version: "2.0.0"
description: "Standards for extracting structured entities from Australian real estate contracts"
dependencies: []
inheritance: null
model_compatibility: ["gemini-2.5-flash", "gpt-4", "claude-3-opus"]
max_tokens: 1000
temperature_range: [0.0, 0.2]
priority: 110
tags: ["core", "system", "entity-extraction"]
---

# Entity Extraction Standards

## Quality Standards

- Ensure outputs conform to the `ContractEntityExtraction` schema .
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

** Provide the final answer only, no chain-of-thought. Output directly in JSON.**

