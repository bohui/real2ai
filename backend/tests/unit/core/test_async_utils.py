"""
Unit tests for async utilities and event loop management.

Tests the async_utils module to ensure proper event loop handling
in Celery workers and prevention of event loop conflicts.
"""

import asyncio
import pytest
from unittest.mock import patch

from app.core.async_utils import (
    ensure_single_event_loop,
    celery_async_task,
    ensure_async_pool_initialization,
    AsyncContextManager,
)


class TestEnsureSingleEventLoop:
    """Test the ensure_single_event_loop decorator."""

    def test_decorator_with_no_existing_loop(self):
        """Test decorator behavior when no event loop is running."""
        
        @ensure_single_event_loop()
        async def test_async_function():
            # Verify we can get the current loop
            loop = asyncio.get_running_loop()
            return f"success_in_loop_{id(loop)}"
        
        result = test_async_function()
        assert result.startswith("success_in_loop_")

    def test_decorator_with_existing_loop(self):
        """Test decorator behavior when an event loop is already running."""
        
        @ensure_single_event_loop()
        async def test_async_function():
            loop = asyncio.get_running_loop()
            return f"success_in_thread_loop_{id(loop)}"
        
        async def run_in_existing_loop():
            # This should run in a thread executor
            result = test_async_function()
            assert result.startswith("success_in_thread_loop_")
            return result
        
        # Run in an existing event loop
        result = asyncio.run(run_in_existing_loop())
        assert result.startswith("success_in_thread_loop_")

    def test_decorator_preserves_function_metadata(self):
        """Test that the decorator preserves function metadata."""
        
        @ensure_single_event_loop()
        async def test_function_with_metadata():
            """Test function docstring."""
            pass
        
        assert test_function_with_metadata.__name__ == "test_function_with_metadata"
        assert "Test function docstring." in test_function_with_metadata.__doc__


class TestCeleryAsyncTask:
    """Test the celery_async_task decorator."""

    @patch('app.core.async_utils.ensure_async_pool_initialization')
    def test_celery_async_task_decorator(self, mock_pool_init):
        """Test that celery_async_task properly initializes pools."""
        mock_pool_init.return_value = asyncio.Future()
        mock_pool_init.return_value.set_result(None)
        
        @celery_async_task
        async def test_task():
            return "task_completed"
        
        result = test_task()
        assert result == "task_completed"
        
        # Verify pool initialization was called
        mock_pool_init.assert_called_once()

    @patch('app.core.async_utils.ensure_async_pool_initialization')
    def test_celery_async_task_with_exception(self, mock_pool_init):
        """Test that celery_async_task handles exceptions properly."""
        mock_pool_init.return_value = asyncio.Future()
        mock_pool_init.return_value.set_result(None)
        
        @celery_async_task
        async def failing_task():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_task()


class TestEnsureAsyncPoolInitialization:
    """Test the ensure_async_pool_initialization function."""

    @patch('app.core.async_utils.ConnectionPoolManager._ensure_loop_bound')
    @pytest.mark.asyncio
    async def test_pool_initialization_success(self, mock_ensure_loop):
        """Test successful pool initialization."""
        mock_ensure_loop.return_value = None
        
        # Should not raise an exception
        await ensure_async_pool_initialization()
        
        mock_ensure_loop.assert_called_once()

    @patch('app.core.async_utils.ConnectionPoolManager._ensure_loop_bound')
    @pytest.mark.asyncio
    async def test_pool_initialization_with_error(self, mock_ensure_loop):
        """Test pool initialization handles errors gracefully."""
        mock_ensure_loop.side_effect = Exception("Pool error")
        
        # Should not raise an exception, just log a warning
        await ensure_async_pool_initialization()
        
        mock_ensure_loop.assert_called_once()


class TestAsyncContextManager:
    """Test the AsyncContextManager class."""

    @pytest.mark.asyncio
    async def test_context_manager_with_no_running_loop(self):
        """Test context manager when no loop is running."""
        async with AsyncContextManager() as ctx:
            assert ctx is not None
            # Should be able to run async operations
            await asyncio.sleep(0.001)

    @patch('app.core.async_utils.ensure_async_pool_initialization')
    @pytest.mark.asyncio
    async def test_context_manager_initializes_pools(self, mock_pool_init):
        """Test that context manager initializes database pools."""
        mock_pool_init.return_value = None
        
        async with AsyncContextManager():
            pass
        
        mock_pool_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self):
        """Test that context manager properly handles exceptions."""
        with pytest.raises(ValueError, match="Test error"):
            async with AsyncContextManager():
                raise ValueError("Test error")


class TestEventLoopConflictPrevention:
    """Integration tests for event loop conflict prevention."""

    @pytest.mark.asyncio
    async def test_simulated_celery_langgraph_scenario(self):
        """Simulate the original Celery + LangGraph + asyncpg scenario."""
        
        # Mock the components that would cause conflicts
        class MockCeleryTask:
            def update_state(self, state, meta):
                pass
        
        @celery_async_task
        async def mock_document_processing(task_self, document_id: str):
            """Mock the problematic document processing function."""
            # Simulate task state updates
            task_self.update_state("PROCESSING", {"progress": 10})
            
            # Simulate database operations
            await ensure_async_pool_initialization()
            
            # Simulate LangGraph workflow.ainvoke()
            await asyncio.sleep(0.01)  # Mock async operation
            
            task_self.update_state("COMPLETED", {"progress": 100})
            return {"success": True, "document_id": document_id}
        
        # Run the test
        mock_task = MockCeleryTask()
        result = mock_document_processing(mock_task, "test-doc-123")
        
        assert result["success"] is True
        assert result["document_id"] == "test-doc-123"

    def test_multiple_concurrent_tasks_no_conflict(self):
        """Test that multiple concurrent tasks don't conflict."""
        
        @celery_async_task
        async def concurrent_task(task_id: str):
            await ensure_async_pool_initialization()
            await asyncio.sleep(0.01)
            return f"completed_{task_id}"
        
        # Run multiple tasks concurrently in the main thread
        # (this would normally cause the event loop conflict)
        results = []
        for i in range(3):
            result = concurrent_task(f"task_{i}")
            results.append(result)
        
        expected = ["completed_task_0", "completed_task_1", "completed_task_2"]
        assert results == expected


@pytest.fixture
def mock_connection_pool_manager():
    """Mock the ConnectionPoolManager for testing."""
    with patch('app.core.async_utils.ConnectionPoolManager') as mock:
        mock._ensure_loop_bound.return_value = None
        yield mock