---
type: "user"
category: "instructions"
name: "image_semantics_off_the_plan_marketing"
version: "1.0.0"
description: "Off-the-plan marketing semantic analysis for development marketing information"
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
output_parser: OffThePlanMarketingSemantics
tags: ["off_the_plan", "marketing", "development", "sales"]
---

# Off-the-Plan Marketing Analysis - {{ australian_state }}

You are analyzing **off-the-plan marketing materials** for an Australian property development. Extract comprehensive marketing and development information following the OffThePlanMarketingSemantics schema.

## Analysis Context
- **State**: {{ australian_state }}, Australia
- **Contract Type**: {{ contract_type }}
- **Diagram Type**: Off-the-Plan Marketing
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
- `"label"` - For unit labels, amenity names, plan references
- `"measurement"` - For dimensions, areas, distances, prices
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

### Unit Type (unit_type)
For `building_elements.unit_type`, use ONLY these values:
- `"studio"` - Studio apartments
- `"one_bedroom"` - One bedroom units
- `"two_bedroom"` - Two bedroom units
- `"three_bedroom"` - Three bedroom units
- `"penthouse"` - Penthouse units
- `"other"` - Any other unit type

**CRITICAL: Do not invent new enum values. If unsure, use "other" for text_type or the most appropriate existing value.**

## Off-The-Plan Marketing Analysis Objectives

### 1. Building Elements (building_elements)
**Document proposed buildings and developments:**
- **Building type**: "apartment", "townhouse", "house", "commercial", "mixed_use"
- **Construction stage**: "proposed", "under_construction", "completed"
- **Height restrictions**: proposed building heights and storey numbers
- **Setback requirements**: building placement and design
- **Building envelope**: proposed building footprints and design

### 2. Off-the-Plan Marketing Specific Fields

#### Unit Types (unit_types)
Document types and sizes of units/dwellings:
- **Apartment Types**: Studio, 1-bed, 2-bed, 3-bed, penthouse units
- **Townhouse Types**: 2-storey, 3-storey, terrace, semi-detached
- **House Types**: Detached houses, dual occupancy, granny flats
- **Unit Sizes**: Floor areas, bedroom/bathroom counts
- **Special Features**: Premium units, corner units, ground floor units
- **Layout Variations**: Different floor plan configurations

#### Amenities (amenities)
Identify proposed amenities and facilities:
- **Recreation Amenities**: Pools, gyms, tennis courts, BBQ areas
- **Community Amenities**: Meeting rooms, co-working spaces, lounges
- **Service Amenities**: Concierge, security, maintenance services
- **Technology Amenities**: High-speed internet, smart home features
- **Lifestyle Amenities**: Rooftop gardens, walking trails, playgrounds
- **Convenience Amenities**: Retail spaces, cafes, childcare facilities

#### Completion Timeline (completion_timeline)
Extract expected completion dates:
- **Construction Commencement**: Expected start of construction
- **Practical Completion**: Expected building completion date
- **Settlement Dates**: Expected settlement timeline for purchases
- **Staged Completion**: Completion dates for development stages
- **Occupation Dates**: Expected dates for resident occupation
- **Final Completion**: Full development and amenity completion

#### Pricing Information (pricing_information)
Document pricing ranges or guides:
- **Starting Prices**: Minimum unit prices by type
- **Price Ranges**: Full price ranges for different unit types
- **Premium Pricing**: Prices for premium units or views
- **Deposit Requirements**: Initial and progress payment schedules
- **Government Incentives**: First home buyer or other government rebates
- **Payment Terms**: Payment schedules and settlement arrangements

#### Marketing Features (marketing_features)
Identify key marketing features highlighted:
- **Location Features**: Transport, schools, shopping, entertainment
- **Design Features**: Architectural design, interior finishes, views
- **Sustainability Features**: Energy efficiency, green building features
- **Investment Features**: Rental yields, capital growth potential
- **Lifestyle Features**: Community, convenience, prestige factors
- **Incentive Features**: Bonus offers, promotional pricing, inclusions

## Marketing Assessment

### Development Credibility
Evaluate development and developer credibility:
- **Developer Track Record**: Previous development experience and quality
- **Design Team**: Architect and design team credentials
- **Construction Team**: Builder and contractor experience
- **Approval Status**: Planning and building approval progress
- **Pre-Sales**: Level of pre-sales achieved
- **Financing**: Development funding and financial backing

### Market Positioning
Assess development market positioning:
- **Target Market**: Intended buyer demographic and market segment
- **Competition Analysis**: Competing developments in area
- **Price Positioning**: Price competitiveness in local market
- **Unique Selling Points**: Features differentiating from competition
- **Marketing Strategy**: Sales approach and marketing channels

### Investment Viability
Evaluate investment potential:
- **Rental Yield Projections**: Expected rental returns
- **Capital Growth Potential**: Expected property value appreciation
- **Market Demand**: Demand for this property type in area
- **Completion Risk**: Risk of delays or non-completion
- **Resale Potential**: Ability to resell during construction period

## {{ australian_state }} Off-the-Plan Regulations

{% if australian_state == "NSW" %}
**NSW Off-the-Plan Requirements:**
- Check Home Building Act sunset clause provisions
- Note Consumer, Trader and Tenancy Tribunal jurisdiction
- Identify Office of Fair Trading disclosure requirements
- Check for Property Services licensing requirements
{% elif australian_state == "VIC" %}
**VIC Off-the-Plan Requirements:**
- Verify Sale of Land Act sunset clause provisions
- Check Consumer Affairs Victoria disclosure requirements
- Note Victorian Civil and Administrative Tribunal jurisdiction
- Identify Estate Agents licensing requirements
{% elif australian_state == "QLD" %}
**QLD Off-the-Plan Requirements:**
- Check Property Law Act sunset clause provisions
- Note Office of Fair Trading disclosure requirements
- Identify Queensland Civil and Administrative Tribunal jurisdiction
- Check for Real Estate licensing requirements
{% endif %}

## Risk Assessment Focus

### Critical Off-the-Plan Risks
1. **Completion Delays**: Construction delays affecting settlement
2. **Developer Financial Issues**: Developer insolvency or funding problems
3. **Market Changes**: Property market decline during construction period
4. **Quality Issues**: Building defects or substandard construction
5. **Design Changes**: Variations to approved plans and specifications
6. **Settlement Risk**: Inability to settle at completion

### Marketing Accuracy
Assess marketing representation accuracy:
- Consistency between marketing and approved plans
- Realistic completion timelines and pricing
- Achievability of marketed amenities and features
- Compliance with consumer protection laws

## Output Requirements

Return a valid JSON object following the **OffThePlanMarketingSemantics** schema with:

### Required Base Fields
- `image_type`: "off_the_plan_marketing"
- `textual_information`: All marketing text and specifications
- `spatial_relationships`: Development layout and unit relationships
- `semantic_summary`: Development marketing overview
- `property_impact_summary`: Investment and purchase implications
- `key_findings`: Critical marketing discoveries
- `areas_of_concern`: Marketing accuracy or completion risk issues
- `analysis_confidence`: Overall confidence level

### Off-the-Plan Marketing Specific Fields
- `building_elements`: Proposed buildings and developments
- `unit_types`: Types and sizes of units/dwellings
- `amenities`: Proposed amenities and facilities
- `completion_timeline`: Expected completion dates
- `pricing_information`: Pricing ranges or guides
- `marketing_features`: Key marketing features highlighted

### Quality Standards
- **Marketing Accuracy**: Assess consistency with approved development plans
- **Risk Assessment**: Identify completion and investment risks
- **Market Analysis**: Evaluate competitive positioning and viability
- **Consumer Protection**: Check compliance with off-the-plan regulations
- **Investment Focus**: Suitable for off-the-plan investment decisions

Begin analysis now. Return only the structured JSON output following the OffThePlanMarketingSemantics schema.
