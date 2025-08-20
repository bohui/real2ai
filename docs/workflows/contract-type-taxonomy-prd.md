## Contract Type Taxonomy Refactor PRD

### Overview
Keep using the single `contract_type` field for primary classification, and add a separate optional `purchase_method` to capture how a purchase occurs. We will rely on OCR/document analysis to infer missing context fields; the UI only needs to select the contract type.

### Goals
- **Non-overlapping taxonomy**: Avoid encoding purchase methods in `contract_type`.
- **Simplicity**: Keep `contract_type`; infer `purchase_method` via OCR. No API versioning or data migration.
- **Operational clarity**: Improve analytics, validation, and prompt routing.

### Non-Goals
- Modifying property type taxonomy.
- Changing legal interpretation beyond classification fields.

## Taxonomy

### Contract Types (authoritative)
- `purchase_agreement`
- `lease_agreement`
- `option_to_purchase`
- `unknown`

### Purchase Methods (optional; only when `contract_type = purchase_agreement`)
- `standard`
- `off_plan`
- `auction`
- `private_treaty`
- `tender`
- `expression_of_interest`

Notes:
- A contract is not both purchase and off-plan; off-plan is a purchase method, not a contract type.
- “Lease” and “Rental” are synonyms; consolidate under `lease_agreement`. `commercial_lease` is folded into `lease_agreement` (lease subcategories deferred).

## Scope of Changes

### Data Model
- Fields:
  - `contract_type` (required) — enum `ContractType`
  - `purchase_method` (nullable) — enum `PurchaseMethod`; only applicable when `contract_type = purchase_agreement`
- No `lease_category` or `contract_primary_type`.
- OCR pipeline infers `purchase_method` from document content when not provided.

### Database (Supabase)
- Redefine `contract_type` enum values to: ('purchase_agreement', 'lease_agreement', 'option_to_purchase', 'unknown').
- Create new enum `purchase_method` = ('standard', 'off_plan', 'auction', 'private_treaty', 'tender', 'expression_of_interest').
- Add nullable column `purchase_method` to `contracts` table.
- No legacy columns, no migrations needed (no real data).

### Backend (Python)
- Update `backend/app/schema/enums/property.py` `ContractType` to the authoritative set above.
- Add new enum file: `backend/app/schema/enums/purchase_method.py`.
- Update `backend/app/models/supabase_models.py` `Contract` model to include optional `purchase_method` and validate it only for `purchase_agreement`.
- Update repositories/services to read/write `purchase_method` when present; rely on OCR pipeline to populate otherwise.
- Add structured logs to trace OCR-derived inferences and any defaults.

### Frontend (TypeScript)
- Only update the `contract_type` options to the authoritative set.
- Do not add a `purchase_method` selector; this will be inferred by OCR.

### APIs
- Requests/Responses: Use `contract_type`. Accept optional `purchase_method`; if omitted, backend will attempt to infer it via OCR.
- No API versioning or deprecation path required.

### Prompt System and Workflows
- Routing:
  - If `contract_type = purchase_agreement`, branch by `purchase_method` (off_plan, auction, private_treaty, tender, expression_of_interest, standard).
  - If `contract_type = lease_agreement`, route to lease path (subcategories deferred).
  - If `contract_type = option_to_purchase`, route to option path.
- Retain existing folder structure; add method-based conditions in `fragment_manager` rules.

## Value normalization in codebase
- Replace any uses of `rental_agreement` with `lease_agreement`.
- Replace any uses of `commercial_lease` with `lease_agreement` (lease subcategories will be added later if needed).
- Where `contract_type` was set to `off_plan` or `auction`, set `contract_type = purchase_agreement` and `purchase_method` accordingly.

## Validation Rules
- `contract_type` must be one of: `purchase_agreement`, `lease_agreement`, `option_to_purchase`, `unknown`.
- If `contract_type = purchase_agreement` and `purchase_method` is provided, it must be one of the defined methods; if not provided, OCR may populate it.
- If `contract_type != purchase_agreement`, `purchase_method` must be null/absent.

## Analytics and Observability
- Track counts by `contract_type` and `purchase_method`.
- Emit structured logs when OCR infers `purchase_method` or when defaults are applied.
- Dashboards/alerts for high `unknown` rates and inference fallbacks.

## Rollout Plan
- Update enums and models.
- Update prompt routing rules.
- Ship; no data migration or API versioning required.

## Testing
- Unit: Enum conversions, validators, repository CRUD.
- Integration: API endpoints dual-read/write; prompt selection logic.
- E2E: Upload and analysis flows for each combination.
- Migration: Idempotency, mapping coverage, integrity constraints.
- Performance: Ensure no regressions in analysis routing.

## Risks and Mitigations
- OCR misclassification of `purchase_method` → Add confidence thresholds and fall back to `standard`; log all inferences.
- Prompt routing errors → Explicit tests for off-plan/auction/tender/EOI branches.

## Open Questions
- Are there additional purchase methods to support (e.g., sealed bid)?
- Lease subcategories (e.g., long-term vs. short-term) can be added later if needed.

## Appendix: Proposed Enums (Illustrative)
```python
# backend/app/schema/enums/property.py (ContractType)
class ContractType(str, Enum):
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    OPTION_TO_PURCHASE = "option_to_purchase"
    UNKNOWN = "unknown"

# backend/app/schema/enums/purchase_method.py
class PurchaseMethod(str, Enum):
    STANDARD = "standard"
    OFF_PLAN = "off_plan"
    AUCTION = "auction"
    PRIVATE_TREATY = "private_treaty"
    TENDER = "tender"
    EXPRESSION_OF_INTEREST = "expression_of_interest"
```


