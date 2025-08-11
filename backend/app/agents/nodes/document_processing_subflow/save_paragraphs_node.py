"""
SaveParagraphsNode for Document Processing Subflow

This module implements saving of user paragraph references to the database.
It creates per-user paragraph rows that reference shared paragraph artifacts,
supporting the user-scoped document model while leveraging shared content.
"""

import logging
import time
from typing import Dict, Any, List
from uuid import UUID

from app.agents.nodes.document_processing_subflow.base_node import DocumentProcessingNodeBase
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.services.repositories.user_docs_repository import UserDocsRepository
from app.core.auth_context import AuthContext

logger = logging.getLogger(__name__)


class SaveParagraphsNode(DocumentProcessingNodeBase):
    """
    Node for saving user document paragraph references.
    
    Creates per-user rows in user_document_paragraphs that reference
    shared paragraph artifacts. This enables user-specific annotations
    and access control while reusing shared content artifacts.
    """

    def __init__(self):
        super().__init__("save_paragraphs")
        # UserDocsRepository will be created with user client during execution

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Execute user paragraph row saving.
        
        Args:
            state: Current document processing state
            
        Returns:
            Updated state with paragraph save results
        """
        start_time = time.time()
        
        try:
            # Validate required state
            document_id = state.get("document_id")
            paragraph_artifacts = state.get("paragraph_artifacts", [])
            
            if not document_id:
                return self._handle_error(
                    state, ValueError("Missing document_id"), 
                    "Document ID required for saving paragraphs"
                )
            
            if not paragraph_artifacts:
                self._log_info("No paragraph artifacts to save, skipping")
                return state

            # Convert document_id to UUID if needed
            if isinstance(document_id, str):
                document_id = UUID(document_id)

            self._log_info(f"Saving {len(paragraph_artifacts)} paragraph references for document {document_id}")

            # Get user ID from auth context and create repository
            user_id = AuthContext.get_user_id()
            if not user_id:
                return self._handle_error(
                    state, ValueError("Missing user authentication"), 
                    "User ID required for saving paragraphs"
                )
            user_repo = UserDocsRepository(UUID(user_id))

            # Prepare paragraph data for batch upsert with enhanced annotations
            paragraph_data = []
            page_paragraph_counts = {}  # Track paragraphs per page for relative indexing
            
            for artifact in paragraph_artifacts:
                try:
                    page_num = artifact["page_number"]
                    doc_para_idx = artifact["paragraph_index"]
                    
                    # Calculate page-relative index
                    page_paragraph_counts[page_num] = page_paragraph_counts.get(page_num, 0) + 1
                    page_relative_index = page_paragraph_counts[page_num]
                    
                    paragraph_data.append({
                        "page_number": page_num,
                        "paragraph_index": doc_para_idx,
                        "artifact_paragraph_id": UUID(artifact["id"]),
                        "annotations": {
                            "doc_paragraph_index": doc_para_idx,  # For clarity and stability
                            "page_relative_index": page_relative_index  # For UI/API convenience
                        }
                    })
                except Exception as e:
                    self._log_warning(f"Failed to prepare paragraph {artifact.get('paragraph_index', '?')}: {e}")
            
            # Batch upsert user document paragraphs  
            try:
                results = await user_repo.batch_upsert_document_paragraphs(
                    document_id=document_id,
                    paragraph_data=paragraph_data
                )
                saved_count = len(results)
                errors = []
                
            except Exception as e:
                # Fallback to individual upserts on batch failure
                self._log_warning(f"Batch upsert failed, falling back to individual upserts: {e}")
                saved_count = 0
                errors = []
                
                # Fallback: compute page relative indices for individual upserts
                fallback_page_counts = {}
                for artifact in paragraph_artifacts:
                    try:
                        artifact_id = UUID(artifact["id"])
                        page_number = artifact["page_number"]
                        paragraph_index = artifact["paragraph_index"]
                        
                        # Calculate page-relative index
                        fallback_page_counts[page_number] = fallback_page_counts.get(page_number, 0) + 1
                        page_relative_index = fallback_page_counts[page_number]
                        
                        # Upsert user document paragraph with enhanced annotations
                        await user_repo.upsert_document_paragraph(
                            document_id=document_id,
                            page_number=page_number,
                            paragraph_index=paragraph_index,
                            artifact_paragraph_id=artifact_id,
                            annotations={
                                "doc_paragraph_index": paragraph_index,
                                "page_relative_index": page_relative_index
                            }
                        )
                        
                        saved_count += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to save paragraph {artifact.get('paragraph_index', '?')}: {e}"
                        self._log_warning(
                            error_msg,
                            extra={
                                "paragraph_index": artifact.get('paragraph_index'),
                                "page_number": artifact.get('page_number'),
                                "artifact_id": artifact.get('id'),
                                "error_type": type(e).__name__
                            }
                        )
                        errors.append({
                            "paragraph_index": artifact.get('paragraph_index'),
                            "error": str(e),
                            "error_type": type(e).__name__
                        })
                        continue

            # Calculate metrics
            duration = time.time() - start_time
            success_rate = saved_count / len(paragraph_artifacts) if paragraph_artifacts else 0

            self._log_info(
                f"Saved {saved_count}/{len(paragraph_artifacts)} paragraph references "
                f"in {duration:.2f}s (success rate: {success_rate:.1%})"
            )

            # Update state with save results
            state = state.copy()
            state.setdefault("processing_metrics", {}).update({
                "paragraph_save_duration_ms": duration * 1000,
                "paragraphs_saved_count": saved_count,
                "paragraph_save_success_rate": success_rate,
                "paragraph_save_errors_count": len(errors),
                "paragraph_save_failures": errors  # Include failed indices for debugging
            })

            # Log errors if any occurred but don't fail the entire operation
            if errors and len(errors) < len(paragraph_artifacts):
                self._log_warning(f"Partial success: {len(errors)} paragraph save failures")
            elif errors:
                return self._handle_error(
                    state, RuntimeError("All paragraph saves failed"), 
                    "Failed to save any paragraph references",
                    {"errors": errors}
                )

            self._record_success(duration)
            return state

        except Exception as e:
            return self._handle_error(
                state, e, "Paragraph save operation failed",
                {"document_id": str(document_id) if 'document_id' in locals() else None}
            )

    async def cleanup(self):
        """Cleanup resources"""
        # No persistent resources to clean up
        pass