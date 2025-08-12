## Document Processing Workflow (LangGraph)

This diagram reflects the control flow defined in `backend/app/agents/subflows/document_processing_workflow.py`.

```mermaid
graph TD
  START([Start])
  END([End])

  START --> A[fetch_document_record]
  A --> B{already_processed_check}

  B -->|already_processed| L[build_summary]
  B -->|needs_processing| C[mark_processing_started]
  B -->|error| Z[error_handling]

  C --> D{extract_text}
  D -->|success| E[paragraph_segmentation]
  D -->|error| Z

  E --> F[save_paragraphs]
  F --> G[save_pages]
  G --> H[aggregate_diagrams]
  H --> I[save_diagrams]
  I --> J[update_metrics]
  J --> K[mark_basic_complete]
  K --> L

  L --> END
  Z --> END
```

### Node Key
- **fetch_document_record**: Fetch metadata and validate access
- **already_processed_check**: Short-circuit if already processed
- **mark_processing_started**: Persist processing start state
- **extract_text**: Perform OCR/LLM/native text extraction
- **paragraph_segmentation**: Segment text into paragraphs and artifacts
- **save_paragraphs**: Persist paragraph references
- **save_pages**: Persist page-level analysis results
- **aggregate_diagrams**: Aggregate diagram detections
- **save_diagrams**: Persist diagram results
- **update_metrics**: Update aggregated metrics on the document
- **mark_basic_complete**: Mark processing status as complete
- **build_summary**: Construct final `ProcessedDocumentSummary`
- **error_handling**: Capture error details and finalize


