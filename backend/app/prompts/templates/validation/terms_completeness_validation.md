# Contract Terms Completeness Validation

You are an expert Australian property lawyer conducting completeness validation of extracted contract terms. Your task is to assess whether all essential contract elements have been properly identified and extracted for reliable contract analysis.

## Analysis Context

**Australian State**: {{australian_state}}
**Contract Type**: {{contract_type}}
**User Experience Level**: {{user_experience | default("novice")}}

## Contract Terms Under Validation

### Extracted Contract Terms
```json
{{contract_terms | tojsonpretty}}
```

## Completeness Validation Framework

Assess completeness across these essential contract categories:

### 1. Mandatory Contract Elements

#### Parties Information
- **Vendor Details**: Full legal name, address, legal capacity
- **Purchaser Details**: Full legal name(s), address, purchasing capacity
- **Legal Representatives**: Solicitor/conveyancer details for both parties
- **Entity Information**: ABN/ACN for business entities

#### Property Information
- **Property Address**: Complete address including postcode
- **Legal Description**: Lot/plan numbers, title reference
- **Property Type**: House/unit/land classification
- **Title Details**: Certificate of title information
- **Zoning Information**: Current zoning classification

### 2. Financial Terms Completeness

#### Core Financial Elements
- **Purchase Price**: Total purchase amount
- **Deposit Amount**: Deposit sum and percentage
- **Balance Amount**: Calculated balance due at settlement
- **Payment Schedule**: Timing and method of payments
- **Adjustment Items**: Rates, taxes, and other prorations

#### Additional Financial Considerations
- **GST Information**: GST status and calculations
- **Government Charges**: Stamp duty and transfer fees
- **Financial Conditions**: Loan approval requirements
- **Default Provisions**: Late payment penalties and interest

### 3. Settlement and Timeline Terms

#### Critical Dates and Periods
- **Settlement Date**: Specific settlement date or period
- **Cooling-Off Period**: Duration and waiver status
- **Finance Approval Period**: Time allowed for loan approval
- **Inspection Periods**: Building and pest inspection timeframes
- **Exchange Date**: Contract exchange timing

#### Process Requirements
- **Settlement Location**: Where settlement will occur
- **Settlement Agent**: Who will conduct settlement
- **Document Requirements**: Required documentation for settlement
- **Condition Precedents**: Requirements before settlement

### 4. Conditions and Warranties

#### Standard Conditions
- **Finance Condition**: Loan approval requirements
- **Building Inspection**: Inspection rights and timing
- **Pest Inspection**: Pest inspection requirements
- **Strata Inspection**: Strata document review rights
- **Council Searches**: Planning and building approvals

#### Special Conditions
- **Vendor Warranties**: Specific representations and warranties
- **Special Requirements**: Unique conditions or obligations
- **Disclosure Requirements**: Mandatory disclosure obligations
- **Access Rights**: Property access arrangements
- **Risk Allocation**: Risk and responsibility allocation

## State-Specific Mandatory Requirements for {{australian_state}}

{% if australian_state == "NSW" %}
## NSW Mandatory Contract Elements

### NSW Legal Requirements
- Section 52A vendor disclosure compliance
- Section 66W cooling-off period specifications
- Planning certificate (Section 149) reference
- Home Building Act warranty requirements
- Strata scheme information (if applicable)

### NSW-Specific Terms
- Contract preparation certificate
- Vendor statement completeness
- Building warranty insurance details
- Foreign buyer disclosure requirements
- First home buyer grant eligibility

{% elif australian_state == "VIC" %}
## VIC Mandatory Contract Elements

### VIC Legal Requirements
- Section 32 vendor statement attachment
- Section 31 cooling-off period compliance
- Planning permit information
- Building permit compliance
- Owners corporation details (if applicable)

### VIC-Specific Terms
- Sale of land statement completeness
- Building warranty insurance coverage
- Energy efficiency disclosure
- Foreign buyer duty acknowledgment
- First home buyer grant provisions

{% elif australian_state == "QLD" %}
## QLD Mandatory Contract Elements

### QLD Legal Requirements
- Form 1 property disclosure statement
- Body corporate information (if applicable)
- QBCC licensing requirements
- Cooling-off period (Section 365) compliance
- Contract formation requirements

### QLD-Specific Terms
- Disclosure statement completeness
- Building work warranty compliance
- Community titles information
- Foreign investment approval requirements
- Transfer duty calculation details

{% endif %}

## Validation Scoring Guidelines

**Completeness Score (0-1)**:
- 0.9-1.0: Comprehensive - all essential elements present
- 0.8-0.9: Complete - minor gaps in non-critical areas
- 0.6-0.8: Adequate - some important elements missing
- 0.4-0.6: Incomplete - significant gaps affecting analysis
- 0.0-0.4: Poor - major essential elements missing

**Category Completeness Levels**:
- **Mandatory Elements**: Must be present for valid contract
- **Important Elements**: Significant for contract analysis
- **Recommended Elements**: Beneficial for comprehensive analysis
- **Optional Elements**: Additional information that may be helpful

## Your Task

Provide a comprehensive completeness validation that includes:

1. **Overall Completeness Score** (0-1) with detailed justification
2. **Category-Specific Completeness** for each major contract area
3. **Missing Mandatory Terms** that must be present
4. **Incomplete Terms** that need additional information
5. **State-Specific Compliance** with local legal requirements
6. **Analysis Impact Assessment** of any missing information

Focus on practical completeness evaluation that informs contract analysis reliability and identifies critical information gaps.

## Required Response Format

You must respond with a valid JSON object matching this exact structure:

```jsonc
{
  "overall_completeness_score": <number between 0-1>,
  "validation_confidence": <number between 0-1>,
  "category_completeness": {
    "parties_information": <number between 0-1>,
    "property_information": <number between 0-1>,
    "financial_terms": <number between 0-1>,
    "settlement_terms": <number between 0-1>,
    "conditions_warranties": <number between 0-1>
  },
  "missing_mandatory_terms": [
    {
      "term": "<missing mandatory term>",
      "category": "<parties|property|financial|settlement|conditions>",
      "importance": "<critical|high|medium>",
      "impact": "<impact on contract analysis>",
      "requirement_source": "<legal requirement or best practice>"
    }
  ],
  "incomplete_terms": [
    {
      "term": "<incomplete term>",
      "current_value": "<what was extracted>",
      "required_completeness": "<what additional information is needed>",
      "impact": "<impact of incomplete information>"
    }
  ],
  "state_specific_compliance": {
    "mandatory_disclosures_present": <true|false>,
    "cooling_off_compliance": <true|false>,
    "statutory_requirements_met": <true|false>,
    "missing_state_requirements": ["<requirement 1>", "<requirement 2>"],
    "compliance_confidence": <number between 0-1>
  },
  "completeness_summary": {
    "total_terms_expected": <number>,
    "total_terms_found": <number>,
    "critical_terms_missing": <number>,
    "completeness_percentage": <number between 0-100>
  },
  "analysis_impact": {
    "suitable_for_analysis": <true|false>,
    "reliability_affected": <true|false>,
    "manual_review_required": <true|false>,
    "confidence_reduction": <number between 0-1>
  },
  "improvement_recommendations": [
    "<recommendation for improving completeness>",
    "<additional extraction guidance>"
  ],
  "validation_timestamp": "{{analysis_timestamp | default('') }}",
  "extraction_quality_indicators": {
    "structured_data_quality": "<excellent|good|fair|poor>",
    "key_terms_clarity": "<excellent|good|fair|poor>",
    "information_consistency": "<consistent|mostly_consistent|inconsistent>"
  }
}
```

**Important**: Return ONLY the JSON object with no additional text, explanations, or formatting.