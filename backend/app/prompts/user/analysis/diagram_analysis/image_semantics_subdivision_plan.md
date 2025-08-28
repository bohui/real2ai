---
type: "user"
category: "instructions"
name: "image_semantics_subdivision_plan"
version: "1.0.0"
description: "Subdivision plan semantic analysis for subdivision layout and infrastructure"
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
output_parser: SubdivisionPlanSemantics
tags: ["subdivision", "lots", "infrastructure", "development"]
---

# Subdivision Plan Analysis - {{ australian_state }}

You are analyzing a **subdivision plan** for an Australian property. Extract comprehensive subdivision layout and infrastructure requirement information following the SubdivisionPlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Subdivision Plan
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
- `"lot_boundary"` - Boundaries between lots
- `"road_boundary"` - Boundaries with roads
- `"reserve_boundary"` - Boundaries with public reserves
- `"easement_boundary"` - Boundaries with easements

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

## Subdivision Plan Analysis Objectives

### 1. Boundary Elements (boundary_elements)
**Map subdivision lot boundaries and layout:**
- **Boundary type**: "lot_boundary", "road_boundary", "reserve_boundary", "easement_boundary"
- **Boundary markings**: survey marks defining lot boundaries
- **Dimensions**: lot sizes, frontages, and areas
- **Encroachments**: boundary adjustments or variations
- **Easements**: utility and access easements within subdivision

### 2. Infrastructure Elements (infrastructure_elements)
**Document subdivision infrastructure requirements:**
- **Infrastructure type**: "road", "sewer", "water", "stormwater", "power", "telecommunications"
- **Construction standards**: infrastructure design specifications
- **Connection requirements**: integration with existing infrastructure
- **Ownership arrangements**: public vs private infrastructure
- **Maintenance responsibilities**: ongoing infrastructure management

### 3. Subdivision Plan Specific Fields

#### Lot Layout (lot_layout)
Document subdivision lot configuration:
- **Lot Numbers**: Individual lot identification numbers
- **Lot Sizes**: Individual lot areas and dimensions
- **Lot Frontages**: Street frontage widths for each lot
- **Lot Depths**: Depth measurements for each lot
- **Corner Lots**: Lots with dual street frontages
- **Irregular Lots**: Non-standard shaped or sized lots
- **Minimum Lot Sizes**: Compliance with planning scheme minimums

#### Road Dedications (road_dedications)
Map roads to be dedicated to council:
- **New Roads**: Roads created by subdivision
- **Road Widths**: Carriageway and reserve widths
- **Road Classifications**: Local streets, collector roads, arterial roads
- **Cul-de-sacs**: Dead-end streets and turning circles
- **Road Naming**: Proposed street names
- **Pavement Specifications**: Road construction standards

#### Easement Dedications (easement_dedications)
Document easements to be created:
- **Utility Easements**: Sewer, water, power, telecommunications easements
- **Drainage Easements**: Stormwater drainage and overland flow
- **Access Easements**: Vehicular and pedestrian access rights
- **Easement Widths**: Dimensions and areas of easements
- **Easement Beneficiaries**: Authorities or utilities benefiting
- **Easement Restrictions**: Building and use limitations

#### Infrastructure Works (infrastructure_works)
Detail required infrastructure construction:
- **Road Construction**: Earthworks, pavement, kerb and gutter
- **Sewer Infrastructure**: Gravity sewers, pump stations, connections
- **Water Infrastructure**: Water mains, hydrants, service connections
- **Stormwater Infrastructure**: Pipes, pits, detention systems
- **Electrical Infrastructure**: Underground power, street lighting
- **Telecommunications**: NBN, copper, fiber infrastructure

#### Approval Conditions (approval_conditions)
Document subdivision approval requirements:
- **Planning Conditions**: Development approval conditions
- **Engineering Conditions**: Infrastructure design and construction standards
- **Environmental Conditions**: Environmental protection measures
- **Bonding Requirements**: Financial guarantees for infrastructure
- **Timing Requirements**: Infrastructure completion deadlines
- **Certification Requirements**: Engineering certification and inspections

## Subdivision Assessment

### Development Economics
Evaluate subdivision financial viability:
- **Lot Values**: Expected sale prices for individual lots
- **Infrastructure Costs**: Total infrastructure construction costs
- **Development Timeline**: Expected subdivision completion timeframe
- **Market Absorption**: Expected lot sales rates
- **Profit Margins**: Development return on investment

### Planning Compliance
Assess subdivision planning compliance:
- **Zoning Compliance**: Lot sizes meet zoning requirements
- **Density Compliance**: Subdivision density within planning limits
- **Open Space Provision**: Public open space dedication requirements
- **Car Parking**: Adequate parking provision for subdivision
- **Access Adequacy**: Satisfactory vehicular and pedestrian access

### Infrastructure Adequacy
Evaluate infrastructure capacity and design:
- **Utility Capacity**: Existing utility capacity for subdivision
- **Road Network**: Adequate road access and circulation
- **Stormwater Management**: Appropriate drainage design
- **Service Levels**: Infrastructure meets development standards
- **Future Expansion**: Potential for future subdivision stages

## {{ australian_state }} Subdivision Requirements

{% if australian_state == "NSW" %}
**NSW Subdivision Framework:**
- Check Environmental Planning and Assessment Act compliance
- Note Local Environment Plan subdivision provisions
- Identify Roads Act road dedication requirements
- Check for Infrastructure Contributions Plan obligations
{% elif australian_state == "VIC" %}
**VIC Subdivision Framework:**
- Verify Planning and Environment Act subdivision requirements
- Check Subdivision Act engineering requirements
- Note Road Management Act road vesting provisions
- Identify Development Contributions Plan obligations
{% elif australian_state == "QLD" %}
**QLD Subdivision Framework:**
- Check Planning Act subdivision requirements
- Note Land Title Act survey and registration requirements
- Identify Local Government Infrastructure Charges
- Check for State Infrastructure Contributions Scheme
{% endif %}

## Risk Assessment Focus

### Critical Subdivision Risks
1. **Infrastructure Cost Overruns**: Higher than expected infrastructure costs
2. **Approval Delays**: Extended subdivision approval processes
3. **Market Demand Risk**: Slow lot sales affecting cash flow
4. **Utility Capacity Issues**: Inadequate existing utility capacity
5. **Environmental Constraints**: Unforeseen environmental limitations
6. **Construction Delays**: Infrastructure construction delays

### Investment Considerations
Assess subdivision investment factors:
- Expected returns per lot and overall subdivision
- Cash flow timing during development period
- Market competition from other subdivisions
- Infrastructure cost vs lot sale price ratios

## Output Requirements

Return a valid JSON object following the **SubdivisionPlanSemantics** schema with:

### Required Base Fields
- `image_type`: "subdivision_plan"
- `textual_information`: All subdivision labels and lot numbers
- `spatial_relationships`: Lot layout and infrastructure relationships
- `semantic_summary`: Subdivision layout overview
- `property_impact_summary`: Subdivision development implications
- `key_findings`: Critical subdivision discoveries
- `areas_of_concern`: Subdivision development issues
- `analysis_confidence`: Overall confidence level

### Subdivision Plan Specific Fields
- `boundary_elements`: Subdivision lot boundary analysis
- `infrastructure_elements`: Required subdivision infrastructure
- `lot_layout`: Subdivision lot sizes and configuration
- `road_dedications`: Roads to be dedicated to council
- `easement_dedications`: Easements to be created or dedicated
- `infrastructure_works`: Required infrastructure construction
- `approval_conditions`: Subdivision approval conditions

### Quality Standards
- **Layout Accuracy**: Precise lot layout and infrastructure mapping
- **Compliance Assessment**: Planning and engineering standard compliance
- **Economic Analysis**: Development viability and return assessment
- **Risk Identification**: Subdivision development risk analysis
- **Infrastructure Focus**: Adequate infrastructure provision assessment

Begin analysis now. Return only the structured JSON output following the SubdivisionPlanSemantics schema.
