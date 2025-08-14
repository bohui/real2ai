"""
Unit tests for DetectDiagramsWithOCRNode
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.agents.nodes.document_processing_subflow.detect_diagrams_with_ocr_node import DetectDiagramsWithOCRNode
from app.prompts.schema.diagram_detection_schema import DiagramDetectionResponse, DiagramDetectionItem
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
    def mock_diagram_detection_response(self):
        """Create a mock diagram detection response"""
        return DiagramDetectionResponse(
            diagram=[
                DiagramDetectionItem(type=DiagramType.FLOOR_PLAN, page=1),
                DiagramDetectionItem(type=DiagramType.SITE_PLAN, page=2)
            ]
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, node, mock_state, mock_ocr_response, mock_diagram_detection_response):
        """Test successful diagram detection execution"""
        
        # Mock the OCR service and parser
        with patch.object(node, '_initialize_services', new_callable=AsyncMock) as mock_init, \
             patch.object(node, '_detect_diagrams_with_ocr', new_callable=AsyncMock, 
                         return_value=mock_ocr_response) as mock_ocr, \
             patch.object(node, '_parse_diagram_response', new_callable=AsyncMock,
                         return_value=mock_diagram_detection_response) as mock_parse:
            
            # Execute the node
            result_state = await node.execute(mock_state)
            
            # Verify service initialization was called
            mock_init.assert_called_once()
            
            # Verify OCR service was called with correct parameters
            mock_ocr.assert_called_once()
            args, kwargs = mock_ocr.call_args
            assert args[0] == "/documents/test-document.pdf"  # storage_path
            assert "Diagram detection only" in args[1]  # prompt contains expected text
            
            # Verify parser was called
            mock_parse.assert_called_once_with(mock_ocr_response)
            
            # Verify result state
            assert "diagram_detection_result" in result_state
            detection_result = result_state["diagram_detection_result"]
            assert detection_result["success"] is True
            assert detection_result["total_diagrams"] == 2
            assert len(detection_result["diagrams"]) == 2
            assert detection_result["diagrams"][0].type == DiagramType.FLOOR_PLAN
            assert detection_result["diagrams"][1].type == DiagramType.SITE_PLAN

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
        """Test execution when OCR service fails"""
        
        with patch.object(node, '_initialize_services', new_callable=AsyncMock) as mock_init, \
             patch.object(node, '_detect_diagrams_with_ocr', new_callable=AsyncMock,
                         side_effect=Exception("OCR service failed")) as mock_ocr:
            
            result_state = await node.execute(mock_state)
            
            # Should set error in state
            assert "error" in result_state
            assert "Diagram detection failed" in result_state["error"]
            assert "OCR service failed" in result_state["error"]

    @pytest.mark.asyncio
    async def test_parse_diagram_response_success(self, node, mock_diagram_detection_response):
        """Test successful parsing of diagram response"""
        
        ocr_response = {
            "content": '{"diagram": [{"type": "floor_plan", "page": 1}]}'
        }
        
        with patch.object(node.parser, 'parse', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = Mock(
                success=True,
                data=mock_diagram_detection_response
            )
            
            result = await node._parse_diagram_response(ocr_response)
            
            assert result == mock_diagram_detection_response
            mock_parse.assert_called_once_with('{"diagram": [{"type": "floor_plan", "page": 1}]}')

    @pytest.mark.asyncio
    async def test_parse_diagram_response_parse_failure(self, node):
        """Test parsing failure handling"""
        
        ocr_response = {
            "content": "invalid json"
        }
        
        with patch.object(node.parser, 'parse', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = Mock(
                success=False,
                error_message="Invalid JSON format"
            )
            
            result = await node._parse_diagram_response(ocr_response)
            
            # Should return empty diagram list on parse failure
            assert isinstance(result, DiagramDetectionResponse)
            assert len(result.diagram) == 0

    @pytest.mark.asyncio
    async def test_parse_diagram_response_empty_content(self, node):
        """Test parsing with empty content"""
        
        ocr_response = {}
        
        result = await node._parse_diagram_response(ocr_response)
        
        # Should return empty diagram list
        assert isinstance(result, DiagramDetectionResponse)
        assert len(result.diagram) == 0

    def test_create_diagram_detection_prompt(self, node):
        """Test diagram detection prompt creation"""
        
        prompt = node._create_diagram_detection_prompt()
        
        # Verify prompt contains expected elements
        assert "Diagram detection only" in prompt
        assert "diagram (array)" in prompt
        assert "site_plan" in prompt
        assert "floor_plan" in prompt
        assert "unknown" in prompt
        assert "Page numbers are 1-based" in prompt

    def test_validate_diagram_data(self, node):
        """Test diagram data validation"""
        
        input_diagrams = [
            {"type": "floor_plan", "page": 1},
            {"type": "invalid_type", "page": 2},  # Invalid type
            {"type": "site_plan", "page": "invalid"},  # Invalid page
            {"type": "site_plan", "page": 3}
        ]
        
        result = node._validate_diagram_data(input_diagrams)
        
        # Should validate and fix data
        assert len(result) == 4
        assert result[0] == {"type": "floor_plan", "page": 1}
        assert result[1] == {"type": "unknown", "page": 2}  # Invalid type fixed
        assert result[2] == {"type": "site_plan", "page": 1}  # Invalid page fixed
        assert result[3] == {"type": "site_plan", "page": 3}

    def test_get_file_type_from_path(self, node):
        """Test file type extraction from path"""
        
        # Test various file extensions
        assert node._get_file_type_from_path("/path/to/file.pdf") == "pdf"
        assert node._get_file_type_from_path("/path/to/file.PNG") == "png"
        assert node._get_file_type_from_path("/path/to/file.jpg") == "jpeg"
        assert node._get_file_type_from_path("/path/to/file.jpeg") == "jpeg"
        assert node._get_file_type_from_path("/path/to/file.unknown") == "pdf"  # Default
        assert node._get_file_type_from_path("/path/to/file") == "pdf"  # No extension