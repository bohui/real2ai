# Unified Artifact Storage System

## Overview

The unified artifact storage system eliminates duplication between the main document processing workflow and external OCR workflow by consolidating artifact tables and providing a single interface for artifact retrieval.

## Problem Solved

**Before**: The main contract analysis workflow needed complex logic to determine where to get document processed results:
- `artifact_pages` (main workflow text) vs `artifact_pages_json` (external OCR metadata)
- `artifact_diagrams` (main workflow diagrams) vs `artifact_pages_jpg` (external OCR images)

**After**: Single unified interface with type discrimination:
- `artifact_pages` handles all page content types: `text`, `markdown`, `json_metadata`
- `artifact_diagrams` handles all visual types: `diagram`, `image_jpg`, `image_png`

## Architecture

### Unified Tables

#### `artifact_pages` (Extended)
```sql
CREATE TABLE artifact_pages (
    id uuid PRIMARY KEY,
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    page_number int NOT NULL,
    page_text_uri text NOT NULL,
    page_text_sha256 text NOT NULL,
    layout jsonb,
    metrics jsonb,
    content_type text DEFAULT 'text' CHECK (content_type IN ('text', 'markdown', 'json_metadata')),
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number)
);
```

#### `artifact_diagrams` (Extended)
```sql
CREATE TABLE artifact_diagrams (
    id uuid PRIMARY KEY,
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    page_number int NOT NULL,
    diagram_key text NOT NULL,
    diagram_meta jsonb NOT NULL,
    artifact_type text DEFAULT 'diagram' CHECK (artifact_type IN ('diagram', 'image_jpg', 'image_png')),
    image_uri text,           -- For diagrams and image artifacts (optional for diagrams)
    image_sha256 text,        -- For diagrams and image artifacts (optional for diagrams)
    image_metadata jsonb,     -- For diagrams and image artifacts (optional for diagrams)
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key)
);
```

**Note**: Diagrams (`artifact_type = 'diagram'`) can optionally have `image_uri` and `image_sha256` fields to store their original images for analysis. Image artifacts (`artifact_type = 'image_jpg'` or `'image_png'`) must have these fields.

### Unified Repository Methods

#### Access Methods (Contract Analysis Workflow)
```python
# Get all page content regardless of workflow that created it
page_artifacts = await artifacts_repo.get_all_page_artifacts(
    content_hmac, algorithm_version, params_fingerprint
)

# Get all visual content regardless of workflow that created it  
visual_artifacts = await artifacts_repo.get_all_visual_artifacts(
    content_hmac, algorithm_version, params_fingerprint
)

# Get comprehensive summary of what's available
summary = await artifacts_repo.get_document_processing_summary(
    content_hmac, algorithm_version, params_fingerprint
)
```

#### Insertion Methods (Processing Workflows)
```python
# Insert page artifact with type discrimination
page_artifact = await artifacts_repo.insert_unified_page_artifact(
    content_hmac=content_hmac,
    algorithm_version=1,
    params_fingerprint="main_workflow",
    page_number=1,
    page_text_uri="supabase://documents/text.txt",
    page_text_sha256="abc123...",
    content_type="text",  # or "markdown", "json_metadata"
    layout={"columns": 2},
    metrics={"word_count": 500}
)

# Insert visual artifact with type discrimination
visual_artifact = await artifacts_repo.insert_unified_visual_artifact(
    content_hmac=content_hmac,
    algorithm_version=1, 
    params_fingerprint="external_ocr",
    page_number=1,
    diagram_key="page_image_1",
    artifact_type="image_jpg",  # or "diagram", "image_png"
    image_uri="supabase://documents/image.jpg",
    image_sha256="def456...",
    image_metadata={"width": 1200, "height": 800}
)
```

## Workflow Usage Patterns

### Main Document Processing Workflow
```python
# Traditional text and diagram processing
await artifacts_repo.insert_unified_page_artifact(
    content_type="text",
    layout=pymupdf_layout_data,
    metrics={"word_count": word_count, "confidence": 0.95}
)

# Store diagram with its original image for analysis
await artifacts_repo.insert_unified_visual_artifact(
    artifact_type="diagram",
    diagram_meta={"type": "site_plan", "confidence": 0.88},
    image_uri="supabase://artifacts/diagram.jpg",  # Original image for analysis
    image_sha256="abc123...",
    image_metadata={"width": 1200, "height": 800, "source": "pdf_extraction"}
)

# Store diagram without image (metadata only)
await artifacts_repo.insert_unified_visual_artifact(
    artifact_type="diagram",
    diagram_meta={"type": "survey_diagram", "confidence": 0.92}
    # No image storage needed for metadata-only diagrams
)
```

### External OCR Processing Workflow  
```python
# External OCR page images and metadata
await artifacts_repo.insert_unified_visual_artifact(
    artifact_type="image_jpg",
    diagram_key=f"page_image_{page_number}",
    image_uri=jpg_uri,
    image_sha256=jpg_hash,
    image_metadata={"source": "external_ocr"}
)

await artifacts_repo.insert_unified_page_artifact(
    content_type="json_metadata", 
    metrics=ocr_stats,
    page_text_uri=json_uri
)
```

### Main Contract Analysis Workflow
```python
# Single interface to get all processed results
summary = await artifacts_repo.get_document_processing_summary(
    content_hmac, algorithm_version, params_fingerprint
)

# Intelligent routing based on what's available
if summary["processing_workflows"]:
    if "main_document_processing" in summary["processing_workflows"]:
        # Use text artifacts and diagrams
        pages = await artifacts_repo.get_all_page_artifacts(...)
        diagrams = await artifacts_repo.get_all_visual_artifacts(...)
        
    if "external_ocr_processing" in summary["processing_workflows"]:
        # External OCR results are also available
        # Can access markdown and JSON metadata through same interface
        all_pages = [p for p in pages if p.content_type in ["text", "markdown"]]
        all_images = [v for v in visuals if v.artifact_type in ["diagram", "image_jpg"]]
```

## Benefits

1. **Simplified Retrieval**: Single method call gets all artifacts regardless of source workflow
2. **Automatic Workflow Detection**: System detects which workflows processed the document
3. **Type Safety**: Content and artifact types prevent confusion between formats
4. **Backward Compatibility**: Legacy view support during transition period
5. **Unified Interface**: Contract analysis workflow doesn't need workflow-specific logic

## Implementation Status

### ✅ Completed
1. **Unified Tables**: Extended `artifact_pages` and `artifact_diagrams` with type discrimination
2. **Repository Methods**: All unified methods implemented in `ArtifactsRepository`
3. **Write Operations**: All nodes use `insert_unified_page_artifact` and `insert_unified_visual_artifact`
4. **Read Operations**: Nodes updated to use `get_all_page_artifacts` and `get_all_visual_artifacts`
5. **Helper Methods**: Added `get_page_artifacts_by_content_hmac` and `get_diagram_artifacts_by_content_hmac` for simplified queries
6. **Table Refactoring**: Renamed `text_extraction_artifacts` → `artifacts_full_text`
7. **Data Model**: Removed `documents.full_text` field; using `artifact_text_id` as single source of truth

### 🔄 In Progress
- Testing and validation of unified retrieval methods
- Documentation updates for API changes

### 📋 TODO
- Remove legacy tables (`artifact_pages_jpg`, `artifact_pages_json`) after validation
- Update client code to use unified artifact system

## Migration Strategy

1. **Phase 1**: ✅ Deploy unified tables with backward compatibility views
2. **Phase 2**: ✅ Update workflows to use unified insertion methods
3. **Phase 3**: ✅ Update contract analysis to use unified retrieval methods
4. **Phase 4**: 🔄 Remove legacy tables after validation

## Example Contract Analysis Integration

```python
class ContractAnalysisWorkflow:
    async def get_document_artifacts(self, content_hmac: str) -> ProcessedArtifacts:
        """Get all available artifacts for contract analysis."""
        
        # Single method call gets everything
        summary = await self.artifacts_repo.get_document_processing_summary(
            content_hmac, algorithm_version=1, params_fingerprint="any"
        )
        
        # No need to check multiple tables or understand workflow differences
        pages = await self.artifacts_repo.get_all_page_artifacts(...)
        visuals = await self.artifacts_repo.get_all_visual_artifacts(...)
        
        return ProcessedArtifacts(
            text_pages=[p for p in pages if p.content_type in ["text", "markdown"]],
            metadata_pages=[p for p in pages if p.content_type == "json_metadata"],
            diagrams=[v for v in visuals if v.artifact_type == "diagram"],
            images=[v for v in visuals if v.artifact_type.startswith("image_")],
            workflows_used=summary["processing_workflows"]
        )
```