"""
Tests for DocumentProcessingNode with user-aware background task integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, UTC

from backend.app.agents.nodes.document_processing_subflow.mainflow_entry import DocumentProcessingNode
from app.agents.states.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from app.core.auth_context import AuthContext


class TestDocumentProcessingNode:
    """Test cases for DocumentProcessingNode with authentication context."""

    @pytest.fixture
    def mock_workflow(self):
        """Mock workflow instance for node initialization."""
        workflow = Mock()
        workflow.use_llm_config = {"document_processing": True}
        workflow.enable_quality_checks = True
        return workflow

    @pytest.fixture
    def document_processing_node(self, mock_workflow):
        """Create DocumentProcessingNode instance for testing."""
        return DocumentProcessingNode(mock_workflow)

    @pytest.fixture
    def sample_state(self):
        """Sample RealEstateAgentState for testing."""
        return RealEstateAgentState(
            {
                "user_id": "user-456",
                "document_data": {
                    "document_id": "doc-123",
                    "file_name": "sample_contract.pdf",
                    "upload_timestamp": datetime.now(UTC).isoformat(),
                },
                "processing_status": ProcessingStatus.PENDING,
                "confidence_scores": {},
            }
        )

    @pytest.fixture
    async def mock_auth_context(self):
        """Mock authentication context."""
        with (
            patch.object(AuthContext, "get_user_id") as mock_get_user_id,
            patch.object(AuthContext, "get_user_token") as mock_get_token,
            patch.object(AuthContext, "is_authenticated") as mock_is_auth,
        ):

            mock_get_user_id.return_value = "user-456"
            mock_get_token.return_value = "mock-jwt-token"
            mock_is_auth.return_value = True

            yield "user-456"

    @pytest.fixture
    def successful_task_result(self):
        """Mock successful task result."""
        mock_result = Mock()
        mock_result.id = "task-789"
        mock_result.get.return_value = {
            "success": True,
            "full_text": "Sample contract text content extracted successfully.",
            "extraction_method": "background_task",
            "extraction_confidence": 0.92,
            "character_count": 55,
            "word_count": 9,
            "processing_time": 3.2,
            "llm_used": True,
        }
        return mock_result

    @pytest.mark.asyncio
    async def test_execute_success_with_background_task(
        self,
        document_processing_node,
        sample_state,
        mock_auth_context,
        successful_task_result,
    ):
        """Test successful document processing using background task."""

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            mock_task_manager.launch_user_task = AsyncMock(
                return_value=successful_task_result
            )

            # Execute the node
            result_state = await document_processing_node.execute(sample_state)

            # Verify task was launched correctly
            mock_task_manager.launch_user_task.assert_called_once()
            call_args = mock_task_manager.launch_user_task.call_args

            # Verify arguments passed to task launcher
            assert call_args[0][1].startswith("doc_process_doc-123_")  # task_id format
            assert call_args[0][2] == "doc-123"  # document_id
            assert call_args[0][3] == "user-456"  # user_id
            assert call_args[0][4] is True  # use_llm

            # Verify task result was retrieved
            successful_task_result.get.assert_called_once_with(timeout=300)

            # Verify state was updated correctly
            assert result_state.get("parsing_status") == ProcessingStatus.COMPLETED
            assert "document_metadata" in result_state

            metadata = result_state["document_metadata"]
            assert (
                metadata["full_text"]
                == "Sample contract text content extracted successfully."
            )
            assert metadata["extraction_method"] == "background_task"
            assert metadata["extraction_confidence"] == 0.92
            assert metadata["character_count"] == 55
            assert metadata["enhanced_processing"] is True

    @pytest.mark.asyncio
    async def test_execute_missing_document_id(
        self, document_processing_node, mock_auth_context
    ):
        """Test handling of missing document_id in state."""

        # State without document_id
        invalid_state = RealEstateAgentState(
            {
                "document_data": {},  # Missing document_id
                "processing_status": ProcessingStatus.PENDING,
            }
        )

        # Execute the node
        result_state = await document_processing_node.execute(invalid_state)

        # Should return error state
        assert "document_processing_failed" in str(result_state)

    @pytest.mark.asyncio
    async def test_execute_no_auth_context(
        self, document_processing_node, sample_state
    ):
        """Test handling of missing authentication context."""

        with patch.object(AuthContext, "get_user_id", return_value=None):
            # Execute the node without auth context
            result_state = await document_processing_node.execute(sample_state)

            # Should return error state
            assert "document_processing_failed" in str(result_state)

    @pytest.mark.asyncio
    async def test_execute_task_failure(
        self, document_processing_node, sample_state, mock_auth_context
    ):
        """Test handling of task execution failure."""

        # Mock task result with failure
        failed_task_result = Mock()
        failed_task_result.id = "failed-task-123"
        failed_task_result.get.return_value = {
            "success": False,
            "error": "Processing failed due to corrupted file",
            "extraction_confidence": 0.0,
        }

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            mock_task_manager.launch_user_task = AsyncMock(
                return_value=failed_task_result
            )

            # Execute the node
            result_state = await document_processing_node.execute(sample_state)

            # Should handle the failure gracefully
            assert result_state.get("error") is not None
            assert "Processing failed" in str(result_state.get("error", ""))

    @pytest.mark.asyncio
    async def test_execute_task_timeout(
        self, document_processing_node, sample_state, mock_auth_context
    ):
        """Test handling of task timeout."""

        # Mock task that times out
        timeout_task_result = Mock()
        timeout_task_result.id = "timeout-task-123"
        timeout_task_result.get.side_effect = Exception(
            "Task timeout after 300 seconds"
        )

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            mock_task_manager.launch_user_task = AsyncMock(
                return_value=timeout_task_result
            )

            # Execute the node
            result_state = await document_processing_node.execute(sample_state)

            # Should handle timeout error
            assert result_state.get("error") is not None
            assert "timeout" in str(result_state.get("error", "")).lower()

    @pytest.mark.asyncio
    async def test_execute_insufficient_text_content(
        self, document_processing_node, sample_state, mock_auth_context
    ):
        """Test handling of insufficient extracted text content."""

        # Mock task result with insufficient content
        insufficient_result = Mock()
        insufficient_result.id = "task-insufficient"
        insufficient_result.get.return_value = {
            "success": True,
            "full_text": "Short",  # Too short (< 100 chars)
            "extraction_method": "background_task",
            "extraction_confidence": 0.8,
            "character_count": 5,
            "word_count": 1,
        }

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            mock_task_manager.launch_user_task = AsyncMock(
                return_value=insufficient_result
            )

            # Execute the node
            result_state = await document_processing_node.execute(sample_state)

            # Should handle insufficient content
            assert result_state.get("error") is not None
            assert "Insufficient text content" in str(result_state.get("error", ""))

    @pytest.mark.asyncio
    async def test_execute_with_llm_disabled(
        self, sample_state, mock_auth_context, successful_task_result
    ):
        """Test document processing with LLM disabled."""

        # Create workflow with LLM disabled
        workflow_no_llm = Mock()
        workflow_no_llm.use_llm_config = {"document_processing": False}
        workflow_no_llm.enable_quality_checks = True

        node = DocumentProcessingNode(workflow_no_llm)

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            mock_task_manager.launch_user_task = AsyncMock(
                return_value=successful_task_result
            )

            # Execute the node
            result_state = await node.execute(sample_state)

            # Verify task was launched with use_llm=False
            call_args = mock_task_manager.launch_user_task.call_args
            assert call_args[0][4] is False  # use_llm parameter

    def test_text_quality_assessment(self, document_processing_node):
        """Test text quality assessment functionality."""

        # Test high quality text
        high_quality_text = """
        This is a comprehensive real estate purchase agreement between the vendor and purchaser.
        The property is located at 123 Main Street and includes various terms and conditions.
        Settlement is scheduled for 30 days from the contract date with a deposit of $50,000.
        """

        quality_result = document_processing_node._assess_text_quality(
            high_quality_text
        )

        assert quality_result["score"] > 0.7
        assert len(quality_result["issues"]) == 0
        assert quality_result["metrics"]["character_count"] > 200
        assert quality_result["metrics"]["word_count"] > 30

        # Test low quality text
        low_quality_text = "a b c d e f"

        quality_result = document_processing_node._assess_text_quality(low_quality_text)

        assert quality_result["score"] < 0.5
        assert len(quality_result["issues"]) > 0
        assert "Too few words extracted" in quality_result["issues"]

    @pytest.mark.asyncio
    async def test_error_handling_with_auth_context(
        self, document_processing_node, sample_state, mock_auth_context
    ):
        """Test error handling includes authentication context information."""

        with patch(
            "app.agents.nodes.document_processing_node.task_manager"
        ) as mock_task_manager:
            # Mock task manager to raise exception
            mock_task_manager.launch_user_task = AsyncMock(
                side_effect=Exception("Task launch failed")
            )

            # Execute the node
            result_state = await document_processing_node.execute(sample_state)

            # Verify error state includes auth context info
            error_details = result_state.get("context", {})
            assert error_details.get("user_id") == "user-456"
            assert error_details.get("has_auth_context") is True


class TestDocumentProcessingNodeIntegration:
    """Integration tests for DocumentProcessingNode."""

    @pytest.mark.asyncio
    async def test_full_processing_workflow(self):
        """Test complete document processing workflow with real-like conditions."""

        # Set up authentication context
        AuthContext.set_auth_context(
            token="integration-test-token",
            user_id="integration-user-123",
            user_email="integration@test.com",
        )

        try:
            # Create workflow and node
            workflow = Mock()
            workflow.use_llm_config = {"document_processing": True}
            workflow.enable_quality_checks = True

            node = DocumentProcessingNode(workflow)

            # Create realistic state
            state = RealEstateAgentState(
                {
                    "document_data": {
                        "document_id": "integration-doc-456",
                        "file_name": "test_contract.pdf",
                        "upload_timestamp": datetime.now(UTC).isoformat(),
                    },
                    "processing_status": ProcessingStatus.PENDING,
                    "session_id": "integration-session-789",
                }
            )

            # Mock the background task execution
            with patch(
                "app.agents.nodes.document_processing_node.task_manager"
            ) as mock_task_manager:
                mock_result = Mock()
                mock_result.id = "integration-task-123"
                mock_result.get.return_value = {
                    "success": True,
                    "full_text": "Integration test contract document with comprehensive content for testing purposes.",
                    "extraction_method": "background_task",
                    "extraction_confidence": 0.88,
                    "character_count": 89,
                    "word_count": 13,
                    "processing_time": 4.1,
                    "llm_used": True,
                }

                mock_task_manager.launch_user_task = AsyncMock(return_value=mock_result)

                # Execute processing
                result_state = await node.execute(state)

                # Verify successful processing
                assert result_state.get("parsing_status") == ProcessingStatus.COMPLETED
                assert "document_metadata" in result_state
                assert result_state["confidence_scores"]["document_processing"] > 0.7

                # Verify task was launched with correct context
                mock_task_manager.launch_user_task.assert_called_once()

        finally:
            # Clean up auth context
            AuthContext.clear_auth_context()
