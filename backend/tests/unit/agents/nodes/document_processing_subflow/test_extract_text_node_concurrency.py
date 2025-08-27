"""
Concurrency tests for ExtractTextNode per-page processing.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.document_processing_subflow.extract_text_node import (
    ExtractTextNode,
)


class _FakePage:
    def __init__(self, idx: int):
        self.idx = idx

    def get_text(self):
        # Force low-text to trigger OCR branch
        return ""

    def get_images(self):
        # Indicate presence of images to meet OCR trigger heuristics
        return [("img",)]


class _FakeDoc:
    def __init__(self, num_pages: int):
        self._n = num_pages

    def __len__(self):
        return self._n

    def load_page(self, idx: int):
        return _FakePage(idx)

    def close(self):
        pass


@pytest.mark.asyncio
async def test_per_page_concurrency_bounded_and_ordered():
    node = ExtractTextNode(use_llm=True, page_concurrency_limit=2)

    # Minimal state used by OCR branch
    state = {
        "document_id": "doc-1",
        "australian_state": "NSW",
        "contract_type": "purchase_agreement",
        "document_type": "contract",
        "content_hmac": "hmac",
        "params_fingerprint": "pf",
    }

    # Track concurrency inside mocked OCR call
    concurrency = {"current": 0, "max": 0}
    lock = asyncio.Lock()

    async def mock_extract_text_diagram_insight(**kwargs):
        filename = kwargs.get("filename", "page_0.png")
        async with lock:
            concurrency["current"] += 1
            concurrency["max"] = max(concurrency["max"], concurrency["current"])
        await asyncio.sleep(0.05)
        async with lock:
            concurrency["current"] -= 1
        # No diagrams; return OCR text only
        return SimpleNamespace(text=f"OCR {filename}", diagrams=[], text_confidence=0.9)

    class _Settings:
        enable_selective_ocr = True
        enable_tesseract_fallback = False

    with (
        patch(
            "app.agents.nodes.document_processing_subflow.extract_text_node.pymupdf"
        ) as mock_pymupdf,
        patch(
            "app.agents.nodes.document_processing_subflow.extract_text_node.get_settings",
            return_value=_Settings,
        ),
        patch.object(
            node,
            "_extract_page_text_with_fonts_excluding_headers_footers",
            return_value=("", ""),
        ),
        patch(
            "app.services.ai.gemini_ocr_service.GeminiOCRService"
        ) as MockGeminiService,
    ):
        mock_doc = _FakeDoc(3)
        mock_pymupdf.open.return_value = mock_doc

        # Mock Gemini service instance
        mock_service_instance = MockGeminiService.return_value
        mock_service_instance.initialize = AsyncMock()
        mock_service_instance.extract_text_diagram_insight = AsyncMock(
            side_effect=mock_extract_text_diagram_insight
        )

        # Execute the hybrid extractor directly
        result = await node._extract_pdf_text_hybrid(b"%PDF%", state)

    assert result.success is True
    # Ordering preserved by page index
    assert [p.page_number for p in result.pages] == [1, 2, 3]
    assert len(result.pages) == 3
    # Full text sections appear in order
    assert (
        result.full_text.find("page 1")
        < result.full_text.find("page 2")
        < result.full_text.find("page 3")
    )
    # Concurrency respected and bounded by semaphore
    assert concurrency["max"] <= 2
    assert concurrency["max"] >= 2


@pytest.mark.asyncio
async def test_shared_state_updates_with_diagrams_are_aggregated_correctly():
    node = ExtractTextNode(use_llm=True, page_concurrency_limit=3)

    state = {
        "document_id": "doc-2",
        "australian_state": "NSW",
        "contract_type": "purchase_agreement",
        "document_type": "contract",
        "content_hmac": "hmac",
        "params_fingerprint": "pf",
    }

    async def mock_extract_with_diagrams(**kwargs):
        # Return one diagram hint per page
        return SimpleNamespace(
            text="OCR text",
            diagrams=[SimpleNamespace(value="floor_plan")],
            text_confidence=0.9,
        )

    class _Settings:
        enable_selective_ocr = True
        enable_tesseract_fallback = False
        artifacts_algorithm_version = 1

    # Provide a mock VisualArtifactService to avoid real storage
    node.visual_artifact_service = MagicMock()
    node.visual_artifact_service.store_visual_artifact = AsyncMock(
        return_value=SimpleNamespace(cache_hit=False)
    )

    with (
        patch(
            "app.agents.nodes.document_processing_subflow.extract_text_node.pymupdf"
        ) as mock_pymupdf,
        patch(
            "app.agents.nodes.document_processing_subflow.extract_text_node.get_settings",
            return_value=_Settings,
        ),
        patch.object(
            node,
            "_extract_page_text_with_fonts_excluding_headers_footers",
            return_value=("", ""),
        ),
        patch(
            "app.services.ai.gemini_ocr_service.GeminiOCRService"
        ) as MockGeminiService,
    ):
        mock_doc = _FakeDoc(3)
        mock_pymupdf.open.return_value = mock_doc

        mock_service_instance = MockGeminiService.return_value
        mock_service_instance.initialize = AsyncMock()
        mock_service_instance.extract_text_diagram_insight = AsyncMock(
            side_effect=mock_extract_with_diagrams
        )

        result = await node._extract_pdf_text_hybrid(b"%PDF%", state)

    # One diagram per page, aggregated correctly
    dpr = node.diagram_processing_result
    assert dpr["success"] is True
    assert dpr["total_diagrams"] == 3
    assert sorted(dpr["diagram_pages"]) == [1, 2, 3]
    assert dpr["diagram_types"].get("floor_plan") == 3
    assert sorted(dpr["pages_processed"]) == [1, 2, 3]

    # Extraction result remains valid
    assert result.success is True
    assert len(result.pages) == 3
