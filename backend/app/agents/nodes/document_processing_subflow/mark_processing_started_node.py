"""
MarkProcessingStartedNode - Set processing_started_at timestamp

This node updates the document record to mark processing as started by setting
the processing_started_at timestamp and updating status to PROCESSING.
"""

from datetime import datetime, timezone

from app.models import ProcessingStatus
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase
from app.services.repositories.user_docs_repository import UserDocsRepository
from app.services.repositories.runs_repository import RunsRepository
import uuid


class MarkProcessingStartedNode(DocumentProcessingNodeBase):
    user_docs_repo = None
    runs_repo = None
    """
    Node responsible for marking document processing as started.

    This node:
    1. Sets processing_started_at timestamp in database
    2. Updates processing_status to PROCESSING
    3. Provides audit trail for processing workflow

    State Updates:
    - Updates database record only (no state changes)
    """

    # Inherit constructor from DocumentProcessingNodeBase

    async def initialize(self, user_id):
        """Initialize repositories with user context"""
        if not self.user_docs_repo:
            self.user_docs_repo = UserDocsRepository(user_id)
        if not self.runs_repo:
            self.runs_repo = RunsRepository(user_id)

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Mark document processing as started.

        Args:
            state: Current processing state with document_id

        Returns:
            Updated state (no changes, but database updated)
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
                    {"operation": "mark_processing_started"},
                )

            self._log_info(f"Marking processing started for document {document_id}")

            # Get user-authenticated client
            user_client = await self.get_user_client()

            # Set processing started timestamp and status
            processing_started_at = datetime.now(timezone.utc)

            update_data = {
                "processing_started_at": processing_started_at,
                "processing_status": ProcessingStatus.PROCESSING.value,
            }

            # Update document record using repository
            from app.services.repositories.documents_repository import (
                DocumentsRepository,
            )
            from uuid import UUID

            docs_repo = DocumentsRepository()
            await docs_repo.update_document_status(
                UUID(document_id),
                ProcessingStatus.PROCESSING.value,
                processing_started_at=processing_started_at,
            )

            # Start a new processing run if not already started
            run_id = state.get("run_id")
            if not run_id and self.runs_repo:
                try:
                    new_run = await self.runs_repo.start_run(
                        document_id=uuid.UUID(document_id),
                        run_type="document_processing",
                        run_input={
                            "document_id": document_id,
                            "processing_started_at": processing_started_at.isoformat(),
                        },
                    )
                    # Store run_id in state for subsequent nodes
                    state = state.copy()
                    state["run_id"] = str(new_run.id)
                    self._log_info(f"Started new processing run {new_run.id}")
                except Exception as e:
                    self._log_warning(f"Failed to start processing run: {e}")

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Successfully marked processing started for document {document_id}",
                extra={
                    "document_id": document_id,
                    "processing_started_at": processing_started_at.isoformat(),
                    "status": ProcessingStatus.PROCESSING.value,
                    "duration_seconds": duration,
                },
            )

            # Return state unchanged (database operation only)
            return state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to mark processing started: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "database_update",
                    "table": "documents",
                    "field": "processing_started_at",
                },
            )
