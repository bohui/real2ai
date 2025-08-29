"""
Unit tests for DetectDiagramsWithOCRNode
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from app.agents.nodes.step0_document_processing.detect_diagrams_with_ocr_node import DetectDiagramsWithOCRNode
from app.prompts.schema.diagram_detection_schema import DiagramDetectionItem
from app.models.supabase_models import DiagramType


class TestDetectDiagramsWithOCRNode:
    """Test cases for DetectDiagramsWithOCRNode"""

    @pytest.fixture
    def node(self):
        """Create a DetectDiagramsWithOCRNode instance for testing"""
        return DetectDiagramsWithOCRNode()

    @pytest.fixture
    def mock_state(self):
        """Create a mock state for testing"""
        return {
            "document_id": "test-doc-123",
            "storage_path": "/documents/test-document.pdf",
            "content_hash": "abc123",
            "use_llm": True
        }

    @pytest.fixture
    def mock_ocr_response(self):
        """Create a mock OCR service response"""
        return {
            "content": '{"diagram": [{"type": "floor_plan", "page": 1}, {"type": "site_plan", "page": 2}]}',
            "candidates": [],
            "usage_metadata": {}
        }

    @pytest.fixture
    def mock_diagram_detection_items(self):
        """Create mock diagram detection items"""
        return [
            DiagramDetectionItem(type=DiagramType.SITE_PLAN, page=1),
            DiagramDetectionItem(type=DiagramType.SURVEY_DIAGRAM, page=2)
        ]

    @pytest.mark.asyncio
    async def test_execute_success(self, node, mock_state, mock_ocr_response, mock_diagram_detection_items):
        """Test successful diagram detection execution"""
        
        # Setup mock text extraction result
        mock_text_result = Mock()
        mock_text_result.success = True
        mock_text_result.pages = [
            Mock(page_number=1, text="Some text", images_found=True),
            Mock(page_number=2, text="Another page", images_found=True)
        ]
        mock_state["text_extraction_result"] = mock_text_result
        
        # Mock the diagram detection methods
        with patch.object(node, '_initialize_services', new_callable=AsyncMock) as mock_init, \
             patch.object(node, '_process_pages_for_diagrams', new_callable=AsyncMock) as mock_process, \
             patch('app.core.config.get_settings') as mock_settings:
            
            # Setup mock settings
            mock_settings_obj = Mock()
            mock_settings_obj.diagram_detection_enabled = True
            mock_settings_obj.max_diagram_pages = 10
            mock_settings.return_value = mock_settings_obj
            
            # Setup mock process return value (returns tuple of diagrams, pages_to_process)
            mock_process.return_value = (mock_diagram_detection_items, [1, 2])
            
            # Execute the node
            result_state = await node.execute(mock_state)
            
            # Verify service initialization was called
            mock_init.assert_called_once()
            
            # Verify process pages was called
            mock_process.assert_called_once()
            
            # Verify result state
            assert "diagram_processing_result" in result_state
            detection_result = result_state["diagram_processing_result"]
            assert detection_result["success"] is True
            assert detection_result["total_diagrams"] == 2
            assert len(detection_result["diagrams"]) == 2
            assert detection_result["diagrams"][0].type == DiagramType.SITE_PLAN
            assert detection_result["diagrams"][1].type == DiagramType.SURVEY_DIAGRAM

    @pytest.mark.asyncio
    async def test_execute_missing_document_id(self, node):
        """Test execution with missing document ID"""
        
        state = {"storage_path": "/documents/test.pdf"}
        
        result_state = await node.execute(state)
        
        # Should set error in state
        assert "error" in result_state
        assert "Document ID and storage path are required" in result_state["error"]
        assert result_state["error_details"]["node"] == "detect_diagrams_with_ocr"

    @pytest.mark.asyncio
    async def test_execute_missing_storage_path(self, node):
        """Test execution with missing storage path"""
        
        state = {"document_id": "test-doc-123"}
        
        result_state = await node.execute(state)
        
        # Should set error in state
        assert "error" in result_state
        assert "Document ID and storage path are required" in result_state["error"]

    @pytest.mark.asyncio
    async def test_execute_ocr_service_failure(self, node, mock_state):
        """Test execution when diagram processing fails"""
        
        # Setup mock text extraction result
        mock_text_result = Mock()
        mock_text_result.success = True
        mock_text_result.pages = [
            Mock(page_number=1, text="Some text", images_found=True)
        ]
        mock_state["text_extraction_result"] = mock_text_result
        
        with patch.object(node, '_initialize_services', new_callable=AsyncMock) as mock_init, \
             patch.object(node, '_process_pages_for_diagrams', new_callable=AsyncMock,
                         side_effect=Exception("Diagram processing failed")) as mock_process, \
             patch('app.core.config.get_settings') as mock_settings:
            
            # Setup mock settings
            mock_settings_obj = Mock()
            mock_settings_obj.diagram_detection_enabled = True
            mock_settings_obj.max_diagram_pages = 10
            mock_settings.return_value = mock_settings_obj
            
            result_state = await node.execute(mock_state)
            
            # Should set error in state
            assert "error" in result_state
            assert "Diagram detection failed" in result_state["error"]
            assert "Diagram processing failed" in result_state["error"]

    @pytest.mark.asyncio
    async def test_detect_diagrams_for_page_success(self, node):
        """Test successful diagram detection for a single page"""
        
        # Mock dependencies
        with patch.object(node, '_render_page_to_jpg', new_callable=AsyncMock) as mock_render, \
             patch.object(node, '_persist_diagram', new_callable=AsyncMock) as mock_persist:
            
            # Setup mocks
            mock_render.return_value = b"fake_jpg_data"
            
            # Mock OCR service
            mock_ocr_service = AsyncMock()
            mock_llm_result = Mock()
            mock_llm_result.diagrams = [Mock(value="site_plan")]
            mock_ocr_service.extract_text_diagram_insight = AsyncMock(return_value=mock_llm_result)
            node.ocr_service = mock_ocr_service
            
            # Execute
            result = await node._detect_diagrams_for_page("test-doc", "/path/to/doc.pdf", 1)
            
            # Verify
            assert len(result) == 1
            assert result[0].type == "site_plan"
            assert result[0].page == 1
            
            # Verify persistence was called
            mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_diagrams_for_page_failure(self, node):
        """Test failure handling in diagram detection for a page"""
        
        # Mock dependencies to fail
        with patch.object(node, '_render_page_to_jpg', new_callable=AsyncMock) as mock_render:
            
            # Setup mocks to fail
            mock_render.side_effect = Exception("Failed to render page")
            
            # Execute
            result = await node._detect_diagrams_for_page("test-doc", "/path/to/doc.pdf", 1)
            
            # Should return empty list on failure
            assert result == []

    @pytest.mark.asyncio
    async def test_detect_diagrams_for_page_no_diagrams(self, node):
        """Test diagram detection when no diagrams are found"""
        
        # Mock dependencies
        with patch.object(node, '_render_page_to_jpg', new_callable=AsyncMock) as mock_render:
            
            # Setup mocks
            mock_render.return_value = b"fake_jpg_data"
            
            # Mock OCR service with no diagrams
            mock_ocr_service = AsyncMock()
            mock_llm_result = Mock()
            mock_llm_result.diagrams = []  # No diagrams found
            mock_ocr_service.extract_text_diagram_insight = AsyncMock(return_value=mock_llm_result)
            node.ocr_service = mock_ocr_service
            
            # Execute
            result = await node._detect_diagrams_for_page("test-doc", "/path/to/doc.pdf", 1)
            
            # Should return empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_render_page_to_jpg(self, node):
        """Test page rendering to JPG"""
        
        # Mock file storage read and PDF rendering
        with patch.object(node, '_read_file_from_storage', new_callable=AsyncMock) as mock_read, \
             patch('fitz.open') as mock_fitz:
            
            # Setup mocks
            mock_read.return_value = b"fake_pdf_content"
            
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_pix = MagicMock()
            # Set up the return values properly
            mock_pix.pil_tobytes.return_value = b"fake_jpg_bytes"
            mock_page.get_pixmap.return_value = mock_pix
            mock_doc.load_page.return_value = mock_page
            mock_fitz.return_value = mock_doc
            
            # Execute
            result = await node._render_page_to_jpg("/path/to/doc.pdf", 1)
            
            # Verify
            assert result == b"fake_jpg_bytes"
            mock_read.assert_called_once_with("/path/to/doc.pdf")


    def test_get_file_type_from_path(self, node):
        """Test file type extraction from path"""
        
        # Test various file extensions
        assert node._get_file_type_from_path("/path/to/file.pdf") == "pdf"
        assert node._get_file_type_from_path("/path/to/file.PNG") == "png"
        assert node._get_file_type_from_path("/path/to/file.jpg") == "jpeg"
        assert node._get_file_type_from_path("/path/to/file.jpeg") == "jpeg"
        assert node._get_file_type_from_path("/path/to/file.unknown") == "pdf"  # Default
        assert node._get_file_type_from_path("/path/to/file") == "pdf"  # No extension

    @pytest.mark.asyncio
    async def test_persist_diagram(self, node):
        """Test individual diagram persistence"""
        
        # Setup
        page_jpg_bytes = b"test_image_data"
        page_number = 1
        diagram = DiagramDetectionItem(type=DiagramType.SITE_PLAN, page=1)
        diagram_index = 1
        
        # Mock the visual artifact service
        mock_visual_service = AsyncMock()
        mock_visual_service.store_visual_artifact = AsyncMock(
            return_value=MagicMock(cache_hit=False)
        )
        node.visual_artifact_service = mock_visual_service
        
        # Mock state
        node._current_state = {
            "content_hmac": "test_hmac",
            "algorithm_version": 1,
            "params_fingerprint": "test_fingerprint"
        }
        
        # Execute
        await node._persist_diagram(page_jpg_bytes, page_number, diagram, diagram_index)
        
        # Verify
        mock_visual_service.store_visual_artifact.assert_called_once()
        call_args = mock_visual_service.store_visual_artifact.call_args
        
        # Check the diagram key format - now expects DiagramType.SITE_PLAN string representation
        assert call_args.kwargs["diagram_key"] == "page_1_diagram_1_DiagramType.SITE_PLAN"
        assert call_args.kwargs["artifact_type"] == "diagram"
        
        # Check diagram metadata
        diagram_meta = call_args.kwargs["diagram_meta"]
        assert diagram_meta["diagram_type"] == DiagramType.SITE_PLAN
        assert diagram_meta["diagram_index"] == 1
        assert diagram_meta["page_number"] == 1
        assert diagram_meta["detection_method"] == "ocr_detection"