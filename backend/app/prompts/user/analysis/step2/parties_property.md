# Parties & Property Verification Analysis

Analyze the parties and property details in this Australian real estate contract with focus on verification, legal capacity, and property identification completeness.

## Contract Context
- **State**: {{australian_state}}
- **Contract Type**: {{contract_type}}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Party Verification
Examine all parties to the transaction and assess:

**For each party, identify:**
- Full legal name as stated in contract
- Role in transaction (vendor, purchaser, guarantor, etc.)
- Any entity structure (individual, company, trust, etc.)
- Contact information and addresses

**Assess legal capacity indicators:**
- Age references or capacity statements
- Authority to contract (for entities)
- Any guardianship or power of attorney arrangements
- Signing authority and witness requirements

**Flag verification concerns:**
- Inconsistent name spellings or formats
- Missing entity registration details (ABN/ACN for companies)
- Unclear authority arrangements
- Potential capacity issues

### 2. Property Identification Verification

**Analyze legal description completeness:**
- Street address accuracy and completeness
- Lot number and plan number (e.g., Lot 1 DP 123456)
- Title reference (Volume/Folio or identifier)
- Property type classification
- Strata information if applicable

**Check for verification issues:**
- Missing critical identifiers
- Inconsistent property descriptions
- Ambiguous location references
- Incomplete legal descriptions

**Cross-reference property details:**
- Ensure consistency across all contract sections
- Verify against any attached plans or documents
- Check for property boundary definitions
- Assess adequacy for title search purposes

### 3. Inclusions and Exclusions Analysis

**Inventory all items mentioned:**
- Fixtures explicitly included or excluded
- Fittings and chattels listed
- Any conditional inclusions
- Items with condition statements

**Assess completeness and clarity:**
- Comprehensive coverage of typical items
- Clear categorization of items
- Unambiguous descriptions
- Condition statements adequacy

**Identify potential issues:**
- Ambiguous item descriptions
- Unusual exclusions that may indicate problems
- Missing common items (appliances, fixtures)
- Potential disputes over item classifications

### 4. Risk Assessment

**Evaluate overall risk indicators:**
- Party verification concerns requiring follow-up
- Property description gaps affecting title searches
- Inclusion/exclusion disputes potential
- Legal capacity or authority issues

**Provide recommendations:**
- Additional verification steps needed
- Documentation requirements for entities
- Clarifications needed for property description
- Items requiring amendment or negotiation

## Contract Text for Analysis

```
{{contract_text}}
```

## Additional Context

{% if entities_extraction_result %}
### Entity Extraction Results
The following entities were previously extracted from this contract:
{{entities_extraction_result | tojsonpretty}}
{% endif %}

{% if legal_requirements_matrix %}
### Legal Requirements
Relevant legal requirements for {{australian_state}} {{contract_type}}:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions

1. **Read through the entire contract** focusing on party and property details
2. **Cross-reference information** between different contract sections
3. **Apply {{australian_state}} specific requirements** for party and property verification
4. **Identify gaps or concerns** that could affect transaction completion
5. **Assess risk levels** using RED/AMBER/GREEN classification
6. **Provide evidence references** for all findings with specific section/clause citations
7. **Include confidence scores** for all major determinations
8. **Focus on practical implications** for buyers and their legal advisors

## Expected Output

Provide a comprehensive analysis following the PartiesPropertyAnalysisResult schema with:

- Complete party verification assessment with legal capacity evaluation
- Detailed property identification verification with completeness assessment  
- Full inclusions/exclusions inventory with dispute risk analysis
- Risk indicators with specific impact and mitigation recommendations
- Overall risk classification and confidence scoring
- Evidence references and analysis notes

Ensure all findings are supported by specific contract text references and comply with {{australian_state}} legal requirements for {{contract_type}} transactions.