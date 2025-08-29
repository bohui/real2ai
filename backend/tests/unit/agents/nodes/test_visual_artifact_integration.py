"""
Integration tests for nodes using VisualArtifactService
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.agents.nodes.step0_document_processing.extract_text_node import ExtractTextNode
from app.agents.nodes.step0_document_processing.detect_diagrams_with_ocr_node import DetectDiagramsWithOCRNode
from app.agents.nodes.step0_document_processing.save_page_jpg_node import SavePageJPGAsArtifactPagesJPGNode
from app.services.visual_artifact_service import VisualArtifactService, VisualArtifactResult
from app.schema.document import TextExtractionResult, PageExtraction, ContentAnalysis, LayoutFeatures


@pytest.fixture
def mock_visual_artifact_service():
    """Mock VisualArtifactService."""
    service = MagicMock(spec=VisualArtifactService)
    service.store_visual_artifact = AsyncMock(
        return_value=VisualArtifactResult(
            artifact_id="test-artifact-id",
            image_uri="supabase://artifacts/test.jpg",
            image_sha256="sha256_test",
            cache_hit=False
        )
    )
    return service


@pytest.fixture
def sample_state():
    """Create sample processing state."""
    return {
        "document_id": str(uuid.uuid4()),
        "storage_path": "test/document.pdf",
        "file_type": "application/pdf",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "australian_state": "NSW",
        "contract_type": "purchase_agreement",
        "document_type": "contract",
    }


@pytest.fixture
def sample_text_extraction_result():
    """Create sample text extraction result."""
    page = PageExtraction(
        page_number=1,
        text_content="Test content with diagram keywords",
        text_length=100,
        word_count=20,
        extraction_method="pymupdf",
        confidence=0.8,
        content_analysis=ContentAnalysis(
            content_types=["text", "diagram"],
            primary_type="text",
            layout_features=LayoutFeatures(
                has_header=False,
                has_footer=False,
                has_signatures=False,
                has_diagrams=True,
                has_tables=False,
            ),
            quality_indicators=None,
        )
    )
    
    return TextExtractionResult(
        success=True,
        full_text="Test content with diagram keywords",
        pages=[page],
        total_pages=1,
        extraction_methods=["pymupdf"],
        total_word_count=20,
        overall_confidence=0.8,
        processing_time=1.0,
    )


class TestExtractTextNodeIntegration:
    """Test ExtractTextNode with VisualArtifactService integration."""
    
    @pytest.mark.asyncio
    async def test_extract_text_with_diagram_hints_uses_visual_service(
        self, sample_state, mock_visual_artifact_service
    ):
        """Test that extract_text_node uses VisualArtifactService for diagram hints."""
        node = ExtractTextNode(use_llm=True)
        node.visual_artifact_service = mock_visual_artifact_service
        
        # Mock the LLM result with diagrams
        mock_llm_result = MagicMock()
        mock_llm_result.text = "OCR extracted text"
        mock_llm_result.diagrams = ["floor_plan", "site_plan"]
        mock_llm_result.text_confidence = 0.95
        
        with patch.object(node, '_render_page_png', return_value=b"mock_png_data"), \
             patch.object(node, 'get_user_client') as mock_client, \
             patch('app.agents.nodes.document_processing_subflow.extract_text_node.get_settings') as mock_settings:
            
            # Setup mocks
            mock_settings.return_value.artifacts_algorithm_version = 1
            mock_client.return_value.download_file = AsyncMock(return_value=b"mock_pdf_data")
            
            # Mock the OCR service
            with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as MockGeminiService:
                mock_service_instance = MockGeminiService.return_value
                mock_service_instance.initialize = AsyncMock()
                mock_service_instance.extract_text_diagram_insight = AsyncMock(return_value=mock_llm_result)
                
                # Execute with sample state
                state_with_result = sample_state.copy()
                
                # Mock PDF processing
                with patch('app.agents.nodes.document_processing_subflow.extract_text_node.pymupdf'):
                    result_state = await node.execute(state_with_result)
        
        # Verify VisualArtifactService was called for each diagram
        assert mock_visual_artifact_service.store_visual_artifact.call_count == 2
        
        # Verify the calls include diagram metadata
        calls = mock_visual_artifact_service.store_visual_artifact.call_args_list
        for i, call in enumerate(calls, 1):
            assert call.kwargs["artifact_type"] == "diagram"
            assert call.kwargs["page_number"] == 1
            assert f"llm_ocr_hint_page_1_{i:02d}" in call.kwargs["diagram_key"]
            assert call.kwargs["diagram_meta"]["detection_method"] == "llm_ocr_hint"
    
    @pytest.mark.asyncio
    async def test_extract_text_handles_visual_service_error(
        self, sample_state, mock_visual_artifact_service
    ):
        """Test that extract_text_node handles VisualArtifactService errors gracefully."""
        node = ExtractTextNode(use_llm=True)
        node.visual_artifact_service = mock_visual_artifact_service
        
        # Make the service raise an exception
        mock_visual_artifact_service.store_visual_artifact.side_effect = Exception("Storage error")
        
        # Mock the LLM result with diagrams
        mock_llm_result = MagicMock()
        mock_llm_result.text = "OCR extracted text"
        mock_llm_result.diagrams = ["floor_plan"]
        mock_llm_result.text_confidence = 0.95
        
        with patch.object(node, '_render_page_png', return_value=b"mock_png_data"), \
             patch.object(node, 'get_user_client') as mock_client, \
             patch('app.agents.nodes.document_processing_subflow.extract_text_node.get_settings') as mock_settings:
            
            mock_settings.return_value.artifacts_algorithm_version = 1
            mock_client.return_value.download_file = AsyncMock(return_value=b"mock_pdf_data")
            
            with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as MockGeminiService:
                mock_service_instance = MockGeminiService.return_value
                mock_service_instance.initialize = AsyncMock()
                mock_service_instance.extract_text_diagram_insight = AsyncMock(return_value=mock_llm_result)
                
                with patch('app.agents.nodes.document_processing_subflow.extract_text_node.pymupdf'):
                    result_state = await node.execute(sample_state.copy())
        
        # Should not fail the entire extraction due to visual service error
        assert "error" not in result_state


class TestDetectDiagramsWithOCRNodeIntegration:
    """Test DetectDiagramsWithOCRNode with VisualArtifactService integration."""
    
    @pytest.mark.asyncio
    async def test_detect_diagrams_uses_visual_service_for_page_jpg(
        self, sample_state, sample_text_extraction_result, mock_visual_artifact_service
    ):
        """Test that detect_diagrams node uses VisualArtifactService for page JPGs."""
        node = DetectDiagramsWithOCRNode()
        node.visual_artifact_service = mock_visual_artifact_service
        
        # Prepare state with text extraction result
        state_with_result = sample_state.copy()
        state_with_result["text_extraction_result"] = sample_text_extraction_result
        
        # Mock the OCR service and diagram detection
        mock_llm_result = MagicMock()
        mock_llm_result.diagrams = [MagicMock(value="floor_plan")]
        
        with patch.object(node, '_render_page_to_jpg', return_value=b"mock_jpg_data"), \
             patch.object(node, 'get_user_client'), \
             patch('app.core.config.get_settings') as mock_settings:
            
            mock_settings.return_value.diagram_detection_enabled = True
            mock_settings.return_value.max_diagram_pages = 10
            
            # Mock OCR service
            node.ocr_service = MagicMock()
            node.ocr_service.extract_text_diagram_insight = AsyncMock(return_value=mock_llm_result)
            
            result_state = await node.execute(state_with_result)
        
        # Verify VisualArtifactService was called
        mock_visual_artifact_service.store_visual_artifact.assert_called_once()
        
        call = mock_visual_artifact_service.store_visual_artifact.call_args
        assert call.kwargs["artifact_type"] == "image_jpg"
        assert call.kwargs["page_number"] == 1
        assert call.kwargs["diagram_key"] == "page_jpg_1"
        assert call.kwargs["image_metadata"]["format"] == "jpeg"


class TestSavePageJPGNodeIntegration:
    """Test SavePageJPGAsArtifactPagesJPGNode with VisualArtifactService integration."""
    
    @pytest.mark.asyncio
    async def test_save_page_jpg_uses_visual_service(
        self, sample_state, mock_visual_artifact_service, tmp_path
    ):
        """Test that save_page_jpg node uses VisualArtifactService."""
        node = SavePageJPGAsArtifactPagesJPGNode()
        node.visual_artifact_service = mock_visual_artifact_service
        
        # Create a temporary JPG file
        jpg_file = tmp_path / "page_1.jpg"
        jpg_file.write_bytes(b"mock_jpg_content")
        
        # Prepare state with OCR pages
        state_with_ocr = sample_state.copy()
        state_with_ocr["ocr_pages"] = [
            {
                "page_number": 1,
                "jpg_path": str(jpg_file),
            }
        ]
        
        result_state = await node.execute(state_with_ocr)
        
        # Verify VisualArtifactService was called
        mock_visual_artifact_service.store_visual_artifact.assert_called_once()
        
        call = mock_visual_artifact_service.store_visual_artifact.call_args
        assert call.kwargs["artifact_type"] == "image_jpg"
        assert call.kwargs["page_number"] == 1
        assert call.kwargs["diagram_key"] == "page_image_1"
        assert call.kwargs["image_metadata"]["extraction_method"] == "external_ocr"
        
        # Verify state was updated with artifact information
        assert "diagram_artifacts" in result_state
        assert len(result_state["diagram_artifacts"]) == 1
        assert result_state["diagram_artifacts"][0]["cache_hit"] is False


class TestVisualArtifactServiceCacheIntegration:
    """Test cache behavior across multiple node operations."""
    
    @pytest.mark.asyncio
    async def test_cache_sharing_across_nodes(self, sample_state):
        """Test that cache is shared when using the same VisualArtifactService instance."""
        # Create a real service (not mocked) for cache testing
        mock_storage = MagicMock()
        mock_storage.upload_page_image_jpg = AsyncMock(
            return_value=("test_uri", "test_sha256")
        )
        
        mock_repo = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.id = "test-id"
        mock_repo.insert_unified_visual_artifact = AsyncMock(return_value=mock_artifact)
        
        service = VisualArtifactService(
            storage_service=mock_storage,
            artifacts_repo=mock_repo,
            cache_ttl=60
        )
        
        # First call
        result1 = await service.store_visual_artifact(
            image_bytes=b"test_image",
            content_hmac="test_hmac",
            algorithm_version=1,
            params_fingerprint="test_fp",
            page_number=1,
            diagram_key="test_key",
            artifact_type="diagram"
        )
        assert result1.cache_hit is False
        
        # Second call with same parameters
        result2 = await service.store_visual_artifact(
            image_bytes=b"test_image",
            content_hmac="test_hmac",
            algorithm_version=1,
            params_fingerprint="test_fp",
            page_number=1,
            diagram_key="test_key",
            artifact_type="diagram"
        )
        assert result2.cache_hit is True
        
        # Verify storage was only called once
        assert mock_storage.upload_page_image_jpg.call_count == 1
        assert mock_repo.insert_unified_visual_artifact.call_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_eviction_with_size_limit(self):
        """Test cache eviction when size limit is reached."""
        mock_storage = MagicMock()
        mock_storage.upload_page_image_jpg = AsyncMock(
            return_value=("test_uri", "test_sha256")
        )
        
        mock_repo = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.id = "test-id"
        mock_repo.insert_unified_visual_artifact = AsyncMock(return_value=mock_artifact)
        
        service = VisualArtifactService(
            storage_service=mock_storage,
            artifacts_repo=mock_repo,
            cache_ttl=60
        )
        # Set small cache size for testing
        service._max_cache_size = 2
        
        # Fill cache beyond capacity
        for i in range(3):
            await service.store_visual_artifact(
                image_bytes=f"test_image_{i}".encode(),
                content_hmac="test_hmac",
                algorithm_version=1,
                params_fingerprint="test_fp",
                page_number=i + 1,
                diagram_key=f"test_key_{i}",
                artifact_type="diagram"
            )
        
        # Cache should not exceed max size
        stats = service.get_cache_stats()
        assert stats["total_entries"] <= service._max_cache_size


@pytest.mark.asyncio
async def test_error_handling_in_visual_service_integration():
    """Test error handling when VisualArtifactService operations fail."""
    mock_storage = MagicMock()
    mock_storage.upload_page_image_jpg = AsyncMock(side_effect=Exception("Upload failed"))
    
    mock_repo = MagicMock()
    
    service = VisualArtifactService(
        storage_service=mock_storage,
        artifacts_repo=mock_repo
    )
    
    # Should propagate the exception
    with pytest.raises(Exception, match="Upload failed"):
        await service.store_visual_artifact(
            image_bytes=b"test_image",
            content_hmac="test_hmac",
            algorithm_version=1,
            params_fingerprint="test_fp",
            page_number=1,
            diagram_key="test_key",
            artifact_type="diagram"
        )
    
    # Verify nothing was cached
    stats = service.get_cache_stats()
    assert stats["total_entries"] == 0