"""
ExtractDiagramsNode - Extract embedded diagrams from markdown content

This node scans markdown files for base64-encoded images and extracts them
as unified visual artifacts with artifact_type="diagram" for storage and indexing.
"""

import os
import re
import base64
import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from .base_node import DocumentProcessingNodeBase
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService

logger = logging.getLogger(__name__)


class ExtractDiagramsFromMarkdownNode(DocumentProcessingNodeBase):
    """
    Node to extract embedded diagrams from markdown content.
    
    This node:
    1. Scans markdown files for base64-encoded images
    2. Extracts and decodes image data
    3. Uploads images as unified visual artifacts
    4. Creates unified visual artifact entries with artifact_type="diagram"
    """
    
    # Regex pattern to match base64 images in markdown
    BASE64_IMAGE_PATTERN = re.compile(
        r'!\[[^\]]*\]\(data:image/([^;]+);base64,([A-Za-z0-9+/=]+)\)',
        re.IGNORECASE
    )
    
    def __init__(self):
        super().__init__("extract_diagrams")
        self.storage_service = ArtifactStorageService()
        self.artifacts_repo = ArtifactsRepository()
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Extract diagrams from markdown files and store as unified visual artifacts.
        
        Args:
            state: Current processing state with ocr_pages
            
        Returns:
            Updated state with diagram_artifacts list (includes extracted diagrams)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting diagram extraction for document {state.get('document_id')}")
            
            # Validate state
            if 'ocr_pages' not in state or not state['ocr_pages']:
                raise ValueError("No OCR pages found in state")
            
            # Get required parameters
            content_hmac = state.get('content_hmac')
            algorithm_version = state.get('algorithm_version', 1)
            params_fingerprint = state.get('params_fingerprint', 'external_ocr')
            
            if not content_hmac:
                raise ValueError("content_hmac is required")
            
            diagram_artifacts = []
            total_extracted = 0
            
            # Process each page's markdown
            for page_info in state['ocr_pages']:
                page_number = page_info['page_number']
                md_path = page_info['md_path']
                
                try:
                    # Read markdown content
                    if not os.path.exists(md_path):
                        self.logger.debug(f"Markdown file not found: {md_path}")
                        continue
                    
                    with open(md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    
                    # Extract diagrams from this page
                    page_diagrams = await self._extract_diagrams_from_content(
                        md_content, content_hmac, algorithm_version, 
                        params_fingerprint, page_number
                    )
                    
                    diagram_artifacts.extend(page_diagrams)
                    total_extracted += len(page_diagrams)
                    
                    if page_diagrams:
                        self.logger.debug(
                            f"Extracted {len(page_diagrams)} diagrams from page {page_number}",
                            extra={
                                'page_number': page_number,
                                'diagrams_extracted': len(page_diagrams),
                                'source_file': os.path.basename(md_path)
                            }
                        )
                
                except Exception as page_error:
                    self.logger.error(
                        f"Failed to process diagrams from page {page_number}: {page_error}",
                        exc_info=True
                    )
                    # Continue processing other pages
                    continue
            
            # Update state with unified visual artifacts
            # Append to existing diagram_artifacts or create new list
            existing_diagrams = state.get('diagram_artifacts', [])
            state['diagram_artifacts'] = existing_diagrams + diagram_artifacts
            
            # Update metrics
            self._update_metrics(start_time, success=True)
            
            self.logger.info(
                f"Successfully extracted {total_extracted} diagrams from {len(state['ocr_pages'])} pages",
                extra={
                    'document_id': state.get('document_id'),
                    'total_diagrams': total_extracted,
                    'total_pages': len(state['ocr_pages']),
                    'content_hmac': content_hmac,
                    'algorithm_version': algorithm_version
                }
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Diagram extraction failed: {e}", exc_info=True)
            self._update_metrics(start_time, success=False)
            
            # Set error state
            state['error'] = f"Diagram extraction failed: {str(e)}"
            state['error_details'] = {
                'node': self.node_name,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'extracted_diagrams': locals().get('total_extracted', 0),
                'total_pages': len(state.get('ocr_pages', []))
            }
            
            return state
    
    async def _extract_diagrams_from_content(
        self,
        md_content: str,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract diagrams from markdown content.
        
        Args:
            md_content: Markdown content to scan
            content_hmac: Document content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            page_number: Page number for context
            
        Returns:
            List of diagram artifact information
        """
        diagrams = []
        
        # Find all base64 images in markdown
        matches = self.BASE64_IMAGE_PATTERN.findall(md_content)
        
        for match_index, (image_type, base64_data) in enumerate(matches):
            try:
                # Decode base64 data
                image_bytes = base64.b64decode(base64_data)
                
                # Calculate image hash
                image_sha256 = hashlib.sha256(image_bytes).hexdigest()
                
                # Determine file extension
                ext = self._normalize_image_extension(image_type)
                
                # Upload to storage
                uri, returned_sha256 = await self.storage_service.upload_diagram_image(
                    image_bytes, content_hmac, page_number, image_sha256, ext
                )
                
                # Prepare diagram metadata
                diagram_meta = {
                    'image_type': image_type,
                    'file_extension': ext,
                    'file_size_bytes': len(image_bytes),
                    'image_sha256': image_sha256,
                    'extraction_method': 'base64_from_markdown',
                    'source_page': page_number,
                    'diagram_index': match_index,
                    'storage_uri': uri
                }
                
                # Generate diagram key (unique identifier within the page)
                diagram_key = f"diagram_{page_number}_{match_index}_{image_sha256[:8]}"
                
                # Create unified visual artifact with artifact_type="diagram"
                artifact_data = await self.artifacts_repo.insert_unified_visual_artifact(
                    content_hmac=content_hmac,
                    algorithm_version=algorithm_version,
                    params_fingerprint=params_fingerprint,
                    page_number=page_number,
                    diagram_key=diagram_key,
                    artifact_type="diagram",
                    image_uri=uri,
                    image_sha256=image_sha256,
                    image_metadata=diagram_meta
                )
                
                diagrams.append({
                    'artifact_id': str(artifact_data.id),
                    'page_number': page_number,
                    'diagram_key': diagram_key,
                    'artifact_type': 'diagram',
                    'image_uri': uri,
                    'image_sha256': image_sha256,
                    'image_metadata': diagram_meta
                })
                
                self.logger.debug(
                    f"Extracted diagram {diagram_key}",
                    extra={
                        'diagram_key': diagram_key,
                        'page_number': page_number,
                        'image_type': image_type,
                        'file_size_bytes': len(image_bytes),
                        'sha256': image_sha256[:16]  # First 16 chars for logging
                    }
                )
                
            except Exception as diagram_error:
                self.logger.error(
                    f"Failed to extract diagram {match_index} from page {page_number}: {diagram_error}",
                    exc_info=True
                )
                # Continue processing other diagrams
                continue
        
        return diagrams
    
    def _normalize_image_extension(self, image_type: str) -> str:
        """
        Normalize image type to standard file extension.
        
        Args:
            image_type: MIME image type (e.g., 'png', 'jpeg')
            
        Returns:
            Normalized file extension
        """
        # Common image type mappings
        type_map = {
            'jpeg': 'jpg',
            'jpg': 'jpg',
            'png': 'png',
            'gif': 'gif',
            'webp': 'webp',
            'svg+xml': 'svg',
            'svg': 'svg',
            'bmp': 'bmp',
            'tiff': 'tiff'
        }
        
        # Clean up the image type
        clean_type = image_type.lower().strip()
        
        # Remove any 'image/' prefix if present
        if clean_type.startswith('image/'):
            clean_type = clean_type[6:]
        
        return type_map.get(clean_type, 'img')  # Default to 'img' if unknown
    
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