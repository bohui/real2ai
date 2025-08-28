---
type: "user"
category: "instructions"
name: "image_semantics_environmental_overlay"
version: "1.0.0"
description: "Environmental overlay semantic analysis for environmental protection and restrictions"
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
output_parser: EnvironmentalOverlaySemantics
tags: ["environmental", "overlay", "protection", "conservation"]
---

# Environmental Overlay Analysis - {{ australian_state }}

You are analyzing an **environmental overlay** for an Australian property. Extract comprehensive environmental protection and restriction information following the EnvironmentalOverlaySemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Environmental Overlay
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
- `"label"` - For overlay labels, area names, plan references
- `"measurement"` - For dimensions, areas, distances, boundaries
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
- `"vegetation"` - Natural vegetation areas
- `"water_body"` - Water bodies
- `"wetland"` - Wetland areas
- `"habitat"` - Wildlife habitat areas
- `"other"` - Any other environmental feature

### Protection Level (protection_level)
For `environmental_elements.protection_level`, use ONLY these values:
- `"high"` - High protection areas
- `"medium"` - Medium protection areas
- `"low"` - Low protection areas
- `"other"` - Any other protection level

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Environmental Overlay Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map all environmental features and restrictions:**
- **Environmental type**: "vegetation", "waterway", "wetland", "habitat", "contamination", "slope"
- **Risk level**: environmental significance and protection level
- **Impact area**: environmental constraint boundaries
- **Mitigation measures**: required environmental protection measures

### 2. Environmental Overlay Specific Fields

#### Overlay Zones (overlay_zones)
Identify all environmental overlay areas:
- **Vegetation Protection Overlays**: Native vegetation conservation areas
- **Waterway Protection Overlays**: Creek, river, and wetland buffers
- **Biodiversity Conservation Overlays**: Habitat protection areas
- **Erosion Management Overlays**: Slope and soil protection areas
- **Contaminated Land Overlays**: Areas with soil/groundwater contamination
- **Salinity Management Overlays**: Areas affected by dryland salinity

#### Protected Areas (protected_areas)
Document environmental protection zones:
- **Endangered Ecological Communities**: Critically important habitat areas
- **Riparian Vegetation**: Waterway vegetation protection zones
- **Coastal Protection Areas**: Foreshore and coastal vegetation
- **Wildlife Corridors**: Animal movement and habitat connection areas
- **Tree Preservation Orders**: Individual or groups of protected trees
- **Wetland Protection Areas**: Swamps, marshes, and water bodies

#### Development Restrictions (development_restrictions)
Map development limitations:
- **Building Exclusion Zones**: Areas where no development permitted
- **Setback Requirements**: Minimum distances from environmental features
- **Clearing Restrictions**: Limitations on vegetation removal
- **Construction Methodology**: Special building techniques required
- **Access Restrictions**: Limitations on vehicle and machinery access
- **Timing Restrictions**: Seasonal construction limitations

#### Vegetation Controls (vegetation_controls)
Document vegetation management requirements:
- **Native Vegetation Retention**: Existing vegetation to be preserved
- **Revegetation Requirements**: Areas requiring new planting
- **Weed Management Obligations**: Invasive species control requirements
- **Tree Protection During Construction**: Root zone and canopy protection
- **Landscape Species Requirements**: Approved plant species for landscaping
- **Maintenance Obligations**: Ongoing vegetation care responsibilities

## Environmental Assessment

### Conservation Significance
Evaluate environmental value:
- **Ecological Importance**: Biodiversity and habitat significance
- **Connectivity Value**: Role in broader environmental corridors
- **Rarity Assessment**: Presence of rare or endangered species
- **Water Quality Protection**: Role in protecting water resources
- **Erosion Control**: Importance for slope and soil stability

### Development Impacts
Assess environmental constraints on development:
- **Developable Area Reduction**: Loss of usable site area
- **Construction Cost Increases**: Additional environmental compliance costs
- **Approval Complexity**: Extended development approval processes
- **Offset Requirements**: Environmental compensation obligations
- **Ongoing Management**: Long-term environmental stewardship costs

### Compliance Requirements
Document regulatory obligations:
- **Permit Requirements**: Environmental approvals needed
- **Impact Assessment**: Required environmental studies
- **Monitoring Obligations**: Ongoing environmental monitoring
- **Reporting Requirements**: Regular compliance reporting
- **Enforcement Risks**: Penalties for non-compliance

## {{ australian_state }} Environmental Framework

{% if australian_state == "NSW" %}
**NSW Environmental Controls:**
- Check Biodiversity Conservation Act requirements
- Note Native Vegetation Regulation compliance
- Identify Water Management Act implications
- Check for Threatened Species Conservation Act coverage
{% elif australian_state == "VIC" %}
**VIC Environmental Controls:**
- Verify Flora and Fauna Guarantee Act requirements
- Check Native Vegetation Permitted Clearing Regulations
- Note Water Act and Catchment and Land Protection Act implications
- Identify Environment Protection Act contamination requirements
{% elif australian_state == "QLD" %}
**QLD Environmental Controls:**
- Check Vegetation Management Act requirements
- Note Environmental Protection Act compliance
- Identify Nature Conservation Act implications
- Check for Marine Parks Act or Fisheries Act coverage
{% endif %}

## Risk Assessment Focus

### Critical Environmental Risks
1. **Severe Development Restrictions**: Major limitations on land use
2. **High Compliance Costs**: Expensive environmental protection requirements
3. **Approval Delays**: Extended approval processes for development
4. **Offset Obligations**: Requirements to provide environmental compensation
5. **Ongoing Management Costs**: Long-term environmental stewardship expenses
6. **Enforcement Action Risk**: Penalties for environmental non-compliance

### Environmental Opportunities
Assess positive environmental aspects:
- Enhanced property amenity from natural features
- Potential for environmental grants or incentives
- Marketing advantages from environmental credentials
- Carbon sequestration and biodiversity benefits

## Output Requirements

Return a valid JSON object following the **EnvironmentalOverlaySemantics** schema with:

### Required Base Fields
- `image_type`: "environmental_overlay"
- `textual_information`: All environmental labels and restrictions
- `spatial_relationships`: Environmental feature and property interactions
- `semantic_summary`: Environmental protection overview
- `property_impact_summary`: Development restrictions and opportunities
- `key_findings`: Critical environmental discoveries
- `areas_of_concern`: Environmental compliance or restriction issues
- `analysis_confidence`: Overall confidence level

### Environmental Overlay Specific Fields
- `environmental_elements`: All environmental features and constraints
- `overlay_zones`: Environmental overlay area classifications
- `protected_areas`: Designated environmental protection zones
- `development_restrictions`: Development limitation areas
- `vegetation_controls`: Vegetation management requirements

### Quality Standards
- **Environmental Accuracy**: Precise environmental boundary identification
- **Compliance Focus**: Emphasize regulatory requirements
- **Impact Assessment**: Clear development restriction analysis
- **Conservation Value**: Assess environmental significance
- **Management Requirements**: Document ongoing environmental obligations

Begin analysis now. Return only the structured JSON output following the EnvironmentalOverlaySemantics schema.
