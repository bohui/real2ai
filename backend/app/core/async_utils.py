"""
Async utilities for safe database connection management with per-loop registry design.

This module provides essential utilities for database connection handling in the dual-mode architecture:
- Per-loop registry system enables true concurrent dual-loop operation  
- Transaction-local GUCs prevent session bleed in shared pools
- Safe repository pattern with explicit user_id passing eliminates session state dependencies
- @langgraph_safe_task decorator provides automatic cross-loop protection and retry logic
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

T = TypeVar("T")


def ensure_single_event_loop():
    """
    Ensure async operations run in a dedicated event loop to prevent conflicts.

    This decorator forces async tasks to run in a dedicated thread with its own
    event loop to prevent conflicts between Celery's event loop management
    and other async frameworks like LangGraph and asyncpg.

    Note: This is primarily used for the complete workflow isolation pattern
    where entire LangGraph workflows run in dedicated threads.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we're already in an async context
            try:
                current_loop = asyncio.get_running_loop()
                # If we're in a running loop, we need to run in a separate thread
                logger.debug(
                    f"Running {func.__name__} in thread executor to avoid loop conflict"
                )

                with ThreadPoolExecutor(max_workers=1, thread_name_prefix="isolated-") as executor:
                    future = executor.submit(
                        _run_async_in_new_loop, func, *args, **kwargs
                    )
                    return future.result()

            except RuntimeError:
                # No running loop, safe to create our own
                logger.debug(f"Running {func.__name__} in new event loop")
                return asyncio.run(func(*args, **kwargs))

        return wrapper

    return decorator


def _run_async_in_new_loop(
    coro_func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs
) -> T:
    """
    Run an async function in a new event loop within a thread.

    This ensures complete isolation from any existing event loops.
    """
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro_func(*args, **kwargs))
    finally:
        # Clean up the event loop
        try:
            # Clean up any remaining tasks
            pending_tasks = asyncio.all_tasks(loop)
            if pending_tasks:
                for task in pending_tasks:
                    task.cancel()
            loop.close()
        except Exception as e:
            logger.debug(f"Event loop cleanup error: {e}")


async def ensure_async_pool_initialization():
    """
    Ensure database connection pools are initialized for the current event loop.

    With the per-loop registry system, this simply ensures that a registry
    exists for the current event loop. Pools are created on-demand.
    """
    try:
        # Import here to avoid circular imports
        from app.database.connection import ConnectionPoolManager

        # Get current loop info
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        logger.debug(
            f"[POOL] Ensuring pool registry exists for loop {current_loop_id}"
        )

        # This will create a registry for this loop if it doesn't exist
        # Pools are created on-demand when needed
        ConnectionPoolManager._get_loop_registry(current_loop)

        logger.debug(
            f"[POOL] Pool registry ready for event loop {current_loop_id}"
        )

    except Exception as e:
        logger.warning(f"[POOL] Failed to ensure pool initialization: {e}")


def celery_async_task(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator for Celery tasks that need to run async code safely.

    This combines @ensure_single_event_loop with proper pool initialization
    to create a safe environment for async code in Celery workers.
    """

    @ensure_single_event_loop()
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Ensure database pools are properly initialized
        await ensure_async_pool_initialization()

        # Run the original function
        return await func(*args, **kwargs)

    return wrapper


def detect_cross_loop_issue(exc: Exception) -> bool:
    """
    Detect if an exception is caused by cross-event loop issues.

    Args:
        exc: Exception to analyze

    Returns:
        True if this is a cross-loop issue, False otherwise
    """
    error_msg = str(exc).lower()
    cross_loop_indicators = [
        "attached to a different loop",
        "future attached to a different loop", 
        "task was destroyed but it is pending",
        "cannot be called from a running event loop",
        "connection was closed in the middle of operation",
        "cannot perform operation: another operation is in progress",
    ]

    return any(indicator in error_msg for indicator in cross_loop_indicators)


class AsyncContextManager:
    """
    Context manager for safely running async operations in Celery workers.

    Usage:
        async with AsyncContextManager():
            # Safe to run async operations here
            result = await some_async_function()
    """

    def __init__(self):
        self.was_running = False

    async def __aenter__(self):
        try:
            # Check if there's already a running loop
            asyncio.get_running_loop()
            self.was_running = True
            logger.debug("Using existing event loop")
        except RuntimeError:
            # No running loop, we're safe to create our own
            self.was_running = False
            logger.debug("Creating new event loop context")

        # Ensure database pools are properly initialized
        await ensure_async_pool_initialization()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clean up if we created the loop context
        if not self.was_running:
            logger.debug("Event loop context cleaned up")

        # Log any exceptions
        if exc_type:
            logger.error(f"Exception in async context: {exc_type.__name__}: {exc_val}")

        return False  # Don't suppress exceptions



def langgraph_safe_task(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., T]:
    """
    Decorator for Celery tasks that execute LangGraph workflows safely.

    This provides enhanced protection specifically for tasks that use LangGraph,
    including cross-loop detection and automatic recovery.

    Usage:
        @celery_app.task
        @langgraph_safe_task
        async def my_workflow_task(...):
            # LangGraph workflow execution here
            return result
    """

    @ensure_single_event_loop()
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                # Ensure database pools are properly initialized
                await ensure_async_pool_initialization()

                # Execute the function
                return await func(*args, **kwargs)

            except Exception as e:
                is_cross_loop = detect_cross_loop_issue(e)
                is_last_attempt = attempt == max_retries

                if is_cross_loop and not is_last_attempt:
                    logger.warning(
                        f"Cross-loop issue detected in {func.__name__} (attempt {attempt + 1}), retrying...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "error": str(e),
                        },
                    )

                    # Brief delay before retry
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue

                else:
                    # Not a cross-loop issue or final attempt
                    if is_cross_loop:
                        logger.error(
                            f"Cross-loop issue persisted after {max_retries} retries in {func.__name__}: {e}"
                        )
                    raise

        # Should never reach here
        raise RuntimeError(f"Unexpected execution path in {func.__name__}")

    return wrapper


# Complex callback management removed - handled by @langgraph_safe_task decorator


# Simplified async utilities - complex isolation handled by per-loop registry + @langgraph_safe_task