---
type: "user"
category: "instructions"
name: "image_semantics_zoning_map"
version: "1.0.0"
description: "Zoning map semantic analysis for development controls and land use"
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
output_parser: ZoningMapSemantics
tags: ["zoning", "planning", "development", "land_use"]
---

# Zoning Map Analysis - {{ australian_state }}

You are analyzing a **zoning map** for an Australian property. Extract comprehensive zoning and development control information following the ZoningMapSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Zoning Map
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

## Zoning Analysis Objectives Objectives

### 1. Environmental Elements (environmental_elements)
**Map all zoning areas and overlays:**
- **Environmental type**: "zoning_area", "overlay", "development_control", "heritage_area"
- **Risk level**: restrictions and development limitations
- **Impact area**: zoning boundaries and affected areas
- **Mitigation measures**: compliance requirements and controls

### 2. Zoning-Specific Fields

#### Zoning Classifications (zoning_classifications)
Identify all zoning categories:
- **Residential Zones**: R1, R2, R3, R4, R5 (low to high density)
- **Commercial Zones**: B1, B2, B3, B4, B5, B6, B7, B8 (various commercial uses)
- **Industrial Zones**: IN1, IN2, IN3, IN4 (general to special industrial)
- **Rural Zones**: RU1, RU2, RU3, RU4, RU5, RU6 (primary production to transition)
- **Special Use Zones**: SP1, SP2, SP3 (infrastructure, classified roads, tourist)
- **Recreation Zones**: RE1, RE2 (public/private recreation)
- **Environmental Zones**: E1, E2, E3, E4 (national parks to environmental living)

#### Development Controls (development_controls)
Document development control areas:
- **Floor Space Ratio (FSR)**: Maximum building floor area controls
- **Building Height Limits**: Maximum height restrictions by zone
- **Density Controls**: Dwelling density and subdivision controls
- **Setback Requirements**: Minimum building setback controls
- **Landscaping Requirements**: Minimum landscaping and tree preservation
- **Parking Requirements**: Minimum parking space provisions

#### Height Restrictions (height_restrictions)
Map building height control zones:
- **Height of Buildings Maps**: Specific height limits (meters/storeys)
- **Height Incentive Areas**: Areas with bonus height provisions
- **Airport Height Restrictions**: Aviation-related height controls
- **Heritage Height Controls**: Height limits in heritage areas
- **View Protection Heights**: Heights protecting public views

#### Land Use Permissions (land_use_permissions)
Document permitted and prohibited uses:
- **Permitted without Consent**: Uses allowed as of right
- **Permitted with Consent**: Uses requiring development approval
- **Prohibited Uses**: Uses not permitted in the zone
- **Additional Permitted Uses**: Special local provisions
- **Existing Use Rights**: Grandfathered non-conforming uses

## Planning Assessment

### Zoning Compliance
Evaluate property use compliance:
- **Current Use Compatibility**: Existing use matches zoning
- **Proposed Use Compliance**: Intended use permitted in zone
- **Development Potential**: Additional development opportunities
- **Non-Conforming Use Issues**: Existing non-compliant uses
- **Expansion Limitations**: Restrictions on extending non-conforming uses

### Development Opportunities
Assess development potential:
- **Redevelopment Options**: Potential for site redevelopment
- **Subdivision Potential**: Ability to subdivide the property
- **Mixed Use Opportunities**: Commercial/residential combinations
- **Density Increases**: Potential for additional dwellings
- **Commercial Conversion**: Residential to commercial conversion potential

### Planning Constraints
Identify development limitations:
- **Heritage Restrictions**: Heritage conservation requirements
- **Environmental Constraints**: Environmental protection limitations
- **Infrastructure Limitations**: Utility capacity constraints
- **Traffic Impact**: Development impact on local traffic
- **Community Opposition**: Potential for objections to development

## {{ australian_state }} Zoning Systems

{% if australian_state == "NSW" %}
**NSW Planning Framework:**
- Check Local Environment Plan (LEP) zoning provisions
- Note State Environmental Planning Policy (SEPP) requirements
- Identify Regional Environment Plan (REP) implications
- Check for Greater Sydney Region Plan consistency
{% elif australian_state == "VIC" %}
**VIC Planning Framework:**
- Verify Planning Scheme zoning provisions
- Check State Planning Policy Framework requirements
- Note Local Planning Policy Framework provisions
- Identify particular and general provisions applicability
{% elif australian_state == "QLD" %}
**QLD Planning Framework:**
- Check Planning Scheme zoning categories
- Note State Planning Policy requirements
- Identify Regional Plan consistency
- Check for State Development Area implications
{% endif %}

## Risk Assessment Focus

### Critical Zoning Risks
1. **Use Non-Compliance**: Current/intended use not permitted in zone
2. **Development Restrictions**: Significant limitations on development potential
3. **Height/Density Conflicts**: Existing buildings exceed current controls
4. **Heritage Constraints**: Severe restrictions on property modifications
5. **Environmental Limitations**: Environmental overlays restricting development
6. **Infrastructure Inadequacy**: Zoning potential exceeds infrastructure capacity

### Investment Implications
Assess zoning impact on property value:
- Development potential and holding capacity
- Rental income potential from permitted uses
- Capital growth potential from zoning changes
- Risk of downzoning or increased restrictions

## Output Requirements

Return a valid JSON object following the **ZoningMapSemantics** schema with:

### Required Base Fields
- `image_type`: "zoning_map"
- `textual_information`: All zoning labels and classifications
- `spatial_relationships`: Zoning boundaries and property interactions
- `semantic_summary`: Zoning and development control overview
- `property_impact_summary`: Development potential and restrictions
- `key_findings`: Critical zoning discoveries
- `areas_of_concern`: Compliance or development issues
- `analysis_confidence`: Overall confidence level

### Zoning Map Specific Fields
- `environmental_elements`: All zoning and overlay areas
- `zoning_classifications`: Complete zoning category mapping
- `development_controls`: Development control requirements
- `height_restrictions`: Building height limitation areas
- `land_use_permissions`: Permitted and prohibited uses

### Quality Standards
- **Planning Accuracy**: Precise zoning boundary identification
- **Use Assessment**: Clear permitted use analysis
- **Development Focus**: Emphasize development potential and constraints
- **Compliance Check**: Reference relevant planning legislation
- **Investment Analysis**: Consider property development opportunities

Begin analysis now. Return only the structured JSON output following the ZoningMapSemantics schema.
