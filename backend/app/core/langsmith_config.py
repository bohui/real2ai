"""
LangSmith integration configuration and utilities.
"""

import os
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import asynccontextmanager
import inspect
from langsmith import Client
from langsmith.run_helpers import trace

from .config import get_settings

logger = logging.getLogger(__name__)


class LangSmithConfig:
    """LangSmith configuration manager."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Client] = None
        self._enabled = bool(self.settings.langsmith_api_key)

    @property
    def enabled(self) -> bool:
        """Check if LangSmith is enabled."""
        return self._enabled

    @property
    def client(self) -> Optional[Client]:
        """Get LangSmith client."""
        if not self._enabled:
            return None

        if not self._client:
            self._client = Client(
                api_key=self.settings.langsmith_api_key,
                api_url=os.getenv(
                    "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
                ),
            )
        return self._client

    @property
    def project_name(self) -> str:
        """Get project name for tracing."""
        return self.settings.langsmith_project

    def configure_environment(self) -> None:
        """Configure environment variables for LangSmith."""
        if self._enabled:
            os.environ["LANGSMITH_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = self.settings.langsmith_project
            os.environ["LANGSMITH_TRACING"] = "true"
            logger.info(
                f"LangSmith configured for project: {self.settings.langsmith_project}"
            )
        else:
            # Ensure tracing is disabled if no API key
            os.environ.pop("LANGSMITH_API_KEY", None)
            os.environ["LANGSMITH_TRACING"] = "false"
            logger.info("LangSmith tracing disabled - no API key provided")


# Global instance
_langsmith_config: Optional[LangSmithConfig] = None


def get_langsmith_config() -> LangSmithConfig:
    """Get LangSmith configuration singleton."""
    global _langsmith_config
    if _langsmith_config is None:
        _langsmith_config = LangSmithConfig()
        _langsmith_config.configure_environment()
    return _langsmith_config


def langsmith_trace(name: Optional[str] = None, run_type: str = "llm", **trace_kwargs):
    """
    Decorator for tracing LLM operations with LangSmith.

    Args:
        name: Custom name for the trace operation
        run_type: Type of operation (llm, chain, tool, etc.)
        **trace_kwargs: Additional tracing parameters
    """

    def decorator(func: Callable):
        config = get_langsmith_config()

        if not config.enabled:
            # Return original function if LangSmith is disabled
            return func

        # Use the function name if no custom name provided
        trace_name = name or f"{func.__module__}.{func.__qualname__}"

        # Helpers to capture and sanitize inputs/outputs so they appear in LangSmith
        # Respect settings to disable truncation entirely
        settings = config.settings
        MAX_STRING_LENGTH = (
            None
            if not settings.langsmith_truncation_enabled
            else settings.langsmith_max_string_length
        )
        MAX_LIST_ITEMS = (
            None
            if not settings.langsmith_truncation_enabled
            else settings.langsmith_max_list_items
        )
        MAX_DICT_ITEMS = (
            None
            if not settings.langsmith_truncation_enabled
            else settings.langsmith_max_dict_items
        )

        def _sanitize_value(value: Any) -> Any:
            try:
                if value is None or isinstance(value, (int, float, bool)):
                    return value
                if isinstance(value, str):
                    if MAX_STRING_LENGTH is None:
                        return value
                    return (
                        value
                        if len(value) <= MAX_STRING_LENGTH
                        else value[:MAX_STRING_LENGTH] + "... [truncated]"
                    )
                if isinstance(value, (bytes, bytearray)):
                    return {"type": "bytes", "length": len(value)}
                if isinstance(value, dict):
                    sanitized_items: Dict[str, Any] = {}
                    for idx, (k, v) in enumerate(value.items()):
                        if MAX_DICT_ITEMS is not None and idx >= MAX_DICT_ITEMS:
                            sanitized_items["__truncated__"] = True
                            break
                        sanitized_items[str(k)] = _sanitize_value(v)
                    return sanitized_items
                if isinstance(value, (list, tuple, set)):
                    sanitized_list = []
                    for idx, item in enumerate(list(value)):
                        if MAX_LIST_ITEMS is not None and idx >= MAX_LIST_ITEMS:
                            sanitized_list.append({"__truncated__": True})
                            break
                        sanitized_list.append(_sanitize_value(item))
                    return sanitized_list
                if hasattr(value, "dict") and callable(getattr(value, "dict")):
                    return _sanitize_value(value.dict())
                if hasattr(value, "model_dump") and callable(
                    getattr(value, "model_dump")
                ):
                    return _sanitize_value(value.model_dump())
                string_value = str(value)
                if MAX_STRING_LENGTH is None:
                    return string_value
                return (
                    string_value
                    if len(string_value) <= MAX_STRING_LENGTH
                    else string_value[:MAX_STRING_LENGTH] + "... [truncated]"
                )
            except Exception:
                return "<unserializable>"

        def _build_inputs_dict(
            fn: Callable, args: tuple, kwargs: dict
        ) -> Dict[str, Any]:
            try:
                signature = inspect.signature(fn)
                try:
                    bound = signature.bind_partial(*args, **kwargs)
                except Exception:
                    bound = None
                inputs: Dict[str, Any] = {}
                if bound:
                    for name, val in bound.arguments.items():
                        if name == "self":
                            continue
                        inputs[name] = _sanitize_value(val)
                else:
                    # Fallback: if binding fails, capture as is
                    if args:
                        inputs["args"] = _sanitize_value(
                            args[1:] if hasattr(args[0], "__class__") else args
                        )
                    if kwargs:
                        inputs["kwargs"] = _sanitize_value(kwargs)
                return inputs
            except Exception:
                return {"error": "failed_to_capture_inputs"}

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Add metadata
            metadata = {
                "function": func.__name__,
                "module": func.__module__,
                "run_type": run_type,
                **trace_kwargs,
            }

            # Extract client information from args if available
            if args and hasattr(args[0], "client_name"):
                metadata["client_name"] = args[0].client_name

            # Capture sanitized inputs BEFORE starting the run so they are visible while pending
            captured_inputs = _build_inputs_dict(func, args, kwargs)

            # Use LangSmith's trace context manager
            with trace(
                name=trace_name,
                run_type=run_type,
                project_name=config.project_name,
                inputs=captured_inputs,
                metadata=metadata,
            ) as run:
                try:
                    result = await func(*args, **kwargs)
                    # Record outputs generically
                    if isinstance(result, dict):
                        # Keep dicts as-is after sanitization
                        run.outputs = _sanitize_value(result)
                    else:
                        # Always wrap non-dict outputs so downstream expects a mapping
                        run.outputs = {"result": _sanitize_value(result)}
                    return result
                except Exception as e:
                    run.error = str(e)
                    # Ensure run is properly ended with error
                    run.end(error=str(e))
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Handle synchronous functions (though most will be async)
            metadata = {
                "function": func.__name__,
                "module": func.__module__,
                "run_type": run_type,
                **trace_kwargs,
            }

            # Capture sanitized inputs BEFORE starting the run so they are visible while pending
            captured_inputs = _build_inputs_dict(func, args, kwargs)

            with trace(
                name=trace_name,
                run_type=run_type,
                project_name=config.project_name,
                inputs=captured_inputs,
                metadata=metadata,
            ) as run:
                try:
                    result = func(*args, **kwargs)
                    if isinstance(result, dict):
                        run.outputs = _sanitize_value(result)
                    else:
                        run.outputs = {"result": _sanitize_value(result)}
                    return result
                except Exception as e:
                    run.error = str(e)
                    run.end(error=str(e))
                    raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def langsmith_session(session_name: str, **metadata):
    """
    Context manager for grouping related LLM operations in a session.

    Args:
        session_name: Name for the session
        **metadata: Additional metadata for the session
    """
    config = get_langsmith_config()

    if not config.enabled:
        # If LangSmith is disabled, just yield without tracing
        yield
        return

    with trace(
        name=session_name,
        run_type="chain",
        project_name=config.project_name,
        metadata=metadata,
    ) as session_run:
        try:
            yield session_run
        except Exception as e:
            session_run.error = str(e)
            session_run.end(error=str(e))
            raise


def get_trace_url(run_id: str) -> Optional[str]:
    """
    Generate LangSmith trace URL for a given run ID.

    Args:
        run_id: The run ID from LangSmith

    Returns:
        URL to the trace in LangSmith UI or None if not configured
    """
    config = get_langsmith_config()
    if not config.enabled:
        return None

    base_url = os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com")
    project_name = config.project_name
    return f"{base_url}/o/default/projects/p/{project_name}/r/{run_id}"


def log_trace_info(operation: str, **metadata):
    """
    Log trace information for debugging.

    Args:
        operation: Name of the operation
        **metadata: Additional metadata to log
    """
    config = get_langsmith_config()
    if config.enabled:
        logger.info(
            f"LangSmith trace: {operation}",
            extra={
                "project": config.project_name,
                "langsmith_enabled": True,
                **metadata,
            },
        )
    else:
        logger.debug(f"Operation: {operation} (LangSmith disabled)", extra=metadata)
