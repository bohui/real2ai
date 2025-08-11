"""
Integration Tests for DocumentProcessingWorkflow

This module contains integration tests for the complete DocumentProcessingWorkflow
including happy path, failure path, and edge cases.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import (
    DocumentProcessingWorkflow,
    DocumentProcessingState
)
from app.schema.document import ProcessedDocumentSummary, ProcessingErrorResponse, TextExtractionResult
from app.models.supabase_models import ProcessingStatus


@pytest.fixture
def workflow():
    """Create DocumentProcessingWorkflow instance for testing."""
    return DocumentProcessingWorkflow(
        use_llm_document_processing=True,
        storage_bucket="test-documents"
    )


@pytest.fixture
def sample_document_id():
    """Sample document ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_user_client():
    """Mock authenticated user client."""
    client = AsyncMock()
    client.database = AsyncMock()
    return client


@pytest.fixture
def sample_text_extraction_result():
    """Sample text extraction result for testing."""
    from app.schema.document import DocumentPage, ContentAnalysis, LayoutFeatures, QualityIndicators
    
    page_analysis = ContentAnalysis(
        content_types=["text"],
        primary_type="text",
        layout_features=LayoutFeatures(
            has_header=True,
            has_footer=False,
            has_signatures=False,
            has_diagrams=False,
            has_tables=False,
        ),
        quality_indicators=QualityIndicators(
            structure_score=0.9,
            readability_score=0.85,
            completeness_score=0.95
        )
    )
    
    sample_page = DocumentPage(
        page_number=1,
        text_content="Sample contract text content",
        text_length=28,
        word_count=4,
        confidence=0.9,
        extraction_method="pdf_native",
        content_analysis=page_analysis
    )
    
    return TextExtractionResult(
        success=True,
        full_text="Sample contract text content",
        total_pages=1,
        pages=[sample_page],
        extraction_methods=["pdf_native"],
        overall_confidence=0.9,
        processing_time=1.2,
        error=None
    )


class TestDocumentProcessingWorkflowIntegration:
    """Integration tests for DocumentProcessingWorkflow."""
    
    @pytest.mark.asyncio
    async def test_already_processed_happy_path(self, workflow, sample_document_id):
        """Test workflow when document is already processed."""
        # Arrange
        existing_summary = ProcessedDocumentSummary(
            success=True,
            document_id=sample_document_id,
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
        
        with patch.object(workflow.already_processed_check_node, 'execute') as mock_execute:
            mock_execute.return_value = DocumentProcessingState(
                document_id=sample_document_id,
                use_llm=True,
                content_hash=None,
                storage_path="documents/test.pdf",
                file_type="application/pdf", 
                text_extraction_result=None,
                diagram_processing_result=None,
                processed_summary=existing_summary,
                error=None,
                error_details=None
            )
            
            with patch.object(workflow.build_summary_node, 'execute') as mock_build:
                mock_build.return_value = DocumentProcessingState(
                    document_id=sample_document_id,
                    use_llm=True,
                    content_hash=None,
                    storage_path="documents/test.pdf",
                    file_type="application/pdf",
                    text_extraction_result=None,
                    diagram_processing_result=None,
                    processed_summary=existing_summary,
                    error=None,
                    error_details=None
                )
                
                # Act
                result = await workflow.process_document(sample_document_id, use_llm=True)
                
                # Assert
                assert isinstance(result, ProcessedDocumentSummary)
                assert result.success is True
                assert result.document_id == sample_document_id
                assert result.full_text == "Sample document text"
    
    @pytest.mark.asyncio
    async def test_full_processing_happy_path(self, workflow, sample_document_id, sample_text_extraction_result):
        """Test complete document processing workflow."""
        # Arrange - Mock all nodes to simulate successful processing
        document_metadata = {
            "id": sample_document_id,
            "storage_path": "documents/test.pdf",
            "file_type": "application/pdf",
            "content_hash": "test_hash_123",
            "processing_status": "pending",
            "original_filename": "test.pdf"
        }
        
        # Mock the nodes in sequence
        with patch.object(workflow.fetch_document_node, 'execute') as mock_fetch:
            mock_fetch.return_value = DocumentProcessingState(
                document_id=sample_document_id,
                use_llm=True,
                content_hash="test_hash_123",
                storage_path="documents/test.pdf",
                file_type="application/pdf",
                text_extraction_result=None,
                diagram_processing_result=None,
                processed_summary=None,
                error=None,
                error_details=None
            )
            
            with patch.object(workflow.already_processed_check_node, 'execute') as mock_check:
                mock_check.return_value = DocumentProcessingState(
                    document_id=sample_document_id,
                    use_llm=True,
                    content_hash="test_hash_123",
                    storage_path="documents/test.pdf",
                    file_type="application/pdf",
                    text_extraction_result=None,
                    diagram_processing_result=None,
                    processed_summary=None,  # No existing summary
                    error=None,
                    error_details=None
                )
                
                with patch.object(workflow.extract_text_node, 'execute') as mock_extract:
                    mock_extract.return_value = DocumentProcessingState(
                        document_id=sample_document_id,
                        use_llm=True,
                        content_hash="test_hash_123",
                        storage_path="documents/test.pdf",
                        file_type="application/pdf",
                        text_extraction_result=sample_text_extraction_result,
                        diagram_processing_result=None,
                        processed_summary=None,
                        error=None,
                        error_details=None
                    )
                    
                    with patch.object(workflow.build_summary_node, 'execute') as mock_build:
                        final_summary = ProcessedDocumentSummary(
                            success=True,
                            document_id=sample_document_id,
                            australian_state="NSW",
                            full_text="Sample contract text content",
                            character_count=28,
                            total_word_count=4,
                            total_pages=1,
                            extraction_method="pdf_native",
                            extraction_confidence=0.9,
                            processing_timestamp=datetime.now(timezone.utc).isoformat(),
                            llm_used=True
                        )
                        
                        mock_build.return_value = DocumentProcessingState(
                            document_id=sample_document_id,
                            use_llm=True,
                            content_hash="test_hash_123",
                            storage_path="documents/test.pdf",
                            file_type="application/pdf",
                            text_extraction_result=sample_text_extraction_result,
                            diagram_processing_result={},
                            processed_summary=final_summary,
                            error=None,
                            error_details=None
                        )
                        
                        # Mock other nodes to return success
                        workflow.mark_processing_started_node.execute = AsyncMock(side_effect=lambda x: x)
                        workflow.save_pages_node.execute = AsyncMock(side_effect=lambda x: x) 
                        workflow.aggregate_diagrams_node.execute = AsyncMock(side_effect=lambda x: x)
                        workflow.save_diagrams_node.execute = AsyncMock(side_effect=lambda x: x)
                        workflow.update_metrics_node.execute = AsyncMock(side_effect=lambda x: x)
                        workflow.mark_basic_complete_node.execute = AsyncMock(side_effect=lambda x: x)
                        
                        # Act
                        result = await workflow.process_document(sample_document_id, use_llm=True)
                        
                        # Assert
                        assert isinstance(result, ProcessedDocumentSummary)
                        assert result.success is True
                        assert result.document_id == sample_document_id
                        assert result.full_text == "Sample contract text content"
                        assert result.extraction_method == "pdf_native"
                        assert result.total_pages == 1
    
    @pytest.mark.asyncio 
    async def test_extraction_failure_path(self, workflow, sample_document_id):
        """Test workflow when text extraction fails."""
        # Arrange - Mock nodes up to extraction failure
        with patch.object(workflow.fetch_document_node, 'execute') as mock_fetch:
            mock_fetch.return_value = DocumentProcessingState(
                document_id=sample_document_id,
                use_llm=True,
                content_hash="test_hash_123",
                storage_path="documents/test.pdf", 
                file_type="application/pdf",
                text_extraction_result=None,
                diagram_processing_result=None,
                processed_summary=None,
                error=None,
                error_details=None
            )
            
            with patch.object(workflow.already_processed_check_node, 'execute') as mock_check:
                mock_check.return_value = DocumentProcessingState(
                    document_id=sample_document_id,
                    use_llm=True,
                    content_hash="test_hash_123",
                    storage_path="documents/test.pdf",
                    file_type="application/pdf",
                    text_extraction_result=None,
                    diagram_processing_result=None,
                    processed_summary=None,  # No existing summary
                    error=None,
                    error_details=None
                )
                
                with patch.object(workflow.extract_text_node, 'execute') as mock_extract:
                    # Mock extraction failure
                    mock_extract.return_value = DocumentProcessingState(
                        document_id=sample_document_id,
                        use_llm=True,
                        content_hash="test_hash_123",
                        storage_path="documents/test.pdf",
                        file_type="application/pdf",
                        text_extraction_result=None,
                        diagram_processing_result=None,
                        processed_summary=None,
                        error="Text extraction failed",
                        error_details={"node": "extract_text", "error_type": "ExtractionError"}
                    )
                    
                    with patch.object(workflow.error_handling_node, 'execute') as mock_error:
                        mock_error.return_value = DocumentProcessingState(
                            document_id=sample_document_id,
                            use_llm=True,
                            content_hash="test_hash_123",
                            storage_path="documents/test.pdf",
                            file_type="application/pdf",
                            text_extraction_result=None,
                            diagram_processing_result=None,
                            processed_summary=None,
                            error="Text extraction failed",
                            error_details={"node": "extract_text", "error_type": "ExtractionError"}
                        )
                        
                        # Mock other nodes
                        workflow.mark_processing_started_node.execute = AsyncMock(side_effect=lambda x: x)
                        
                        # Act
                        result = await workflow.process_document(sample_document_id, use_llm=True)
                        
                        # Assert
                        assert isinstance(result, ProcessingErrorResponse)
                        assert result.success is False
                        assert "Text extraction failed" in result.error
    
    @pytest.mark.asyncio
    async def test_document_not_found_failure(self, workflow, sample_document_id):
        """Test workflow when document is not found."""
        # Arrange
        with patch.object(workflow.fetch_document_node, 'execute') as mock_fetch:
            mock_fetch.return_value = DocumentProcessingState(
                document_id=sample_document_id,
                use_llm=True,
                content_hash=None,
                storage_path=None,
                file_type=None,
                text_extraction_result=None,
                diagram_processing_result=None,
                processed_summary=None,
                error="Document not found or access denied",
                error_details={"node": "fetch_document_record", "error_type": "NotFoundError"}
            )
            
            with patch.object(workflow.error_handling_node, 'execute') as mock_error:
                mock_error.return_value = DocumentProcessingState(
                    document_id=sample_document_id,
                    use_llm=True,
                    content_hash=None,
                    storage_path=None,
                    file_type=None,
                    text_extraction_result=None,
                    diagram_processing_result=None,
                    processed_summary=None,
                    error="Document not found or access denied",
                    error_details={"node": "fetch_document_record", "error_type": "NotFoundError"}
                )
                
                # Act
                result = await workflow.process_document(sample_document_id, use_llm=True)
                
                # Assert
                assert isinstance(result, ProcessingErrorResponse)
                assert result.success is False
                assert "Document not found or access denied" in result.error
    
    @pytest.mark.asyncio
    async def test_workflow_exception_handling(self, workflow, sample_document_id):
        """Test workflow handles unexpected exceptions gracefully."""
        # Arrange - Make fetch node throw an exception
        with patch.object(workflow.fetch_document_node, 'execute') as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected database error")
            
            # Act
            result = await workflow.process_document(sample_document_id, use_llm=True)
            
            # Assert
            assert isinstance(result, ProcessingErrorResponse)
            assert result.success is False
            assert "Workflow execution failed" in result.error


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])