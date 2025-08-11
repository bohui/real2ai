"""
SaveDiagramsNode - Persist diagram detection results with artifact references

This node persists diagram detection results using the artifact system for
content-addressed storage and user-scoped references.
"""

import uuid
from typing import Dict, Any
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
    
    def __init__(self):
        super().__init__("save_diagrams")
        self.user_docs_repo = None
        self.artifacts_repo = None

    async def initialize(self, user_id):
        """Initialize repositories with user context"""
        if not self.user_docs_repo:
            self.user_docs_repo = UserDocsRepository(user_id)
        if not self.artifacts_repo:
            self.artifacts_repo = ArtifactsRepository()

    async def cleanup(self):
        """Clean up repository connections"""
        if self.user_docs_repo:
            await self.user_docs_repo.close()
            self.user_docs_repo = None
        if self.artifacts_repo:
            await self.artifacts_repo.close()
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
            
            if not document_id or not text_extraction_result or not text_extraction_result.success:
                self._log_info(f"No valid extraction result for document {document_id}")
                return state

            pages = text_extraction_result.pages
            if not pages:
                return state
            
            # Get user context and initialize repos
            user_context = await self.get_user_context()
            await self.initialize(uuid.UUID(user_context.user_id))
            
            # Get diagram artifacts if using artifact system
            diagram_artifacts = []
            if content_hmac and algorithm_version is not None and params_fingerprint:
                diagram_artifacts = await self.artifacts_repo.get_diagram_artifacts(
                    content_hmac, algorithm_version, params_fingerprint
                )
            
            artifact_map = {(d.page_number, d.diagram_key): d.id for d in diagram_artifacts}
            diagrams_saved = 0
            document_uuid = uuid.UUID(document_id)
            
            for page in pages:
                if not page.content_analysis or not page.content_analysis.layout_features.has_diagrams:
                    continue
                    
                diagram_key = f"diagram_page_{page.page_number}"
                artifact_diagram_id = artifact_map.get((page.page_number, diagram_key))
                
                if artifact_diagram_id:
                    # Use artifact reference
                    annotations = {
                        "diagram_type": getattr(page.content_analysis, 'diagram_type', 'unknown'),
                        "confidence": page.confidence,
                        "detection_method": "artifact_reuse"
                    }
                    
                    await self.user_docs_repo.upsert_document_diagram(
                        document_id=document_uuid,
                        page_number=page.page_number,
                        diagram_key=diagram_key,
                        artifact_diagram_id=artifact_diagram_id,
                        annotations=annotations
                    )
                    diagrams_saved += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            
            self._log_info(f"Saved {diagrams_saved} diagrams for document {document_id}")
            return state
            
        except Exception as e:
            return self._handle_error(state, e, f"Failed to save diagrams: {str(e)}", {
                "document_id": state.get("document_id")
            })