"""
SavePageJPGNode - Save JPG image content as unified visual artifacts

This node processes OCR JPG files and stores them as unified visual artifacts
with artifact_type="image_jpg", eliminating the need for separate tables.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from .base_node import DocumentProcessingNodeBase
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService
from app.services.visual_artifact_service import VisualArtifactService

logger = logging.getLogger(__name__)


class SavePageJPGAsArtifactPagesJPGNode(DocumentProcessingNodeBase):
    """
    Node to save JPG content as unified visual artifacts.
    
    This node:
    1. Reads JPG content from OCR files
    2. Uploads to storage service
    3. Creates unified visual artifacts with artifact_type="image_jpg"
    4. Calculates metrics (file size, image dimensions if available)
    """
    
    def __init__(self):
        super().__init__("save_page_jpg")
        self.storage_service = ArtifactStorageService()
        self.artifacts_repo = ArtifactsRepository()
        self.visual_artifact_service = VisualArtifactService(
            storage_service=self.storage_service,
            artifacts_repo=self.artifacts_repo
        )
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Process and save JPG pages as JPG artifacts.
        
        Args:
            state: Current processing state with ocr_pages
            
        Returns:
            Updated state with diagram_artifacts list (includes JPG images)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting JPG page artifact creation for document {state.get('document_id')}")
            
            # Validate state
            if 'ocr_pages' not in state or not state['ocr_pages']:
                raise ValueError("No OCR pages found in state")
            
            # Get required parameters
            content_hmac = state.get('content_hmac')
            algorithm_version = state.get('algorithm_version', 1)
            params_fingerprint = state.get('params_fingerprint', 'external_ocr')
            
            if not content_hmac:
                raise ValueError("content_hmac is required")
            
            visual_artifacts = []
            processed_pages = 0
            
            # Process each page
            for page_info in state['ocr_pages']:
                page_number = page_info['page_number']
                jpg_path = page_info['jpg_path']
                
                try:
                    # Read JPG content
                    if not os.path.exists(jpg_path):
                        self.logger.warning(f"JPG file not found: {jpg_path}")
                        continue
                    
                    with open(jpg_path, 'rb') as f:
                        jpg_bytes = f.read()
                    
                    # Calculate metrics
                    file_size = len(jpg_bytes)
                    
                    # Basic image metadata (could be extended with PIL if needed)
                    metadata = {
                        'file_size_bytes': file_size,
                        'extraction_method': 'external_ocr',
                        'source_file': os.path.basename(jpg_path)
                    }
                    
                    diagram_key = f"page_image_{page_number}"
                    
                    # Use visual artifact service to store both image and metadata
                    result = await self.visual_artifact_service.store_visual_artifact(
                        image_bytes=jpg_bytes,
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page_number,
                        diagram_key=diagram_key,
                        artifact_type="image_jpg",
                        image_metadata=metadata
                    )
                    
                    visual_artifacts.append({
                        'artifact_id': result.artifact_id,
                        'page_number': page_number,
                        'diagram_key': diagram_key,
                        'artifact_type': 'image_jpg',
                        'image_uri': result.image_uri,
                        'image_sha256': result.image_sha256,
                        'image_metadata': metadata,
                        'cache_hit': result.cache_hit
                    })
                    
                    processed_pages += 1
                    
                    if result.cache_hit:
                        self.logger.debug(
                            f"Reused cached JPG artifact for page {page_number}",
                            extra={
                                'page_number': page_number,
                                'source_file': os.path.basename(jpg_path),
                                'cache_hit': True
                            }
                        )
                    else:
                        self.logger.debug(
                            f"Processed JPG page {page_number}",
                            extra={
                                'page_number': page_number,
                                'file_size_bytes': file_size,
                                'source_file': os.path.basename(jpg_path),
                                'cache_hit': False
                            }
                        )
                
                except Exception as page_error:
                    self.logger.error(
                        f"Failed to process JPG page {page_number}: {page_error}",
                        exc_info=True
                    )
                    # Continue processing other pages
                    continue
            
            if processed_pages == 0:
                raise ValueError("No JPG pages were successfully processed")
            
            # Update state with unified visual artifacts  
            # Append to existing diagram_artifacts or create new list
            existing_diagrams = state.get('diagram_artifacts', [])
            state['diagram_artifacts'] = existing_diagrams + visual_artifacts
            
            # Update metrics
            self._update_metrics(start_time, success=True)
            
            self.logger.info(
                f"Successfully created {processed_pages} unified JPG visual artifacts",
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
            self.logger.error(f"JPG page artifact creation failed: {e}", exc_info=True)
            self._update_metrics(start_time, success=False)
            
            # Set error state
            state['error'] = f"JPG page processing failed: {str(e)}"
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