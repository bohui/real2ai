---
type: "user"
category: "instructions"
name: "image_semantics_flood_map"
version: "1.0.0"
description: "Flood map semantic analysis for water risk assessment"
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
output_parser: FloodMapSemantics
tags: ["flood", "water", "risk", "environmental"]
---

# Flood Map Analysis - {{ australian_state }}

You are analyzing a **flood map** for an Australian property. Extract comprehensive flood risk information, water levels, and mitigation requirements following the FloodMapSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Flood Map
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
- `"label"` - For zone labels, area names, plan references
- `"measurement"` - For flood levels, distances, areas, elevations
- `"title"` - For main headings, map titles, section headers
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
- `"flood_zone"` - Flood-prone areas
- `"water_body"` - Rivers, creeks, lakes
- `"drainage"` - Stormwater drainage features
- `"vegetation"` - Natural vegetation areas
- `"other"` - Any other environmental feature

### Risk Level (risk_level)
For `risk_indicators.risk_level`, use ONLY these values:
- `"high"` - High flood risk areas
- `"medium"` - Medium flood risk areas
- `"low"` - Low flood risk areas
- `"minimal"` - Minimal flood risk areas

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Flood Map Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map all flood-related features:**
- **Environmental type**: "flood_zone", "water_feature", "drainage", "wetland"
- **Risk level**: low, medium, high, extreme
- **Impact area**: affected zones and their extent
- **Mitigation measures**: existing flood protection measures

### 2. Flood-Specific Fields

#### Flood Zones (flood_zones)
Identify all flood risk classifications:
- **Flood Planning Areas (FPA)**: 1:100 year flood zones
- **Flood Planning Levels (FPL)**: specific water levels
- **High Hazard Areas**: dangerous flood zones
- **Flood Fringe Areas**: lower risk flood zones
- **Probable Maximum Flood (PMF)**: extreme flood extents

#### Water Levels (water_levels)
Extract flood level information:
- Australian Height Datum (AHD) levels
- Design flood levels for different return periods
- Freeboard requirements above flood levels
- Historic flood level markers
- Minimum floor level requirements

#### Escape Routes (escape_routes)
Map emergency access and evacuation:
- Emergency evacuation routes
- Safe refuge areas above flood levels
- Emergency vehicle access during floods
- Community evacuation centers
- Warning system locations

#### Flood Mitigation (flood_mitigation)
Document flood protection measures:
- Levees and flood walls
- Stormwater detention basins
- Flood gates and barriers
- Pumping stations
- Early warning systems

## Flood Risk Assessment

### Flood Hazard Classification
Analyze flood hazard factors:
- **Depth**: water depth during design flood
- **Velocity**: water flow velocity
- **Hazard Category**: H1-H6 classification
- **Hydraulic Category**: floodway vs flood storage
- **Duration**: flood duration estimates

### Property Impact Analysis
Assess specific property risks:
- **Building Risk**: structures within flood zones
- **Access Risk**: road/driveway flooding impacts
- **Infrastructure Risk**: utilities affected by flooding
- **Insurance Implications**: flood insurance requirements
- **Development Restrictions**: flood-related building controls

### Flood Planning Requirements
Document planning constraints:
- **Fill Requirements**: minimum fill levels
- **Building Design**: flood-resistant construction
- **Evacuation Plans**: emergency procedures
- **Development Applications**: flood impact assessments
- **Council Requirements**: specific local flood controls

## Technical Flood Analysis Objectives

### Hydrological Data
Extract water flow information:
- **Catchment Areas**: upstream water sources
- **Flow Directions**: water movement patterns
- **Discharge Rates**: peak flood flows
- **Return Periods**: 1:10, 1:100, 1:500 year events
- **Climate Change**: future flood projections

### Flood Modeling Results
Document flood study findings:
- **Model Type**: 1D, 2D, or coupled flood models
- **Flood Study Date**: currency of flood information
- **Study Authority**: responsible flood authority
- **Model Accuracy**: confidence levels in predictions
- **Validation Data**: historic flood verification

## {{ australian_state }} Flood Requirements

{% if australian_state == "NSW" %}
**NSW Flood Management:**
- Check NSW Flood Prone Land Policy compliance
- Note State Emergency Service (SES) flood classifications
- Identify Local Environment Plan (LEP) flood controls
- Check for coastal inundation considerations
{% elif australian_state == "VIC" %}
**VIC Flood Management:**
- Verify Planning Scheme flood overlay compliance
- Check Melbourne Water or regional authority requirements
- Note Special Building Overlay (SBO) implications
- Identify Land Subject to Inundation Overlay (LSIO)
{% elif australian_state == "QLD" %}
**QLD Flood Management:**
- Check State Planning Policy flood requirements
- Note Queensland Reconstruction Authority guidelines
- Identify Brisbane River or regional flood studies
- Check for storm tide inundation areas
{% endif %}

## Risk Assessment Priorities

### Critical Flood Risks
1. **Property Inundation**: Buildings within flood zones
2. **Access Isolation**: Property cut off during floods  
3. **Infrastructure Damage**: Utilities vulnerable to flooding
4. **Insurance Exclusions**: Flood damage not covered
5. **Development Restrictions**: Building limitations in flood areas
6. **Emergency Access**: Evacuation route limitations

### Mitigation Assessment
Evaluate flood protection adequacy:
- Existing flood mitigation effectiveness
- Required additional protection measures
- Community flood warning systems
- Emergency response capabilities

## Output Requirements

Return a valid JSON object following the **FloodMapSemantics** schema with:

### Required Base Fields
- `image_type`: "flood_map"
- `textual_information`: All flood labels and level data
- `spatial_relationships`: Flood zone interactions with property
- `semantic_summary`: Flood risk overview
- `property_impact_summary`: Development and insurance implications
- `key_findings`: Critical flood discoveries
- `areas_of_concern`: High risk flood issues
- `analysis_confidence`: Overall confidence level

### Flood Map Specific Fields
- `environmental_elements`: All flood-related environmental features
- `flood_zones`: Complete flood risk zone mapping
- `water_levels`: Flood level data and requirements
- `escape_routes`: Emergency access and evacuation
- `flood_mitigation`: Protection measures and systems

### Quality Standards
- **Risk Accuracy**: Precise flood zone boundaries
- **Level Precision**: Exact water level measurements
- **Impact Assessment**: Clear property risk evaluation
- **Compliance Focus**: Relevant planning requirements
- **Emergency Planning**: Evacuation and safety considerations

Begin analysis now. Return only the structured JSON output following the FloodMapSemantics schema.
