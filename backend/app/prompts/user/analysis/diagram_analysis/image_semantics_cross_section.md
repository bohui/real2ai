---
type: "user"
category: "instructions"
name: "image_semantics_cross_section"
version: "1.0.0"
description: "Cross section semantic analysis for vertical building and site analysis"
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
output_parser: CrossSectionSemantics
tags: ["cross_section", "vertical", "structure", "subsurface"]
---

# Cross Section Analysis - {{ australian_state }}

You are analyzing a **cross section diagram** for an Australian property. Extract comprehensive vertical building and site information following the CrossSectionSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Cross Section
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
- `"label"` - For section labels, layer names, plan references
- `"measurement"` - For depths, heights, distances, thicknesses
- `"title"` - For main headings, section titles, headers
- `"legend"` - For map keys, symbols, abbreviations
- `"note"` - For explanatory text, legal statements, conditions
- `"warning"` - For cautionary text, important notices
- `"other"` - For any text that doesn't fit the above categories

### Confidence Level (analysis_confidence)
For `analysis_confidence`, use ONLY these values:
- `"high"` - When analysis is comprehensive and confident
- `"medium"` - When analysis has some uncertainty
- `"low"` - When analysis has significant limitations

### Environmental Type (environmental_type)
For `environmental_elements.environmental_type`, use ONLY these values:
- `"soil"` - Soil layers
- `"rock"` - Rock layers
- `"water"` - Water table or aquifers
- `"vegetation"` - Vegetation layers
- `"other"` - Any other environmental feature

### Layer Type (layer_type)
For `environmental_elements.layer_type`, use ONLY these values:
- `"surface"` - Surface layers
- `"subsurface"` - Subsurface layers
- `"bedrock"` - Bedrock layers
- `"other"` - Any other layer type

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

## Cross Section Analysis Objectives

### 1. Building Elements (building_elements)
**Document building elements shown in cross-section:**
- **Building type**: "foundation", "structure", "floor", "roof", "basement"
- **Construction stage**: existing or proposed building elements
- **Height restrictions**: floor heights and ceiling clearances
- **Setback requirements**: building placement relative to boundaries
- **Building envelope**: internal space configuration and layout

### 2. Environmental Elements (environmental_elements)
**Map ground conditions and environmental layers:**
- **Environmental type**: "soil_layer", "rock_formation", "groundwater", "fill"
- **Risk level**: geotechnical and environmental stability
- **Impact area**: areas affected by ground conditions
- **Mitigation measures**: required foundation or ground treatment

### 3. Cross Section Specific Fields

#### Elevation Profile (elevation_profile)
Document elevation changes along the section line:
- **Ground Surface Levels**: Natural ground elevation profile
- **Finished Floor Levels**: Building floor elevations (RL)
- **Ceiling Heights**: Internal floor to ceiling dimensions
- **Roof Levels**: Ridge heights and roof profile elevations
- **Basement Levels**: Below-ground floor elevations
- **External Levels**: Paving, landscaping, and external surface levels

#### Subsurface Conditions (subsurface_conditions)
Map subsurface conditions and soil layers:
- **Soil Types**: Clay, sand, rock, fill, organic soils
- **Soil Layers**: Stratification and layer boundaries
- **Rock Formations**: Bedrock depth and rock type
- **Groundwater**: Water table levels and seasonal variations
- **Fill Materials**: Engineered fill or uncontrolled fill
- **Contamination**: Any indicated soil or groundwater contamination

#### Structural Elements (structural_elements)
Identify structural elements and construction details:
- **Foundation Systems**: Footings, piers, piles, slabs
- **Structural Frame**: Beams, columns, load-bearing walls
- **Floor Systems**: Floor structures and construction methods
- **Roof Structure**: Roof framing and construction systems
- **Retaining Structures**: Retaining walls and earth retention
- **Waterproofing**: Basement and below-ground waterproofing

#### Vertical Relationships (vertical_relationships)
Document vertical relationships between elements:
- **Floor Level Relationships**: Level differences between spaces
- **Headroom Clearances**: Adequate ceiling heights and clearances
- **Service Clearances**: Space for mechanical services and utilities
- **Access Relationships**: Stairs, lifts, and vertical circulation
- **Foundation Relationships**: Building foundations to soil conditions
- **Drainage Relationships**: Surface and subsurface drainage

#### Construction Challenges (construction_challenges)
Identify construction challenges revealed by section:
- **Excavation Requirements**: Depth and extent of required excavation
- **Shoring Requirements**: Temporary earth support during construction
- **Dewatering Needs**: Groundwater control during construction
- **Access Difficulties**: Construction access and equipment limitations
- **Soil Stability Issues**: Poor soil conditions requiring treatment
- **Rock Excavation**: Hard rock requiring special excavation methods

## Technical Analysis Objectives

### Geotechnical Assessment
Evaluate foundation and soil conditions:
- **Bearing Capacity**: Soil bearing capacity for foundations
- **Settlement Risk**: Potential for differential or excessive settlement
- **Slope Stability**: Cut and fill slope stability
- **Groundwater Impact**: Effects of groundwater on construction and use
- **Soil Movement**: Potential for shrink-swell or expansive soils

### Structural Analysis
Assess structural design and adequacy:
- **Load Paths**: Structural load transfer to foundations
- **Span Adequacy**: Floor and roof span capabilities
- **Height Compliance**: Floor height compliance with building codes
- **Structural Integration**: Coordination between different structural elements
- **Seismic Considerations**: Earthquake resistance and structural connections

### Building Services Integration
Evaluate services integration:
- **Service Routing**: Space for mechanical, electrical, plumbing services
- **Vertical Services**: Lift shafts, stair wells, service risers
- **Floor Penetrations**: Openings for services through floors
- **Ceiling Space**: Adequate ceiling space for services and access
- **Plant Room Access**: Access to mechanical plant and equipment

## Output Requirements

Return a valid JSON object following the **CrossSectionSemantics** schema with:

### Required Base Fields
- `image_type`: "cross_section"
- `textual_information`: All section labels and level annotations
- `spatial_relationships`: Vertical element relationships
- `semantic_summary`: Cross section overview
- `property_impact_summary`: Construction and design implications
- `key_findings`: Critical cross section discoveries
- `areas_of_concern`: Structural or construction issues
- `analysis_confidence`: Overall confidence level

### Cross Section Specific Fields
- `building_elements`: Building elements shown in cross-section
- `environmental_elements`: Ground conditions and environmental layers
- `elevation_profile`: Elevation changes along section line
- `subsurface_conditions`: Subsurface conditions and soil layers
- `structural_elements`: Structural elements and construction details
- `vertical_relationships`: Vertical relationships between elements
- `construction_challenges`: Construction challenges revealed by section

### Quality Standards
- **Technical Accuracy**: Precise structural and geotechnical analysis
- **Construction Focus**: Emphasize buildability and construction challenges
- **Code Compliance**: Check building code compliance for heights and clearances
- **Integration Assessment**: Evaluate coordination between building systems
- **Risk Identification**: Identify geotechnical and structural risks

Begin analysis now. Return only the structured JSON output following the CrossSectionSemantics schema.
