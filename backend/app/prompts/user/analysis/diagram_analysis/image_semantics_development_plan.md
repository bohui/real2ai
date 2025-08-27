---
type: "user"
category: "instructions"
name: "image_semantics_development_plan"
version: "1.0.0"
description: "Development plan semantic analysis for proposed development requirements"
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
output_parser: DevelopmentPlanSemantics
tags: ["development", "planning", "staged", "infrastructure"]
---

# Development Plan Analysis - {{ australian_state }}

You are analyzing a **development plan** for an Australian property. Extract comprehensive development staging, infrastructure, and requirement information following the DevelopmentPlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Development Plan
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

## Development Plan Analysis Objectives

### 1. Building Elements (building_elements)
**Document proposed development buildings:**
- **Building type**: "residential", "commercial", "mixed_use", "community", "infrastructure"
- **Construction stage**: "stage_1", "stage_2", "future", "completed"
- **Height restrictions**: proposed building heights and storey limits
- **Setback requirements**: building placement and boundary setbacks
- **Building envelope**: proposed building footprints and massing

### 2. Boundary Elements (boundary_elements)
**Map development site boundaries:**
- **Boundary type**: "development_site", "stage_boundary", "lot_boundary", "reserve"
- **Boundary markings**: development boundary definitions
- **Dimensions**: site areas and stage areas
- **Encroachments**: proposed boundary modifications
- **Easements**: new easements required for development

### 3. Infrastructure Elements (infrastructure_elements)
**Document development infrastructure:**
- **Infrastructure type**: "road", "sewer", "water", "power", "stormwater", "community"
- **Construction stage**: infrastructure delivery timing
- **Specifications**: infrastructure capacity and design standards
- **Connections**: integration with existing infrastructure
- **Responsibilities**: developer vs authority infrastructure obligations

### 4. Development Plan Specific Fields

#### Development Stages (development_stages)
Document development staging and timeline:
- **Stage 1 Development**: Initial development phase details
- **Stage 2+ Development**: Subsequent development phases
- **Completion Timeframes**: Expected completion dates for each stage
- **Staging Dependencies**: Prerequisites for advancing to next stage
- **Infrastructure Staging**: Infrastructure delivery aligned with development
- **Population Staging**: Expected resident/worker numbers per stage

#### Density Requirements (density_requirements)
Extract development density and yield:
- **Dwelling Density**: Dwellings per hectare or lot yield
- **Population Density**: Expected resident population density
- **Floor Space Ratio**: Commercial/retail floor space density
- **Building Coverage**: Site coverage percentages
- **Landscape Ratio**: Minimum landscaping requirements
- **Car Parking Ratios**: Required parking spaces per dwelling/employee

#### Open Space Provision (open_space_provision)
Map public and private open space:
- **Public Open Space**: Parks, reserves, and community areas
- **Private Open Space**: Individual lot outdoor space requirements
- **Community Facilities**: Recreation centers, playgrounds, sports facilities
- **Environmental Corridors**: Habitat protection and connection areas
- **Stormwater Areas**: Detention basins and water quality treatment
- **Accessibility**: Disabled access to all public areas

#### Infrastructure Contributions (infrastructure_contributions)
Document developer infrastructure obligations:
- **Road Infrastructure**: New roads, upgrades, intersections
- **Utility Infrastructure**: Sewer, water, power, telecommunications upgrades
- **Community Infrastructure**: Schools, community centers, emergency services
- **Public Transport**: Bus stops, railway stations, transport hubs
- **Environmental Infrastructure**: Habitat restoration, revegetation
- **Developer Contributions**: Section 94/Infrastructure charges

#### Affordable Housing (affordable_housing)
Identify affordable housing requirements:
- **Affordable Housing Targets**: Percentage of affordable/social housing
- **Price Points**: Affordable housing price brackets
- **Housing Types**: Affordable housing dwelling types and sizes
- **Management Arrangements**: Social housing provider arrangements
- **Timing Requirements**: Delivery timing for affordable housing
- **Alternative Contributions**: Cash-in-lieu or off-site provisions

## Development Assessment

### Approval Status
Evaluate development approval progress:
- **Planning Approval**: Development application status
- **Construction Certificate**: Building approval status
- **Infrastructure Agreements**: Utility and road authority agreements
- **Environmental Approvals**: EPA and environmental authority approvals
- **Heritage Approvals**: Heritage council or local heritage approvals

### Market Analysis
Assess development market viability:
- **Market Demand**: Demand for proposed housing/commercial types
- **Pricing Strategy**: Expected sale prices and market positioning
- **Competition Analysis**: Competing developments in area
- **Absorption Rates**: Expected sales rates per stage
- **Rental Yields**: Investment return expectations

### Risk Assessment
Identify development risks:
- **Market Risk**: Demand changes during development period
- **Construction Risk**: Building cost escalation and delays
- **Approval Risk**: Potential for approval conditions or refusal
- **Infrastructure Risk**: Utility capacity or delivery delays
- **Environmental Risk**: Unforeseen environmental constraints

## {{ australian_state }} Development Requirements

{% if australian_state == "NSW" %}
**NSW Development Framework:**
- Check Environmental Planning and Assessment Act compliance
- Note State Environmental Planning Policy (SEPP) requirements
- Identify Infrastructure Contributions Plan obligations
- Check for Greater Sydney Commission alignment
{% elif australian_state == "VIC" %}
**VIC Development Framework:**
- Verify Planning and Environment Act compliance
- Check Development Contributions Plan requirements
- Note Victorian Planning Provisions compliance
- Identify Growth Areas Infrastructure Contribution obligations
{% elif australian_state == "QLD" %}
**QLD Development Framework:**
- Check Planning Act development requirements
- Note State Planning Policy compliance
- Identify Infrastructure Charges Schedule obligations
- Check for Priority Development Area provisions
{% endif %}

## Risk Assessment Focus

### Critical Development Risks
1. **Market Timing Risk**: Development completion vs market demand cycles
2. **Infrastructure Delivery Risk**: Utility capacity or timing issues
3. **Approval Condition Risk**: Unexpected approval requirements
4. **Cost Escalation Risk**: Construction and infrastructure cost increases
5. **Environmental Constraint Risk**: Unforeseen environmental limitations
6. **Community Opposition Risk**: Local resident objections to development

### Investment Considerations
Assess development investment implications:
- Expected returns on investment per stage
- Cash flow timing and development funding requirements
- Exit strategy options for different development stages
- Potential for value uplift from development approvals

## Output Requirements

Return a valid JSON object following the **DevelopmentPlanSemantics** schema with:

### Required Base Fields
- `image_type`: "development_plan"
- `textual_information`: All development labels and staging information
- `spatial_relationships`: Development stage and infrastructure relationships
- `semantic_summary`: Development plan overview
- `property_impact_summary`: Development timing and requirements
- `key_findings`: Critical development discoveries
- `areas_of_concern`: Development risk or constraint issues
- `analysis_confidence`: Overall confidence level

### Development Plan Specific Fields
- `building_elements`: Proposed development buildings
- `boundary_elements`: Development site boundaries
- `infrastructure_elements`: Required development infrastructure
- `development_stages`: Development staging and timeline
- `density_requirements`: Development density and yield targets
- `open_space_provision`: Public and community space requirements
- `infrastructure_contributions`: Developer infrastructure obligations
- `affordable_housing`: Affordable housing requirements and delivery

### Quality Standards
- **Development Clarity**: Clear development staging and requirements
- **Infrastructure Assessment**: Complete infrastructure obligation analysis
- **Market Viability**: Realistic development timeline and market assessment
- **Risk Identification**: Comprehensive development risk analysis
- **Compliance Focus**: Relevant development approval requirements

Begin analysis now. Return only the structured JSON output following the DevelopmentPlanSemantics schema.
