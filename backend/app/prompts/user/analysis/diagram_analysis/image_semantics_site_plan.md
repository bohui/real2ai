---
type: "user"
category: "instructions"
name: "image_semantics_site_plan"
version: "1.0.0"
description: "Site plan semantic analysis for property layout and boundaries"
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
output_parser: SitePlanSemantics
tags: ["site_plan", "boundaries", "building", "layout"]
---

# Site Plan Analysis - {{ australian_state }}

You are analyzing a **site plan** for an Australian property. Extract comprehensive semantic information focusing on property layout, building placement, and site infrastructure following the SitePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Site Plan
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
- `"label"` - For lot numbers, street names, plan references
- `"measurement"` - For dimensions, distances, areas, bearings
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

### Boundary Type (boundary_type)
For `boundary_elements.boundary_type`, use ONLY these values:
- `"front"` - Front boundary of the property
- `"rear"` - Rear boundary of the property
- `"side"` - Side boundaries of the property
- `"common"` - Common boundaries with other properties

### Building Type (building_type)
For `building_elements.building_type`, use ONLY these values:
- `"house"` - Main residential building
- `"garage"` - Garage or carport structure
- `"shed"` - Storage or utility building
- `"pool"` - Swimming pool or spa
- `"deck"` - Outdoor deck or patio
- `"carport"` - Covered parking area
- `"other"` - Any other building type

### Infrastructure Type (infrastructure_type)
For `infrastructure_elements.infrastructure_type`, use ONLY these values:
- `"road"` - Road infrastructure
- `"sewer"` - Sewerage infrastructure
- `"water"` - Water supply infrastructure
- `"stormwater"` - Drainage infrastructure
- `"power"` - Electrical infrastructure
- `"telecommunications"` - Communication infrastructure

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

## Site Plan Analysis Objectives

### 1. Property Boundaries (boundary_elements)
**Extract all boundary information:**
- **Boundary type**: front, rear, side, common
- **Boundary markings**: fences, walls, survey pegs, natural features
- **Dimensions**: length measurements, angles, setbacks
- **Encroachments**: any structures crossing boundary lines
- **Easements**: location, width, purpose, beneficiary parties

**For each boundary element:**
```json
{
  "element_type": "boundary",
  "boundary_type": "front|rear|side|common",
  "boundary_marking": "fence|wall|survey_peg|natural_feature",
  "dimensions": "measurement with units",
  "encroachments": ["list of crossing structures"],
  "easements": ["easement descriptions"]
}
```

### 2. Building Elements (building_elements)
**Identify all structures:**
- **Building type**: house, garage, shed, pool, deck, carport
- **Construction stage**: existing, proposed, under construction
- **Height restrictions**: maximum heights, storey limits
- **Setback requirements**: distances from all boundaries
- **Building envelope**: allowable construction areas

**For each building element:**
```json
{
  "element_type": "building",
  "building_type": "specific building type",
  "construction_stage": "existing|proposed|under_construction",
  "height_restrictions": "height limits if shown",
  "setback_requirements": "setback distances",
  "building_envelope": "envelope constraints"
}
```

### 3. Site Infrastructure (infrastructure_elements)
**Document site utilities and access:**
- **Infrastructure type**: driveway, path, utilities, drainage
- **Location**: position relative to buildings and boundaries
- **Specifications**: materials, dimensions, gradients
- **Access points**: vehicle and pedestrian entry points
- **Service connections**: utility connection locations

### 4. Site-Specific Fields

#### Lot Dimensions (lot_dimensions)
Extract overall site measurements:
- Total lot area (if shown)
- Frontage width and depth
- Overall lot shape and orientation

#### Building Setbacks (building_setbacks)
Document all setback requirements:
- Front setback distances
- Rear setback requirements  
- Side setback minimums
- Corner setback rules (if applicable)

#### Access Points (access_points)
Identify all access arrangements:
- Vehicle access from street
- Pedestrian access points
- Emergency vehicle access
- Service vehicle access

#### Parking Areas (parking_areas)
Map all parking provisions:
- Covered parking (garage, carport)
- Open parking spaces
- Visitor parking areas
- Loading/service areas

## Spatial Analysis Requirements

### Location Referencing
- Use normalized coordinates (0-1 scale) for all elements
- Reference positions to lot boundaries and existing structures
- Note cardinal directions and orientation

### Measurement Extraction
- Extract ALL visible dimensions and measurements
- Note scale bars and measurement units
- Calculate missing dimensions where possible
- Flag incomplete or unclear measurements

### Text Analysis
- Extract all text labels, lot numbers, street names
- Identify technical annotations and notes
- Note handwritten modifications or additions
- Preserve planning reference numbers

## {{ australian_state }} Compliance Focus

{% if australian_state == "NSW" %}
**NSW Requirements:**
- Check compliance with DCP setback requirements
- Note any heritage overlay constraints
- Identify BASIX requirements implications
- Check for coastal hazard considerations
{% elif australian_state == "VIC" %}
**VIC Requirements:**
- Verify ResCode setback compliance
- Check sustainable design orientation
- Note native vegetation constraints
- Identify any overlay requirements
{% elif australian_state == "QLD" %}
**QLD Requirements:**
- Check State Planning Policy compliance
- Note character area overlay requirements
- Identify any koala habitat constraints
- Check for state transport corridor impacts
{% endif %}

## Risk Assessment Priorities

### Critical Site Plan Risks
1. **Setback Non-Compliance**: Buildings too close to boundaries
2. **Access Adequacy**: Insufficient vehicle or emergency access
3. **Building Envelope Violations**: Structures outside allowable areas
4. **Easement Conflicts**: Buildings or improvements over easements
5. **Parking Shortfall**: Insufficient parking for dwelling requirements
6. **Site Coverage Excess**: Buildings covering too much of the lot

### Evidence Requirements
For each risk identified:
- Reference specific measurements or labels
- Note relevant planning standards
- Cite any conflicting information
- Suggest verification requirements

## Output Requirements

Return a valid JSON object following the **SitePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "site_plan"
- `textual_information`: All extracted text with locations
- `spatial_relationships`: Element interactions and conflicts
- `semantic_summary`: High-level site layout description
- `property_impact_summary`: Development implications
- `key_findings`: Most significant discoveries
- `areas_of_concern`: Issues requiring attention
- `analysis_confidence`: Overall confidence level

### Site Plan Specific Fields
- `boundary_elements`: Complete boundary analysis
- `building_elements`: All structures and buildings
- `infrastructure_elements`: Site utilities and access
- `lot_dimensions`: Overall site measurements
- `building_setbacks`: All setback requirements
- `access_points`: Access and circulation
- `parking_areas`: Parking provisions

### Quality Standards
- **Completeness**: Every visible element identified
- **Accuracy**: Only information clearly visible in the plan
- **Measurements**: All dimensions extracted with units
- **Compliance**: Reference relevant planning standards
- **Risk Focus**: Emphasize development constraints

Begin analysis now. Return only the structured JSON output following the SitePlanSemantics schema.
