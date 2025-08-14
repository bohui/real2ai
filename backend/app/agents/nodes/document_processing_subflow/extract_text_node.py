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
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.content_utils import compute_content_hmac, compute_params_fingerprint
from app.utils.storage_utils import ArtifactStorageService
from app.core.config import get_settings


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
        self.artifacts_repo = None
        self.storage_service = None
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

    async def initialize(self):
        """Initialize artifacts repository and storage service"""
        if not self.artifacts_repo:
            self.artifacts_repo = ArtifactsRepository()
        if not self.storage_service:
            # Use 'documents' bucket to match application configuration
            self.storage_service = ArtifactStorageService(bucket_name="documents")

    async def cleanup(self):
        """Clean up artifacts repository connection"""
        if self.artifacts_repo:
            self.artifacts_repo = None
        # Storage service doesn't need cleanup

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Extract text from document with comprehensive analysis and artifact caching.

        This method implements the idempotent artifact lookup and storage pattern:
        1. Compute content HMAC and parameters fingerprint
        2. Look up existing text extraction artifact
        3. If found, reuse artifact; if not found, compute and store artifact
        4. Hydrate state with artifact IDs and metrics

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
            content_hmac = state.get("content_hmac")

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

            # Initialize artifacts repository if needed
            await self.initialize()

            self._log_info(
                f"Starting text extraction for document {document_id}",
                extra={
                    "storage_path": storage_path,
                    "file_type": file_type,
                    "use_llm": self.use_llm,
                    "has_content_hmac": bool(content_hmac),
                },
            )

            # Get user-authenticated client for file operations
            user_client = await self.get_user_client()

            # Download file content to compute HMAC if not provided
            file_content = None
            if not content_hmac:
                try:
                    # Use client wrapper for storage download
                    file_content = await user_client.download_file(
                        bucket=self.storage_bucket, path=storage_path
                    )
                    content_hmac = compute_content_hmac(file_content)
                    self._log_info(f"Computed content HMAC: {content_hmac}")
                except Exception as e:
                    return self._handle_error(
                        state,
                        e,
                        f"Failed to download file or compute HMAC: {str(e)}",
                        {"storage_path": storage_path},
                    )

            # Get algorithm version and compute parameters fingerprint
            settings = get_settings()
            algorithm_version = settings.artifacts_algorithm_version
            # Normalize file type to expected MIME values
            normalized_file_type = (file_type or "").lower()
            if normalized_file_type in {"pdf"}:
                normalized_file_type = "application/pdf"
            elif normalized_file_type in {"png", "jpg", "jpeg", "tiff", "bmp"}:
                normalized_file_type = f"image/{'jpeg' if normalized_file_type == 'jpg' else normalized_file_type}"
            elif normalized_file_type in {"docx"}:
                normalized_file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            params = {
                "file_type": normalized_file_type,
                "use_llm": self.use_llm,
                "ocr_zoom": self._ocr_zoom,
                "min_text_len_for_ocr": self._min_text_len_for_ocr,
                "diagram_keywords": sorted(
                    self._diagram_keywords
                ),  # Sort for consistency
            }
            params_fingerprint = compute_params_fingerprint(params)

            self._log_info(
                f"Artifact parameters: algorithm_version={algorithm_version}, params_fingerprint={params_fingerprint[:12]}..."
            )

            # Check if artifacts are enabled
            if not settings.enable_artifacts:
                self._log_info("Artifacts disabled, performing direct text extraction")
                text_extraction_result = (
                    await self._extract_text_with_comprehensive_analysis(
                        user_client=user_client,
                        document_id=document_id,
                        storage_path=storage_path,
                        file_type=normalized_file_type,
                        state=state,
                        file_content=file_content,
                    )
                )
            else:
                # Try to get existing text artifact
                text_artifact = await self.artifacts_repo.get_full_text_artifact(
                    content_hmac, algorithm_version, params_fingerprint
                )

                if text_artifact:
                    self._log_info(
                        f"Found existing text artifact {text_artifact.id}, reusing results",
                        extra={
                            "artifact_id": str(text_artifact.id),
                            "total_pages": text_artifact.total_pages,
                            "total_words": text_artifact.total_words,
                            "methods": text_artifact.methods,
                        },
                    )

                    # Get associated page artifacts using unified method
                    page_artifacts = await self.artifacts_repo.get_all_page_artifacts(
                        content_hmac, algorithm_version, params_fingerprint
                    )

                    # Build TextExtractionResult from artifacts
                    text_extraction_result = await self._build_result_from_artifacts(
                        text_artifact, page_artifacts
                    )
                else:
                    self._log_info(
                        "No existing artifact found, computing text extraction"
                    )

                    # Compute text extraction
                    text_extraction_result = (
                        await self._extract_text_with_comprehensive_analysis(
                            user_client=user_client,
                            document_id=document_id,
                            storage_path=storage_path,
                            file_type=normalized_file_type,
                            state=state,
                            file_content=file_content,
                        )
                    )

                    # Store artifacts if extraction succeeded
                    if text_extraction_result and text_extraction_result.success:
                        await self._store_text_artifacts(
                            content_hmac,
                            algorithm_version,
                            params_fingerprint,
                            text_extraction_result,
                            params,
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
                        "file_type": normalized_file_type,
                        "content_hmac": content_hmac,
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
                        "content_hmac": content_hmac,
                    },
                )

            # Update state with extraction result and artifact metadata
            updated_state = state.copy()
            updated_state["text_extraction_result"] = text_extraction_result
            updated_state["content_hmac"] = content_hmac
            updated_state["algorithm_version"] = algorithm_version
            updated_state["params_fingerprint"] = params_fingerprint

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Successfully extracted text from document {document_id}",
                extra={
                    "document_id": document_id,
                    "content_hmac": content_hmac,
                    "character_count": len(full_text),
                    "total_pages": text_extraction_result.total_pages,
                    "extraction_methods": text_extraction_result.extraction_methods,
                    "overall_confidence": text_extraction_result.overall_confidence,
                    "total_word_count": text_extraction_result.total_word_count,
                    "use_llm": self.use_llm,
                    "duration_seconds": duration,
                    "artifacts_enabled": settings.enable_artifacts,
                },
            )

            return updated_state

        except Exception as e:
            # Use graceful degradation to allow workflow to continue if possible
            return self._handle_error_with_graceful_degradation(
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

    async def _build_result_from_artifacts(
        self, text_artifact, page_artifacts
    ) -> TextExtractionResult:
        """
        Build TextExtractionResult from stored artifacts.

        Args:
            text_artifact: FullTextArtifact with full text data
            page_artifacts: List of PageArtifacts

        Returns:
            TextExtractionResult reconstructed from artifacts
        """
        try:
            # Download full text from storage
            try:
                full_text = await self.storage_service.download_text_blob(
                    text_artifact.full_text_uri
                )

                # Verify integrity
                if not await self.storage_service.verify_blob_integrity(
                    text_artifact.full_text_uri, text_artifact.full_text_sha256
                ):
                    self._log_warning(
                        f"Full text integrity check failed for artifact {text_artifact.id}"
                    )
                    # Continue anyway, but log the issue

            except Exception as e:
                self._log_warning(
                    f"Failed to download full text from {text_artifact.full_text_uri}: {e}"
                )
                full_text = (
                    f"[Error loading full text from artifact {text_artifact.id}]"
                )

            # Build pages from page artifacts
            pages = []
            for page_artifact in page_artifacts:
                try:
                    # Download page text from storage
                    page_text = await self.storage_service.download_text_blob(
                        page_artifact.page_text_uri
                    )

                    # Verify integrity
                    if not await self.storage_service.verify_blob_integrity(
                        page_artifact.page_text_uri, page_artifact.page_text_sha256
                    ):
                        self._log_warning(
                            f"Page text integrity check failed for page {page_artifact.page_number}"
                        )

                except Exception as e:
                    self._log_warning(
                        f"Failed to download page text from {page_artifact.page_text_uri}: {e}"
                    )
                    page_text = f"[Error loading page {page_artifact.page_number} text]"

                page_extraction = PageExtraction(
                    page_number=page_artifact.page_number,
                    text_content=page_text,
                    text_length=len(page_text),
                    word_count=len(page_text.split()) if page_text else 0,
                    extraction_method="artifact_reuse",
                    confidence=0.9,  # High confidence for cached results
                    content_analysis=self._make_page_analysis(
                        page_text,
                        has_image=page_artifact.layout
                        and page_artifact.layout.get("has_diagrams", False),
                    ),
                )
                pages.append(page_extraction)

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                pages=pages,
                total_pages=text_artifact.total_pages,
                extraction_methods=["artifact_reuse"],
                total_word_count=text_artifact.total_words,
                overall_confidence=0.9,
                processing_time=0.1,  # Very fast since we're reusing
            )
        except Exception as e:
            self._log_warning(f"Failed to build result from artifacts: {e}")
            raise

    async def _store_text_artifacts(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        result: TextExtractionResult,
        params: dict,
    ):
        """
        Store text extraction results as artifacts with real object storage.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            result: TextExtractionResult to store
            params: Processing parameters
        """
        try:
            # Upload full text to storage and get URI + SHA256
            full_text_uri, full_text_sha256 = (
                await self.storage_service.upload_text_blob(
                    result.full_text or "", content_hmac
                )
            )

            # Store main text artifact with real URI and hash
            text_artifact = await self.artifacts_repo.insert_full_text_artifact(
                content_hmac=content_hmac,
                algorithm_version=algorithm_version,
                params_fingerprint=params_fingerprint,
                full_text_uri=full_text_uri,
                full_text_sha256=full_text_sha256,
                total_pages=result.total_pages,
                total_words=result.total_word_count or 0,
                methods={
                    "extraction_methods": result.extraction_methods,
                    "params": params,
                },
                timings={"processing_time": result.processing_time},
            )

            self._log_info(
                f"Stored text artifact {text_artifact.id} with URI {full_text_uri}"
            )

            # Store page artifacts with real storage
            for page in result.pages or []:
                try:
                    # Upload page text to storage
                    page_text_uri, page_text_sha256 = (
                        await self.storage_service.upload_page_text(
                            page.text_content or "", content_hmac, page.page_number
                        )
                    )

                    page_artifact = await self.artifacts_repo.insert_unified_page_artifact(
                        content_hmac=content_hmac,
                        algorithm_version=algorithm_version,
                        params_fingerprint=params_fingerprint,
                        page_number=page.page_number,
                        page_text_uri=page_text_uri,
                        page_text_sha256=page_text_sha256,
                        content_type="text",
                        layout=(
                            page.content_analysis.layout_features.__dict__
                            if page.content_analysis
                            else None
                        ),
                        metrics={
                            "confidence": page.confidence,
                            "word_count": page.word_count,
                            "text_length": page.text_length,
                            "extraction_method": page.extraction_method,
                        },
                    )

                    self._log_info(
                        f"Stored page artifact {page_artifact.id} for page {page.page_number} with URI {page_text_uri}"
                    )

                except Exception as e:
                    self._log_warning(
                        f"Failed to store page {page.page_number} artifact: {e}"
                    )
                    # Continue with other pages

        except Exception as e:
            # Log error but don't fail the overall operation since extraction succeeded
            self._log_warning(f"Failed to store artifacts: {e}")

    async def _extract_text_with_comprehensive_analysis(
        self,
        user_client,
        document_id: str,
        storage_path: str,
        file_type: str,
        state: DocumentProcessingState,
        file_content: Optional[bytes] = None,
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
            state: Current processing state for context
            file_content: Optional pre-downloaded file content

        Returns:
            TextExtractionResult with extracted text and analysis
        """
        try:
            # Download file content from storage if not provided
            if file_content is None:
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
                return await self._extract_pdf_text_hybrid(file_content, state)
            elif file_type.startswith("image/"):
                text, method = await self._extract_image_text_basic(file_content, state)
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
        self, file_content: bytes, state: DocumentProcessingState
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

                # Selective OCR for low-text/scanned pages (LLM first, PyTesseract fallback)
                settings = get_settings()
                if settings.enable_selective_ocr and (is_low_text or has_images or has_diagram_kw):
                    ocr_text = ""
                    ocr_method = method
                    
                    # Try LLM OCR first if enabled
                    if self.use_llm and gemini_service:
                        try:
                            # Render page image at higher DPI
                            png_bytes = self._render_page_png(page, zoom=self._ocr_zoom)
                            llm_result = await gemini_service.extract_text_diagram_insight(
                                file_content=png_bytes,
                                file_type="png",
                                filename=f"page_{idx+1}.png",
                                analysis_focus="ocr",
                                australian_state=state.get("australian_state", "NSW"),
                                contract_type=state.get("contract_type", "purchase_agreement"),
                                document_type=state.get("document_type", "contract"),
                            )
                            llm_text = (llm_result or {}).get("text", "")
                            if len(llm_text.strip()) > len(raw_text.strip()):
                                ocr_text = llm_text
                                ocr_method = "gemini_ocr"
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
                                f"Gemini OCR failed on page {idx+1}, trying PyTesseract fallback: {e}"
                            )
                    
                    # PyTesseract fallback for scanned pages if LLM OCR failed or unavailable
                    if not ocr_text and is_low_text and settings.enable_tesseract_fallback:
                        try:
                            # Render page image for PyTesseract
                            png_bytes = self._render_page_png(page, zoom=self._ocr_zoom)
                            tesseract_text = await self._extract_text_with_tesseract(png_bytes)
                            if tesseract_text and len(tesseract_text.strip()) > len(raw_text.strip()):
                                ocr_text = tesseract_text
                                ocr_method = "tesseract_ocr"
                        except Exception as e:
                            self._log_warning(
                                f"PyTesseract OCR failed on page {idx+1}: {e}"
                            )
                    
                    # Use OCR text if it's better than native text
                    if ocr_text:
                        text_to_use = ocr_text
                        method = ocr_method

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

    async def _extract_image_text_basic(self, file_content: bytes, state: DocumentProcessingState) -> tuple[str, str]:
        """Basic OCR text extraction from images."""
        try:
            settings = get_settings()
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
                        australian_state=state.get("australian_state", "NSW"),
                        contract_type=state.get("contract_type", "purchase_agreement"),
                        document_type=state.get("document_type", "contract"),
                    )
                    text = (result or {}).get("text", "")
                    return text, "ocr_gemini"
                except Exception as e:
                    self._log_warning(f"LLM OCR unavailable, falling back: {e}")
                    # Fall through to tesseract
            
            # Try basic Tesseract OCR if enabled
            if settings.enable_tesseract_fallback:
                try:
                    import pytesseract
                    from PIL import Image
                    from io import BytesIO

                    image = Image.open(BytesIO(file_content))
                    text = pytesseract.image_to_string(image)
                    return text, "ocr_tesseract"
                except ImportError:
                    return "", "ocr_unavailable"
            else:
                return "", "tesseract_disabled"

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

    async def _extract_text_with_tesseract(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes using PyTesseract.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Extracted text string
        """
        try:
            import pytesseract
            from PIL import Image
            from io import BytesIO
            
            # Open image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            
            return text.strip()
            
        except ImportError:
            self._log_warning("PyTesseract not available for OCR fallback")
            return ""
        except Exception as e:
            self._log_warning(f"PyTesseract OCR failed: {e}")
            return ""

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
