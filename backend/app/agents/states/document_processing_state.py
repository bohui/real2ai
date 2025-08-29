from typing import TypedDict, Dict, Optional, Any, Annotated

from app.schema.document import (
    ProcessedDocumentSummary,
    TextExtractionResult,
    DiagramProcessingResult,
)
from app.agents.states.base import LangGraphBaseState


class ErrorDetails(TypedDict):
    """Schema for error details in document processing state."""

    node: str
    error_type: str
    error_message: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None
    root_cause_type: Optional[str] = None
    root_cause_message: Optional[str] = None
    exception_chain: Optional[str] = None
    node_location: Optional[str] = None
    error_category: Optional[str] = None


class DocumentProcessingState(LangGraphBaseState):
    """
    State schema for the document processing subflow.

    Required fields:
    - document_id: ID of document to process
    - use_llm: Whether to use LLM for advanced OCR/analysis

    Working fields (populated during flow):
    - storage_path: Path to document in storage
    - file_type: Detected file type
    - content_hash: Content hash for deduplication (inherited from LangGraphBaseState)
    - content_hmac: HMAC for artifact key generation (inherited from LangGraphBaseState)
    - algorithm_version: Version of processing algorithm
    - params_fingerprint: Fingerprint of processing parameters
    - text_extraction_result: Results from text extraction
    - local_tmp_path: Local temp file path for the document (to avoid re-downloads)
    - diagram_processing_result: Results from diagram processing

    Output fields:
    - processed_summary: Final ProcessedDocumentSummary result

    Error fields:
    - error: Error message if processing fails
    - error_details: Detailed error information

    Progress fields:
    - notify_progress: Optional callback for per-page progress updates (inherited from LangGraphBaseState)
    - contract_id: Optional contract ID for progress routing

    All fields use Annotated types with reducer functions to prevent LangGraph concurrent update errors.
    """

    # Required input - must be annotated for concurrent updates
    document_id: Annotated[str, lambda x, y: y]  # Last value wins
    use_llm: Annotated[bool, lambda x, y: y]  # Last value wins

    # Optional input overrides - must be annotated for concurrent updates
    australian_state: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    contract_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    document_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins

    # Working state - must be annotated for concurrent updates
    storage_path: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    file_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    algorithm_version: Annotated[Optional[int], lambda x, y: y]  # Last value wins
    params_fingerprint: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    local_tmp_path: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    text_extraction_result: Annotated[
        Optional[TextExtractionResult], lambda x, y: y
    ]  # Last value wins
    diagram_processing_result: Annotated[
        Optional[DiagramProcessingResult], lambda x, y: y
    ]  # Last value wins
    layout_format_result: Annotated[
        Optional[Any], lambda x, y: y
    ]  # LayoutFormatResult from LayoutFormatCleanupNode

    # Output - must be annotated for concurrent updates
    processed_summary: Annotated[
        Optional[ProcessedDocumentSummary], lambda x, y: y
    ]  # Last value wins

    # Error handling - must be annotated for concurrent updates
    error: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    error_details: Annotated[Optional[ErrorDetails], lambda x, y: y]  # Last value wins

    # Contract ID if nodes need it for progress routing - must be annotated for concurrent updates
    contract_id: Annotated[Optional[str], lambda x, y: y]  # Last value wins
