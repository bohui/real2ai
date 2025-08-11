"""
Document Quality Validation Node for Contract Analysis Workflow

This module contains the node responsible for validating document quality.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class DocumentQualityValidationNode(BaseNode):
    """
    Node responsible for validating the quality of processed documents.

    This node performs comprehensive document quality validation including:
    - Text quality assessment with LLM assistance (optional)
    - Content completeness validation
    - Readability and structure analysis
    - Key terms coverage verification
    """

    def __init__(self, workflow):
        super().__init__(workflow, "document_quality_validation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Validate document quality using enhanced tools with configurable LLM usage.

        Args:
            state: Current workflow state with processed document

        Returns:
            Updated state with quality validation results
        """
        if not self.enable_quality_checks:
            return state

        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting document quality validation", state)

            # Handle case where document_data might be None
            document_data = state.get("document_data", {})
            if not document_data:
                self._log_step_debug("No document data available for quality validation", state)
                # Return state with default quality metrics
                state["document_quality_metrics"] = {
                    "text_quality_score": 0.5,
                    "completeness_score": 0.5,
                    "readability_score": 0.5,
                    "key_terms_coverage": 0.5,
                    "extraction_confidence": 0.5,
                    "issues_identified": ["No document data available"],
                    "improvement_suggestions": ["Verify document was properly uploaded"],
                }
                state["confidence_scores"]["document_quality"] = 0.5
                return self.update_state_step(
                    state,
                    "document_quality_validation_warning",
                    error="No document data available for quality validation",
                )

            document_text = document_data.get("content", "")
            document_metadata = document_data.get("metadata", {})

            # Fail-fast for empty documents
            if not document_text or len(document_text.strip()) < 50:
                error_msg = f"Document too short for analysis: {len(document_text)} characters"
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    error_msg,
                    {"document_length": len(document_text or "")}
                )

            # Perform quality validation
            use_llm = self.use_llm_config.get("document_quality", True)
            
            if use_llm:
                try:
                    quality_metrics = await self._validate_document_quality_with_llm(
                        document_text, document_metadata
                    )
                except Exception as llm_error:
                    self._log_exception(llm_error, state, {"fallback_to_rule_based": True})
                    if self.enable_fallbacks:
                        quality_metrics = await self._validate_document_quality_rule_based(
                            document_text, document_metadata
                        )
                    else:
                        raise llm_error
            else:
                quality_metrics = await self._validate_document_quality_rule_based(
                    document_text, document_metadata
                )

            # Update state with quality metrics
            state["document_quality_metrics"] = quality_metrics
            confidence_score = quality_metrics.get("overall_confidence", 0.5)
            state["confidence_scores"]["document_quality"] = confidence_score

            # Determine if quality is acceptable
            quality_threshold = 0.6
            quality_passed = confidence_score >= quality_threshold

            if quality_passed:
                self._log_step_debug(
                    f"Document quality validation passed (score: {confidence_score:.2f})",
                    state,
                    {"quality_metrics": quality_metrics}
                )
                return self.update_state_step(
                    state, "document_quality_validated", data={"quality_metrics": quality_metrics}
                )
            else:
                self._log_step_debug(
                    f"Document quality validation failed (score: {confidence_score:.2f})",
                    state,
                    {"quality_metrics": quality_metrics}
                )
                return self.update_state_step(
                    state,
                    "document_quality_validation_failed",
                    error=f"Document quality below threshold (score: {confidence_score:.2f})",
                    data={"quality_metrics": quality_metrics}
                )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Document quality validation failed: {str(e)}",
                {"use_llm": self.use_llm_config.get("document_quality", True)}
            )

    async def _validate_document_quality_with_llm(
        self, text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate document quality using LLM analysis."""
        try:
            from app.core.prompts import PromptContext, ContextType

            context = PromptContext(
                context_type=ContextType.VALIDATION,
                variables={
                    "document_text": text[:2000],  # Limit for LLM processing
                    "document_metadata": metadata,
                    "validation_type": "document_quality",
                    "quality_criteria": [
                        "text_clarity",
                        "content_completeness",
                        "key_terms_presence",
                        "readability"
                    ]
                }
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="validation/document_quality",
                context=context,
                service_name="contract_analysis_workflow"
            )

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            # Parse LLM response
            quality_result = self._safe_json_parse(response)
            if quality_result:
                return quality_result

            # Fallback to rule-based if parsing fails
            return await self._validate_document_quality_rule_based(text, metadata)

        except Exception as e:
            self._log_exception(e, context={"text_length": len(text)})
            if self.enable_fallbacks:
                return await self._validate_document_quality_rule_based(text, metadata)
            raise

    async def _validate_document_quality_rule_based(
        self, text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate document quality using rule-based analysis."""
        from app.agents.tools.validation import validate_document_quality

        try:
            validation_result = validate_document_quality.invoke({
                "document_text": text,
                "document_metadata": metadata
            })

            # Enhance with additional metrics
            words = text.split()
            quality_metrics = {
                "text_quality_score": validation_result.get("text_quality_score", 0.7),
                "completeness_score": validation_result.get("completeness_score", 0.7),
                "readability_score": validation_result.get("readability_score", 0.7),
                "key_terms_coverage": validation_result.get("key_terms_coverage", 0.7),
                "extraction_confidence": validation_result.get("extraction_confidence", 0.7),
                "issues_identified": validation_result.get("issues_identified", []),
                "improvement_suggestions": validation_result.get("improvement_suggestions", []),
                "overall_confidence": validation_result.get("overall_confidence", 0.7),
                "metrics": {
                    "word_count": len(words),
                    "character_count": len(text),
                    "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
                }
            }

            return quality_metrics

        except Exception as e:
            self._log_exception(e, context={"validation_method": "rule_based"})
            # Return minimal quality metrics
            return {
                "text_quality_score": 0.5,
                "completeness_score": 0.5,
                "readability_score": 0.5,
                "key_terms_coverage": 0.5,
                "extraction_confidence": 0.5,
                "issues_identified": ["Quality validation failed"],
                "improvement_suggestions": ["Manual review recommended"],
                "overall_confidence": 0.5,
            }