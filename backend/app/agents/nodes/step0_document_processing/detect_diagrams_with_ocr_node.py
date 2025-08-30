"""
DetectDiagramsWithOCRNode - Use OCR service to detect diagrams per-page

This node uses Gemini OCR with the PROMPT_DIAGRAMS_ONLY template to detect
diagrams in document pages using individual page JPGs, not the full document.
"""

import asyncio
from typing import Dict, Any, List, Set

from app.agents.nodes.step0_document_processing.base_node import (
    DocumentProcessingNodeBase,
)
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.core.langsmith_config import langsmith_trace
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.prompts.schema.diagram_detection_schema import DiagramDetectionItem
from app.services.visual_artifact_service import VisualArtifactService


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
        # Configuration will be loaded from settings
        self.artifacts_repo = None
        self.visual_artifact_service = None

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
            local_tmp_path = state.get("local_tmp_path")
            text_extraction_result = state.get("text_extraction_result")

            if not document_id or not storage_path:
                raise ValueError("Document ID and storage path are required")

            if not text_extraction_result or not text_extraction_result.success:
                raise ValueError(
                    "Text extraction must be completed before diagram detection"
                )

            self._log_info(
                f"Starting per-page OCR-based diagram detection for document {document_id}",
                document_id=document_id,
                storage_path=storage_path,
                local_tmp_exists=bool(local_tmp_path),
            )

            # Load settings and check if diagram detection is enabled
            from app.core.config import get_settings

            settings = get_settings()

            if not settings.diagram_detection_enabled:
                self._log_info("Diagram detection disabled, skipping")
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
                self._log_warning("No pages found in text extraction result")
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
                self._log_info(
                    f"Limiting diagram detection to {max_diagram_pages} pages (total: {len(pages)})"
                )
                # Use first N pages for processing
                pages = pages[:max_diagram_pages]

            # Check for existing diagram processing results from extract_text_node to avoid duplicate API calls
            existing_diagram_result = state.get("diagram_processing_result")
            existing_processed_pages = set()
            existing_diagrams = []

            if existing_diagram_result and existing_diagram_result.get("success"):
                # Extract pages that were already processed by Gemini OCR
                existing_processed_pages = set(
                    existing_diagram_result.get("pages_processed", [])
                )
                existing_diagrams = existing_diagram_result.get("diagrams", [])

                self._log_info(
                    f"Found existing diagram processing result",
                    extra={
                        "existing_processed_pages": list(existing_processed_pages),
                        "existing_diagrams_count": len(existing_diagrams),
                        "processing_method": existing_diagram_result.get(
                            "detection_summary", {}
                        ).get("processing_method", "unknown"),
                    },
                )

            content_hmac = state.get("content_hmac")
            algorithm_version = state.get("algorithm_version")
            params_fingerprint = state.get("params_fingerprint")

            # Store state for use in JPG persistence
            self._current_state = state

            # Process diagrams per-page with retries
            all_diagrams, pages_to_process = await self._process_pages_for_diagrams(
                document_id,
                storage_path,
                pages,
                settings,
                existing_processed_pages,
            )

            # Merge existing diagrams with newly detected ones and update state
            if existing_diagram_result and existing_diagram_result.get("success"):
                # Combine existing and new diagrams
                combined_diagrams = existing_diagrams + all_diagrams
                combined_processed_pages = existing_processed_pages.union(
                    set(pages_to_process)
                )

                # Update the existing diagram processing result
                existing_diagram_result["diagrams"] = combined_diagrams
                existing_diagram_result["total_diagrams"] = len(combined_diagrams)
                existing_diagram_result["pages_processed"] = list(
                    combined_processed_pages
                )
                existing_diagram_result["diagram_pages"] = list(
                    set(
                        getattr(d, "page", None)
                        for d in combined_diagrams
                        if getattr(d, "page", None) is not None
                    )
                )
                existing_diagram_result["detection_summary"][
                    "processing_method"
                ] = "hybrid_extraction_and_ocr_detection"
                existing_diagram_result["detection_summary"]["pages_analyzed"] = len(
                    combined_processed_pages
                )
                existing_diagram_result["detection_summary"]["pages_with_diagrams"] = (
                    len(
                        set(
                            getattr(d, "page", None)
                            for d in combined_diagrams
                            if getattr(d, "page", None) is not None
                        )
                    )
                )
                existing_diagram_result["processing_timestamp"] = (
                    self._get_current_timestamp()
                )

                # Keep the existing result in state
                state["diagram_processing_result"] = existing_diagram_result

                self._log_info(
                    f"Merged existing and new diagram detection results",
                    extra={
                        "existing_diagrams": len(existing_diagrams),
                        "new_diagrams": len(all_diagrams),
                        "combined_total": len(combined_diagrams),
                        "total_pages_processed": len(combined_processed_pages),
                    },
                )
            else:
                # No existing result, create new one
                state["diagram_processing_result"] = {
                    "success": True,
                    "diagrams": all_diagrams,
                    "total_diagrams": len(all_diagrams),
                    "pages_processed": list(range(1, len(pages) + 1)),
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

            for diagram in combined_diagrams:
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

            self._log_info(
                f"Diagram detection completed successfully",
                document_id=document_id,
                diagrams_detected=len(combined_diagrams),
                pages_processed=combined_processed_pages,
                diagram_types=[d.type for d in combined_diagrams],
            )

            return state

        except Exception as e:
            self._log_error(
                f"Diagram detection failed: {e}",
                exc_info=True,
                document_id=state.get("document_id"),
            )

            state["error"] = f"Diagram detection failed: {str(e)}"
            state["error_details"] = {
                "node": "detect_diagrams_with_ocr",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

            return state

    async def _process_pages_for_diagrams(
        self,
        document_id: str,
        storage_path: str,
        pages: List[Dict[str, Any]],
        settings,
        existing_processed_pages: Set[int],
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
        all_diagrams: List[DiagramDetectionItem] = []
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
                # Check if this page was already processed by Gemini OCR in extract_text_node
                if page_number in existing_processed_pages:
                    # Page was processed but no diagram found, still skip OCR
                    self._log_info(
                        f"Skipping OCR for page {page_number} - already processed by Gemini OCR",
                        document_id=document_id,
                        reason="existing_gemini_ocr_no_diagrams",
                    )
                else:
                    pages_to_process.append(page_number)
                    self._log_info(
                        f"Page {page_number} selected for diagram detection",
                        document_id=document_id,
                        has_diagrams_flag=has_diagrams_flag,
                        has_low_text=has_low_text,
                        has_diagram_keywords=has_diagram_keywords,
                    )

        if not pages_to_process:
            self._log_info(
                f"No pages selected for diagram detection for document {document_id}"
            )
            return all_diagrams, pages_to_process

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
                        self._log_warning(
                            f"Failed to process page {page_number} for diagrams (attempt {retry_count + 1}/{max_retries}): {e}. Retrying in {retry_delay}s",
                            document_id=document_id,
                            page_number=page_number,
                            retry_count=retry_count + 1,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self._log_error(
                            f"Failed to process page {page_number} for diagrams after {max_retries} attempts: {e}",
                            document_id=document_id,
                            page_number=page_number,
                        )
                        # Don't add diagrams for this page, continue to next page

        return all_diagrams, pages_to_process

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

            # Use shared Gemini OCR service with PromptManager to detect diagram for this page
            # Reuse the same structured method as text OCR, focusing the analysis on diagram detection
            state = getattr(self, "_current_state", {}) or {}
            llm_result = await self.ocr_service.extract_text_diagram_insight(
                file_content=page_jpg_bytes,
                file_type="jpg",
                filename=f"page_{page_number}.jpg",
                analysis_focus="diagram_detection",
                australian_state=state.get("australian_state"),
                contract_type=state.get("contract_type"),
                document_type=state.get("document_type"),
            )

            page_diagrams = []
            # Diagrams are returned directly as a list of DiagramType enums
            diagrams = getattr(llm_result, "diagrams", None) or []
            if diagrams:
                for d in diagrams:
                    diagram_type_value = (
                        getattr(d, "value", None) or str(d) or "unknown"
                    )
                    page_diagrams.append(
                        DiagramDetectionItem(type=diagram_type_value, page=page_number)
                    )

            self._log_info(
                f"Page {page_number} diagram detection: {len(page_diagrams)} diagrams found",
                document_id=document_id,
                page_number=page_number,
                diagram_types=[d.type for d in page_diagrams],
            )

            # Persist each detected diagram as individual visual artifacts to enable reuse
            try:
                # Persist each diagram individually
                for i, diagram in enumerate(page_diagrams):
                    await self._persist_diagram(
                        page_jpg_bytes, page_number, diagram, i + 1
                    )

                self._log_info(
                    f"Persisted {len(page_diagrams)} individual diagrams for page {page_number}",
                    page=page_number,
                )
            except Exception as persist_err:
                self._log_warning(
                    f"Failed to persist OCR diagram artifacts for page {page_number}: {persist_err}"
                )

            return page_diagrams

        except Exception as e:
            self._log_error(
                f"Failed to detect diagrams for page {page_number}: {e}",
                document_id=document_id,
                page_number=page_number,
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
            self._log_error(f"Failed to render page {page_number} to JPG: {e}")
            raise

    async def _read_file_from_storage(self, storage_path: str) -> bytes:
        """
        Read file content from storage.

        Args:
            storage_path: Path to file in storage

        Returns:
            File content as bytes
        """
        try:
            # Prefer local tmp path if present in state to avoid re-downloading
            try:
                state = getattr(self, "_current_state", {}) or {}
                local_tmp_path = state.get("local_tmp_path")
                if local_tmp_path:
                    import os

                    if os.path.exists(local_tmp_path):
                        with open(local_tmp_path, "rb") as f:
                            data = f.read()
                        return data
            except Exception:
                pass

            # Prefer authenticated user client for binary download from configured bucket
            try:
                user_client = await self.get_user_client()
                file_content = await user_client.download_file(
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
            self._log_error(
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

    async def _persist_diagram(
        self,
        page_jpg_bytes: bytes,
        page_number: int,
        diagram: DiagramDetectionItem,
        diagram_index: int,
    ):
        """
        Persist an individual detected diagram as an artifact.

        Args:
            page_jpg_bytes: Rendered JPG bytes for the page
            page_number: Page number (1-based)
            diagram: The individual diagram detection item
            diagram_index: Index of the diagram on the page (1-based)
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
                    # Initialize visual artifact service if needed
                    if not self.visual_artifact_service:
                        from app.utils.storage_utils import ArtifactStorageService
                        from app.services.repositories.artifacts_repository import (
                            ArtifactsRepository,
                        )

                        if not self.artifacts_repo:
                            self.artifacts_repo = ArtifactsRepository()

                        self.visual_artifact_service = VisualArtifactService(
                            storage_service=ArtifactStorageService(),
                            artifacts_repo=self.artifacts_repo,
                        )

                    # Create unique key for this specific diagram
                    diagram_key = (
                        f"page_{page_number}_diagram_{diagram_index}_{diagram.type}"
                    )

                    # Prepare diagram-specific metadata
                    diagram_meta = {
                        "detection_method": "ocr_detection",
                        "source": "gemini",
                        "diagram_type": diagram.type,
                        "diagram_index": diagram_index,
                        "page_number": page_number,
                        "rendered_for": "ocr_detection",
                        "zoom": "2.0x",
                    }

                    # Use visual artifact service to store the diagram
                    result = await self.visual_artifact_service.store_visual_artifact(
                        image_bytes=page_jpg_bytes,
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page_number,
                        diagram_key=diagram_key,
                        artifact_type="diagram",
                        image_metadata={
                            "format": "jpeg",
                            "quality": "high",
                            "dpi": "144",
                        },
                        diagram_meta=diagram_meta,
                    )

                    if result.cache_hit:
                        self._log_info(f"Reused cached diagram artifact: {diagram_key}")
                    else:
                        self._log_info(
                            f"Persisted diagram {diagram_index} ({diagram.type}) from page {page_number}: {diagram_key}"
                        )

        except Exception as e:
            # Don't fail OCR detection if individual diagram persistence fails
            self._log_warning(
                f"Failed to persist diagram {diagram_index} from page {page_number}: {e}"
            )

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
