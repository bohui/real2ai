---
type: "user"
category: "instructions"
name: "image_semantics_sewer_service_diagram"
version: "1.0.0"
description: "Sewer service diagram semantic analysis for infrastructure mapping"
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
output_parser: SewerServiceSemantics
tags: ["sewer", "infrastructure", "pipes", "utilities"]
---

# Sewer Service Diagram Analysis - {{ australian_state }}

You are analyzing a **sewer service diagram** for an Australian property. Extract detailed infrastructure information focusing on sewer lines, connections, and service requirements following the SewerServiceSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Sewer Service Diagram
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
- `"label"` - For pipe labels, manhole numbers, plan references
- `"measurement"` - For pipe diameters, depths, distances, flows
- `"title"` - For main headings, diagram titles, section headers
- `"legend"` - For map keys, symbols, abbreviations
- `"note"` - For explanatory text, legal statements, conditions
- `"warning"` - For cautionary text, important notices
- `"other"` - For any text that doesn't fit the above categories

### Confidence Level (analysis_confidence)
For `analysis_confidence`, use ONLY these values:
- `"high"` - When analysis is comprehensive and confident
- `"medium"` - When analysis has some uncertainty
- `"low"` - When analysis has significant limitations

### Infrastructure Type (infrastructure_type)
For `infrastructure_elements.infrastructure_type`, use ONLY these values:
- `"sewer"` - Sewerage infrastructure
- `"water"` - Water supply infrastructure
- `"stormwater"` - Drainage infrastructure
- `"other"` - Any other infrastructure type

### Pipe Material (pipe_material)
For `infrastructure_elements.pipe_material`, use ONLY these values:
- `"concrete"` - Concrete pipes
- `"clay"` - Clay pipes
- `"plastic"` - Plastic pipes
- `"metal"` - Metal pipes
- `"other"` - Any other pipe material

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

## Sewer Service Diagram Analysis Objectives

### 1. Infrastructure Elements (infrastructure_elements)
**Map all sewer infrastructure:**
- **Infrastructure type**: "sewer" (primary), "water", "gas", "power", "telecoms"
- **Pipe diameter**: Extract all pipe size specifications (mm, inches)
- **Depth**: Below-ground depth measurements where shown
- **Material**: Pipe material type (PVC, concrete, earthenware, etc.)
- **Ownership**: Council/public vs private sections
- **Maintenance access**: Access pit locations and requirements

**For each infrastructure element:**
```json
{
  "element_type": "pipe",
  "infrastructure_type": "sewer",
  "pipe_diameter": "diameter with units",
  "depth": "depth below surface",
  "material": "pipe material type",
  "ownership": "council|private|shared",
  "maintenance_access": "access requirements"
}
```

### 2. Sewer-Specific Fields

#### Pipe Network (pipe_network)
Document the complete sewer system layout:
- Main sewer lines routing and direction
- Branch connections and junctions
- Pipe size transitions and reducers
- Flow direction indicators
- Invert levels and gradients

#### Connection Points (connection_points)
Identify all service connections:
- Property connection points to main sewer
- Boundary trap locations
- Inspection shaft positions
- Overflow relief gully locations
- Pump station connections (if applicable)

#### Maintenance Access (maintenance_access)
Map access requirements:
- Maintenance pit locations and sizes
- Vehicular access routes for maintenance
- Clearance requirements around infrastructure
- Access easement boundaries
- Emergency access provisions

#### Easement Areas (easement_areas)
Define sewer easement boundaries:
- Easement width and alignment
- Building restriction zones
- Landscaping limitations within easements
- Access rights for maintenance
- Easement beneficiary (usually council/utility)

## Technical Analysis Requirements

### Pipe Specifications
Extract detailed technical information:
- **Diameters**: All pipe sizes (e.g., "150mm", "6 inch")
- **Materials**: Pipe construction materials
- **Grades**: Pipe gradients and fall directions
- **Inverts**: Invert levels where shown
- **Connections**: Junction types and configurations

### Flow Analysis
Document sewer flow characteristics:
- **Direction**: Flow direction arrows and indicators
- **Capacity**: Pipe capacity information if shown
- **Overflow**: Overflow paths and relief points
- **Pumping**: Any pump stations or lift stations

### Property Integration
Analyze property-specific connections:
- **Building Connections**: How buildings connect to sewer
- **Boundary Impacts**: Where sewer crosses property boundaries
- **Development Constraints**: Areas where sewer restricts building
- **Service Requirements**: Connection obligations for property

## Spatial Mapping

### Location Referencing
- Use normalized coordinates (0-1 scale) for all infrastructure
- Reference pipe locations to property boundaries
- Map relationships between different infrastructure types
- Note proximity to existing or proposed buildings

### Measurement Extraction
- Extract ALL pipe diameters and depths
- Note distances between connection points
- Record setback distances from boundaries
- Calculate easement widths and clearances

### Technical Annotations
- Extract all technical labels and specifications
- Note pipe material codes and standards
- Record flow rates or capacity information
- Preserve maintenance access notes

## {{ australian_state }} Specific Requirements

{% if australian_state == "NSW" %}
**NSW Sewer Standards:**
- Check compliance with Sydney Water/local utility standards
- Note Section 73 certificate implications
- Identify any heritage area sewer constraints
- Check for coastal treatment requirements
{% elif australian_state == "VIC" %}
**VIC Sewer Standards:**
- Verify compliance with local water authority standards
- Check for EPA discharge requirements
- Note any heritage overlay sewer constraints
- Identify sustainable drainage requirements
{% elif australian_state == "QLD" %}
**QLD Sewer Standards:**
- Check compliance with local utility standards
- Note any environmentally relevant activity requirements
- Identify coastal management plan implications
- Check for state infrastructure integration
{% endif %}

## Risk Assessment Focus

### Critical Sewer Risks
1. **Building Envelope Conflicts**: Sewer mains under proposed building areas
2. **Easement Violations**: Proposed development within sewer easements
3. **Access Restrictions**: Inadequate maintenance access to infrastructure
4. **Connection Obligations**: Required sewer connection responsibilities
5. **Depth Conflicts**: Shallow sewer lines affecting foundation design
6. **Capacity Issues**: Sewer capacity limitations for development

### Infrastructure Conflicts
- Pipe intersections and clearance issues
- Conflicts with other utilities
- Building setback violations from sewer mains
- Access route blockages

## Output Requirements

Return a valid JSON object following the **SewerServiceSemantics** schema with:

### Required Base Fields
- `image_type`: "sewer_service_diagram"
- `textual_information`: All technical labels and specifications
- `spatial_relationships`: Pipe networks and building interactions
- `semantic_summary`: Sewer system overview
- `property_impact_summary`: Development implications
- `key_findings`: Critical infrastructure discoveries
- `areas_of_concern`: Potential conflicts or restrictions
- `analysis_confidence`: Overall confidence level

### Sewer Service Specific Fields
- `infrastructure_elements`: Complete sewer infrastructure mapping
- `pipe_network`: Detailed pipe system layout
- `connection_points`: All service connection locations
- `maintenance_access`: Access requirements and restrictions
- `easement_areas`: Sewer easement boundaries and limitations

### Quality Standards
- **Technical Precision**: Accurate pipe specifications and dimensions
- **Complete Coverage**: Map entire visible sewer network
- **Ownership Clarity**: Distinguish public vs private infrastructure
- **Risk Focus**: Emphasize building and development conflicts
- **Compliance Check**: Note relevant utility standards

Begin analysis now. Return only the structured JSON output following the SewerServiceSemantics schema.
