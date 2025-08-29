"""
ContractLLMNode: LLMNode specialization for contract-backed nodes.

Parameters:
- contract_attribute: the JSONB column on `contracts` to check/persist (e.g., 'extracted_entity')

Subclasses can override `_build_updated_fields(parsed, state)` to supply additional
repository fields (e.g., contract_type, property_address) while the base class
handles short-circuiting and state updates generically.
"""

import logging
from typing import Any, Dict, Optional

from app.agents.states.contract_state import RealEstateAgentState
from .llm_base import LLMNode

logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE = 0.5


class ContractLLMNode(LLMNode):
    def __init__(
        self,
        workflow,
        node_name: str,
        *,
        contract_attribute: str,
        result_model: Any,
        state_attribute: Optional[str] = None,
        progress_range: tuple[int, int] = (0, 100),
    ):
        super().__init__(workflow, node_name, progress_range)
        self.contract_attribute = contract_attribute
        self.result_model = result_model
        self.min_confidence = DEFAULT_MIN_CONFIDENCE
        # Allow state field name to differ from DB contract column
        self.state_attribute = state_attribute or contract_attribute

    async def _short_circuit_check(
        self, state: RealEstateAgentState
    ) -> Optional[RealEstateAgentState]:
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")

            if not content_hash:
                return None

            contracts_repo = ContractsRepository()
            existing_contract = await contracts_repo.get_contract_by_content_hash(
                content_hash
            )
            if not existing_contract:
                return None

            cached_value = getattr(existing_contract, self.contract_attribute, None)
            if isinstance(cached_value, dict) and bool(cached_value):
                state[self.state_attribute] = cached_value
                try:
                    confidence_score = cached_value.get("confidence_score")
                    if confidence_score is not None:
                        state.setdefault("confidence_scores", {})[
                            self.state_attribute
                        ] = confidence_score
                except Exception:
                    pass

                self._log_step_debug(
                    f"Skipping {self.node_name}; using cached {self.contract_attribute}",
                    state,
                    {"content_hash": content_hash},
                )
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={
                        "reason": "existing_cached_value",
                        "source": "contracts_cache",
                        "contract_attribute": self.contract_attribute,
                    },
                )
        except Exception as check_err:
            logger.warning(
                f"{self.__class__.__name__}: Idempotency check failed (non-fatal): {check_err}"
            )
        return None

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            if isinstance(data, self.result_model):
                return data
            if hasattr(data, "model_validate"):
                return self.result_model.model_validate(data)
        except Exception:
            return None
        return None

    async def _persist_results(self, state: RealEstateAgentState, parsed: Any) -> None:
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")
            if not content_hash:
                logger.warning(
                    f"{self.__class__.__name__}: Missing content_hash; skipping contract persist"
                )
                return

            # Always use single-column section updater with the node's contract_attribute
            value = (
                parsed.model_dump(mode="json")
                if hasattr(parsed, "model_dump")
                else parsed
            )
            repo = ContractsRepository()
            await repo.update_section_analysis_key(
                content_hash,
                self.contract_attribute,
                value,
                updated_by=self.node_name,
            )
        except Exception as repo_err:
            logger.warning(
                f"{self.__class__.__name__}: Section persist failed (non-fatal): [{type(repo_err).__name__}] {repo_err}"
            )

    def _evaluate_quality(
        self, result: Optional[Any], state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Generic quality evaluation for contract-backed nodes using confidence_score."""
        if result is None:
            return {"ok": False, "reason": "no_result"}

        try:
            # Check if result has confidence_score field
            confidence_score = getattr(result, "confidence_score", 0.0)

            # Use workflow-defined minimum confidence threshold
            min_confidence = float(
                self.CONFIG_KEYS.get("min_confidence", self.min_confidence)
            )

            if confidence_score < min_confidence:
                return {
                    "ok": False,
                    "reason": "low_confidence",
                    "confidence_score": confidence_score,
                    "threshold": min_confidence,
                }

            # Basic validation - ensure some meaningful content exists
            has_content = self._validate_content(result)

            if not has_content:
                return {"ok": False, "reason": "no_meaningful_content"}

            return {
                "ok": True,
                "confidence_score": confidence_score,
                "content_validated": True,
            }

        except Exception as e:
            return {"ok": False, "reason": "evaluation_error", "error": str(e)}

    def _validate_content(self, result: Any) -> bool:
        """Validate that the result contains meaningful content. Override in subclasses if needed."""
        try:
            if hasattr(result, "model_dump"):
                data = result.model_dump()
            else:
                data = result

            if not isinstance(data, dict):
                return False

            # Basic check for non-empty content - adjust this logic per contract_attribute if needed
            # This is a generic check that looks for any non-empty lists or non-null strings
            for key, value in data.items():
                if key in [
                    "confidence_score",
                    "analysis_timestamp",
                    "analyzer_version",
                ]:
                    continue  # Skip metadata fields

                if isinstance(value, list) and len(value) > 0:
                    return True
                elif isinstance(value, str) and len(value.strip()) > 0:
                    return True
                elif isinstance(value, dict) and len(value) > 0:
                    return True

            return False

        except Exception:
            return False

    def _build_updated_fields(
        self, parsed: Any, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        try:
            value = (
                parsed.model_dump(mode="json")
                if hasattr(parsed, "model_dump")
                else parsed
            )
        except Exception:
            value = None
        return {self.state_attribute: value}

    async def _update_state_success(
        self, state: RealEstateAgentState, parsed: Any, quality: Dict[str, Any]
    ) -> RealEstateAgentState:
        try:
            value = (
                parsed.model_dump(mode="json")
                if hasattr(parsed, "model_dump")
                else parsed
            )
        except Exception:
            value = None

        state[self.state_attribute] = value

        # Try to propagate confidence score into a stable key for this contract attribute
        try:
            confidence_score = getattr(parsed, "confidence_score", None)
            if confidence_score is not None:
                state.setdefault("confidence_scores", {})[
                    self.state_attribute
                ] = confidence_score
        except Exception:
            pass

        return self.update_state_step(
            state,
            f"{self.node_name}_complete",
            data={
                "quality": quality,
            },
        )

    async def get_full_text(self, state: RealEstateAgentState) -> str:
        """Retrieve full text for the current document from state or repository.

        Returns empty string on failure; logs details for diagnostics.
        """
        try:
            document_metadata = state.get("ocr_processing", {})
            full_text = document_metadata.get("full_text", "")
        except Exception:
            document_metadata = {}
            full_text = ""

        if full_text:
            return full_text

        try:
            document_data = state.get("document_data", {})
            document_id = document_data.get("document_id")
            if not document_id:
                raise Exception("No document_id available to read from repository")

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
                raise Exception("No user_id available for repository access")

            documents_repo = DocumentsRepository(user_id=user_id)
            document = await documents_repo.get_document(document_id)
            if not document:
                raise Exception(f"Document not found in repository: {document_id}")

            if not document.artifact_text_id:
                raise Exception("Document has no associated text artifact")

            artifacts_repo = ArtifactsRepository()
            full_text_artifact = await artifacts_repo.get_full_text_artifact_by_id(
                document.artifact_text_id
            )
            if not full_text_artifact:
                raise Exception(
                    f"Full text artifact not found: {document.artifact_text_id}"
                )

            storage_service = ArtifactStorageService()
            full_text = await storage_service.download_text_blob(
                full_text_artifact.full_text_uri
            )
            self._log_step_debug(
                "Retrieved text for contract processing",
                state,
                {
                    "document_id": document_id,
                    "artifact_id": str(document.artifact_text_id),
                    "text_length": len(full_text),
                    "total_pages": getattr(full_text_artifact, "total_pages", None),
                },
            )
            return full_text
        except Exception as repo_error:
            self._log_exception(
                repo_error,
                state,
                {"operation": f"{self.node_name}_document_repository_read"},
            )
            return ""
