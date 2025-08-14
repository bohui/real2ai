"""
DetectDiagramsWithOCRNode - Use OCR service to detect diagrams per-page

This node uses Gemini OCR with the PROMPT_DIAGRAMS_ONLY template to detect
diagrams in document pages using individual page JPGs, not the full document.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from app.agents.nodes.document_processing_subflow.base_node import (
    DocumentProcessingNodeBase,
)
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.core.langsmith_config import langsmith_trace
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.core.prompts.output_parser import create_parser
from app.prompts.schema.diagram_detection_schema import (
    DiagramDetectionResponse,
    DiagramDetectionItem,
)
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
    async def execute(
        self, state: "DocumentProcessingState"
    ) -> "DocumentProcessingState":
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

            if not text_extraction_result or not text_extraction_result.success:
                raise ValueError(
                    "Text extraction must be completed before diagram detection"
                )

            logger.info(
                f"Starting per-page OCR-based diagram detection for document {document_id}",
                extra={"document_id": document_id, "storage_path": storage_path},
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
                    "detection_summary": {
                        "skipped_reason": "diagram_detection_disabled"
                    },
                    "processing_timestamp": self._get_current_timestamp(),
                }
                return state

            # Initialize OCR service
            await self._initialize_services()

            # Get pages from text extraction result
            pages = text_extraction_result.pages or []
            if not pages:
                logger.warning("No pages found in text extraction result")
                state["diagram_processing_result"] = {
                    "success": True,
                    "diagrams": [],
                    "total_diagrams": 0,
                    "diagram_pages": [],
                    "diagram_types": {},
                    "detection_summary": {"skipped_reason": "no_pages_found"},
                    "processing_timestamp": self._get_current_timestamp(),
                }
                return state

            # Apply max_diagram_pages limit for cost control
            max_diagram_pages = getattr(settings, "max_diagram_pages", 10)
            if len(pages) > max_diagram_pages:
                logger.info(
                    f"Limiting diagram detection to {max_diagram_pages} pages (total: {len(pages)})"
                )
                # Use first N pages for processing
                pages = pages[:max_diagram_pages]

            # Store state for use in JPG persistence
            self._current_state = state

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
                "diagram_pages": list(
                    set(
                        getattr(d, "page", None)
                        for d in all_diagrams
                        if getattr(d, "page", None) is not None
                    )
                ),
                "diagram_types": {},
                "detection_summary": {
                    "processing_method": "ocr_detection",
                    "pages_analyzed": len(pages),
                    "pages_with_diagrams": len(
                        set(
                            getattr(d, "page", None)
                            for d in all_diagrams
                            if getattr(d, "page", None) is not None
                        )
                    ),
                },
                "processing_timestamp": self._get_current_timestamp(),
            }

            # Count diagram types for summary
            for diagram in all_diagrams:
                diagram_type = diagram.type
                if (
                    diagram_type
                    not in state["diagram_processing_result"]["diagram_types"]
                ):
                    state["diagram_processing_result"]["diagram_types"][
                        diagram_type
                    ] = 0
                state["diagram_processing_result"]["diagram_types"][diagram_type] += 1

            # Clean up state reference
            if hasattr(self, "_current_state"):
                delattr(self, "_current_state")

            logger.info(
                f"Diagram detection completed successfully",
                extra={
                    "document_id": document_id,
                    "diagrams_detected": len(all_diagrams),
                    "pages_processed": len(pages),
                    "diagram_types": [d.type for d in all_diagrams],
                },
            )

            return state

        except Exception as e:
            logger.error(
                f"Diagram detection failed: {e}",
                exc_info=True,
                extra={"document_id": state.get("document_id")},
            )

            state["error"] = f"Diagram detection failed: {str(e)}"
            state["error_details"] = {
                "node": "detect_diagrams_with_ocr",
                "error_type": type(e).__name__,
                "error_message": str(e),
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

        # Filter pages that are candidates for diagram detection using actual schema fields
        max_diagram_pages = getattr(settings, "max_diagram_pages", 10)
        for page in pages[:max_diagram_pages]:  # Limit to control costs
            # `page` is a SchemaBase-derived model, so .get works via getattr
            page_number = page.get("page_number", 0)
            text_length = page.get("text_length", 0)
            content_analysis = page.get("content_analysis")

            has_low_text = text_length < 100
            has_diagrams_flag = False
            has_diagram_keywords = False

            if content_analysis is not None:
                layout = content_analysis.get("layout_features")
                has_diagrams_flag = (
                    bool(layout and getattr(layout, "has_diagrams", False))
                    or content_analysis.get("primary_type") == "diagram"
                    or ("diagram" in (content_analysis.get("content_types") or []))
                )
                # We don't have explicit "has_diagram_keywords" on schema; infer from primary/content_types
                has_diagram_keywords = has_diagrams_flag

            if has_diagrams_flag or has_low_text or has_diagram_keywords:
                pages_to_process.append(page_number)
                logger.info(
                    f"Page {page_number} selected for diagram detection",
                    extra={
                        "document_id": document_id,
                        "has_diagrams_flag": has_diagrams_flag,
                        "has_low_text": has_low_text,
                        "has_diagram_keywords": has_diagram_keywords,
                    },
                )

        if not pages_to_process:
            logger.info(
                f"No pages selected for diagram detection for document {document_id}"
            )
            return all_diagrams

        # Process each candidate page with retry logic
        for page_number in pages_to_process:
            max_retries = getattr(settings, "diagram_detection_max_retries", 3)
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
                            extra={
                                "document_id": document_id,
                                "page_number": page_number,
                                "retry_count": retry_count + 1,
                            },
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to process page {page_number} for diagrams after {max_retries} attempts: {e}",
                            extra={
                                "document_id": document_id,
                                "page_number": page_number,
                            },
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

            # Persist rendered JPG as artifact for reuse (if we have artifact metadata in state)
            await self._persist_page_jpg_if_needed(page_jpg_bytes, page_number)

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
                page_diagram = DiagramDetectionItem(type=diagram.type, page=page_number)
                page_diagrams.append(page_diagram)

            logger.info(
                f"Page {page_number} diagram detection: {len(page_diagrams)} diagrams found",
                extra={
                    "document_id": document_id,
                    "page_number": page_number,
                    "diagram_types": [d.type for d in page_diagrams],
                },
            )

            return page_diagrams

        except Exception as e:
            logger.error(
                f"Failed to detect diagrams for page {page_number}: {e}",
                extra={"document_id": document_id, "page_number": page_number},
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

            # Use PyMuPDF (fitz) to render page to JPG; fallback module name support
            try:
                import fitz  # type: ignore
            except ImportError:  # pragma: no cover - environment specific
                import pymupdf as fitz  # type: ignore

            doc = fitz.open(stream=file_content, filetype="pdf")
            page = doc.load_page(page_number - 1)  # fitz uses 0-based indexing

            # Render page to PNG with zoom for better quality
            matrix = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
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
                ],
            )

            # Call Gemini service
            response = await self.ocr_service.gemini_service.client.agenerate_content(
                contents=contents, config=config
            )

            return {
                "content": response.text,
                "candidates": response.candidates,
                "usage_metadata": response.usage_metadata,
            }

        except Exception as e:
            logger.error(
                f"OCR service call failed for page {page_number}: {e}", exc_info=True
            )
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
                logger.warning(
                    "No content in OCR response, returning empty diagram list"
                )
                return DiagramDetectionResponse(diagram=[])

            # Parse using structured parser
            parsing_result = await self.parser.parse(content)

            if not parsing_result.success:
                logger.warning(
                    f"Failed to parse diagram response: {parsing_result.error_message}",
                    extra={"raw_content": content[:500]},
                )
                return DiagramDetectionResponse(diagram=[])

            return parsing_result.data

        except Exception as e:
            logger.error(f"Failed to parse diagram response: {e}", exc_info=True)
            # Return empty result rather than failing the whole workflow
            return DiagramDetectionResponse(diagram=[])

    def _validate_diagram_data(
        self, diagrams: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
                    logger.warning(
                        f"Invalid diagram type: {diagram_type}, using 'unknown'"
                    )
                    diagram_type = "unknown"

                # Validate page number
                page_number = diagram.get("page", 1)
                if not isinstance(page_number, int) or page_number < 1:
                    logger.warning(f"Invalid page number: {page_number}, using 1")
                    page_number = 1

                validated_diagrams.append({"type": diagram_type, "page": page_number})

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
            # Prefer authenticated user client for binary download from configured bucket
            try:
                user_client = await self.get_user_client()
                file_content = await user_client.storage.download(
                    bucket="documents", path=storage_path
                )
                if not isinstance(file_content, (bytes, bytearray)):
                    # Some clients may return str; convert to bytes
                    file_content = bytes(file_content)
            except Exception as client_err:
                # Fallback: if storage_path is a supabase URI to a text blob (unlikely for PDFs), try ArtifactStorageService
                from app.utils.storage_utils import ArtifactStorageService

                storage_service = ArtifactStorageService()
                if isinstance(storage_path, str) and storage_path.startswith(
                    "supabase://"
                ):
                    text = await storage_service.download_text_blob(storage_path)
                    file_content = text.encode("utf-8")
                else:
                    raise RuntimeError(
                        f"Failed to download file content for diagram OCR: {client_err}"
                    )

            return file_content

        except Exception as e:
            logger.error(
                f"Failed to read file from storage: {storage_path}, error: {e}"
            )
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
            extension = file_path.lower().split(".")[-1]

            # Map extensions to MIME types
            mime_type_mapping = {
                "pdf": "pdf",
                "png": "png",
                "jpg": "jpeg",
                "jpeg": "jpeg",
                "webp": "webp",
                "gif": "gif",
                "bmp": "bmp",
                "tiff": "tiff",
            }

            return mime_type_mapping.get(extension, "pdf")

        except Exception:
            return "pdf"  # Default to PDF

    async def _persist_page_jpg_if_needed(
        self, page_jpg_bytes: bytes, page_number: int
    ):
        """
        Persist rendered page JPG as artifact to avoid recomputation on re-runs.

        Args:
            page_jpg_bytes: Rendered JPG bytes
            page_number: Page number (1-based)
        """
        try:
            # Get state from current context (if available)
            if hasattr(self, "_current_state"):
                state = self._current_state
                content_hmac = state.get("content_hmac")
                algorithm_version = state.get("algorithm_version")
                params_fingerprint = state.get("params_fingerprint")

                if (
                    content_hmac
                    and algorithm_version is not None
                    and params_fingerprint
                ):
                    # Upload JPG to storage
                    from app.utils.storage_utils import ArtifactStorageService

                    storage_service = ArtifactStorageService()

                    # Generate JPG storage path
                    jpg_filename = f"page_{page_number}.jpg"
                    jpg_uri = await storage_service.upload_page_jpg(
                        content_hmac,
                        algorithm_version,
                        params_fingerprint,
                        page_number,
                        page_jpg_bytes,
                    )

                    # Calculate SHA256 for integrity
                    import hashlib

                    jpg_sha256 = hashlib.sha256(page_jpg_bytes).hexdigest()

                    # Persist as unified diagram artifact with artifact_type='image_jpg'
                    if not hasattr(self, "artifacts_repo") or not self.artifacts_repo:
                        from app.services.repositories.artifacts_repository import (
                            ArtifactsRepository,
                        )

                        self.artifacts_repo = ArtifactsRepository()

                    diagram_key = f"page_jpg_{page_number}"

                    await self.artifacts_repo.insert_diagram_artifact(
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page_number,
                        diagram_key=diagram_key,
                        diagram_meta={"rendered_for": "ocr_detection", "zoom": "2.0x"},
                        artifact_type="image_jpg",
                        image_uri=jpg_uri,
                        image_sha256=jpg_sha256,
                        image_metadata={
                            "format": "jpeg",
                            "quality": "high",
                            "dpi": "144",
                        },
                    )

                    self._log_info(
                        f"Persisted page {page_number} JPG as artifact: {diagram_key}"
                    )

        except Exception as e:
            # Don't fail OCR detection if JPG persistence fails
            self._log_warning(f"Failed to persist page {page_number} JPG: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
