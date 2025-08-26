## Document Processing Workflow (LangGraph)

This diagram reflects the control flow defined in `backend/app/agents/subflows/document_processing_workflow.py`.

```mermaid
graph TD
  START([Start])
  END([End])

  START --> FDR[fetch_document_record]
  FDR --> APC[already_processed_check]

  %% Already processed short-circuit
  APC -- already_processed --> BS[build_summary]
  APC -- needs_processing --> MPS[mark_processing_started]
  APC -- error --> EH[error_handling]

  %% Processing pipeline
  MPS --> ET[extract_text]
  ET -- success --> SD[save_diagrams]
  ET -- error --> EH

  SD --> UM[update_metrics]
  UM --> LFC[layout_format_cleanup]
  LFC --> MBC[mark_basic_complete]
  MBC --> BS

  %% Terminal edges
  BS --> END
  EH --> END
```

### Node Key
- **fetch_document_record**: Fetch metadata and validate access.
- **already_processed_check**: Short-circuit if results exist; else proceed or route to error.
- **mark_processing_started**: Mark job started and set initial status/progress.
- **extract_text**: Perform LLM/native OCR and text extraction.
- **save_diagrams**: Persist diagram detection results (aggregated per document).
- **update_metrics**: Update document metrics after extraction and diagram save.
- **layout_format_cleanup**: Clean and normalize layout/formatting without LLM.
- **mark_basic_complete**: Mark processing as complete for the basic pipeline.
- **build_summary**: Construct `ProcessedDocumentSummary`.
- **error_handling**: Handle errors and produce `ProcessingErrorResponse`.

### Progress Ranges (from code)
- fetch_document_record: 0–5
- already_processed_check: 5–7
- mark_processing_started: 7–8
- extract_text: 7–34
- save_diagrams: 34–40
- update_metrics: 40–41
- layout_format_cleanup: 41–48
- mark_basic_complete: 48–49
- build_summary: 49–50

## Step 3 Synthesis Workflow (LangGraph)

This diagram reflects the control flow defined in `backend/app/agents/subflows/step3_synthesis_workflow.py`.

```mermaid
graph TD
  START([Start])
  END([End])

  START --> AR[aggregate_risks<br/>0-5%]
  AR --> AP[generate_action_plan<br/>5-10%]
  AR --> CS[compute_compliance_score<br/>10-15%]
  
  AP --> BR[synthesize_buyer_report<br/>15-20%]
  CS --> BR
  
  BR --> END

  %% Styling
  classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:2px
  classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
  classDef parallel fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
  
  class START,END startEnd
  class AR,AP,CS,BR process
```

### Node Key
- **aggregate_risks** (0-5%): Aggregates risks from all contract sections using the RiskAggregatorNode
- **generate_action_plan** (5-10%): Generates actionable recommendations using the ActionPlanNode  
- **compute_compliance_score** (10-15%): Computes overall compliance score using the ComplianceScoreNode
- **synthesize_buyer_report** (15-20%): Creates final buyer report using the BuyerReportNode

### Workflow Characteristics
- **Parallel Execution**: Both `generate_action_plan` and `compute_compliance_score` run in parallel after `aggregate_risks`
- **Convergence**: Both parallel paths converge at `synthesize_buyer_report` before completion
- **Progress Tracking**: Each node has defined progress ranges for monitoring
- **State Management**: Uses `Step3SynthesisState` to maintain workflow state and results

The workflow takes inputs from Step 2 (section analysis results and cross-validation) and produces a comprehensive synthesis including risk summary, action plan, compliance score, and final buyer report.


