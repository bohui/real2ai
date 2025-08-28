---
type: "user"
category: "instructions"
name: "image_semantics_contour_map"
version: "1.0.0"
description: "Contour map semantic analysis for topography and elevation"
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
output_parser: ContourMapSemantics
tags: ["contour", "topography", "elevation", "slope"]
---

# Contour Map Analysis - {{ australian_state }}

You are analyzing a **contour map** for an Australian property. Extract comprehensive topographical and elevation information following the ContourMapSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Contour Map
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
- `"label"` - For contour labels, elevation marks, plan references
- `"measurement"` - For elevations, distances, areas, slopes
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
- `"contour"` - Contour lines
- `"elevation"` - Elevation points
- `"slope"` - Slope areas
- `"water_body"` - Water bodies
- `"other"` - Any other environmental feature

### Slope Type (slope_type)
For `environmental_elements.slope_type`, use ONLY these values:
- `"gentle"` - Gentle slopes
- `"moderate"` - Moderate slopes
- `"steep"` - Steep slopes
- `"very_steep"` - Very steep slopes
- `"other"` - Any other slope type

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

## Contour Map Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map topographical and elevation features:**
- **Environmental type**: "elevation_change", "slope", "ridge", "valley", "drainage"
- **Risk level**: slope stability and development suitability
- **Impact area**: areas affected by topographical constraints
- **Mitigation measures**: required slope stabilization or drainage

### 2. Contour-Specific Fields

#### Elevation Ranges (elevation_ranges)
Document elevation variations across property:
- **Highest Elevation**: Maximum elevation points on property
- **Lowest Elevation**: Minimum elevation points on property
- **Elevation Difference**: Total elevation change across site
- **Spot Heights**: Specific elevation measurements (RL values)
- **Benchmark References**: Survey datum and reference points
- **Elevation Zones**: Areas of similar elevation ranges

#### Contour Intervals (contour_intervals)
Extract contour line specifications:
- **Contour Spacing**: Interval between contour lines (e.g., 0.5m, 1m, 2m)
- **Index Contours**: Major contour lines with elevation labels
- **Intermediate Contours**: Minor contour lines between index contours
- **Contour Accuracy**: Survey accuracy class and reliability
- **Depression Contours**: Contours indicating depressions or holes
- **Supplementary Contours**: Additional contours for detailed areas

#### Slope Analysis (slope_analysis)
Assess slope gradients and stability:
- **Slope Gradients**: Percentage grades and angles across property
- **Steep Slope Areas**: Areas exceeding development thresholds
- **Gentle Slope Areas**: Areas suitable for standard development
- **Slope Direction**: Aspect and orientation of slopes
- **Slope Stability Assessment**: Potential for erosion or landslip
- **Cut and Fill Implications**: Earthworks required for development

#### Drainage Patterns (drainage_patterns)
Map natural water flow and drainage:
- **Ridge Lines**: Highest elevation lines and watershed boundaries
- **Valley Lines**: Natural drainage channels and watercourses
- **Flow Directions**: Direction of surface water flow
- **Catchment Areas**: Areas draining to specific points
- **Drainage Concentration Points**: Areas where water accumulates
- **Overland Flow Paths**: Natural flood and stormwater routes

#### Cut Fill Requirements (cut_fill_requirements)
Assess earthworks needs for development:
- **Cut Areas**: Areas requiring excavation for level building sites
- **Fill Areas**: Areas requiring fill to achieve building levels
- **Retaining Wall Requirements**: Areas needing slope retention
- **Earthworks Volumes**: Estimated cut and fill quantities
- **Access for Earthworks**: Machinery access for site preparation
- **Disposal Requirements**: Off-site disposal or retention of spoil

## Topographical Assessment

### Development Suitability
Evaluate land suitability for development:
- **Buildable Areas**: Relatively flat areas suitable for construction
- **Slope Limitations**: Areas too steep for standard development
- **Foundation Requirements**: Special foundation needs for slopes
- **Access Challenges**: Driveway gradients and construction access
- **Utility Installation**: Challenges for sewer, water, power installation

### Drainage and Stormwater
Assess water management implications:
- **Natural Drainage**: Existing drainage patterns to preserve
- **Stormwater Management**: Required stormwater control measures
- **Erosion Control**: Measures needed to prevent soil erosion
- **Flood Risk**: Low-lying areas subject to water accumulation
- **Detention Requirements**: Need for stormwater detention systems

### Construction Implications
Evaluate building and construction factors:
- **Foundation Design**: Special foundation requirements for slopes
- **Access Roads**: Driveway gradients and construction vehicle access
- **Services Installation**: Utility connection challenges on slopes
- **Site Safety**: Construction safety on sloping sites
- **Cost Implications**: Additional costs for slope construction

## {{ australian_state }} Slope Development Standards

{% if australian_state == "NSW" %}
**NSW Slope Development:**
- Check Local Environment Plan slope development controls
- Note SEPP (Building Sustainability Index) BASIX slope provisions
- Identify geotechnical investigation requirements
- Check for landslip or soil erosion mapping
{% elif australian_state == "VIC" %}
**VIC Slope Development:**
- Verify Planning Scheme slope and erosion overlays
- Check Building Regulations slope construction requirements
- Note Erosion Management Overlay provisions
- Identify Land Subject to Inundation considerations
{% elif australian_state == "QLD" %}
**QLD Slope Development:**
- Check Planning Scheme slope hazard overlays
- Note Queensland Development Code slope provisions
- Identify State Planning Policy natural hazard requirements
- Check for erosion prone area mapping
{% endif %}

## Risk Assessment Focus

### Critical Topographical Risks
1. **Excessive Slope**: Areas too steep for practical development
2. **Slope Instability**: Risk of landslip or soil movement
3. **Drainage Problems**: Poor natural drainage causing water issues
4. **High Earthworks Costs**: Expensive cut and fill requirements
5. **Access Difficulties**: Steep driveways exceeding grade limits
6. **Foundation Challenges**: Complex foundation requirements

### Development Opportunities
Assess positive topographical aspects:
- Views and outlook from elevated positions
- Natural drainage and stormwater management
- Terraced development opportunities
- Privacy from elevation differences

## Output Requirements

Return a valid JSON object following the **ContourMapSemantics** schema with:

### Required Base Fields
- `image_type`: "contour_map"
- `textual_information`: All elevation labels and contour markings
- `spatial_relationships`: Topographical feature relationships
- `semantic_summary`: Topographical overview
- `property_impact_summary`: Development implications of topography
- `key_findings`: Critical topographical discoveries
- `areas_of_concern`: Slope or drainage issues
- `analysis_confidence`: Overall confidence level

### Contour Map Specific Fields
- `environmental_elements`: Topographical and elevation features
- `elevation_ranges`: Elevation variation across property
- `contour_intervals`: Contour line specifications and accuracy
- `slope_analysis`: Slope gradient and stability assessment
- `drainage_patterns`: Natural water flow and drainage
- `cut_fill_requirements`: Earthworks needs for development

### Quality Standards
- **Elevation Accuracy**: Precise elevation measurements and ranges
- **Slope Assessment**: Accurate gradient and stability analysis
- **Drainage Analysis**: Complete natural drainage pattern mapping
- **Development Focus**: Emphasize construction and development implications
- **Engineering Considerations**: Include geotechnical and foundation factors

Begin analysis now. Return only the structured JSON output following the ContourMapSemantics schema.
