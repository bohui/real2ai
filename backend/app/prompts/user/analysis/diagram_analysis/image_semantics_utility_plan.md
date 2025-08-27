---
type: "user"
category: "instructions"
name: "image_semantics_utility_plan"
version: "1.0.0"
description: "Utility plan semantic analysis for infrastructure services"
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
output_parser: UtilityPlanSemantics
tags: ["utility", "infrastructure", "services", "connections"]
---

# Utility Plan Analysis - {{ australian_state }}

You are analyzing a **utility plan** for an Australian property. Extract comprehensive utility infrastructure information including power, gas, water, and telecommunications following the UtilityPlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Utility Plan
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

## Utility Infrastructure Analysis Objectives

### 1. Infrastructure Elements (infrastructure_elements)
**Map all utility infrastructure:**
- **Infrastructure type**: "power", "gas", "water", "telecoms", "nbn"
- **Pipe diameter**: Cable/pipe specifications and sizes
- **Depth**: Underground depth measurements
- **Material**: Cable/pipe material types
- **Ownership**: Utility company vs private infrastructure
- **Maintenance access**: Access requirements and restrictions

### 2. Utility-Specific Fields

#### Utility Types (utility_types)
Identify all utility services present:
- **Electrical Power**: overhead/underground power lines, transformers
- **Natural Gas**: high/medium/low pressure gas mains
- **Water Supply**: water mains, service connections
- **Telecommunications**: copper, fiber, coaxial cables
- **NBN Infrastructure**: fiber to premises/node connections
- **Sewerage**: (if shown on utility plan)

#### Service Connections (service_connections)
Map all utility connection points:
- **Connection locations**: where utilities connect to property
- **Meter positions**: utility meter and equipment locations
- **Service line routing**: from main to connection point
- **Connection capacity**: service size and capacity
- **Connection obligations**: developer vs utility responsibilities

#### Easement Corridors (easement_corridors)
Document utility easement requirements:
- **Easement widths**: corridor dimensions for each utility
- **Access rights**: utility maintenance access requirements
- **Building restrictions**: limitations on development within easements
- **Shared easements**: multiple utilities within same corridor
- **Easement beneficiaries**: specific utility companies

#### Meter Locations (meter_locations)
Identify all utility metering points:
- **Electricity meters**: single/three phase meter positions
- **Gas meters**: domestic/commercial gas meter locations
- **Water meters**: main and sub-meter positions
- **Telecommunications**: NBN connection boxes, pit locations
- **Multi-utility sites**: combined utility meter locations

#### Capacity Information (capacity_information)
Extract utility capacity details:
- **Power capacity**: transformer ratings, service capacities
- **Gas pressures**: service pressure ratings
- **Water pressures**: service pressure and flow rates
- **Data capacity**: telecommunications bandwidth capabilities
- **Load calculations**: electrical load assessments

## Technical Utility Analysis Objectives

### Infrastructure Specifications
Document technical details:
- **Cable/Pipe Sizes**: diameter, capacity, voltage ratings
- **Materials**: copper, aluminum, PVC, steel specifications
- **Installation Methods**: underground, overhead, directional boring
- **Protection Systems**: conduits, sleeves, marker tapes
- **Safety Clearances**: minimum distances between utilities

### Utility Coordination
Analyze utility interactions:
- **Crossing Points**: where utilities intersect
- **Clearance Requirements**: minimum separation distances
- **Conflict Resolution**: utilities sharing space or routes
- **Construction Sequencing**: installation order requirements
- **Protection Measures**: existing utility protection during construction

### Service Adequacy
Assess utility service levels:
- **Capacity vs Demand**: adequate service for property use
- **Redundancy**: backup service availability
- **Future Expansion**: capacity for additional loads
- **Service Quality**: voltage regulation, pressure maintenance
- **Reliability**: service interruption history

## {{ australian_state }} Utility Standards

{% if australian_state == "NSW" %}
**NSW Utility Requirements:**
- Check Ausgrid/Endeavour Energy power standards
- Note Jemena/Australian Gas Networks requirements
- Identify Sydney Water/local water authority standards
- Check NBN Co and telecommunications requirements
{% elif australian_state == "VIC" %}
**VIC Utility Requirements:**
- Verify AusNet/CitiPower/Powercor electrical standards
- Check AusNet Services/Multinet gas requirements
- Note Yarra Valley Water/local water standards
- Identify NBN and telecommunications infrastructure
{% elif australian_state == "QLD" %}
**QLD Utility Requirements:**
- Check Energex/Ergon Energy power standards
- Note Australian Gas Networks requirements
- Identify Urban Utilities/local water authority standards
- Check NBN Co telecommunications requirements
{% endif %}

## Risk Assessment Focus

### Critical Utility Risks
1. **Service Inadequacy**: Insufficient utility capacity for intended use
2. **Connection Delays**: Utility connection timing issues
3. **Easement Conflicts**: Building restrictions due to utility easements
4. **Cost Implications**: Unexpected utility connection or upgrade costs
5. **Access Restrictions**: Utility maintenance access affecting property use
6. **Safety Hazards**: High voltage or high pressure utility safety issues

### Development Impacts
Assess utility constraints on development:
- Building envelope restrictions due to easements
- Additional utility infrastructure requirements
- Service relocation costs for development
- Utility protection requirements during construction

## Output Requirements

Return a valid JSON object following the **UtilityPlanSemantics** schema with:

### Required Base Fields
- `image_type`: "utility_plan"
- `textual_information`: All utility labels and specifications
- `spatial_relationships`: Utility infrastructure interactions
- `semantic_summary`: Utility infrastructure overview
- `property_impact_summary`: Development and connection implications
- `key_findings`: Critical utility discoveries
- `areas_of_concern`: Service or access issues
- `analysis_confidence`: Overall confidence level

### Utility Plan Specific Fields
- `infrastructure_elements`: Complete utility infrastructure mapping
- `utility_types`: All utility services identified
- `service_connections`: Connection points and requirements
- `easement_corridors`: Utility easement boundaries and restrictions
- `meter_locations`: All utility metering points
- `capacity_information`: Service capacity and load data

### Quality Standards
- **Technical Accuracy**: Precise utility specifications
- **Complete Coverage**: Map all visible utility infrastructure
- **Service Assessment**: Evaluate adequacy for property use
- **Risk Identification**: Highlight development constraints
- **Compliance Check**: Reference relevant utility standards

Begin analysis now. Return only the structured JSON output following the UtilityPlanSemantics schema.
