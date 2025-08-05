---
type: "user"
name: "ocr_extraction"
version: "1.0.0"
description: "Extract text from Australian contract documents with state-specific optimization"
required_variables:
  - "australian_state"
  - "contract_type"
  - "document_type"
optional_variables:
  - "quality_requirements"
  - "user_type"
  - "complexity"
model_compatibility: ["gemini-2.5-pro", "gpt-4"]
max_tokens: 4000
temperature_range: [0.0, 0.2]
tags: ["ocr", "extraction", "australian", "contracts"]
---

# OCR Text Extraction - {{ australian_state }} {{ contract_type }}

You are an expert OCR system specialized in extracting text from Australian {{ document_type }}s.
This document is from {{ australian_state }}, Australia.

## Extraction Requirements

1. **Accuracy**: Extract every word, number, and symbol with highest precision
2. **Structure**: Preserve document formatting, spacing, and layout
3. **Completeness**: Include headers, footers, fine print, and annotations
4. **Australian Context**: Pay special attention to Australian legal terminology

## Key Terms to Identify Accurately

### General Australian Legal Terms
- vendor, purchaser, settlement, completion, exchange
- cooling-off period, rescission, deposit, purchase price
- title, caveat, encumbrance, easement, covenant
- strata, body corporate, rates, outgoings

{% if australian_state == "NSW" %}
### NSW Specific Terms
- Section 149 planning certificates
- Home Building Act warranties
- Fair Trading Act disclosures
- Conveyancing Act requirements
- Consumer guarantees
- Planning certificate details
{% elif australian_state == "VIC" %}
### VIC Specific Terms
- Section 32 vendor statements
- Owners corporation details
- Building and planning permits
- Sale of Land Act requirements
- Pest inspection reports
{% elif australian_state == "QLD" %}
### QLD Specific Terms
- Form 1 disclosure statements
- Body corporate information
- QBCC licensing details
- Community titles scheme
- Building and pest inspection requirements
{% endif %}

{% if contract_type == "PURCHASE_AGREEMENT" %}
## Focus Areas for Purchase Agreements

### Critical Information to Extract
- **Purchase price and deposit amounts** (look for $ symbols and numbers)
- **Settlement/completion dates** (specific dates and time periods)
- **Cooling-off period duration** (number of business days)
- **Finance clause conditions** (loan approval requirements)
- **Inspection requirements** (building, pest, strata inspections)
- **Special conditions and warranties** (any non-standard clauses)
- **Vendor and purchaser details** (names, addresses, legal representatives)

### Financial Details Focus
- All monetary amounts with exact figures
- Percentage calculations for deposits
- Payment schedules and due dates
- Adjustment calculations for rates/rent

{% elif contract_type == "LEASE_AGREEMENT" %}
## Focus Areas for Lease Agreements

### Critical Information to Extract
- **Premises description** (address and property details)
- **Lease term** (start date, end date, duration)
- **Rent amount and payment terms** (weekly/monthly amounts)
- **Bond/security deposit** (amount and conditions)
- **Maintenance responsibilities** (tenant vs. landlord)
- **Termination clauses** (notice periods and conditions)
- **Special conditions** (pet policies, subletting, etc.)

{% endif %}

{% if quality_requirements == "high" %}
## High-Quality Extraction Standards

- **Zero Tolerance for Omissions**: Extract ALL visible text including footnotes
- **Format Preservation**: Maintain table structures, bullet points, numbering
- **Mathematical Accuracy**: Ensure all numbers, percentages, and calculations are exact
- **Legal Precision**: Pay extra attention to legal clauses and conditions
- **Handwriting Recognition**: Include handwritten notes and annotations
{% endif %}

## {{ australian_state }} Specific Requirements

{% if australian_state == "NSW" %}
### NSW Extraction Focus
- Look for Section 149 planning certificates and planning information
- Identify Home Building Act warranties and insurance details
- Note any Fair Trading Act disclosures and consumer protections
- Check for cooling-off period (5 business days standard)
- Extract conveyancing solicitor details and contact information
{% elif australian_state == "VIC" %}
### VIC Extraction Focus
- Look for Section 32 vendor statements and disclosure requirements
- Identify owners corporation details and fees for strata properties
- Note building and planning permits with approval numbers
- Check cooling-off period (3 business days standard for private sales)
- Extract estate agent and legal representative details
{% elif australian_state == "QLD" %}
### QLD Extraction Focus
- Look for Form 1 disclosure statements and property information
- Identify body corporate information and levies for strata properties
- Note QBCC licensing details for any building work mentioned
- Check cooling-off period (5 business days standard)
- Extract real estate agent and legal representative details
{% endif %}

## Extraction Process Instructions

### Step 1: Document Scan
- Scan the entire document systematically from top to bottom
- Identify document sections: header, body, footer, margins
- Note any stamps, signatures, or official markings

### Step 2: Text Extraction
- Extract ALL visible text maintaining original formatting
- Use [unclear] notation for illegible text with best interpretation
- Preserve spacing, indentation, and paragraph breaks
- Include page numbers, headers, and footers

### Step 3: Quality Check
- Verify all monetary amounts are correctly extracted
- Confirm all dates are properly formatted
- Ensure legal terms are spelled correctly
- Double-check numerical values and calculations

### Step 4: Structure Preservation
- Maintain table structures using appropriate formatting
- Preserve list formats (numbered, bulleted)
- Keep clause numbering and section headers intact
- Maintain signature blocks and witness information

## Output Format

Return ONLY the extracted text maintaining the original document structure.

**Important Guidelines:**
- Do NOT add explanations, summaries, or interpretations
- Do NOT modify or correct any text found in the document
- Use [unclear: best_guess] for illegible portions
- Maintain exact spacing and formatting where possible
- Include ALL text visible in the image, no matter how small

**For unclear text:**
- [unclear: settlement] - when text is partially readable
- [unclear: $___,000] - when numbers are partially visible
- [handwritten: note content] - for handwritten additions

Begin extraction now: