---
type: "user"
category: "instructions"
name: "image_semantics_drainage_plan"
version: "1.0.0"
description: "Drainage plan semantic analysis for stormwater management"
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
output_parser: DrainagePlanSemantics
tags: ["drainage", "stormwater", "water_management", "infrastructure"]
---

# Drainage Plan Analysis - {{ australian_state }}

You are analyzing a **drainage plan** for an Australian property. Extract stormwater drainage infrastructure and water management systems following the DrainagePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Drainage Plan
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
- `"label"` - For drain labels, catchment areas, plan references
- `"measurement"` - For pipe diameters, depths, distances, flows
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

### Infrastructure Type (infrastructure_type)
For `infrastructure_elements.infrastructure_type`, use ONLY these values:
- `"stormwater"` - Stormwater drainage infrastructure
- `"sewer"` - Sewerage infrastructure
- `"water"` - Water supply infrastructure
- `"other"` - Any other infrastructure type

### Drainage Type (drainage_type)
For `infrastructure_elements.drainage_type`, use ONLY these values:
- `"pipe"` - Drainage pipes
- `"channel"` - Open drainage channels
- `"pit"` - Drainage pits
- `"swale"` - Drainage swales
- `"other"` - Any other drainage type

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Drainage Plan Analysis Objectives

### 1. Infrastructure Elements (infrastructure_elements)
**Map all drainage infrastructure:**
- **Infrastructure type**: "stormwater", "drainage", "detention", "bioretention"
- **Pipe diameter**: Drainage pipe sizes and specifications
- **Depth**: Underground pipe depths and inverts
- **Material**: Pipe materials (concrete, PVC, steel, etc.)
- **Ownership**: Council vs private drainage infrastructure
- **Maintenance access**: Access for cleaning and maintenance

### 2. Drainage-Specific Fields

#### Drainage Network (drainage_network)
Document complete stormwater system:
- **Pipe network layout**: Main drains and branch connections
- **Flow directions**: Stormwater flow paths and directions
- **Pipe gradients**: Pipe falls and hydraulic gradients
- **Junction types**: Pit connections and pipe junctions
- **Network capacity**: Design flow rates and pipe capacities

#### Catchment Areas (catchment_areas)
Map water collection areas:
- **Roof catchments**: Building roof areas draining to system
- **Paved catchments**: Driveways, paths, and hard surfaces
- **Landscape catchments**: Garden and lawn drainage areas
- **External catchments**: Off-site water entering system
- **Total catchment areas**: Combined catchment calculations

#### Outfall Points (outfall_points)
Identify drainage discharge locations:
- **Street drainage connections**: Connection to public stormwater
- **Natural watercourse outfalls**: Discharge to creeks or rivers
- **Soakage areas**: On-site infiltration and soakage systems
- **Pumped outfalls**: Pumping station discharge points
- **Combined outfalls**: Multiple system discharge points

#### Retention Systems (retention_systems)
Document water management systems:
- **Detention basins**: Temporary stormwater storage
- **Retention ponds**: Permanent water storage systems
- **Bioretention systems**: Natural water treatment systems
- **Rainwater tanks**: Rooftop water collection and storage
- **Constructed wetlands**: Engineered water treatment wetlands

#### Pipe Capacities (pipe_capacities)
Extract drainage capacity information:
- **Pipe sizes and capacities**: Flow rates for different pipe sizes
- **Design storm events**: 1:5, 1:10, 1:100 year storm capacities
- **Overland flow paths**: Emergency overflow routes
- **System adequacy**: Capacity vs catchment requirements
- **Upgrade requirements**: Potential capacity upgrade needs

## Hydraulic Analysis Objectives

### Flow Assessment
Evaluate drainage system performance:
- **Hydraulic gradients**: Adequate pipe falls for flow
- **Flow velocities**: Self-cleansing velocities in pipes
- **System surcharge**: Potential for pipe surcharging
- **Flood immunity**: System performance in major storms
- **Emergency overflows**: Overland flow path adequacy

### Water Quality
Assess stormwater quality management:
- **First flush diverters**: Initial stormwater pollution control
- **Gross pollutant traps**: Litter and debris removal
- **Bioretention treatment**: Natural water quality improvement
- **Sediment traps**: Sediment removal from stormwater
- **Oil separation**: Hydrocarbon removal systems

### Maintenance Requirements
Document ongoing maintenance needs:
- **Regular inspections**: Required maintenance schedules
- **Cleaning access**: Ability to clean and maintain systems
- **Replacement planning**: Anticipated infrastructure replacement
- **Performance monitoring**: System performance assessment
- **Compliance reporting**: Regulatory reporting requirements

## {{ australian_state }} Drainage Standards

{% if australian_state == "NSW" %}
**NSW Drainage Requirements:**
- Check local council drainage standards
- Note BASIX stormwater management requirements
- Identify Sydney Water or local authority requirements
- Check for Water Sensitive Urban Design (WSUD) requirements
{% elif australian_state == "VIC" %}
**VIC Drainage Requirements:**
- Verify local council drainage standards
- Check Melbourne Water or regional authority requirements
- Note Best Practice Environmental Management Guidelines
- Identify WSUD and stormwater quality requirements
{% elif australian_state == "QLD" %}
**QLD Drainage Requirements:**
- Check local council drainage standards
- Note Queensland Urban Drainage Manual requirements
- Identify State Planning Policy water quality objectives
- Check for Healthy Waters Management Plan compliance
{% endif %}

## Risk Assessment Focus

### Critical Drainage Risks
1. **Inadequate Capacity**: Insufficient drainage for design storms
2. **Poor Water Quality**: Lack of stormwater treatment systems
3. **Maintenance Access**: Difficult or impossible system maintenance
4. **Overflow Issues**: Inadequate emergency overflow provisions
5. **Compliance Gaps**: Non-compliance with drainage standards
6. **System Conflicts**: Conflicts with other utilities or development

### Development Impacts
Assess drainage implications for development:
- Additional drainage infrastructure requirements
- Stormwater detention and treatment obligations
- Connection to existing drainage systems
- Ongoing maintenance responsibilities

## Output Requirements

Return a valid JSON object following the **DrainagePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "drainage_plan"
- `textual_information`: All drainage labels and specifications
- `spatial_relationships`: Drainage system interactions
- `semantic_summary`: Stormwater management overview
- `property_impact_summary`: Development and compliance implications
- `key_findings`: Critical drainage discoveries
- `areas_of_concern`: Drainage adequacy or compliance issues
- `analysis_confidence`: Overall confidence level

### Drainage Plan Specific Fields
- `infrastructure_elements`: Complete drainage infrastructure mapping
- `drainage_network`: Detailed pipe system layout
- `catchment_areas`: Water collection and flow areas
- `outfall_points`: Drainage discharge locations
- `retention_systems`: Water management and treatment systems
- `pipe_capacities`: System capacity and performance data

### Quality Standards
- **Technical Accuracy**: Precise drainage specifications
- **System Assessment**: Complete drainage system evaluation
- **Compliance Check**: Relevant drainage standards
- **Risk Focus**: Development and environmental constraints
- **Water Management**: Sustainable stormwater practices

Begin analysis now. Return only the structured JSON output following the DrainagePlanSemantics schema.
