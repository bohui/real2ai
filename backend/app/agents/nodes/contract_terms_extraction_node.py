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
                # read from document repository
                try:
                    # Get document ID from document_data
                    document_data = state.get("document_data", {})
                    document_id = document_data.get("document_id")

                    if not document_id:
                        error_msg = "No document_id available to read from repository"
                        self._log_step_debug(error_msg, state)
                        return self._handle_node_error(
                            state,
                            Exception(error_msg),
                            "Cannot read document from repository - missing document_id",
                            {"document_data_keys": list(document_data.keys())},
                        )

                    # Import repositories and storage service
                    from app.services.repositories.documents_repository import (
                        DocumentsRepository,
                    )
                    from app.services.repositories.artifacts_repository import (
                        ArtifactsRepository,
                    )
                    from app.utils.storage_utils import ArtifactStorageService
                    from app.core.auth_context import AuthContext

                    # Get user ID for repository access
                    user_id = AuthContext.get_user_id()
                    if not user_id:
                        # Fallback to state user_id if available
                        user_id = state.get("user_id")
                        if not user_id:
                            error_msg = "No user_id available for repository access"
                            return self._handle_node_error(
                                state,
                                Exception(error_msg),
                                "Cannot access document repository - missing user_id",
                                {"document_id": document_id},
                            )

                    # Get document from repository
                    documents_repo = DocumentsRepository(user_id=user_id)
                    document = await documents_repo.get_document(document_id)

                    if not document:
                        error_msg = f"Document not found in repository: {document_id}"
                        return self._handle_node_error(
                            state,
                            Exception(error_msg),
                            "Document not found in repository",
                            {"document_id": document_id, "user_id": user_id},
                        )

                    # Check if document has artifact_text_id
                    if not document.artifact_text_id:
                        error_msg = "Document has no associated text artifact"
                        return self._handle_node_error(
                            state,
                            Exception(error_msg),
                            "Document has no text artifact for reading",
                            {
                                "document_id": document_id,
                                "processing_status": document.processing_status,
                                "artifact_text_id": document.artifact_text_id,
                            },
                        )

                    # Get full text artifact using the artifact_text_id
                    artifacts_repo = ArtifactsRepository()
                    full_text_artifact = (
                        await artifacts_repo.get_full_text_artifact_by_id(
                            document.artifact_text_id
                        )
                    )

                    if not full_text_artifact:
                        error_msg = (
                            f"Full text artifact not found: {document.artifact_text_id}"
                        )
                        return self._handle_node_error(
                            state,
                            Exception(error_msg),
                            "Full text artifact not found in repository",
                            {
                                "document_id": document_id,
                                "artifact_text_id": document.artifact_text_id,
                            },
                        )

                    # Download the full text content from storage
                    storage_service = ArtifactStorageService()
                    try:
                        full_text = await storage_service.download_text_blob(
                            full_text_artifact.full_text_uri
                        )
                        self._log_step_debug(
                            "Successfully retrieved text from artifact storage",
                            state,
                            {
                                "document_id": document_id,
                                "artifact_id": str(document.artifact_text_id),
                                "text_length": len(full_text),
                                "total_pages": full_text_artifact.total_pages,
                                "total_words": full_text_artifact.total_words,
                            },
                        )
                    except Exception as storage_error:
                        error_msg = f"Failed to download text from artifact storage: {storage_error}"
                        return self._handle_node_error(
                            state,
                            Exception(error_msg),
                            "Failed to download text content from artifact storage",
                            {
                                "document_id": document_id,
                                "artifact_id": str(document.artifact_text_id),
                                "artifact_uri": full_text_artifact.full_text_uri,
                                "storage_error": str(storage_error),
                            },
                        )

                except Exception as repo_error:
                    self._log_exception(
                        repo_error,
                        state,
                        {
                            "operation": "document_repository_read",
                            "document_id": document_id,
                        },
                    )
                    # Continue with empty text - will be handled by existing error logic
                    full_text = ""

            # Enhanced diagnostics for empty document
            # diagnostic_info = {
            #     "document_metadata_keys": (
            #         list(document_metadata.keys()) if document_metadata else []
            #     ),
            #     "document_metadata_type": str(type(document_metadata)),
            #     "document_data_keys": (
            #         list(state.get("document_data", {}).keys())
            #         if state.get("document_data")
            #         else []
            #     ),
            #     "parsing_status": str(state.get("parsing_status", "unknown")),
            #     "document_processing_complete": "document_metadata" in state
            #     and isinstance(state.get("document_metadata"), dict),
            # }

            # error_msg = "No text available for contract terms extraction - document processing may have failed"

            # # Log detailed diagnostic information for debugging
            # # Use getattr for defensive access in case method is missing
            # log_warning = getattr(self, "_log_warning", None)
            # if log_warning:
            #     log_warning(
            #         f"Contract terms extraction failed: empty document",
            #         extra=diagnostic_info,
            #     )
            # else:
            #     logger.warning(
            #         f"Contract terms extraction failed: empty document",
            #         extra=diagnostic_info,
            #     )

            # return self._handle_node_error(
            #     state,
            #     Exception(error_msg),
            #     error_msg,
            #     diagnostic_info,
            # )

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
            # Defensive access for confidence_scores
            state.setdefault("confidence_scores", {})[
                "contract_extraction"
            ] = confidence_score

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
            # Required context for service mapping
            australian_state_value = (
                state.get("australian_state")
                or document_metadata.get("australian_state")
                or "NSW"
            )
            contract_type_value = state.get("contract_type") or "purchase_agreement"
            user_type_value = state.get("user_type") or "general"
            user_experience_level_value = (
                state.get("user_experience_level")
                or state.get("user_experience")
                or "intermediate"
            )

            context = PromptContext(
                context_type=ContextType.EXTRACTION,
                variables={
                    "extracted_text": text[:8000],  # Limit for LLM processing
                    "document_metadata": document_metadata,
                    "extraction_type": "contract_terms",
                    # Service mapping required variables
                    "australian_state": australian_state_value,
                    "contract_type": contract_type_value,
                    "user_type": user_type_value,
                    "user_experience_level": user_experience_level_value,
                    "extraction_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use fragment-based prompts if enabled; ensure we always pass required context defaults
            if self.extraction_config.get("use_fragments", True):
                rendered_prompt = await self.prompt_manager.render(
                    template_name="analysis/contract_structure",
                    context=context,
                    service_name="contract_analysis_workflow",
                )
            else:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="contract_analysis_base",
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

                    # Fallback to JSON parsing with braces recovery
                    contract_terms = self._safe_json_parse(response)
                    if contract_terms:
                        return contract_terms

                    # Attempt to extract JSON substring if the model returned extra text
                    import re

                    json_snippets = re.findall(r"\{[\s\S]*\}", response)
                    for snippet in json_snippets:
                        parsed = self._safe_json_parse(snippet)
                        if parsed:
                            return parsed

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
            # Determine state for extraction if available in workflow state
            australian_state = (
                state.get("australian_state") if isinstance(state, dict) else None
            )

            extraction_result = extract_australian_contract_terms.invoke(
                {"document_text": text, "state": australian_state or ""}
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
