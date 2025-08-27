---
type: "user"
category: "instructions"
name: "image_semantics_title_plan"
version: "1.0.0"
description: "Title plan semantic analysis for legal boundaries and ownership"
fragment_orchestration: "image_analysis"
required_variables:
  - "image_data"
  - "australian_state"
  - "contract_type"
optional_variables:
  - "purchase_method"
  - "use_category"
  - "property_condition"
  - "transaction_complexity"
  - "seed_snippets"
  - "diagram_filenames"
model_compatibility: ["gemini-2.5-flash", "gpt-4-vision"]
max_tokens: 32768
temperature_range: [0.1, 0.3]
output_parser: TitlePlanSemantics
tags: ["title", "legal", "boundaries", "ownership"]
---

# Title Plan Analysis - {{ australian_state }}

You are analyzing a **title plan** for an Australian property. Extract legal boundary information, lot details, and ownership structures following the TitlePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Title Plan
{% if purchase_method %}
- **Purchase Method**: {{ purchase_method }}
{% endif %}
{% if use_category %}
- **Use Category**: {{ use_category }}
{% endif %}
{% if property_condition %}
- **Property Condition**: {{ property_condition }}
{% endif %}
{% if transaction_complexity %}
- **Transaction Complexity**: {{ transaction_complexity }}
{% endif %}

{% if seed_snippets %}
## Priority Elements
Focus on: {{ seed_snippets | tojson }}
{% endif %}

{% if diagram_filenames %}
## Files
Analyzing: {{ diagram_filenames | join(", ") }}
{% endif %}

## Title Plan Analysis Objectives

### 1. Boundary Elements (boundary_elements)
**Extract legal property boundaries:**
- **Boundary type**: "front", "rear", "side", "common", "curved"
- **Boundary markings**: survey marks defining legal boundaries
- **Dimensions**: precise legal measurements and bearings
- **Encroachments**: structures crossing legal boundaries
- **Easements**: legal easements affecting boundaries

### 2. Title Plan Specific Fields

#### Lot Numbers (lot_numbers)
Identify all lot identification:
- **Individual lots**: residential/commercial lot numbers
- **Common property lots**: shared facility lots
- **Access lots**: road and access way lots
- **Utility lots**: infrastructure and utility lots
- **Reserve lots**: public reserve and drainage lots

#### Plan Numbers (plan_numbers)
Document plan registration details:
- **Plan of subdivision numbers**: registered plan references
- **Plan types**: Deposited Plan (DP), Strata Plan (SP), etc.
- **Plan dates**: registration and amendment dates
- **Plan authorities**: Local Government Area/registrar details
- **Parent plan references**: original subdivision plans

#### Easements (easements)
Map all legal easements and restrictions:
- **Easement types**: drainage, access, utility, light/air
- **Easement dimensions**: width, length, and area
- **Beneficiary parties**: who benefits from easement
- **Burden/benefit**: which lots are burdened/benefited
- **Easement purposes**: specific use permissions

#### Owners Details (owners_details)
Extract ownership information (where shown):
- **Registered proprietors**: legal owner names
- **Ownership types**: fee simple, leasehold, strata title
- **Share entitlements**: unit entitlements in strata schemes
- **Corporate ownership**: company/trust ownership
- **Joint ownership**: tenants in common/joint tenants

## Legal Title Analysis Objectives

### Title Boundaries vs Survey
Analyze boundary definitions:
- **Legal vs Physical**: title boundaries vs fence lines
- **Survey Accuracy**: boundary precision and marking
- **Boundary Disputes**: areas of uncertainty or conflict
- **Title Dimensions**: legal measurements vs actual measurements
- **Adverse Possession**: long-term occupation differences

### Easement Analysis
Detailed easement examination:
- **Easement Creation**: how and when easements were created
- **Easement Rights**: specific rights granted
- **Easement Obligations**: maintenance and access responsibilities
- **Easement Variations**: any modifications to original easements
- **Easement Impacts**: effects on property use and development

### Strata/Community Title Elements
For strata and community title properties:
- **Unit entitlements**: voting and levy calculation shares
- **Common property**: shared areas and facilities
- **Exclusive use areas**: private use of common property
- **Management rights**: building management arrangements
- **By-law restrictions**: scheme-specific rules and restrictions

## {{ australian_state }} Title Requirements

{% if australian_state == "NSW" %}
**NSW Title System:**
- Check Torrens Title system compliance
- Note Land and Property Information (LPI) plan standards
- Identify any Old System Title implications
- Check for Aboriginal Land Rights Act considerations
{% elif australian_state == "VIC" %}
**VIC Title System:**
- Verify Torrens Title system compliance
- Check Land Use Victoria plan standards
- Note any Crown Land implications
- Identify Traditional Owner settlement considerations
{% elif australian_state == "QLD" %}
**QLD Title System:**
- Check Torrens Title system compliance
- Note Department of Resources plan standards
- Identify any Native Title implications
- Check for State Land considerations
{% endif %}

## Risk Assessment Priorities

### Critical Title Risks
1. **Boundary Uncertainties**: Unclear or disputed boundaries
2. **Easement Conflicts**: Easements affecting property use
3. **Title Defects**: Missing or incorrect title information
4. **Access Issues**: Legal access to public roads
5. **Encroachment Problems**: Unauthorized use of neighboring land
6. **Registration Errors**: Errors in plan registration

### Legal Compliance Issues
- **Planning Compliance**: lot sizes meeting planning requirements
- **Subdivision Compliance**: proper subdivision approval
- **Easement Compliance**: easements properly created and registered
- **Survey Compliance**: adequate survey accuracy for title purposes

## Output Requirements

Return a valid JSON object following the **TitlePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "title_plan"
- `textual_information`: All legal annotations and identifiers
- `spatial_relationships`: Lot and easement relationships
- `semantic_summary`: Title structure overview
- `property_impact_summary`: Legal and ownership implications
- `key_findings`: Critical title discoveries
- `areas_of_concern`: Legal issues or uncertainties
- `analysis_confidence`: Overall confidence level

### Title Plan Specific Fields
- `boundary_elements`: Legal boundary analysis
- `lot_numbers`: All lot identifications
- `plan_numbers`: Plan registration details
- `easements`: Complete easement mapping
- `owners_details`: Ownership information (if visible)

### Quality Standards
- **Legal Accuracy**: Precise legal boundary identification
- **Complete Documentation**: All visible legal elements
- **Risk Assessment**: Identify title and ownership risks
- **Compliance Check**: Reference relevant title legislation
- **Professional Standard**: Suitable for legal/conveyancing review

Begin analysis now. Return only the structured JSON output following the TitlePlanSemantics schema.
