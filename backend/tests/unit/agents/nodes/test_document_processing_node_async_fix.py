"""
Unit tests for DocumentProcessingNode async event loop fix.

Tests ensure that the DocumentProcessingNode properly handles async operations
without causing event loop conflicts when called from ContractAnalysisWorkflow.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.nodes.step0_document_processing.mainflow_entry import (
    DocumentProcessingNode,
)
from app.agents.states.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from app.schema.document import ProcessedDocumentSummary


class TestDocumentProcessingNodeAsyncFix:
    """Test the async event loop fix for DocumentProcessingNode."""

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow for testing."""
        mock = Mock()
        mock.use_llm_config = {"document_processing": True}
        mock.enable_quality_checks = True
        return mock

    @pytest.fixture
    def document_processing_node(self, mock_workflow):
        """Create DocumentProcessingNode instance for testing."""
        return DocumentProcessingNode(mock_workflow)

    @pytest.fixture
    def sample_state(self):
        """Create sample state for testing."""
        return RealEstateAgentState(
            {
                "document_id": "test-document-123",
                "document_data": {
                    "id": "test-document-123",
                    "storage_path": "documents/test.pdf",
                    "file_type": "pdf",
                    "content_hash": "test-hash-123",
                },
                "current_step": "document_processing",
                "processing_start_time": "2024-01-15T10:00:00Z",
                "metadata": {"test": True},
            }
        )

    @pytest.mark.asyncio
    @patch("app.agents.nodes.document_processing_node.DocumentProcessingWorkflow")
    @patch("app.core.auth_context.AuthContext.get_user_id")
    async def test_async_context_manager_prevents_event_loop_conflicts(
        self,
        mock_get_user_id,
        mock_workflow_class,
        document_processing_node,
        sample_state,
    ):
        """Test that AsyncContextManager prevents event loop conflicts."""
        # Setup mocks
        mock_get_user_id.return_value = "test-user-123"

        # Mock successful document processing
        mock_workflow_instance = AsyncMock()
        mock_workflow_class.return_value = mock_workflow_instance

        mock_result = ProcessedDocumentSummary(
            success=True,
            document_id="test-document-123",
            total_pages=5,
            character_count=1000,
            processing_time=2.5,
            extraction_method="hybrid",
            processing_timestamp="2024-01-15T10:00:00Z",
        )
        mock_workflow_instance.process_document.return_value = mock_result

        # Execute the node
        result_state = await document_processing_node.execute(sample_state)

        # Verify the workflow was called within async context
        mock_workflow_class.assert_called_once_with(
            use_llm_document_processing=True, storage_bucket="documents"
        )

        mock_workflow_instance.process_document.assert_called_once_with(
            document_id="test-document-123", use_llm=True, content_hash="test-hash-123"
        )

        # Verify successful result
        assert result_state["processing_status"] == ProcessingStatus.COMPLETED
        assert result_state["processed_summary"] == mock_result

    @pytest.mark.asyncio
    @patch("app.agents.nodes.document_processing_node.DocumentProcessingWorkflow")
    @patch("app.core.auth_context.AuthContext.get_user_id")
    async def test_async_context_manager_handles_workflow_errors(
        self,
        mock_get_user_id,
        mock_workflow_class,
        document_processing_node,
        sample_state,
    ):
        """Test that AsyncContextManager properly handles workflow errors."""
        # Setup mocks
        mock_get_user_id.return_value = "test-user-123"

        # Mock workflow that raises an error
        mock_workflow_instance = AsyncMock()
        mock_workflow_class.return_value = mock_workflow_instance
        mock_workflow_instance.process_document.side_effect = RuntimeError(
            "Task got Future attached to a different loop"
        )

        # Execute the node
        result_state = await document_processing_node.execute(sample_state)

        # Verify error handling
        assert result_state["processing_status"] == ProcessingStatus.FAILED
        assert "Document processing subflow failed" in result_state["processing_errors"]

    @pytest.mark.asyncio
    @patch("app.core.async_utils.ensure_async_pool_initialization")
    @patch("app.agents.nodes.document_processing_node.DocumentProcessingWorkflow")
    @patch("app.core.auth_context.AuthContext.get_user_id")
    async def test_async_pool_initialization_called(
        self,
        mock_get_user_id,
        mock_workflow_class,
        mock_pool_init,
        document_processing_node,
        sample_state,
    ):
        """Test that async pool initialization is called."""
        # Setup mocks
        mock_get_user_id.return_value = "test-user-123"
        mock_pool_init.return_value = None

        mock_workflow_instance = AsyncMock()
        mock_workflow_class.return_value = mock_workflow_instance
        mock_workflow_instance.process_document.return_value = ProcessedDocumentSummary(
            success=True,
            document_id="test-document-123",
            total_pages=1,
            character_count=100,
            processing_time=1.0,
            extraction_method="hybrid",
            processing_timestamp="2024-01-15T10:00:00Z",
        )

        # Execute the node
        await document_processing_node.execute(sample_state)

        # Verify async pool initialization was called
        mock_pool_init.assert_called_once()

    def test_multiple_concurrent_workflow_calls_no_conflict(self):
        """Test that multiple concurrent workflow calls don't cause event loop conflicts."""

        async def simulate_workflow_call(node, state, call_id):
            """Simulate a workflow call that might cause event loop conflicts."""
            # This would normally cause the "Future attached to different loop" error
            # before our fix
            state_copy = state.copy()
            state_copy["document_id"] = f"doc-{call_id}"
            return await node.execute(state_copy)

        async def run_concurrent_test():
            """Run multiple workflow calls concurrently."""
            # Create test components
            mock_workflow = Mock()
            mock_workflow.use_llm_config = {"document_processing": True}
            mock_workflow.enable_quality_checks = True

            node = DocumentProcessingNode(mock_workflow)

            sample_state = RealEstateAgentState(
                {
                    "document_id": "base-document",
                    "document_data": {
                        "id": "base-document",
                        "storage_path": "documents/base.pdf",
                        "file_type": "pdf",
                        "content_hash": "base-hash",
                    },
                    "current_step": "document_processing",
                    "processing_start_time": "2024-01-15T10:00:00Z",
                    "metadata": {"test": True},
                }
            )

            # Mock workflow calls to avoid actual processing
            with patch(
                "app.agents.nodes.document_processing_node.DocumentProcessingWorkflow"
            ) as mock_class:
                with patch(
                    "app.core.auth_context.AuthContext.get_user_id"
                ) as mock_auth:
                    mock_auth.return_value = "test-user"

                    # Create multiple concurrent calls
                    tasks = []
                    for i in range(3):
                        task = simulate_workflow_call(node, sample_state, i)
                        tasks.append(task)

                    # This should not raise event loop conflicts
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # All calls should succeed or fail gracefully (no event loop errors)
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            # Should not be event loop related errors
                            assert "Future attached to a different loop" not in str(
                                result
                            )

        # Run the concurrent test
        asyncio.run(run_concurrent_test())
