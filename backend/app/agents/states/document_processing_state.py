from typing import TypedDict, Dict, Optional, Any

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
    - content_hash: Content hash for deduplication
    - content_hmac: HMAC for artifact key generation
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
    - notify_progress: Optional callback for per-page progress updates
    - contract_id: Optional contract ID for progress routing
    """

    # Required input
    document_id: str
    use_llm: bool

    # Optional input overrides
    australian_state: Optional[str]
    contract_type: Optional[str]
    document_type: Optional[str]

    # Working state
    storage_path: Optional[str]
    file_type: Optional[str]
    content_hmac: Optional[str]
    algorithm_version: Optional[int]
    params_fingerprint: Optional[str]
    local_tmp_path: Optional[str]
    text_extraction_result: Optional[TextExtractionResult]
    diagram_processing_result: Optional[DiagramProcessingResult]
    layout_format_result: Optional[
        Any
    ]  # LayoutFormatResult from LayoutFormatCleanupNode

    # Output
    processed_summary: Optional[ProcessedDocumentSummary]

    # Error handling
    error: Optional[str]
    error_details: Optional[ErrorDetails]

    # Contract ID if nodes need it for progress routing
    contract_id: Optional[str]
