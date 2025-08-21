"""
DocumentProcessingWorkflow - LangGraph Subflow for Document Processing

This module implements a dedicated LangGraph StateGraph focused purely on document processing.
It extracts document processing logic from the main contract workflow into a reusable,
testable subflow with granular nodes.

Architecture:
- Dedicated state management for document processing operations
- Single responsibility nodes with clear interfaces
- User-aware authentication throughout the flow
- Comprehensive error handling and recovery
- Support for both LLM and non-LLM processing paths
"""

import logging
from typing import Dict, Any, Optional, TypedDict, Callable, Awaitable
from datetime import datetime, timezone
from langgraph.graph import StateGraph
from pydantic import BaseModel

from app.core.auth_context import AuthContext
from app.schema.document import (
    ProcessedDocumentSummary,
    ProcessingErrorResponse,
    TextExtractionResult,
    DiagramProcessingResult,
)
from app.core.langsmith_config import langsmith_trace

# ContractLayoutSummary no longer needed - using LayoutFormatCleanupNode instead

logger = logging.getLogger(__name__)


class ErrorDetails(BaseModel):
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


class DocumentProcessingState(TypedDict):
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
    content_hash: Optional[str]
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

    # Progress callback for per-page progress updates
    notify_progress: Optional[Callable[[str, int, str], Awaitable[None]]]

    # Contract ID if nodes need it for progress routing
    contract_id: Optional[str]


class DocumentProcessingWorkflow:
    """
    LangGraph StateGraph for document processing operations.

    This workflow handles the complete document processing pipeline:
    1. Fetch document metadata and validate access
    2. Check if already processed (short-circuit optimization)
    3. Mark processing as started
    4. Extract text using appropriate method (LLM/OCR/native)
    5. Save page-level analysis results
    6. Aggregate and save diagram detection results
    7. Update document metrics and status
    8. Build final summary result

    The workflow is user-aware and maintains authentication context throughout.
    All database operations respect Row Level Security (RLS) policies.
    """

    # Progress ranges for each step (defined centrally to avoid magic numbers)
    PROGRESS_RANGES = {
        "fetch_document_record": (0, 5),
        "already_processed_check": (5, 7),
        "mark_processing_started": (7, 8),
        "extract_text": (7, 34),
        # "save_pages": (28, 36),
        "save_diagrams": (34, 40),
        "update_metrics": (40, 41),
        "layout_format_cleanup": (41, 48),
        "mark_basic_complete": (48, 49),
        "build_summary": (49, 50),
    }

    def __init__(
        self,
        use_llm_document_processing: bool = True,
        storage_bucket: str = "documents",
    ):
        """
        Initialize the document processing workflow.

        Args:
            use_llm_document_processing: Enable advanced LLM-based OCR/analysis
            storage_bucket: Storage bucket name for file operations
        """
        self.use_llm_document_processing = use_llm_document_processing
        self.storage_bucket = storage_bucket

        # Initialize nodes (will be created in _create_nodes)
        self.nodes = {}

        # Create workflow
        self.workflow = self._create_workflow()

        logger.info(
            f"DocumentProcessingWorkflow initialized with LLM processing: {use_llm_document_processing}"
        )

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with document processing nodes."""
        workflow = StateGraph(DocumentProcessingState)

        # Import nodes here to avoid circular imports
        from app.agents.nodes.document_processing_subflow import (
            FetchDocumentRecordNode,
            AlreadyProcessedCheckNode,
            MarkProcessingStartedNode,
            ExtractTextNode,
            LayoutFormatCleanupNode,
            SavePagesNode,
            SaveDiagramsNode,
            UpdateMetricsNode,
            MarkBasicCompleteNode,
            BuildSummaryNode,
            ErrorHandlingNode,
        )

        # Initialize nodes
        self.fetch_document_node = FetchDocumentRecordNode()
        self.already_processed_check_node = AlreadyProcessedCheckNode()
        self.mark_processing_started_node = MarkProcessingStartedNode()
        self.extract_text_node = ExtractTextNode(
            use_llm=self.use_llm_document_processing,
            progress_range=self.PROGRESS_RANGES["extract_text"],
        )
        self.layout_format_cleanup_node = LayoutFormatCleanupNode(
            progress_range=self.PROGRESS_RANGES["layout_format_cleanup"]
        )
        # self.save_pages_node = SavePagesNode(
        #     progress_range=self.PROGRESS_RANGES["save_pages"]
        # )
        self.save_diagrams_node = SaveDiagramsNode(
            progress_range=self.PROGRESS_RANGES["save_diagrams"]
        )
        self.update_metrics_node = UpdateMetricsNode()
        self.mark_basic_complete_node = MarkBasicCompleteNode()
        self.build_summary_node = BuildSummaryNode()
        self.error_handling_node = ErrorHandlingNode()

        # Store nodes for access
        self.nodes = {
            "fetch_document_record": self.fetch_document_node,
            "already_processed_check": self.already_processed_check_node,
            "mark_processing_started": self.mark_processing_started_node,
            "extract_text": self.extract_text_node,
            "layout_format_cleanup": self.layout_format_cleanup_node,
            # "save_pages": self.save_pages_node,
            "save_diagrams": self.save_diagrams_node,
            "update_metrics": self.update_metrics_node,
            "mark_basic_complete": self.mark_basic_complete_node,
            "build_summary": self.build_summary_node,
            "error_handling": self.error_handling_node,
        }

        # Add nodes to workflow
        workflow.add_node("fetch_document_record", self.fetch_document_record)
        workflow.add_node("already_processed_check", self.already_processed_check)
        workflow.add_node("mark_processing_started", self.mark_processing_started)
        workflow.add_node("extract_text", self.extract_text)
        workflow.add_node("layout_format_cleanup", self.layout_format_cleanup)
        # workflow.add_node("save_pages", self.save_pages)
        workflow.add_node("save_diagrams", self.save_diagrams)
        workflow.add_node("update_metrics", self.update_metrics)
        workflow.add_node("mark_basic_complete", self.mark_basic_complete)
        workflow.add_node("build_summary", self.build_summary)
        workflow.add_node("error_handling", self.error_handling)

        # Set entry point
        workflow.set_entry_point("fetch_document_record")

        # Define workflow edges
        workflow.add_edge("fetch_document_record", "already_processed_check")

        # Conditional edge from already_processed_check
        workflow.add_conditional_edges(
            "already_processed_check",
            self.check_already_processed,
            {
                "already_processed": "build_summary",
                "needs_processing": "mark_processing_started",
                "error": "error_handling",
            },
        )

        # Processing pipeline
        workflow.add_edge("mark_processing_started", "extract_text")

        # Conditional edge from extract_text
        workflow.add_conditional_edges(
            "extract_text",
            self.check_extraction_success,
            {"success": "save_diagrams", "error": "error_handling"},
        )

        # Success pipeline
        # workflow.add_edge("save_pages", "save_diagrams")
        workflow.add_edge("save_diagrams", "update_metrics")
        # Run layout format cleanup before marking basic complete
        workflow.add_edge("update_metrics", "layout_format_cleanup")
        workflow.add_edge("layout_format_cleanup", "mark_basic_complete")
        workflow.add_edge("mark_basic_complete", "build_summary")

        # Terminal edges
        workflow.add_edge("build_summary", "__end__")
        workflow.add_edge("error_handling", "__end__")

        return workflow.compile()

    async def _notify_status(self, state, step: str, percent: int, desc: str) -> None:
        """Notify progress status - similar to contract workflow pattern."""
        # Best-effort async persistence callback from state
        notify = (state or {}).get("notify_progress")
        if notify:
            try:
                await notify(step, percent, desc)
            except Exception as persist_error:
                logger.debug(
                    f"[ProgressTracking] Persist callback failed: {persist_error}"
                )

    # Node execution methods
    @langsmith_trace(name="fetch_document_record", run_type="tool")
    async def fetch_document_record(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Fetch document metadata from database."""
        result = await self.fetch_document_node.execute(state)
        # Notify progress completion for non-incremental step
        await self._notify_status(
            state,
            "fetch_document_record",
            self.PROGRESS_RANGES["fetch_document_record"][1],
            "Document record fetched",
        )
        return result

    @langsmith_trace(name="already_processed_check", run_type="tool")
    async def already_processed_check(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Check if document is already processed."""
        result = await self.already_processed_check_node.execute(state)
        # Notify progress completion for non-incremental step
        await self._notify_status(
            state,
            "already_processed_check",
            self.PROGRESS_RANGES["already_processed_check"][1],
            "Already processed check complete",
        )
        return result

    @langsmith_trace(name="mark_processing_started", run_type="tool")
    async def mark_processing_started(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Mark processing as started in database."""
        result = await self.mark_processing_started_node.execute(state)
        await self._notify_status(
            state,
            "mark_processing_started",
            self.PROGRESS_RANGES["mark_processing_started"][1],
            "Processing started",
        )
        return result

    async def extract_text(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Extract text from document using appropriate method."""
        return await self.extract_text_node.execute(state)

    # @langsmith_trace(name="layout_format_cleanup", run_type="tool")
    async def layout_format_cleanup(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Clean and format text layout without LLM processing."""
        return await self.layout_format_cleanup_node.execute(state)

    # @langsmith_trace(name="save_pages", run_type="tool")
    # async def save_pages(
    #     self, state: DocumentProcessingState
    # ) -> DocumentProcessingState:
    #     """Save page-level analysis results to database."""
    #     return await self.save_pages_node.execute(state)

    # @langsmith_trace(name="save_diagrams", run_type="tool")
    async def save_diagrams(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Save diagram detection results to database."""
        return await self.save_diagrams_node.execute(state)

    # @langsmith_trace(name="update_metrics", run_type="tool")
    async def update_metrics(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Update document with aggregated metrics."""
        result = await self.update_metrics_node.execute(state)
        await self._notify_status(
            state,
            "update_metrics",
            self.PROGRESS_RANGES["update_metrics"][1],
            "Metrics update complete",
        )
        return result

    # @langsmith_trace(name="mark_basic_complete", run_type="tool")
    async def mark_basic_complete(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Mark document processing as complete."""
        result = await self.mark_basic_complete_node.execute(state)
        # Notify progress completion for non-incremental step
        await self._notify_status(
            state,
            "mark_basic_complete",
            self.PROGRESS_RANGES["mark_basic_complete"][1],
            "Basic processing complete",
        )
        return result

    # @langsmith_trace(name="build_summary", run_type="chain")
    async def build_summary(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Build final processing summary result."""
        result = await self.build_summary_node.execute(state)
        # Notify progress completion for non-incremental step
        await self._notify_status(
            state,
            "build_summary",
            self.PROGRESS_RANGES["build_summary"][1],
            "Summary build complete",
        )
        return result

    # @langsmith_trace(name="error_handling", run_type="tool")
    async def error_handling(
        self, state: DocumentProcessingState
    ) -> DocumentProcessingState:
        """Handle processing errors and update status."""
        return await self.error_handling_node.execute(state)

    # Conditional edge functions
    def check_already_processed(self, state: DocumentProcessingState) -> str:
        """Check if document needs processing or is already done."""
        if state.get("error"):
            return "error"
        elif state.get("processed_summary"):
            return "already_processed"
        else:
            return "needs_processing"

    def check_extraction_success(self, state: DocumentProcessingState) -> str:
        """Check if text extraction was successful."""
        text_extraction_result = state.get("text_extraction_result")
        if (
            state.get("error")
            or not text_extraction_result
            or not text_extraction_result.success
        ):
            return "error"
        else:
            return "success"

    def check_processing_success(self, state: DocumentProcessingState) -> str:
        """Check if processing step was successful."""
        if state.get("error"):
            return "error"
        else:
            return "success"

    @langsmith_trace(name="document_processing_workflow", run_type="chain")
    async def process_document(
        self,
        document_id: str,
        use_llm: bool = None,
        content_hash: Optional[str] = None,
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        document_type: Optional[str] = None,
        notify_progress: Optional[Callable[[str, int, str], Awaitable[None]]] = None,
        contract_id: Optional[str] = None,
    ) -> ProcessedDocumentSummary | ProcessingErrorResponse:
        """
        Main entry point for document processing.

        Args:
            document_id: ID of document to process
            use_llm: Override LLM usage setting (optional)
            content_hash: Content hash override (optional)
            australian_state: Australian state for context (optional)
            contract_type: Contract type for context (optional)
            document_type: Document type for context (optional)
            notify_progress: Callback for per-page progress updates (optional)
            contract_id: Contract ID for progress routing (optional)

        Returns:
            ProcessedDocumentSummary on success or ProcessingErrorResponse on failure
        """
        try:
            # Create initial state
            initial_state = DocumentProcessingState(
                document_id=document_id,
                use_llm=(
                    use_llm if use_llm is not None else self.use_llm_document_processing
                ),
                content_hash=content_hash,
                australian_state=australian_state,
                contract_type=contract_type,
                document_type=document_type,
                notify_progress=notify_progress,
                contract_id=contract_id,
                storage_path=None,
                file_type=None,
                text_extraction_result=None,
                diagram_processing_result=None,
                layout_format_result=None,
                processed_summary=None,
                error=None,
                error_details=None,
            )

            # Wire progress callback to extract_text_node if provided
            if notify_progress:
                self.extract_text_node.set_progress_callback(notify_progress)
                # self.save_pages_node.set_progress_callback(notify_progress)
                self.save_diagrams_node.set_progress_callback(notify_progress)

            # Execute workflow
            result_state = await self.workflow.ainvoke(initial_state)

            # Return appropriate response
            if result_state.get("processed_summary"):
                return result_state["processed_summary"]
            elif result_state.get("error"):
                error_details = result_state.get("error_details")
                return ProcessingErrorResponse(
                    success=False,
                    error=result_state["error"],
                    processing_time=0.0,
                    processing_timestamp=datetime.now(timezone.utc).isoformat(),
                    recovery_suggestions=[
                        "Check document format and size",
                        "Verify file is not corrupted",
                        "Try processing with different settings",
                        "Contact support if the problem persists",
                    ],
                )
            else:
                return ProcessingErrorResponse(
                    success=False,
                    error="Unknown processing failure",
                    processing_time=0.0,
                    processing_timestamp=datetime.now(timezone.utc).isoformat(),
                    recovery_suggestions=[
                        "Check document format and size",
                        "Verify file is not corrupted",
                        "Try processing with different settings",
                        "Contact support if the problem persists",
                    ],
                )

        except Exception as e:
            logger.error(f"Document processing workflow failed: {e}", exc_info=True)
            return ProcessingErrorResponse(
                success=False,
                error=f"Workflow execution failed: {str(e)}",
                processing_time=0.0,
                processing_timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get workflow performance metrics."""
        node_metrics = {}
        for node_name, node in self.nodes.items():
            if hasattr(node, "get_metrics"):
                node_metrics[node_name] = node.get_metrics()

        return {
            "workflow_type": "document_processing",
            "use_llm_processing": self.use_llm_document_processing,
            "storage_bucket": self.storage_bucket,
            "total_nodes": len(self.nodes),
            "node_metrics": node_metrics,
        }
