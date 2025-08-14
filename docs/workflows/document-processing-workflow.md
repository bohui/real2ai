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
  D -->|success| E{detect_diagrams_with_ocr}
  D -->|error| Z

  E -->|success| F[save_pages]
  E -->|error| Z

  F --> G[save_diagrams]
  G --> H[update_metrics]
  H --> I[mark_basic_complete]
  I --> L

  L --> END
  Z --> END
```

### Node Key
- **fetch_document_record**: Fetch metadata and validate access
- **already_processed_check**: Short-circuit if already processed
- **mark_processing_started**: Persist processing start state
- **extract_text**: Perform MuPDF text extraction and generate page JPGs
- **detect_diagrams_with_ocr**: Use Gemini OCR to detect diagrams and classify types
- **save_pages**: Persist page-level text and JPG artifacts
- **save_diagrams**: Persist diagram detection results from OCR
- **update_metrics**: Update aggregated metrics on the document
- **mark_basic_complete**: Mark processing status as complete
- **build_summary**: Construct final `ProcessedDocumentSummary`
- **error_handling**: Capture error details and finalize

### Workflow Changes
This workflow has been updated to use the new schema design without paragraphs:
- **Removed**: `paragraph_segmentation`, `save_paragraphs`, `aggregate_diagrams` nodes
- **Added**: `detect_diagrams_with_ocr` node that uses Gemini OCR with diagram detection prompt
- **Modified**: `extract_text` now focuses on MuPDF text extraction only
- **Modified**: `save_pages` stores text + JPG artifacts (no markdown/JSON in this workflow)


