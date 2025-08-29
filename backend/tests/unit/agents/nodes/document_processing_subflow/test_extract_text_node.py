"""
Unit tests for ExtractTextNode
"""

import pytest

from app.agents.nodes.step0_document_processing.extract_text_node import ExtractTextNode


class TestExtractTextNode:
    """Test cases for ExtractTextNode"""

    @pytest.fixture
    def node(self):
        """Create an ExtractTextNode instance for testing"""
        return ExtractTextNode()

    @pytest.fixture
    def mock_state(self):
        """Create a mock state for testing"""
        return {
            "document_id": "test-doc-123",
            "storage_path": "/documents/test-document.pdf",
            "content_hash": "abc123",
            "use_llm": True
        }

    @pytest.mark.asyncio
    async def test_initialize_sets_artifacts_bucket(self, node):
        """Test that initialization sets the correct bucket for artifacts storage"""
        
        # Initialize the node
        await node.initialize()
        
        # Verify the storage service uses the artifacts bucket
        assert node.storage_service.bucket_name == "artifacts"

    @pytest.mark.asyncio
    async def test_artifacts_repo_initialization(self, node):
        """Test that artifacts repository is properly initialized"""
        
        # Initialize the node
        await node.initialize()
        
        # Verify artifacts repo is initialized
        assert node.artifacts_repo is not None

    @pytest.mark.asyncio
    async def test_visual_artifact_service_initialization(self, node):
        """Test that visual artifact service is properly initialized with artifacts bucket"""
        
        # Initialize the node
        await node.initialize()
        
        # Verify visual artifact service is initialized with correct storage service
        assert node.visual_artifact_service is not None
        assert node.visual_artifact_service.storage_service.bucket_name == "artifacts"

    @pytest.mark.asyncio
    async def test_execute_missing_required_fields(self, node):
        """Test execution with missing required fields"""
        
        # Test missing document_id
        state = {"storage_path": "/documents/test.pdf"}
        result_state = await node.execute(state)
        assert "error" in result_state
        assert "Document metadata incomplete for text extraction" in result_state["error"]
        
        # Test missing storage_path
        state = {"document_id": "test-doc-123"}
        result_state = await node.execute(state)
        assert "error" in result_state
        assert "Document metadata incomplete for text extraction" in result_state["error"]

    @pytest.mark.asyncio
    async def test_node_name(self, node):
        """Test that node has correct name"""
        assert node.node_name == "extract_text"