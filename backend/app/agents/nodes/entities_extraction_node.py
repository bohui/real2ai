"""
Entities Extraction Node for Contract Analysis Workflow

Runs entity extraction using the contract_entities_extraction prompt
and parses into ContractEntityExtraction.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.models.contract_state import RealEstateAgentState
from app.prompts.schema.entity_extraction_schema import ContractEntityExtraction
from .base import BaseNode

logger = logging.getLogger(__name__)


class EntitiesExtractionNode(BaseNode):
    """
    Performs entity extraction from contracts to identify key information
    such as parties, dates, financial amounts, and property details.
    """

    def __init__(self, workflow):
        super().__init__(workflow, "entities_extraction")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting entities extraction", state)

            # Obtain document text
            document_metadata = state.get("document_metadata", {})
            full_text = document_metadata.get("full_text", "")

            if not full_text:
                try:
                    document_data = state.get("document_data", {})
                    document_id = document_data.get("document_id")
                    if not document_id:
                        return self._handle_node_error(
                            state,
                            Exception(
                                "No document_id available to read from repository"
                            ),
                            "Cannot read document from repository - missing document_id",
                            {"document_data_keys": list(document_data.keys())},
                        )

                    from app.services.repositories.documents_repository import (
                        DocumentsRepository,
                    )
                    from app.services.repositories.artifacts_repository import (
                        ArtifactsRepository,
                    )
                    from app.utils.storage_utils import ArtifactStorageService
                    from app.core.auth_context import AuthContext

                    user_id = AuthContext.get_user_id() or state.get("user_id")
                    if not user_id:
                        return self._handle_node_error(
                            state,
                            Exception("No user_id available for repository access"),
                            "Cannot access document repository - missing user_id",
                            {"document_id": document_id},
                        )

                    documents_repo = DocumentsRepository(user_id=user_id)
                    document = await documents_repo.get_document(document_id)
                    if not document:
                        return self._handle_node_error(
                            state,
                            Exception(
                                f"Document not found in repository: {document_id}"
                            ),
                            "Document not found in repository",
                            {"document_id": document_id, "user_id": user_id},
                        )

                    if not document.artifact_text_id:
                        return self._handle_node_error(
                            state,
                            Exception("Document has no associated text artifact"),
                            "Document has no text artifact for reading",
                            {
                                "document_id": document_id,
                                "processing_status": document.processing_status,
                                "artifact_text_id": document.artifact_text_id,
                            },
                        )

                    artifacts_repo = ArtifactsRepository()
                    full_text_artifact = (
                        await artifacts_repo.get_full_text_artifact_by_id(
                            document.artifact_text_id
                        )
                    )
                    if not full_text_artifact:
                        return self._handle_node_error(
                            state,
                            Exception(
                                f"Full text artifact not found: {document.artifact_text_id}"
                            ),
                            "Full text artifact not found in repository",
                            {
                                "document_id": document_id,
                                "artifact_id": str(document.artifact_text_id),
                            },
                        )

                    storage_service = ArtifactStorageService()
                    full_text = await storage_service.download_text_blob(
                        full_text_artifact.full_text_uri
                    )
                    self._log_step_debug(
                        "Retrieved text for entities extraction",
                        state,
                        {
                            "document_id": document_id,
                            "artifact_id": str(document.artifact_text_id),
                            "text_length": len(full_text),
                            "total_pages": full_text_artifact.total_pages,
                        },
                    )
                except Exception as repo_error:
                    self._log_exception(
                        repo_error,
                        state,
                        {"operation": "document_repository_read_entities_extraction"},
                    )
                    full_text = ""

            from app.core.prompts import PromptContext, ContextType
            from app.services import get_llm_service

            document_metadata = state.get("document_metadata", {})
            state_value = (
                state.get("australian_state")
                and state.get("australian_state").value
                or "NSW"
            )
            contract_type_value = state.get("contract_type") or "purchase_agreement"
            user_type_value = state.get("user_type") or "general"
            user_experience_value = (
                state.get("user_experience_level")
                or state.get("user_experience")
                or "intermediate"
            )

            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "contract_text": full_text,
                    "analysis_type": "entities_extraction",
                    "document_metadata": document_metadata,
                    "contract_type": contract_type_value,
                    "user_type": user_type_value,
                    "user_experience": user_experience_value,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            parser = self.get_parser("entities_extraction")
            composition_result = await self.prompt_manager.render_composed(
                composition_name="contract_entities_extraction",
                context=context,
                output_parser=parser,
            )
            rendered_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")
            model_name = composition_result.get("metadata", {}).get("model")

            llm_service = await get_llm_service()
            max_retries = self.extraction_config.get("max_retries", 2)

            parsed_result: Optional[ContractEntityExtraction] = None
            if parser is not None:
                parsing_result = await llm_service.generate_content(
                    prompt=rendered_prompt,
                    system_message=system_prompt,
                    model=model_name,
                    output_parser=parser,
                    parse_generation_max_attempts=max_retries,
                )
                if (
                    getattr(parsing_result, "success", False)
                    and getattr(parsing_result, "parsed_data", None) is not None
                ):
                    parsed = parsing_result.parsed_data
                    if isinstance(parsed, ContractEntityExtraction):
                        parsed_result = parsed
                    elif hasattr(parsed, "model_validate"):
                        parsed_result = ContractEntityExtraction.model_validate(parsed)

            if parsed_result is None:
                # Fallback: treat as best-effort, not fatal
                self._log_warning(
                    "Entities extraction parsing failed; continuing without extracted entities"
                )
                return self.update_state_step(
                    state,
                    "entities_extraction_skipped",
                    data={"reason": "parse_failed_or_empty"},
                )

            # Persist to contracts table BEFORE mutating state, following mapping rules
            try:
                from app.services.repositories.contracts_repository import (
                    ContractsRepository,
                )

                def _to_str(v: Any) -> Optional[str]:
                    try:
                        if v is None:
                            return None
                        return str(v.value) if hasattr(v, "value") else str(v)
                    except Exception:
                        return None

                # Resolve content_hash
                content_hash = (
                    state.get("content_hash")
                    or state.get("content_hmac")
                    or (state.get("document_data", {}) or {}).get("content_hash")
                    or (state.get("document_metadata", {}) or {}).get("content_hash")
                )

                if content_hash:
                    metadata = parsed_result.metadata
                    property_address = None
                    try:
                        if (
                            parsed_result.property_address
                            and parsed_result.property_address.full_address
                        ):
                            property_address = (
                                parsed_result.property_address.full_address
                            )
                    except Exception:
                        property_address = None

                    contracts_repo = ContractsRepository()
                    await contracts_repo.upsert_contract_by_content_hash(
                        content_hash=content_hash,
                        contract_type=_to_str(getattr(metadata, "contract_type", None))
                        or "unknown",
                        purchase_method=_to_str(
                            getattr(metadata, "purchase_method", None)
                        ),
                        use_category=_to_str(getattr(metadata, "use_category", None)),
                        state=_to_str(getattr(metadata, "state", None)),
                        property_address=property_address,
                        extracted_entity=parsed_result.model_dump(),
                        updated_by=self.node_name,
                    )
                else:
                    logger.warning(
                        "EntitiesExtractionNode: Missing content_hash; skipping contract upsert"
                    )
            except Exception as repo_err:
                logger.warning(
                    f"EntitiesExtractionNode: Contract upsert failed (non-fatal): {repo_err}"
                )

            # Update state with extraction result
            state["entities_extraction_result"] = parsed_result.model_dump()
            if (
                parsed_result.metadata
                and parsed_result.metadata.overall_confidence is not None
            ):
                state.setdefault("confidence_scores", {})[
                    "entities_extraction"
                ] = parsed_result.metadata.overall_confidence

            return self.update_state_step(
                state,
                "entities_extraction_complete",
                data={
                    "overall_confidence": (
                        parsed_result.metadata.overall_confidence
                        if parsed_result.metadata
                        else None
                    ),
                    "has_parties": bool(parsed_result.parties),
                    "has_dates": bool(parsed_result.dates),
                    "has_financial_amounts": bool(parsed_result.financial_amounts),
                    "has_property_details": bool(parsed_result.property_details),
                    "has_legal_references": bool(parsed_result.legal_references),
                },
            )

        except Exception as e:
            self._log_exception(e, state, {"operation": "entities_extraction"})
            return self._handle_node_error(
                state,
                e,
                f"Entities extraction failed: {str(e)}",
                {"composition": "contract_entities_extraction"},
            )
