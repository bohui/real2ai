# LangGraph Document Processing Workflow

## Overview

This document visualizes the dedicated LangGraph subflow for document processing. It aligns with the structure and conventions used in the contract analysis workflow documentation, focusing on the core processing nodes, conditional routing, and terminal outcomes.

---

## Workflow Diagram

```mermaid
flowchart TD
    START(["Start: Document Processing"]) --> FR["fetch_document_record"]

    FR --> APC["already_processed_check"]
    APC --> APC_DEC{"already_processed?"}

    APC_DEC -->|"already_processed"| BS["build_summary"]
    APC_DEC -->|"needs_processing"| MPS["mark_processing_started"]
    APC_DEC -->|"error"| EH["error_handling"]

    MPS --> ET["extract_text"]
    ET --> EX_DEC{"extraction_success?"}

    EX_DEC -->|"success"| SP["save_pages"]
    EX_DEC -->|"error"| EH

    SP --> AD["aggregate_diagrams"]
    AD --> SD["save_diagrams"]
    SD --> UM["update_metrics"]
    UM --> MBC["mark_basic_complete"]
    MBC --> BS

    BS --> END(["End: Summary Built"]) 
    EH --> END

    %% State checkpoints (dotted refs)
    FR -.-> S1["State: metadata loaded"]
    ET -.-> S2["State: text_extraction_result"]
    SD -.-> S3["State: diagrams saved"]
    MBC -.-> S4["State: processing status = COMPLETE"]
    BS -.-> S5["State: processed_summary"]
```

---

## Notes

- The flow is user-aware and maintains authentication context throughout all nodes.
- Conditional routing mirrors `check_already_processed` and `check_extraction_success` decisions.
- Terminal states converge at `build_summary` (success) or `error_handling` (failure).


