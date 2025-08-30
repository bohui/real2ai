"""
SavePageMarkdownNode - Save markdown content as unified page artifacts

This node processes OCR markdown files and stores them as unified page artifacts
with content_type="markdown", ensuring proper type discrimination.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from .base_node import DocumentProcessingNodeBase
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService

logger = logging.getLogger(__name__)


class SavePageMarkdownAsArtifactPagesNode(DocumentProcessingNodeBase):
    """
    Node to save markdown content as unified page artifacts.
    
    This node:
    1. Reads markdown content from OCR files
    2. Uploads to storage service
    3. Creates unified page artifacts with content_type="markdown"
    4. Calculates metrics (word count, text length)
    """
    
    def __init__(self):
        super().__init__("save_page_markdown")
        self.storage_service = ArtifactStorageService()
        self.artifacts_repo = ArtifactsRepository()
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Process and save markdown pages as unified page artifacts.
        
        Args:
            state: Current processing state with ocr_pages
            
        Returns:
            Updated state with page_artifacts list (includes markdown content)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting markdown page artifact creation for document {state.get('document_id')}")
            
            # Validate state
            if 'ocr_pages' not in state or not state['ocr_pages']:
                raise ValueError("No OCR pages found in state")
            
            # Get required parameters
            content_hmac = state.get('content_hmac')
            algorithm_version = state.get('algorithm_version', 1)
            params_fingerprint = state.get('params_fingerprint', 'external_ocr')
            
            if not content_hmac:
                raise ValueError("content_hmac is required")
            
            page_artifacts = []
            processed_pages = 0
            
            # Process each page
            for page_info in state['ocr_pages']:
                page_number = page_info['page_number']
                md_path = page_info['md_path']
                chosen_variant = page_info['chosen_md_variant']
                
                try:
                    # Read markdown content
                    if not os.path.exists(md_path):
                        self.logger.warning(f"Markdown file not found: {md_path}")
                        continue
                    
                    with open(md_path, 'rb') as f:
                        md_bytes = f.read()
                    
                    # Upload to storage
                    uri, sha256 = await self.storage_service.upload_page_markdown(
                        md_bytes, content_hmac, page_number
                    )
                    
                    # Calculate metrics
                    md_text = md_bytes.decode('utf-8')
                    text_length = len(md_bytes)
                    word_count = len(md_text.split())
                    line_count = len(md_text.splitlines())
                    
                    # Create artifact using unified repository method
                    artifact_data = await self.artifacts_repo.insert_unified_page_artifact(
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page_number,
                        page_text_uri=uri,
                        page_text_sha256=sha256,
                        content_type="markdown",
                        layout={},  # No layout info from external OCR markdown
                        metrics={
                            'text_length': text_length,
                            'word_count': word_count,
                            'line_count': line_count,
                            'extraction_method': 'external_ocr',
                            'md_variant': chosen_variant,
                            'file_size_bytes': text_length
                        }
                    )
                    
                    page_artifacts.append({
                        'artifact_id': str(artifact_data.id),
                        'page_number': page_number,
                        'content_type': 'markdown',
                        'uri': uri,
                        'sha256': sha256,
                        'metrics': {
                            'text_length': text_length,
                            'word_count': word_count,
                            'line_count': line_count
                        }
                    })
                    
                    processed_pages += 1
                    
                    self.logger.debug(
                        f"Processed markdown page {page_number}",
                        extra={
                            'page_number': page_number,
                            'text_length': text_length,
                            'word_count': word_count,
                            'md_variant': chosen_variant
                        }
                    )
                
                except Exception as page_error:
                    self.logger.error(
                        f"Failed to process page {page_number}: {page_error}",
                        exc_info=True
                    )
                    # Continue processing other pages
                    continue
            
            if processed_pages == 0:
                raise ValueError("No pages were successfully processed")
            
            # Update state with unified page artifacts
            # Append to existing page_artifacts or create new list
            existing_pages = state.get('page_artifacts', [])
            state['page_artifacts'] = existing_pages + page_artifacts
            
            # Update metrics
            self._update_metrics(start_time, success=True)
            
            self.logger.info(
                f"Successfully created {processed_pages} unified markdown page artifacts",
                extra={
                    'document_id': state.get('document_id'),
                    'processed_pages': processed_pages,
                    'total_pages': len(state['ocr_pages']),
                    'content_hmac': content_hmac,
                    'algorithm_version': algorithm_version
                }
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Markdown page artifact creation failed: {e}", exc_info=True)
            self._update_metrics(start_time, success=False)
            
            # Set error state
            state['error'] = f"Markdown page processing failed: {str(e)}"
            state['error_details'] = {
                'node': self.node_name,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'processed_pages': locals().get('processed_pages', 0),
                'total_pages': len(state.get('ocr_pages', []))
            }
            
            return state
    
    def _update_metrics(self, start_time: datetime, success: bool):
        """Update performance metrics."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        self._metrics["executions"] += 1
        self._metrics["total_duration"] += duration
        self._metrics["average_duration"] = (
            self._metrics["total_duration"] / self._metrics["executions"]
        )
        
        if success:
            self._metrics["successes"] += 1
        else:
            self._metrics["failures"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get node performance metrics."""
        return {
            **self._metrics,
            "success_rate": (
                self._metrics["successes"] / self._metrics["executions"]
                if self._metrics["executions"] > 0 else 0.0
            )
        }