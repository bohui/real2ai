# Financial Terms Analysis

Analyze the financial terms and monetary obligations in this Australian real estate contract with focus on accuracy, market alignment, and risk assessment.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Purchase Price Verification

**Extract and verify purchase price details:**
- Purchase price as stated in contract (numeric and written forms)
- Cross-check numeric and written amounts for consistency
- Identify any price adjustments or variations

**Arithmetic accuracy assessment:**
- Verify all price-related calculations
- Check percentage calculations (deposit, commissions, etc.)
- Validate any arithmetic in schedules or appendices
- Flag any calculation errors or inconsistencies

**Market assessment (if data available):**
- Compare against recent comparable sales
- Assess if price appears above, at, or below market
- Note any unusual pricing structures or arrangements
- Consider property type and location factors

### 2. Deposit Analysis and Security

**Deposit amount and structure:**
- Deposit amount and percentage of purchase price
- Payment timeline and milestones
- Any deposit increase provisions
- Alternative deposit arrangements

**Security arrangements:**
- Trust account details and holder information
- Protection mechanisms for deposit security
- Stakeholder or agent holding arrangements
- Insurance or guarantee provisions

**Risk assessment:**
- Adequacy of deposit protection
- Risks to deposit security
- Unusual or high-risk arrangements
- Recovery mechanisms if transaction fails

### 3. Payment Schedule Review

**Identify all payment obligations:**
- Progress payments (for off-plan contracts)
- Additional fees, charges, and levies
- Interest provisions and calculations
- Late payment penalties and charges

**Cash flow analysis:**
- Total financial obligations beyond purchase price
- Payment timing and cash flow requirements
- Interest rate provisions and calculations
- Impact on buyer's financial position

**Special payment provisions:**
- Unusual payment structures or requirements
- Conditional payment arrangements
- Foreign exchange considerations (if applicable)
- Financing integration requirements

### 4. GST and Tax Implications

**GST status determination:**
- Whether GST applies to the transaction
- Vendor's GST registration status (if determinable)
- Property classification for GST purposes
- GST-inclusive vs GST-additional pricing

**GST calculation verification:**
- Accuracy of GST amounts (if applicable)
- Correct application of GST rates
- Input tax credit considerations
- New vs existing property GST treatment

**Other tax implications:**
- Stamp duty calculation considerations
- Land tax apportionment issues
- Foreign buyer duties (if applicable)
- Capital gains tax considerations for vendor

### 5. Risk Assessment

**Financial risk evaluation:**
- Price risk (significantly above market value)
- Deposit security risks
- Cash flow and payment risks
- Tax and compliance risks

**Impact assessment:**
- Potential financial losses or additional costs
- Timeline risks affecting financing
- Market volatility exposure
- Legal and compliance consequences

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction_result %}
### Entity Extraction Results
Previously extracted financial data:
{{entities_extraction_result | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} financial requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Systematic Review**: Examine all financial clauses, schedules, and appendices
2. **Arithmetic Verification**: Double-check all calculations and numerical consistency
3. **Market Context**: Apply {{australian_state}} market knowledge where possible
4. **Risk Focus**: Identify financial risks with quantified impact where feasible
5. **GST Compliance**: Apply current Australian GST law and ATO guidance
6. **Evidence Documentation**: Reference specific contract clauses and sections
7. **Confidence Assessment**: Provide confidence scores for all major determinations
8. **Practical Impact**: Focus on buyer's financial position and obligations

## Expected Output

Provide comprehensive financial analysis following the FinancialTermsAnalysisResult schema:

- Complete purchase price verification with market assessment
- Detailed deposit analysis with security evaluation
- Full payment schedule review with cash flow impact
- Comprehensive GST and tax implications analysis
- Risk indicators with quantified financial impacts where possible
- Overall risk classification and confidence scoring
- Evidence references and calculation verification

Ensure all arithmetic is verified and all financial risks are clearly identified with actionable recommendations for the buyer and their advisors.

**Critical Success Criteria (PRD 4.1.2.2):**
- 100% accuracy in financial calculations
- Complete identification of all payment obligations
- Risk scoring for deposit security arrangements
- Market-based price assessment where feasible