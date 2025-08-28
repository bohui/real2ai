---
type: "user"
category: "instructions"
name: "image_semantics_survey_diagram"
version: "1.0.0"
description: "Survey diagram semantic analysis for precise boundaries and measurements"
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
output_parser: SurveyDiagramSemantics
tags: ["survey", "boundaries", "measurements", "precision"]
---

# Survey Diagram Analysis - {{ australian_state }}

You are analyzing a **survey diagram** for an Australian property. Extract precise boundary information, measurements, and survey data following the SurveyDiagramSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Survey Diagram
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
- `"label"` - For survey mark numbers, lot references, plan numbers
- `"measurement"` - For distances, angles, bearings, elevations
- `"title"` - For main headings, survey titles, section headers
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
- `"lot_boundary"` - Boundaries between lots
- `"road_boundary"` - Boundaries with roads
- `"reserve_boundary"` - Boundaries with public reserves
- `"easement_boundary"` - Boundaries with easements

### Survey Mark Type (survey_mark_type)
For `boundary_elements.survey_mark_type`, use ONLY these values:
- `"peg"` - Survey pegs
- `"nail"` - Survey nails
- `"drill_hole"` - Drill holes
- `"monument"` - Survey monuments
- `"other"` - Any other survey mark type

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

## Survey Analysis Objectives

### 1. Boundary Elements (boundary_elements)
**Extract precise boundary information:**
- **Boundary type**: front, rear, side, curved, irregular
- **Boundary markings**: survey pegs, iron bars, concrete marks, natural features
- **Dimensions**: precise measurements with bearings and distances
- **Encroachments**: any structures crossing surveyed boundaries
- **Easements**: surveyed easement boundaries and purposes

### 2. Survey-Specific Fields

#### Survey Marks (survey_marks)
Document all survey reference points:
- Permanent survey marks (PSM) and their identifiers
- Temporary survey marks and pegs
- Benchmark elevations and datum references
- Coordinate system reference points
- Survey control network connections

#### Measurements (measurements)
Extract all precise survey measurements:
- Boundary distances with exact measurements (e.g., "25.347m")
- Bearing information (e.g., "N 45°30'15" E")
- Angular measurements and corner angles
- Area calculations and lot area
- Coordinate positions (MGA, AMG, local grid)

#### Elevation Data (elevation_data)
Map elevation and contour information:
- Spot heights and elevation points
- Contour lines and intervals
- Reduced levels (RL) at key points
- Natural surface elevations
- Cut and fill requirements

#### Coordinate System (coordinate_system)
Identify the survey coordinate system:
- Map Grid of Australia (MGA) zones
- Australian Map Grid (AMG) references
- Local coordinate systems
- Datum information (GDA94, GDA2020)
- Zone and projection details

## Technical Survey Analysis Objectives

### Precision Requirements
Extract all technical survey data:
- **Distances**: Record to millimeter precision where shown
- **Bearings**: Include degrees, minutes, seconds
- **Areas**: Total lot area and partial areas
- **Angles**: Internal and external corner angles
- **Coordinates**: Full coordinate positions

### Survey Accuracy
Document survey quality indicators:
- Survey accuracy class (e.g., Class A, B, C)
- Survey method notation (total station, GPS, etc.)
- Closure error information
- Survey standard compliance

### Legal Survey Elements
Identify legally significant features:
- Title boundary vs. occupation boundary differences
- Adverse possession indicators
- Boundary disputes or uncertainties
- Survey certificate requirements

## Spatial Mapping

### Location Referencing
- Use normalized coordinates (0-1 scale) for diagram elements
- Reference all measurements to survey control points
- Map relationships between boundary segments
- Note survey mark locations precisely

### Measurement Extraction
- Extract ALL measurements with full precision
- Note bearing directions and magnetic declination
- Record area calculations and verification
- Document coordinate positions completely

### Survey Annotations
- Extract surveyor names and registration numbers
- Note survey dates and revision dates
- Record survey instrument information
- Preserve legal descriptions and lot identifiers

## {{ australian_state }} Survey Standards

{% if australian_state == "NSW" %}
**NSW Survey Requirements:**
- Check compliance with Surveying and Spatial Information Act
- Note cadastral survey standards
- Identify any heritage survey constraints
- Check for coastal survey requirements
{% elif australian_state == "VIC" %}
**VIC Survey Requirements:**
- Verify compliance with Surveying Act standards
- Check cadastral survey accuracy requirements
- Note any heritage overlay survey needs
- Identify subdivision survey compliance
{% elif australian_state == "QLD" %}
**QLD Survey Requirements:**
- Check compliance with Survey and Mapping Infrastructure Act
- Note digital cadastral database requirements
- Identify any state land survey implications
- Check for coastal protection survey needs
{% endif %}

## Risk Assessment Focus

### Critical Survey Risks
1. **Boundary Discrepancies**: Differences between title and occupation
2. **Survey Accuracy Issues**: Insufficient precision for development
3. **Encroachment Conflicts**: Structures over surveyed boundaries
4. **Easement Boundary Disputes**: Unclear easement definitions
5. **Survey Currency**: Outdated survey information
6. **Corner Mark Loss**: Missing or damaged survey marks

### Survey Quality Indicators
- Survey closure within acceptable limits
- Appropriate survey class for intended use
- Complete corner mark recovery
- Current survey standards compliance

## Output Requirements

Return a valid JSON object following the **SurveyDiagramSemantics** schema with:

### Required Base Fields
- `image_type`: "survey_diagram"
- `textual_information`: All survey annotations and measurements
- `spatial_relationships`: Boundary segment relationships
- `semantic_summary`: Survey layout and precision summary
- `property_impact_summary`: Survey implications for development
- `key_findings`: Critical survey discoveries
- `areas_of_concern`: Boundary or accuracy issues
- `analysis_confidence`: Overall confidence level

### Survey Specific Fields
- `boundary_elements`: Complete surveyed boundary analysis
- `survey_marks`: All survey reference points
- `measurements`: Precise distance and bearing data
- `elevation_data`: Height and contour information
- `coordinate_system`: Survey coordinate system details

### Quality Standards
- **Precision**: Extract measurements to full available precision
- **Completeness**: Map all visible survey elements
- **Accuracy**: Only record clearly visible survey data
- **Legal Focus**: Emphasize boundary and title implications
- **Technical Compliance**: Note survey standard adherence

Begin analysis now. Return only the structured JSON output following the SurveyDiagramSemantics schema.
