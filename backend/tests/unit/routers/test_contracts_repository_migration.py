"""
Unit tests for contracts.py repository migration

Tests verify that the migrated contracts router uses repositories correctly
and maintains the same functionality as before the migration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.router.contracts import _get_user_document
from app.services.repositories.documents_repository import DocumentsRepository
from app.models.supabase_models import Document


class TestContractsRouterMigration:
    """Test contracts router repository migration"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = str(uuid4())
        self.document_id = str(uuid4())

        self.mock_document = Document(
            id=UUID(self.document_id),
            user_id=UUID(self.user_id),
            original_filename="test_contract.pdf",
            storage_path="/storage/test_contract.pdf",
            file_type="pdf",
            file_size=2048,
            content_hash="test_content_hash_456",
            processing_status="processed",
        )

    @pytest.mark.asyncio
    async def test_get_user_document_success(self):
        """Test successful document retrieval using repository"""

        # Mock the DocumentsRepository
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        # Mock the user client (not used anymore but passed to function)
        mock_user_client = Mock()

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            result = await _get_user_document(
                mock_user_client, self.document_id, self.user_id
            )

        # Verify repository was called correctly
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))

        # Verify backward compatibility - result should be dict format
        assert isinstance(result, dict)
        assert result["id"] == self.document_id
        assert result["user_id"] == self.user_id
        assert result["original_filename"] == "test_contract.pdf"
        assert result["content_hash"] == "test_content_hash_456"
        assert result["processing_status"] == "processed"

    @pytest.mark.asyncio
    async def test_get_user_document_not_found(self):
        """Test handling when document is not found"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = None  # Document not found

        mock_user_client = Mock()

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            with pytest.raises(
                ValueError, match="Document not found or you don't have access to it"
            ):
                await _get_user_document(
                    mock_user_client, self.document_id, self.user_id
                )

    @pytest.mark.asyncio
    async def test_get_user_document_repository_error(self):
        """Test handling of repository errors"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.side_effect = Exception(
            "Database connection failed"
        )

        mock_user_client = Mock()

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            with pytest.raises(Exception, match="Database connection failed"):
                await _get_user_document(
                    mock_user_client, self.document_id, self.user_id
                )

    @pytest.mark.asyncio
    async def test_backward_compatibility_data_format(self):
        """Test that the migration maintains backward compatibility with data formats"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        mock_user_client = Mock()

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            result = await _get_user_document(
                mock_user_client, self.document_id, self.user_id
            )

        # Verify all expected fields are present in dict format
        expected_fields = [
            "id",
            "user_id",
            "original_filename",
            "storage_path",
            "file_type",
            "file_size",
            "content_hash",
            "processing_status",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

        # Verify data types are strings for IDs (backward compatibility)
        assert isinstance(result["id"], str)
        assert isinstance(result["user_id"], str)

    @pytest.mark.asyncio
    async def test_user_client_no_longer_used(self):
        """Test that user_client.database is no longer used"""

        # This test verifies that we no longer use the user_client.database
        # The user_client parameter is kept for compatibility but not used

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        # Create a user client that would fail if database was accessed
        mock_user_client = Mock()
        mock_user_client.database.select.side_effect = Exception("Should not be called")

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            # This should succeed without touching user_client.database
            result = await _get_user_document(
                mock_user_client, self.document_id, self.user_id
            )

        # Verify the repository was used instead
        mock_docs_repo.get_document.assert_called_once()

        # Verify user_client.database was never called
        assert not mock_user_client.database.select.called

    @pytest.mark.asyncio
    async def test_uuid_conversion_handled(self):
        """Test that string document_id is properly converted to UUID"""

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        mock_user_client = Mock()

        with patch(
            "app.router.contracts.DocumentsRepository", return_value=mock_docs_repo
        ):
            await _get_user_document(mock_user_client, self.document_id, self.user_id)

        # Verify that the string document_id was converted to UUID for repository call
        call_args = mock_docs_repo.get_document.call_args[0]
        assert isinstance(call_args[0], UUID)
        assert str(call_args[0]) == self.document_id
