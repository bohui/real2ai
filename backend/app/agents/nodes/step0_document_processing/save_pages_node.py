"""
SavePagesNode - Persist page-level analysis results with artifact references

This node persists page-level text extraction and analysis results using
the artifact system for content-addressed storage and user-scoped references.
"""

import uuid
from datetime import datetime, timezone

from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase
from app.services.repositories.user_docs_repository import UserDocsRepository
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService


class SavePagesNode(DocumentProcessingNodeBase):
    """
    Node responsible for saving page-level analysis results with artifact references.

    This node:
    1. Takes text extraction results and artifact metadata from state
    2. Maps artifact page IDs to user document pages using upserts
    3. Maintains user authentication context for RLS enforcement
    4. Handles idempotent operations for retry safety

    State Updates:
    - No state changes (database operation only)
    """

    def __init__(self, progress_range: tuple[int, int] = (28, 36)):
        super().__init__("save_pages")
        self.user_docs_repo = None
        self.artifacts_repo = None
        # Use artifacts bucket for storing page artifacts
        self.storage_service = ArtifactStorageService(bucket_name="artifacts")
        self.progress_range = progress_range

    async def initialize(self, user_id):
        """Initialize repositories with user context"""
        if not self.user_docs_repo:
            self.user_docs_repo = UserDocsRepository(user_id)
        if not self.artifacts_repo:
            self.artifacts_repo = ArtifactsRepository()

    async def cleanup(self):
        """Clean up repository connections"""
        if self.user_docs_repo:
            self.user_docs_repo = None
        if self.artifacts_repo:
            self.artifacts_repo = None

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Save page-level analysis results with artifact references.

        This method implements idempotent page upserts that map artifact page IDs
        to user document pages without storing raw text content.

        Args:
            state: Current processing state with artifact metadata

        Returns:
            Updated state (no changes, database updated)
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            # Validate required state
            document_id = state.get("document_id")
            content_hmac = state.get("content_hmac")
            algorithm_version = state.get("algorithm_version")
            params_fingerprint = state.get("params_fingerprint")
            text_extraction_result = state.get("text_extraction_result")

            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "save_pages"},
                )

            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Text extraction result is missing or unsuccessful",
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": (
                            text_extraction_result.success
                            if text_extraction_result
                            else False
                        ),
                    },
                )

            if not all(
                [content_hmac, algorithm_version is not None, params_fingerprint]
            ):
                return self._handle_error(
                    state,
                    ValueError("Missing artifact metadata"),
                    "Artifact metadata required for page mapping",
                    {
                        "document_id": document_id,
                        "has_content_hmac": bool(content_hmac),
                        "has_algorithm_version": algorithm_version is not None,
                        "has_params_fingerprint": bool(params_fingerprint),
                    },
                )

            pages = text_extraction_result.pages
            if not pages:
                self._log_info(f"No pages to save for document {document_id}")
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._record_success(duration)
                return state

            # Ensure user context is available before repository operations
            state = self._ensure_user_context(state)
            if "auth_error" in state:
                return self._handle_error(
                    state,
                    ValueError(state["auth_error"]),
                    "User authentication required for saving pages",
                )

            # Get user ID for repository initialization
            user_context = await self.get_user_context()
            user_id = uuid.UUID(user_context.user_id)

            # Initialize repositories
            await self.initialize(user_id)

            self._log_info(
                f"Saving {len(pages)} pages for document {document_id} using artifact mapping",
                extra={
                    "document_id": document_id,
                    "page_count": len(pages),
                    "content_hmac": content_hmac,
                    "algorithm_version": algorithm_version,
                    "params_fingerprint": params_fingerprint[:12],
                },
            )

            # Get page artifacts for mapping using unified method
            page_artifacts = await self.artifacts_repo.get_all_page_artifacts(
                content_hmac, algorithm_version, params_fingerprint
            )

            # Create artifact ID mapping by page number
            artifact_map = {
                artifact.page_number: artifact.id for artifact in page_artifacts
            }

            # Upsert document pages with artifact references
            pages_saved = 0
            document_uuid = uuid.UUID(document_id)
            total_pages = len(pages)

            for idx, page in enumerate(pages):
                # Emit incremental progress for each page
                await self.emit_page_progress(
                    current_page=idx + 1,
                    total_pages=total_pages,
                    description="Saving page",
                    progress_range=self.progress_range,
                )
                artifact_page_id = artifact_map.get(page.page_number)
                if not artifact_page_id:
                    # Fallback: create and store page artifact on-the-fly so it is still saved under documents prefix
                    try:
                        page_text = getattr(page, "text_content", "") or ""
                        page_text_uri, page_text_sha256 = (
                            await self.storage_service.upload_page_text(
                                page_text, content_hmac, page.page_number
                            )
                        )

                        created_page_artifact = (
                            await self.artifacts_repo.insert_unified_page_artifact(
                                content_hmac=content_hmac,
                                algorithm_version=algorithm_version,
                                params_fingerprint=params_fingerprint,
                                page_number=page.page_number,
                                page_text_uri=page_text_uri,
                                page_text_sha256=page_text_sha256,
                                content_type="text",
                                layout=(
                                    page.content_analysis.layout_features.__dict__
                                    if getattr(page, "content_analysis", None)
                                    is not None
                                    else None
                                ),
                                metrics={
                                    "confidence": getattr(page, "confidence", 0.0),
                                    "word_count": getattr(page, "word_count", 0),
                                    "text_length": getattr(
                                        page, "text_length", len(page_text)
                                    ),
                                    "extraction_method": getattr(
                                        page, "extraction_method", "unknown"
                                    ),
                                },
                            )
                        )
                        artifact_page_id = created_page_artifact.id
                        artifact_map[page.page_number] = artifact_page_id
                        self._log_info(
                            f"Created missing page artifact for page {page.page_number}",
                            extra={
                                "page_number": page.page_number,
                                "artifact_id": str(artifact_page_id),
                                "uri": page_text_uri,
                            },
                        )
                    except Exception as create_err:
                        self._log_warning(
                            f"No artifact found for page {page.page_number} and failed to create one: {create_err}"
                        )
                        continue

                # Build user annotations from page analysis
                page_analysis = page.content_analysis
                annotations = {}
                if page_analysis:
                    annotations = {
                        "content_types": getattr(page_analysis, "content_types", []),
                        "primary_content_type": getattr(
                            page_analysis, "primary_type", None
                        ),
                        "extraction_confidence": getattr(page, "confidence", 0.0),
                        "extraction_method": getattr(
                            page, "extraction_method", "unknown"
                        ),
                        "quality_indicators": (
                            page_analysis.quality_indicators.__dict__
                            if hasattr(page_analysis, "quality_indicators")
                            and page_analysis.quality_indicators
                            else None
                        ),
                    }

                # Flags for processing state
                flags = {
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processing_version": algorithm_version,
                }

                # Upsert document page with artifact reference
                await self.user_docs_repo.upsert_document_page(
                    document_id=document_uuid,
                    page_number=page.page_number,
                    artifact_page_id=artifact_page_id,
                    annotations=annotations,
                    flags=flags,
                )

                pages_saved += 1

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Successfully saved {pages_saved} pages for document {document_id}",
                extra={
                    "document_id": document_id,
                    "pages_saved": pages_saved,
                    "duration_seconds": duration,
                    "artifact_mapping": len(artifact_map),
                },
            )

            return state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to save document pages: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "upsert_document_page",
                    "page_count": (
                        len(state.get("text_extraction_result").pages)
                        if state.get("text_extraction_result")
                        and state.get("text_extraction_result").pages
                        else 0
                    ),
                    "content_hmac": state.get("content_hmac"),
                },
            )
