---
type: "user"
category: "instructions"
name: "image_semantics_bushfire_map"
version: "1.0.0"
description: "Bushfire map semantic analysis for fire risk assessment"
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
output_parser: BushfireMapSemantics
tags: ["bushfire", "fire", "risk", "vegetation"]
---

# Bushfire Map Analysis - {{ australian_state }}

You are analyzing a **bushfire map** for an Australian property. Extract comprehensive bushfire risk information, vegetation assessments, and construction requirements following the BushfireMapSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Bushfire Map
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

## Bushfire Risk Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map all fire-related features:**
- **Environmental type**: "bushfire_zone", "vegetation", "slope", "access_route"
- **Risk level**: "low", "medium", "high", "extreme", "catastrophic"
- **Impact area**: fire impact zones and their extent
- **Mitigation measures**: existing fire protection measures

### 2. Bushfire-Specific Fields

#### Bushfire Zones (bushfire_zones)
Identify fire risk classifications:
- **Bushfire Attack Level (BAL)**: BAL-LOW, BAL-12.5, BAL-19, BAL-29, BAL-40, BAL-FZ
- **Bushfire Prone Land**: designated bushfire prone areas
- **Fire Weather Districts**: local fire weather zone classifications
- **Asset Protection Zones (APZ)**: required defensible space areas
- **Strategic Fire Advantage Zones**: planned fire management areas

#### Vegetation Types (vegetation_types)
Classify vegetation and fuel loads:
- **Vegetation classes**: forest, woodland, shrubland, grassland, mallee
- **Fuel load classifications**: light, moderate, heavy fuel loads
- **Vegetation condition**: green, dry, cured, senescent
- **Fire-prone species**: specific high-risk vegetation types
- **Vegetation management zones**: areas requiring fuel reduction

#### Defensible Space (defensible_space)
Map required fire protection zones:
- **Inner Protection Area (IPA)**: 0-19m from buildings
- **Outer Protection Area (OPA)**: 19m+ from buildings
- **Fuel load reduction requirements**: vegetation management needs
- **Asset protection maintenance**: ongoing management obligations
- **Building protection zones**: specific building fire protection areas

#### Evacuation Routes (evacuation_routes)
Identify emergency access and evacuation:
- **Primary evacuation routes**: main roads for emergency egress
- **Secondary evacuation routes**: alternative escape paths
- **Emergency assembly areas**: safe refuge points
- **Emergency vehicle access**: fire service access routes
- **Traffic management points**: evacuation traffic control locations

#### Construction Requirements (construction_requirements)
Document fire-resistant building requirements:
- **AS 3959 compliance**: Australian Standard for bushfire construction
- **BAL-specific requirements**: construction standards for each BAL rating
- **Ember protection**: building design for ember attack
- **Water supply requirements**: fire fighting water access
- **Driveway specifications**: emergency vehicle access standards

## Fire Risk Assessment

### Hazard Analysis
Evaluate bushfire hazard factors:
- **Slope analysis**: upslope fire behavior and radiant heat
- **Aspect analysis**: north-facing vs south-facing fire risk
- **Vegetation proximity**: distance to fire-prone vegetation
- **Fire history**: previous fire events and frequency
- **Climate factors**: rainfall, temperature, wind patterns

### Risk Mitigation
Assess fire protection measures:
- **Fuel reduction**: required vegetation management
- **Water supply**: fire fighting water availability
- **Access adequacy**: emergency vehicle access compliance
- **Building design**: fire-resistant construction requirements
- **Landscape design**: fire-resistant landscaping requirements

### Emergency Planning
Evaluate emergency preparedness:
- **Evacuation planning**: personal emergency plans
- **Communication systems**: emergency warning systems
- **Community facilities**: local fire services and equipment
- **Seasonal restrictions**: fire season building restrictions
- **Insurance implications**: bushfire insurance requirements

## {{ australian_state }} Fire Requirements

{% if australian_state == "NSW" %}
**NSW Bushfire Standards:**
- Check Planning for Bush Fire Protection (PBP) compliance
- Note Rural Fire Service (RFS) requirements
- Identify Environmental Planning and Assessment Act implications
- Check for Special Fire Protection Purpose developments
{% elif australian_state == "VIC" %}
**VIC Bushfire Standards:**
- Verify Planning Scheme bushfire provisions
- Check Country Fire Authority (CFA) requirements
- Note Bushfire Management Overlay (BMO) implications
- Identify Building in Bushfire Prone Areas requirements
{% elif australian_state == "QLD" %}
**QLD Bushfire Standards:**
- Check State Planning Policy bushfire requirements
- Note Queensland Fire and Emergency Services standards
- Identify Planning Scheme bushfire overlay requirements
- Check for Building Code of Australia bushfire provisions
{% endif %}

## Risk Assessment Priorities

### Critical Bushfire Risks
1. **High BAL Rating**: Properties in BAL-29, BAL-40, or BAL-FZ zones
2. **Inadequate Defensible Space**: Insufficient vegetation clearance
3. **Poor Emergency Access**: Limited evacuation or fire service access
4. **Construction Non-Compliance**: Buildings not meeting fire standards
5. **Fuel Load Hazards**: High vegetation fuel loads near buildings
6. **Water Supply Deficiency**: Inadequate fire fighting water access

### Development Implications
Assess bushfire impacts on development:
- Additional construction costs for fire-resistant building
- Ongoing vegetation management obligations
- Emergency access and egress requirements
- Insurance premium implications
- Planning approval complexities

## Output Requirements

Return a valid JSON object following the **BushfireMapSemantics** schema with:

### Required Base Fields
- `image_type`: "bushfire_map"
- `textual_information`: All fire risk labels and classifications
- `spatial_relationships`: Fire risk zones and property interactions
- `semantic_summary`: Bushfire risk overview
- `property_impact_summary`: Development and insurance implications
- `key_findings`: Critical fire risk discoveries
- `areas_of_concern`: High risk bushfire issues
- `analysis_confidence`: Overall confidence level

### Bushfire Map Specific Fields
- `environmental_elements`: All fire-related environmental features
- `bushfire_zones`: Complete fire risk zone mapping
- `vegetation_types`: Vegetation and fuel load classifications
- `defensible_space`: Required asset protection zones
- `evacuation_routes`: Emergency access and evacuation
- `construction_requirements`: Fire-resistant building standards

### Quality Standards
- **Risk Accuracy**: Precise BAL and fire zone boundaries
- **Vegetation Assessment**: Detailed fuel load analysis
- **Compliance Focus**: Relevant fire safety standards
- **Emergency Planning**: Access and evacuation considerations
- **Development Impact**: Construction and insurance implications

Begin analysis now. Return only the structured JSON output following the BushfireMapSemantics schema.
