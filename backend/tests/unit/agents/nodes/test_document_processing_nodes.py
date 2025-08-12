"""
Unit Tests for Document Processing Subflow Nodes

This module contains unit tests for the DocumentProcessingWorkflow subflow nodes.
Tests use fixtures for Supabase client interactions and mock external dependencies.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from uuid import UUID

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.agents.nodes.document_processing_subflow import (
    FetchDocumentRecordNode,
    AlreadyProcessedCheckNode,
    MarkProcessingStartedNode,
    BuildSummaryNode,
    ErrorHandlingNode,
    ParagraphSegmentationNode,
    SaveParagraphsNode,
)
from app.schema.document import ProcessedDocumentSummary
from app.services.repositories.documents_repository import Document


@pytest.fixture
def mock_user_client():
    """Mock authenticated user client."""
    client = AsyncMock()
    client.database = AsyncMock()
    return client


@pytest.fixture
def sample_document_id():
    """Sample document ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_state():
    """Sample document processing state."""
    return DocumentProcessingState(
        document_id=str(uuid.uuid4()),
        use_llm=True,
        content_hash=None,
        storage_path=None,
        file_type=None,
        text_extraction_result=None,
        diagram_processing_result=None,
        processed_summary=None,
        error=None,
        error_details=None
    )


class TestFetchDocumentRecordNode:
    """Test cases for FetchDocumentRecordNode."""
    
    @pytest.mark.asyncio
    async def test_successful_fetch(self, sample_state, mock_user_client):
        """Test successful document metadata fetch."""
        # Arrange - Create Document object for repository
        document_obj = Document(
            id=UUID(sample_state["document_id"]),
            user_id=UUID(str(uuid.uuid4())),  # Mock user ID
            original_filename="test_document.pdf",
            storage_path="documents/test.pdf",
            file_type="application/pdf",
            file_size=1024,
            content_hash="test_hash_123",
            processing_status="pending"
        )
        
        # Mock the DocumentsRepository
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = document_obj
        
        # Ensure mock_user_client.database is never called
        mock_user_client.database.select.side_effect = Exception("Should not be called - use repository instead")
        
        node = FetchDocumentRecordNode()
        
        with patch('app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository', return_value=mock_docs_repo):
            with patch.object(node, 'get_user_client', return_value=mock_user_client):
                # Act
                result = await node.execute(sample_state)
                
                # Assert
                assert result["storage_path"] == "documents/test.pdf"
                assert result["file_type"] == "application/pdf" 
                assert result["content_hash"] == "test_hash_123"
                assert result["error"] is None
                
                # Verify repository was called correctly
                mock_docs_repo.get_document.assert_called_once_with(UUID(sample_state["document_id"]))
                
                # Verify user_client.database was NOT called
                assert not mock_user_client.database.select.called
    
    @pytest.mark.asyncio
    async def test_document_not_found(self, sample_state, mock_user_client):
        """Test handling when document is not found."""
        # Arrange - Mock repository to return None (document not found)
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = None
        
        # Ensure mock_user_client.database is never called
        mock_user_client.database.select.side_effect = Exception("Should not be called - use repository instead")
        
        node = FetchDocumentRecordNode()
        
        with patch('app.agents.nodes.document_processing_subflow.fetch_document_node.DocumentsRepository', return_value=mock_docs_repo):
            with patch.object(node, 'get_user_client', return_value=mock_user_client):
                # Act
                result = await node.execute(sample_state)
                
                # Assert
                assert result["error"] == "Document not found or access denied"
                assert result["error_details"] is not None
                assert result["error_details"]["node"] == "fetch_document_record"
                
                # Verify repository was called
                mock_docs_repo.get_document.assert_called_once_with(UUID(sample_state["document_id"]))
                
                # Verify user_client.database was NOT called
                assert not mock_user_client.database.select.called
    
    @pytest.mark.asyncio
    async def test_missing_document_id(self, mock_user_client):
        """Test handling when document_id is missing."""
        # Arrange
        state = DocumentProcessingState(
            document_id="",  # Empty document ID
            use_llm=True,
            content_hash=None,
            storage_path=None,
            file_type=None,
            text_extraction_result=None,
            diagram_processing_result=None,
            processed_summary=None,
            error=None,
            error_details=None
        )
        
        node = FetchDocumentRecordNode()
        
        with patch.object(node, 'get_user_client', return_value=mock_user_client):
            # Act
            result = await node.execute(state)
            
            # Assert
            assert result["error"] == "Document ID is required"
            assert result["error_details"] is not None


class TestAlreadyProcessedCheckNode:
    """Test cases for AlreadyProcessedCheckNode."""
    
    @pytest.mark.asyncio
    async def test_already_processed_document(self, sample_state):
        """Test when document is already processed."""
        # Arrange
        sample_summary = ProcessedDocumentSummary(
            success=True,
            document_id=sample_state["document_id"],
            australian_state="NSW",
            full_text="Sample document text",
            character_count=100,
            total_word_count=20,
            total_pages=1,
            extraction_method="pdf_native",
            extraction_confidence=0.95,
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            llm_used=True
        )
        
        node = AlreadyProcessedCheckNode()
        
        with patch('app.services.document_service.DocumentService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_processed_document_summary.return_value = sample_summary
            mock_service.return_value = mock_service_instance
            
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result["processed_summary"] == sample_summary
            assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_not_processed_document(self, sample_state):
        """Test when document is not yet processed.""" 
        # Arrange
        node = AlreadyProcessedCheckNode()
        
        with patch('app.services.document_service.DocumentService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_processed_document_summary.return_value = None
            mock_service.return_value = mock_service_instance
            
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result["processed_summary"] is None
            assert result["error"] is None


class TestBuildSummaryNode:
    """Test cases for BuildSummaryNode."""
    
    @pytest.mark.asyncio
    async def test_build_summary_with_existing_summary(self, sample_state):
        """Test building summary when already exists in state."""
        # Arrange
        existing_summary = ProcessedDocumentSummary(
            success=True,
            document_id=sample_state["document_id"],
            australian_state="NSW",
            full_text="Existing summary",
            character_count=100,
            total_word_count=15,
            total_pages=1,
            extraction_method="existing",
            extraction_confidence=0.9,
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            llm_used=True
        )
        
        state_with_summary = sample_state.copy()
        state_with_summary["processed_summary"] = existing_summary
        
        node = BuildSummaryNode()
        
        # Act
        result = await node.execute(state_with_summary)
        
        # Assert
        assert result["processed_summary"] == existing_summary
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_build_summary_missing_extraction_result(self, sample_state):
        """Test building summary when text extraction result is missing."""
        # Arrange
        node = BuildSummaryNode()
        
        # Act
        result = await node.execute(sample_state)
        
        # Assert
        assert result["error"] == "Cannot build summary without successful text extraction"
        assert result["error_details"] is not None


class TestErrorHandlingNode:
    """Test cases for ErrorHandlingNode."""
    
    @pytest.mark.asyncio
    async def test_handle_error_with_document_id(self, sample_state, mock_user_client):
        """Test error handling with valid document ID."""
        # Arrange
        error_state = sample_state.copy()
        error_state["error"] = "Sample processing error"
        error_state["error_details"] = {
            "error_type": "ProcessingError",
            "node": "extract_text"
        }
        
        # Mock the DocumentsRepository used in ErrorHandlingNode
        mock_docs_repo = AsyncMock()
        mock_docs_repo.update_processing_status_and_results = AsyncMock()
        
        # Ensure mock_user_client.database is never called
        mock_user_client.database.update.side_effect = Exception("Should not be called - use repository instead")
        
        node = ErrorHandlingNode()
        
        with patch('app.services.repositories.documents_repository.DocumentsRepository', return_value=mock_docs_repo):
            with patch.object(node, 'get_user_client', return_value=mock_user_client):
                # Act
                result = await node.execute(error_state)
                
                # Assert
                assert result["error"] == "Sample processing error"
                assert result["error_details"] is not None
                
                # Verify repository method was called correctly
                mock_docs_repo.update_processing_status_and_results.assert_called_once()
                call_args = mock_docs_repo.update_processing_status_and_results.call_args
                assert call_args[0][0] == UUID(sample_state["document_id"])  # document_id as UUID
                assert call_args[0][1] == "failed"  # ProcessingStatus.FAILED.value
                
                # Verify user_client.database was NOT called
                assert not mock_user_client.database.update.called
    
    @pytest.mark.asyncio
    async def test_handle_error_without_document_id(self):
        """Test error handling without document ID."""
        # Arrange
        state = DocumentProcessingState(
            document_id="",  # Missing document ID
            use_llm=True,
            content_hash=None,
            storage_path=None,
            file_type=None,
            text_extraction_result=None,
            diagram_processing_result=None,
            processed_summary=None,
            error="Some error occurred",
            error_details=None
        )
        
        node = ErrorHandlingNode()
        
        # Act
        result = await node.execute(state)
        
        # Assert
        assert "Missing document ID" in result["error"] or result["error"] == "Some error occurred"
        assert result["error_details"] is not None


class TestParagraphSegmentationNode:
    """Test cases for ParagraphSegmentationNode."""

    @pytest.fixture
    def sample_text_extraction_result(self):
        """Sample text extraction result for testing."""
        return {
            "success": True,
            "full_text": "This is the first paragraph.\n\nThis is the second paragraph with more content.\n\nA third paragraph here.",
            "pages": [
                {
                    "page_number": 1,
                    "text": "This is the first paragraph.\n\nThis is the second paragraph",
                    "words": 12
                },
                {
                    "page_number": 2,
                    "text": " with more content.\n\nA third paragraph here.",
                    "words": 8
                }
            ],
            "total_pages": 2,
            "extraction_methods": ["text"]
        }

    @pytest.fixture
    def mock_artifacts_repo(self):
        """Mock artifacts repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_successful_paragraph_segmentation(self, sample_state, sample_text_extraction_result, mock_artifacts_repo, mock_storage_service):
        """Test successful paragraph segmentation and artifact creation."""
        # Arrange
        sample_state["text_extraction_result"] = sample_text_extraction_result
        sample_state["content_hmac"] = "test_content_hmac"
        
        # Mock no existing artifacts
        mock_artifacts_repo.get_paragraph_artifacts.return_value = []
        
        # Mock storage upload
        mock_storage_service.upload_paragraph_text.return_value = ("test_uri", "test_sha256")
        
        # Mock artifact insertion
        mock_artifact = Mock()
        mock_artifact.id = uuid.uuid4()
        mock_artifact.paragraph_index = 0
        mock_artifact.page_number = 1
        mock_artifact.paragraph_text_uri = "test_uri"
        mock_artifact.features = {"page_spans": [], "start_offset": 0, "end_offset": 100}
        mock_artifacts_repo.insert_paragraph_artifact.return_value = mock_artifact
        
        node = ParagraphSegmentationNode()
        
        with patch.object(node, 'artifacts_repo', mock_artifacts_repo), \
             patch.object(node, 'storage_service', mock_storage_service), \
             patch.object(node, 'paragraphs_enabled', True):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result["error"] is None
            assert "paragraphs" in result
            assert "paragraph_artifacts" in result
            assert len(result["paragraphs"]) > 0
            assert "processing_metrics" in result
            assert result["processing_metrics"]["reuse_hit"] is False

    @pytest.mark.asyncio
    async def test_paragraph_segmentation_with_existing_artifacts(self, sample_state, sample_text_extraction_result, mock_artifacts_repo):
        """Test paragraph segmentation when artifacts already exist (idempotency)."""
        # Arrange
        sample_state["text_extraction_result"] = sample_text_extraction_result
        sample_state["content_hmac"] = "test_content_hmac"
        
        # Mock existing artifacts
        existing_artifact = Mock()
        existing_artifact.id = uuid.uuid4()
        existing_artifact.paragraph_index = 0
        existing_artifact.page_number = 1
        existing_artifact.features = {
            "page_spans": [{"page": 1, "start": 0, "end": 100}],
            "start_offset": 0,
            "end_offset": 100
        }
        mock_artifacts_repo.get_paragraph_artifacts.return_value = [existing_artifact]
        
        node = ParagraphSegmentationNode()
        
        with patch.object(node, 'artifacts_repo', mock_artifacts_repo), \
             patch.object(node, 'paragraphs_enabled', True):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result["error"] is None
            assert "paragraphs" in result
            assert "paragraph_artifacts" in result
            assert result["processing_metrics"]["reuse_hit"] is True
            assert result["processing_metrics"]["reused_paragraphs_count"] == 1

    @pytest.mark.asyncio
    async def test_paragraph_segmentation_disabled(self, sample_state, sample_text_extraction_result):
        """Test paragraph segmentation when feature is disabled."""
        # Arrange
        sample_state["text_extraction_result"] = sample_text_extraction_result
        
        node = ParagraphSegmentationNode()
        
        with patch.object(node, 'paragraphs_enabled', False):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result == sample_state  # No changes
            assert "paragraphs" not in result

    @pytest.mark.asyncio
    async def test_paragraph_segmentation_no_text_result(self, sample_state):
        """Test paragraph segmentation with no text extraction result."""
        # Arrange - no text_extraction_result
        node = ParagraphSegmentationNode()
        
        with patch.object(node, 'paragraphs_enabled', True):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result == sample_state  # No changes


class TestSaveParagraphsNode:
    """Test cases for SaveParagraphsNode."""

    @pytest.fixture
    def sample_paragraph_artifacts(self):
        """Sample paragraph artifacts for testing."""
        return [
            {
                "id": str(uuid.uuid4()),
                "paragraph_index": 0,
                "page_number": 1,
                "text_uri": "test_uri_1",
                "features": {"page_spans": [{"page": 1, "start": 0, "end": 50}]}
            },
            {
                "id": str(uuid.uuid4()),
                "paragraph_index": 1,
                "page_number": 1,
                "text_uri": "test_uri_2",
                "features": {"page_spans": [{"page": 1, "start": 50, "end": 100}]}
            }
        ]

    @pytest.fixture
    def mock_user_docs_repo(self):
        """Mock user docs repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_successful_paragraph_save(self, sample_state, sample_paragraph_artifacts, mock_user_docs_repo):
        """Test successful saving of paragraph references."""
        # Arrange
        sample_state["paragraph_artifacts"] = sample_paragraph_artifacts
        
        # Mock successful upserts
        mock_user_docs_repo.upsert_document_paragraph.return_value = Mock()
        
        node = SaveParagraphsNode()
        
        with patch.object(node, 'get_user_client') as mock_get_client, \
             patch('app.agents.nodes.document_processing_subflow.save_paragraphs_node.UserDocsRepository', return_value=mock_user_docs_repo):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result["error"] is None
            assert "processing_metrics" in result
            assert result["processing_metrics"]["paragraphs_saved_count"] == 2
            assert result["processing_metrics"]["paragraph_save_success_rate"] == 1.0
            
            # Verify repository calls
            assert mock_user_docs_repo.upsert_document_paragraph.call_count == 2

    @pytest.mark.asyncio
    async def test_save_paragraphs_no_artifacts(self, sample_state, mock_user_docs_repo):
        """Test saving paragraphs when no artifacts exist."""
        # Arrange - no paragraph_artifacts
        node = SaveParagraphsNode()
        
        with patch.object(node, 'get_user_client'):
            # Act
            result = await node.execute(sample_state)
            
            # Assert
            assert result == sample_state  # No changes

    @pytest.mark.asyncio
    async def test_save_paragraphs_missing_document_id(self, sample_paragraph_artifacts, mock_user_docs_repo):
        """Test saving paragraphs with missing document ID."""
        # Arrange
        state = DocumentProcessingState(
            document_id="",  # Missing document ID
            use_llm=True,
            content_hash=None,
            storage_path=None,
            file_type=None,
            text_extraction_result=None,
            diagram_processing_result=None,
            processed_summary=None,
            error=None,
            error_details=None
        )
        state["paragraph_artifacts"] = sample_paragraph_artifacts
        
        node = SaveParagraphsNode()
        
        # Act
        result = await node.execute(state)
        
        # Assert
        assert "Document ID required" in result["error"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])