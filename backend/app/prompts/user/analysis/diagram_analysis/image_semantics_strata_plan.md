---
type: "user"
category: "instructions"
name: "image_semantics_strata_plan"
version: "1.0.0"
description: "Strata plan semantic analysis for strata ownership structure"
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
output_parser: StrataPlanSemantics
tags: ["strata", "ownership", "common_property", "units"]
---

# Strata Plan Analysis - {{ australian_state }}

You are analyzing a **strata plan** for an Australian property. Extract strata ownership structure, common property, and unit details following the StrataPlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Strata Plan
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

## Schema Compliance Requirements

**IMPORTANT: Use ONLY the following enum values as specified in the schema:**

### Text Type (text_type)
For `textual_information.text_type`, use ONLY these values:
- `"label"` - For lot numbers, area names, plan references
- `"measurement"` - For lot areas, dimensions, distances
- `"title"` - For main headings, plan titles, section headers
- `"legend"` - For map keys, symbols, abbreviations
- `"note"` - For explanatory text, legal statements, conditions
- `"warning"` - For cautionary text, important notices
- `"other"` - For any text that doesn't fit the above categories

### Confidence Level (analysis_confidence)
For `analysis_confidence`, use ONLY these values:
- `"high"` - When analysis is comprehensive and confident
- `"medium"` - When analysis has some uncertainty
- `"low"` - When analysis has significant limitations

### Building Type (building_type)
For `building_elements.building_type`, use ONLY these values:
- `"residential"` - Residential units
- `"commercial"` - Commercial units
- `"mixed_use"` - Mixed use units
- `"other"` - Any other building type

### Area Type (area_type)
For `building_elements.area_type`, use ONLY these values:
- `"exclusive_use"` - Exclusive use areas
- `"common_area"` - Common areas
- `"limited_common"` - Limited common areas
- `"other"` - Any other area type

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Strata Plan Analysis Objectives

### 1. Boundary Elements (boundary_elements)
**Extract strata lot boundaries:**
- **Boundary type**: "unit", "common_property", "exclusive_use", "accessway"
- **Boundary markings**: walls, floors, ceilings defining lot boundaries
- **Dimensions**: unit areas and common property dimensions
- **Encroachments**: any boundary variations or encroachments
- **Easements**: internal easements within strata scheme

### 2. Building Elements (building_elements)
**Document strata buildings and structures:**
- **Building type**: "residential_unit", "commercial_unit", "common_facility", "parking"
- **Construction stage**: existing buildings within strata scheme
- **Height restrictions**: building height within strata development
- **Setback requirements**: building setbacks within strata lots
- **Building envelope**: allowable building areas within lots

### 3. Strata-Specific Fields

#### Lot Entitlements (lot_entitlements)
Extract unit entitlement information:
- **Unit entitlements**: numerical entitlements for each lot
- **Schedule of unit entitlements**: total scheme entitlements
- **Entitlement calculations**: basis for entitlement allocation
- **Voting entitlements**: voting rights based on entitlements
- **Levy contributions**: maintenance levy calculation basis

#### Common Areas (common_areas)
Identify all common property:
- **Common property lots**: designated common property areas
- **Shared facilities**: pools, gyms, gardens, community rooms
- **Access ways**: common corridors, stairs, lifts, driveways
- **Utility areas**: common utility rooms, plant rooms, substations
- **Roof and basement**: common roof space and basement areas

#### Exclusive Use Areas (exclusive_use_areas)
Map exclusive use allocations:
- **Allocated parking**: parking spaces allocated to specific lots
- **Storage areas**: storage rooms allocated to lots
- **Courtyards/balconies**: private outdoor areas
- **Garden beds**: allocated garden maintenance areas
- **Utility connections**: meter locations and service connections

#### Strata Restrictions (strata_restrictions)
Document scheme restrictions:
- **Building restrictions**: limitations on unit modifications
- **Use restrictions**: permitted uses for each lot type
- **Pet restrictions**: animal keeping limitations
- **Noise restrictions**: quiet hours and noise limitations
- **Architectural restrictions**: external modification controls

#### Management Areas (management_areas)
Identify management responsibilities:
- **Body corporate management**: areas under BC control
- **Professional management**: externally managed areas
- **Self-management**: owner-managed common areas
- **Caretaker areas**: areas with caretaking agreements
- **Maintenance schedules**: regular maintenance responsibility areas

## Strata Ownership Analysis Objectives

### Unit Structure
Analyze strata lot composition:
- **Residential lots**: apartment/townhouse unit identification
- **Commercial lots**: retail/office unit identification
- **Parking lots**: designated parking lot numbers
- **Storage lots**: storage facility lot numbers
- **Utility lots**: common utility and service lots

### Entitlement Assessment
Evaluate entitlement structure:
- **Entitlement fairness**: reasonable allocation basis
- **Area correlation**: entitlements vs actual unit areas
- **Value correlation**: entitlements vs unit values
- **Special entitlements**: any non-standard entitlement arrangements
- **Future variations**: potential for entitlement changes

### Common Property Management
Assess common property adequacy:
- **Facility adequacy**: sufficient common facilities for scheme size
- **Maintenance access**: adequate access for maintenance
- **Insurance coverage**: appropriate common property insurance
- **Management costs**: reasonable management and maintenance costs
- **Capital works**: major repair and replacement planning

## {{ australian_state }} Strata Requirements

{% if australian_state == "NSW" %}
**NSW Strata Laws:**
- Check Strata Schemes Management Act compliance
- Note Community Land Management Act implications
- Identify Building Defects provisions
- Check for Collective Sales provisions
{% elif australian_state == "VIC" %}
**VIC Strata Laws:**
- Verify Owners Corporation Act compliance
- Check Subdivision Act requirements
- Note Building and Construction Industry Security of Payment Act
- Identify dispute resolution requirements
{% elif australian_state == "QLD" %}
**QLD Strata Laws:**
- Check Body Corporate and Community Management Act compliance
- Note Building Units and Group Titles Act implications
- Identify Queensland Civil and Administrative Tribunal jurisdiction
- Check for defects liability provisions
{% endif %}

## Risk Assessment Priorities

### Critical Strata Risks
1. **Entitlement Disputes**: Unfair or incorrect unit entitlements
2. **Common Property Issues**: Inadequate or poorly maintained facilities
3. **Management Problems**: Poor body corporate governance
4. **Financial Issues**: High levies or special assessments
5. **Building Defects**: Structural or waterproofing issues
6. **Use Conflicts**: Conflicting lot uses or restrictions

### Investment Considerations
Assess strata investment risks:
- Management rights and agreements
- Rental restrictions and compliance
- Capital works and maintenance costs
- Building age and condition
- Strata insurance adequacy

## Output Requirements

Return a valid JSON object following the **StrataPlanSemantics** schema with:

### Required Base Fields
- `image_type`: "strata_plan"
- `textual_information`: All strata labels and lot numbers
- `spatial_relationships`: Lot and common property relationships
- `semantic_summary`: Strata structure overview
- `property_impact_summary`: Ownership and management implications
- `key_findings`: Critical strata discoveries
- `areas_of_concern`: Strata issues or risks
- `analysis_confidence`: Overall confidence level

### Strata Plan Specific Fields
- `boundary_elements`: Strata lot boundary analysis
- `building_elements`: Buildings within strata scheme
- `lot_entitlements`: Unit entitlement structure
- `common_areas`: Common property identification
- `exclusive_use_areas`: Exclusive use allocations
- `strata_restrictions`: Scheme restrictions and rules
- `management_areas`: Management responsibility areas

### Quality Standards
- **Legal Accuracy**: Precise strata lot identification
- **Entitlement Analysis**: Complete unit entitlement assessment
- **Management Assessment**: Body corporate governance evaluation
- **Risk Identification**: Strata-specific risks and issues
- **Investment Analysis**: Suitable for strata purchase decisions

Begin analysis now. Return only the structured JSON output following the StrataPlanSemantics schema.
