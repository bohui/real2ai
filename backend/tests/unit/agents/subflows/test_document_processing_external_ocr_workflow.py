"""
Unit tests for DocumentProcessingExternalOCRWorkflow and related nodes.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch

from app.agents.subflows.document_processing_external_ocr_workflow import (
    DocumentProcessingExternalOCRWorkflow,
    ExternalOCRProcessingState
)
from app.schema.document import ProcessedDocumentSummary, ProcessingErrorResponse
from app.core.auth_context import AuthContext


class TestExternalOCRProcessingNodes:
    """Test individual nodes in the external OCR processing workflow."""

    @pytest.fixture
    def temp_ocr_dir(self):
        """Create temporary OCR directory with sample files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample OCR output files
            page_files = []
            for page_num in [1, 2]:
                # Regular markdown file
                md_path = os.path.join(temp_dir, f"document_page_{page_num}.md")
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Page {page_num}\n\nThis is the content of page {page_num}.\n\n"
                            f"![Diagram](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==)")
                
                # JPG file
                jpg_path = os.path.join(temp_dir, f"document_page_{page_num}.jpg")
                with open(jpg_path, 'wb') as f:
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')  # Minimal JPEG header
                
                # JSON file  
                json_path = os.path.join(temp_dir, f"document_page_{page_num}.json")
                with open(json_path, 'w') as f:
                    json.dump({
                        'page_number': page_num,
                        'confidence': 0.95,
                        'text_blocks': [{'text': f'Content for page {page_num}'}]
                    }, f)
                
                page_files.append({
                    'page_number': page_num,
                    'md_path': md_path,
                    'jpg_path': jpg_path, 
                    'json_path': json_path
                })
            
            yield temp_dir, page_files

    @pytest.fixture
    def sample_state(self, temp_ocr_dir):
        """Create sample processing state."""
        temp_dir, page_files = temp_ocr_dir
        return ExternalOCRProcessingState(
            document_id="test-doc-123",
            use_llm=False,
            external_ocr_dir=temp_dir,
            content_hmac="test-content-hmac-456", 
            algorithm_version=1,
            params_fingerprint="external_ocr",
            ocr_pages=None,
            page_artifacts=None,
            page_jpg_artifacts=None,
            page_json_artifacts=None,
            diagram_artifacts=None,
            processed_summary=None,
            error=None,
            error_details=None,
            storage_path=temp_dir,
            file_type="external_ocr",
            text_extraction_result=None,
            diagram_processing_result=None
        )

    @pytest.fixture
    def mock_auth_context(self):
        """Mock authentication context."""
        with patch.object(AuthContext, 'get_current_context') as mock_context:
            mock_user = Mock()
            mock_user.user_id = "test-user-456"
            mock_context.return_value = mock_user
            yield mock_user

    @pytest.mark.asyncio
    async def test_ingest_external_ocr_outputs_node_success(self, sample_state, temp_ocr_dir, mock_auth_context):
        """Test IngestExternalOCROutputsNode successful execution."""
        from app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node import IngestExternalOCROutputsNode
        
        temp_dir, page_files = temp_ocr_dir
        node = IngestExternalOCROutputsNode()
        
        result_state = await node.execute(sample_state)
        
        # Verify successful ingestion
        assert result_state.get('error') is None
        assert 'ocr_pages' in result_state
        assert len(result_state['ocr_pages']) == 2
        
        # Check page mapping structure
        page = result_state['ocr_pages'][0]
        assert 'page_number' in page
        assert 'md_path' in page
        assert 'jpg_path' in page
        assert 'json_path' in page
        assert 'chosen_md_variant' in page

    @pytest.mark.asyncio
    async def test_ingest_external_ocr_outputs_node_missing_directory(self, mock_auth_context):
        """Test IngestExternalOCROutputsNode with missing directory."""
        from app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node import IngestExternalOCROutputsNode
        
        state = ExternalOCRProcessingState(
            document_id="test-doc",
            use_llm=False,
            external_ocr_dir="/nonexistent/directory",
            content_hmac="test-hmac",
            algorithm_version=1,
            params_fingerprint="external_ocr",
            storage_path="/nonexistent/directory",
            file_type="external_ocr",
            text_extraction_result=None,
            diagram_processing_result=None
        )
        
        node = IngestExternalOCROutputsNode()
        result_state = await node.execute(state)
        
        # Should have error
        assert result_state.get('error') is not None
        assert 'does not exist' in result_state['error']

    @pytest.mark.asyncio
    async def test_save_page_markdown_node_success(self, sample_state, temp_ocr_dir, mock_auth_context):
        """Test SavePageMarkdownAsArtifactPagesNode successful execution."""
        from app.agents.nodes.document_processing_subflow.save_page_markdown_node import SavePageMarkdownAsArtifactPagesNode
        
        temp_dir, page_files = temp_ocr_dir
        
        # Set up state with OCR pages
        sample_state['ocr_pages'] = [
            {
                'page_number': 1,
                'md_path': page_files[0]['md_path'],
                'jpg_path': page_files[0]['jpg_path'],
                'json_path': page_files[0]['json_path'],
                'chosen_md_variant': 'regular'
            }
        ]
        
        node = SavePageMarkdownAsArtifactPagesNode()
        
        # Mock the dependencies
        with patch.object(node, 'storage_service') as mock_storage, \
             patch.object(node, 'artifacts_repo') as mock_repo:
            
            mock_storage.upload_page_markdown = AsyncMock(return_value=("test-uri", "test-sha256"))
            mock_artifact = Mock()
            mock_artifact.id = "artifact-123"
            mock_repo.insert_page_artifact = AsyncMock(return_value=mock_artifact)
            
            result_state = await node.execute(sample_state)
            
            # Verify successful processing
            assert result_state.get('error') is None
            assert 'page_artifacts' in result_state
            assert len(result_state['page_artifacts']) == 1
            
            artifact = result_state['page_artifacts'][0]
            assert artifact['artifact_id'] == "artifact-123"
            assert artifact['page_number'] == 1
            assert artifact['uri'] == "test-uri"
            assert artifact['sha256'] == "test-sha256"

    @pytest.mark.asyncio
    async def test_extract_diagrams_node_success(self, sample_state, temp_ocr_dir, mock_auth_context):
        """Test ExtractDiagramsFromMarkdownNode successful execution."""
        from app.agents.nodes.document_processing_subflow.extract_diagrams_node import ExtractDiagramsFromMarkdownNode
        
        temp_dir, page_files = temp_ocr_dir
        
        # Set up state with OCR pages
        sample_state['ocr_pages'] = [
            {
                'page_number': 1,
                'md_path': page_files[0]['md_path'],
                'jpg_path': page_files[0]['jpg_path'],
                'json_path': page_files[0]['json_path'],
                'chosen_md_variant': 'regular'
            }
        ]
        
        node = ExtractDiagramsFromMarkdownNode()
        
        # Mock the dependencies
        with patch.object(node, 'storage_service') as mock_storage, \
             patch.object(node, 'artifacts_repo') as mock_repo:
            
            mock_storage.upload_diagram_image = AsyncMock(return_value=("diagram-uri", "diagram-sha256"))
            mock_diagram = Mock()
            mock_diagram.id = "diagram-456"
            mock_repo.insert_diagram_artifact = AsyncMock(return_value=mock_diagram)
            
            result_state = await node.execute(sample_state)
            
            # Verify successful processing
            assert result_state.get('error') is None
            assert 'diagram_artifacts' in result_state
            assert len(result_state['diagram_artifacts']) == 1
            
            diagram = result_state['diagram_artifacts'][0]
            assert diagram['artifact_id'] == "diagram-456"
            assert diagram['page_number'] == 1
            assert 'diagram_key' in diagram
            assert diagram['uri'] == "diagram-uri"


class TestDocumentProcessingExternalOCRWorkflow:
    """Test the complete external OCR processing workflow."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentProcessingExternalOCRWorkflow(storage_bucket="test-documents")

    @pytest.fixture
    def temp_ocr_dir(self):
        """Create temporary OCR directory with sample files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample files for testing
            for page_num in [1, 2]:
                # Markdown with embedded image
                md_path = os.path.join(temp_dir, f"doc_page_{page_num}.md")
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Page {page_num}\nContent for page {page_num}.\n")
                
                # JPG file
                jpg_path = os.path.join(temp_dir, f"doc_page_{page_num}.jpg")
                with open(jpg_path, 'wb') as f:
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01')
                
                # JSON file
                json_path = os.path.join(temp_dir, f"doc_page_{page_num}.json")
                with open(json_path, 'w') as f:
                    json.dump({'page': page_num, 'confidence': 0.9}, f)
            
            yield temp_dir

    @pytest.fixture
    def mock_auth_context(self):
        """Mock authentication context."""
        with patch.object(AuthContext, 'get_current_context') as mock_context:
            mock_user = Mock()
            mock_user.user_id = "workflow-test-user"
            mock_context.return_value = mock_user
            yield mock_user

    @pytest.mark.asyncio
    async def test_workflow_success(self, workflow, temp_ocr_dir, mock_auth_context):
        """Test complete workflow execution success."""
        
        # Mock all node dependencies
        with patch('app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node.IngestExternalOCROutputsNode') as mock_ingest, \
             patch('app.agents.nodes.document_processing_subflow.save_page_markdown_node.SavePageMarkdownAsArtifactPagesNode') as mock_md, \
             patch('app.agents.nodes.document_processing_subflow.save_page_jpg_node.SavePageJPGAsArtifactPagesJPGNode') as mock_jpg, \
             patch('app.agents.nodes.document_processing_subflow.save_page_json_node.SavePageJSONAsArtifactPagesJSONNode') as mock_json, \
             patch('app.agents.nodes.document_processing_subflow.extract_diagrams_node.ExtractDiagramsFromMarkdownNode') as mock_diagrams:
            
            # Setup mock node instances
            for mock_class, result_key in [
                (mock_ingest, 'ocr_pages'),
                (mock_md, 'page_artifacts'), 
                (mock_jpg, 'page_jpg_artifacts'),
                (mock_json, 'page_json_artifacts'),
                (mock_diagrams, 'diagram_artifacts')
            ]:
                mock_instance = AsyncMock()
                mock_instance.execute = AsyncMock(side_effect=self._mock_node_success(result_key))
                mock_class.return_value = mock_instance
            
            # Execute workflow
            result = await workflow.process_external_ocr(
                document_id="test-workflow-doc",
                external_ocr_dir=temp_ocr_dir,
                content_hmac="workflow-test-hmac",
                algorithm_version=1,
                params_fingerprint="external_ocr"
            )
            
            # Verify successful result
            assert isinstance(result, ProcessedDocumentSummary)
            assert result.success is True
            assert result.document_id == "test-workflow-doc"
            assert result.total_pages == 2
            assert result.extraction_methods == ["external_ocr"]
            assert result.overall_confidence == 1.0

    @pytest.mark.asyncio
    async def test_workflow_ingestion_failure(self, workflow, temp_ocr_dir, mock_auth_context):
        """Test workflow with ingestion failure."""
        
        with patch('app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node.IngestExternalOCROutputsNode') as mock_ingest:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(return_value={
                'error': 'Failed to find OCR files',
                'error_details': {'node': 'ingest_ocr_outputs'}
            })
            mock_ingest.return_value = mock_instance
            
            # Execute workflow
            result = await workflow.process_external_ocr(
                document_id="test-failure-doc",
                external_ocr_dir="/nonexistent",
                content_hmac="test-hmac",
                algorithm_version=1,
                params_fingerprint="external_ocr"
            )
            
            # Verify error response
            assert isinstance(result, ProcessingErrorResponse)
            assert result.success is False
            assert "Failed to find OCR files" in result.error

    @pytest.mark.asyncio
    async def test_workflow_partial_processing_failure(self, workflow, temp_ocr_dir, mock_auth_context):
        """Test workflow with partial processing failure."""
        
        with patch('app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node.IngestExternalOCROutputsNode') as mock_ingest, \
             patch('app.agents.nodes.document_processing_subflow.save_page_markdown_node.SavePageMarkdownAsArtifactPagesNode') as mock_md:
            
            # First node succeeds
            mock_ingest_instance = AsyncMock()
            mock_ingest_instance.execute = AsyncMock(side_effect=self._mock_node_success('ocr_pages'))
            mock_ingest.return_value = mock_ingest_instance
            
            # Second node fails
            mock_md_instance = AsyncMock()
            mock_md_instance.execute = AsyncMock(return_value={
                'error': 'Failed to save markdown artifacts',
                'error_details': {'node': 'save_markdown'}
            })
            mock_md.return_value = mock_md_instance
            
            # Execute workflow
            result = await workflow.process_external_ocr(
                document_id="test-partial-failure",
                external_ocr_dir=temp_ocr_dir,
                content_hmac="test-hmac",
                algorithm_version=1,
                params_fingerprint="external_ocr"
            )
            
            # Verify error response
            assert isinstance(result, ProcessingErrorResponse)
            assert result.success is False
            assert "Failed to save markdown artifacts" in result.error

    @pytest.mark.asyncio
    async def test_workflow_exception_handling(self, workflow, temp_ocr_dir, mock_auth_context):
        """Test workflow exception handling."""
        
        with patch('app.agents.nodes.document_processing_subflow.ingest_external_ocr_outputs_node.IngestExternalOCROutputsNode') as mock_ingest:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(side_effect=Exception("Unexpected node error"))
            mock_ingest.return_value = mock_instance
            
            # Execute workflow
            result = await workflow.process_external_ocr(
                document_id="test-exception",
                external_ocr_dir=temp_ocr_dir,
                content_hmac="test-hmac",
                algorithm_version=1,
                params_fingerprint="external_ocr"
            )
            
            # Verify error response
            assert isinstance(result, ProcessingErrorResponse)
            assert result.success is False
            assert "Workflow execution failed" in result.error

    def test_workflow_conditional_edges(self, workflow):
        """Test workflow conditional edge logic."""
        
        # Test successful ingestion
        success_state = {'ocr_pages': [{'page_number': 1}]}
        assert workflow.check_ingestion_success(success_state) == "success"
        
        # Test failed ingestion
        error_state = {'error': 'Ingestion failed'}
        assert workflow.check_ingestion_success(error_state) == "error"
        
        # Test missing ocr_pages
        empty_state = {}
        assert workflow.check_ingestion_success(empty_state) == "error"
        
        # Test general processing success
        assert workflow.check_processing_success({'some_result': True}) == "success"
        assert workflow.check_processing_success({'error': 'Processing failed'}) == "error"

    def test_workflow_metrics(self, workflow):
        """Test workflow metrics collection."""
        metrics = workflow.get_metrics()
        
        assert metrics['workflow_type'] == 'external_ocr_processing'
        assert metrics['storage_bucket'] == 'test-documents'
        assert 'total_nodes' in metrics
        assert 'node_metrics' in metrics

    def _mock_node_success(self, result_key):
        """Helper to create mock node execution that adds expected result to state."""
        async def mock_execute(state):
            # Simulate successful node execution
            new_state = state.copy()
            
            if result_key == 'ocr_pages':
                new_state[result_key] = [
                    {'page_number': 1, 'md_path': 'page1.md'},
                    {'page_number': 2, 'md_path': 'page2.md'}
                ]
            elif result_key in ['page_artifacts', 'page_jpg_artifacts', 'page_json_artifacts']:
                new_state[result_key] = [
                    {'artifact_id': 'artifact-1', 'page_number': 1, 'metrics': {'word_count': 50}},
                    {'artifact_id': 'artifact-2', 'page_number': 2, 'metrics': {'word_count': 75}}
                ]
            elif result_key == 'diagram_artifacts':
                new_state[result_key] = [
                    {'artifact_id': 'diagram-1', 'page_number': 1}
                ]
            
            return new_state
        
        return mock_execute


class TestExternalOCRNodeEdgeCases:
    """Test edge cases and error conditions for individual nodes."""

    @pytest.mark.asyncio
    async def test_save_page_markdown_node_missing_files(self):
        """Test SavePageMarkdownNode with missing markdown files."""
        from app.agents.nodes.document_processing_subflow.save_page_markdown_node import SavePageMarkdownAsArtifactPagesNode
        
        state = ExternalOCRProcessingState(
            document_id="test-doc",
            use_llm=False,
            content_hmac="test-hmac",
            algorithm_version=1,
            params_fingerprint="external_ocr",
            ocr_pages=[{
                'page_number': 1,
                'md_path': '/nonexistent/file.md',
                'jpg_path': '/nonexistent/file.jpg', 
                'json_path': '/nonexistent/file.json',
                'chosen_md_variant': 'regular'
            }],
            storage_path="test",
            file_type="external_ocr",
            text_extraction_result=None,
            diagram_processing_result=None
        )
        
        node = SavePageMarkdownAsArtifactPagesNode()
        
        with patch.object(AuthContext, 'get_current_context') as mock_context:
            mock_user = Mock()
            mock_user.user_id = "test-user"
            mock_context.return_value = mock_user
            
            result_state = await node.execute(state)
            
            # Should handle missing files gracefully
            assert result_state.get('error') is not None
            assert 'No pages were successfully processed' in result_state['error']

    @pytest.mark.asyncio
    async def test_extract_diagrams_node_no_images(self):
        """Test ExtractDiagramsNode with markdown containing no images."""
        from app.agents.nodes.document_processing_subflow.extract_diagrams_node import ExtractDiagramsFromMarkdownNode
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create markdown file without base64 images
            md_path = os.path.join(temp_dir, "no_images.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write("# Page 1\n\nThis page has no embedded images.\n\nJust regular text content.")
            
            state = ExternalOCRProcessingState(
                document_id="test-doc",
                use_llm=False,
                content_hmac="test-hmac",
                algorithm_version=1,
                params_fingerprint="external_ocr",
                ocr_pages=[{
                    'page_number': 1,
                    'md_path': md_path,
                    'jpg_path': 'dummy.jpg',
                    'json_path': 'dummy.json',
                    'chosen_md_variant': 'regular'
                }],
                storage_path="test",
                file_type="external_ocr", 
                text_extraction_result=None,
                diagram_processing_result=None
            )
            
            node = ExtractDiagramsFromMarkdownNode()
            
            with patch.object(AuthContext, 'get_current_context') as mock_context:
                mock_user = Mock()
                mock_user.user_id = "test-user"
                mock_context.return_value = mock_user
                
                result_state = await node.execute(state)
                
                # Should succeed with empty diagram list
                assert result_state.get('error') is None
                assert result_state.get('diagram_artifacts') == []

    def test_external_ocr_workflow_state_inheritance(self):
        """Test that ExternalOCRProcessingState properly inherits from DocumentProcessingState."""
        state = ExternalOCRProcessingState(
            document_id="test-inheritance",
            use_llm=False,
            external_ocr_dir="/test/path",
            content_hmac="test-hmac",
            algorithm_version=1,
            params_fingerprint="external_ocr",
            storage_path="test",
            file_type="external_ocr", 
            text_extraction_result=None,
            diagram_processing_result=None
        )
        
        # Verify base fields are accessible
        assert state['document_id'] == "test-inheritance"
        assert state['use_llm'] is False
        
        # Verify extended fields are accessible
        assert state['external_ocr_dir'] == "/test/path"
        assert state['content_hmac'] == "test-hmac"
        assert state['algorithm_version'] == 1
        assert state['params_fingerprint'] == "external_ocr"