"""
SaveDiagramsNode - Persist diagram detection results with artifact references

This node persists diagram detection results using the artifact system for
content-addressed storage and user-scoped references.
"""

import uuid
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase
from app.services.repositories.user_docs_repository import UserDocsRepository
from app.services.repositories.artifacts_repository import ArtifactsRepository


class SaveDiagramsNode(DocumentProcessingNodeBase):
    """
    Node responsible for saving diagram detection results with artifact references.

    This node:
    1. Takes text extraction results with page-level diagram analysis
    2. Maps artifact diagram IDs to user document diagrams using upserts
    3. Handles idempotent operations for retry safety

    State Updates:
    - No state changes (database operation only)
    """

    user_docs_repo = None
    artifacts_repo = None
    # Inherit constructor from DocumentProcessingNodeBase

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
        """Save diagram detection results with artifact references."""
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            document_id = state.get("document_id")
            content_hmac = state.get("content_hmac")
            algorithm_version = state.get("algorithm_version")
            params_fingerprint = state.get("params_fingerprint")
            text_extraction_result = state.get("text_extraction_result")
            diagram_processing_result = state.get("diagram_processing_result")

            if (
                not document_id
                or not text_extraction_result
                or not text_extraction_result.success
            ):
                self._log_info(f"No valid extraction result for document {document_id}")
                return state

            pages = text_extraction_result.pages
            if not pages:
                return state

            # Ensure user context is available before repository operations
            state = self._ensure_user_context(state)
            if "auth_error" in state:
                return self._handle_error(
                    state,
                    ValueError(state["auth_error"]),
                    "User authentication required for saving diagrams",
                )

            # Get user context and initialize repos
            user_context = await self.get_user_context()
            await self.initialize(uuid.UUID(user_context.user_id))

            # # First, persist any new diagram detections as artifacts - don't need to
            current_result = diagram_processing_result
            # if (
            #     current_result
            #     and current_result.get("detection_summary")
            #     and content_hmac
            #     and algorithm_version is not None
            #     and params_fingerprint
            # ):
            #     # Check if the result has diagrams
            #     detected_diagrams = current_result.get("diagrams", [])

            #     # Track diagram sequence per page for deterministic keys
            #     page_diagram_counts = {}
            #     for diagram in detected_diagrams:
            #         try:
            #             # Create deterministic diagram key using sequence number per page
            #             page_num = diagram.get("page") or diagram.get("page_number")
            #             if page_num not in page_diagram_counts:
            #                 page_diagram_counts[page_num] = 0
            #             page_diagram_counts[page_num] += 1
            #             diagram_key = f"diagram_page_{page_num}_{diagram.get('type')}_{page_diagram_counts[page_num]:02d}"

            #             # Insert diagram detection as artifact
            #             await self.artifacts_repo.insert_diagram_artifact(
            #                 content_hmac=content_hmac,
            #                 algorithm_version=algorithm_version,
            #                 params_fingerprint=params_fingerprint,
            #                 page_number=page_num,
            #                 diagram_key=diagram_key,
            #                 diagram_meta={
            #                     "type": diagram.get("type"),
            #                     "confidence": diagram.get("confidence", 0.0),
            #                     "description": diagram.get("description", ""),
            #                     "detection_method": "ocr_detection",
            #                     "bbox": diagram.get("bbox"),
            #                 },
            #                 artifact_type="diagram",
            #             )
            #             self._log_info(
            #                 f"Persisted diagram detection as artifact: {diagram_key}"
            #             )
            #         except Exception as e:
            #             self._log_warning(
            #                 f"Failed to persist diagram detection as artifact: {e}"
            #             )

            # Get diagram artifacts if using artifact system
            diagram_artifacts = []
            if content_hmac and algorithm_version is not None and params_fingerprint:
                # Use unified method to get all visual artifacts (diagrams and images)
                diagram_artifacts = await self.artifacts_repo.get_all_visual_artifacts(
                    content_hmac, algorithm_version, params_fingerprint
                )

            # Refresh artifact map after persisting new detections
            if content_hmac and algorithm_version is not None and params_fingerprint:
                diagram_artifacts = await self.artifacts_repo.get_all_visual_artifacts(
                    content_hmac, algorithm_version, params_fingerprint
                )

            artifact_map = {
                (d.page_number, d.diagram_key): d.id for d in diagram_artifacts
            }
            diagrams_saved = 0
            document_uuid = uuid.UUID(document_id)

            # Process diagrams from detection result (primary source)
            diagram_types = {}
            diagram_pages = []

            if current_result and current_result.get("success"):
                detected_diagrams = current_result.get("diagrams", [])
                # Track diagram sequence per page for deterministic keys (consistent with persistence above)
                page_diagram_counts = {}
                for diagram in detected_diagrams:
                    page_number = getattr(diagram, "page", None) or getattr(
                        diagram, "page_number", None
                    )
                    diagram_type = diagram.type

                    # Use same deterministic key generation as above
                    if page_number not in page_diagram_counts:
                        page_diagram_counts[page_number] = 0
                    page_diagram_counts[page_number] += 1
                    diagram_key = f"diagram_page_{page_number}_{diagram_type}_{page_diagram_counts[page_number]:02d}"

                    # Track diagram types and pages for result summary
                    if diagram_type not in diagram_types:
                        diagram_types[diagram_type] = 0
                    diagram_types[diagram_type] += 1

                    if page_number not in diagram_pages:
                        diagram_pages.append(page_number)

                    # Find corresponding artifact
                    artifact_diagram_id = artifact_map.get((page_number, diagram_key))

                    if artifact_diagram_id:
                        # Use artifact reference to create user mapping
                        annotations = {
                            "diagram_type": diagram_type,
                            "confidence": getattr(diagram, "confidence", 0.0),
                            "description": getattr(diagram, "description", ""),
                            "detection_method": "ocr_detection",
                            "bbox": getattr(diagram, "bbox", None),
                        }

                        await self.user_docs_repo.upsert_document_diagram(
                            document_id=document_uuid,
                            page_number=page_number,
                            diagram_key=diagram_key,
                            artifact_diagram_id=artifact_diagram_id,
                            annotations=annotations,
                        )
                        diagrams_saved += 1

            # Set diagram_processing_result for downstream metrics
            updated_state = state.copy()
            from app.schema.document import DiagramProcessingResult

            # Convert page numbers to DiagramPageSummary objects
            diagram_page_summaries = []
            total_diagram_pages = len(diagram_pages)

            for idx, page_num in enumerate(sorted(diagram_pages)):
                # Emit incremental progress for each diagram page
                await self.emit_page_progress(
                    state,
                    current_page=idx + 1,
                    total_pages=total_diagram_pages,
                    description="Saving diagram page",
                    progress_range=self.progress_range,
                )
                # Find diagrams for this page to get the primary type and confidence
                page_diagrams = [
                    d
                    for d in detected_diagrams
                    if getattr(d, "page", None) == page_num
                    or getattr(d, "page_number", None) == page_num
                ]
                if page_diagrams:
                    # Use the first diagram's type and confidence for the page summary
                    primary_type = (
                        page_diagrams[0].type
                        if hasattr(page_diagrams[0], "type")
                        else "unknown"
                    )
                    confidence = getattr(page_diagrams[0], "confidence", 0.0)
                else:
                    primary_type = "unknown"
                    confidence = 0.0

                diagram_page_summaries.append(
                    {
                        "page_number": page_num,
                        "primary_type": primary_type,
                        "confidence": confidence,
                    }
                )

            updated_state["diagram_processing_result"] = DiagramProcessingResult(
                total_diagrams=diagrams_saved,
                diagram_pages=diagram_page_summaries,
                diagram_types=diagram_types,
                detection_summary={
                    "artifacts_created": len(diagram_artifacts),
                    "user_mappings_created": diagrams_saved,
                    # Standardize to string labels for consistency across nodes
                    # "ocr_detection" when there was a current detection result present,
                    # otherwise "legacy_analysis" when saving without a detection pass
                    "processing_method": (
                        "ocr_detection" if current_result else "legacy_analysis"
                    ),
                },
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Saved {diagrams_saved} diagrams for document {document_id}",
                extra={
                    "diagrams_saved": diagrams_saved,
                    "diagram_types": diagram_types,
                    "diagram_pages": len(diagram_pages),
                },
            )
            return updated_state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to save diagrams: {str(e)}",
                {"document_id": state.get("document_id")},
            )
