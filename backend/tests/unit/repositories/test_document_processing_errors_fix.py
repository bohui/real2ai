"""Test that processing_errors field is properly parsed from JSON in Document models."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from app.models.supabase_models import Document
from app.services.repositories.documents_repository import DocumentsRepository


class TestDocumentProcessingErrorsFix:
    """Test that processing_errors field is properly parsed from JSON."""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_conn.fetch = AsyncMock()
        return mock_conn

    @pytest.fixture
    def documents_repo(self):
        """Create DocumentsRepository instance."""
        repo = DocumentsRepository()
        repo.user_id = uuid4()
        return repo

    @pytest.mark.asyncio
    async def test_processing_errors_parsed_from_json_string(
        self, mock_connection, documents_repo
    ):
        """Test that processing_errors JSON string is parsed to dict."""
        # Mock the database row with processing_errors as a JSON string
        mock_row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "original_filename": "test.pdf",
            "storage_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_hash": "abc123",
            "processing_status": "failed",
            "processing_started_at": datetime.now(timezone.utc),
            "processing_completed_at": datetime.now(timezone.utc),
            "processing_errors": '{"error": "Text extraction failed", "processing_failed": true}',
            "artifact_text_id": None,
            "total_pages": 0,
            "total_word_count": 0,
            "total_text_length": 0,
            "overall_quality_score": 0.0,
            "extraction_confidence": 0.0,
            "text_extraction_method": None,
            "has_diagrams": False,
            "diagram_count": 0,
            "document_type": None,
            "australian_state": None,
            "contract_type": None,
            "processing_notes": None,
            "upload_metadata": None,
            "processing_results": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Mock the connection context manager
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)

        # Mock get_user_connection to return our mock connection
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "app.services.repositories.documents_repository.get_user_connection",
                lambda user_id: mock_connection,
            )

            # Mock fetchrow to return our mock row
            mock_connection.fetchrow.return_value = mock_row

            # Call get_document
            result = await documents_repo.get_document(mock_row["id"])

            # Verify the result is a Document object
            assert isinstance(result, Document)

            # Verify processing_errors is a dict, not a string
            assert isinstance(result.processing_errors, dict)
            assert result.processing_errors["error"] == "Text extraction failed"
            assert result.processing_errors["processing_failed"] is True

    @pytest.mark.asyncio
    async def test_processing_errors_handles_none_value(
        self, mock_connection, documents_repo
    ):
        """Test that processing_errors handles None values correctly."""
        # Mock the database row with processing_errors as None
        mock_row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "original_filename": "test.pdf",
            "storage_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_hash": "abc123",
            "processing_status": "completed",
            "processing_started_at": datetime.now(timezone.utc),
            "processing_completed_at": datetime.now(timezone.utc),
            "processing_errors": None,  # No errors
            "artifact_text_id": None,
            "total_pages": 0,
            "total_word_count": 0,
            "total_text_length": 0,
            "overall_quality_score": 0.0,
            "extraction_confidence": 0.0,
            "text_extraction_method": None,
            "has_diagrams": False,
            "diagram_count": 0,
            "document_type": None,
            "australian_state": None,
            "contract_type": None,
            "processing_notes": None,
            "upload_metadata": None,
            "processing_results": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Mock the connection context manager
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)

        # Mock get_user_connection to return our mock connection
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "app.services.repositories.documents_repository.get_user_connection",
                lambda user_id: mock_connection,
            )

            # Mock fetchrow to return our mock row
            mock_connection.fetchrow.return_value = mock_row

            # Call get_document
            result = await documents_repo.get_document(mock_row["id"])

            # Verify the result is a Document object
            assert isinstance(result, Document)

            # Verify processing_errors is None
            assert result.processing_errors is None

    @pytest.mark.asyncio
    async def test_processing_errors_handles_already_dict_value(
        self, mock_connection, documents_repo
    ):
        """Test that processing_errors handles already-parsed dict values correctly."""
        # Mock the database row with processing_errors as already a dict
        mock_row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "original_filename": "test.pdf",
            "storage_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_hash": "abc123",
            "processing_status": "failed",
            "processing_started_at": datetime.now(timezone.utc),
            "processing_completed_at": datetime.now(timezone.utc),
            "processing_errors": {
                "error": "Already a dict",
                "code": 500,
            },  # Already a dict
            "artifact_text_id": None,
            "total_pages": 0,
            "total_word_count": 0,
            "total_text_length": 0,
            "overall_quality_score": 0.0,
            "extraction_confidence": 0.0,
            "text_extraction_method": None,
            "has_diagrams": False,
            "diagram_count": 0,
            "document_type": None,
            "australian_state": None,
            "contract_type": None,
            "processing_notes": None,
            "upload_metadata": None,
            "processing_results": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Mock the connection context manager
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)

        # Mock get_user_connection to return our mock connection
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "app.services.repositories.documents_repository.get_user_connection",
                lambda user_id: mock_connection,
            )

            # Mock fetchrow to return our mock row
            mock_connection.fetchrow.return_value = mock_row

            # Call get_document
            result = await documents_repo.get_document(mock_row["id"])

            # Verify the result is a Document object
            assert isinstance(result, Document)

            # Verify processing_errors is still a dict
            assert isinstance(result.processing_errors, dict)
            assert result.processing_errors["error"] == "Already a dict"
            assert result.processing_errors["code"] == 500

    @pytest.mark.asyncio
    async def test_processing_errors_handles_invalid_json(
        self, mock_connection, documents_repo
    ):
        """Test that processing_errors handles invalid JSON gracefully."""
        # Mock the database row with processing_errors as invalid JSON
        mock_row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "original_filename": "test.pdf",
            "storage_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_hash": "abc123",
            "processing_status": "failed",
            "processing_started_at": datetime.now(timezone.utc),
            "processing_completed_at": datetime.now(timezone.utc),
            "processing_errors": '{"error": "Invalid JSON',  # Invalid JSON string
            "artifact_text_id": None,
            "total_pages": 0,
            "total_word_count": 0,
            "total_text_length": 0,
            "overall_quality_score": 0.0,
            "extraction_confidence": 0.0,
            "text_extraction_method": None,
            "has_diagrams": False,
            "diagram_count": 0,
            "document_type": None,
            "australian_state": None,
            "contract_type": None,
            "processing_notes": None,
            "upload_metadata": None,
            "processing_results": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Mock the connection context manager
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)

        # Mock get_user_connection to return our mock connection
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "app.services.repositories.documents_repository.get_user_connection",
                lambda user_id: mock_connection,
            )

            # Mock fetchrow to return our mock row
            mock_connection.fetchrow.return_value = mock_row

            # Call get_document
            result = await documents_repo.get_document(mock_row["id"])

            # Verify the result is a Document object
            assert isinstance(result, Document)

            # Verify processing_errors is None (invalid JSON should result in None)
            assert result.processing_errors is None
