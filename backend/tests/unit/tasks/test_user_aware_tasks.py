"""
Tests for user-aware background tasks with authentication context management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.tasks.user_aware_tasks import run_document_processing_subflow
from app.core.auth_context import AuthContext
from app.core.task_context import task_manager
from app.services.document_service import DocumentService


class TestUserAwareTasks:
    """Test cases for user-aware background tasks."""

    @pytest.fixture
    async def mock_auth_context(self):
        """Mock authentication context for testing."""
        with (
            patch.object(AuthContext, "get_user_id") as mock_get_user_id,
            patch.object(AuthContext, "get_user_token") as mock_get_token,
            patch.object(AuthContext, "is_authenticated") as mock_is_auth,
        ):

            mock_get_user_id.return_value = "test-user-123"
            mock_get_token.return_value = "mock-jwt-token"
            mock_is_auth.return_value = True

            yield {"user_id": "test-user-123", "token": "mock-jwt-token"}

    @pytest.fixture
    def mock_document_service(self):
        """Mock document service for testing."""
        mock_service = Mock(spec=DocumentService)
        mock_service.initialize = AsyncMock()
        mock_service.process_document_by_id = AsyncMock()
        return mock_service

    @pytest.fixture
    def sample_processing_result(self):
        """Sample document processing result."""
        return {
            "success": True,
            "full_text": "This is a sample contract document with extracted text content.",
            "extraction_method": "background_task",
            "extraction_confidence": 0.95,
            "character_count": 65,
            "word_count": 11,
            "processing_time": 2.5,
            "llm_used": True,
        }

    @pytest.mark.asyncio
    async def test_process_document_with_context_success(
        self, mock_auth_context, mock_document_service, sample_processing_result
    ):
        """Test successful document processing with authentication context."""

        # Mock successful processing
        mock_document_service.process_document_by_id.return_value = (
            sample_processing_result
        )

        # Mock celery task
        mock_task = Mock()
        mock_task.request.id = "task-123"
        mock_task.update_state = Mock()

        with patch("app.tasks.user_aware_tasks.DocumentService") as MockDocumentService:
            MockDocumentService.return_value = mock_document_service

            # Execute the task function
            result = await process_document_with_context.__wrapped__(
                mock_task, document_id="doc-456", user_id="test-user-123", use_llm=True
            )

        # Verify document service was initialized
        mock_document_service.initialize.assert_called_once()

        # Verify document processing was called
        mock_document_service.process_document_by_id.assert_called_once_with(
            document_id="doc-456"
        )

        # Verify task state updates
        assert mock_task.update_state.call_count >= 2

        # Verify result structure
        assert result["success"] is True
        assert result["document_id"] == "doc-456"
        assert result["user_id"] == "test-user-123"
        assert result["task_id"] == "task-123"
        assert "processing_time" in result
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_process_document_user_context_mismatch(
        self, mock_document_service, sample_processing_result
    ):
        """Test handling of user context mismatch."""

        # Mock mismatched user context
        with patch.object(AuthContext, "get_user_id", return_value="different-user"):
            mock_task = Mock()
            mock_task.request.id = "task-123"

            # Should raise ValueError for user mismatch
            with pytest.raises(Exception) as exc_info:
                await process_document_with_context.__wrapped__(
                    mock_task,
                    document_id="doc-456",
                    user_id="test-user-123",
                    use_llm=True,
                )

            assert "User context mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_document_service_failure(
        self, mock_auth_context, mock_document_service
    ):
        """Test handling of document service failures."""

        # Mock service failure
        mock_document_service.process_document_by_id.return_value = {
            "success": False,
            "error": "Document processing failed",
            "extraction_confidence": 0.0,
        }

        mock_task = Mock()
        mock_task.request.id = "task-123"
        mock_task.update_state = Mock()

        with patch("app.tasks.user_aware_tasks.DocumentService") as MockDocumentService:
            MockDocumentService.return_value = mock_document_service

            # Should raise exception for processing failure
            with pytest.raises(Exception) as exc_info:
                await process_document_with_context.__wrapped__(
                    mock_task,
                    document_id="doc-456",
                    user_id="test-user-123",
                    use_llm=True,
                )

            assert "Document processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_document_initialization_failure(
        self, mock_auth_context, mock_document_service
    ):
        """Test handling of service initialization failures."""

        # Mock initialization failure
        mock_document_service.initialize.side_effect = Exception(
            "Initialization failed"
        )

        mock_task = Mock()
        mock_task.request.id = "task-123"

        with patch("app.tasks.user_aware_tasks.DocumentService") as MockDocumentService:
            MockDocumentService.return_value = mock_document_service

            # Should raise exception for initialization failure
            with pytest.raises(Exception) as exc_info:
                await process_document_with_context.__wrapped__(
                    mock_task,
                    document_id="doc-456",
                    user_id="test-user-123",
                    use_llm=True,
                )

            assert "Initialization failed" in str(exc_info.value)

    def test_task_configuration(self):
        """Test that the task is properly configured with decorators."""

        # Verify the task has the required decorators and configuration
        assert hasattr(process_document_with_context, "delay")
        assert hasattr(process_document_with_context, "apply_async")

        # The task should be bound to self for progress updates
        assert process_document_with_context.request is not None or hasattr(
            process_document_with_context, "_get_request"
        )

    @pytest.mark.asyncio
    async def test_task_manager_integration(self, mock_auth_context):
        """Test integration with task manager for launching tasks."""

        with (
            patch.object(task_manager, "create_task_context") as mock_create_context,
            patch.object(process_document_with_context, "delay") as mock_delay,
        ):

            # Mock context creation
            mock_create_context.return_value = "context-key-123"

            # Mock task result
            mock_task_result = Mock()
            mock_task_result.id = "task-456"
            mock_delay.return_value = mock_task_result

            # Launch task
            result = await task_manager.launch_user_task(
                process_document_with_context,
                "task-id-789",
                "doc-123",
                "user-456",
                True,
            )

            # Verify context was created
            mock_create_context.assert_called_once_with("task-id-789")

            # Verify task was launched with context key
            mock_delay.assert_called_once_with(
                "context-key-123", "doc-123", "user-456", True
            )

            # Verify result
            assert result.id == "task-456"


class TestTaskContextIntegration:
    """Test integration between tasks and authentication context."""

    @pytest.mark.asyncio
    async def test_auth_context_propagation(self):
        """Test that authentication context is properly propagated to background tasks."""

        # Set up authentication context
        AuthContext.set_auth_context(
            token="test-jwt-token",
            user_id="test-user-123",
            user_email="test@example.com",
        )

        try:
            # Create task context
            task_context = AuthContext.create_task_context()

            # Verify context data
            assert task_context["user_token"] == "test-jwt-token"
            assert task_context["user_id"] == "test-user-123"
            assert task_context["user_email"] == "test@example.com"
            assert "created_at" in task_context

            # Clear context and restore from task context
            AuthContext.clear_auth_context()
            assert AuthContext.get_user_id() is None

            # Restore context
            AuthContext.restore_task_context(task_context)

            # Verify restoration
            assert AuthContext.get_user_id() == "test-user-123"
            assert AuthContext.get_user_token() == "test-jwt-token"
            assert AuthContext.get_user_email() == "test@example.com"

        finally:
            # Clean up
            AuthContext.clear_auth_context()

    @pytest.mark.asyncio
    async def test_isolated_client_creation(self, mock_auth_context):
        """Test creation of isolated clients for concurrent tasks."""

        with patch("app.core.auth_context.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.set_user_token = Mock()
            mock_get_client.return_value = mock_client

            # Get isolated authenticated client
            client = await AuthContext.get_isolated_authenticated_client()

            # Verify client was configured with user token
            mock_client.set_user_token.assert_called_once()
            assert client == mock_client
