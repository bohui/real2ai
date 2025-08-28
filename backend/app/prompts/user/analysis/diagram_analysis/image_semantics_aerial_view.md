---
type: "user"
category: "instructions"
name: "image_semantics_aerial_view"
version: "1.0.0"
description: "Aerial view semantic analysis for contextual property assessment"
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
output_parser: AerialViewSemantics
tags: ["aerial", "context", "surroundings", "satellite"]
---

# Aerial View Analysis - {{ australian_state }}

You are analyzing an **aerial view** for an Australian property. Extract comprehensive contextual information about the property and its surroundings following the AerialViewSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Aerial View
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
- `"label"` - For area labels, feature names, plan references
- `"measurement"` - For dimensions, areas, distances, scales
- `"title"` - For main headings, image titles, section headers
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

### Environmental Type (environmental_type)
For `environmental_elements.environmental_type`, use ONLY these values:
- `"vegetation"` - Natural vegetation areas
- `"water_body"` - Water bodies
- `"open_space"` - Open space areas
- `"developed"` - Developed areas
- `"other"` - Any other environmental feature

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

## Aerial View Analysis Objectives

### 1. Building Elements (building_elements)
**Identify buildings and structures visible from above:**
- **Building type**: "house", "apartment", "commercial", "industrial", "infrastructure"
- **Construction stage**: existing buildings and development progress
- **Height restrictions**: relative building heights and scale
- **Setback requirements**: actual building placement and spacing
- **Building envelope**: building footprints and site utilization

### 2. Environmental Elements (environmental_elements)
**Map natural and environmental features:**
- **Environmental type**: "vegetation", "water_feature", "topography", "coastal"
- **Risk level**: environmental constraints and opportunities
- **Impact area**: environmental feature extent and boundaries
- **Mitigation measures**: visible environmental protection measures

### 3. Infrastructure Elements (infrastructure_elements)
**Document visible infrastructure from aerial perspective:**
- **Infrastructure type**: "road", "rail", "utility", "recreational"
- **Condition assessment**: visible infrastructure condition
- **Capacity indicators**: scale and adequacy of infrastructure
- **Connectivity**: infrastructure networks and connections
- **Access quality**: vehicle and pedestrian access arrangements

### 4. Aerial View Specific Fields

#### Site Context (site_context)
Assess surrounding area characteristics:
- **Land Use Patterns**: Residential, commercial, industrial, rural land uses
- **Development Density**: Low, medium, high density development patterns
- **Street Patterns**: Grid, curvilinear, cul-de-sac street layouts
- **Block Sizes**: Typical lot sizes and subdivision patterns
- **Zoning Transitions**: Changes between different land use zones
- **Growth Patterns**: Evidence of recent or planned development

#### Access Visibility (access_visibility)
Evaluate access and circulation from aerial view:
- **Road Hierarchy**: Main roads, local streets, private drives
- **Public Transport**: Bus routes, railway lines, stations visible
- **Pedestrian Networks**: Footpaths, cycleways, pedestrian connections
- **Parking Arrangements**: Street parking, driveways, parking lots
- **Emergency Access**: Fire service access and emergency vehicle routes
- **Service Access**: Garbage collection, delivery vehicle access

#### Neighboring Developments (neighboring_developments)
Analyze adjacent and nearby properties:
- **Property Types**: Surrounding property characteristics and uses
- **Building Styles**: Architectural styles and development periods
- **Maintenance Standards**: Property maintenance and presentation levels
- **Development Activity**: Construction activity or redevelopment
- **Vacant Land**: Undeveloped land and development potential
- **Incompatible Uses**: Potentially conflicting neighboring land uses

#### Natural Features (natural_features)
Document natural landscape elements:
- **Topography**: Hills, valleys, flat areas, elevation changes
- **Vegetation**: Tree coverage, parks, bushland, agricultural areas
- **Water Features**: Rivers, creeks, dams, coastal areas
- **Soil Conditions**: Visible soil types, erosion, stability issues
- **Drainage Patterns**: Natural drainage and stormwater flow
- **Environmental Corridors**: Wildlife corridors and habitat connections

#### Urban Fabric (urban_fabric)
Assess overall urban development patterns:
- **Development Age**: Historic vs contemporary development areas
- **Subdivision Patterns**: Regular vs irregular lot layouts
- **Infrastructure Integration**: How well infrastructure serves development
- **Open Space Distribution**: Parks, reserves, recreational facilities
- **Commercial Centers**: Shopping centers, business districts
- **Community Facilities**: Schools, hospitals, community centers

## Contextual Assessment

### Location Quality
Evaluate property location advantages:
- **Accessibility**: Proximity to transport and major roads
- **Amenity Access**: Distance to shops, schools, services
- **Environmental Quality**: Natural features and landscape quality
- **Neighborhood Character**: Established vs developing area character
- **Future Development**: Potential for area improvement or deterioration

### Visual Impact Assessment
Analyze visual amenity factors:
- **Views and Outlook**: Quality of views from property
- **Privacy Levels**: Visual privacy from neighboring properties
- **Noise Sources**: Visible noise sources (roads, industry, airports)
- **Visual Barriers**: Trees, fences, buildings affecting views
- **Aesthetic Quality**: Overall visual appeal of surrounding area

### Risk Identification
Identify contextual risks from aerial view:
- **Flood Risk**: Low-lying areas, proximity to water features
- **Bushfire Risk**: Vegetation proximity and fire access
- **Infrastructure Constraints**: Overhead power lines, easements
- **Development Pressure**: Areas under development pressure
- **Environmental Constraints**: Protected areas, steep slopes

## Output Requirements

Return a valid JSON object following the **AerialViewSemantics** schema with:

### Required Base Fields
- `image_type`: "aerial_view"
- `textual_information`: Any visible labels or annotations
- `spatial_relationships`: Property relationships to surrounding features
- `semantic_summary`: Aerial view contextual overview
- `property_impact_summary`: How surrounding context affects property
- `key_findings`: Critical contextual discoveries
- `areas_of_concern`: Contextual risks or issues
- `analysis_confidence`: Overall confidence level

### Aerial View Specific Fields
- `building_elements`: Visible buildings and structures
- `environmental_elements`: Natural and environmental features
- `infrastructure_elements`: Visible infrastructure from aerial perspective
- `site_context`: Surrounding area land use and development patterns
- `access_visibility`: Access routes and transportation connections
- `neighboring_developments`: Adjacent property characteristics
- `natural_features`: Landscape and environmental elements
- `urban_fabric`: Overall urban development patterns

### Quality Standards
- **Contextual Accuracy**: Accurate assessment of surrounding area
- **Scale Assessment**: Appropriate evaluation of relative sizes and distances
- **Pattern Recognition**: Identification of development and land use patterns
- **Risk Focus**: Emphasize contextual factors affecting property value
- **Opportunity Identification**: Recognize positive contextual factors

Begin analysis now. Return only the structured JSON output following the AerialViewSemantics schema.
