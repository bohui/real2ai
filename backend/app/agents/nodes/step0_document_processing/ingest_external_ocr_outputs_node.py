"""
IngestExternalOCROutputsNode - Load external OCR output files

This node scans an external OCR output directory and normalizes the file structure
for processing. It handles _nohf.md variants and validates file presence.
"""

import os
import glob
import re
import logging
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from .base_node import DocumentProcessingNodeBase
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState

logger = logging.getLogger(__name__)


@dataclass
class OcrPage:
    """OCR page file mapping."""
    page_number: int
    md_path: str
    jpg_path: str
    json_path: str
    chosen_md_variant: str


class IngestExternalOCROutputsNode(DocumentProcessingNodeBase):
    """
    Node to load and normalize external OCR output files.
    
    This node:
    1. Scans the OCR directory for page files
    2. Handles _nohf.md variant preference
    3. Validates required file presence
    4. Creates normalized page mapping for downstream processing
    """
    
    def __init__(self):
        super().__init__("ingest_external_ocr_outputs")
    
    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Scan OCR directory and prepare file mapping.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated state with ocr_pages list
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting OCR ingestion for document {state.get('document_id')}")
            
            # Get OCR directory path
            ocr_dir = state.get('external_ocr_dir') or state.get('storage_path')
            if not ocr_dir:
                raise ValueError("No external OCR directory specified")
            
            if not os.path.exists(ocr_dir):
                raise ValueError(f"OCR directory does not exist: {ocr_dir}")
            
            # Configuration
            use_nohf = state.get('USE_NOHF_VARIANT', True)
            
            self.logger.debug(f"Scanning OCR directory: {ocr_dir}, use_nohf: {use_nohf}")
            
            # Scan for markdown files
            md_pattern = os.path.join(ocr_dir, "*_page_*.md")
            md_files = glob.glob(md_pattern)
            
            if not md_files:
                raise ValueError(f"No OCR markdown files found in {ocr_dir}")
            
            # Process files into pages
            ocr_pages = []
            page_numbers = set()
            
            for md_file in sorted(md_files):
                # Extract page number and variant
                match = re.search(r'_page_(\d+)(_nohf)?\.md$', os.path.basename(md_file))
                if not match:
                    self.logger.warning(f"Skipping file with invalid pattern: {md_file}")
                    continue
                
                page_num = int(match.group(1))
                is_nohf = bool(match.group(2))
                
                # Skip regular variant if nohf preferred and exists
                if use_nohf and not is_nohf:
                    nohf_path = md_file.replace('.md', '_nohf.md')
                    if os.path.exists(nohf_path):
                        self.logger.debug(f"Skipping {md_file} in favor of nohf variant")
                        continue
                
                # Skip duplicate page numbers
                if page_num in page_numbers:
                    self.logger.debug(f"Skipping duplicate page {page_num}: {md_file}")
                    continue
                
                page_numbers.add(page_num)
                
                # Build corresponding file paths
                base_path = re.sub(r'(_nohf)?\.md$', '', md_file)
                page_entry = OcrPage(
                    page_number=page_num,
                    md_path=md_file,
                    jpg_path=f"{base_path}.jpg",
                    json_path=f"{base_path}.json",
                    chosen_md_variant='nohf' if is_nohf else 'regular'
                )
                
                # Validate required files exist
                missing_files = []
                if not os.path.exists(page_entry.md_path):
                    missing_files.append("MD")
                if not os.path.exists(page_entry.jpg_path):
                    missing_files.append("JPG")
                if not os.path.exists(page_entry.json_path):
                    missing_files.append("JSON")
                
                if missing_files:
                    self.logger.warning(
                        f"Page {page_num} missing files: {', '.join(missing_files)}"
                    )
                    # Continue processing - we'll handle partial pages gracefully
                
                ocr_pages.append(page_entry)
            
            if not ocr_pages:
                raise ValueError(f"No valid OCR pages found in {ocr_dir}")
            
            # Sort pages by page number
            ocr_pages.sort(key=lambda p: p.page_number)
            
            # Convert to dicts for state storage
            ocr_pages_dict = [
                {
                    'page_number': page.page_number,
                    'md_path': page.md_path,
                    'jpg_path': page.jpg_path,
                    'json_path': page.json_path,
                    'chosen_md_variant': page.chosen_md_variant
                }
                for page in ocr_pages
            ]
            
            # Update state
            state['ocr_pages'] = ocr_pages_dict
            
            # Update metrics
            self._update_metrics(start_time, success=True)
            
            self.logger.info(
                f"Successfully ingested {len(ocr_pages)} OCR pages",
                extra={
                    'document_id': state.get('document_id'),
                    'page_count': len(ocr_pages),
                    'use_nohf_variant': use_nohf,
                    'ocr_directory': ocr_dir
                }
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"OCR ingestion failed: {e}", exc_info=True)
            self._update_metrics(start_time, success=False)
            
            # Set error state
            state['error'] = f"OCR ingestion failed: {str(e)}"
            state['error_details'] = {
                'node': self.node_name,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'ocr_directory': state.get('external_ocr_dir') or state.get('storage_path')
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