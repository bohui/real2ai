"""
Document Processing Node for Contract Analysis Workflow

This module contains the node responsible for processing documents and extracting text content.
"""

import re
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from app.core.async_utils import AsyncContextManager, ensure_async_pool_initialization
from .base import BaseNode
from app.agents.subflows.document_processing_workflow import (
    DocumentProcessingWorkflow,
)
from app.schema.document import (
    ProcessedDocumentSummary,
    ProcessingErrorResponse,
)

logger = logging.getLogger(__name__)


class DocumentProcessingNode(BaseNode):
    """
    Node responsible for processing contract documents and extracting text content.

    This node handles:
    - Document text extraction using DocumentService
    - Text quality assessment
    - Metadata extraction and enrichment
    - Processing confidence scoring

    The node can operate with or without LLM assistance based on workflow configuration.
    """

    def __init__(self, workflow):
        super().__init__(workflow, "document_processing")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Process document and extract text content.

        Args:
            state: Current workflow state containing document information

        Returns:
            Updated state with processed document data
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting document processing", state)

            # Validate document metadata
            document_data: Dict[str, Any] = state.get("document_data", {})
            document_id = document_data.get("document_id")

            if not document_id:
                error_msg = "Missing document_id in document_data"
                self._log_step_debug(error_msg, state)
                return self.update_state_step(
                    state, "document_processing_failed", error=error_msg
                )

            # Use the document processing subflow directly (no Celery blocking)
            use_llm = self.use_llm_config.get("document_processing", True)
            from app.core.auth_context import AuthContext

            # Get current user ID for task context
            user_id = AuthContext.get_user_id()
            if not user_id:
                # Log diagnostic context to help identify why auth is missing
                try:
                    from app.core.auth_context import AuthContext as AC

                    self._log_step_debug(
                        "Missing AuthContext; attempting fallback to state user_id",
                        state,
                        {
                            "doc_id": document_id,
                            "has_token": bool(AC.get_user_token()),
                            "thread_name": __import__("threading")
                            .current_thread()
                            .name,
                        },
                    )
                except Exception:
                    pass

                # Fallback: use user_id from workflow state if available
                fallback_user_id = state.get("user_id")
                if fallback_user_id:
                    user_id = fallback_user_id
                else:
                    return self._handle_node_error(
                        state,
                        ValueError("User authentication required"),
                        "User authentication context required for document processing",
                        {"document_id": document_id, "use_llm": use_llm},
                    )

            # Run the subflow inline within the current task context
            try:
                # Ensure async context is properly managed to prevent event loop conflicts
                async with AsyncContextManager():
                    subflow = DocumentProcessingWorkflow(
                        use_llm_document_processing=use_llm, storage_bucket="documents"
                    )
                    content_hash = document_data.get("content_hash")
                    # Extract australian_state properly handling enum type
                    australian_state = state.get("australian_state", "NSW")
                    if hasattr(australian_state, "value"):
                        australian_state = australian_state.value
                    elif hasattr(australian_state, "name"):
                        australian_state = australian_state.name
                    else:
                        australian_state = str(australian_state)
                    
                    result = await subflow.process_document(
                        document_id=document_id, 
                        use_llm=use_llm, 
                        content_hash=content_hash,
                        australian_state=australian_state,
                        contract_type=state.get("contract_type", "purchase_agreement"),
                        document_type=state.get("document_type", "contract"),
                        notify_progress=state.get("notify_progress"),
                        contract_id=state.get("contract_id"),
                    )
                    summary = result
            except Exception as subflow_error:
                return self._handle_node_error(
                    state,
                    subflow_error,
                    f"Document processing subflow failed: {str(subflow_error)}",
                    {
                        "document_id": document_id,
                        "use_llm": use_llm,
                        "operation": "subflow_inline",
                    },
                )

            # Validate subflow result
            success = False
            error_msg = None
            if isinstance(summary, ProcessedDocumentSummary):
                success = bool(summary.success)
            elif isinstance(summary, ProcessingErrorResponse):
                success = False
                error_msg = summary.error
            else:
                # Fallback for unexpected type
                try:
                    success = bool(getattr(summary, "success", False))
                    error_msg = getattr(summary, "error", None)
                except Exception:
                    success = False
                    error_msg = "Processing failed"

            if not success:
                error_msg = error_msg or "Processing failed"
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    "Document processing failed",
                    {"document_id": document_id, "use_llm": use_llm},
                )

            # Extract text and metadata
            if isinstance(summary, ProcessedDocumentSummary):
                extracted_text = summary.full_text or ""
                extraction_method = summary.extraction_method or "unknown"
                extraction_confidence = float(summary.extraction_confidence or 0.0)
            else:
                # Defensive fallback for other schema types
                extracted_text = getattr(summary, "full_text", None) or getattr(
                    summary, "extracted_text", ""
                )
                extraction_method = getattr(summary, "extraction_method", "unknown")
                extraction_confidence = float(
                    getattr(summary, "extraction_confidence", 0.0)
                )

            # Assess text quality
            text_quality = (
                self._assess_text_quality(extracted_text)
                if self.enable_quality_checks
                else {"score": 0.8, "issues": []}
            )

            # Validate extracted text quality
            if not extracted_text or len(extracted_text.strip()) < 100:
                # Enhanced diagnostics for empty/insufficient text
                # Safely capture summary keys and success flag from Pydantic models
                try:
                    if hasattr(summary, "model_dump"):
                        summary_dict = summary.model_dump()  # pydantic v2
                    elif hasattr(summary, "dict"):
                        summary_dict = summary.dict()  # pydantic v1
                    else:
                        summary_dict = {k: getattr(summary, k) for k in dir(summary)}
                except Exception:
                    summary_dict = {}

                diagnostic_info = {
                    "character_count": len(extracted_text or ""),
                    "word_count": len((extracted_text or "").split()),
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "document_id": document_id,
                    "summary_keys": list(summary_dict.keys()),
                    "use_llm": use_llm,
                    "processing_success": bool(summary_dict.get("success", False)),
                }

                error_msg = f"Insufficient text content extracted from document (got {len(extracted_text or '')} characters)"

                # Log detailed diagnostic information for debugging
                self._log_warning(
                    f"Document processing extracted insufficient text: {diagnostic_info}",
                    extra=diagnostic_info,
                )

                return self._handle_node_error(
                    state,
                    Exception("Insufficient text content"),
                    error_msg,
                    diagnostic_info,
                )

            # Update confidence scores
            if "confidence_scores" not in state:
                state["confidence_scores"] = {}
            state["confidence_scores"]["document_processing"] = (
                extraction_confidence * text_quality["score"]
            )

            # Update state with processed data (align keys with downstream validators)
            text_quality_score = (
                float(text_quality.get("score", 0.0))
                if isinstance(text_quality, dict)
                else 0.0
            )

            updated_data = {
                # Keep detailed metadata (existing consumers rely on this)
                "document_metadata": {
                    "full_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "text_quality": text_quality,
                    # Add flattened score for compatibility with validators expecting this key
                    "text_quality_score": text_quality_score,
                    "character_count": len(extracted_text),
                    "total_word_count": len(extracted_text.split()),
                    "processing_timestamp": summary.get(
                        "processing_timestamp", datetime.now(UTC).isoformat()
                    ),
                    "enhanced_processing": True,
                    "llm_used": getattr(summary, "llm_used", False),
                },
                # Provide top-level quality metrics for report compilation and validation nodes
                "document_quality_metrics": {
                    "text_quality_score": text_quality_score,
                    "extraction_confidence": extraction_confidence,
                    # Simple completeness proxy based on content length
                    "completeness_score": (
                        1.0
                        if len(extracted_text) >= 1000
                        else 0.7 if len(extracted_text) >= 300 else 0.4
                    ),
                },
                # Provide top-level extracted_text for backward/compatibility checks
                "extracted_text": extracted_text,
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            self._log_step_debug(
                f"Document processing completed: {len(extracted_text)} chars extracted (LLM: {use_llm})",
                state,
                {
                    "extraction_method": extraction_method,
                    "confidence": extraction_confidence,
                },
            )

            return self.update_state_step(
                state, "document_processed", data=updated_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Document processing failed: {str(e)}",
                {"use_llm": self.use_llm_config.get("document_processing", True)},
            )

    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """
        Assess the quality of extracted text content.

        Evaluates text based on:
        - Content length and word count
        - OCR quality indicators
        - Contract-specific keyword presence
        - Text readability metrics

        Args:
            text: Extracted text to assess

        Returns:
            Dictionary containing quality score and identified issues
        """
        if not text:
            return {"score": 0.0, "issues": ["No text content"]}

        # Enhanced quality metrics
        words = text.split()
        total_chars = len(text)
        total_words = len(words)

        issues = []
        score = 1.0

        # Check for minimum content
        if total_chars < 200:
            issues.append("Very short document")
            score *= 0.5

        if total_words < 50:
            issues.append("Too few words extracted")
            score *= 0.5

        # Enhanced OCR quality checks
        if words:
            single_char_words = sum(1 for word in words if len(word) == 1)
            single_char_ratio = single_char_words / total_words

            if single_char_ratio > 0.3:
                issues.append("High ratio of single characters (poor OCR)")
                score *= 0.6

            # Check for repeated characters (OCR artifacts)
            repeated_patterns = len(re.findall(r"(.)\1{3,}", text))
            if repeated_patterns > 5:
                issues.append("Multiple repeated character patterns detected")
                score *= 0.7

        # Enhanced contract keyword detection
        contract_keywords = [
            "contract",
            "agreement",
            "purchase",
            "sale",
            "property",
            "vendor",
            "purchaser",
            "settlement",
            "deposit",
            "conditions",
            "title",
            "transfer",
        ]

        keyword_matches = sum(
            1 for keyword in contract_keywords if keyword.lower() in text.lower()
        )
        keyword_coverage = keyword_matches / len(contract_keywords)

        if keyword_coverage < 0.2:
            issues.append("Low contract keyword coverage")
            score *= 0.8

        # Additional quality checks
        average_word_length = (
            sum(len(word) for word in words) / total_words if words else 0
        )
        if average_word_length < 3:
            issues.append("Very short average word length")
            score *= 0.7

        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues,
            "metrics": {
                "character_count": total_chars,
                "word_count": total_words,
                "keyword_coverage": keyword_coverage,
                "average_word_length": average_word_length,
                "single_char_ratio": single_char_words / total_words if words else 0,
            },
        }
