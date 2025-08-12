"""
Async utilities for proper event loop management in Celery workers.

This module provides utilities to ensure proper async execution in Celery workers
and prevents event loop conflicts between Celery, LangGraph, and asyncpg.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

T = TypeVar('T')


def ensure_single_event_loop():
    """
    Ensure all async operations use the same event loop.
    
    This decorator forces async tasks to run in a dedicated thread with its own
    event loop to prevent conflicts between Celery's event loop management
    and other async frameworks like LangGraph and asyncpg.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we're already in an async context
            try:
                current_loop = asyncio.get_running_loop()
                # If we're in a running loop, we need to run in a separate thread
                logger.debug(f"Running {func.__name__} in thread executor to avoid loop conflict")
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_async_in_new_loop, func, *args, **kwargs)
                    return future.result()
                    
            except RuntimeError:
                # No running loop, safe to create our own
                logger.debug(f"Running {func.__name__} in new event loop")
                return asyncio.run(func(*args, **kwargs))
        
        return wrapper
    return decorator


def _run_async_in_new_loop(coro_func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs) -> T:
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
        loop.close()


async def ensure_async_pool_initialization():
    """
    Ensure database connection pools are initialized in the correct event loop context.
    
    This function should be called at the start of async operations to ensure
    connection pools are bound to the current event loop.
    """
    try:
        # Import here to avoid circular imports
        from app.database.connection import ConnectionPoolManager
        
        # Force pool manager to check and rebind to current loop
        ConnectionPoolManager._ensure_loop_bound()
        logger.debug("Database connection pools bound to current event loop")
        
    except Exception as e:
        logger.warning(f"Failed to ensure pool initialization: {e}")


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


class AsyncContextManager:
    """
    Context manager for safely running async operations in Celery workers.
    
    Usage:
        async with AsyncContextManager():
            # Safe to run async operations here
            result = await some_async_function()
    """
    
    def __init__(self):
        self.loop = None
        self.was_running = False
    
    async def __aenter__(self):
        try:
            # Check if there's already a running loop
            existing_loop = asyncio.get_running_loop()
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