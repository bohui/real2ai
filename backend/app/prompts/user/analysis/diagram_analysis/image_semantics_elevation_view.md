---
type: "user"
category: "instructions"
name: "image_semantics_elevation_view"
version: "1.0.0"
description: "Elevation view semantic analysis for building facade and external appearance"
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
output_parser: ElevationViewSemantics
tags: ["elevation", "facade", "appearance", "design"]
---

# Elevation View Analysis - {{ australian_state }}

You are analyzing an **elevation view** for an Australian property. Extract comprehensive building facade and external appearance information following the ElevationViewSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Elevation View
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
- `"label"` - For elevation labels, feature names, plan references
- `"measurement"` - For heights, dimensions, distances, levels
- `"title"` - For main headings, elevation titles, section headers
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

### Elevation Type (elevation_type)
For `building_elements.elevation_type`, use ONLY these values:
- `"front"` - Front elevation
- `"rear"` - Rear elevation
- `"side"` - Side elevation
- `"other"` - Any other elevation type

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Elevation View Analysis Objectives

### 1. Building Elements (building_elements)
**Document building facades and external features:**
- **Building type**: "facade", "wall", "roof", "feature", "opening"
- **Construction stage**: existing or proposed building facade elements
- **Height restrictions**: building height and facade proportions
- **Setback requirements**: building placement and street alignment
- **Building envelope**: facade design and building form

### 2. Elevation View Specific Fields

#### Facade Treatments (facade_treatments)
Document building facade materials and treatments:
- **Wall Materials**: Brick, render, cladding, stone, concrete materials
- **Roof Materials**: Tile, metal, membrane, slate roofing materials
- **Window Types**: Casement, sliding, double-hung, fixed window types
- **Door Types**: Entry doors, garage doors, sliding doors
- **Architectural Features**: Balconies, verandas, awnings, pergolas
- **Color Schemes**: External color palette and material combinations

#### Height Relationships (height_relationships)
Assess building height relationships to surroundings:
- **Building Heights**: Overall building height and storey numbers
- **Neighboring Buildings**: Height relationships to adjacent buildings
- **Street Relationship**: Building height relationship to street scale
- **Setback Heights**: Height at different setback distances
- **Roof Heights**: Ridge heights and roof peak elevations
- **Parapet Heights**: Flat roof parapet and balustrade heights

#### Architectural Features (architectural_features)
Identify significant architectural features:
- **Design Style**: Contemporary, traditional, heritage, modern architectural style
- **Proportions**: Window-to-wall ratios, floor height proportions
- **Symmetry**: Facade symmetry and compositional balance
- **Articulation**: Facade depth, shadow lines, and surface modulation
- **Feature Elements**: Chimneys, dormers, bay windows, architectural details
- **Entrance Design**: Main entry design and prominence

#### Material Specifications (material_specifications)
Document external material specifications:
- **Wall Construction**: Material types, finishes, and construction methods
- **Roof Construction**: Roofing materials and installation methods
- **Window Specifications**: Window materials, glazing, and hardware
- **Door Specifications**: Door materials, hardware, and security features
- **Balcony Materials**: Balcony decking, balustrades, and structural materials
- **Landscape Materials**: Hard landscaping materials and finishes

#### Visual Impact (visual_impact)
Assess visual impact on streetscape and neighbors:
- **Streetscape Character**: Contribution to street character and consistency
- **Neighbor Impact**: Visual impact on neighboring properties
- **Bulk and Scale**: Building mass and scale appropriateness
- **Privacy Impact**: Windows and balconies affecting neighbor privacy
- **Shadow Impact**: Building shadow effects on neighbors and public areas
- **View Impact**: Building impact on existing views and vistas

## Design Assessment

### Architectural Quality
Evaluate architectural design quality:
- **Design Coherence**: Consistency and integration of design elements
- **Material Appropriateness**: Suitability of materials for climate and use
- **Proportion and Scale**: Appropriateness of building proportions
- **Detail Quality**: Quality and execution of architectural details
- **Innovation**: Creative or innovative design approaches
- **Sustainability**: Passive solar design and environmental responsiveness

### Planning Compliance
Assess planning and design compliance:
- **Height Compliance**: Building height compliance with planning controls
- **Setback Compliance**: Building setback compliance from boundaries
- **Character Compliance**: Consistency with neighborhood character
- **Design Guidelines**: Compliance with local design guidelines
- **Heritage Compatibility**: Appropriateness in heritage contexts
- **Accessibility**: Universal design and accessibility provisions

### Construction Feasibility
Evaluate construction and maintenance considerations:
- **Construction Complexity**: Ease of construction and detailing
- **Material Durability**: Long-term performance of selected materials
- **Maintenance Requirements**: Ongoing maintenance needs and access
- **Weather Protection**: Building protection from weather elements
- **Thermal Performance**: Building thermal efficiency and comfort
- **Cost Implications**: Construction and lifecycle cost considerations

## {{ australian_state }} Design Standards

{% if australian_state == "NSW" %}
**NSW Design Requirements:**
- Check Local Environment Plan design provisions
- Note State Environmental Planning Policy design requirements
- Identify Apartment Design Guide compliance (if applicable)
- Check for heritage area design guidelines
{% elif australian_state == "VIC" %}
**VIC Design Requirements:**
- Verify Planning Scheme design provisions
- Check ResCode multi-dwelling design standards
- Note Better Apartments Design Standards (if applicable)
- Identify neighborhood character overlays
{% elif australian_state == "QLD" %}
**QLD Design Requirements:**
- Check Planning Scheme design provisions
- Note Queensland Development Code requirements
- Identify character area overlays
- Check for subtropical design considerations
{% endif %}

## Risk Assessment Focus

### Critical Design Risks
1. **Planning Non-Compliance**: Building design not meeting planning requirements
2. **Neighbor Opposition**: Design causing neighbor objections or disputes
3. **Construction Complexity**: Difficult or expensive construction details
4. **Material Performance**: Poor material selection for climate or use
5. **Maintenance Issues**: High maintenance or difficult access requirements
6. **Heritage Conflicts**: Inappropriate design in heritage areas

### Design Opportunities
Assess positive design aspects:
- Enhanced property value from quality design
- Energy efficiency and environmental performance
- Lifestyle benefits from design features
- Competitive advantage in property market

## Output Requirements

Return a valid JSON object following the **ElevationViewSemantics** schema with:

### Required Base Fields
- `image_type`: "elevation_view"
- `textual_information`: All facade labels and material annotations
- `spatial_relationships`: Facade element relationships
- `semantic_summary`: Building facade overview
- `property_impact_summary`: Design and compliance implications
- `key_findings`: Critical elevation discoveries
- `areas_of_concern`: Design compliance or construction issues
- `analysis_confidence`: Overall confidence level

### Elevation View Specific Fields
- `building_elements`: Building facades and external features
- `facade_treatments`: Building facade materials and treatments
- `height_relationships`: Height relationships to surroundings
- `architectural_features`: Significant architectural features
- `material_specifications`: External material specifications
- `visual_impact`: Visual impact on streetscape and neighbors

### Quality Standards
- **Design Analysis**: Comprehensive architectural design assessment
- **Compliance Focus**: Planning and building code compliance evaluation
- **Construction Assessment**: Buildability and maintenance consideration
- **Visual Impact**: Streetscape and neighbor impact evaluation
- **Market Analysis**: Design appropriateness for target market

Begin analysis now. Return only the structured JSON output following the ElevationViewSemantics schema.
