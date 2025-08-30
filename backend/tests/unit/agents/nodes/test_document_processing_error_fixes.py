"""
Test suite for document processing error fixes

This module tests the fixes for:
1. Event loop attachment issues in Celery tasks
2. Type errors in database status updates  
3. Connection pool management improvements
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.agents.nodes.step0_document_processing.error_handling_node import ErrorHandlingNode
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.tasks.evaluation_tasks import run_async_task
from app.database.connection import get_user_connection


class TestEventLoopFixes:
    """Test event loop management improvements"""

    def test_run_async_task_decorator_with_existing_loop(self):
        """Test that run_async_task handles existing event loops properly"""
        
        @run_async_task
        async def sample_async_function(value):
            return f"processed_{value}"
        
        # Mock an existing running loop
        with patch('asyncio.get_running_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            
            # Mock create_task to return a completed future
            mock_task = Mock()
            mock_task.result.return_value = "processed_test"
            mock_loop.create_task.return_value = mock_task
            
            with patch('asyncio.create_task', return_value=mock_task):
                result = sample_async_function("test")
                assert result == mock_task
    
    def test_run_async_task_decorator_no_existing_loop(self):
        """Test that run_async_task creates new loop when none exists"""
        
        @run_async_task 
        async def sample_async_function(value):
            return f"processed_{value}"
        
        # Mock no existing loop (RuntimeError)
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No running loop")):
            with patch('asyncio.new_event_loop') as mock_new_loop:
                mock_loop = Mock()
                mock_loop.run_until_complete.return_value = "processed_test"
                mock_new_loop.return_value = mock_loop
                
                with patch('asyncio.set_event_loop'):
                    with patch('asyncio.all_tasks', return_value=[]):
                        result = sample_async_function("test")
                        assert result == "processed_test"
                        mock_loop.close.assert_called_once()


class TestDatabaseStatusUpdateFixes:
    """Test database status update type error fixes"""

    @pytest.fixture
    def error_handling_node(self):
        """Create ErrorHandlingNode instance for testing"""
        return ErrorHandlingNode()

    @pytest.fixture
    def sample_error_state(self):
        """Create sample error state for testing"""
        return DocumentProcessingState(
            document_id=str(uuid4()),
            use_llm=True,
            error="Test error message",
            error_details={
                "node": "test_node",
                "error_type": "TestError",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            storage_path=None,
            file_type=None,
            text_extraction_result=None,
            diagram_processing_result=None,
            processed_summary=None
        )

    @pytest.mark.asyncio
    async def test_error_handling_node_correct_parameter_passing(self, error_handling_node, sample_error_state):
        """Test that error handling node passes correct parameters to repository"""
        
        with patch.object(error_handling_node, 'get_user_client') as mock_get_client:
            with patch('app.services.repositories.documents_repository.DocumentsRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo.update_processing_status_and_results = AsyncMock()
                mock_repo_class.return_value = mock_repo
                
                # Mock base node methods
                error_handling_node._record_execution = Mock()
                error_handling_node._record_success = Mock()
                error_handling_node._log_info = Mock()
                error_handling_node._log_warning = Mock()
                
                result_state = await error_handling_node.execute(sample_error_state)
                
                # Verify that update_processing_status_and_results was called with correct parameters
                mock_repo.update_processing_status_and_results.assert_called_once()
                
                # Get the call arguments
                call_args = mock_repo.update_processing_status_and_results.call_args
                
                # Check that parameters are passed as keyword arguments
                assert 'document_id' in call_args.kwargs
                assert 'processing_status' in call_args.kwargs
                assert 'error_details' in call_args.kwargs
                
                # Check that processing_status is a string, not a dict
                assert isinstance(call_args.kwargs['processing_status'], str)
                assert call_args.kwargs['processing_status'] == 'FAILED'
                
                # Check that error_details is a dict
                assert isinstance(call_args.kwargs['error_details'], dict)
                assert 'error' in call_args.kwargs['error_details']

    @pytest.mark.asyncio
    async def test_error_handling_node_without_document_id(self, error_handling_node):
        """Test error handling when document_id is missing"""
        
        state_without_id = DocumentProcessingState(
            document_id=None,  # Missing document_id
            use_llm=True,
            error="Test error",
            error_details={},
            storage_path=None,
            file_type=None,
            text_extraction_result=None,
            diagram_processing_result=None,
            processed_summary=None
        )
        
        # Mock base node methods
        error_handling_node._record_execution = Mock()
        error_handling_node._log_warning = Mock()
        
        result_state = await error_handling_node.execute(state_without_id)
        
        # Should handle gracefully without database update
        assert result_state.get('error') is not None
        assert 'Missing document ID' in result_state.get('error', '')
        error_handling_node._log_warning.assert_called()


class TestConnectionPoolManagement:
    """Test connection pool management improvements"""

    @pytest.mark.asyncio 
    async def test_user_connection_error_handling(self):
        """Test that user connection context manager handles errors properly"""
        
        user_id = uuid4()
        
        # Mock the connection pool and connection
        with patch('app.database.connection.ConnectionPoolManager.get_user_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_connection = Mock()
            
            # Simulate connection acquisition success but usage error
            mock_pool.acquire.return_value = mock_connection
            mock_get_pool.return_value = mock_pool
            
            with patch('app.database.connection._setup_user_session') as mock_setup:
                with patch('app.database.connection._reset_session_gucs') as mock_reset:
                    with patch('app.database.connection.get_settings') as mock_settings:
                        mock_settings.return_value.db_pool_mode = "shared"
                        
                        # Test that connection is released even when an error occurs during usage
                        with pytest.raises(ValueError):
                            async with get_user_connection(user_id):
                                raise ValueError("Simulated database error")
                        
                        # Verify connection was still released
                        mock_pool.release.assert_called_once_with(mock_connection)

    @pytest.mark.asyncio
    async def test_connection_release_failure_handling(self):
        """Test that connection release failures are handled gracefully"""
        
        user_id = uuid4()
        
        with patch('app.database.connection.ConnectionPoolManager.get_user_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_connection = Mock()
            
            # Simulate connection release failure
            mock_pool.acquire.return_value = mock_connection
            mock_pool.release.side_effect = Exception("Connection release failed")
            mock_get_pool.return_value = mock_pool
            
            with patch('app.database.connection._setup_user_session'):
                with patch('app.database.connection._reset_session_gucs'):
                    with patch('app.database.connection.get_settings') as mock_settings:
                        mock_settings.return_value.db_pool_mode = "shared"
                        
                        with patch('app.database.connection.logger') as mock_logger:
                            # Should not raise exception despite release failure
                            async with get_user_connection(user_id):
                                pass
                            
                            # Should log the error
                            mock_logger.error.assert_called()


class TestIntegratedDocumentProcessingFixes:
    """Integration tests for all fixes working together"""

    @pytest.mark.asyncio
    async def test_document_processing_workflow_error_recovery(self):
        """Test that document processing workflow recovers from errors properly"""
        
        # Mock the document processing workflow components
        with patch('app.agents.subflows.document_processing_workflow.DocumentProcessingWorkflow') as mock_workflow_class:
            mock_workflow = Mock()
            mock_workflow.ainvoke = AsyncMock(side_effect=Exception("Simulated processing error"))
            mock_workflow_class.return_value = mock_workflow
            
            # Test that the workflow can be called in a Celery-like environment
            @run_async_task
            async def simulate_celery_task():
                try:
                    # Simulate calling the workflow like in a Celery task
                    result = await mock_workflow.ainvoke({
                        'document_id': str(uuid4()),
                        'use_llm': True
                    })
                    return result
                except Exception as e:
                    # Should handle error gracefully
                    return {'error': str(e), 'status': 'failed'}
            
            # This should not raise an exception
            with patch('asyncio.get_running_loop', side_effect=RuntimeError("No running loop")):
                result = simulate_celery_task()
                assert isinstance(result, dict)
                assert 'error' in result


if __name__ == "__main__":
    pytest.main([__file__])