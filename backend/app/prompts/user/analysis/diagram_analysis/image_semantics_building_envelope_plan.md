---
type: "user"
category: "instructions"
name: "image_semantics_building_envelope_plan"
version: "1.0.0"
description: "Building envelope plan semantic analysis for development constraints"
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
output_parser: BuildingEnvelopePlanSemantics
tags: ["building_envelope", "development", "setbacks", "constraints"]
---

# Building Envelope Plan Analysis - {{ australian_state }}

You are analyzing a **building envelope plan** for an Australian property. Extract comprehensive development constraint information and allowable building areas following the BuildingEnvelopePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Building Envelope Plan
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
- `"label"` - For envelope labels, area names, plan references
- `"measurement"` - For dimensions, areas, distances, heights
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
- `"residential"` - Residential buildings
- `"commercial"` - Commercial buildings
- `"industrial"` - Industrial buildings
- `"mixed_use"` - Mixed use buildings
- `"other"` - Any other building type

### Envelope Type (envelope_type)
For `building_elements.envelope_type`, use ONLY these values:
- `"buildable"` - Buildable areas
- `"restricted"` - Restricted building areas
- `"setback"` - Setback areas
- `"other"` - Any other envelope type

### Relationship Type (relationship_type)
For `spatial_relationships.relationship_type`, use ONLY these values:
- `"adjacent"` - Elements next to each other
- `"above"` - One element above another
- `"below"` - One element below another
- `"under"` - One element underneath another
- `"crosses"` - Elements that cross or intersect paths
- `"intersects"` - Elements that intersect or overlap boundaries
- `"connected_to"` - Elements that are connected
- `"overlaps"` - Elements that partially overlap
- `"parallel"` - Elements that run parallel to each other
- `"perpendicular"` - Elements that meet at right angles
- `"near"` - Elements in close proximity
- `"far"` - Elements at a distance
- `"within"` - One element contained within another
- `"other"` - Any other spatial relationship

**CRITICAL: Do not invent new enum values. If unsure, use "other" or the most appropriate existing value.**

## Building Envelope Plan Analysis Objectives

### 1. Building Elements (building_elements)
**Document building envelope constraints:**
- **Building type**: "envelope_boundary", "setback_line", "height_plane", "building_area"
- **Construction stage**: allowable future construction within envelope
- **Height restrictions**: maximum building heights within envelope
- **Setback requirements**: required setbacks from all boundaries
- **Building envelope**: three-dimensional allowable building space

### 2. Boundary Elements (boundary_elements)
**Map property boundaries affecting envelope:**
- **Boundary type**: property boundaries that define envelope constraints
- **Boundary markings**: survey marks and boundary definitions
- **Dimensions**: precise boundary measurements and setback distances
- **Encroachments**: existing structures within setback areas
- **Easements**: easements affecting building envelope

### 3. Building Envelope Specific Fields

#### Setback Requirements (setback_requirements)
Document all mandatory setback distances:
- **Front Setbacks**: Minimum distances from front boundary
- **Rear Setbacks**: Minimum distances from rear boundary
- **Side Setbacks**: Minimum distances from side boundaries
- **Secondary Street Setbacks**: Setbacks from secondary street frontages
- **Watercourse Setbacks**: Setbacks from creeks, rivers, or drainage
- **Easement Setbacks**: Additional setbacks from easement boundaries

#### Height Limits (height_limits)
Map building height restrictions:
- **Maximum Building Height**: Overall height limits (meters/storeys)
- **Height Planes**: Angled height restrictions from boundaries
- **Roof Height Limits**: Restrictions on roof form and pitch
- **Chimney/Plant Height**: Limits on building services and equipment
- **Heritage Height Restrictions**: Special height limits in heritage areas

#### Floor Area Ratio (floor_area_ratio)
Document floor space limitations:
- **Maximum FSR**: Floor space ratio limitations
- **Gross Floor Area**: Total allowable building floor area
- **Bonus FSR Provisions**: Additional floor space for design excellence
- **Non-Contributory Areas**: Areas excluded from FSR calculations
- **FSR Calculation Methods**: How floor area is measured and calculated

#### Coverage Limits (coverage_limits)
Identify site coverage restrictions:
- **Maximum Site Coverage**: Percentage of site that can be built on
- **Building Footprint Limits**: Ground floor building area restrictions
- **Impervious Surface Limits**: Total hard surface area restrictions
- **Landscaping Requirements**: Minimum soft landscaping percentages
- **Private Open Space**: Required outdoor space per dwelling

#### Buildable Area (buildable_area)
Define allowable construction zones:
- **Primary Building Area**: Main building construction zone
- **Secondary Building Area**: Ancillary building areas (garages, sheds)
- **No-Build Zones**: Areas where construction is prohibited
- **Restricted Building Areas**: Areas with special building requirements
- **Basement/Underground Areas**: Below-ground construction allowances

## Development Assessment

### Envelope Compliance
Evaluate existing building compliance:
- **Current Building Compliance**: Existing structures within envelope
- **Non-Conforming Elements**: Buildings exceeding current envelope
- **Existing Use Rights**: Grandfathered non-compliant buildings
- **Expansion Potential**: Ability to extend existing non-conforming buildings
- **Replacement Rights**: Rights to rebuild non-conforming structures

### Development Potential
Assess future development opportunities:
- **Additional Floor Area**: Remaining development capacity
- **Dwelling Potential**: Number of additional dwellings possible
- **Commercial Development**: Commercial floor space potential
- **Renovation Opportunities**: Modification and extension potential
- **Subdivision Impact**: Effect of potential subdivision on envelope

### Design Considerations
Evaluate building design constraints:
- **Solar Access Requirements**: Overshadowing restrictions
- **Privacy Requirements**: Window and balcony placement restrictions
- **Acoustic Requirements**: Noise mitigation building placement
- **Energy Efficiency**: Building orientation and design requirements
- **Accessibility Requirements**: Disabled access and circulation

## {{ australian_state }} Building Envelope Standards

{% if australian_state == "NSW" %}
**NSW Building Envelope Controls:**
- Check Local Environment Plan (LEP) building height and FSR controls
- Note State Environmental Planning Policy (SEPP) design requirements
- Identify Apartment Design Guide compliance requirements
- Check for Design Excellence provisions
{% elif australian_state == "VIC" %}
**VIC Building Envelope Controls:**
- Verify Planning Scheme height and setback controls
- Check ResCode multi-dwelling design requirements
- Note Better Apartments Design Standards compliance
- Identify clause 55/56 design response requirements
{% elif australian_state == "QLD" %}
**QLD Building Envelope Controls:**
- Check Planning Scheme building height and setback controls
- Note State Planning Policy design requirements
- Identify Queensland Development Code requirements
- Check for Neighbourhood Character overlays
{% endif %}

## Risk Assessment Focus

### Critical Envelope Risks
1. **Non-Compliant Buildings**: Existing buildings exceeding envelope controls
2. **Limited Development Potential**: Minimal remaining building capacity
3. **Complex Setback Requirements**: Multiple conflicting setback controls
4. **Height Plane Conflicts**: Building heights affected by angled restrictions
5. **FSR Exhaustion**: Site already at maximum floor area ratio
6. **Infrastructure Constraints**: Services limiting development potential

### Development Economics
Assess financial implications:
- Development yield and return on investment
- Construction cost implications of envelope constraints
- Market value impact of development restrictions
- Holding costs during development approval process

## Output Requirements

Return a valid JSON object following the **BuildingEnvelopePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "building_envelope_plan"
- `textual_information`: All envelope labels and measurements
- `spatial_relationships`: Building envelope and boundary interactions
- `semantic_summary`: Development constraint overview
- `property_impact_summary`: Development potential and limitations
- `key_findings`: Critical envelope discoveries
- `areas_of_concern`: Development constraint issues
- `analysis_confidence`: Overall confidence level

### Building Envelope Specific Fields
- `building_elements`: Building envelope constraint elements
- `boundary_elements`: Property boundaries affecting development
- `setback_requirements`: All mandatory setback distances
- `height_limits`: Building height restriction areas
- `floor_area_ratio`: Floor space ratio limitations
- `coverage_limits`: Site coverage percentage restrictions
- `buildable_area`: Allowable construction zone definitions

### Quality Standards
- **Measurement Precision**: Exact setback and height measurements
- **Development Focus**: Emphasize building potential and constraints
- **Compliance Assessment**: Check existing building envelope compliance
- **Economic Analysis**: Consider development feasibility and returns
- **Design Integration**: Assess building design opportunities and limitations

Begin analysis now. Return only the structured JSON output following the BuildingEnvelopePlanSemantics schema.
