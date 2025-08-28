---
type: "user"
category: "instructions"
name: "image_semantics_heritage_overlay"
version: "1.0.0"
description: "Heritage overlay semantic analysis for heritage protection and restrictions"
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
output_parser: HeritageOverlaySemantics
tags: ["heritage", "conservation", "protection", "historic"]
---

# Heritage Overlay Analysis - {{ australian_state }}

You are analyzing a **heritage overlay** for an Australian property. Extract comprehensive heritage protection and conservation requirement information following the HeritageOverlaySemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Heritage Overlay
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
- `"label"` - For heritage labels, area names, plan references
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
- `"heritage_zone"` - Heritage protection zones
- `"heritage_item"` - Individual heritage items
- `"conservation_area"` - Conservation areas
- `"archaeological"` - Archaeological sites
- `"other"` - Any other environmental feature

### Heritage Significance (heritage_significance)
For `environmental_elements.heritage_significance`, use ONLY these values:
- `"state"` - State heritage significance
- `"local"` - Local heritage significance
- `"national"` - National heritage significance
- `"other"` - Any other heritage significance

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Heritage Overlay Analysis Objectives

### 1. Environmental Elements (environmental_elements)
**Map heritage areas and protected features:**
- **Environmental type**: "heritage_building", "heritage_area", "conservation_area", "archaeological_site"
- **Risk level**: heritage significance and protection level
- **Impact area**: heritage constraint boundaries
- **Mitigation measures**: required heritage conservation measures

### 2. Building Elements (building_elements)
**Identify heritage buildings and structures:**
- **Building type**: "heritage_building", "contributory_building", "non_contributory_building"
- **Construction stage**: existing heritage structures
- **Height restrictions**: heritage-appropriate height limitations
- **Setback requirements**: heritage context setback requirements
- **Building envelope**: heritage-sensitive development areas

### 3. Heritage Overlay Specific Fields

#### Heritage Significance (heritage_significance)
Document heritage value and importance:
- **State Heritage Register Listings**: Properties on state heritage registers
- **National Heritage List**: Commonwealth heritage listed properties
- **Local Heritage Items**: Council heritage inventory items
- **Heritage Conservation Areas**: Broader heritage precincts
- **Indigenous Heritage Sites**: Aboriginal or Torres Strait Islander cultural sites
- **Archaeological Potential**: Areas with potential archaeological remains

#### Protection Requirements (protection_requirements)
Map heritage protection measures:
- **Fabric Conservation**: Requirements to preserve original building materials
- **Form and Setting**: Protection of building form and landscape setting
- **Views and Vistas**: Protection of views to/from heritage places
- **Curtilage Protection**: Protection of heritage building surrounds
- **Interpretation Requirements**: Heritage interpretation and signage
- **Conservation Management Plans**: Required heritage management documents

#### Development Controls (development_controls)
Document heritage development restrictions:
- **Demolition Controls**: Restrictions on demolition or removal
- **Alteration Controls**: Requirements for heritage-sensitive alterations
- **Addition Controls**: Controls on new additions to heritage buildings
- **Subdivision Controls**: Restrictions on heritage property subdivision
- **Tree Removal Controls**: Protection of heritage significant vegetation
- **Advertising Sign Controls**: Restrictions on commercial signage

#### Conservation Areas (conservation_areas)
Identify heritage conservation precincts:
- **Heritage Precincts**: Broader areas of heritage significance
- **Character Areas**: Areas with consistent historic character
- **Streetscape Protection**: Protection of historic street patterns
- **Landmark Buildings**: Key buildings defining area character
- **Historic Districts**: Areas with coordinated heritage themes
- **Buffer Zones**: Areas protecting heritage place settings

#### Permit Requirements (permit_requirements)
Document heritage approval obligations:
- **Heritage Permits**: Required heritage approvals for works
- **Development Applications**: Planning approvals with heritage assessment
- **Building Permits**: Building approvals with heritage conditions
- **Tree Removal Permits**: Approvals for vegetation removal
- **Demolition Permits**: Special permits for heritage building demolition
- **Archaeological Permits**: Approvals for ground-disturbing works

## Heritage Assessment

### Heritage Value Analysis
Evaluate heritage significance:
- **Historic Significance**: Association with historic events or periods
- **Aesthetic Significance**: Architectural or landscape design value
- **Scientific Significance**: Technical or research importance
- **Social Significance**: Community cultural or social value
- **Rarity**: Uniqueness or representative importance
- **Integrity**: Degree of intactness and authenticity

### Development Impact Assessment
Assess heritage constraints on development:
- **Development Limitations**: Restrictions on building modifications
- **Design Requirements**: Heritage-appropriate design standards
- **Material Requirements**: Use of traditional or compatible materials
- **Approval Complexity**: Extended heritage approval processes
- **Cost Implications**: Additional heritage compliance costs
- **Professional Requirements**: Need for heritage specialists

### Conservation Planning
Evaluate ongoing heritage management:
- **Maintenance Standards**: Required heritage building maintenance
- **Conservation Works**: Planned heritage restoration projects
- **Management Obligations**: Ongoing heritage stewardship responsibilities
- **Interpretation Opportunities**: Heritage tourism and education potential
- **Grant Opportunities**: Available heritage conservation funding

## {{ australian_state }} Heritage Framework

{% if australian_state == "NSW" %}
**NSW Heritage System:**
- Check Heritage Act 1977 State Heritage Register listings
- Note Local Environment Plan heritage provisions
- Identify Aboriginal Land Rights Act implications
- Check for National Parks and Wildlife Act coverage
{% elif australian_state == "VIC" %}
**VIC Heritage System:**
- Verify Heritage Act 2017 Victorian Heritage Register listings
- Check Planning Scheme Heritage Overlay provisions
- Note Aboriginal Heritage Act 2006 requirements
- Identify National Trust or local heritage classifications
{% elif australian_state == "QLD" %}
**QLD Heritage System:**
- Check Queensland Heritage Act heritage register listings
- Note Planning Scheme heritage overlay provisions
- Identify Aboriginal Cultural Heritage Act requirements
- Check for National Trust or local heritage significance
{% endif %}

## Risk Assessment Focus

### Critical Heritage Risks
1. **Severe Development Restrictions**: Major limitations on property modification
2. **High Compliance Costs**: Expensive heritage-appropriate materials and methods
3. **Extended Approval Processes**: Lengthy heritage approval requirements
4. **Ongoing Maintenance Obligations**: Expensive heritage building maintenance
5. **Professional Service Requirements**: Need for specialized heritage consultants
6. **Enforcement Action Risk**: Penalties for unauthorized heritage works

### Heritage Opportunities
Assess positive heritage aspects:
- Heritage grants and funding opportunities
- Tourism and commercial heritage value
- Marketing advantages from heritage significance
- Community recognition and prestige

## Output Requirements

Return a valid JSON object following the **HeritageOverlaySemantics** schema with:

### Required Base Fields
- `image_type`: "heritage_overlay"
- `textual_information`: All heritage labels and classifications
- `spatial_relationships`: Heritage area and property interactions
- `semantic_summary`: Heritage protection overview
- `property_impact_summary`: Development restrictions and opportunities
- `key_findings`: Critical heritage discoveries
- `areas_of_concern`: Heritage compliance or restriction issues
- `analysis_confidence`: Overall confidence level

### Heritage Overlay Specific Fields
- `environmental_elements`: Heritage areas and protected features
- `building_elements`: Heritage buildings and structures
- `heritage_significance`: Heritage value categories and ratings
- `protection_requirements`: Heritage conservation measures
- `development_controls`: Heritage development restrictions
- `conservation_areas`: Heritage precinct boundaries
- `permit_requirements`: Heritage approval obligations

### Quality Standards
- **Heritage Accuracy**: Precise heritage boundary and classification identification
- **Significance Assessment**: Clear heritage value analysis
- **Compliance Focus**: Emphasize heritage regulatory requirements
- **Development Impact**: Assess modification and development limitations
- **Conservation Planning**: Include ongoing heritage management requirements

Begin analysis now. Return only the structured JSON output following the HeritageOverlaySemantics schema.
