---
type: "user"
category: "instructions"
name: "image_semantics_parking_plan"
version: "1.0.0"
description: "Parking plan semantic analysis for parking and vehicle circulation"
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
output_parser: ParkingPlanSemantics
tags: ["parking", "vehicles", "circulation", "access"]
---

# Parking Plan Analysis - {{ australian_state }}

You are analyzing a **parking plan** for an Australian property. Extract comprehensive parking and vehicle circulation information following the ParkingPlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Parking Plan
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

## Parking Plan Analysis Objectives

### 1. Infrastructure Elements (infrastructure_elements)
**Document parking areas and vehicle circulation:**
- **Infrastructure type**: "parking_space", "driveway", "access_road", "circulation_area"
- **Construction specifications**: Pavement types and construction standards
- **Drainage requirements**: Stormwater management for parking areas
- **Safety features**: Lighting, signage, and security measures
- **Access control**: Entry/exit controls and barriers

### 2. Parking Plan Specific Fields

#### Parking Spaces (parking_spaces)
Document number and types of parking spaces:
- **Total Parking Spaces**: Overall parking capacity
- **Residential Parking**: Parking allocated to residential units
- **Visitor Parking**: Parking for visitors and guests
- **Commercial Parking**: Parking for commercial/retail uses
- **Staff Parking**: Employee parking areas
- **Motorcycle Parking**: Dedicated motorcycle spaces
- **Bicycle Parking**: Bicycle storage and parking areas

#### Access Arrangements (access_arrangements)
Map vehicle access and circulation routes:
- **Vehicle Entry Points**: Access from public roads
- **Vehicle Exit Points**: Egress to public roads
- **Internal Circulation**: Vehicle movement within site
- **One-way Systems**: Directional traffic flow controls
- **Emergency Access**: Fire service and emergency vehicle access
- **Service Vehicle Access**: Garbage collection and delivery access

#### Disabled Access (disabled_access)
Identify disabled parking and access provisions:
- **Disabled Parking Spaces**: Number and location of accessible spaces
- **Accessible Routes**: Pathways from disabled parking to buildings
- **Gradient Compliance**: Accessible parking and pathway gradients
- **Space Dimensions**: Disabled parking space sizes and clearances
- **Signage Requirements**: Required disabled parking signage
- **Drop-off Areas**: Accessible passenger loading zones

#### Visitor Parking (visitor_parking)
Document visitor parking arrangements:
- **Visitor Space Numbers**: Total visitor parking capacity
- **Visitor Space Locations**: Convenient visitor parking areas
- **Time Restrictions**: Parking time limits for visitors
- **Permit Requirements**: Visitor parking permit systems
- **Overflow Parking**: Additional parking during peak periods
- **Public Transport Access**: Proximity to public transport

#### Loading Areas (loading_areas)
Map loading and service vehicle areas:
- **Loading Bay Locations**: Designated loading and unloading areas
- **Service Vehicle Access**: Routes for delivery and service vehicles
- **Turning Areas**: Space for large vehicle maneuvering
- **Time Restrictions**: Limited hours for loading activities
- **Waste Collection**: Garbage and recycling collection areas
- **Emergency Services**: Access for emergency and maintenance vehicles

## Parking Assessment

### Compliance Evaluation
Assess parking provision compliance:
- **Planning Requirements**: Minimum parking space compliance
- **Accessibility Standards**: Disabled access compliance
- **Safety Standards**: Lighting, signage, and visibility compliance
- **Design Standards**: Parking space dimensions and layout compliance
- **Traffic Engineering**: Circulation and access design adequacy

### Capacity Analysis
Evaluate parking adequacy:
- **Peak Demand**: Parking demand during busy periods
- **Space Utilization**: Efficiency of parking space layout
- **Future Needs**: Parking capacity for potential development
- **Alternative Transport**: Reduced parking for public transport access
- **Car Share**: Provision for car sharing and electric vehicles

### Operational Considerations
Assess parking operation factors:
- **Management Systems**: Parking control and enforcement
- **Maintenance Requirements**: Cleaning, repairs, and surface maintenance
- **Security Measures**: Surveillance, lighting, and access control
- **Environmental Impact**: Stormwater, landscaping, and urban heat
- **Cost Implications**: Construction, maintenance, and operational costs

## {{ australian_state }} Parking Standards

{% if australian_state == "NSW" %}
**NSW Parking Requirements:**
- Check Local Environment Plan parking provisions
- Note State Environmental Planning Policy parking rates
- Identify Roads and Maritime Services access requirements
- Check for car sharing and sustainable transport provisions
{% elif australian_state == "VIC" %}
**VIC Parking Requirements:**
- Verify Planning Scheme parking provisions
- Check VicRoads access and traffic requirements
- Note Disability Discrimination Act accessibility requirements
- Identify sustainable transport parking reductions
{% elif australian_state == "QLD" %}
**QLD Parking Requirements:**
- Check Planning Scheme parking provisions
- Note Department of Transport and Main Roads requirements
- Identify Queensland Development Code parking standards
- Check for public transport parking reductions
{% endif %}

## Risk Assessment Focus

### Critical Parking Risks
1. **Inadequate Parking**: Insufficient parking for intended use
2. **Access Safety Issues**: Poor visibility or dangerous access arrangements
3. **Non-Compliance**: Failure to meet planning or accessibility requirements
4. **Traffic Conflicts**: Vehicle circulation conflicts with pedestrians
5. **Emergency Access**: Inadequate emergency vehicle access
6. **Future Capacity**: Insufficient parking for development expansion

### Parking Opportunities
Assess positive parking aspects:
- Convenient and accessible parking provision
- Potential for shared parking arrangements
- Electric vehicle charging infrastructure
- Integration with public transport

## Output Requirements

Return a valid JSON object following the **ParkingPlanSemantics** schema with:

### Required Base Fields
- `image_type`: "parking_plan"
- `textual_information`: All parking labels and circulation markings
- `spatial_relationships`: Parking and circulation element relationships
- `semantic_summary`: Parking and access overview
- `property_impact_summary`: Parking adequacy and compliance implications
- `key_findings`: Critical parking discoveries
- `areas_of_concern`: Parking adequacy or safety issues
- `analysis_confidence`: Overall confidence level

### Parking Plan Specific Fields
- `infrastructure_elements`: Parking areas and vehicle circulation
- `parking_spaces`: Number and types of parking spaces
- `access_arrangements`: Vehicle access and circulation routes
- `disabled_access`: Disabled parking and accessibility provisions
- `visitor_parking`: Visitor parking arrangements
- `loading_areas`: Loading and service vehicle areas

### Quality Standards
- **Capacity Accuracy**: Precise parking space counts and dimensions
- **Compliance Assessment**: Planning and accessibility standard compliance
- **Safety Analysis**: Vehicle and pedestrian safety evaluation
- **Access Evaluation**: Emergency and service vehicle access adequacy
- **Operational Assessment**: Parking management and maintenance considerations

Begin analysis now. Return only the structured JSON output following the ParkingPlanSemantics schema.
