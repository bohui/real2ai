"""
Unit tests for SavePagesNode
"""

import pytest

from app.agents.nodes.step0_document_processing.save_pages_node import SavePagesNode


class TestSavePagesNode:
    """Test cases for SavePagesNode"""

    @pytest.fixture
    def node(self):
        """Create a SavePagesNode instance for testing"""
        return SavePagesNode()

    @pytest.fixture
    def mock_state(self):
        """Create a mock state for testing"""
        return {
            "document_id": "test-doc-123",
            "storage_path": "/documents/test-document.pdf",
            "content_hash": "abc123",
            "pages": [
                {"page_number": 1, "content": "Page 1 content"},
                {"page_number": 2, "content": "Page 2 content"}
            ]
        }

    def test_initialization_sets_artifacts_bucket(self, node):
        """Test that initialization sets the correct bucket for artifacts storage"""
        
        # Check the storage service uses the artifacts bucket
        assert node.storage_service.bucket_name == "artifacts"

    @pytest.mark.asyncio
    async def test_initialize_repositories(self, node):
        """Test that repositories are properly initialized"""
        
        # Initialize the node
        await node.initialize(user_id="test-user")
        
        # Verify repositories are initialized
        assert node.user_docs_repo is not None
        assert node.artifacts_repo is not None

    @pytest.mark.asyncio
    async def test_execute_missing_required_fields(self, node):
        """Test execution with missing required fields"""
        
        # Test missing document_id
        state = {"storage_path": "/documents/test.pdf", "pages": []}
        result_state = await node.execute(state)
        assert "error" in result_state
        assert "Document ID is required" in result_state["error"]
        
        # Test missing pages
        state = {"document_id": "test-doc-123", "storage_path": "/documents/test.pdf"}
        result_state = await node.execute(state)
        assert "error" in result_state
        assert "Text extraction result is missing or unsuccessful" in result_state["error"]

    @pytest.mark.asyncio
    async def test_execute_empty_pages(self, node):
        """Test execution with empty pages list"""
        
        state = {
            "document_id": "test-doc-123",
            "storage_path": "/documents/test.pdf",
            "pages": []
        }
        
        result_state = await node.execute(state)
        assert "error" in result_state
        assert "Text extraction result is missing or unsuccessful" in result_state["error"]

    @pytest.mark.asyncio
    async def test_node_name(self, node):
        """Test that node has correct name"""
        assert node.node_name == "save_pages"