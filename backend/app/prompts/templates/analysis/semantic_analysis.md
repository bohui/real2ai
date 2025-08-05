---
type: "user"
category: "analysis"
name: "semantic_analysis"
version: "1.0.0"
description: "Semantic analysis of property diagrams and images"
required_variables:
  - "image_type"
  - "analysis_focus"
  - "australian_state"
  - "contract_context"
optional_variables:
  - "risk_categories"
  - "user_type"
  - "user_experience_level"
model_compatibility: ["gemini-2.5-pro", "gpt-4-vision"]
max_tokens: 10000
temperature_range: [0.1, 0.3]
tags: ["semantic", "analysis", "property", "diagrams", "images"]
---

# Semantic Analysis Instructions

Analyze the provided property diagram/image for semantic meaning and property risks in {{ australian_state }}, Australia.

## Analysis Context

- **Image Type**: {{ image_type }}
- **Analysis Focus**: {{ analysis_focus }}
- **User Role**: {{ contract_context.user_type | default("buyer") }}
- **Experience Level**: {{ contract_context.user_experience_level | default("novice") }}
- **Contract Type**: {{ contract_context.contract_type | default("purchase_agreement") }}

## Semantic Analysis Framework

### 1. Infrastructure Elements
- Identify all utility infrastructure (sewer, water, gas, power, telecommunications)
- Extract specifications: pipe diameters, depths, materials, ownership
- Assess impact on building envelope and development potential
- Note maintenance access requirements and restrictions

### 2. Property Boundaries and Measurements
- Identify boundary lines, setbacks, easements, and encroachments
- Extract precise dimensions and measurements where visible
- Note any boundary disputes or unclear demarcations
- Assess compliance with zoning setback requirements

### 3. Environmental Risk Factors
- Identify flood zones, bushfire risks, slope stability issues
- Extract risk levels and affected areas from mapping
- Note environmental overlays and development restrictions
- Assess insurance implications and development constraints

### 4. Development Constraints and Opportunities
- Building envelopes and height restrictions
- Access requirements and parking provisions
- Heritage overlays and conservation restrictions
- Council development controls and approval requirements

## State-Specific Analysis Requirements

{{ state_specific_analysis_fragments }}

## Risk Assessment Framework

For each identified element, evaluate:

**Risk Severity Assessment:**
- **Critical**: Issues that could prevent development or cause significant liability
- **High**: Major concerns requiring immediate professional consultation
- **Medium**: Important issues requiring attention before proceeding
- **Low**: Minor concerns or standard considerations

**Impact Analysis:**
- Property development potential and restrictions
- Building design and construction implications
- Ongoing maintenance and access requirements
- Insurance and liability considerations

## Professional Consultation Matrix

Based on identified elements, recommend:

- **Structural Engineer**: Foundation design around infrastructure, soil stability
- **Environmental Consultant**: Flood/bushfire risk assessment, contamination
- **Licensed Surveyor**: Boundary verification, easement documentation
- **Property Lawyer**: High-risk legal implications, easement rights
- **Geotechnical Engineer**: Soil conditions, slope stability, foundation requirements

## Output Requirements

Provide structured analysis including:

### Infrastructure Analysis
- Complete inventory of identified infrastructure elements
- Specifications and ownership details where determinable
- Building envelope impacts and construction considerations
- Access and maintenance requirements

### Boundary and Legal Analysis
- Property boundaries and dimensions
- Easements, encroachments, and right-of-way issues
- Compliance with zoning and setback requirements
- Title boundary alignment verification needs

### Environmental Risk Assessment
- Identified environmental hazards and risk levels
- Development restrictions and approval requirements
- Insurance implications and coverage considerations
- Mitigation strategies and professional consultation needs

### Development Impact Summary
- Overall property development potential
- Key constraints and approval requirements
- Construction considerations and design impacts
- Estimated costs for professional consultations

### Priority Action Items
Rank all identified issues by:
1. **Immediate Action Required** (before contract exchange)
2. **Investigation Needed** (before settlement)
3. **Long-term Considerations** (for property ownership/development)

Focus on practical property implications for a {{ contract_context.user_type | default("buyer") }} making informed decisions about this {{ australian_state }} property transaction.