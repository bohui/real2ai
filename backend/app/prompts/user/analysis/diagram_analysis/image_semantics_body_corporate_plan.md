---
type: "user"
category: "instructions"
name: "image_semantics_body_corporate_plan"
version: "1.0.0"
description: "Body corporate plan semantic analysis for body corporate management structure"
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
output_parser: BodyCorporatePlanSemantics
tags: ["body_corporate", "management", "common_areas", "maintenance"]
---

# Body Corporate Plan Analysis - {{ australian_state }}

You are analyzing a **body corporate plan** for an Australian property. Extract comprehensive body corporate management structure and responsibility information following the BodyCorporatePlanSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Body Corporate Plan
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
- `"label"` - For lot labels, area names, plan references
- `"measurement"` - For dimensions, areas, distances, entitlements
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

### Building Type (building_type)
For `building_elements.building_type`, use ONLY these values:
- `"residential"` - Residential units
- `"commercial"` - Commercial units
- `"mixed_use"` - Mixed use units
- `"other"` - Any other building type

### Management Type (management_type)
For `building_elements.management_type`, use ONLY these values:
- `"exclusive_use"` - Exclusive use areas
- `"common_area"` - Common areas
- `"limited_common"` - Limited common areas
- `"other"` - Any other management type

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

## Body Corporate Plan Analysis Objectives

### 1. Boundary Elements (boundary_elements)
**Map body corporate boundaries and common areas:**
- **Boundary type**: "body_corporate_boundary", "common_area", "exclusive_area", "shared_facility"
- **Boundary markings**: boundaries defining body corporate responsibility
- **Dimensions**: common area sizes and exclusive area allocations
- **Encroachments**: boundary variations or shared responsibilities
- **Easements**: internal easements within body corporate scheme

### 2. Building Elements (building_elements)
**Identify buildings under body corporate control:**
- **Building type**: "common_building", "exclusive_building", "shared_facility", "infrastructure"
- **Construction stage**: existing buildings within body corporate
- **Height restrictions**: building maintenance access requirements
- **Setback requirements**: maintenance access and boundary requirements
- **Building envelope**: areas under body corporate maintenance responsibility

### 3. Body Corporate Specific Fields

#### Management Areas (management_areas)
Document areas under body corporate management:
- **Common Property**: Areas owned and maintained by body corporate
- **Restricted Common Property**: Limited access common areas
- **Exclusive Use Areas**: Areas allocated to specific owners
- **Shared Facilities**: Pools, gyms, gardens, community rooms
- **Service Areas**: Plant rooms, substations, maintenance areas
- **Access Ways**: Common driveways, stairs, lifts, corridors

#### Maintenance Responsibilities (maintenance_responsibilities)
Map maintenance responsibility allocations:
- **Body Corporate Maintenance**: Infrastructure maintained by body corporate
- **Owner Maintenance**: Areas maintained by individual owners
- **Shared Maintenance**: Jointly maintained areas or services
- **Professional Maintenance**: Externally contracted maintenance services
- **Emergency Maintenance**: Urgent repair responsibility arrangements
- **Planned Maintenance**: Scheduled maintenance and replacement programs

#### Common Facilities (common_facilities)
Identify shared facilities and amenities:
- **Recreation Facilities**: Pools, gyms, tennis courts, playgrounds
- **Community Facilities**: Meeting rooms, function centers, libraries
- **Service Facilities**: Laundries, storage areas, mailbox areas
- **Parking Facilities**: Common parking areas and visitor parking
- **Garden Areas**: Landscaped areas and recreational gardens
- **Security Facilities**: Entry systems, CCTV, security lighting

#### Levies Structure (levies_structure)
Document body corporate levy structure information:
- **Administrative Levies**: General body corporate administration costs
- **Maintenance Levies**: Ongoing maintenance and repair costs
- **Sinking Fund Levies**: Long-term capital replacement funds
- **Special Levies**: One-off or extraordinary expense levies
- **Levy Calculation**: Basis for individual owner levy contributions
- **Payment Schedules**: Frequency and timing of levy payments

#### Restrictions (restrictions)
Document body corporate restrictions and rules:
- **Use Restrictions**: Limitations on property and common area use
- **Pet Restrictions**: Animal keeping rules and limitations
- **Noise Restrictions**: Quiet hours and noise control rules
- **Parking Restrictions**: Parking allocation and visitor rules
- **Renovation Restrictions**: Approval requirements for owner modifications
- **Commercial Use Restrictions**: Limitations on business activities

## Body Corporate Assessment

### Governance Structure
Evaluate body corporate management arrangements:
- **Management Type**: Professional, caretaker, or self-management
- **Committee Structure**: Body corporate committee roles and responsibilities
- **Decision Making**: Voting procedures and meeting requirements
- **Dispute Resolution**: Internal and external dispute resolution processes
- **Record Keeping**: Body corporate records and document management

### Financial Management
Assess body corporate financial arrangements:
- **Budget Management**: Annual budgeting and financial planning
- **Reserve Funds**: Adequate reserves for maintenance and repairs
- **Levy Collection**: Efficiency of levy collection and arrears management
- **Insurance Coverage**: Adequate building and public liability insurance
- **Audit Requirements**: Financial audit and reporting requirements

### Facility Management
Evaluate common facility management:
- **Maintenance Standards**: Quality of facility maintenance and presentation
- **Service Contracts**: Professional service provider arrangements
- **Utility Management**: Common area electricity, water, and gas management
- **Security Management**: Access control and security system management
- **Compliance Management**: Regulatory compliance and safety requirements

## {{ australian_state }} Body Corporate Framework

{% if australian_state == "NSW" %}
**NSW Strata/Community Laws:**
- Check Strata Schemes Management Act requirements
- Note Community Land Management Act provisions
- Identify Strata Schemes Development Act implications
- Check for Fair Trading body corporate regulations
{% elif australian_state == "VIC" %}
**VIC Body Corporate Laws:**
- Verify Owners Corporation Act requirements
- Check Owners Corporation Regulations provisions
- Note Consumer Affairs Victoria oversight requirements
- Identify Victorian Civil and Administrative Tribunal jurisdiction
{% elif australian_state == "QLD" %}
**QLD Body Corporate Laws:**
- Check Body Corporate and Community Management Act requirements
- Note Body Corporate and Community Management Regulation provisions
- Identify Office of the Commissioner for Body Corporate oversight
- Check for Queensland Civil and Administrative Tribunal jurisdiction
{% endif %}

## Risk Assessment Focus

### Critical Body Corporate Risks
1. **Poor Management**: Ineffective body corporate administration
2. **High Levies**: Excessive or increasing body corporate costs
3. **Maintenance Issues**: Deferred or inadequate facility maintenance
4. **Financial Problems**: Insufficient reserves or levy collection issues
5. **Governance Disputes**: Committee conflicts or owner disputes
6. **Insurance Gaps**: Inadequate or lapsed body corporate insurance

### Investment Considerations
Assess body corporate investment factors:
- Management quality and committee effectiveness
- Financial stability and reserve fund adequacy
- Facility quality and maintenance standards
- Owner satisfaction and community harmony

## Output Requirements

Return a valid JSON object following the **BodyCorporatePlanSemantics** schema with:

### Required Base Fields
- `image_type`: "body_corporate_plan"
- `textual_information`: All body corporate labels and area designations
- `spatial_relationships`: Common area and boundary relationships
- `semantic_summary`: Body corporate structure overview
- `property_impact_summary`: Management and cost implications
- `key_findings`: Critical body corporate discoveries
- `areas_of_concern`: Management or financial issues
- `analysis_confidence`: Overall confidence level

### Body Corporate Plan Specific Fields
- `boundary_elements`: Body corporate boundary analysis
- `building_elements`: Buildings under body corporate control
- `management_areas`: Areas under body corporate management
- `maintenance_responsibilities`: Maintenance responsibility allocations
- `common_facilities`: Shared facilities and amenities
- `levies_structure`: Body corporate levy structure information
- `restrictions`: Body corporate restrictions and rules

### Quality Standards
- **Management Accuracy**: Precise responsibility and boundary identification
- **Financial Analysis**: Body corporate cost and levy assessment
- **Governance Assessment**: Management quality and effectiveness evaluation
- **Facility Evaluation**: Common facility quality and maintenance assessment
- **Investment Focus**: Suitable for body corporate property investment decisions

Begin analysis now. Return only the structured JSON output following the BodyCorporatePlanSemantics schema.
