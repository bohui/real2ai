"""
SavePageJSONNode - Save JSON metadata content as unified page artifacts

This node processes OCR JSON files and stores them as unified page artifacts
with content_type="json_metadata", eliminating the need for separate tables.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from .base_node import DocumentProcessingNodeBase
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService

logger = logging.getLogger(__name__)


class SavePageJSONAsArtifactPagesJSONNode(DocumentProcessingNodeBase):
    """
    Node to save JSON content as unified page artifacts.
    
    This node:
    1. Reads JSON content from OCR files
    2. Uploads to storage service
    3. Creates unified page artifacts with content_type="json_metadata"
    4. Calculates metrics (file size, JSON structure stats)
    """
    
    def __init__(self):
        super().__init__("save_page_json")
        self.storage_service = ArtifactStorageService()
        self.artifacts_repo = ArtifactsRepository()
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Process and save JSON pages as unified page artifacts.
        
        Args:
            state: Current processing state with ocr_pages
            
        Returns:
            Updated state with page_artifacts list (includes JSON metadata)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting JSON page artifact creation for document {state.get('document_id')}")
            
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
                json_path = page_info['json_path']
                
                try:
                    # Read JSON content
                    if not os.path.exists(json_path):
                        self.logger.warning(f"JSON file not found: {json_path}")
                        continue
                    
                    with open(json_path, 'rb') as f:
                        json_bytes = f.read()
                    
                    # Parse JSON to calculate stats
                    try:
                        json_data = json.loads(json_bytes.decode('utf-8'))
                        
                        # Calculate JSON structure stats
                        def count_json_elements(obj, counts=None):
                            if counts is None:
                                counts = {'objects': 0, 'arrays': 0, 'strings': 0, 'numbers': 0, 'booleans': 0, 'nulls': 0}
                            
                            if isinstance(obj, dict):
                                counts['objects'] += 1
                                for value in obj.values():
                                    count_json_elements(value, counts)
                            elif isinstance(obj, list):
                                counts['arrays'] += 1
                                for item in obj:
                                    count_json_elements(item, counts)
                            elif isinstance(obj, str):
                                counts['strings'] += 1
                            elif isinstance(obj, (int, float)):
                                counts['numbers'] += 1
                            elif isinstance(obj, bool):
                                counts['booleans'] += 1
                            elif obj is None:
                                counts['nulls'] += 1
                            
                            return counts
                        
                        element_counts = count_json_elements(json_data)
                        
                    except json.JSONDecodeError as json_error:
                        self.logger.warning(f"Invalid JSON in {json_path}: {json_error}")
                        element_counts = {}
                    
                    # Upload to storage
                    uri, sha256 = await self.storage_service.upload_page_json(
                        json_bytes, content_hmac, page_number
                    )
                    
                    # Calculate metrics
                    file_size = len(json_bytes)
                    
                    # Prepare stats for database
                    stats = {
                        'file_size_bytes': file_size,
                        'extraction_method': 'external_ocr',
                        'source_file': os.path.basename(json_path),
                        **element_counts  # Include JSON structure stats
                    }
                    
                    # Create artifact using unified repository method
                    artifact_data = await self.artifacts_repo.insert_unified_page_artifact(
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page_number,
                        page_text_uri=uri,
                        page_text_sha256=sha256,
                        content_type="json_metadata",
                        metrics=stats
                    )
                    
                    page_artifacts.append({
                        'artifact_id': str(artifact_data.id),
                        'page_number': page_number,
                        'content_type': 'json_metadata',
                        'uri': uri,
                        'sha256': sha256,
                        'metrics': {
                            'file_size_bytes': file_size,
                            **element_counts
                        }
                    })
                    
                    processed_pages += 1
                    
                    self.logger.debug(
                        f"Processed JSON page {page_number}",
                        extra={
                            'page_number': page_number,
                            'file_size_bytes': file_size,
                            'json_elements': element_counts,
                            'source_file': os.path.basename(json_path)
                        }
                    )
                
                except Exception as page_error:
                    self.logger.error(
                        f"Failed to process JSON page {page_number}: {page_error}",
                        exc_info=True
                    )
                    # Continue processing other pages
                    continue
            
            if processed_pages == 0:
                raise ValueError("No JSON pages were successfully processed")
            
            # Update state with unified page artifacts
            # Append to existing page_artifacts or create new list
            existing_pages = state.get('page_artifacts', [])
            state['page_artifacts'] = existing_pages + page_artifacts
            
            # Update metrics
            self._update_metrics(start_time, success=True)
            
            self.logger.info(
                f"Successfully created {processed_pages} unified JSON metadata page artifacts",
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
            self.logger.error(f"JSON page artifact creation failed: {e}", exc_info=True)
            self._update_metrics(start_time, success=False)
            
            # Set error state
            state['error'] = f"JSON page processing failed: {str(e)}"
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