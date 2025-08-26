## Step 2 Section Analysis Workflow (LangGraph)

This diagram reflects the control flow defined in `backend/app/agents/subflows/step2_section_analysis_workflow.py`.

```mermaid
graph TD
  START([Start])
  END([End])

  %% Initialization
  START --> I[initialize_workflow]
  I --> P[prepare_context]

  %% Phase 1: Foundation Analysis (parallel-capable)
  P --> F1A[analyze_parties_property]
  P --> F1B[analyze_financial_terms]
  P --> F1C[analyze_conditions]
  P --> F1D[analyze_warranties]
  P --> F1E[analyze_default_termination]
  P --> F1F[analyze_diagram]

  %% Phase 2: Dependent Analysis (DAG sequencing)
  F1B --> S2A[analyze_settlement_logistics]
  F1C --> S2A

  F1F --> S2B[analyze_title_encumbrances]
  F1A --> S2B

  %% Phase 3: Synthesis Analysis (depends on prior nodes)
  S2A --> S3A[calculate_adjustments_outgoings]
  F1B --> S3A

  S2A --> S3B[check_disclosure_compliance]
  S2B --> S3B

  S2A --> S3C[identify_special_risks]
  S2B --> S3C

  %% Cross-section validation and finalization
  S3A --> X[validate_cross_sections]
  S3B --> X
  S3C --> X

  X --> F[finalize_results]
  F --> END
```

### Phases
- **Foundation Analysis (parallel)**: Parties/Property, Financial Terms, Conditions, Warranties, Default & Termination, Diagram semantics
- **Dependent Analysis (sequenced)**: Settlement Logistics depends on Financial Terms and Conditions; Title & Encumbrances depends on Diagram semantics and Parties/Property
- **Synthesis Analysis (sequenced)**: Adjustments & Outgoings depends on Settlement Logistics and Financial Terms; Disclosure Compliance and Special Risks depend on Settlement Logistics and Title & Encumbrances → Cross-section Validation → Finalization

### Node Key
- **initialize_workflow**: Validate inputs, set `start_time`, emit initial progress.
- **prepare_context**: Prepare retrieval/context, hoist inputs and derive legal requirements when needed.
- **analyze_parties_property**: Analyze parties and property description.
- **analyze_financial_terms**: Analyze consideration, deposits, timing.
- **analyze_conditions**: Analyze conditions precedent/subsequent.
- **analyze_warranties**: Analyze warranties and representations.
- **analyze_default_termination**: Analyze defaults and termination.
- **analyze_diagram**: Analyze diagram semantics uploaded or derived.
- **analyze_settlement_logistics**: Settlement timing, deliverables, logistics.
- **analyze_title_encumbrances**: Title, encumbrances, related diagrams/artifacts.
- **calculate_adjustments_outgoings**: Compute adjustments and outgoings.
- **check_disclosure_compliance**: Validate disclosure obligations.
- **identify_special_risks**: Surface special conditions and risk flags.
- **validate_cross_sections**: Cross-check for inconsistencies.
- **finalize_results**: Aggregate outputs and produce final artifacts.


