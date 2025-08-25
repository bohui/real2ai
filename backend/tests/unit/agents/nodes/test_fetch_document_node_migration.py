"""
Unit tests for fetch_document_node.py repository migration

Tests verify that the migrated node uses repositories correctly
and maintains the same functionality as before the migration.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID

from app.agents.nodes.document_processing_subflow.fetch_document_node import (
    FetchDocumentRecordNode,
)
from app.models.supabase_models import Document


class TestFetchDocumentNodeMigration:
    """Test fetch_document_node repository migration"""

    def setup_method(self):
        """Setup test fixtures"""
        self.node = FetchDocumentRecordNode()
        self.document_id = str(uuid4())
        self.user_id = str(uuid4())

        self.mock_document = Document(
            id=UUID(self.document_id),
            user_id=UUID(self.user_id),
            original_filename="test_document.pdf",
            storage_path="/storage/test_document.pdf",
            file_type="pdf",
            file_size=1024,
            content_hash="test_content_hash_789",
            processing_status="uploaded",
        )

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful document fetching using repository"""

        # Mock the DocumentsRepository
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        # Mock state
        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify repository was called correctly
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))

        # Verify state was updated correctly
        assert result["storage_path"] == "/storage/test_document.pdf"
        assert result["file_type"] == "pdf"
        assert result["content_hash"] == "test_content_hash_789"

        # Verify document metadata was stored
        assert "_document_metadata" in result
        metadata = result["_document_metadata"]
        assert metadata["original_filename"] == "test_document.pdf"
        assert metadata["processing_status"] == "uploaded"
        assert "fetched_at" in metadata

    @pytest.mark.asyncio
    async def test_execute_document_not_found(self):
        """Test handling when document is not found"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = None  # Document not found

        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify error handling
        assert "error" in result
        assert "Document not found or access denied" in result["error_message"]
        assert result["error_details"]["user_has_access"] is False

    @pytest.mark.asyncio
    async def test_execute_missing_document_id(self):
        """Test handling when document_id is missing from state"""

        state = {}  # Missing document_id

        result = await self.node.execute(state)

        # Verify error handling
        assert "error" in result
        assert "Document ID is required" in result["error_message"]
        assert "provided_state_keys" in result["error_details"]

    @pytest.mark.asyncio
    async def test_execute_incomplete_metadata(self):
        """Test handling when document has incomplete metadata"""

        # Create document with missing storage_path
        incomplete_document = Document(
            id=UUID(self.document_id),
            user_id=UUID(self.user_id),
            original_filename="test.pdf",
            storage_path=None,  # Missing required field
            file_type="pdf",
            file_size=1024,
            content_hash="test_hash",
            processing_status="uploaded",
        )

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = incomplete_document

        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify error handling
        assert "error" in result
        assert "Document metadata is incomplete" in result["error_message"]
        assert result["error_details"]["has_storage_path"] is False
        assert result["error_details"]["has_file_type"] is True

    @pytest.mark.asyncio
    async def test_repository_error_handling(self):
        """Test handling of repository errors"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.side_effect = Exception(
            "Database connection failed"
        )

        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify error handling
        assert "error" in result
        assert "Failed to fetch document metadata" in result["error_message"]
        assert "Database connection failed" in str(result["error"])

    @pytest.mark.asyncio
    async def test_content_hash_preservation(self):
        """Test that existing content_hash in state is preserved if document doesn't have one"""

        # Create document without content_hash
        document_without_hash = Document(
            id=UUID(self.document_id),
            user_id=UUID(self.user_id),
            original_filename="test.pdf",
            storage_path="/storage/test.pdf",
            file_type="pdf",
            file_size=1024,
            content_hash=None,  # No content hash in document
            processing_status="uploaded",
        )

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = document_without_hash

        state = {
            "document_id": self.document_id,
            "content_hash": "existing_hash_from_state",
        }

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify existing content_hash from state was preserved
        assert result["content_hash"] == "existing_hash_from_state"

    @pytest.mark.asyncio
    async def test_no_user_client_access(self):
        """Test that user_client is no longer used"""

        # This test verifies that we no longer use self.get_user_client()
        # The repository handles user context internally

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        state = {"document_id": self.document_id}

        # Mock get_user_client to fail if called
        with (
            patch.object(self.node, "get_user_client") as mock_get_client,
            patch(
                "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
                return_value=mock_docs_repo,
            ),
        ):

            mock_get_client.side_effect = Exception("Should not be called")

            result = await self.node.execute(state)

        # Verify repository was used and user_client was not called
        mock_docs_repo.get_document.assert_called_once()
        mock_get_client.assert_not_called()

        # Verify successful result
        assert "error" not in result
        assert result["storage_path"] == "/storage/test_document.pdf"

    @pytest.mark.asyncio
    async def test_uuid_conversion(self):
        """Test that string document_id is properly converted to UUID"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            await self.node.execute(state)

        # Verify UUID conversion
        call_args = mock_docs_repo.get_document.call_args[0]
        assert isinstance(call_args[0], UUID)
        assert str(call_args[0]) == self.document_id

    @pytest.mark.asyncio
    async def test_backward_compatibility_dict_format(self):
        """Test that the node still returns dict format for downstream compatibility"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        state = {"document_id": self.document_id}

        with patch(
            "app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository",
            return_value=mock_docs_repo,
        ):
            result = await self.node.execute(state)

        # Verify that internal document processing still works with dict access
        assert isinstance(result["storage_path"], str)
        assert isinstance(result["file_type"], str)
        assert result["_document_metadata"]["original_filename"] == "test_document.pdf"
