"""
ExtractTextNode - Extract text with comprehensive analysis

This node migrates the _extract_text_with_comprehensive_analysis method from DocumentService
into a dedicated node for the document processing subflow.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.schema.document import (
    TextExtractionResult,
    PageExtraction,
    ContentAnalysis,
    LayoutFeatures,
    QualityIndicators,
)
from .base_node import DocumentProcessingNodeBase


class ExtractTextNode(DocumentProcessingNodeBase):
    """
    Node responsible for extracting text from documents using comprehensive analysis.

    This node:
    1. Downloads document from storage using user context
    2. Extracts text based on file type (PDF, DOCX, images)
    3. Performs quality assessment and diagram detection
    4. Uses LLM-enhanced OCR when enabled and beneficial

    State Updates:
    - text_extraction_result: Complete TextExtractionResult with pages and analysis
    """

    def __init__(self, use_llm: bool = True):
        super().__init__("extract_text")
        self.use_llm = use_llm
        self.storage_bucket = "documents"
        # Heuristics / thresholds
        self._min_text_len_for_ocr = 60
        self._ocr_zoom = 2.0
        self._diagram_keywords = [
            "diagram",
            "plan",
            "map",
            "layout",
            "site plan",
            "floor plan",
            "survey",
            "boundary",
            "title plan",
            "sewer",
            "sewerage",
            "utilities",
            "service",
            "flood",
            "bushfire",
            "drainage",
            "contour",
            "easement",
            "zoning",
            "cadastral",
        ]

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Extract text from document with comprehensive analysis.

        Args:
            state: Current processing state with document metadata

        Returns:
            Updated state with text_extraction_result or error
        """
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            # Validate required state
            document_id = state.get("document_id")
            storage_path = state.get("storage_path")
            file_type = state.get("file_type")

            if not all([document_id, storage_path, file_type]):
                return self._handle_error(
                    state,
                    ValueError("Missing required document metadata"),
                    "Document metadata incomplete for text extraction",
                    {
                        "has_document_id": bool(document_id),
                        "has_storage_path": bool(storage_path),
                        "has_file_type": bool(file_type),
                    },
                )

            self._log_info(
                f"Starting text extraction for document {document_id}",
                extra={
                    "storage_path": storage_path,
                    "file_type": file_type,
                    "use_llm": self.use_llm,
                },
            )

            # Get user-authenticated client for file operations
            user_client = await self.get_user_client()

            # Extract text using comprehensive analysis method
            text_extraction_result = (
                await self._extract_text_with_comprehensive_analysis(
                    user_client=user_client,
                    document_id=document_id,
                    storage_path=storage_path,
                    file_type=file_type,
                )
            )

            # Validate extraction result
            if not text_extraction_result or not text_extraction_result.success:
                error_msg = (
                    text_extraction_result.error
                    if text_extraction_result
                    else "Text extraction failed"
                )
                return self._handle_error(
                    state,
                    ValueError(error_msg),
                    f"Text extraction failed: {error_msg}",
                    {
                        "document_id": document_id,
                        "storage_path": storage_path,
                        "file_type": file_type,
                        "extraction_attempted": True,
                        "extraction_success": False,
                    },
                )

            # Validate extracted content
            full_text = text_extraction_result.full_text or ""
            if len(full_text.strip()) < 100:
                return self._handle_error(
                    state,
                    ValueError("Insufficient text content"),
                    "Insufficient text content extracted from document",
                    {
                        "document_id": document_id,
                        "character_count": len(full_text),
                        "extraction_method": text_extraction_result.extraction_methods,
                        "total_pages": text_extraction_result.total_pages,
                    },
                )

            # Update state with extraction result
            updated_state = state.copy()
            updated_state["text_extraction_result"] = text_extraction_result

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Successfully extracted text from document {document_id}",
                extra={
                    "document_id": document_id,
                    "character_count": len(full_text),
                    "total_pages": text_extraction_result.total_pages,
                    "extraction_methods": text_extraction_result.extraction_methods,
                    "overall_confidence": text_extraction_result.overall_confidence,
                    "total_word_count": text_extraction_result.total_word_count,
                    "use_llm": self.use_llm,
                    "duration_seconds": duration,
                },
            )

            return updated_state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Text extraction failed: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "storage_path": state.get("storage_path"),
                    "file_type": state.get("file_type"),
                    "use_llm": self.use_llm,
                    "operation": "text_extraction",
                },
            )

    async def _extract_text_with_comprehensive_analysis(
        self, user_client, document_id: str, storage_path: str, file_type: str
    ) -> TextExtractionResult:
        """
        Extract text from document with comprehensive analysis.

        This method downloads the file from storage and extracts text based on file type.
        It's a simplified version that delegates to utility functions to avoid
        the full DocumentService dependency.

        Args:
            user_client: Authenticated user client
            document_id: Document ID for logging
            storage_path: Path to file in storage
            file_type: MIME type of the file

        Returns:
            TextExtractionResult with extracted text and analysis
        """
        try:
            # Download file content from storage
            try:
                file_content = await user_client.storage.download(
                    bucket="documents", path=storage_path
                )
            except Exception as e:
                return TextExtractionResult(
                    success=False,
                    error=f"Failed to download file from storage: {str(e)}",
                    full_text="",
                    total_pages=0,
                    pages=[],
                    extraction_methods=[],
                    overall_confidence=0.0,
                    processing_time=0.0,
                )
            # Route by file type
            if file_type == "application/pdf":
                return await self._extract_pdf_text_hybrid(file_content)
            elif file_type.startswith("image/"):
                text, method = await self._extract_image_text_basic(file_content)
                page = PageExtraction(
                    page_number=1,
                    text_content=text,
                    text_length=len(text),
                    word_count=len(text.split()) if text else 0,
                    extraction_method=method,
                    confidence=0.8 if text else 0.0,
                    content_analysis=self._make_page_analysis(text, has_image=True),
                )
                return TextExtractionResult(
                    success=True,
                    full_text=text,
                    total_pages=1,
                    pages=[page],
                    extraction_methods=[method],
                    overall_confidence=page.confidence,
                    processing_time=1.0,
                )
            elif file_type in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                text, method = await self._extract_docx_text_basic(file_content)
                page = PageExtraction(
                    page_number=1,
                    text_content=text,
                    text_length=len(text),
                    word_count=len(text.split()) if text else 0,
                    extraction_method=method,
                    confidence=0.8 if text else 0.0,
                    content_analysis=self._make_page_analysis(text),
                )
                return TextExtractionResult(
                    success=True,
                    full_text=text,
                    total_pages=1,
                    pages=[page],
                    extraction_methods=[method],
                    overall_confidence=page.confidence,
                    processing_time=1.0,
                )
            else:
                return TextExtractionResult(
                    success=False,
                    error=f"Unsupported file type: {file_type}",
                    full_text="",
                    total_pages=0,
                    pages=[],
                    extraction_methods=[],
                    overall_confidence=0.0,
                    processing_time=0.0,
                )

        except Exception as e:
            self._log_warning(f"Text extraction failed for document {document_id}: {e}")
            return TextExtractionResult(
                success=False,
                error=str(e),
                full_text="",
                total_pages=0,
                pages=[],
                extraction_methods=[],
                overall_confidence=0.0,
                processing_time=0.0,
            )

    async def _extract_pdf_text_basic(self, file_content: bytes) -> tuple[str, str]:
        """Basic PDF text extraction."""
        try:
            # Try PyMuPDF first
            try:
                import pymupdf

                doc = pymupdf.open(stream=file_content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text, "pdf_pymupdf"
            except ImportError:
                pass

            # Fallback to pypdf
            try:
                import pypdf
                from io import BytesIO

                reader = pypdf.PdfReader(BytesIO(file_content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text, "pdf_pypdf"
            except ImportError:
                pass

            return "", "pdf_unavailable"

        except Exception as e:
            self._log_warning(f"PDF extraction failed: {e}")
            return "", "pdf_failed"

    async def _extract_pdf_text_hybrid(
        self, file_content: bytes
    ) -> TextExtractionResult:
        """Hybrid PDF extraction: PyMuPDF first, selective OCR/VLM per page."""
        try:
            import pymupdf
            from io import BytesIO

            # Lazy import to avoid hard dependency if not used
            gemini_service = None
            if self.use_llm:
                try:
                    from app.services.ai.gemini_ocr_service import GeminiOCRService

                    gemini_service = GeminiOCRService()
                    await gemini_service.initialize()
                except Exception as e:
                    self._log_warning(
                        f"Failed to initialize GeminiOCRService, continuing without VLM: {e}"
                    )
                    gemini_service = None

            doc = pymupdf.open(stream=file_content, filetype="pdf")
            pages: List[PageExtraction] = []
            extraction_methods: List[str] = []
            full_text_parts: List[str] = []

            for idx in range(len(doc)):
                page = doc.load_page(idx)
                raw_text = page.get_text() or ""
                method = "pymupdf"
                text_to_use = raw_text

                # Heuristic flags
                is_low_text = len(raw_text.strip()) < self._min_text_len_for_ocr
                has_images = bool(page.get_images())
                has_diagram_kw = self._has_diagram_keywords(raw_text)

                # Selective LLM OCR for diagram/low-text pages
                if (
                    self.use_llm
                    and (is_low_text or has_images or has_diagram_kw)
                    and gemini_service
                ):
                    try:
                        # Render page image at higher DPI
                        png_bytes = self._render_page_png(page, zoom=self._ocr_zoom)
                        llm_result = await gemini_service.extract_text_diagram_insight(
                            file_content=png_bytes,
                            file_type="png",
                            filename=f"page_{idx+1}.png",
                            analysis_focus="diagram_detection",
                        )
                        llm_text = (llm_result or {}).get("text", "")
                        if len(llm_text.strip()) > len(raw_text.strip()):
                            text_to_use = llm_text
                            method = "gemini_ocr"
                        # If LLM indicated diagram, mark later in analysis
                        has_images = has_images or bool(
                            (llm_result or {}).get("diagram_hint", {}).get("is_diagram")
                        )
                        if (
                            (llm_result or {})
                            .get("diagram_hint", {})
                            .get("diagram_type")
                        ):
                            # Attach as hint via analysis
                            pass
                    except Exception as e:
                        self._log_warning(
                            f"Gemini OCR failed on page {idx+1}, using native text: {e}"
                        )

                page_analysis = self._make_page_analysis(
                    text_to_use, has_image=has_images, has_diagram_kw=has_diagram_kw
                )

                page_extraction = PageExtraction(
                    page_number=idx + 1,
                    text_content=text_to_use,
                    text_length=len(text_to_use),
                    word_count=len(text_to_use.split()) if text_to_use else 0,
                    extraction_method=method,
                    confidence=self._estimate_confidence(text_to_use),
                    content_analysis=page_analysis,
                )

                pages.append(page_extraction)
                full_text_parts.append(f"\n--- Page {idx + 1} ---\n{text_to_use}")
                if method not in extraction_methods:
                    extraction_methods.append(method)

            doc.close()

            full_text = "".join(full_text_parts)
            overall_conf = (
                sum(p.confidence for p in pages) / len(pages) if pages else 0.0
            )
            total_words = sum(p.word_count for p in pages)

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                pages=pages,
                total_pages=len(pages),
                extraction_methods=extraction_methods,
                total_word_count=total_words,
                overall_confidence=overall_conf,
            )
        except Exception as e:
            self._log_warning(f"Hybrid PDF extraction failed: {e}")
            return TextExtractionResult(
                success=False,
                error=str(e),
                full_text="",
                pages=[],
                extraction_methods=[],
                overall_confidence=0.0,
                total_pages=0,
                total_word_count=0,
            )

    async def _extract_image_text_basic(self, file_content: bytes) -> tuple[str, str]:
        """Basic OCR text extraction from images."""
        try:
            if self.use_llm:
                try:
                    from app.services.ai.gemini_ocr_service import GeminiOCRService

                    service = GeminiOCRService()
                    await service.initialize()
                    result = await service.extract_text_diagram_insight(
                        file_content=file_content,
                        file_type="png",  # treat as image; service just needs a valid image type
                        filename="image_page.png",
                        analysis_focus="ocr",
                    )
                    text = (result or {}).get("text", "")
                    return text, "ocr_gemini"
                except Exception as e:
                    self._log_warning(f"LLM OCR unavailable, falling back: {e}")
                    # Fall through to tesseract
            else:
                # Try basic Tesseract OCR
                try:
                    import pytesseract
                    from PIL import Image
                    from io import BytesIO

                    image = Image.open(BytesIO(file_content))
                    text = pytesseract.image_to_string(image)
                    return text, "ocr_tesseract"
                except ImportError:
                    return "", "ocr_unavailable"

        except Exception as e:
            self._log_warning(f"Image OCR failed: {e}")
            return "", "ocr_failed"

    async def _extract_docx_text_basic(self, file_content: bytes) -> tuple[str, str]:
        """Basic DOCX text extraction."""
        try:
            from docx import Document
            from io import BytesIO

            doc = Document(BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text, "docx_python_docx"

        except ImportError:
            return "", "docx_unavailable"
        except Exception as e:
            self._log_warning(f"DOCX extraction failed: {e}")
            return "", "docx_failed"

    def _render_page_png(self, page, zoom: float = 2.0) -> bytes:
        """Render a PyMuPDF page to PNG bytes with a zoom factor."""
        try:
            import pymupdf

            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            return pix.pil_tobytes(format="PNG")
        except Exception:
            # Fallback to default rendering
            pix = page.get_pixmap()
            return pix.pil_tobytes(format="PNG")

    def _has_diagram_keywords(self, text: str) -> bool:
        if not text:
            return False
        lower = text.lower()
        return any(kw in lower for kw in self._diagram_keywords)

    def _make_page_analysis(
        self, text: str, has_image: bool = False, has_diagram_kw: bool = False
    ) -> ContentAnalysis:
        layout = LayoutFeatures(
            has_header=False,
            has_footer=False,
            has_signatures=False,
            has_diagrams=bool(has_image or has_diagram_kw),
            has_tables=False,
        )
        quality = QualityIndicators(
            structure_score=self._estimate_structure_score(text),
            readability_score=self._estimate_readability(text),
        )
        content_types: List[str] = []
        if text and len(text.strip()) > 0:
            content_types.append("text")
        if layout.has_diagrams:
            content_types.append("diagram")
        primary = (
            "diagram"
            if layout.has_diagrams and not text
            else ("text" if text else "unknown")
        )
        return ContentAnalysis(
            content_types=content_types,
            primary_type=primary,
            layout_features=layout,
            quality_indicators=quality,
        )

    def _estimate_confidence(self, text: str) -> float:
        if not text or len(text.strip()) == 0:
            return 0.0
        # Simple heuristic: longer and cleaner text -> higher confidence
        base = 0.6 if len(text) < 50 else 0.75 if len(text) < 200 else 0.85
        penalty = self._noise_penalty(text)
        return max(0.0, min(1.0, base - penalty))

    def _estimate_structure_score(self, text: str) -> float:
        if not text:
            return 0.0
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return 0.0
        avg_len = sum(len(ln) for ln in lines) / len(lines)
        return max(0.0, min(1.0, avg_len / 80.0))

    def _estimate_readability(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.split()
        if not words:
            return 0.0
        avg = sum(len(w.strip(".,!?:;()")) for w in words) / len(words)
        # Optimal around 5 characters
        return max(0.0, min(1.0, 1.0 - abs(avg - 5.0) / 10.0))

    def _noise_penalty(self, text: str) -> float:
        import re

        total = len(text)
        if total == 0:
            return 0.4
        specials = len(re.findall(r"[^\w\s.,!?:;()\-]", text)) / total
        singles = len([w for w in text.split() if len(w) == 1 and w.isalpha()])
        single_ratio = singles / max(1, len(text.split()))
        return min(0.4, specials * 0.8 + single_ratio * 0.6)
