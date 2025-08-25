---
type: "user"
category: "instructions"
name: "contract_entities_extraction"
version: "3.0.0"
description: "Entity extraction and section seed selection for Step 2 analysis"
fragment_orchestration: "contract_analysis"
required_variables:
  - "contract_text"
optional_variables: []
# model_compatibility: ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free", "google/gemini-2.5-flash"]
model_compatibility: ["gemini-2.5-flash"]
max_tokens: 8000
temperature_range: [0.1, 0.4]
output_parser: ContractEntityExtraction
tags: ["contract", "extraction", "section-seeds", "modular"]
---

# Step 1: Entity Extraction Instructions (Extraction-Only)

Extract structured entities and high-signal section seeds from the provided Australian real estate contract. Do not perform risk assessment, adequacy judgments, timeline mapping, or recommendations. Populate the `ContractEntityExtraction` schema only.

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

Populate these root-level entities. For each item derived from `EntityBase`, include: `confidence` (0.0–1.0), `page_number` (>=1), and `context` when helpful.

- Property Address (`property_address`): full address; lot/plan/title; `property_type` if present.
- Parties (`parties`): names, roles, contact details; solicitor info when present.
- Dates (`dates`): normalize to YYYY-MM-DD in `date_value`; retain original `date_text`; set `is_business_days` where stated; set `date_type`.
- Financial Amounts (`financial_amounts`): numeric `amount` (strip symbols/commas); `currency` default AUD; set `amount_type`.
- Legal References (`legal_references`): include `act_name`, `section_number`, `state_specific` when present.
- Conditions (`conditions`, extraction-only): `clause_id` if available; `condition_text` (verbatim excerpt), optional `condition_summary`; if explicitly stated, set `is_special_condition`/`is_standard_condition`, `requires_action`, `action_by_whom`; record `deadline_text` and normalized `action_deadline` when determinable.
- Property Details (`property_details`): zoning, easements/encumbrances, bedrooms/bathrooms/parking; strata flags and identifiers; levies under `strata_fees` when present.
- Additional Addresses (`additional_addresses`): mailing/service/registered office addresses.
- Contact References (`contact_references`): raw phone/email strings.

Rules:
- Prefer verbatim excerpts for evidence fields (`date_text`, `metadata.sources`, `condition_text`).
- Do not infer unstated facts; set null/empty with appropriately reduced `confidence`.
- Maintain internal consistency (e.g., parties referenced in conditions appear in `parties`).

## 3) Section Seeds Planner (for Step 2)

Produce high-signal snippet selections to guide Step 2 nodes. Use the `SectionKey` enum for `section_key` values: `parties_property`, `financial_terms`, `conditions`, `warranties`, `default_termination`, `settlement_logistics`, `title_encumbrances`, `adjustments_outgoings`, `disclosure_compliance`, `special_risks`, `cross_section_validation`.

For each relevant section:
- Select 1–20 concise snippets (avoid redundancy) capturing the core evidence for that section.
- Each snippet must include: `section_key`, `clause_id` (if available), `page_number`, `start_offset`, `end_offset`, `snippet_text`, `selection_rationale`, and `confidence`.
- If the same snippet is relevant to multiple sections, it may be duplicated across sections.
- Provide `retrieval_instructions[section]` as a short query hint to expand context if needed (e.g., “find all finance approval deadlines and consequences”).
- Set `section_seeds.retrieval_index_id` to null if unknown (the system may populate it later).

Do not perform any risk scoring, adequacy judgments, or timeline/dependency analysis in seeds—only selection and rationale.

## Text to process:
```
{{ contract_text }}
```