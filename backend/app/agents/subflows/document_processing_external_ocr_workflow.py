"""
DocumentProcessingExternalOCRWorkflow - LangGraph Subflow for External OCR Processing

This module implements a specialized LangGraph StateGraph for processing external OCR output files.
It replaces paragraph-based processing with page-based artifacts (MD, JPG, JSON) and extracts
embedded diagrams from markdown content.

Architecture:
- Page-based artifact storage using content-addressed keys
- External OCR file ingestion and normalization
- Base64 image extraction from markdown content
- Idempotent processing with ON CONFLICT DO NOTHING
- User-aware authentication throughout the flow
"""

import logging
from typing import Dict, Any, Optional, Annotated
from datetime import datetime, timezone
from langgraph.graph import StateGraph

from app.schema.document import ProcessedDocumentSummary, ProcessingErrorResponse
from app.core.langsmith_config import langsmith_trace
from app.agents.subflows.document_processing_workflow import DocumentProcessingState

logger = logging.getLogger(__name__)


class ExternalOCRProcessingState(DocumentProcessingState):
    """
    Extended state schema for external OCR processing workflow.

    Additional fields:
    - external_ocr_dir: Directory containing external OCR output files
    - content_hmac: Content HMAC for artifact addressing (inherited from DocumentProcessingState)
    - algorithm_version: Algorithm version for artifact versioning (inherited from DocumentProcessingState)
    - params_fingerprint: Parameters fingerprint for artifact identification (inherited from DocumentProcessingState)
    - ocr_pages: List of OCR page file mappings
    - page_artifacts: List of unified page artifact metadata (text, markdown, JSON)
    - diagram_artifacts: List of unified visual artifact metadata (diagrams, images)

    All additional fields use Annotated types with reducer functions to prevent LangGraph concurrent update errors.
    """

    # External OCR specific fields - must be annotated for concurrent updates
    external_ocr_dir: Annotated[Optional[str], lambda x, y: y]  # Last value wins

    # OCR file mapping - must be annotated for concurrent updates
    ocr_pages: Annotated[Optional[list], lambda x, y: y]  # Last value wins

    # Unified artifact results - must be annotated for concurrent updates
    page_artifacts: Annotated[Optional[list], lambda x, y: y]  # Last value wins
    diagram_artifacts: Annotated[Optional[list], lambda x, y: y]  # Last value wins


class DocumentProcessingExternalOCRWorkflow:
    """
    LangGraph StateGraph for external OCR document processing.

    This workflow handles the external OCR processing pipeline:
    1. Ingest external OCR output files (MD, JPG, JSON per page)
    2. Save markdown content as unified page artifacts (content_type="markdown")
    3. Save JPG images as unified visual artifacts (artifact_type="image_jpg")
    4. Save JSON metadata as unified page artifacts (content_type="json_metadata")
    5. Extract embedded diagrams from markdown content
    6. Build final summary result

    The workflow is user-aware and maintains authentication context throughout.
    All database operations respect Row Level Security (RLS) policies.
    """

    def __init__(self, storage_bucket: str = "documents"):
        """
        Initialize the external OCR processing workflow.

        Args:
            storage_bucket: Storage bucket name for file operations
        """
        self.storage_bucket = storage_bucket

        # Initialize nodes (will be created in _create_nodes)
        self.nodes = {}

        # Create workflow
        self.workflow = self._create_workflow()

        logger.info(
            f"DocumentProcessingExternalOCRWorkflow initialized with storage bucket: {storage_bucket}"
        )

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with external OCR processing nodes."""
        workflow = StateGraph(ExternalOCRProcessingState)

        # Import nodes
        from app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node import (
            IngestExternalOCROutputsNode,
        )
        from app.agents.nodes.document_processing_subflow.save_page_markdown_node import (
            SavePageMarkdownAsArtifactPagesNode,
        )
        from app.agents.nodes.document_processing_subflow.save_page_jpg_node import (
            SavePageJPGAsArtifactPagesJPGNode,
        )
        from app.agents.nodes.document_processing_subflow.save_page_json_node import (
            SavePageJSONAsArtifactPagesJSONNode,
        )
        from app.agents.nodes.document_processing_subflow.extract_diagrams_node import (
            ExtractDiagramsFromMarkdownNode,
        )

        # Initialize nodes
        self.ingest_ocr_outputs_node = IngestExternalOCROutputsNode()
        self.save_markdown_node = SavePageMarkdownAsArtifactPagesNode()
        self.save_jpg_node = SavePageJPGAsArtifactPagesJPGNode()
        self.save_json_node = SavePageJSONAsArtifactPagesJSONNode()
        self.extract_diagrams_node = ExtractDiagramsFromMarkdownNode()

        # Store nodes for access
        self.nodes = {
            "ingest_ocr_outputs": self.ingest_ocr_outputs_node,
            "save_markdown": self.save_markdown_node,
            "save_jpg": self.save_jpg_node,
            "save_json": self.save_json_node,
            "extract_diagrams": self.extract_diagrams_node,
        }

        # Add nodes to workflow
        workflow.add_node("ingest_ocr_outputs", self.ingest_ocr_outputs_node)
        workflow.add_node("save_markdown", self.save_markdown_node)
        workflow.add_node("save_jpg", self.save_jpg_node)
        workflow.add_node("save_json", self.save_json_node)
        workflow.add_node("extract_diagrams", self.extract_diagrams_node)
        workflow.add_node("error_handling", self.error_handling)
        workflow.add_node("build_summary", self.build_summary)

        # Set entry point
        workflow.set_entry_point("ingest_ocr_outputs")

        # Define workflow edges with error handling
        workflow.add_conditional_edges(
            "ingest_ocr_outputs",
            self.check_ingestion_success,
            {"success": "save_markdown", "error": "error_handling"},
        )

        workflow.add_conditional_edges(
            "save_markdown",
            self.check_processing_success,
            {"success": "save_jpg", "error": "error_handling"},
        )

        workflow.add_conditional_edges(
            "save_jpg",
            self.check_processing_success,
            {"success": "save_json", "error": "error_handling"},
        )

        workflow.add_conditional_edges(
            "save_json",
            self.check_processing_success,
            {"success": "extract_diagrams", "error": "error_handling"},
        )

        workflow.add_conditional_edges(
            "extract_diagrams",
            self.check_processing_success,
            {"success": "build_summary", "error": "error_handling"},
        )

        # Terminal edges
        workflow.add_edge("build_summary", "__end__")
        workflow.add_edge("error_handling", "__end__")

        return workflow.compile()

    # Node execution methods
    @langsmith_trace(name="ingest_ocr_outputs", run_type="tool")
    async def ingest_ocr_outputs(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Ingest and normalize external OCR output files."""
        return await self.ingest_ocr_outputs_node.execute(state)

    @langsmith_trace(name="save_markdown", run_type="tool")
    async def save_markdown(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Save markdown content as page artifacts."""
        return await self.save_markdown_node.execute(state)

    @langsmith_trace(name="save_jpg", run_type="tool")
    async def save_jpg(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Save JPG images as unified visual artifacts."""
        return await self.save_jpg_node.execute(state)

    @langsmith_trace(name="save_json", run_type="tool")
    async def save_json(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Save JSON metadata as unified page artifacts."""
        return await self.save_json_node.execute(state)

    @langsmith_trace(name="extract_diagrams", run_type="tool")
    async def extract_diagrams(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Extract embedded diagrams from markdown content."""
        return await self.extract_diagrams_node.execute(state)

    async def build_summary(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Build final processing summary result."""
        try:
            # Calculate summary metrics from unified artifacts
            all_page_artifacts = state.get("page_artifacts", [])
            all_visual_artifacts = state.get("diagram_artifacts", [])

            # Count by artifact type from unified lists
            markdown_count = len(
                [p for p in all_page_artifacts if p.get("content_type") == "markdown"]
            )
            json_count = len(
                [
                    p
                    for p in all_page_artifacts
                    if p.get("content_type") == "json_metadata"
                ]
            )
            text_count = len(
                [p for p in all_page_artifacts if p.get("content_type") == "text"]
            )
            page_count = len(all_page_artifacts)

            jpg_count = len(
                [
                    v
                    for v in all_visual_artifacts
                    if v.get("artifact_type") == "image_jpg"
                ]
            )
            diagram_count = len(
                [v for v in all_visual_artifacts if v.get("artifact_type") == "diagram"]
            )

            # Build ProcessedDocumentSummary
            summary = ProcessedDocumentSummary(
                success=True,
                document_id=state["document_id"],
                processing_time=0.0,  # Could track actual time if needed
                processing_timestamp=datetime.now(timezone.utc).isoformat(),
                total_pages=page_count,
                total_words=sum(
                    artifact.get("metrics", {}).get("word_count", 0)
                    for artifact in all_page_artifacts
                ),
                extraction_methods=["external_ocr"],
                overall_confidence=1.0,  # External OCR is considered reliable
                pages=[
                    {
                        "page_number": artifact["page_number"],
                        "word_count": artifact.get("metrics", {}).get("word_count", 0),
                        "confidence": 1.0,
                    }
                    for artifact in all_page_artifacts
                ],
                artifacts={
                    "page_count": page_count,
                    "markdown_count": markdown_count,
                    "json_count": json_count,
                    "text_count": text_count,
                    "jpg_count": jpg_count,
                    "diagram_count": diagram_count,
                    "content_hmac": state.get("content_hmac"),
                    "algorithm_version": state.get("algorithm_version", 1),
                    "params_fingerprint": state.get(
                        "params_fingerprint", "external_ocr"
                    ),
                },
            )

            state["processed_summary"] = summary

            logger.info(
                f"External OCR processing completed successfully",
                extra={
                    "document_id": state["document_id"],
                    "page_count": page_count,
                    "markdown_count": markdown_count,
                    "json_count": json_count,
                    "text_count": text_count,
                    "jpg_count": jpg_count,
                    "diagram_count": diagram_count,
                },
            )

            return state

        except Exception as e:
            logger.error(f"Build summary failed: {e}", exc_info=True)
            state["error"] = f"Failed to build summary: {str(e)}"
            state["error_details"] = {
                "node": "build_summary",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            return state

    async def error_handling(
        self, state: ExternalOCRProcessingState
    ) -> ExternalOCRProcessingState:
        """Handle processing errors and create error response."""
        error_message = state.get("error", "Unknown error occurred")
        error_details = state.get("error_details", {})

        logger.error(
            f"External OCR processing failed: {error_message}",
            extra={
                "document_id": state.get("document_id"),
                "error_details": error_details,
            },
        )

        # Clear processed_summary to ensure error response
        state["processed_summary"] = None

        return state

    # Conditional edge functions
    def check_ingestion_success(self, state: ExternalOCRProcessingState) -> str:
        """Check if OCR ingestion was successful."""
        if state.get("error"):
            return "error"
        elif state.get("ocr_pages"):
            return "success"
        else:
            return "error"

    def check_processing_success(self, state: ExternalOCRProcessingState) -> str:
        """Check if current processing step was successful."""
        if state.get("error"):
            return "error"
        else:
            return "success"

    @langsmith_trace(name="external_ocr_processing_workflow", run_type="chain")
    async def process_external_ocr(
        self,
        document_id: str,
        external_ocr_dir: str,
        content_hmac: str,
        algorithm_version: int = 1,
        params_fingerprint: str = "external_ocr",
    ) -> ProcessedDocumentSummary | ProcessingErrorResponse:
        """
        Main entry point for external OCR processing.

        Args:
            document_id: ID of document to process
            external_ocr_dir: Directory containing external OCR output files
            content_hmac: Content HMAC for artifact addressing
            algorithm_version: Algorithm version for artifact versioning
            params_fingerprint: Parameters fingerprint for artifact identification

        Returns:
            ProcessedDocumentSummary on success or ProcessingErrorResponse on failure
        """
        try:
            # Create initial state
            initial_state = ExternalOCRProcessingState(
                document_id=document_id,
                use_llm=False,  # External OCR doesn't use LLM
                external_ocr_dir=external_ocr_dir,
                content_hmac=content_hmac,
                algorithm_version=algorithm_version,
                params_fingerprint=params_fingerprint,
                ocr_pages=None,
                page_artifacts=None,
                diagram_artifacts=None,
                processed_summary=None,
                error=None,
                error_details=None,
                # Required parent fields
                storage_path=external_ocr_dir,
                file_type="external_ocr",
                text_extraction_result=None,
                diagram_processing_result=None,
            )

            # Execute workflow
            result_state = await self.workflow.ainvoke(initial_state)

            # Return appropriate response
            if result_state.get("processed_summary"):
                return result_state["processed_summary"]
            elif result_state.get("error"):
                return ProcessingErrorResponse(
                    success=False,
                    error=result_state["error"],
                    processing_time=0.0,
                    processing_timestamp=datetime.now(timezone.utc).isoformat(),
                    details=result_state.get("error_details"),
                )
            else:
                return ProcessingErrorResponse(
                    success=False,
                    error="Unknown processing failure",
                    processing_time=0.0,
                    processing_timestamp=datetime.now(timezone.utc).isoformat(),
                )

        except Exception as e:
            logger.error(f"External OCR workflow failed: {e}", exc_info=True)
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
            "workflow_type": "external_ocr_processing",
            "storage_bucket": self.storage_bucket,
            "total_nodes": len(self.nodes),
            "node_metrics": node_metrics,
        }
