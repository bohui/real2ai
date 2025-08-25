"""
LayoutFormatCleanupNode - Clean and format text layout without LLM processing

This node takes the text extraction result, generates font-to-layout mapping,
and cleans up the text format to produce a properly formatted markdown output.
It does NOT extract contract information like purchase_method, use_category,
contract_terms, or property_address - only focuses on layout formatting.
"""

from typing import Dict, Any, Optional, List
import re
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.prompts.schema.contract_layout_summary_schema import LayoutFormatResult
from .base_node import DocumentProcessingNodeBase
from app.utils.font_layout_mapper import FontLayoutMapper
from app.utils.storage_utils import ArtifactStorageService
from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.content_utils import compute_content_hmac, compute_params_fingerprint
from app.services.repositories.contracts_repository import ContractsRepository


class LayoutFormatCleanupNode(DocumentProcessingNodeBase):
    def __init__(self, progress_range: tuple[int, int] = (43, 48)):
        super().__init__("layout_format_cleanup")
        self.font_mapper = FontLayoutMapper()
        self.progress_range = progress_range
        self.storage_service = None
        self.artifacts_repo = None

    async def initialize(self):
        """Initialize storage service and artifacts repository"""
        if not self.storage_service:
            self.storage_service = ArtifactStorageService(bucket_name="artifacts")
        if not self.artifacts_repo:
            self.artifacts_repo = ArtifactsRepository()

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            # Initialize services
            await self.initialize()

            document_id = state.get("document_id")
            text_extraction_result = state.get("text_extraction_result")
            content_hash = (
                state.get("content_hash")
                or ((state.get("_document_metadata") or {}).get("content_hash"))
                or state.get("content_hmac")
            )

            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "layout_format_cleanup"},
                )

            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Text extraction result is missing or unsuccessful",
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": (
                            text_extraction_result.success
                            if text_extraction_result
                            else False
                        ),
                    },
                )

            # Idempotency: if we already saved formatted raw_text for this content, skip
            if content_hash:
                try:
                    contracts_repo = ContractsRepository()
                    existing_contract = (
                        await contracts_repo.get_contract_by_content_hash(content_hash)
                    )
                    if existing_contract and (existing_contract.raw_text or "").strip():
                        self._log_info(
                            "Skipping layout formatting: raw_text already saved",
                            extra={
                                "document_id": document_id,
                                "content_hash": content_hash,
                                "reason": "idempotent_skip_existing_raw_text",
                            },
                        )

                        font_to_layout_mapping: Dict[str, str] = {}
                        layout_result = LayoutFormatResult(
                            raw_text=text_extraction_result.full_text or "",
                            formatted_text=existing_contract.raw_text,
                            font_to_layout_mapping=font_to_layout_mapping,
                        )

                        updated_state = state.copy()
                        updated_state["layout_format_result"] = layout_result
                        # No new artifact created in skip path
                        duration = (
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds()
                        self._record_success(duration)
                        return updated_state
                except Exception as e:
                    # Non-fatal: continue with formatting if check fails
                    self._log_warning(
                        f"Idempotency check failed; proceeding with formatting: {e}",
                        extra={
                            "document_id": document_id,
                            "content_hash": content_hash,
                        },
                    )

            full_text = text_extraction_result.full_text or ""
            if not full_text:
                return self._handle_error(
                    state,
                    ValueError("Empty full_text"),
                    "Full text is empty; cannot clean layout format",
                    {"document_id": document_id},
                )

            # STEP 1: Generate font to layout mapping from the full document
            self._log_info(
                "Generating font to layout mapping for document",
                extra={"document_id": document_id},
            )

            font_to_layout_mapping = self.font_mapper.generate_font_layout_mapping(
                full_text
            )

            if font_to_layout_mapping:
                self._log_info(
                    f"Generated font layout mapping with {len(font_to_layout_mapping)} font sizes",
                    extra={
                        "document_id": document_id,
                        "font_mapping": font_to_layout_mapping,
                    },
                )
            else:
                self._log_warning(
                    "No font layout mapping generated; proceeding without mapping",
                    extra={"document_id": document_id},
                )

            # STEP 2: Clean and format the text using the font mapping
            self._log_info(
                "Cleaning and formatting text layout",
                extra={"document_id": document_id},
            )

            formatted_text = await self._format_text_with_layout_mapping(
                full_text, font_to_layout_mapping
            )

            # STEP 3: Save formatted text as artifacts and build result
            self._log_info(
                "Saving formatted text as artifacts",
                extra={"document_id": document_id},
            )

            # Compute content HMAC and parameters fingerprint for artifact storage
            content_hmac = state.get("content_hmac")
            if not content_hmac:
                self._log_error("Content HMAC not found in state, shouldn't happen")
                raise ValueError("Content HMAC not found in state")

            algorithm_version = 1  # Layout formatting algorithm version
            params = {
                "font_mapping": font_to_layout_mapping,
                "algorithm": "font_layout_mapping",
                "version": algorithm_version,
            }
            params_fingerprint = compute_params_fingerprint(params)

            # Store formatted text artifacts
            formatted_text_artifact_id = await self._store_formatted_text_artifacts(
                content_hmac,
                algorithm_version,
                params_fingerprint,
                formatted_text,
                text_extraction_result,
                params,
            )

            # Update contract raw_text with formatted text
            try:
                content_hash = state.get("content_hash")
                if not content_hash:
                    metadata = state.get("_document_metadata") or {}
                    content_hash = state.get("content_hmac") or metadata.get(
                        "content_hash"
                    )

                if content_hash:
                    contracts_repo = ContractsRepository()
                    await contracts_repo.upsert_contract_by_content_hash(
                        content_hash=content_hash,
                        # contract_type=str(state.get("contract_type") or "unknown"),
                        # state=(
                        #     str(state.get("australian_state"))
                        #     if state.get("australian_state") is not None
                        #     else None
                        # ),
                        raw_text=formatted_text,
                        updated_by=self.node_name,
                    )
                else:
                    self._log_warning(
                        "Missing content_hash; skipping raw_text upsert",
                        extra={"document_id": document_id},
                    )
            except Exception as upsert_err:
                # Non-fatal: continue processing even if upsert fails
                self._log_warning(
                    f"Failed to upsert formatted raw_text: {upsert_err}",
                    extra={"document_id": document_id},
                )

            # STEP 4: Create layout format result
            # Add debug logging to help identify validation issues
            self._log_info(
                f"Creating LayoutFormatResult with font mapping: {font_to_layout_mapping}",
                extra={
                    "document_id": document_id,
                    "font_mapping_type": type(font_to_layout_mapping).__name__,
                    "font_mapping_keys": (
                        list(font_to_layout_mapping.keys())
                        if font_to_layout_mapping
                        else []
                    ),
                    "font_mapping_values": (
                        list(font_to_layout_mapping.values())
                        if font_to_layout_mapping
                        else []
                    ),
                },
            )

            # Additional detailed logging for debugging
            if font_to_layout_mapping:
                for key, value in font_to_layout_mapping.items():
                    self._log_info(
                        f"Font mapping entry: key='{key}' (type: {type(key).__name__}), value='{value}' (type: {type(value).__name__})",
                        extra={"document_id": document_id},
                    )

            layout_result = LayoutFormatResult(
                raw_text=full_text,
                formatted_text=formatted_text,
                font_to_layout_mapping=font_to_layout_mapping,
            )

            # Update state with formatted text and artifacts
            updated_state = state.copy()
            updated_state["layout_format_result"] = layout_result
            updated_state["formatted_text_artifact_id"] = formatted_text_artifact_id

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)

            # Progress is handled by workflow level

            self._log_info(
                f"Layout format cleanup complete for document {document_id}",
                extra={
                    "document_id": document_id,
                    "duration_seconds": duration,
                    "font_mapping_generated": bool(font_to_layout_mapping),
                    "original_text_length": len(full_text),
                    "formatted_text_length": len(formatted_text),
                    "formatted_text_artifact_id": formatted_text_artifact_id,
                },
            )

            return updated_state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to clean layout format: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "layout_format_cleanup",
                },
            )

    async def _format_text_with_layout_mapping(
        self, text: str, font_mapping: Dict[str, str]
    ) -> str:
        """
        Format text using font-to-layout mapping to create clean markdown.

        Args:
            text: Raw OCR text with font markers
            font_mapping: Dictionary mapping font sizes to layout elements

        Returns:
            Formatted markdown text
        """
        # Split by page delimiters (capture the delimiter so we can preserve it)
        # Examples of delimiters: "--- Page 1 ---", "--- Page 3 of 12 ---"
        page_delimiter_pattern = re.compile(r"^(--- Page [^-\n]* ---)\n?", re.MULTILINE)
        parts = page_delimiter_pattern.split(text)

        formatted_pages: List[str] = []
        page_bodies: List[str] = []

        if len(parts) == 1:
            # No explicit page delimiters; treat entire text as a single page
            if parts[0].strip():
                page_bodies.append(parts[0])
        else:
            # parts structure: [preamble, header1, body1, header2, body2, ...]
            preamble = parts[0]
            if preamble.strip():
                page_bodies.append(preamble)

            # Iterate over header/body pairs
            for i in range(1, len(parts), 2):
                header = parts[i]
                body = parts[i + 1] if i + 1 < len(parts) else ""

                # Format body first using mapping or simple cleanup
                if font_mapping:
                    formatted_body = self._format_page_with_mapping(body, font_mapping)
                else:
                    formatted_body = self._format_page_without_mapping(body)

                # Build markdown comment for the page header and prepend it
                header_text_match = re.match(r"---\s*(.*?)\s*---", header.strip())
                header_text = (
                    header_text_match.group(1) if header_text_match else header.strip()
                )
                header_comment = f"<!-- {header_text} -->"

                if formatted_body:
                    formatted_pages.append(
                        "\n\n".join([header_comment, formatted_body])
                    )
                else:
                    # Preserve page boundary even if no body content
                    formatted_pages.append(header_comment)

                page_bodies.append(body)

        # Compute total pages based on non-empty bodies (align with previous behavior)
        total_pages = len([p for p in page_bodies if p.strip()])
        processed_pages = 0

        # Process preamble (if any) as the first page without a header comment
        if len(parts) > 1:
            preamble = parts[0]
            if preamble.strip():
                if font_mapping:
                    formatted_preamble = self._format_page_with_mapping(
                        preamble, font_mapping
                    )
                else:
                    formatted_preamble = self._format_page_without_mapping(preamble)

                if formatted_preamble:
                    formatted_pages.insert(0, formatted_preamble)

                processed_pages += 1

                if hasattr(self, "progress_callback") and self.progress_callback:
                    try:
                        await self.emit_page_progress(
                            current_page=processed_pages,
                            total_pages=total_pages,
                            description="Formatting page layout",
                            progress_range=self.progress_range,
                        )
                    except Exception as e:
                        self._log_warning(f"Failed to emit page progress: {e}")
        else:
            # Single page (no delimiters) path
            if page_bodies:
                processed_pages = 1
                if hasattr(self, "progress_callback") and self.progress_callback:
                    try:
                        await self.emit_page_progress(
                            current_page=processed_pages,
                            total_pages=total_pages or 1,
                            description="Formatting page layout",
                            progress_range=self.progress_range,
                        )
                    except Exception as e:
                        self._log_warning(f"Failed to emit page progress: {e}")

            # When no delimiters, ensure formatted_pages contains the formatted body
            if not formatted_pages and page_bodies:
                body = page_bodies[0]
                if font_mapping:
                    formatted_only = self._format_page_with_mapping(body, font_mapping)
                else:
                    formatted_only = self._format_page_without_mapping(body)
                if formatted_only:
                    formatted_pages.append(formatted_only)

        # For documents with explicit pages, we already emitted progress for preamble; now emit for each header/body pair
        if len(parts) > 1 and total_pages > (1 if parts[0].strip() else 0):
            remaining_pages = total_pages - processed_pages
            for _ in range(remaining_pages):
                processed_pages += 1
                if hasattr(self, "progress_callback") and self.progress_callback:
                    try:
                        await self.emit_page_progress(
                            current_page=processed_pages,
                            total_pages=total_pages,
                            description="Formatting page layout",
                            progress_range=self.progress_range,
                        )
                    except Exception as e:
                        self._log_warning(f"Failed to emit page progress: {e}")

        return "\n\n".join(formatted_pages)

    def _format_page_without_mapping(self, page_text: str) -> str:
        """
        Format a single page without font mapping - just clean the text.

        Args:
            page_text: Text content of a single page

        Returns:
            Cleaned page text
        """
        lines = page_text.strip().split("\n")
        formatted_lines = []

        for line in lines:
            if not line.strip():
                continue

            # Remove font markers and clean the line
            font_pattern = re.compile(r"\[\[\[[^\]]*\]\]\]")
            clean_text = font_pattern.sub("", line).strip()

            if clean_text:
                formatted_lines.append(clean_text)

        # If no content after cleaning, return empty string
        if not formatted_lines:
            return ""

        # Join with double newlines to match expected format
        return "\n\n".join(formatted_lines)

    def _format_page_with_mapping(
        self, page_text: str, font_mapping: Dict[str, str]
    ) -> str:
        """
        Format a single page using font mapping.

        Args:
            page_text: Text content of a single page
            font_mapping: Dictionary mapping font sizes to layout elements

        Returns:
            Formatted page text
        """
        lines = page_text.strip().split("\n")
        formatted_lines = []

        for line in lines:
            if not line.strip():
                continue

                # Look for font size markers (including invalid ones)
            font_pattern = re.compile(r"\[\[\[([^\]]*)\]\]\]")
            match = font_pattern.search(line)

            if match:
                font_size = match.group(1)
                # Remove the font marker for clean text
                clean_text = font_pattern.sub("", line).strip()

                if clean_text:
                    # Check if font_size is numeric and exists in mapping
                    try:
                        float(font_size)
                        layout_element = font_mapping.get(font_size, "body_text")
                    except ValueError:
                        # Invalid font size, treat as body text
                        layout_element = "body_text"

                    formatted_line = self._apply_layout_formatting(
                        clean_text, layout_element
                    )
                    formatted_lines.append(formatted_line)
            else:
                # No font marker, treat as regular text
                if line.strip():
                    formatted_lines.append(line.strip())

        # Join with double newlines to match expected format
        return "\n\n".join(formatted_lines)

    def _apply_layout_formatting(self, text: str, layout_element: str) -> str:
        """
        Apply markdown formatting based on layout element type.

        Args:
            text: Clean text without font markers
            layout_element: Type of layout element (main_title, section_heading, etc.)

        Returns:
            Formatted markdown text
        """
        if not text:
            return ""

        if layout_element == "main_title":
            return f"# {text}"
        elif layout_element == "section_heading":
            return f"## {text}"
        elif layout_element == "subsection_heading":
            return f"### {text}"
        elif layout_element == "emphasis_text":
            return f"**{text}**"
        elif layout_element == "body_text":
            return text
        elif layout_element == "other":
            return text
        else:
            # Default to body text for unknown layout elements
            return text

    def _remove_font_markers(self, text: str) -> str:
        """
        Remove font markers from text when no mapping is available.

        Args:
            text: Raw OCR text with font markers

        Returns:
            Clean text without font markers
        """
        font_pattern = re.compile(r"\[\[\[[^\]]*\]\]\]")
        # Remove font markers and page delimiters for clean output
        cleaned_text = font_pattern.sub("", text)
        page_delimiter_pattern = re.compile(r"^--- Page [^-\n]* ---\n", re.MULTILINE)
        cleaned_text = page_delimiter_pattern.sub("", cleaned_text)
        return cleaned_text

    async def _store_formatted_text_artifacts(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        formatted_text: str,
        original_result: Dict[str, Any],  # Changed from TextExtractionResult
        params: dict,
    ) -> str:
        """
        Store formatted text as artifacts with real object storage.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            formatted_text: Formatted text content
            original_result: Original TextExtractionResult for metadata
            params: Processing parameters

        Returns:
            str: The artifact ID of the created formatted text artifact
        """
        try:
            # Upload formatted text to storage and get URI + SHA256
            formatted_text_uri, formatted_text_sha256 = (
                await self.storage_service.upload_text_blob(
                    formatted_text, content_hmac, "formatted_text"
                )
            )

            # Create formatted text artifact using existing full text artifact method
            # Since formatted text is a processed version of the full text
            formatted_text_artifact = (
                await self.artifacts_repo.insert_full_text_artifact(
                    content_hmac=content_hmac,
                    algorithm_version=algorithm_version,
                    params_fingerprint=params_fingerprint,
                    full_text_uri=formatted_text_uri,
                    full_text_sha256=formatted_text_sha256,
                    total_pages=original_result.get("total_pages")
                    or len(
                        original_result.get("pages", [])
                    ),  # Changed from original_result.total_pages
                    total_words=len(formatted_text.split()),
                    methods={
                        "extraction_methods": ["layout_formatting"],
                        "font_mapping": params.get("font_mapping", {}),
                        "algorithm": params.get("algorithm", "font_layout_mapping"),
                        "version": params.get("version", algorithm_version),
                        "original_extraction_methods": original_result.get(
                            "extraction_methods"
                        )  # Changed from original_result.extraction_methods
                        or [],
                    },
                    timings={
                        "layout_formatting_time": 0.1,  # Estimated processing time
                        "total_processing_time": 0.1,
                    },
                )
            )

            self._log_info(
                f"Stored formatted text artifact: {formatted_text_artifact.id}",
                extra={
                    "artifact_id": str(formatted_text_artifact.id),
                    "content_hmac": content_hmac,
                    "formatted_text_uri": formatted_text_uri,
                },
            )

            return str(formatted_text_artifact.id)

        except Exception as e:
            self._log_warning(f"Failed to store formatted text artifacts: {e}")
            raise

    def _record_execution(self):
        """Record that this node has been executed."""
        self._metrics["executions"] += 1

    def _record_success(self, duration: float):
        """Record successful execution with duration."""
        self._metrics["successes"] += 1
        self._metrics["total_duration"] += duration
        self._metrics["average_duration"] = (
            self._metrics["total_duration"] / self._metrics["successes"]
        )

    def _log_info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message with optional extra context."""
        if extra:
            self.logger.info(f"{message} - {extra}")
        else:
            self.logger.info(message)

    def _log_warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message with optional extra context."""
        if extra:
            self.logger.warning(f"{message} - {extra}")
        else:
            self.logger.warning(message)

    def _log_debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message with optional extra context."""
        if extra:
            self.logger.debug(f"{message} - {extra}")
        else:
            self.logger.debug(message)

    def _handle_error(
        self,
        state: DocumentProcessingState,
        error: Exception,
        error_message: str,
        error_context: Dict[str, Any],
    ) -> DocumentProcessingState:
        """Handle errors during execution."""
        self._metrics["failures"] += 1
        self.logger.error(
            f"Error in {self.node_name}: {error_message}",
            extra={"error": str(error), "context": error_context},
        )

        # Return state with error information
        error_state = state.copy()
        error_state["error"] = {
            "node": self.node_name,
            "message": error_message,
            "context": error_context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return error_state
