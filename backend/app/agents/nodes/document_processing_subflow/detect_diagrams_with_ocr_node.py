"""
DetectDiagramsWithOCRNode - Use OCR service to detect diagrams per-page

This node uses Gemini OCR with the PROMPT_DIAGRAMS_ONLY template to detect
diagrams in document pages using individual page JPGs, not the full document.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from app.agents.nodes.document_processing_subflow.base_node import DocumentProcessingNodeBase
from app.core.langsmith_config import langsmith_trace
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.core.prompts.output_parser import create_parser
from app.prompts.schema.diagram_detection_schema import DiagramDetectionResponse, DiagramDetectionItem
from app.models.supabase_models import DiagramType

logger = logging.getLogger(__name__)


class DetectDiagramsWithOCRNode(DocumentProcessingNodeBase):
    """
    Node that detects diagrams using OCR service per-page with page JPGs.
    
    This node:
    1. Gets page extraction results from text_extraction_result
    2. For each page with images/low text, renders page to JPG
    3. Calls Gemini OCR per-page with diagram detection prompt
    4. Aggregates diagram detection results from all pages
    5. Stores diagram detection results in state for later persistence
    """

    def __init__(self):
        super().__init__("detect_diagrams_with_ocr")
        self.ocr_service = None
        self.parser = create_parser(DiagramDetectionResponse)
        # Configuration will be loaded from settings

    async def _initialize_services(self):
        """Initialize OCR service if not already initialized"""
        if self.ocr_service is None:
            # Get user client asynchronously
            user_client = await self.get_user_client()
            self.ocr_service = GeminiOCRService(user_client=user_client)
            await self.ocr_service.initialize()

    @langsmith_trace(name="detect_diagrams_with_ocr", run_type="tool")
    async def execute(self, state: "DocumentProcessingState") -> "DocumentProcessingState":
        """
        Execute diagram detection using OCR service per-page.
        
        Args:
            state: Current workflow state containing document info and text extraction results
            
        Returns:
            Updated state with diagram detection results
        """
        try:
            document_id = state.get("document_id")
            storage_path = state.get("storage_path")
            text_extraction_result = state.get("text_extraction_result")
            
            if not document_id or not storage_path:
                raise ValueError("Document ID and storage path are required")
                
            if not text_extraction_result or not text_extraction_result.get("success"):
                raise ValueError("Text extraction must be completed before diagram detection")

            logger.info(
                f"Starting per-page OCR-based diagram detection for document {document_id}",
                extra={"document_id": document_id, "storage_path": storage_path}
            )

            # Load settings and check if diagram detection is enabled
            from app.core.config import get_settings
            settings = get_settings()
            
            if not settings.diagram_detection_enabled:
                logger.info("Diagram detection disabled, skipping")
                state["diagram_processing_result"] = {
                    "success": True,
                    "diagrams": [],
                    "total_diagrams": 0,
                    "diagram_pages": [],
                    "diagram_types": {},
                    "detection_summary": {"skipped_reason": "diagram_detection_disabled"},
                    "processing_timestamp": self._get_current_timestamp()
                }
                return state

            # Initialize OCR service
            await self._initialize_services()

            # Get pages from text extraction result
            pages = text_extraction_result.get("pages", [])
            if not pages:
                logger.warning("No pages found in text extraction result")
                state["diagram_processing_result"] = {
                    "success": True,
                    "diagrams": [],
                    "total_diagrams": 0,
                    "diagram_pages": [],
                    "diagram_types": {},
                    "detection_summary": {"skipped_reason": "no_pages_found"},
                    "processing_timestamp": self._get_current_timestamp()
                }
                return state

            # Apply max_diagram_pages limit for cost control
            max_diagram_pages = getattr(settings, 'max_diagram_pages', 10)
            if len(pages) > max_diagram_pages:
                logger.info(f"Limiting diagram detection to {max_diagram_pages} pages (total: {len(pages)})")
                # Use first N pages for processing
                pages = pages[:max_diagram_pages]

            # Process diagrams per-page with retries
            all_diagrams = await self._process_pages_for_diagrams(
                document_id, storage_path, pages, settings
            )
            
            # Store diagram processing results in state (canonical field)
            state["diagram_processing_result"] = {
                "success": True,
                "diagrams": all_diagrams,
                "total_diagrams": len(all_diagrams),
                "pages_processed": len(pages),
                "diagram_pages": list(set(d.page_number for d in all_diagrams)),
                "diagram_types": {},
                "detection_summary": {
                    "processing_method": "ocr_detection",
                    "pages_analyzed": len(pages),
                    "pages_with_diagrams": len(set(d.page_number for d in all_diagrams))
                },
                "processing_timestamp": self._get_current_timestamp()
            }
            
            # Count diagram types for summary
            for diagram in all_diagrams:
                diagram_type = diagram.type
                if diagram_type not in state["diagram_processing_result"]["diagram_types"]:
                    state["diagram_processing_result"]["diagram_types"][diagram_type] = 0
                state["diagram_processing_result"]["diagram_types"][diagram_type] += 1
            
            # Keep diagram_detection_result for backward compatibility (will be removed later)
            state["diagram_detection_result"] = state["diagram_processing_result"]
            
            logger.info(
                f"Diagram detection completed successfully",
                extra={
                    "document_id": document_id,
                    "diagrams_detected": len(all_diagrams),
                    "pages_processed": len(pages),
                    "diagram_types": [d.type for d in all_diagrams]
                }
            )
            
            return state

        except Exception as e:
            logger.error(
                f"Diagram detection failed: {e}",
                exc_info=True,
                extra={"document_id": state.get("document_id")}
            )
            
            state["error"] = f"Diagram detection failed: {str(e)}"
            state["error_details"] = {
                "node": "detect_diagrams_with_ocr",
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
            
            return state

    def _create_diagram_detection_prompt(self) -> str:
        """
        Create diagram detection prompt based on gemini_client_cli.py
        
        Returns:
            Formatted prompt for diagram detection
        """
        return """Diagram detection only

Goal
- Return ONLY a JSON object with one key: diagram (array)
- Each item: {"type": one of [site_plan, sewer_diagram, service_location_diagram, flood_map, bushfire_map, title_plan, survey_diagram, floor_plan, elevation, unknown], "page": integer}
- Identify all visual elements that correspond to diagrams/images in the document
- Do not include any other keys or textual content

Notes
- Use 'unknown' if unsure
- Page numbers are 1-based
- Only include actual diagrams, plans, maps, and technical drawings
- Exclude text-only pages, headers, footers, and decorative elements"""

    async def _process_pages_for_diagrams(
        self, document_id: str, storage_path: str, pages: List[Dict[str, Any]], settings
    ) -> List[DiagramDetectionItem]:
        """
        Process pages for diagram detection using per-page approach.
        
        Args:
            document_id: Document ID for logging
            storage_path: Path to document in storage  
            pages: List of page extraction results from text extraction
            
        Returns:
            List of detected diagrams with types and page numbers
        """
        all_diagrams = []
        pages_to_process = []
        
        # Filter pages that are candidates for diagram detection
        for page in pages[:settings.max_diagram_pages]:  # Limit to control costs
            page_number = page.get("page_number", 0)
            content_analysis = page.get("content_analysis", {})
            
            # Check if page is a candidate for diagram detection
            has_images = content_analysis.get("has_images", False)
            has_low_text = content_analysis.get("text_length", 0) < 100  # Low text threshold
            has_diagram_keywords = content_analysis.get("has_diagram_keywords", False)
            
            if has_images or has_low_text or has_diagram_keywords:
                pages_to_process.append(page_number)
                logger.info(
                    f"Page {page_number} selected for diagram detection",
                    extra={
                        "document_id": document_id,
                        "has_images": has_images,
                        "has_low_text": has_low_text,
                        "has_diagram_keywords": has_diagram_keywords
                    }
                )
        
        if not pages_to_process:
            logger.info(f"No pages selected for diagram detection for document {document_id}")
            return all_diagrams
        
        # Process each candidate page with retry logic
        for page_number in pages_to_process:
            max_retries = getattr(settings, 'diagram_detection_max_retries', 3)
            retry_delay = 1.0  # Start with 1 second delay
            
            for retry_count in range(max_retries):
                try:
                    page_diagrams = await self._detect_diagrams_for_page(
                        document_id, storage_path, page_number
                    )
                    all_diagrams.extend(page_diagrams)
                    break  # Success, break out of retry loop
                    
                except Exception as e:
                    if retry_count < max_retries - 1:
                        logger.warning(
                            f"Failed to process page {page_number} for diagrams (attempt {retry_count + 1}/{max_retries}): {e}. Retrying in {retry_delay}s",
                            extra={"document_id": document_id, "page_number": page_number, "retry_count": retry_count + 1}
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to process page {page_number} for diagrams after {max_retries} attempts: {e}",
                            extra={"document_id": document_id, "page_number": page_number}
                        )
                        # Don't add diagrams for this page, continue to next page
        
        return all_diagrams

    async def _detect_diagrams_for_page(
        self, document_id: str, storage_path: str, page_number: int
    ) -> List[DiagramDetectionItem]:
        """
        Detect diagrams for a single page using page JPG.
        
        Args:
            document_id: Document ID for logging
            storage_path: Path to document in storage
            page_number: Page number to process (1-based)
            
        Returns:
            List of detected diagrams for this page
        """
        try:
            # Generate page JPG from PDF
            page_jpg_bytes = await self._render_page_to_jpg(storage_path, page_number)
            
            # Call OCR service for diagram detection on this page
            diagram_prompt = self._create_diagram_detection_prompt()
            detection_result = await self._detect_diagrams_with_page_jpg(
                page_jpg_bytes, page_number, diagram_prompt
            )
            
            # Parse response and filter results for this page
            diagram_data = await self._parse_diagram_response(detection_result)
            
            # Filter diagrams to only include this page and update page numbers
            page_diagrams = []
            for diagram in diagram_data.diagram:
                # Update page number to match actual page being processed
                page_diagram = DiagramDetectionItem(
                    type=diagram.type,
                    page=page_number
                )
                page_diagrams.append(page_diagram)
            
            logger.info(
                f"Page {page_number} diagram detection: {len(page_diagrams)} diagrams found",
                extra={
                    "document_id": document_id,
                    "page_number": page_number,
                    "diagram_types": [d.type for d in page_diagrams]
                }
            )
            
            return page_diagrams
            
        except Exception as e:
            logger.error(
                f"Failed to detect diagrams for page {page_number}: {e}",
                extra={"document_id": document_id, "page_number": page_number}
            )
            return []

    async def _render_page_to_jpg(self, storage_path: str, page_number: int) -> bytes:
        """
        Render a specific page from PDF to JPG bytes.
        
        Args:
            storage_path: Path to PDF in storage
            page_number: Page number to render (1-based)
            
        Returns:
            JPG bytes for the page
        """
        try:
            # Read file content from storage
            file_content = await self._read_file_from_storage(storage_path)
            
            # Use PyMuPDF to render page to JPG
            import pymupdf
            
            doc = pymupdf.open(stream=file_content, filetype="pdf")
            page = doc.load_page(page_number - 1)  # PyMuPDF uses 0-based indexing
            
            # Render page to PNG with zoom for better quality
            matrix = pymupdf.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=matrix)
            jpg_bytes = pix.pil_tobytes(format="JPEG")
            
            doc.close()
            return jpg_bytes
            
        except Exception as e:
            logger.error(f"Failed to render page {page_number} to JPG: {e}")
            raise

    async def _detect_diagrams_with_page_jpg(
        self, page_jpg_bytes: bytes, page_number: int, prompt: str
    ) -> Dict[str, Any]:
        """
        Call OCR service for diagram detection using page JPG.
        
        Args:
            page_jpg_bytes: JPG bytes for the page
            page_number: Page number being processed
            prompt: Diagram detection prompt
            
        Returns:
            Raw OCR service response
        """
        try:
            # Use Gemini service directly for diagram detection with custom prompt
            from google.genai.types import Content, Part, GenerateContentConfig
            
            # Create content with page image and custom prompt
            page_content = Part.from_bytes(data=page_jpg_bytes, mime_type="image/jpeg")
            prompt_part = Part.from_text(text=prompt)
            contents = [Content(role="user", parts=[page_content, prompt_part])]
            
            # Configure generation for structured output
            config = GenerateContentConfig(
                temperature=0,
                top_p=1,
                seed=0,
                max_output_tokens=1024,  # Smaller for per-page processing
                safety_settings=[
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                ]
            )
            
            # Call Gemini service
            response = await self.ocr_service.gemini_service.client.agenerate_content(
                contents=contents, config=config
            )
            
            return {
                "content": response.text,
                "candidates": response.candidates,
                "usage_metadata": response.usage_metadata
            }
            
        except Exception as e:
            logger.error(f"OCR service call failed for page {page_number}: {e}", exc_info=True)
            raise

    async def _parse_diagram_response(
        self, ocr_response: Dict[str, Any]
    ) -> DiagramDetectionResponse:
        """
        Parse OCR response using structured output parser.
        
        Args:
            ocr_response: Raw response from OCR service
            
        Returns:
            Parsed and validated diagram detection data
        """
        try:
            # Extract content from OCR response
            content = ocr_response.get("content", ocr_response.get("result", ""))
            
            if not content:
                logger.warning("No content in OCR response, returning empty diagram list")
                return DiagramDetectionResponse(diagram=[])
            
            # Parse using structured parser
            parsing_result = await self.parser.parse(content)
            
            if not parsing_result.success:
                logger.warning(
                    f"Failed to parse diagram response: {parsing_result.error_message}",
                    extra={"raw_content": content[:500]}
                )
                return DiagramDetectionResponse(diagram=[])
            
            return parsing_result.data
            
        except Exception as e:
            logger.error(f"Failed to parse diagram response: {e}", exc_info=True)
            # Return empty result rather than failing the whole workflow
            return DiagramDetectionResponse(diagram=[])

    def _validate_diagram_data(self, diagrams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean diagram detection data.
        
        Args:
            diagrams: Raw diagram data from OCR
            
        Returns:
            Validated diagram data
        """
        validated_diagrams = []
        
        for diagram in diagrams:
            try:
                # Validate diagram type
                diagram_type = diagram.get("type", "unknown")
                if diagram_type not in [dt.value for dt in DiagramType]:
                    logger.warning(f"Invalid diagram type: {diagram_type}, using 'unknown'")
                    diagram_type = "unknown"
                
                # Validate page number
                page_number = diagram.get("page", 1)
                if not isinstance(page_number, int) or page_number < 1:
                    logger.warning(f"Invalid page number: {page_number}, using 1")
                    page_number = 1
                
                validated_diagrams.append({
                    "type": diagram_type,
                    "page": page_number
                })
                
            except Exception as e:
                logger.warning(f"Skipping invalid diagram data: {diagram}, error: {e}")
                continue
        
        return validated_diagrams

    async def _read_file_from_storage(self, storage_path: str) -> bytes:
        """
        Read file content from storage.
        
        Args:
            storage_path: Path to file in storage
            
        Returns:
            File content as bytes
        """
        try:
            # Import storage service
            from app.services.storage.file_storage_service import FileStorageService
            
            storage_service = FileStorageService()
            file_content = await storage_service.read_file(storage_path)
            
            return file_content
            
        except Exception as e:
            logger.error(f"Failed to read file from storage: {storage_path}, error: {e}")
            raise

    def _get_file_type_from_path(self, file_path: str) -> str:
        """
        Get file type from file path extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File type string
        """
        try:
            extension = file_path.lower().split('.')[-1]
            
            # Map extensions to MIME types
            mime_type_mapping = {
                'pdf': 'pdf',
                'png': 'png',
                'jpg': 'jpeg',
                'jpeg': 'jpeg',
                'webp': 'webp',
                'gif': 'gif',
                'bmp': 'bmp',
                'tiff': 'tiff'
            }
            
            return mime_type_mapping.get(extension, 'pdf')
            
        except Exception:
            return 'pdf'  # Default to PDF

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()