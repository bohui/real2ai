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

            # Prefer processed full_text from document_metadata if present, otherwise fallback to raw document_data
            document_data = state.get("document_data", {}) or {}
            processed_metadata = state.get("document_metadata", {}) or {}

            # Primary text source precedence: processed full_text -> document_data.content -> ""
            document_text = processed_metadata.get("full_text") or document_data.get(
                "content", ""
            )
            # Metadata precedence: processed document_metadata -> document_data.metadata -> {}
            document_metadata = (
                processed_metadata or document_data.get("metadata", {}) or {}
            )

            # Fail-fast for empty documents
            if not document_text or len(document_text.strip()) < 50:
                error_msg = (
                    f"Document too short for analysis: {len(document_text)} characters"
                )
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    error_msg,
                    {"document_length": len(document_text or "")},
                )

            # Perform quality validation
            use_llm = self.use_llm_config.get("document_quality", True)

            if use_llm:
                # Check if clients are available before attempting LLM validation
                if not self.openai_client and not self.gemini_client:
                    logger.warning(
                        "No AI clients available, falling back to rule-based validation"
                    )
                    quality_metrics = await self._validate_document_quality_rule_based(
                        document_text, document_metadata
                    )
                else:
                    try:
                        quality_metrics = (
                            await self._validate_document_quality_with_llm(
                                document_text, document_metadata
                            )
                        )
                    except Exception as llm_error:
                        self._log_exception(
                            llm_error, state, {"fallback_to_rule_based": True}
                        )
                        if self.enable_fallbacks:
                            quality_metrics = (
                                await self._validate_document_quality_rule_based(
                                    document_text, document_metadata
                                )
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
                    {"quality_metrics": quality_metrics},
                )
                return self.update_state_step(
                    state,
                    "document_quality_validated",
                    data={"quality_metrics": quality_metrics},
                )
            else:
                self._log_step_debug(
                    f"Document quality validation failed (score: {confidence_score:.2f})",
                    state,
                    {"quality_metrics": quality_metrics},
                )
                return self.update_state_step(
                    state,
                    "document_quality_validation_failed",
                    error=f"Document quality below threshold (score: {confidence_score:.2f})",
                    data={"quality_metrics": quality_metrics},
                )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Document quality validation failed: {str(e)}",
                {"use_llm": self.use_llm_config.get("document_quality", True)},
            )

    async def _validate_document_quality_with_llm(
        self, text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate document quality using LLM analysis."""
        # Check if clients are available
        if not self.openai_client and not self.gemini_client:
            raise Exception("No AI clients available for LLM validation")

        try:
            from app.core.prompts import PromptContext, ContextType

            # Provide defaults for required context variables expected by templates/service mapping
            australian_state_value = (metadata or {}).get("australian_state") or "NSW"
            document_type_value = (metadata or {}).get("document_type") or "contract"
            extraction_method_value = (metadata or {}).get("extraction_method") or "ocr"
            analysis_timestamp_value = datetime.now(UTC).isoformat()

            # Sanitize metadata to avoid oversized prompts (remove large text blobs)
            def _sanitize_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
                if not isinstance(data, dict):
                    return {}
                drop_keys = {
                    "full_text",
                    "pages",
                    "page_texts",
                    "raw_text",
                    "extracted_text",
                    "content",
                    "original_pages",
                }
                sanitized: Dict[str, Any] = {}
                for key, value in data.items():
                    if key in drop_keys:
                        continue
                    if isinstance(value, str):
                        sanitized[key] = value[:1000] + (
                            "..." if len(value) > 1000 else ""
                        )
                    elif isinstance(value, list):
                        sanitized[key] = value[:50]
                    elif isinstance(value, dict):
                        # Shallow sanitize nested dicts to avoid huge payloads
                        nested: Dict[str, Any] = {}
                        for nk, nv in value.items():
                            if nk in drop_keys:
                                continue
                            if isinstance(nv, str):
                                nested[nk] = nv[:500] + ("..." if len(nv) > 500 else "")
                            # Skip deeply nested large structures
                        if nested:
                            sanitized[key] = nested
                    else:
                        sanitized[key] = value
                return sanitized

            sanitized_metadata = _sanitize_metadata(metadata or {})

            context = PromptContext(
                context_type=ContextType.VALIDATION,
                variables={
                    "document_text": text[:2000],  # Limit for LLM processing
                    "document_metadata": sanitized_metadata,
                    "validation_type": "document_quality",
                    "quality_criteria": [
                        "text_clarity",
                        "content_completeness",
                        "key_terms_presence",
                        "readability",
                    ],
                    # Template-required variables
                    "australian_state": australian_state_value,
                    "document_type": document_type_value,
                    "extraction_method": extraction_method_value,
                    "analysis_timestamp": analysis_timestamp_value,
                    # Service mapping required variables (best-effort defaults)
                    "extracted_text": text[:2000],
                    "contract_type": (metadata or {}).get("contract_type")
                    or "purchase_agreement",
                    "user_type": (metadata or {}).get("user_type") or "general",
                    "user_experience_level": (metadata or {}).get(
                        "user_experience_level"
                    )
                    or "intermediate",
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="validation/document_quality_validation",
                context=context,
                service_name="contract_analysis_workflow",
            )

            response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            # Parse LLM response if we got one
            if response:
                quality_result = self._safe_json_parse(response)
                if quality_result:
                    return quality_result

            # Fallback to rule-based if no response or parsing fails
            logger.info(
                "LLM validation failed or returned no response, falling back to rule-based validation"
            )
            return await self._validate_document_quality_rule_based(text, metadata)

        except Exception as e:
            self._log_exception(e, context={"text_length": len(text)})
            if self.enable_fallbacks:
                logger.info(
                    "LLM validation failed, falling back to rule-based validation"
                )
                return await self._validate_document_quality_rule_based(text, metadata)
            raise

    async def _validate_document_quality_rule_based(
        self, text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate document quality using rule-based analysis."""
        from app.agents.tools.validation import validate_document_quality

        try:
            validation_result = validate_document_quality.invoke(
                {"document_text": text, "document_metadata": metadata}
            )

            # Convert pydantic model to dict safely
            try:
                validation_dict = (
                    validation_result.model_dump()
                    if hasattr(validation_result, "model_dump")
                    else dict(validation_result)
                )
            except Exception:
                # Fallback: best-effort attribute extraction
                validation_dict = {
                    k: getattr(validation_result, k)
                    for k in [
                        "text_quality_score",
                        "completeness_score",
                        "readability_score",
                        "key_terms_coverage",
                        "extraction_confidence",
                        "issues_identified",
                        "improvement_suggestions",
                        "overall_confidence",
                    ]
                    if hasattr(validation_result, k)
                }

            # Enhance with additional metrics
            words = text.split()
            quality_metrics = {
                "text_quality_score": validation_dict.get("text_quality_score", 0.7),
                "completeness_score": validation_dict.get("completeness_score", 0.7),
                "readability_score": validation_dict.get("readability_score", 0.7),
                "key_terms_coverage": validation_dict.get("key_terms_coverage", 0.7),
                "extraction_confidence": validation_dict.get(
                    "extraction_confidence", 0.7
                ),
                "issues_identified": validation_dict.get("issues_identified", []),
                "improvement_suggestions": validation_dict.get(
                    "improvement_suggestions", []
                ),
                "overall_confidence": validation_dict.get("overall_confidence", 0.7),
                "metrics": {
                    "word_count": len(words),
                    "character_count": len(text),
                    "average_word_length": (
                        sum(len(word) for word in words) / len(words) if words else 0
                    ),
                },
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
