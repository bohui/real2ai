---
type: "user"
category: "instructions"
name: "image_semantics_landscape_plan"
version: "1.0.0"
description: "Landscape plan semantic analysis for vegetation and landscape requirements"
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
output_parser: LandscapePlanSemantics
tags: ["landscape", "vegetation", "gardens", "trees"]
---

# Landscape Plan Analysis - {{ australian_state }}

You are analyzing a **landscape plan** for an Australian property. Extract comprehensive vegetation and landscape requirement information following the LandscapePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Landscape Plan
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

## Landscape Plan Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map vegetation and landscape features:**
- **Environmental type**: "existing_vegetation", "proposed_vegetation", "landscape_feature", "hardscape"
- **Risk level**: vegetation protection and management requirements
- **Impact area**: landscape treatment zones
- **Mitigation measures**: vegetation protection and establishment requirements

### 2. Landscape Plan Specific Fields

#### Vegetation Zones (vegetation_zones)
Document existing and proposed vegetation areas:
- **Existing Vegetation**: Native trees, shrubs, and groundcover to retain
- **Proposed Vegetation**: New plantings and landscape treatments
- **Vegetation Types**: Native, exotic, edible, ornamental plant categories
- **Planting Zones**: Different landscape character areas
- **Succession Planting**: Staged vegetation establishment programs
- **Restoration Areas**: Areas requiring ecological restoration

#### Tree Preservation (tree_preservation)
Identify trees to be preserved or protected:
- **Significant Trees**: Large, mature, or rare trees requiring protection
- **Tree Protection Zones**: Root zone and canopy protection areas
- **Construction Impact**: Trees affected by development
- **Tree Removal**: Trees approved for removal or relocation
- **Tree Replacement**: Required replacement trees for removed vegetation
- **Tree Maintenance**: Ongoing tree care and management requirements

#### Planting Requirements (planting_requirements)
Document required landscaping and planting:
- **Minimum Landscaping**: Required landscape area percentages
- **Species Requirements**: Specific plant species or types required
- **Planting Densities**: Trees, shrubs, and groundcover densities
- **Plant Sizes**: Minimum plant sizes at installation
- **Planting Seasons**: Optimal timing for plant establishment
- **Establishment Periods**: Required plant establishment and maintenance periods

#### Irrigation Systems (irrigation_systems)
Map water management and irrigation:
- **Irrigation Types**: Drip, sprinkler, subsurface irrigation systems
- **Water Sources**: Mains water, rainwater, recycled water sources
- **Irrigation Zones**: Different watering requirement areas
- **Water Efficiency**: Water-wise landscaping and conservation measures
- **Automatic Systems**: Programmable irrigation controllers
- **Maintenance Access**: Access for irrigation system maintenance

#### Hardscape Elements (hardscape_elements)
Document paved areas and structures:
- **Paved Areas**: Driveways, paths, patios, and courtyards
- **Retaining Walls**: Terracing and slope retention structures
- **Fencing**: Privacy, security, and boundary fencing
- **Outdoor Structures**: Pergolas, gazebos, sheds, and storage
- **Water Features**: Ponds, fountains, and decorative water elements
- **Lighting**: Landscape and security lighting systems

## Landscape Assessment

### Design Compliance
Evaluate landscape design compliance:
- **Planning Requirements**: Minimum landscape area compliance
- **Species Compliance**: Native vegetation or approved species use
- **Water Restrictions**: Compliance with water conservation requirements
- **Fire Safety**: Appropriate vegetation for bushfire risk areas
- **Maintenance Requirements**: Realistic maintenance expectations

### Environmental Benefits
Assess landscape environmental advantages:
- **Biodiversity Support**: Habitat provision for native wildlife
- **Stormwater Management**: Landscape contribution to drainage
- **Carbon Sequestration**: Tree and vegetation carbon storage
- **Microclimate**: Cooling and air quality benefits
- **Soil Stabilization**: Erosion control and soil improvement

### Maintenance Considerations
Evaluate ongoing landscape management:
- **Maintenance Costs**: Estimated annual landscape maintenance
- **Water Requirements**: Irrigation needs and water costs
- **Professional Services**: Need for landscape maintenance contractors
- **Seasonal Care**: Pruning, fertilizing, and seasonal plant care
- **Replacement Cycles**: Expected plant replacement and renewal

## {{ australian_state }} Landscape Requirements

{% if australian_state == "NSW" %}
**NSW Landscape Standards:**
- Check Local Environment Plan landscaping provisions
- Note BASIX water efficiency landscaping requirements
- Identify native vegetation protection requirements
- Check for tree preservation order compliance
{% elif australian_state == "VIC" %}
**VIC Landscape Standards:**
- Verify Planning Scheme landscaping requirements
- Check Native Vegetation Permitted Clearing Regulations
- Note significant tree protection provisions
- Identify water restriction landscaping compliance
{% elif australian_state == "QLD" %}
**QLD Landscape Standards:**
- Check Planning Scheme landscaping provisions
- Note Vegetation Management Act requirements
- Identify water efficiency landscaping standards
- Check for significant tree protection requirements
{% endif %}

## Risk Assessment Focus

### Critical Landscape Risks
1. **Non-Compliance**: Failure to meet landscape area or species requirements
2. **Establishment Failure**: Poor plant survival and establishment
3. **High Maintenance Costs**: Expensive ongoing landscape maintenance
4. **Water Restrictions**: Limitations on landscape irrigation
5. **Tree Damage**: Damage to significant trees during construction
6. **Neighbor Disputes**: Boundary vegetation and privacy issues

### Landscape Opportunities
Assess positive landscape aspects:
- Enhanced property value from quality landscaping
- Environmental benefits and sustainability credentials
- Outdoor lifestyle and recreational opportunities
- Privacy and microclimate improvements

## Output Requirements

Return a valid JSON object following the **LandscapePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "landscape_plan"
- `textual_information`: All landscape labels and plant specifications
- `spatial_relationships`: Landscape element relationships
- `semantic_summary`: Landscape design overview
- `property_impact_summary`: Landscape maintenance and compliance implications
- `key_findings`: Critical landscape discoveries
- `areas_of_concern`: Landscape compliance or maintenance issues
- `analysis_confidence`: Overall confidence level

### Landscape Plan Specific Fields
- `environmental_elements`: Vegetation and landscape features
- `vegetation_zones`: Existing and proposed vegetation areas
- `tree_preservation`: Trees to be preserved or protected
- `planting_requirements`: Required landscaping and planting
- `irrigation_systems`: Water management and irrigation
- `hardscape_elements`: Paved areas and landscape structures

### Quality Standards
- **Plant Accuracy**: Precise vegetation species and location identification
- **Compliance Focus**: Emphasize landscape regulatory requirements
- **Maintenance Assessment**: Realistic ongoing maintenance evaluation
- **Environmental Benefits**: Assess ecological and sustainability advantages
- **Design Integration**: Evaluate landscape design cohesion and functionality

Begin analysis now. Return only the structured JSON output following the LandscapePlanSemantics schema.
