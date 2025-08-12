"""
ParagraphSegmentationNode for Document Processing Subflow

This module implements paragraph segmentation for document processing.
It takes full_text from text extraction and segments it into paragraphs,
creating shared artifacts for reuse across users while maintaining
cross-page paragraph support via page_spans.
"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from uuid import UUID

from app.agents.nodes.document_processing_subflow.base_node import (
    DocumentProcessingNodeBase,
)
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.services.repositories.artifacts_repository import (
    ArtifactsRepository,
    ParagraphArtifact,
)
from app.utils.storage_utils import ArtifactStorageService
from app.utils.content_utils import compute_params_fingerprint, compute_content_hmac
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PageSpan:
    """Represents a span of text within a page"""

    page: int
    start: int
    end: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {"page": self.page, "start": self.start, "end": self.end}


@dataclass
class ParagraphSegment:
    """Represents a segmented paragraph with metadata"""

    paragraph_index: int
    text: str
    page_spans: List[PageSpan]
    start_offset: int
    end_offset: int
    normalization: Dict[str, bool]
    boundary_signals: Optional[Dict[str, Any]] = None


class ParagraphSegmentationNode(DocumentProcessingNodeBase):
    """
    Node for segmenting document text into paragraphs.

    Creates shared paragraph artifacts that can be reused across users
    and documents with the same content. Supports cross-page paragraphs
    via page_spans tracking.
    """

    def __init__(self):
        super().__init__("paragraph_segmentation")
        self.artifacts_repo = ArtifactsRepository()
        # Use 'documents' bucket to match the rest of the application
        self.storage_service = ArtifactStorageService(bucket_name="documents")

        # Get configuration
        settings = get_settings()
        self.paragraphs_enabled = getattr(settings, "paragraphs_enabled", True)
        self.algorithm_version = getattr(settings, "paragraph_algo_version", 1)
        self.paragraph_params = getattr(
            settings, "paragraph_params", self._get_default_params()
        )
        self.use_llm = getattr(settings, "paragraph_use_llm", False)

    def _get_default_params(self) -> Dict[str, Any]:
        """Get default paragraph segmentation parameters"""
        return {
            "min_paragraph_length": 10,
            "max_paragraph_length": 5000,
            "normalize_whitespace": True,
            "fix_hyphenation": True,
            "use_sentence_boundary": False,
            "merge_across_pages": True,
            "paragraph_break_patterns": [
                r"\n\s*\n",  # Double newline
                r"\.\s*\n\s*[A-Z]",  # Period followed by newline and capital
                r":\s*\n",  # Colon followed by newline
            ],
            "continuation_patterns": [
                r"-\s*\n\s*[a-z]",  # Hyphenated word continuation
                r",\s*\n",  # Comma continuation
                r"and\s*\n",  # 'and' continuation
            ],
        }

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Execute paragraph segmentation.

        Args:
            state: Current document processing state

        Returns:
            Updated state with paragraph information
        """
        start_time = time.time()

        try:
            # Check if paragraphs are enabled
            if not self.paragraphs_enabled:
                self._log_info("Paragraph processing disabled, skipping")
                return state

            # Validate required state
            text_result = state.get("text_extraction_result")
            if not text_result or not text_result.get("success"):
                self._log_warning(
                    "No text extraction result, skipping paragraph segmentation"
                )
                return state

            full_text = text_result.get("full_text", "")
            pages = text_result.get("pages", [])
            content_hmac = state.get("content_hmac")

            if not full_text:
                self._log_warning("Missing full_text, skipping paragraph segmentation")
                return state

            # Compute content_hmac if not provided
            if not content_hmac:
                try:
                    content_hmac = compute_content_hmac(full_text.encode("utf-8"))
                    self._log_info(
                        f"Computed content HMAC from full_text: {content_hmac}"
                    )
                    # Update state with computed HMAC
                    state = state.copy()
                    state["content_hmac"] = content_hmac
                except ValueError as e:
                    self._log_warning(
                        f"Cannot compute content HMAC for paragraph segmentation: {e}. "
                        "Skipping paragraph processing. Ensure DOCUMENT_HMAC_SECRET is configured."
                    )
                    return state

            # Compute parameters fingerprint
            params_fingerprint = compute_params_fingerprint(self.paragraph_params)

            self._log_info(
                f"Starting paragraph segmentation for {len(full_text)} characters",
                extra={
                    "algorithm_version": self.algorithm_version,
                    "paragraph_params_fingerprint": params_fingerprint,
                    "content_hmac": content_hmac,
                },
            )

            # Check for existing artifacts (idempotency)
            existing_artifacts = await self.artifacts_repo.get_paragraph_artifacts(
                content_hmac=content_hmac,
                algorithm_version=self.algorithm_version,
                params_fingerprint=params_fingerprint,
            )

            if existing_artifacts:
                self._log_info(
                    f"Found {len(existing_artifacts)} existing paragraph artifacts, reusing",
                    extra={
                        "paragraph_artifact_reuse_count": len(existing_artifacts),
                        "paragraph_artifact_created_count": 0,
                        "reuse_ratio": 1.0,
                        "algorithm_version": self.algorithm_version,
                        "paragraph_params_fingerprint": params_fingerprint,
                    },
                )
                # Build light paragraph metadata from existing artifacts
                paragraphs, paragraph_artifacts = self._build_paragraph_metadata(
                    existing_artifacts
                )
                duration = time.time() - start_time

                # Update state
                state = state.copy()
                state["paragraphs"] = paragraphs
                state["paragraph_artifacts"] = paragraph_artifacts
                state["paragraph_params_fingerprint"] = (
                    params_fingerprint  # For observability and caching
                )
                state.setdefault("processing_metrics", {}).update(
                    {
                        "paragraph_segmentation_duration_ms": duration * 1000,
                        "paragraphs_count": len(paragraphs),
                        "reuse_hit": True,
                        "reused_paragraphs_count": len(existing_artifacts),
                        "paragraph_algorithm_version": self.algorithm_version,
                        "paragraph_params_fingerprint": params_fingerprint,
                        "paragraph_artifact_created_count": 0,
                        "paragraph_artifact_reuse_count": len(existing_artifacts),
                        "reuse_ratio": 1.0,
                    }
                )

                self._record_success(duration)
                return state

            # Perform paragraph segmentation
            segments = await self._segment_paragraphs(full_text, pages)

            if not segments:
                self._log_warning("No paragraphs extracted")
                return state

            self._log_info(
                f"Segmented {len(segments)} paragraphs",
                extra={
                    "algorithm_version": self.algorithm_version,
                    "paragraph_params_fingerprint": params_fingerprint,
                },
            )

            # Upload paragraph texts and create artifacts with bounded concurrency
            # This also optimizes memory: only 8 paragraph texts held simultaneously
            semaphore = asyncio.Semaphore(8)  # Limit concurrent storage/DB operations

            async def _store_segment(segment):
                async with semaphore:
                    try:
                        # Upload paragraph text
                        first_page = (
                            segment.page_spans[0].page if segment.page_spans else 1
                        )
                        text_uri, text_sha256 = (
                            await self.storage_service.upload_paragraph_text(
                                paragraph_text=segment.text,
                                content_hmac=content_hmac,
                                page_number=first_page,
                                paragraph_index=segment.paragraph_index,
                            )
                        )

                        # Prepare features JSON
                        features = {
                            "page_spans": [
                                span.to_dict() for span in segment.page_spans
                            ],
                            "start_offset": segment.start_offset,
                            "end_offset": segment.end_offset,
                            "normalization": segment.normalization,
                            "offsets_normalized": True,  # Clarify that offsets are in normalized coordinate system
                            "document_paragraph_index": segment.paragraph_index,  # For clarity and stability
                        }

                        if segment.boundary_signals:
                            features["boundary_signals"] = segment.boundary_signals

                        # Insert artifact
                        artifact = await self.artifacts_repo.insert_paragraph_artifact(
                            content_hmac=content_hmac,
                            algorithm_version=self.algorithm_version,
                            params_fingerprint=params_fingerprint,
                            page_number=first_page,
                            paragraph_index=segment.paragraph_index,
                            paragraph_text_uri=text_uri,
                            paragraph_text_sha256=text_sha256,
                            features=features,
                        )

                        return artifact

                    except Exception as e:
                        self._log_warning(
                            f"Failed to process paragraph {segment.paragraph_index}: {e}",
                            extra={
                                "paragraph_index": segment.paragraph_index,
                                "algorithm_version": self.algorithm_version,
                                "paragraph_params_fingerprint": params_fingerprint,
                                "content_hmac": content_hmac,
                                "error_type": type(e).__name__,
                            },
                        )
                        return None

            # Execute all storage operations concurrently with bounded semaphore
            artifact_results = await asyncio.gather(
                *[_store_segment(s) for s in segments], return_exceptions=False
            )
            artifacts = [a for a in artifact_results if a is not None]

            # Build light paragraph metadata
            paragraphs, paragraph_artifacts = self._build_paragraph_metadata(artifacts)

            # Calculate metrics
            duration = time.time() - start_time
            avg_length = (
                sum(len(s.text) for s in segments) / len(segments) if segments else 0
            )
            created_count = len(artifacts)
            reuse_ratio = 0.0  # All newly created

            # Update state
            state = state.copy()
            state["paragraphs"] = paragraphs
            state["paragraph_artifacts"] = paragraph_artifacts
            state["paragraph_params_fingerprint"] = (
                params_fingerprint  # For observability and caching
            )
            state.setdefault("processing_metrics", {}).update(
                {
                    "paragraph_segmentation_duration_ms": duration * 1000,
                    "paragraphs_count": len(paragraphs),
                    "avg_paragraph_len": avg_length,
                    "reuse_hit": False,
                    "reused_paragraphs_count": 0,
                    "paragraph_algorithm_version": self.algorithm_version,
                    "paragraph_params_fingerprint": params_fingerprint,
                    "paragraph_artifact_created_count": created_count,
                    "paragraph_artifact_reuse_count": 0,
                    "reuse_ratio": reuse_ratio,
                }
            )

            self._log_info(
                f"Paragraph segmentation completed in {duration:.2f}s",
                extra={
                    "paragraphs_count": len(paragraphs),
                    "avg_paragraph_len": avg_length,
                    "paragraph_artifact_created_count": created_count,
                    "paragraph_artifact_reuse_count": 0,
                    "reuse_ratio": reuse_ratio,
                    "algorithm_version": self.algorithm_version,
                    "paragraph_params_fingerprint": params_fingerprint,
                },
            )
            self._record_success(duration)
            return state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                "Paragraph segmentation failed",
                {"paragraphs_enabled": self.paragraphs_enabled},
            )

    def _build_paragraph_metadata(
        self, artifacts: List[ParagraphArtifact]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Build light paragraph metadata from artifacts.

        Args:
            artifacts: List of paragraph artifacts

        Returns:
            Tuple of (paragraphs, paragraph_artifacts)
        """
        paragraphs = []
        paragraph_artifacts = []

        for artifact in artifacts:
            features = artifact.features or {}

            # Light paragraph structure
            paragraph = {
                "artifact_id": str(artifact.id),
                "paragraph_index": artifact.paragraph_index,
                "page_spans": features.get("page_spans", []),
                "start_offset": features.get("start_offset"),
                "end_offset": features.get("end_offset"),
            }
            paragraphs.append(paragraph)

            # Artifact metadata
            artifact_meta = {
                "id": str(artifact.id),
                "paragraph_index": artifact.paragraph_index,
                "page_number": artifact.page_number,
                "text_uri": artifact.paragraph_text_uri,
                "features": features,
            }
            paragraph_artifacts.append(artifact_meta)

        return paragraphs, paragraph_artifacts

    async def _segment_paragraphs(
        self, full_text: str, pages: List[Dict[str, Any]]
    ) -> List[ParagraphSegment]:
        """
        Segment full text into paragraphs.

        Args:
            full_text: Complete document text
            pages: List of page metadata

        Returns:
            List of paragraph segments
        """
        # Normalize text
        normalized_text, normalization = self._normalize_text(full_text)

        # Build page offset map for cross-page tracking using normalized coordinates
        page_offset_map = self._build_normalized_page_offset_map(
            pages, normalized_text, normalization
        )

        # Find paragraph boundaries
        paragraph_boundaries = self._find_paragraph_boundaries(normalized_text)

        # Create paragraph segments
        segments = []
        for i, (start, end) in enumerate(paragraph_boundaries):
            text = normalized_text[start:end].strip()

            if len(text) < self.paragraph_params["min_paragraph_length"]:
                continue

            # Find page spans for this paragraph
            page_spans = self._find_page_spans(start, end, page_offset_map)

            segment = ParagraphSegment(
                paragraph_index=i,
                text=text,
                page_spans=page_spans,
                start_offset=start,
                end_offset=end,
                normalization=normalization,
            )
            segments.append(segment)

        return segments

    def _normalize_text(self, text: str) -> Tuple[str, Dict[str, bool]]:
        """
        Normalize text for paragraph segmentation.

        Args:
            text: Input text

        Returns:
            Tuple of (normalized_text, normalization_info)
        """
        normalized = text
        normalization = {"whitespace_normalized": False, "hyphenation_fixed": False}

        # Normalize whitespace
        if self.paragraph_params["normalize_whitespace"]:
            # Replace multiple whitespace with single space, preserve paragraph breaks
            normalized = re.sub(r"[ \t]+", " ", normalized)
            normalized = re.sub(r"\r\n", "\n", normalized)  # Windows line endings
            normalization["whitespace_normalized"] = True

        # Fix soft hyphenation across page breaks
        if self.paragraph_params["fix_hyphenation"]:
            # Pattern: word-<whitespace/newline>word -> wordword
            normalized = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", normalized)
            normalization["hyphenation_fixed"] = True

        return normalized, normalization

    def _build_page_offset_map(
        self, pages: List[Dict[str, Any]], full_text: str
    ) -> List[Dict[str, Any]]:
        """
        Build mapping of text offsets to page numbers.

        This must match the exact assembly used in ExtractTextNode:
        full_text_parts.append(f"\n--- Page {idx + 1} ---\n{text_to_use}")

        Args:
            pages: Page metadata from text extraction result
            full_text: Full document text as assembled by ExtractTextNode

        Returns:
            List of page offset mappings
        """
        page_map = []
        current_offset = 0

        for idx, page_info in enumerate(pages):
            # Handle both PageExtraction objects and dict representations
            if hasattr(page_info, "text_content"):
                page_text = page_info.text_content
                page_number = page_info.page_number
            else:
                page_text = page_info.get("text_content", "")
                page_number = page_info.get("page_number", idx + 1)

            # Calculate the exact page header and content as assembled in ExtractTextNode
            page_header = f"\n--- Page {page_number} ---\n"
            page_content_with_header = page_header + page_text

            # Skip the initial newline for first page if full_text doesn't start with it
            if idx == 0 and not full_text.startswith("\n"):
                page_header = page_header.lstrip("\n")
                page_content_with_header = page_header + page_text

            # Map offsets within the assembled full_text
            start_offset = current_offset
            content_start_offset = start_offset + len(page_header)
            end_offset = start_offset + len(page_content_with_header)

            page_map.append(
                {
                    "page_number": page_number,
                    "start_offset": content_start_offset,  # Start after header
                    "end_offset": end_offset,
                    "text_length": len(page_text),
                    "header_length": len(page_header),
                    "total_length": len(page_content_with_header),
                }
            )

            current_offset = end_offset

        return page_map

    def _build_normalized_page_offset_map(
        self,
        pages: List[Dict[str, Any]],
        normalized_full_text: str,
        normalization: Dict[str, bool],
    ) -> List[Dict[str, Any]]:
        """
        Build mapping of normalized text offsets to page numbers.

        This applies the same normalization to each page's content and headers
        as was applied to the full_text, ensuring coordinate system alignment.

        Args:
            pages: Page metadata from text extraction result
            normalized_full_text: Full document text after normalization
            normalization: Normalization operations that were applied

        Returns:
            List of page offset mappings in normalized coordinate system
        """
        page_map = []
        current_offset = 0
        logger.info(f"Normalized full text: {normalized_full_text}")

        for idx, page_info in enumerate(pages):
            # Handle both PageExtraction objects and dict representations
            if hasattr(page_info, "text_content"):
                page_text = page_info.text_content
                page_number = page_info.page_number
            else:
                page_text = page_info.get("text_content", "")
                page_number = page_info.get("page_number", idx + 1)

            # Calculate the exact page header and content as assembled in ExtractTextNode
            page_header = f"\n--- Page {page_number} ---\n"
            page_content_with_header = page_header + page_text

            # Skip the initial newline for first page if full_text doesn't start with it
            if idx == 0 and not normalized_full_text.startswith("\n"):
                page_header = page_header.lstrip("\n")
                page_content_with_header = page_header + page_text

            # Apply the same normalization to this page's content
            normalized_page_content, _ = self._normalize_text(page_content_with_header)

            # Calculate normalized lengths
            normalized_header = page_header
            if normalization.get("whitespace_normalized"):
                normalized_header = re.sub(r"[ \t]+", " ", normalized_header)
                normalized_header = re.sub(r"\r\n", "\n", normalized_header)

            # Map offsets within the normalized full_text
            start_offset = current_offset
            content_start_offset = start_offset + len(normalized_header)
            end_offset = start_offset + len(normalized_page_content)

            page_map.append(
                {
                    "page_number": page_number,
                    "start_offset": content_start_offset,  # Start after header
                    "end_offset": end_offset,
                    "text_length": len(normalized_page_content)
                    - len(normalized_header),
                    "header_length": len(normalized_header),
                    "total_length": len(normalized_page_content),
                }
            )

            current_offset = end_offset

        return page_map

    def _find_page_spans(
        self, start_offset: int, end_offset: int, page_offset_map: List[Dict[str, Any]]
    ) -> List[PageSpan]:
        """
        Find which pages a paragraph spans across.

        Args:
            start_offset: Paragraph start in full text
            end_offset: Paragraph end in full text
            page_offset_map: Page offset mappings

        Returns:
            List of PageSpan objects
        """
        spans = []

        for page_info in page_offset_map:
            page_start = page_info["start_offset"]
            page_end = page_info["end_offset"]
            page_number = page_info["page_number"]

            # Check if paragraph overlaps with this page
            if end_offset <= page_start or start_offset >= page_end:
                continue  # No overlap

            # Calculate overlap
            overlap_start = (
                max(start_offset, page_start) - page_start
            )  # Relative to page
            overlap_end = min(end_offset, page_end) - page_start  # Relative to page

            spans.append(
                PageSpan(page=page_number, start=overlap_start, end=overlap_end)
            )

        return spans

    def _find_paragraph_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """
        Find paragraph boundaries in text.

        Args:
            text: Normalized text

        Returns:
            List of (start, end) tuples for each paragraph
        """
        # Combine break patterns
        break_patterns = self.paragraph_params["paragraph_break_patterns"]
        combined_pattern = "|".join(f"({pattern})" for pattern in break_patterns)

        if not combined_pattern:
            # Fallback: split on double newlines
            combined_pattern = r"\n\s*\n"

        # Find all break positions
        boundaries = []
        current_start = 0

        for match in re.finditer(combined_pattern, text):
            # End current paragraph before the break
            current_end = match.start()

            if current_end > current_start:
                boundaries.append((current_start, current_end))

            # Start next paragraph after the break
            current_start = match.end()

        # Handle final paragraph
        if current_start < len(text):
            boundaries.append((current_start, len(text)))

        # Filter out very short paragraphs and merge if needed
        return self._filter_and_merge_boundaries(boundaries, text)

    def _filter_and_merge_boundaries(
        self, boundaries: List[Tuple[int, int]], text: str
    ) -> List[Tuple[int, int]]:
        """
        Filter short paragraphs and merge when appropriate.

        Args:
            boundaries: Initial paragraph boundaries
            text: Full text

        Returns:
            Filtered paragraph boundaries
        """
        min_length = self.paragraph_params["min_paragraph_length"]
        max_length = self.paragraph_params["max_paragraph_length"]
        filtered = []

        for start, end in boundaries:
            paragraph_text = text[start:end].strip()

            if len(paragraph_text) < min_length:
                # Try to merge with previous paragraph
                if filtered and len(paragraph_text) > 0:
                    prev_start, _ = filtered[-1]
                    merged_text = text[prev_start:end].strip()

                    if len(merged_text) <= max_length:
                        # Merge with previous
                        filtered[-1] = (prev_start, end)
                        continue

                # Skip if too short and can't merge
                continue

            elif len(paragraph_text) > max_length:
                # Split long paragraphs at sentence boundaries
                split_boundaries = self._split_long_paragraph(start, end, text)
                filtered.extend(split_boundaries)
            else:
                filtered.append((start, end))

        return filtered

    def _split_long_paragraph(
        self, start: int, end: int, text: str
    ) -> List[Tuple[int, int]]:
        """
        Split a long paragraph at sentence boundaries.

        Args:
            start: Paragraph start offset
            end: Paragraph end offset
            text: Full text

        Returns:
            List of split paragraph boundaries
        """
        max_length = self.paragraph_params["max_paragraph_length"]
        paragraph_text = text[start:end]

        # Find sentence boundaries within the paragraph
        sentence_pattern = r"[.!?]+\s+"
        sentences = []
        current_start = 0

        for match in re.finditer(sentence_pattern, paragraph_text):
            sentence_end = match.end()
            sentences.append((current_start, sentence_end))
            current_start = sentence_end

        # Add final sentence if exists
        if current_start < len(paragraph_text):
            sentences.append((current_start, len(paragraph_text)))

        # Group sentences into chunks under max_length
        chunks = []
        current_chunk_start = 0
        current_chunk_length = 0

        for sent_start, sent_end in sentences:
            sentence_length = sent_end - sent_start

            if (
                current_chunk_length + sentence_length > max_length
                and current_chunk_length > 0
            ):
                # Start new chunk
                chunks.append((start + current_chunk_start, start + sent_start))
                current_chunk_start = sent_start
                current_chunk_length = sentence_length
            else:
                current_chunk_length = sent_end - current_chunk_start

        # Add final chunk
        if current_chunk_start < len(paragraph_text):
            chunks.append((start + current_chunk_start, end))

        return chunks if chunks else [(start, end)]

    async def cleanup(self):
        """Cleanup resources"""
        if self.artifacts_repo:
            await self.artifacts_repo.close()
