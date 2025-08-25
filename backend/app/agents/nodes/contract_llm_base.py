"""
ContractLLMNode: LLMNode specialization for contract-backed nodes.

Parameters:
- contract_attribute: the JSONB column on `contracts` to check/persist (e.g., 'extracted_entity')
- state_field: the workflow state key to set on success/short-circuit (e.g., 'entities_extraction')

Subclasses can override `_build_updated_fields(parsed, state)` to supply additional
repository fields (e.g., contract_type, property_address) while the base class
handles short-circuiting and state updates generically.
"""

import logging
from typing import Any, Dict, Optional

from app.models.contract_state import RealEstateAgentState
from .llm_base import LLMNode

logger = logging.getLogger(__name__)


class ContractLLMNode(LLMNode):
    def __init__(
        self,
        workflow,
        node_name: str,
        *,
        contract_attribute: str,
        state_field: str,
    ):
        super().__init__(workflow, node_name)
        self.contract_attribute = contract_attribute
        self.state_field = state_field

    async def _short_circuit_check(
        self, state: RealEstateAgentState
    ) -> Optional[RealEstateAgentState]:
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
                state[self.state_field] = cached_value
                try:
                    metadata = cached_value.get("metadata", {})
                    overall_confidence = metadata.get("overall_confidence")
                    if overall_confidence is not None:
                        state.setdefault("confidence_scores", {})[
                            self.node_name
                        ] = overall_confidence
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

    async def _persist_results(self, state: RealEstateAgentState, parsed: Any) -> None:
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
            if not content_hash:
                logger.warning(
                    f"{self.__class__.__name__}: Missing content_hash; skipping contract upsert"
                )
                return

            updated_fields = self._build_updated_fields(parsed, state) or {}
            updated_fields.setdefault("updated_by", self.node_name)

            contracts_repo = ContractsRepository()
            await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                **updated_fields,
            )
        except Exception as repo_err:
            logger.warning(
                f"{self.__class__.__name__}: Contract upsert failed (non-fatal): {repo_err}"
            )

    def _build_updated_fields(
        self, parsed: Any, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        try:
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        except Exception:
            value = None
        return {self.contract_attribute: value}

    async def _update_state_success(
        self, state: RealEstateAgentState, parsed: Any, quality: Dict[str, Any]
    ) -> RealEstateAgentState:
        try:
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        except Exception:
            value = None

        state[self.state_field] = value

        # Try to propagate overall confidence into a stable key for this node
        try:
            metadata = getattr(parsed, "metadata", None)
            overall_conf = getattr(metadata, "overall_confidence", None)
            if overall_conf is not None:
                state.setdefault("confidence_scores", {})[self.node_name] = overall_conf
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
            document_metadata = state.get("document_metadata", {})
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
