# Contract Analysis Report

## Executive Summary
**Document Type**: [Contract Type]
**Jurisdiction**: {{ australian_state }}, Australia  
**Analysis Date**: {{ now().strftime('%d/%m/%Y') }}
**Overall Risk Level**: [HIGH/MEDIUM/LOW]

### Key Findings
- **Critical Issues**: [Number] issues requiring immediate attention
- **Moderate Concerns**: [Number] items needing consideration  
- **Standard Terms**: [Number] terms consistent with market practice

### Immediate Actions Required
1. [Most urgent action item with deadline]
2. [Second priority action with timeline]
3. [Additional actions as needed]

---

## Document Overview

### Contract Details
- **Property Address**: [Full property address]
- **Vendor**: [Vendor name and details]
- **Purchaser**: [Purchaser name and details]
- **Contract Date**: [DD/MM/YYYY]
- **Standard Form**: [Contract type and version]

### Financial Summary
- **Purchase Price**: {{ purchase_price | currency if purchase_price else '[Amount]' }}
- **Deposit Amount**: {{ deposit_amount | currency if deposit_amount else '[Amount] ([%] of purchase price)' }}
- **Settlement Date**: {{ settlement_date | australian_date if settlement_date else '[DD/MM/YYYY]' }}
- **Total Estimated Costs**: [Amount including all fees and expenses]

---

## Detailed Analysis

### 1. Essential Terms Assessment

#### Property Description
- **Legal Description**: [Title details and lot/plan numbers]
- **Physical Description**: [Property type, size, and key features]
- **Zoning**: [Current zoning and permitted uses]
- **Title Type**: [Torrens, Strata, Community Title, etc.]

#### Financial Terms
- **Purchase Price**: {{ purchase_price | currency if purchase_price else '[Detailed price breakdown]' }}
- **Deposit Terms**: 
  - Amount and percentage
  - Payment date and method
  - Stakeholder arrangements
- **Balance Payment**:
  - Settlement amount and date
  - Adjustment arrangements
  - Late payment penalties

### 2. Conditions Analysis

#### Standard Conditions Status
| Condition | Status | Deadline | Risk Level |
|-----------|---------|----------|------------|
| Finance Approval | [Active/Satisfied/Waived] | [DD/MM/YYYY] | [HIGH/MED/LOW] |
| Building Inspection | [Active/Satisfied/Waived] | [DD/MM/YYYY] | [HIGH/MED/LOW] |
| Pest Inspection | [Active/Satisfied/Waived] | [DD/MM/YYYY] | [HIGH/MED/LOW] |
| Legal Searches | [Active/Satisfied/Waived] | [DD/MM/YYYY] | [HIGH/MED/LOW] |

#### Special Conditions Review
1. **[Special Condition 1]**
   - **Impact**: [Effect on buyer/seller]
   - **Risk Assessment**: [HIGH/MEDIUM/LOW]
   - **Recommendation**: [Action required]

2. **[Special Condition 2]**
   - **Impact**: [Effect on transaction]
   - **Risk Assessment**: [HIGH/MEDIUM/LOW]
   - **Recommendation**: [Action required]

### 3. Risk Assessment

#### 🔴 High-Risk Issues
{% for issue in high_risk_issues %}
**{{ loop.index }}. {{ issue.title }}**
- **Description**: {{ issue.description }}
- **Impact**: {{ issue.impact }}
- **Recommendation**: {{ issue.recommendation }}
- **Urgency**: {{ issue.urgency }}
{% endfor %}

#### 🟡 Medium-Risk Concerns
{% for concern in medium_risk_concerns %}
**{{ loop.index }}. {{ concern.title }}**
- **Description**: {{ concern.description }}
- **Mitigation**: {{ concern.mitigation }}
{% endfor %}

#### 🟢 Low-Risk Items
{% for item in low_risk_items %}
- {{ item.description }}
{% endfor %}

### 4. Compliance Assessment

#### State-Specific Requirements
{% if australian_state == "NSW" %}
**NSW Compliance Checklist:**
- ✅/❌ Section 149 Planning Certificate provided
- ✅/❌ Home Building Act warranties included
- ✅/❌ Fair Trading Act disclosures complete
- ✅/❌ Cooling-off period properly disclosed (5 business days)
{% elif australian_state == "VIC" %}
**Victoria Compliance Checklist:**
- ✅/❌ Section 32 Vendor Statement provided
- ✅/❌ Owners Corporation details disclosed
- ✅/❌ Sale of Land Act requirements met
- ✅/❌ Cooling-off period properly disclosed (3 business days)
{% elif australian_state == "QLD" %}
**Queensland Compliance Checklist:**
- ✅/❌ Form 1 Disclosure Statement provided
- ✅/❌ Body Corporate information disclosed
- ✅/❌ QBCC licensing verified
- ✅/❌ Cooling-off period properly disclosed (5 business days)
{% endif %}

#### Consumer Protection Status
- **Cooling-off Rights**: [Available/Waived/Expired]
- **Statutory Warranties**: [Included/Modified/Excluded]
- **Unfair Terms Assessment**: [Compliant/Concerns Identified]

---

## Recommendations

### Immediate Actions (Next 7 Days)
1. **[Action 1]** - Priority: HIGH
   - Deadline: [DD/MM/YYYY]
   - Responsible party: [Buyer/Seller/Solicitor]
   - Estimated cost: [Amount if applicable]

2. **[Action 2]** - Priority: HIGH
   - Deadline: [DD/MM/YYYY]
   - Details: [Specific requirements]

### Short-term Actions (Next 2-4 Weeks)
1. **[Action 1]** - Priority: MEDIUM
   - Timeline: [Date range]
   - Requirements: [What needs to be done]

### Professional Consultations Recommended
- **Solicitor/Conveyancer**: [Specific issues requiring legal advice]
- **Building Inspector**: [Structural or construction concerns]
- **Financial Advisor**: [Complex financing or tax implications]
- **[Other Specialists]**: [As required for specific issues]

---

## Cost Analysis

### Total Transaction Costs Estimate
| Cost Category | Estimated Amount | Notes |
|---------------|------------------|-------|
| Purchase Price | {{ purchase_price | currency if purchase_price else '[Amount]' }} | Contract price |
| Deposit | {{ deposit_amount | currency if deposit_amount else '[Amount]' }} | Due: [Date] |
| Stamp Duty | [Amount] | {{ australian_state }} rates |
| Legal Fees | [Amount] | Conveyancing costs |
| Inspections | [Amount] | Building, pest, other |
| Loan Costs | [Amount] | Application, valuation fees |
| Insurance | [Amount] | First year premium |
| **TOTAL ESTIMATED** | **[Total Amount]** | |

### Ongoing Costs (Annual)
- Council Rates: [Amount]
- Land Tax: [Amount if applicable]
- Insurance: [Amount]
- Strata/Body Corporate: [Amount if applicable]
- Maintenance Reserve: [Amount]

---

## Next Steps Checklist

### Before Settlement
- [ ] Complete building and pest inspections by [date]
- [ ] Obtain finance approval by [date]
- [ ] Review all disclosure documents
- [ ] Arrange property insurance
- [ ] Confirm settlement arrangements
- [ ] [Other specific requirements]

### At Settlement
- [ ] Final property inspection
- [ ] Confirm all conditions satisfied
- [ ] Review settlement statement
- [ ] Complete property transfer
- [ ] Collect keys and property documents

---

## Disclaimer

This analysis is based on the contract document provided and is for informational purposes only. It does not constitute legal advice. Professional legal advice should be obtained for any specific legal issues or concerns identified in this analysis.

**Analysis prepared by**: Real2AI Contract Analysis System
**Analysis date**: {{ now().strftime('%d/%m/%Y at %H:%M') }}
**Document version**: {{ contract_version if contract_version else 'Not specified' }}