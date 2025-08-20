## Epic story: Contract classification powered by OCR

### Narrative
A buyer uploads a property contract. The UI keeps things simple and only asks for one decision: the `contract_type`. They choose “purchase agreement” or “lease agreement,” or “option to purchase.” That’s it.

Behind the scenes, OCR parses the document to infer the missing context fields:
- If it’s a purchase agreement, OCR determines the `purchase_method` (off_plan, auction, private_treaty, tender, expression_of_interest, or standard).
- For both purchase and lease agreements, OCR identifies the `use_category` (residential, commercial, industrial, or retail).

Prompts and analysis route correctly based on the chosen `contract_type` and any OCR-inferred context. There are no API versions or data migrations to worry about, and the schema remains minimal and direct. The system produces consistent logic and useful analytics with minimal UI friction.

### Why this matters
- Reduces user cognitive load to a single, clear choice.
- Preserves a lean schema while capturing important distinctions via OCR.
- Improves routing accuracy for prompts and analysis without UI complexity.

---

## Scope

### Authoritative field
- `contract_type` is the single authoritative user-provided classification.

### OCR-inferred fields
- `purchase_method` is inferred when `contract_type = purchase_agreement`.
- `lease_category` is inferred when `contract_type = lease_agreement`.

### No UI changes for inference fields
- The UI does not surface `purchase_method` or `lease_category` selectors.
- These fields are optional in the schema and will be populated by OCR where possible.

---

## Enums

### ContractType (authoritative)
- `purchase_agreement`
- `lease_agreement`
- `option_to_purchase`
- `unknown`

### PurchaseMethod (OCR-inferred; only when `contract_type = purchase_agreement`)
- `standard`
- `off_plan`
- `auction`
- `private_treaty`
- `tender`
- `expression_of_interest`

### UseCategory (OCR-inferred; applies to `purchase_agreement` and `lease_agreement`)
- `residential`
- `commercial`
- `industrial`
- `retail`

---

## User stories
- As an end user, I only set `contract_type` so I’m not forced to understand legal or transactional nuances.
- As the backend, I infer `purchase_method` and `use_category` via OCR to enrich routing with zero extra UI burden.
- As an analyst, I see consistent routing and outputs driven by `contract_type`, with extra specificity from OCR when available.
- As a developer, I work with a small, stable schema: `contract_type` plus optional `purchase_method` and `lease_category`.

---

## Acceptance criteria
- Allowed `contract_type` values: `purchase_agreement`, `lease_agreement`, `option_to_purchase`, `unknown`.
- `purchase_method` (optional) allowed values: `standard`, `off_plan`, `auction`, `private_treaty`, `tender`, `expression_of_interest`.
- `use_category` (optional) allowed values: `residential`, `commercial`, `industrial`, `retail`.
- UI only exposes `contract_type` selection.
- OCR attempts to populate `purchase_method` for purchase agreements and `use_category` for both purchase and lease agreements.
- Routing rules:
  - If `contract_type = purchase_agreement`, branch by `purchase_method` when present.
  - If `contract_type = lease_agreement`, branch by `use_category` when present.
  - If `contract_type = option_to_purchase`, route to option path.
- Rejected states:
  - `purchase_method` present when `contract_type ≠ purchase_agreement`.
  - `use_category` present when `contract_type = option_to_purchase`.
  - `contract_type` not in the allowed set.

---

## Validation & logging
- Validate enum values and cross-field dependencies server-side.
- Log all OCR-derived inferences (including confidence) and any defaulting behavior for observability.

---

## Analytics
- Track counts and trends by `contract_type`, `purchase_method`, and `use_category`.
- Monitor unknowns and low-confidence inferences to improve OCR prompts and models.

---

## Out of scope
- API versioning and data migrations (no real data yet).
- UI inputs for `purchase_method` and `lease_category`.

---

## Test scenarios
- Upload purchase agreement with clear auction terms → `contract_type = purchase_agreement`, OCR → `purchase_method = auction`, correct routing.
- Upload purchase agreement off-plan → OCR → `purchase_method = off_plan`, correct routing.
- Upload lease with language indicating commercial use → OCR → `use_category = commercial`, correct routing.
- Upload option to purchase → correct routing without inference fields.
- Ensure invalid combinations are rejected (e.g., `lease_category` sent with `purchase_agreement`).


---

## Context propagation
The following fields must be included in the analysis context for downstream prompts, workflows, and tools:
- `contract_type` (always present)
- `purchase_method` (nullable; present only for purchase agreements when inferred)
- `use_category` (nullable; present for purchase or lease agreements when inferred)

Example context payload shape:
```json
{
  "contract": {
    "contract_type": "purchase_agreement",
    "purchase_method": "auction",
    "use_category": "commercial"
  },
  "document": {
    "id": "<uuid>",
    "australian_state": "NSW"
  },
  "ocr": {
    "purchase_method_confidence": 0.92,
    "use_category_confidence": 0.88
  }
}
```

Acceptance criteria for context propagation:
- Context includes the three fields with correct nullability rules.
- Confidence metrics are available for any OCR-inferred values.
- Prompt/router components read these fields to select fragments and processing paths.


