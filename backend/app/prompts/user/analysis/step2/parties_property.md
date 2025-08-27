---
type: "user"
category: "instructions"
name: "parties_property_analysis"
version: "2.0.0"
description: "Step 2.1 - Parties and Property Verification Analysis"
fragment_orchestration: "step2_parties_property"
required_variables:
  - "analysis_timestamp"
optional_variables:
  - "extracted_entity"
  - "legal_requirements_matrix"
  - "contract_type"
  - "retrieval_index_id"
  - "seed_snippets"
  - "australian_state"
  - "use_category"
  - "property_condition"
  - "purchase_method"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 6000
temperature_range: [0.1, 0.3]
output_parser: PartiesPropertyAnalysisResult
tags: ["step2", "parties", "property", "verification"]
---

# Parties & Property Verification Analysis (Step 2.1)

Perform systematic verification analysis of parties and property details using Step 1 outputs as baseline. Use provided seed snippets first; expand via targeted retrieval only if coverage or confidence is insufficient. Avoid using full contract text unless explicitly instructed or required to resolve ambiguities.

## Contract Context
{% set meta = (extracted_entity or {}).get('metadata') or {} %}
- **State**: {{ australian_state or meta.get('state') or 'unknown' }}
- **Contract Type**: {{ contract_type or meta.get('contract_type') or 'unknown' }}
- **Purchase Method**: {{ purchase_method or meta.get('purchase_method') or 'unknown' }}
- **Use Category**: {{ use_category or meta.get('use_category') or 'unknown' }}
- **Property Condition**: {{ property_condition or meta.get('property_condition') or 'unknown' }}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Party Verification
Examine all parties to the transaction and assess:

**For each party, identify:**
- Full legal name as stated in contract
- Role in transaction (vendor, purchaser, guarantor, etc.)
- Any entity structure (individual, company, trust, etc.)
- Contact information and addresses

**Assess legal capacity indicators:**
- Age references or capacity statements
- Authority to contract (for entities)
- Any guardianship or power of attorney arrangements
- Signing authority and witness requirements

**Flag verification concerns:**
- Inconsistent name spellings or formats
- Missing entity registration details (ABN/ACN for companies)
- Unclear authority arrangements
- Potential capacity issues

### 2. Property Identification Verification

**Analyze legal description completeness:**
- Street address accuracy and completeness
- Lot number and plan number (e.g., Lot 1 DP 123456)
- Title reference (Volume/Folio or identifier)
- Property type classification
- Strata information if applicable

**Check for verification issues:**
- Missing critical identifiers
- Inconsistent property descriptions
- Ambiguous location references
- Incomplete legal descriptions

**Cross-reference property details:**
- Ensure consistency across all contract sections
- Verify against any attached plans or documents
- Check for property boundary definitions
- Assess adequacy for title search purposes

### 3. Inclusions and Exclusions Analysis

**Inventory all items mentioned:**
- Fixtures explicitly included or excluded
- Fittings and chattels listed
- Any conditional inclusions
- Items with condition statements

**Assess completeness and clarity:**
- Comprehensive coverage of typical items
- Clear categorization of items
- Unambiguous descriptions
- Condition statements adequacy

**Identify potential issues:**
- Ambiguous item descriptions
- Unusual exclusions that may indicate problems
- Missing common items (appliances, fixtures)
- Potential disputes over item classifications

### 4. Risk Assessment

**Evaluate overall risk indicators:**
- Party verification concerns requiring follow-up
- Property description gaps affecting title searches
- Inclusion/exclusion disputes potential
- Legal capacity or authority issues

**Provide recommendations:**
- Additional verification steps needed
- Documentation requirements for entities
- Clarifications needed for property description
- Items requiring amendment or negotiation

## Seed Snippets (Primary Context)

{% if seed_snippets %}
Use these high-signal snippets as primary context:
{{seed_snippets | tojsonpretty}}
{% else %}
No seed snippets provided.
{% endif %}

## Additional Context

{% if extracted_entity %}
### Entity Extraction Results (Baseline)
Use these as the canonical baseline; verify and reconcile discrepancies found in seeds or retrieval:
{{extracted_entity | tojsonpretty}}

### Step 1 Metadata (Scoping)
Use `metadata` to scope applicable checks and thresholds (state, contract_type, purchase_method, use_category, property_condition):
{{ meta | tojsonpretty }}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
Relevant legal requirements for {{australian_state}} {{contract_type}}:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions (Seeds + Retrieval + Metadata Scoping)

1. Use `extracted_entity` (and its `metadata`) as the baseline; scope checks per state/contract_type/purchase_method/use_category/property_condition.
2. Use `seed_snippets` as primary evidence. Cite clause ids/sections where possible.
3. If seed coverage/confidence is insufficient, perform targeted retrieval from `retrieval_index_id` using concise queries (e.g., names/roles, authority/witness requirements, legal description lot/plan/title). Limit retrieval to only what is necessary.
4. Reconcile any discrepancies between seeds, retrieval snippets, and baseline entities; prefer explicit contract language.
5. Assess risk levels using high/medium/low classification. Provide evidence citations for all findings.
6. Report whether retrieval was used and how many additional snippets were incorporated.

## Expected Output

Provide a comprehensive analysis following the PartiesPropertyAnalysisResult schema with:

- Complete party verification assessment with legal capacity evaluation
- Detailed property identification verification with completeness assessment  
- Full inclusions/exclusions inventory with dispute risk analysis
- Risk indicators with specific impact and mitigation recommendations
- Overall risk classification and confidence scoring
- Evidence references and analysis notes

Ensure all findings are supported by specific contract text references and comply with {{australian_state}} legal requirements for {{contract_type}} transactions.