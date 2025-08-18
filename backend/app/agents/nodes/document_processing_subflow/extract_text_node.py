"""
ExtractTextNode - Extract text with comprehensive analysis

This node migrates the _extract_text_with_comprehensive_analysis method from DocumentService
into a dedicated node for the document processing subflow.
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import tempfile
import uuid
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
from app.services.visual_artifact_service import VisualArtifactService
from app.schema.document import DiagramProcessingResult


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
        self.visual_artifact_service = None
        self.text_extraction_result = None
        # Heuristics / thresholds
        self._min_text_len_for_ocr = 100
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
            # Use artifacts bucket for storing text extraction artifacts
            self.storage_service = ArtifactStorageService(bucket_name="artifacts")
        if not self.visual_artifact_service:
            self.visual_artifact_service = VisualArtifactService(
                storage_service=self.storage_service, artifacts_repo=self.artifacts_repo
            )

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
            updated_state = state.copy()

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
                    updated_state["content_hmac"] = content_hmac
                    # Save a local tmp copy for downstream reuse (to avoid re-downloads)
                    try:
                        tmp_dir = tempfile.mkdtemp(prefix="r2a_doc_")
                        file_name = (
                            os.path.basename(storage_path) or f"{content_hmac}.bin"
                        )
                        local_path = os.path.join(tmp_dir, file_name)
                        with open(local_path, "wb") as f:
                            f.write(file_content)
                        updated_state["local_tmp_path"] = local_path
                        self._log_debug(
                            f"Saved local tmp copy at {local_path}",
                            local_tmp_path=local_path,
                        )
                    except Exception as tmp_err:
                        self._log_debug(
                            f"Failed to save local tmp copy: {tmp_err}",
                            storage_path=storage_path,
                        )
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

            # Make params and version available to downstream steps immediately
            # so that any artifact writes (e.g., OCR diagram hints) have a valid fingerprint
            updated_state["algorithm_version"] = algorithm_version
            updated_state["params_fingerprint"] = params_fingerprint

            # Check if artifacts are enabled
            if not settings.enable_artifacts:
                self._log_info("Artifacts disabled, performing direct text extraction")
                self.text_extraction_result = (
                    await self._extract_text_with_comprehensive_analysis(
                        user_client=user_client,
                        document_id=document_id,
                        storage_path=storage_path,
                        file_type=normalized_file_type,
                        state=updated_state,
                        file_content=file_content,
                        content_hmac=content_hmac,
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
                    self.text_extraction_result = (
                        await self._build_result_from_artifacts(
                            text_artifact, page_artifacts
                        )
                    )
                else:
                    self._log_info(
                        "No existing artifact found, computing text extraction"
                    )

                    # Compute text extraction
                    self.text_extraction_result = (
                        await self._extract_text_with_comprehensive_analysis(
                            user_client=user_client,
                            document_id=document_id,
                            storage_path=storage_path,
                            file_type=normalized_file_type,
                            state=updated_state,
                            file_content=file_content,
                        )
                    )

                    # Store artifacts if extraction succeeded
                    artifact_text_id = None
                    if (
                        self.text_extraction_result
                        and self.text_extraction_result.success
                    ):
                        artifact_text_id = await self._store_text_artifacts(
                            content_hmac,
                            algorithm_version,
                            params_fingerprint,
                            self.text_extraction_result,
                            params,
                        )

            # Validate extraction result
            if (
                not self.text_extraction_result
                or not self.text_extraction_result.success
            ):
                error_msg = (
                    self.text_extraction_result.error
                    if self.text_extraction_result
                    else "Text extraction failed"
                )

                # CRITICAL FIX: Add comprehensive logging for text extraction failures
                self._log_error(
                    f"Text extraction failed for document {document_id}: {error_msg}",
                    extra={
                        "document_id": document_id,
                        "storage_path": storage_path,
                        "file_type": normalized_file_type,
                        "content_hmac": content_hmac,
                        "extraction_attempted": True,
                        "extraction_success": False,
                        "text_extraction_result": (
                            self.text_extraction_result.model_dump()
                            if self.text_extraction_result
                            and hasattr(self.text_extraction_result, "model_dump")
                            else str(self.text_extraction_result)
                        ),
                        "file_size_bytes": len(file_content) if file_content else 0,
                        "use_llm": self.use_llm,
                    },
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
            full_text = self.text_extraction_result.full_text or ""
            if len(full_text.strip()) < 100:
                # CRITICAL FIX: Add comprehensive logging for insufficient content
                diagnostic_info = {
                    "document_id": document_id,
                    "character_count": len(full_text),
                    "stripped_character_count": len(full_text.strip()),
                    "extraction_method": self.text_extraction_result.extraction_methods,
                    "total_pages": self.text_extraction_result.total_pages,
                    "content_hmac": content_hmac,
                    "file_type": normalized_file_type,
                    "file_size_bytes": len(file_content) if file_content else 0,
                    "use_llm": self.use_llm,
                    "extraction_confidence": getattr(
                        self.text_extraction_result, "overall_confidence", 0.0
                    ),
                    "raw_text_sample": (
                        full_text[:200] + "..." if len(full_text) > 200 else full_text
                    ),
                }

                self._log_error(
                    f"Insufficient text content extracted from document {document_id}: "
                    f"got {len(full_text.strip())} characters (minimum: 100)",
                    extra=diagnostic_info,
                )

                return self._handle_error(
                    state,
                    ValueError("Insufficient text content"),
                    "Insufficient text content extracted from document",
                    diagnostic_info,
                )

            # Update state with extraction result and artifact metadata

            updated_state["text_extraction_result"] = self.text_extraction_result
            updated_state["diagram_processing_result"] = self.diagram_processing_result
            updated_state["content_hmac"] = content_hmac
            updated_state["algorithm_version"] = algorithm_version
            updated_state["params_fingerprint"] = params_fingerprint
            # Store the artifact_text_id so it can be linked to the document
            if "artifact_text_id" in locals() and artifact_text_id:
                updated_state["artifact_text_id"] = artifact_text_id

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            self._log_info(
                f"Successfully extracted text from document {document_id}",
                extra={
                    "document_id": document_id,
                    "content_hmac": content_hmac,
                    "character_count": len(full_text),
                    "total_pages": self.text_extraction_result.total_pages,
                    "extraction_methods": self.text_extraction_result.extraction_methods,
                    "overall_confidence": self.text_extraction_result.overall_confidence,
                    "total_word_count": self.text_extraction_result.total_word_count,
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

        Returns:
            UUID: The artifact_text_id of the created full text artifact
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

            # Store the artifact ID to return
            artifact_text_id = text_artifact.id

            # Store page artifacts with real storage
            for page in result.pages or []:
                try:
                    # Upload page text to storage
                    page_text_uri, page_text_sha256 = (
                        await self.storage_service.upload_page_text(
                            page.text_content or "", content_hmac, page.page_number
                        )
                    )

                    page_artifact = (
                        await self.artifacts_repo.insert_unified_page_artifact(
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
                    )

                    self._log_info(
                        f"Stored page artifact {page_artifact.id} for page {page.page_number} with URI {page_text_uri}"
                    )

                except Exception as e:
                    self._log_warning(
                        f"Failed to store page {page.page_number} artifact: {e}"
                    )
                    # Continue with other pages

            # Return the full text artifact ID
            return artifact_text_id

        except Exception as e:
            # Log error but don't fail the overall operation since extraction succeeded
            self._log_warning(f"Failed to store artifacts: {e}")
            raise  # Re-raise to handle properly

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
                    file_content = await user_client.download_file(
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
            # CRITICAL FIX: Add logging for basic PDF extraction
            self._log_info(
                "Starting basic PDF text extraction",
                extra={
                    "file_size_bytes": len(file_content),
                    "file_size_mb": round(len(file_content) / (1024 * 1024), 2),
                },
            )

            # Try PyMuPDF first
            try:
                import pymupdf

                doc = pymupdf.open(stream=file_content, filetype="pdf")
                text = ""
                pages_count = 0
                page_texts = []

                for page in doc:
                    page_text = page.get_text() or ""
                    text += page_text
                    page_texts.append(page_text)
                    pages_count += 1

                doc.close()

                # CRITICAL FIX: Log detailed extraction results
                self._log_info(
                    f"Basic PDF extraction via PyMuPDF completed",
                    extra={
                        "pages": pages_count,
                        "total_text_length": len(text),
                        "total_text_stripped": len(text.strip()),
                        "page_text_lengths": [len(pt.strip()) for pt in page_texts],
                        "page_text_samples": [
                            pt[:100] + "..." if len(pt) > 100 else pt
                            for pt in page_texts
                        ],
                        "extraction_method": "pdf_pymupdf",
                    },
                )

                return text, "pdf_pymupdf"
            except ImportError:
                self._log_warning("PyMuPDF not available, trying pypdf fallback")
                pass

            # Fallback to pypdf
            try:
                import pypdf
                from io import BytesIO

                reader = pypdf.PdfReader(BytesIO(file_content))
                text = ""
                page_texts = []

                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text += page_text
                    page_texts.append(page_text)

                # CRITICAL FIX: Log detailed extraction results
                self._log_info(
                    f"Basic PDF extraction via pypdf completed",
                    extra={
                        "pages": len(reader.pages),
                        "total_text_length": len(text),
                        "total_text_stripped": len(text.strip()),
                        "page_text_lengths": [len(pt.strip()) for pt in page_texts],
                        "page_text_samples": [
                            pt[:100] + "..." if len(pt) > 100 else pt
                            for pt in page_texts
                        ],
                        "extraction_method": "pdf_pypdf",
                    },
                )

                return text, "pdf_pypdf"
            except ImportError:
                self._log_warning("pypdf not available")
                pass

            self._log_warning("No PDF extraction libraries available")
            return "", "pdf_unavailable"

        except Exception as e:
            self._log_error(f"PDF extraction failed: {e}", extra={"error": str(e)})
            return "", "pdf_failed"

    async def _extract_pdf_text_hybrid(
        self, file_content: bytes, state: DocumentProcessingState
    ) -> TextExtractionResult:
        """Hybrid PDF extraction: PyMuPDF first, selective OCR/VLM per page."""
        # Initialize diagram processing result tracking
        self.diagram_processing_result = {
            "success": True,
            "diagrams": [],
            "total_diagrams": 0,
            "pages_processed": [],  # Will track only pages processed by Gemini OCR
            "diagram_pages": [],
            "diagram_types": {},
            "detection_summary": {
                "processing_method": "hybrid_extraction_llm_hints",
                "pages_analyzed": 0,
                "pages_with_diagrams": 0,
                "detection_source": "llm_ocr_hints",
            },
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        }

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
                    self._log_info(
                        "Initialized GeminiOCRService for hybrid PDF extraction"
                    )
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
                # Only run OCR when there's insufficient text AND visual content that might contain text
                settings = get_settings()
                should_ocr = (
                    (is_low_text + has_images + has_diagram_kw) >= 2
                    if settings.enable_selective_ocr
                    else False
                )
                trigger_label = (
                    "low_text_and_images"
                    if (is_low_text and has_images)
                    else (
                        "low_text_and_diagram_keywords"
                        if (is_low_text and has_diagram_kw)
                        else "no_trigger"
                    )
                )

                self._log_info(
                    f"Selective OCR decision for page {idx + 1}",
                    is_low_text=is_low_text,
                    has_images=has_images,
                    has_diagram_kw=has_diagram_kw,
                    min_text_len_for_ocr=self._min_text_len_for_ocr,
                    should_ocr=should_ocr,
                    trigger=trigger_label,
                )

                if should_ocr:
                    ocr_text = ""
                    ocr_method = method
                    # Try LLM OCR first if enabled
                    if self.use_llm and gemini_service:
                        try:
                            self._log_info(
                                f"Invoking Gemini OCR for page {idx + 1}",
                                extra={
                                    "trigger": trigger_label,
                                    "use_llm": self.use_llm,
                                },
                            )
                            # Render page image at higher DPI
                            png_bytes = self._render_page_png(page, zoom=self._ocr_zoom)
                            llm_result = (
                                await gemini_service.extract_text_diagram_insight(
                                    file_content=png_bytes,
                                    file_type="png",
                                    filename=f"page_{idx+1}.png",
                                    analysis_focus="ocr",
                                    australian_state=state.get(
                                        "australian_state", "NSW"
                                    ),
                                    contract_type=state.get(
                                        "contract_type", "purchase_agreement"
                                    ),
                                    document_type=state.get(
                                        "document_type", "contract"
                                    ),
                                )
                            )
                            llm_text = (llm_result.text or "") if llm_result else ""
                            if len(llm_text.strip()) > len(raw_text.strip()):
                                ocr_text = llm_text
                                ocr_method = "gemini_ocr"
                                self._log_info(
                                    f"Gemini OCR chosen for page {idx + 1}",
                                    extra={"chars": len(ocr_text)},
                                )
                            # If LLM returned diagram types, mark later in analysis
                            diagrams = getattr(llm_result, "diagrams", None) or []
                            has_images = bool(diagrams)

                            # Update diagram processing result with detected diagrams
                            if diagrams:
                                for hint_index, diagram_type in enumerate(
                                    diagrams, start=1
                                ):
                                    diagram_type_value = (
                                        getattr(diagram_type, "value", None)
                                        or str(diagram_type)
                                        or "unknown"
                                    )
                                    confidence = float(
                                        getattr(llm_result, "text_confidence", 0.0)
                                        or 0.0
                                    )

                                    # Create a simple diagram representation
                                    class SimpleDiagram:
                                        def __init__(
                                            self, page, type_value, confidence, method
                                        ):
                                            self.page = page
                                            self.type = type_value
                                            self.confidence = confidence
                                            self.detection_method = method

                                    # Add to diagram processing result
                                    self.diagram_processing_result["diagrams"].append(
                                        SimpleDiagram(
                                            idx + 1,  # page number
                                            diagram_type_value,
                                            confidence,
                                            "llm_ocr_hint",
                                        )
                                    )

                                    # Update counts and tracking
                                    self.diagram_processing_result[
                                        "total_diagrams"
                                    ] += 1
                                    if (
                                        idx + 1
                                        not in self.diagram_processing_result[
                                            "diagram_pages"
                                        ]
                                    ):
                                        self.diagram_processing_result[
                                            "diagram_pages"
                                        ].append(idx + 1)

                                    # Update diagram types count
                                    if (
                                        diagram_type_value
                                        not in self.diagram_processing_result[
                                            "diagram_types"
                                        ]
                                    ):
                                        self.diagram_processing_result["diagram_types"][
                                            diagram_type_value
                                        ] = 0
                                    self.diagram_processing_result["diagram_types"][
                                        diagram_type_value
                                    ] += 1

                            # Track this page as processed by Gemini OCR (regardless of whether diagrams were found)
                            if (
                                idx + 1
                                not in self.diagram_processing_result["pages_processed"]
                            ):
                                self.diagram_processing_result[
                                    "pages_processed"
                                ].append(idx + 1)

                            # Persist artifact hints with images so downstream diagram detection can skip duplicate API calls
                            if has_images:
                                try:
                                    # Ensure services are initialized
                                    if not self.visual_artifact_service:
                                        await self.initialize()

                                    # Persist per-hint artifacts with visual content
                                    persisted_any = False
                                    diagrams = getattr(llm_result, "diagrams", [])
                                    for hint_index, diagram_type in enumerate(
                                        diagrams, start=1
                                    ):
                                        diagram_type_value = (
                                            getattr(diagram_type, "value", None)
                                            or str(diagram_type)
                                            or "unknown"
                                        )
                                        diagram_key = f"llm_ocr_hint_page_{idx+1}_{hint_index:02d}"

                                        # Use visual artifact service to store both image and metadata
                                        result = await self.visual_artifact_service.store_visual_artifact(
                                            image_bytes=png_bytes,
                                            content_hmac=state["content_hmac"],
                                            algorithm_version=get_settings().artifacts_algorithm_version,
                                            params_fingerprint=state.get(
                                                "params_fingerprint"
                                            )
                                            or "",
                                            page_number=idx + 1,
                                            diagram_key=diagram_key,
                                            artifact_type="diagram",
                                            diagram_meta={
                                                "type": diagram_type_value,
                                                "confidence": float(
                                                    getattr(
                                                        llm_result,
                                                        "text_confidence",
                                                        0.0,
                                                    )
                                                    or 0.0
                                                ),
                                                "detection_method": "llm_ocr_hint",
                                            },
                                        )
                                        persisted_any = True
                                        if result.cache_hit:
                                            self._log_info(
                                                f"Reused cached visual artifact for page {idx + 1} hint {hint_index}"
                                            )

                                    if persisted_any:
                                        self._log_info(
                                            f"Stored LLM OCR diagram hint(s) with images for page {idx + 1}",
                                            extra={
                                                "hint_count": (
                                                    len(diagrams) if diagrams else 1
                                                )
                                            },
                                        )
                                except Exception as persist_err:
                                    # Do not fail text extraction if persisting hint fails
                                    self._log_warning(
                                        f"Failed to persist LLM OCR diagram hint for page {idx + 1}: {persist_err}"
                                    )
                            # No single diagram_hint anymore
                        except Exception as e:
                            self._log_warning(
                                f"Gemini OCR failed on page {idx+1}, trying PyTesseract fallback: {e}"
                            )
                    else:
                        self._log_info(
                            f"Skipping Gemini OCR for page {idx + 1}",
                            extra={
                                "use_llm": self.use_llm,
                                "service_available": bool(gemini_service),
                                "trigger": trigger_label,
                            },
                        )

                    # PyTesseract fallback for scanned pages if LLM OCR failed or unavailable
                    if (
                        not ocr_text
                        and is_low_text
                        and settings.enable_tesseract_fallback
                    ):
                        try:
                            self._log_info(
                                f"Attempting Tesseract OCR fallback for page {idx + 1}",
                                extra={
                                    "is_low_text": is_low_text,
                                    "fallback_enabled": settings.enable_tesseract_fallback,
                                },
                            )
                            # Render page image for PyTesseract
                            png_bytes = self._render_page_png(page, zoom=self._ocr_zoom)
                            tesseract_text = await self._extract_text_with_tesseract(
                                png_bytes
                            )
                            if tesseract_text and len(tesseract_text.strip()) > len(
                                raw_text.strip()
                            ):
                                ocr_text = tesseract_text
                                ocr_method = "tesseract_ocr"
                                self._log_info(
                                    f"Tesseract OCR chosen for page {idx + 1}",
                                    extra={"chars": len(ocr_text)},
                                )
                        except Exception as e:
                            self._log_warning(
                                f"PyTesseract OCR failed on page {idx+1}: {e}"
                            )

                    # Use OCR text if it's better than native text
                    if ocr_text:
                        text_to_use = ocr_text
                        method = ocr_method

                page_analysis = self._make_page_analysis(
                    text_to_use,
                    has_image=has_images,
                    has_diagram_kw=has_diagram_kw,
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

            # Update final diagram processing result with page counts
            if hasattr(self, "diagram_processing_result"):
                # pages_processed already contains only the pages that were processed by Gemini OCR
                # Update detection summary with actual counts
                self.diagram_processing_result["detection_summary"][
                    "pages_analyzed"
                ] = len(self.diagram_processing_result["pages_processed"])
                self.diagram_processing_result["detection_summary"][
                    "pages_with_diagrams"
                ] = len(self.diagram_processing_result["diagram_pages"])

            # CRITICAL FIX: Add comprehensive logging for PDF extraction results
            self._log_info(
                f"PDF text extraction completed for document {state.get('document_id', 'unknown')}",
                extra={
                    "document_id": state.get("document_id"),
                    "total_pages": len(pages),
                    "extraction_methods": extraction_methods,
                    "full_text_length": len(full_text),
                    "full_text_sample": (
                        full_text[:500] + "..." if len(full_text) > 500 else full_text
                    ),
                    "overall_confidence": overall_conf,
                    "total_words": total_words,
                    "pages_with_text": len(
                        [
                            p
                            for p in pages
                            if p.text_content and len(p.text_content.strip()) > 0
                        ]
                    ),
                    "pages_without_text": len(
                        [
                            p
                            for p in pages
                            if not p.text_content or len(p.text_content.strip()) == 0
                        ]
                    ),
                },
            )

            # CRITICAL FIX: Check if we have sufficient text content
            if len(full_text.strip()) < 100:
                self._log_warning(
                    f"PDF extraction produced insufficient text: {len(full_text.strip())} characters (minimum: 100)",
                    extra={
                        "document_id": state.get("document_id"),
                        "full_text": full_text,
                        "page_details": [
                            {
                                "page": p.page_number,
                                "text_length": len(p.text_content or ""),
                                "extraction_method": p.extraction_method,
                                "confidence": p.confidence,
                                "has_images": (
                                    p.content_analysis.layout_features.has_images
                                    if p.content_analysis
                                    else False
                                ),
                            }
                            for p in pages
                        ],
                    },
                )

                # Try to provide a more helpful error message
                if len(pages) == 0:
                    error_msg = "PDF extraction failed - no pages could be processed"
                elif all(len(p.text_content or "").strip() < 10 for p in pages):
                    error_msg = "PDF extraction failed - all pages contain insufficient text (document may be image-based or corrupted)"
                else:
                    error_msg = f"PDF extraction failed - extracted only {len(full_text.strip())} characters across {len(pages)} pages"

                return TextExtractionResult(
                    success=False,
                    error=error_msg,
                    full_text=full_text,  # Keep what we have for debugging
                    pages=pages,
                    extraction_methods=extraction_methods,
                    overall_confidence=overall_conf,
                    total_pages=len(pages),
                    total_word_count=total_words,
                )

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
            # Clean up diagram processing result on failure
            if hasattr(self, "diagram_processing_result"):
                delattr(self, "diagram_processing_result")
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

    async def _extract_image_text_basic(
        self, file_content: bytes, state: DocumentProcessingState
    ) -> tuple[str, str]:
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
                    text = result.text if result else ""
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
        self,
        text: str,
        has_image: bool = False,
        has_diagram_kw: bool = False,
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
