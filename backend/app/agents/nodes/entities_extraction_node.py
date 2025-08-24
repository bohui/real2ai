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
from app.schema.enums.property import ContractType
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

            # Idempotency check: if we already have extracted_entity saved for this contract, skip
            try:
                from app.services.repositories.contracts_repository import (
                    ContractsRepository,
                )

                content_hash = (
                    state.get("content_hash")
                    or state.get("content_hmac")
                    or (state.get("document_data", {}) or {}).get("content_hash")
                    or (state.get("document_metadata", {}) or {}).get("content_hash")
                )

                if content_hash:
                    contracts_repo = ContractsRepository()
                    existing_contract = (
                        await contracts_repo.get_contract_by_content_hash(content_hash)
                    )
                    if (
                        existing_contract
                        and isinstance(existing_contract.extracted_entity, dict)
                        and bool(existing_contract.extracted_entity)
                    ):
                        state["entities_extraction_result"] = (
                            existing_contract.extracted_entity
                        )
                        try:
                            metadata = existing_contract.extracted_entity.get(
                                "metadata", {}
                            )
                            overall_confidence = metadata.get("overall_confidence")
                            if overall_confidence is not None:
                                state.setdefault("confidence_scores", {})[
                                    "entities_extraction"
                                ] = overall_confidence
                        except Exception:
                            pass

                        self._log_step_debug(
                            "Skipping entities extraction; using cached extracted_entity",
                            state,
                            {"content_hash": content_hash},
                        )
                        return self.update_state_step(
                            state,
                            "entities_extraction_skipped",
                            data={
                                "reason": "existing_extracted_entity",
                                "source": "contracts_cache",
                            },
                        )
            except Exception as check_err:
                logger.warning(
                    f"EntitiesExtractionNode: Idempotency check failed (non-fatal): {check_err}"
                )

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
            metadata = composition_result.get("metadata", {})
            # Prefer explicitly configured composition model, otherwise derive from template model_compatibility
            model_name = (
                metadata.get("primary_model")
                or metadata.get("model")
                or (metadata.get("model_compatibility", []) or [None])[0]
            )
            fallback_models = list(metadata.get("fallback_models") or [])
            if not fallback_models:
                compat_list = list(metadata.get("model_compatibility") or [])
                fallback_models = [m for m in compat_list if m and m != model_name]

            llm_service = await get_llm_service()
            max_retries = self.extraction_config.get("max_retries", 2)
            min_confidence: float = float(
                self.extraction_config.get("min_confidence", 0.75)
            )

            def _coerce_to_model(data: Any) -> Optional[ContractEntityExtraction]:
                if isinstance(data, ContractEntityExtraction):
                    return data
                if hasattr(data, "model_validate"):
                    try:
                        return ContractEntityExtraction.model_validate(data)
                    except Exception:
                        return None
                return None

            def _evaluate_quality(result: ContractEntityExtraction) -> Dict[str, Any]:
                try:
                    coverage = {
                        "has_parties": bool(result.parties),
                        "has_dates": bool(result.dates),
                        "has_financial_amounts": bool(result.financial_amounts),
                        "has_property_details": bool(result.property_details),
                        "has_legal_references": bool(result.legal_references),
                        "has_conditions": hasattr(result, "conditions")
                        and bool(getattr(result, "conditions", [])),
                    }
                    overall_conf = (
                        result.metadata.overall_confidence
                        if getattr(result, "metadata", None) is not None
                        else None
                    )
                    coverage_score = sum(1 for v in coverage.values() if v) / max(
                        len(coverage), 1
                    )
                    ok = (
                        overall_conf is not None and overall_conf >= min_confidence
                    ) or coverage_score >= 0.7
                    return {
                        "ok": ok,
                        "overall_confidence": overall_conf,
                        "coverage_score": coverage_score,
                        **coverage,
                    }
                except Exception:
                    return {"ok": False}

            parsed_result: Optional[ContractEntityExtraction] = None
            parsed_quality: Dict[str, Any] = {"ok": False}
            if parser is not None:
                # Primary attempt with selected model
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
                    primary_parsed = _coerce_to_model(parsing_result.parsed_data)
                    if primary_parsed is not None:
                        parsed_result = primary_parsed
                        parsed_quality = _evaluate_quality(primary_parsed)

                # Fallback attempts if quality is insufficient
                if not parsed_quality.get("ok", False) and fallback_models:
                    try:
                        self._log_warning(
                            "Entities extraction: primary model quality low; evaluating fallbacks",
                            state,
                            {
                                "primary_model": model_name,
                                "fallback_models": fallback_models,
                                "primary_quality": parsed_quality,
                            },
                        )

                        def _score(q: Dict[str, Any]) -> float:
                            conf = q.get("overall_confidence")
                            cov = q.get("coverage_score", 0.0)
                            return (
                                conf if isinstance(conf, (int, float)) else 0.0
                            ) * 0.7 + cov * 0.3

                        best_result = parsed_result
                        best_quality = parsed_quality

                        for fb_model in fallback_models:
                            try:
                                fb_result = await llm_service.generate_content(
                                    prompt=rendered_prompt,
                                    system_message=system_prompt,
                                    model=fb_model,
                                    output_parser=parser,
                                    parse_generation_max_attempts=max_retries,
                                )
                                if (
                                    getattr(fb_result, "success", False)
                                    and getattr(fb_result, "parsed_data", None)
                                    is not None
                                ):
                                    fb_parsed = _coerce_to_model(fb_result.parsed_data)
                                    if fb_parsed is not None:
                                        fb_quality = _evaluate_quality(fb_parsed)
                                        if _score(fb_quality) > _score(best_quality):
                                            best_result = fb_parsed
                                            best_quality = fb_quality
                            except Exception as inner_fb_err:
                                logger.warning(
                                    f"EntitiesExtractionNode: fallback model '{fb_model}' attempt failed: {inner_fb_err}"
                                )

                        parsed_result = best_result
                        parsed_quality = best_quality
                    except Exception as fb_err:
                        logger.warning(
                            f"EntitiesExtractionNode: evaluating fallback models failed: {fb_err}"
                        )

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
                        contract_type=_to_str(
                            getattr(metadata, "contract_type", ContractType.UNKNOWN)
                        ),
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
