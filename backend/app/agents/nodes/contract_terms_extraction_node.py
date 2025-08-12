"""
Contract Terms Extraction Node for Contract Analysis Workflow

This module contains the node responsible for extracting contract terms from processed documents.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState, ContractTerms
from .base import BaseNode

logger = logging.getLogger(__name__)


class ContractTermsExtractionNode(BaseNode):
    """
    Node responsible for extracting contract terms from processed documents.

    This node handles:
    - Contract terms extraction using LLM or rule-based methods
    - Confidence scoring for extracted terms
    - Fallback mechanisms for extraction failures
    - Structured parsing and validation of extracted data
    """

    def __init__(self, workflow):
        super().__init__(workflow, "contract_terms_extraction")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Extract contract terms from the processed document.

        Args:
            state: Current workflow state containing processed document

        Returns:
            Updated state with extracted contract terms
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        # Initialize variables used in error context before try to avoid UnboundLocalError
        extraction_method = self.extraction_config.get("method", "llm_structured")
        use_llm = self.use_llm_config.get("contract_analysis", True)

        try:
            self._log_step_debug("Starting contract terms extraction", state)

            # Get document data
            document_metadata = state.get("document_metadata", {})
            full_text = document_metadata.get("full_text", "")

            if not full_text:
                error_msg = "No text available for contract terms extraction"
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    error_msg,
                    {"document_metadata_keys": list(document_metadata.keys())},
                )

            # Extract terms using configured method

            if use_llm and extraction_method == "llm_structured":
                try:
                    contract_terms = await self._extract_terms_llm(full_text, state)
                    extraction_source = "llm_structured"
                except Exception as llm_error:
                    self._log_exception(
                        llm_error, state, {"fallback_enabled": self.enable_fallbacks}
                    )

                    if self.enable_fallbacks and self.extraction_config.get(
                        "fallback_to_rule_based", True
                    ):
                        contract_terms = await self._extract_terms_rule_based(
                            full_text, state
                        )
                        extraction_source = "rule_based_fallback"
                    else:
                        raise llm_error
            else:
                contract_terms = await self._extract_terms_rule_based(full_text, state)
                extraction_source = "rule_based"

            # Validate extraction results
            if not contract_terms or not isinstance(contract_terms, dict):
                return self._handle_node_error(
                    state,
                    Exception("Empty or invalid terms extraction result"),
                    "Contract terms extraction produced no valid results",
                    {"extraction_method": extraction_source},
                )

            # Calculate confidence score
            confidence_score = self._calculate_extraction_confidence(
                contract_terms, full_text
            )

            # Check confidence threshold
            confidence_threshold = self.extraction_config.get(
                "confidence_threshold", 0.3
            )
            if confidence_score < confidence_threshold:
                self._log_step_debug(
                    f"Low extraction confidence: {confidence_score:.2f} < {confidence_threshold}",
                    state,
                    {"extraction_method": extraction_source},
                )

            # Update state with extracted terms
            state["contract_terms"] = contract_terms
            state["confidence_scores"]["contract_extraction"] = confidence_score

            extraction_data = {
                "contract_terms": contract_terms,
                "extraction_method": extraction_source,
                "confidence_score": confidence_score,
                "terms_count": len(contract_terms),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Contract terms extracted successfully: {len(contract_terms)} terms (confidence: {confidence_score:.2f})",
                state,
                {"extraction_method": extraction_source},
            )

            return self.update_state_step(
                state, "contract_terms_extracted", data=extraction_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Contract terms extraction failed: {str(e)}",
                {"use_llm": use_llm, "extraction_method": extraction_method},
            )

    async def _extract_terms_llm(
        self, text: str, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Extract contract terms using LLM with structured prompts."""
        try:
            from app.core.prompts import PromptContext, ContextType

            # Get document metadata for context
            document_metadata = state.get("document_metadata", {})

            context = PromptContext(
                context_type=ContextType.EXTRACTION,
                variables={
                    "extracted_text": text[:8000],  # Limit for LLM processing
                    "document_metadata": document_metadata,
                    "extraction_type": "contract_terms",
                    "contract_type": "property_contract",
                    "user_type": "general",
                    "user_experience_level": "intermediate",
                    "extraction_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use fragment-based prompts if enabled
            if self.extraction_config.get("use_fragments", True):
                rendered_prompt = await self.prompt_manager.render(
                    template_name="extraction/contract_terms_structured",
                    context=context,
                    service_name="contract_analysis_workflow",
                )
            else:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="extraction/contract_terms_basic",
                    context=context,
                    service_name="contract_analysis_workflow",
                )

            # Generate response with retries
            max_retries = self.extraction_config.get("max_retries", 2)

            for attempt in range(max_retries + 1):
                try:
                    response = await self._generate_content_with_fallback(
                        rendered_prompt, use_gemini_fallback=True
                    )

                    # Parse structured response
                    if self.structured_parsers.get("contract_terms"):
                        parsing_result = self.structured_parsers[
                            "contract_terms"
                        ].parse(response)
                        if parsing_result.success and parsing_result.data:
                            return parsing_result.data

                    # Fallback to JSON parsing
                    contract_terms = self._safe_json_parse(response)
                    if contract_terms:
                        return contract_terms

                    if attempt < max_retries:
                        self._log_step_debug(
                            f"LLM extraction attempt {attempt + 1} failed, retrying",
                            state,
                        )
                        continue
                    else:
                        raise Exception(
                            "Failed to parse LLM response after all retries"
                        )

                except Exception as parse_error:
                    if attempt < max_retries:
                        self._log_step_debug(
                            f"Parse error on attempt {attempt + 1}: {parse_error}",
                            state,
                        )
                        continue
                    else:
                        raise parse_error

        except Exception as e:
            self._log_exception(e, state, {"extraction_method": "llm"})
            if not self.enable_fallbacks:
                raise
            # Will fallback to rule-based extraction
            raise e

    async def _extract_terms_rule_based(
        self, text: str, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Extract contract terms using rule-based methods."""
        try:
            from app.agents.tools.domain import extract_australian_contract_terms

            # Use domain-specific extraction tool
            extraction_result = extract_australian_contract_terms.invoke(
                {"contract_text": text, "extraction_config": self.extraction_config}
            )

            if isinstance(extraction_result, dict):
                return extraction_result
            else:
                # Handle case where tool returns non-dict result
                return {
                    "extraction_method": "rule_based",
                    "raw_result": extraction_result,
                    "confidence": 0.6,
                }

        except Exception as e:
            self._log_exception(e, state, {"extraction_method": "rule_based"})
            # Return minimal terms structure
            return {
                "purchase_price": None,
                "settlement_date": None,
                "deposit_amount": None,
                "cooling_off_period": None,
                "property_address": None,
                "vendor_details": {},
                "purchaser_details": {},
                "special_conditions": [],
                "extraction_method": "rule_based_minimal",
                "confidence": 0.3,
                "error": str(e),
            }

    def _calculate_extraction_confidence(
        self, contract_terms: Dict[str, Any], full_text: str
    ) -> float:
        """Calculate confidence score for extracted contract terms."""
        try:
            # Base confidence from extraction method
            base_confidence = contract_terms.get("confidence", 0.5)

            # Key fields presence scoring
            key_fields = [
                "purchase_price",
                "settlement_date",
                "deposit_amount",
                "property_address",
                "vendor_details",
                "purchaser_details",
            ]

            present_fields = sum(1 for field in key_fields if contract_terms.get(field))
            completeness_score = present_fields / len(key_fields)

            # Text coverage scoring (how much of the text was utilized)
            extracted_values = []
            for key, value in contract_terms.items():
                if isinstance(value, str) and value:
                    extracted_values.append(value.lower())
                elif isinstance(value, dict):
                    for sub_value in value.values():
                        if isinstance(sub_value, str) and sub_value:
                            extracted_values.append(sub_value.lower())

            # Check if extracted values appear in original text
            text_lower = full_text.lower()
            verified_values = sum(
                1 for value in extracted_values if value in text_lower
            )
            verification_score = (
                verified_values / len(extracted_values) if extracted_values else 0.5
            )

            # Combined confidence score
            final_confidence = (
                base_confidence * 0.4
                + completeness_score * 0.4
                + verification_score * 0.2
            )

            return max(0.0, min(1.0, final_confidence))

        except Exception as e:
            self._log_exception(
                e, context={"calculation_method": "extraction_confidence"}
            )
            return 0.5
