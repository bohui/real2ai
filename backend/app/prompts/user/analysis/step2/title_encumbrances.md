---
type: "user"
category: "instructions"
name: "title_encumbrances_analysis"
version: "2.0.0"
description: "Step 2.8 - Title and Encumbrances Analysis with Diagram Integration"
fragment_orchestration: "step2_title_encumbrances"
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "entities_extraction"
  - "uploaded_diagrams"
  - "legal_requirements_matrix"
  - "contract_type"
  - "retrieval_index_id"
  - "seed_snippets"
  - "image_semantics_result"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 10000
temperature_range: [0.1, 0.3]
output_parser: TitleEncumbrancesAnalysisResult
tags: ["step2", "title", "encumbrances", "diagrams", "integration"]
---

# Title and Encumbrances Analysis with Diagram Integration (Step 2.8)

Perform comprehensive analysis of title quality, encumbrances, and integrated diagram analysis covering 20+ diagram types in this Australian real estate contract, focusing on verification requirements and risk assessment.

## Contract Context
- **State**: {{ australian_state or 'unknown' }}
- **Contract Type**: {{ contract_type or 'unknown' }}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Title Analysis and Verification

**Title identification and verification:**
- Title reference (Volume/Folio or current identifier)
- Title type (Torrens, Old System, Strata)
- Registered proprietor verification
- Dealing restrictions and limitations

**Vendor capacity assessment:**
- Authority to sell assessment
- Corporate authority (if vendor is entity)
- Power of attorney arrangements
- Trustee or executor capacity

**Title quality evaluation:**
- Title defects or irregularities
- Prior dealing compliance
- Registration currency and accuracy
- Historical title issues

**Investigation requirements:**
- Required title searches and verifications
- Currency of title information
- Additional investigation needed
- Timeline for title verification

### 2. Comprehensive Encumbrance Analysis

**Identify all encumbrances:**
- Mortgages and charges
- Easements and rights of way
- Restrictive covenants
- Caveats and cautions
- Leases and licenses
- Statutory restrictions
- Planning overlays

**For each encumbrance, evaluate:**
- Registration details and priority
- Impact on property use and enjoyment
- Effect on property value
- Ongoing obligations for buyer
- Removal prospects and requirements
- Compliance obligations

**Encumbrance risk assessment:**
- Critical encumbrances requiring attention
- Encumbrances affecting financing
- Encumbrances affecting development potential
- Hidden or unregistered encumbrances risk

### 3. Integrated Diagram Analysis (20+ Types)

**Comprehensive diagram inventory:**

**Structural and Layout Diagrams:**
- Floor plans and room layouts
- Elevation drawings and sections
- Architectural detail drawings
- Structural engineering plans

**Property and Land Diagrams:**
- Site plans and property layouts
- Survey plans and boundary definitions
- Subdivision plans and lot layouts
- Landscape and garden plans

**Infrastructure and Services:**
- Services diagrams (water, sewer, gas, electricity)
- Drainage and stormwater plans
- Telecommunications and data plans
- Fire safety and emergency plans

**Legal and Regulatory:**
- Easement diagrams and rights of way
- Planning overlay maps
- Heritage constraint plans
- Environmental restriction plans

**Development and Construction:**
- Development approval plans
- Construction staging diagrams
- Traffic management plans
- Accessibility compliance plans

**Strata and Community:**
- Strata plans and common property
- Parking allocation diagrams
- Community facility plans
- Body corporate area definitions

### 4. Diagram Quality and Compliance Assessment

**For each diagram type, analyze:**
- Accuracy and currency of information
- Compliance with approval conditions
- Professional preparation standards
- Legal status and enforceability

**Cross-reference verification:**
- Consistency with contract descriptions
- Alignment with title particulars
- Integration between different diagram types
- Identification of conflicts or discrepancies

**Professional standards assessment:**
- Licensed surveyor preparation
- Architect or engineer certification
- Compliance with {{australian_state}} standards
- Quality of drafting and presentation

### 5. Services and Utilities Integration

**Service availability analysis:**
- Connection to municipal services
- Private service arrangements
- Service capacity and adequacy
- Future service requirements

**Utility infrastructure assessment:**
- Existing utility connections
- Upgrade requirements and costs
- Service authority requirements
- Connection timing and procedures

**Service encumbrances and easements:**
- Service easement locations and impacts
- Maintenance access requirements
- Future service expansion provisions
- Service authority rights and obligations

### 6. Boundary and Survey Analysis

**Boundary definition verification:**
- Survey accuracy and currency
- Boundary marker locations
- Fence line and boundary alignment
- Encroachment identification

**Survey requirements:**
- Need for updated survey
- Specific survey requirements
- Survey cost and timing
- Professional surveyor recommendations

**Boundary risk assessment:**
- Encroachment risks
- Boundary dispute potential
- Fence responsibility and costs
- Neighbor relationship impacts

### 7. Development Potential Assessment

**Development rights analysis:**
- Permitted development under encumbrances
- Restriction on future development
- Planning approval requirements
- Heritage or environmental constraints

**Diagram implications for development:**
- Existing approvals and their scope
- Infrastructure capacity for development
- Access and circulation for development
- Service upgrade requirements

## Diagram Integration Requirements

{% if image_semantics_result %}
### Diagram Semantics (Phase 1 Output)
Use the extracted diagram semantics as primary context for integration:
{{image_semantics_result | tojsonpretty}}
{% elif uploaded_diagrams %}
### Available Diagrams for Analysis
The following diagrams have been uploaded for integrated analysis:
{{uploaded_diagrams | tojsonpretty}}
{% endif %}

**Integration Instructions:**
- Cross-reference diagram semantics with contract terms and title particulars
- Verify consistency between different diagram types
- Identify conflicts or discrepancies; cite diagram references
- Assess quality, legal status, and approval/compliance information

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} title and encumbrance requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Seed Snippets (Primary Context)

{% if seed_snippets %}
Use these high-signal title/encumbrance snippets as primary context:
{{seed_snippets | tojsonpretty}}
{% else %}
No seed snippets provided.
{% endif %}

## Analysis Instructions (Seeds + Retrieval + Diagram Semantics)

1. Use `entities_extraction` and `image_semantics_result` as baseline context; verify and enrich using `seed_snippets` as primary evidence.
2. If baseline + seeds are insufficient, retrieve targeted clauses (title particulars, encumbrance schedules, easements/rights, services, overlays, surveys) from `retrieval_index_id` with concise queries. Record what was retrieved.
3. Cross-verify: ensure consistency between title/contract text and diagram semantics; document discrepancies and their implications.
4. Assess risks across title defects, encumbrance impacts, diagram reliance, and boundary issues; provide mitigation actions and verification steps.
5. Apply state-specific title registration and diagram approval requirements; assess professional standards.
6. Provide evidence citations (clauses, diagram references, registry references) for all material findings.

## Expected Output

Provide comprehensive title and encumbrances analysis following the TitleEncumbrancesAnalysisResult schema:

- Complete title analysis with verification requirements and risk assessment
- Detailed encumbrance inventory with impact and removal assessment
- Comprehensive diagram analysis across all 20+ types with quality and compliance evaluation
- Integrated services and utilities analysis with adequacy and upgrade assessment
- Boundary and survey analysis with encroachment and dispute risk evaluation
- Development potential assessment with constraint and opportunity identification
- Cross-reference verification with consistency and discrepancy analysis
- Overall risk classification with investigation and mitigation recommendations

**Critical Success Criteria (PRD 4.1.2.8):**
- 100% identification of title defects and encumbrances
- Complete integration of all available diagrams (20+ types)
- Accurate assessment of diagram quality and legal status
- Clear evaluation of title verification requirements and risks