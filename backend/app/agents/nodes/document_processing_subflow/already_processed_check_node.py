"""
AlreadyProcessedCheckNode - Short-circuit if document already processed

This node checks if the document has already been processed by calling the
get_processed_document_summary function. If a summary exists, it populates
the processed_summary field to enable short-circuiting.
"""

from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.schema.document import ProcessedDocumentSummary
from .base_node import DocumentProcessingNodeBase


class AlreadyProcessedCheckNode(DocumentProcessingNodeBase):
    """
    Node responsible for checking if document is already processed.

    This node:
    1. Calls DocumentService.get_processed_document_summary()
    2. If summary exists, populates processed_summary to short-circuit workflow
    3. If not processed, allows workflow to continue

    State Updates:
    - processed_summary: ProcessedDocumentSummary if already processed
    """

    # Inherit constructor from DocumentProcessingNodeBase

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Check if document is already processed.

        Args:
            state: Current processing state with document_id

        Returns:
            Updated state with processed_summary (if already processed) or continuation signal
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            document_id = state.get("document_id")
            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "already_processed_check"},
                )

            self._log_info(f"Checking if document {document_id} is already processed")

            # Get user-authenticated client
            user_client = await self.get_user_client()

            # Check if document is already processed by looking at database
            summary = await self._get_processed_document_summary(
                user_client, document_id
            )

            updated_state = state.copy()

            if summary:
                # Document is already processed, populate summary for short-circuit
                updated_state["processed_summary"] = summary

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)

                self._log_info(
                    f"Document {document_id} is already processed, short-circuiting workflow",
                    extra={
                        "document_id": document_id,
                        "summary_exists": True,
                        "full_text_length": (
                            len(summary.full_text) if summary.full_text else 0
                        ),
                        "total_pages": summary.total_pages,
                        "extraction_method": summary.extraction_method,
                        "processing_timestamp": summary.processing_timestamp,
                        "duration_seconds": duration,
                    },
                )
            else:
                # Document needs processing
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)

                self._log_info(
                    f"Document {document_id} needs processing",
                    extra={
                        "document_id": document_id,
                        "summary_exists": False,
                        "duration_seconds": duration,
                    },
                )

            return updated_state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to check if document is already processed: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "get_processed_document_summary",
                },
            )

    async def _get_processed_document_summary(self, user_client, document_id: str):
        """
        Get processed document summary from database.

        Migrated from DocumentService.get_processed_document_summary.

        Args:
            user_client: Authenticated user client
            document_id: Document ID to check

        Returns:
            ProcessedDocumentSummary if processed, None otherwise
        """
        try:
            # Get document record using repository
            from app.services.repositories.documents_repository import (
                DocumentsRepository,
            )
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )
            from uuid import UUID

            docs_repo = DocumentsRepository()
            document_obj = await docs_repo.get_document(UUID(document_id))

            if not document_obj:
                return None

            # Convert to dict for backward compatibility
            document = {
                "id": str(document_obj.id),
                "australian_state": getattr(document_obj, "australian_state", None),
                "total_pages": getattr(document_obj, "total_pages", None),
                "total_word_count": getattr(document_obj, "total_word_count", None),
                "extraction_confidence": getattr(
                    document_obj, "extraction_confidence", None
                ),
                "processing_timestamp": getattr(
                    document_obj, "processing_timestamp", None
                ),
                "text_extraction_method": getattr(
                    document_obj, "text_extraction_method", None
                ),
                "processing_status": document_obj.processing_status,
                "original_filename": document_obj.original_filename,
                "file_type": document_obj.file_type,
                "storage_path": document_obj.storage_path,
                "content_hash": document_obj.content_hash,
                "artifact_text_id": getattr(document_obj, "artifact_text_id", None),
            }

            # Check if document has been processed
            from app.models.supabase_models import DocumentStatus

            processing_status = document.get("processing_status")
            if processing_status not in [
                DocumentStatus.BASIC_COMPLETE,
                DocumentStatus.ANALYSIS_COMPLETE,
            ]:
                return None

            # Check for artifacts presence using repositories
            from app.services.repositories.artifacts_repository import (
                ArtifactsRepository,
            )

            artifacts_repo = ArtifactsRepository()

            # Check if there are page artifacts or diagram artifacts
            content_hash = document.get("content_hash")
            if not content_hash:
                return None

            # Compute content_hmac by downloading and hashing file content
            storage_path = document.get("storage_path")
            if not storage_path:
                return None

            try:
                # Download file content from storage to compute proper content_hmac
                file_content = await user_client.download_file(
                    bucket="documents", path=storage_path
                )
                if not isinstance(file_content, (bytes, bytearray)):
                    # Some clients may return str; convert to bytes
                    file_content = (
                        bytes(file_content, "utf-8")
                        if isinstance(file_content, str)
                        else bytes(file_content)
                    )

                # Compute SHA256 hash of file content
                import hashlib

                content_hmac = hashlib.sha256(file_content).hexdigest()

                # Verify it matches stored content_hash (optional validation)
                if content_hmac != content_hash:
                    self._log_warning(
                        f"Content hash mismatch: computed={content_hmac[:12]}..., stored={content_hash[:12]}... for document {document_id}"
                    )
                    # Continue with computed hash for artifact queries

            except Exception as e:
                self._log_warning(
                    f"Failed to download file content for hash computation: {e}"
                )
                # Fallback to stored content_hash if download fails
                content_hmac = content_hash

            # Query for page artifacts (text content)
            page_artifacts = await artifacts_repo.get_page_artifacts_by_content_hmac(
                content_hmac
            )
            # Query for diagram artifacts
            diagram_artifacts = (
                await artifacts_repo.get_diagram_artifacts_by_content_hmac(content_hmac)
            )

            # Document is considered processed if it has at least one page artifact
            if not page_artifacts:
                return None

            # Get australian_state from document or related contract
            australian_state = document.get("australian_state")
            content_hash = document.get("content_hash")

            if not australian_state and content_hash:
                contracts_repo = ContractsRepository()
                contracts = await contracts_repo.get_contracts_by_content_hash(
                    content_hash, limit=1
                )
                if contracts:
                    australian_state = getattr(contracts[0], "australian_state", None)

            if not australian_state:
                return None

            # Reconstruct full text from page artifacts
            full_text = ""
            if page_artifacts:
                # Sort by page number and concatenate text
                sorted_artifacts = sorted(page_artifacts, key=lambda x: x.page_number)
                page_texts = []
                for artifact in sorted_artifacts:
                    # Download text content from storage
                    try:
                        from app.utils.storage_utils import ArtifactStorageService

                        storage_service = ArtifactStorageService()
                        page_text = await storage_service.download_text_blob(
                            artifact.page_text_uri
                        )
                        if page_text:
                            page_texts.append(page_text)
                    except Exception as e:
                        self._log_warning(
                            f"Failed to download page text for artifact {artifact.id}: {e}"
                        )

                full_text = "\n\n".join(page_texts)

            # Fallback if no text could be reconstructed
            if not full_text:
                full_text = (
                    "[Previously processed document - text content not available]"
                )

            # Build ProcessedDocumentSummary
            return ProcessedDocumentSummary(
                success=True,
                document_id=document_id,
                australian_state=australian_state,
                full_text=full_text,
                character_count=len(full_text),
                total_word_count=document.get("total_word_count")
                or len(full_text.split()),
                total_pages=document.get("total_pages") or len(page_artifacts),
                extraction_method=document.get("text_extraction_method") or "unknown",
                extraction_confidence=document.get("extraction_confidence") or 0.0,
                processing_timestamp=(
                    document.get("processing_timestamp")
                    or datetime.now(timezone.utc).isoformat()
                ),
                llm_used=True,  # Default assumption
                original_filename=document.get("original_filename"),
                file_type=document.get("file_type"),
                storage_path=document.get("storage_path"),
                content_hash=content_hash,
            )

        except Exception as e:
            self._log_warning(f"Error checking processed document summary: {e}")
            return None
