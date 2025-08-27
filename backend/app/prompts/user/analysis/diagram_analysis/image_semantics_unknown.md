---
type: "user"
category: "instructions"
name: "image_semantics_unknown"
version: "1.0.0"
description: "Generic diagram semantic analysis for unclassified diagram types"
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
output_parser: GenericDiagramSemantics
tags: ["unknown", "generic", "analysis", "property"]
---

# Generic Diagram Analysis - {{ australian_state }}

You are analyzing an **unclassified diagram** for an Australian property. Extract all visible semantic information using general analysis principles following the GenericDiagramSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Unknown/Unclassified
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

## General Analysis Objectives

Since this diagram type is unclassified, perform comprehensive analysis to identify:

### 1. Diagram Type Classification
**Attempt to identify the diagram type:**
- Examine title, headers, and labels for type indicators
- Look for characteristic elements of known diagram types
- Note scale, orientation, and technical specifications
- Identify the primary purpose and focus of the diagram

### 2. Content Analysis Strategy
**Systematic element identification:**
- **Infrastructure Elements**: Any pipes, cables, utilities, services
- **Boundary Elements**: Property lines, easements, setbacks, restrictions
- **Building Elements**: Structures, buildings, improvements, development
- **Environmental Elements**: Natural features, hazards, constraints, overlays

### 3. Text and Label Extraction
**Comprehensive text analysis:**
- Extract ALL visible text, labels, and annotations
- Note technical specifications and measurements
- Identify legend and key information
- Record reference numbers and administrative details
- Preserve scale and orientation information

### 4. Spatial Analysis
**Map spatial relationships:**
- Use normalized coordinates (0-1 scale) for all elements
- Document element positions relative to property boundaries
- Note proximity relationships and potential conflicts
- Measure distances and dimensions where visible

## Risk-Focused Analysis

### Property Impact Assessment
Evaluate how diagram content affects property:
- **Development Constraints**: Any limitations on building or use
- **Legal Obligations**: Compliance requirements or restrictions
- **Infrastructure Requirements**: Service connections or upgrades needed
- **Environmental Constraints**: Natural hazards or protected areas
- **Access Requirements**: Vehicle, pedestrian, or emergency access

### Compliance Considerations
Check for regulatory implications:
- **Planning Requirements**: Zoning, overlays, development controls
- **Building Standards**: Construction standards and requirements
- **Environmental Regulations**: Conservation, contamination, hazards
- **Utility Standards**: Service connection and capacity requirements

## {{ australian_state }} Context

{% if australian_state == "NSW" %}
**NSW Considerations:**
- Apply relevant NSW planning and building standards
- Consider Environmental Planning and Assessment Act implications
- Note potential Heritage Act or contamination issues
- Check for coastal, flood, or bushfire considerations
{% elif australian_state == "VIC" %}
**VIC Considerations:**
- Apply relevant VIC planning scheme provisions
- Consider Building Act and regulations
- Note potential Heritage Act or EPA implications
- Check for native vegetation or environmental overlays
{% elif australian_state == "QLD" %}
**QLD Considerations:**
- Apply relevant QLD planning scheme provisions
- Consider Building Act and development standards
- Note potential State Planning Policy implications
- Check for vegetation management or environmental constraints
{% endif %}

## Analysis Quality Standards

### Completeness Requirements
- **Element Coverage**: Identify every visible element
- **Text Extraction**: Capture all readable text and numbers
- **Measurement Recording**: Extract all dimensions and specifications
- **Relationship Mapping**: Document spatial interactions

### Risk Assessment
- **Development Impact**: How does this diagram affect property development?
- **Legal Implications**: Are there legal obligations or restrictions?
- **Financial Impact**: Do diagram elements affect property value or costs?
- **Safety Considerations**: Are there safety or access concerns?

### Uncertainty Management
- **Confidence Levels**: Use appropriate confidence ratings
- **Missing Information**: Note areas requiring further investigation
- **Partial Visibility**: Handle unclear or partially visible elements
- **Recommendation**: Suggest diagram reclassification if possible

## Output Requirements

Return a valid JSON object following the **GenericDiagramSemantics** schema with:

### Required Base Fields
- `image_type`: "unknown"
- `textual_information`: All extracted text with locations and types
- `spatial_relationships`: All element interactions and proximities
- `semantic_summary`: Overview of diagram content and purpose
- `property_impact_summary`: How diagram affects property understanding
- `key_findings`: Most important discoveries from analysis
- `areas_of_concern`: Issues requiring attention or investigation
- `analysis_confidence`: Overall confidence in analysis

### Analysis Metadata
- `processing_notes`: Notes about analysis approach and limitations
- `suggested_followup`: Recommendations for further investigation
- Include any potential diagram type reclassification suggestions

### Quality Standards
- **Comprehensive Coverage**: Extract maximum information from available content
- **Risk Focus**: Emphasize property development and ownership impacts
- **Professional Standard**: Suitable for legal and technical review
- **Uncertainty Handling**: Clear about limitations and confidence levels

Begin analysis now. Return only the structured JSON output following the GenericDiagramSemantics schema.
