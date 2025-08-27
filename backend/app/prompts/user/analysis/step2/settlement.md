---
type: "user"
category: "instructions"
name: "settlement_analysis"
version: "2.0.0"
description: "Step 2.7 - Settlement Logistics Analysis"
fragment_orchestration: "step2_settlement"
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_timestamp"
optional_variables:
  - "extracted_entity"
  - "financial_terms_result"
  - "conditions_result"
  - "legal_requirements_matrix"
  - "contract_type"
  - "retrieval_index_id"
  - "seed_snippets"
  - "image_semantics_result"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 8000
temperature_range: [0.1, 0.3]
output_parser: SettlementAnalysisResult
tags: ["step2", "settlement", "logistics", "dependent"]
---

# Settlement Logistics Analysis (Step 2.7)

Perform comprehensive analysis of settlement procedures, document requirements, timing coordination, and completion obligations in this Australian real estate contract, focusing on practical logistics and risk assessment.

## Contract Context
- **State**: {{ australian_state or 'unknown' }}
- **Contract Type**: {{ contract_type or 'unknown' }}
- **Analysis Date**: {{analysis_timestamp}}

## Analysis Requirements

### 1. Settlement Date and Timing Analysis

**Settlement date determination:**
- Specified settlement date or calculation method
- Business day requirements and holiday considerations
- Extension provisions and circumstances
- Time of essence declarations for settlement

**Timing coordination assessment:**
- Adequacy of time between contract and settlement
- Coordination with condition satisfaction deadlines
- Finance approval and settlement timing
- Inspection completion and settlement coordination

**Timeline risk evaluation:**
- Realistic assessment of settlement timeline
- Buffer periods and contingency time
- Critical path dependencies
- Potential timing conflicts

### 2. Settlement Location and Method

**Location analysis:**
- Specified settlement location (solicitor offices, agreed venue)
- Electronic settlement provisions (PEXA, etc.)
- Backup location arrangements
- Accessibility and practical considerations

**Method assessment:**
- Settlement procedure type (traditional, electronic, hybrid)
- {{australian_state}} electronic settlement requirements
- Fallback procedures if electronic settlement fails
- Coordination requirements between parties

**Logistics evaluation:**
- Practical feasibility of arrangements
- Travel and attendance requirements
- Technology requirements and backup plans
- Cost implications of settlement method

### 3. Document Preparation Requirements

**Identify all required documents:**
- Title documents and certificates
- Mortgage discharge documents
- Planning and building permits
- Compliance certificates and approvals
- Rates and utility clearances
- Insurance documentation
- Strata documents (if applicable)

**For each document, assess:**
- Preparation time requirements
- Party responsible for provision
- Risk of delays or unavailability
- Alternative arrangements if unavailable
- Original vs copy requirements

**Document coordination analysis:**
- Sequence of document preparation
- Dependencies between documents
- Coordination requirements with third parties
- Electronic lodgment requirements

### 4. Funds Coordination Analysis

**Funding requirements:**
- Total settlement funds calculation
- Breakdown by funding source
- Timing for funds availability
- Banking coordination requirements

**Finance settlement coordination:**
- Bank requirements and procedures
- Settlement statement preparation
- Funds transfer arrangements
- Contingency funding plans

**Risk assessment:**
- Funding shortfall risks
- Bank coordination risks
- Foreign exchange considerations (if applicable)
- Backup funding arrangements

### 5. Possession and Property Transition

**Possession arrangements:**
- Possession date and time specifications
- Key handover procedures
- Property condition requirements at possession
- Utility connection and transfer arrangements

**Transition logistics:**
- Property inspection at settlement
- Utility readings and transfers
- Insurance transition requirements
- Security system transfers

**Risk evaluation:**
- Possession delay risks
- Property damage during transition
- Utility connection issues
- Security and access concerns

### 6. Settlement Statement and Adjustments

**Settlement statement requirements:**
- Preparation responsibilities
- Approval and acceptance procedures
- Dispute resolution for adjustments
- Final amount calculation verification

**Adjustment calculations:**
- Rates and tax apportionments
- Utility account adjustments
- Rent apportionments (if applicable)
- Other outgoings and fees

**Verification procedures:**
- Statement accuracy verification
- Adjustment calculation methods
- Supporting documentation requirements
- Dispute resolution mechanisms

## Seed Snippets (Primary Context)

{% if seed_snippets %}
Use these high-signal settlement snippets as primary context:
{{seed_snippets | tojsonpretty}}
{% else %}
No seed snippets provided.
{% endif %}

### 7. Post-Settlement Obligations

**Immediate post-settlement requirements:**
- Document lodgment obligations
- Notification requirements
- Insurance arrangements
- Utility account transfers

**Ongoing obligations:**
- Warranty periods and responsibilities
- Defect liability periods
- Maintenance responsibilities
- Future compliance requirements

## Dependency Analysis

{% if financial_terms_result %}
### Financial Terms Integration
Settlement logistics must coordinate with financial requirements:
{{financial_terms_result | tojsonpretty}}
{% endif %}

{% if conditions_result %}
### Conditions Integration
Settlement timing must account for condition satisfaction:
{{conditions_result | tojsonpretty}}
{% endif %}

{% if image_semantics_result %}
### Diagram Semantics Integration
Use relevant diagram semantics that affect practical settlement logistics (services, access, boundary constraints):
{{ image_semantics_result | tojsonpretty }}
{% endif %}


## Additional Context

{% if legal_requirements_matrix %}
### Legal Requirements
{{australian_state}} {{contract_type}} settlement requirements:
{{legal_requirements_matrix | tojsonpretty}}
{% endif %}

## Analysis Instructions (Seeds + Retrieval + Phase 1 Outputs)

1. Use Phase 1 outputs (dependencies above) as baseline. Verify and enrich using `seed_snippets` as primary evidence.
2. If baseline + seeds are insufficient, retrieve targeted settlement clauses (timing, location/method, required documents, funds, possession, statements/adjustments) from `retrieval_index_id` with concise queries. Record what was retrieved.
3. Integrate dependencies: incorporate `financial_terms_result` and `conditions_result` when assessing logistics and timing.
4. Emphasize practical feasibility: identify real-world coordination requirements and bottlenecks.
5. Apply state-specific procedures and electronic settlement requirements; define fallback procedures if electronic settlement fails.
6. Map the critical path and dependencies; include contingency buffers and escalation plans.
7. Cite specific clauses/schedules as evidence for every material finding.
8. Ensure the final timeline aligns with all condition deadlines and funding availability.

## Expected Output

Provide comprehensive settlement logistics analysis following the SettlementAnalysisResult schema:

- Complete settlement procedure analysis with timing and location assessment
- Detailed document preparation requirements with risk and timeline evaluation
- Comprehensive funds coordination analysis with risk assessment
- Property possession arrangement analysis with transition logistics
- Settlement statement and adjustment procedures review
- Critical path analysis with dependency mapping
- Overall risk classification with practical recommendations

**Critical Success Criteria (PRD 4.1.2.7):**
- 100% identification of settlement requirements and dependencies
- Accurate timeline and coordination analysis
- Complete document preparation and availability assessment
- Clear evaluation of settlement logistics feasibility