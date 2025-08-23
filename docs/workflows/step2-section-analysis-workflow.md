## Step 2 Section-by-Section Analysis Workflow (LangGraph)

This diagram reflects the control flow defined in `backend/app/agents/subflows/step2_section_analysis_workflow.py`.

```mermaid
graph TD
  START([Start])
  END([End])

  START --> INIT[initialize_workflow]

  INIT --> P1A[analyze_parties_property]
  INIT --> P1B[analyze_financial_terms]
  INIT --> P1C[analyze_conditions]
  INIT --> P1D[analyze_warranties]
  INIT --> P1E[analyze_default_termination]

  P1A --> C1[check_phase1_completion]
  P1B --> C1
  P1C --> C1
  P1D --> C1
  P1E --> C1

  C1 --> S2A[analyze_settlement_logistics]
  C1 --> S2B[analyze_title_encumbrances]

  S2A --> C2[check_phase2_completion]
  S2B --> C2

  C2 --> S3A[calculate_adjustments_outgoings]
  C2 --> S3B[check_disclosure_compliance]
  C2 --> S3C[identify_special_risks]

  S3A --> V[validate_cross_sections]
  S3B --> V
  S3C --> V

  V --> F[finalize_results]
  F --> END
```

### Node Key
- **initialize_workflow**: Prepare initial state and inputs
- **analyze_parties_property**: Analyze parties and property details
- **analyze_financial_terms**: Analyze payment, price, deposits and timing
- **analyze_conditions**: Analyze conditions precedent/subsequent and contingencies
- **analyze_warranties**: Analyze representations and warranties
- **analyze_default_termination**: Analyze default/termination clauses and remedies
- **check_phase1_completion**: Verify all foundation analyses completed
- **analyze_settlement_logistics**: Analyze settlement/possession, deliverables, timelines
- **analyze_title_encumbrances**: Analyze title, encumbrances, easements, registrations
- **check_phase2_completion**: Verify dependent analyses completed
- **calculate_adjustments_outgoings**: Compute adjustments, rates, outgoings
- **check_disclosure_compliance**: Validate disclosure obligations and compliance
- **identify_special_risks**: Identify special conditions and risk exposures
- **validate_cross_sections**: Cross-check findings across sections for consistency
- **finalize_results**: Aggregate outputs and produce final analysis artifacts


