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
from .base import BaseNode

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

            # Use the new document processing subflow via Celery task
            use_llm = self.use_llm_config.get("document_processing", True)
            
            # Import the task here to avoid circular imports
            from app.tasks.user_aware_tasks import run_document_processing_subflow
            from app.core.auth_context import AuthContext
            
            # Get current user ID for task context
            user_id = AuthContext.get_user_id()
            if not user_id:
                return self._handle_node_error(
                    state,
                    ValueError("User authentication required"),
                    "User authentication context required for document processing",
                    {"document_id": document_id, "use_llm": use_llm}
                )

            # Launch document processing subflow task
            task_result = run_document_processing_subflow.apply_async(
                args=[document_id, user_id, use_llm],
                kwargs={}
            )
            
            # Wait for task completion (with timeout)
            try:
                result = task_result.get(timeout=300)  # 5 minute timeout
                summary = result.get("result")
            except Exception as task_error:
                return self._handle_node_error(
                    state,
                    task_error,
                    f"Document processing task failed: {str(task_error)}",
                    {
                        "document_id": document_id,
                        "task_id": task_result.id,
                        "use_llm": use_llm,
                        "operation": "subflow_task"
                    }
                )

            if not summary or not summary.get("success"):
                error_msg = (
                    summary.get("error")
                    if isinstance(summary, dict)
                    else "Processing failed"
                )
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    "Document processing failed",
                    {"document_id": document_id, "use_llm": use_llm}
                )

            # Extract text and metadata
            extracted_text = summary.get("full_text") or summary.get("extracted_text", "")
            extraction_method = summary.get("extraction_method", "unknown")
            extraction_confidence = summary.get("extraction_confidence", 0.0)

            # Assess text quality
            text_quality = self._assess_text_quality(extracted_text) if self.enable_quality_checks else {"score": 0.8, "issues": []}

            # Validate extracted text quality
            if not extracted_text or len(extracted_text.strip()) < 100:
                return self._handle_node_error(
                    state,
                    Exception("Insufficient text content"),
                    "Insufficient text content extracted from document",
                    {"character_count": len(extracted_text or "")}
                )

            # Update confidence scores
            if "confidence_scores" not in state:
                state["confidence_scores"] = {}
            state["confidence_scores"]["document_processing"] = (
                extraction_confidence * text_quality["score"]
            )

            # Update state with processed data
            updated_data = {
                "document_metadata": {
                    "full_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "text_quality": text_quality,
                    "character_count": len(extracted_text),
                    "total_word_count": len(extracted_text.split()),
                    "processing_timestamp": summary.get(
                        "processing_timestamp", datetime.now(UTC).isoformat()
                    ),
                    "enhanced_processing": True,
                    "llm_used": summary.get("llm_used", False),
                },
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            self._log_step_debug(
                f"Document processing completed: {len(extracted_text)} chars extracted (LLM: {use_llm})",
                state,
                {"extraction_method": extraction_method, "confidence": extraction_confidence}
            )

            return self.update_state_step(state, "document_processed", data=updated_data)

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Document processing failed: {str(e)}",
                {"use_llm": self.use_llm_config.get("document_processing", True)}
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
            "contract", "agreement", "purchase", "sale", "property", "vendor", 
            "purchaser", "settlement", "deposit", "conditions", "title", "transfer"
        ]
        
        keyword_matches = sum(1 for keyword in contract_keywords if keyword.lower() in text.lower())
        keyword_coverage = keyword_matches / len(contract_keywords)
        
        if keyword_coverage < 0.2:
            issues.append("Low contract keyword coverage")
            score *= 0.8

        # Additional quality checks
        average_word_length = sum(len(word) for word in words) / total_words if words else 0
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
            }
        }