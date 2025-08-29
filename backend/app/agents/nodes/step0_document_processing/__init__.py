"""
Document Processing Subflow Nodes

This package contains all the nodes for the DocumentProcessingWorkflow.
Each node has a single responsibility and clear interface.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from .fetch_document_node import FetchDocumentRecordNode
    from .already_processed_check_node import AlreadyProcessedCheckNode
    from .mark_processing_started_node import MarkProcessingStartedNode
    from .extract_text_node import ExtractTextNode
    from .layout_summarise_node_too_slow import LayoutSummariseNode
    from .layout_format_cleanup_node import LayoutFormatCleanupNode
    from .detect_diagrams_with_ocr_node import DetectDiagramsWithOCRNode
    from .extract_diagrams_node import ExtractDiagramsFromMarkdownNode
    from .ingest_external_ocr_outputs_node import IngestExternalOCROutputsNode

    from .save_pages_node import SavePagesNode
    from .save_diagrams_node import SaveDiagramsNode
    from .save_page_markdown_node import SavePageMarkdownAsArtifactPagesNode
    from .save_page_json_node import SavePageJSONAsArtifactPagesJSONNode
    from .save_page_jpg_node import SavePageJPGAsArtifactPagesJPGNode
    from .update_metrics_node import UpdateMetricsNode
    from .mark_basic_complete_node import MarkBasicCompleteNode
    from .build_summary_node import BuildSummaryNode
    from .error_handling_node import ErrorHandlingNode

    logger.debug("Successfully imported all document processing subflow nodes")

except ImportError as e:
    logger.error(f"Failed to import document processing subflow nodes: {e}")
    raise

__all__ = [
    "FetchDocumentRecordNode",
    "AlreadyProcessedCheckNode",
    "MarkProcessingStartedNode",
    "ExtractTextNode",
    "LayoutSummariseNode",
    "LayoutFormatCleanupNode",
    "DetectDiagramsWithOCRNode",
    "ExtractDiagramsFromMarkdownNode",
    "IngestExternalOCROutputsNode",
    "SavePagesNode",
    "SaveDiagramsNode",
    "SavePageMarkdownAsArtifactPagesNode",
    "SavePageJSONAsArtifactPagesJSONNode",
    "SavePageJPGAsArtifactPagesJPGNode",
    "UpdateMetricsNode",
    "MarkBasicCompleteNode",
    "BuildSummaryNode",
    "ErrorHandlingNode",
]
