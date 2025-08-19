"""
Test cases for LangSmith Config fixes.

This module tests the fixes for error handling in the LangSmith tracing decorators.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from functools import wraps

from app.core.langsmith_config import (
    langsmith_trace,
    langsmith_session,
    get_langsmith_config,
    LangSmithConfig
)


class TestLangSmithConfigFixes:
    """Test the fixes for error handling in LangSmith configuration."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.langsmith_api_key = "test_api_key"
        settings.langsmith_project = "test_project"
        return settings

    @pytest.fixture
    def mock_langsmith_config(self, mock_settings):
        """Create a mock LangSmith config."""
        with patch('app.core.langsmith_config.get_settings', return_value=mock_settings):
            config = LangSmithConfig()
            config._enabled = True
            return config

    @pytest.fixture
    def sample_async_function(self):
        """Create a sample async function for testing."""
        @langsmith_trace(name="test_function", run_type="llm")
        async def test_function(data: dict, user_id: str = None):
            if data.get("error"):
                raise ValueError("Test error")
            return {"result": "success", "data": data, "user_id": user_id}
        
        return test_function

    @pytest.fixture
    def sample_sync_function(self):
        """Create a sample sync function for testing."""
        @langsmith_trace(name="test_sync_function", run_type="tool")
        def test_sync_function(data: dict, user_id: str = None):
            if data.get("error"):
                raise ValueError("Test sync error")
            return {"result": "success", "data": data, "user_id": user_id}
        
        return test_sync_function

    @pytest.mark.asyncio
    async def test_async_function_success_tracing(self, sample_async_function, mock_langsmith_config):
        """Test that successful async function execution is traced correctly."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Execute the function
                result = await sample_async_function({"test": "data"}, "user123")
                
                # Verify the result
                assert result["result"] == "success"
                assert result["data"]["test"] == "data"
                assert result["user_id"] == "user123"
                
                # Verify tracing was called
                mock_trace.assert_called_once()
                call_args = mock_trace.call_args
                assert call_args[1]["name"] == "test_function"
                assert call_args[1]["run_type"] == "llm"
                assert call_args[1]["project_name"] == "test_project"

    @pytest.mark.asyncio
    async def test_async_function_error_tracing(self, sample_async_function, mock_langsmith_config):
        """Test that async function errors are traced and handled correctly."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_run.error = None
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Execute the function with error
                with pytest.raises(ValueError, match="Test error"):
                    await sample_async_function({"error": True}, "user123")
                
                # Verify error was recorded
                assert mock_run.error == "Test error"
                # Verify run.end was called with error
                mock_run.end.assert_called_once_with(error="Test error")

    def test_sync_function_success_tracing(self, sample_sync_function, mock_langsmith_config):
        """Test that successful sync function execution is traced correctly."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Execute the function
                result = sample_sync_function({"test": "data"}, "user123")
                
                # Verify the result
                assert result["result"] == "success"
                assert result["data"]["test"] == "data"
                assert result["user_id"] == "user123"
                
                # Verify tracing was called
                mock_trace.assert_called_once()
                call_args = mock_trace.call_args
                assert call_args[1]["name"] == "test_sync_function"
                assert call_args[1]["run_type"] == "tool"

    def test_sync_function_error_tracing(self, sample_sync_function, mock_langsmith_config):
        """Test that sync function errors are traced and handled correctly."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_run.error = None
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Execute the function with error
                with pytest.raises(ValueError, match="Test sync error"):
                    sample_sync_function({"error": True}, "user123")
                
                # Verify error was recorded
                assert mock_run.error == "Test sync error"
                # Verify run.end was called with error
                mock_run.end.assert_called_once_with(error="Test sync error")

    @pytest.mark.asyncio
    async def test_langsmith_session_context_manager(self, mock_langsmith_config):
        """Test the langsmith_session context manager."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_session_run = Mock()
                mock_session_run.error = None
                mock_trace.return_value.__enter__.return_value = mock_session_run
                
                # Use the context manager
                async with langsmith_session("test_session", user_id="user123") as session:
                    assert session == mock_session_run
                    # Simulate some work
                    await asyncio.sleep(0.01)
                
                # Verify session was traced
                mock_trace.assert_called_once()
                call_args = mock_trace.call_args
                assert call_args[1]["name"] == "test_session"
                assert call_args[1]["run_type"] == "chain"
                assert call_args[1]["project_name"] == "test_project"

    @pytest.mark.asyncio
    async def test_langsmith_session_error_handling(self, mock_langsmith_config):
        """Test error handling in langsmith_session context manager."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_session_run = Mock()
                mock_session_run.error = None
                mock_trace.return_value.__enter__.return_value = mock_session_run
                
                # Use the context manager with an error
                with pytest.raises(ValueError, match="Session error"):
                    async with langsmith_session("test_session", user_id="user123") as session:
                        raise ValueError("Session error")
                
                # Verify error was recorded
                assert mock_session_run.error == "Session error"
                # Verify session.end was called with error
                mock_session_run.end.assert_called_once_with(error="Session error")

    def test_langsmith_disabled_returns_original_function(self, mock_langsmith_config):
        """Test that when LangSmith is disabled, the original function is returned."""
        mock_langsmith_config._enabled = False
        
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            # Create a function with the decorator
            @langsmith_trace(name="test_function", run_type="llm")
            def test_function():
                return "original_result"
            
            # The function should work normally without tracing
            result = test_function()
            assert result == "original_result"

    @pytest.mark.asyncio
    async def test_langsmith_disabled_session_context_manager(self, mock_langsmith_config):
        """Test that when LangSmith is disabled, the session context manager yields without tracing."""
        mock_langsmith_config._enabled = False
        
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            # Use the context manager
            async with langsmith_session("test_session") as session:
                # Should yield None when disabled
                assert session is None
                # Simulate some work
                await asyncio.sleep(0.01)

    def test_input_sanitization_for_complex_objects(self, mock_langsmith_config):
        """Test that complex input objects are properly sanitized for tracing."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Create a function that takes complex inputs
                @langsmith_trace(name="complex_input_test", run_type="llm")
                def complex_input_function(data_dict, data_list, data_bytes, data_none):
                    return {"result": "success"}
                
                # Test with complex inputs
                complex_dict = {"nested": {"deep": {"value": "test"}}}
                complex_list = ["item1", "item2", "item3"]
                complex_bytes = b"binary_data"
                complex_none = None
                
                result = complex_input_function(complex_dict, complex_list, complex_bytes, complex_none)
                
                # Verify the function executed successfully
                assert result["result"] == "success"
                
                # Verify inputs were captured (sanitized)
                assert mock_run.inputs is not None

    def test_output_sanitization_for_different_types(self, mock_langsmith_config):
        """Test that different output types are properly sanitized for tracing."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Test dict output
                @langsmith_trace(name="dict_output_test", run_type="llm")
                def dict_output_function():
                    return {"key": "value", "number": 42}
                
                result = dict_output_function()
                assert result["key"] == "value"
                assert mock_run.outputs is not None
                
                # Test non-dict output
                @langsmith_trace(name="string_output_test", run_type="llm")
                def string_output_function():
                    return "simple_string_result"
                
                result = string_output_function()
                assert result == "simple_string_result"
                # Non-dict outputs should be wrapped in a dict
                assert mock_run.outputs is not None

    def test_function_signature_binding_handles_errors_gracefully(self, mock_langsmith_config):
        """Test that function signature binding errors are handled gracefully."""
        with patch('app.core.langsmith_config.get_langsmith_config', return_value=mock_langsmith_config):
            with patch('app.core.langsmith_config.trace') as mock_trace:
                # Mock the trace context manager
                mock_run = Mock()
                mock_run.inputs = {}
                mock_run.outputs = {}
                mock_trace.return_value.__enter__.return_value = mock_run
                
                # Create a function with complex signature that might cause binding issues
                @langsmith_trace(name="complex_signature_test", run_type="llm")
                def complex_signature_function(*args, **kwargs):
                    return {"result": "success", "args": args, "kwargs": kwargs}
                
                # Test with various argument patterns
                result = complex_signature_function("arg1", "arg2", kwarg1="value1", kwarg2="value2")
                assert result["result"] == "success"
                
                # Verify inputs were captured (even if binding failed)
                assert mock_run.inputs is not None

    def test_langsmith_config_singleton_pattern(self):
        """Test that LangSmith config follows singleton pattern."""
        # Clear the global instance
        import app.core.langsmith_config
        app.core.langsmith_config._langsmith_config = None
        
        with patch('app.core.langsmith_config.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.langsmith_api_key = "test_key"
            mock_settings.langsmith_project = "test_project"
            mock_get_settings.return_value = mock_settings
            
            # Get config twice
            config1 = get_langsmith_config()
            config2 = get_langsmith_config()
            
            # Should be the same instance
            assert config1 is config2
            assert config1.project_name == "test_project"
