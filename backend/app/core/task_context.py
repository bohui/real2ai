"""
Secure Task Context Management for Background Tasks

This module provides secure storage and retrieval of user authentication
context for background tasks, enabling proper RLS enforcement in async operations.
"""

import json
import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from contextlib import asynccontextmanager
from functools import wraps

import redis
from cryptography.fernet import Fernet
import asyncio

from app.core.config import get_settings
from app.core.auth_context import AuthContext

logger = logging.getLogger(__name__)


class SecureTaskContextStore:
    """
    Secure storage for background task authentication context.

    Uses Redis for storage with encryption to protect user tokens
    and automatic TTL for security.
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info(f"Settings loaded: {type(self.settings)}")
        logger.info(f"Environment TASK_ENCRYPTION_KEY exists: {'TASK_ENCRYPTION_KEY' in os.environ}")
        if 'TASK_ENCRYPTION_KEY' in os.environ:
            logger.info(f"TASK_ENCRYPTION_KEY from env: {os.environ['TASK_ENCRYPTION_KEY'][:10]}...")
        self.redis_client = None
        self.cipher = None
        self.default_ttl = timedelta(hours=1)  # Task context expiry
        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection and encryption cipher"""
        if self._initialized:
            return

        try:
            # Initialize Redis connection
            redis_url = getattr(self.settings, "redis_url", "redis://localhost:6379")
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=False)

            # Test Redis connection
            await self._test_redis_connection()

            # Initialize encryption cipher
            encryption_key = getattr(self.settings, "task_encryption_key", None)
            logger.info(f"Settings task_encryption_key: {encryption_key is not None}")
            logger.info(f"Available settings attributes: {[attr for attr in dir(self.settings) if 'task' in attr.lower()]}")
            
            if not encryption_key:
                # Generate a key for development (NOT for production)
                logger.warning("No task_encryption_key found, generating temporary key")
                encryption_key = Fernet.generate_key()

            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()

            self.cipher = Fernet(encryption_key)

            self._initialized = True
            logger.info("SecureTaskContextStore initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SecureTaskContextStore: {e}")
            raise

    async def _test_redis_connection(self):
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            logger.debug("Redis connection test successful")
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            raise

    async def store_context(self, task_id: str, auth_context: Dict[str, Any]) -> str:
        """
        Store encrypted auth context for background task.

        Args:
            task_id: Unique identifier for the task
            auth_context: Authentication context dictionary

        Returns:
            Context key for retrieving the stored context
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Add metadata
            context_with_metadata = {
                **auth_context,
                "stored_at": datetime.now(UTC).isoformat(),
                "task_id": task_id,
                "version": "1.0",
            }

            # Encrypt the context
            context_json = json.dumps(context_with_metadata)
            encrypted_context = self.cipher.encrypt(context_json.encode())

            # Store with TTL
            context_key = f"task_auth:{task_id}"
            ttl_seconds = int(self.default_ttl.total_seconds())
            self.redis_client.setex(
                context_key, ttl_seconds, encrypted_context
            )

            logger.info(f"Stored task context for task: {task_id}, TTL: {ttl_seconds}s, Key: {context_key}")
            return context_key

        except Exception as e:
            logger.error(f"Failed to store task context for {task_id}: {e}")
            raise

    async def retrieve_context(self, context_key: str) -> Dict[str, Any]:
        """
        Retrieve and decrypt auth context.

        Args:
            context_key: Key returned from store_context

        Returns:
            Decrypted authentication context

        Raises:
            ValueError: If context expired or not found
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get encrypted context from Redis
            encrypted_context = self.redis_client.get(context_key)
            if not encrypted_context:
                # Check if key exists but is empty vs completely missing
                exists = self.redis_client.exists(context_key)
                ttl = self.redis_client.ttl(context_key)
                logger.error(f"Context retrieval failed - Key exists: {bool(exists)}, TTL: {ttl}, Key: {context_key}")
                raise ValueError("Task context expired or not found")

            # Decrypt and parse
            decrypted_data = self.cipher.decrypt(encrypted_context)
            context = json.loads(decrypted_data.decode())

            logger.debug(f"Retrieved task context: {context.get('task_id', 'unknown')}")
            return context

        except Exception as e:
            logger.error(f"Failed to retrieve task context {context_key}: {e}")
            raise

    async def cleanup_context(self, context_key: str) -> bool:
        """
        Clean up stored context.

        Args:
            context_key: Key to clean up

        Returns:
            True if cleanup successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = self.redis_client.delete(context_key)
            if result:
                logger.debug(f"Cleaned up task context: {context_key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to cleanup task context {context_key}: {e}")
            return False

    async def extend_context_ttl(
        self, context_key: str, additional_seconds: int = 3600
    ) -> bool:
        """
        Extend TTL for long-running tasks.

        Args:
            context_key: Key to extend TTL for
            additional_seconds: Additional seconds to extend

        Returns:
            True if extension successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = self.redis_client.expire(context_key, additional_seconds)
            if result:
                logger.debug(f"Extended TTL for context: {context_key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to extend TTL for {context_key}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the context store.

        Returns:
            Health status information
        """
        health_status = {
            "service": "SecureTaskContextStore",
            "status": "unknown",
            "initialized": self._initialized,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            if not self._initialized:
                await self.initialize()

            # Test Redis connection
            await self._test_redis_connection()

            # Test encryption/decryption
            test_data = {"test": "data", "timestamp": time.time()}
            encrypted = self.cipher.encrypt(json.dumps(test_data).encode())
            decrypted = json.loads(self.cipher.decrypt(encrypted).decode())

            if decrypted == test_data:
                health_status["status"] = "healthy"
                health_status["redis_connection"] = "ok"
                health_status["encryption"] = "ok"
            else:
                health_status["status"] = "degraded"
                health_status["error"] = "Encryption test failed"

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status


# Global instance
_task_store: Optional[SecureTaskContextStore] = None


async def get_task_store() -> SecureTaskContextStore:
    """Get the global task store instance"""
    global _task_store
    if _task_store is None:
        _task_store = SecureTaskContextStore()
        await _task_store.initialize()
    return _task_store


@asynccontextmanager
async def task_auth_context(context_key: str):
    """
    Context manager for background task authentication.

    Usage:
        async with task_auth_context(context_key):
            # AuthContext is restored with user token
            client = await AuthContext.get_authenticated_client()
            # Perform user-scoped operations
    """
    task_store = await get_task_store()

    try:
        # Restore auth context
        auth_context = await task_store.retrieve_context(context_key)
        AuthContext.restore_task_context(auth_context)

        logger.debug(
            f"Restored task auth context for user: {AuthContext.get_user_id()}"
        )
        yield AuthContext

    finally:
        # Clean up context
        AuthContext.clear_auth_context()
        await task_store.cleanup_context(context_key)
        logger.debug("Cleaned up task auth context")


def user_aware_task(
    func=None, *, recovery_enabled=False, checkpoint_frequency=None, recovery_priority=0
):
    """
    Decorator for background tasks that need user authentication context.
    Enhanced with optional recovery capabilities.

    The decorated function will receive a context_key as its first parameter,
    which is used to restore user authentication context.

    Args:
        recovery_enabled: Enable automatic task recovery on container restart
        checkpoint_frequency: Create checkpoint every N percent progress (if recovery enabled)
        recovery_priority: Recovery priority (0-10, higher = more important)

    Usage:
        @celery_app.task
        @user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=1)
        async def process_document(recovery_ctx, context_key: str, document_id: str, user_id: str):
            # AuthContext is automatically restored
            # recovery_ctx provides checkpointing capabilities if recovery_enabled=True
            client = await AuthContext.get_authenticated_client()
            # Process document with user permissions
    """

    def decorator(func):
        if recovery_enabled:
            # Create recovery-enabled wrapper that handles user context first
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                def async_wrapper(self, *args, **kwargs):
                    # Extract context_key from args (first argument after self)
                    logger.info(f"Recovery async_wrapper called with args: {args}")
                    logger.info(f"Recovery async_wrapper called with kwargs: {kwargs}")
                    if not args:
                        raise TypeError("Missing context_key argument")
                    context_key = args[0]
                    remaining_args = args[1:]
                    logger.info(f"Extracted context_key: {context_key}")
                    logger.info(f"Remaining args: {remaining_args}")
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _recovery_enabled_async_wrapper(
                                context_key,
                                func,
                                recovery_priority,
                                checkpoint_frequency,
                                *remaining_args,
                                **kwargs,
                            )
                        )
                    finally:
                        loop.close()

                return async_wrapper
            else:

                @wraps(func)
                def sync_wrapper(self, *args, **kwargs):
                    # Extract context_key from args (first argument after self)
                    if not args:
                        raise TypeError("Missing context_key argument")
                    context_key = args[0]
                    remaining_args = args[1:]
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _recovery_enabled_sync_wrapper(
                                context_key,
                                func,
                                recovery_priority,
                                checkpoint_frequency,
                                *remaining_args,
                                **kwargs,
                            )
                        )
                    finally:
                        loop.close()

                return sync_wrapper

        else:
            # Original user_aware_task behavior without recovery
            if asyncio.iscoroutinefunction(func):
                # Handle async functions
                @wraps(func)
                def async_wrapper(self, *args, **kwargs):
                    # Extract context_key from args (first argument after self)
                    if not args:
                        raise TypeError("Missing context_key argument")
                    context_key = args[0]
                    remaining_args = args[1:]
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _async_wrapper_async(context_key, func, *remaining_args, **kwargs)
                        )
                    finally:
                        loop.close()

                return async_wrapper
            else:
                # Handle sync functions
                @wraps(func)
                def sync_wrapper(self, *args, **kwargs):
                    # Extract context_key from args (first argument after self)
                    if not args:
                        raise TypeError("Missing context_key argument")
                    context_key = args[0]
                    remaining_args = args[1:]
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _async_wrapper_sync(context_key, func, *remaining_args, **kwargs)
                        )
                    finally:
                        loop.close()

                return sync_wrapper

    # Handle both @user_aware_task and @user_aware_task(...) syntax
    if func is None:
        return decorator
    else:
        return decorator(func)


async def _async_wrapper_async(context_key: str, func, *args, **kwargs):
    """Internal async wrapper for async functions."""
    async with task_auth_context(context_key):
        return await func(*args, **kwargs)


async def _async_wrapper_sync(context_key: str, func, *args, **kwargs):
    """Internal async wrapper for sync functions."""
    async with task_auth_context(context_key):
        return func(*args, **kwargs)


async def _recovery_enabled_async_wrapper(
    context_key: str,
    func,
    recovery_priority: int,
    checkpoint_frequency: int,
    *args,
    **kwargs,
):
    """Recovery-enabled wrapper for async functions."""
    # First restore user context
    async with task_auth_context(context_key):
        # Now create recovery context with user_id available
        from app.core.task_recovery import create_recovery_context

        # Get user_id from restored context
        user_id = AuthContext.get_user_id()

        # Create recovery context
        recovery_ctx = await create_recovery_context(
            user_id=user_id,
            recovery_priority=recovery_priority,
            checkpoint_frequency=checkpoint_frequency,
        )

        # Execute function with recovery context as first parameter
        return await func(recovery_ctx, *args, **kwargs)


async def _recovery_enabled_sync_wrapper(
    context_key: str,
    func,
    recovery_priority: int,
    checkpoint_frequency: int,
    *args,
    **kwargs,
):
    """Recovery-enabled wrapper for sync functions."""
    # First restore user context
    async with task_auth_context(context_key):
        # Now create recovery context with user_id available
        from app.core.task_recovery import create_recovery_context

        # Get user_id from restored context
        user_id = AuthContext.get_user_id()

        # Create recovery context
        recovery_ctx = await create_recovery_context(
            user_id=user_id,
            recovery_priority=recovery_priority,
            checkpoint_frequency=checkpoint_frequency,
        )

        # Execute function with recovery context as first parameter
        return func(recovery_ctx, *args, **kwargs)


class TaskContextManager:
    """
    High-level manager for task context operations.

    Provides convenience methods for common task context patterns.
    """

    def __init__(self):
        self.store = None

    async def initialize(self):
        """Initialize the context manager"""
        self.store = await get_task_store()

    async def create_task_context(self, task_id: str) -> str:
        """
        Create task context from current auth context.

        Args:
            task_id: Unique task identifier

        Returns:
            Context key for the stored context
        """
        if not self.store:
            await self.initialize()

        # Get current auth context
        task_context = AuthContext.create_task_context()

        if not task_context.get("user_token"):
            raise ValueError("No user token in current auth context")

        # Store context
        context_key = await self.store.store_context(task_id, task_context)

        logger.info(
            f"Created task context for task {task_id}, user: {task_context.get('user_id')}"
        )
        return context_key

    async def launch_user_task(self, celery_task, task_id: str, *args, **kwargs):
        """
        Launch a user-aware Celery task with auth context.

        Args:
            celery_task: Celery task function
            task_id: Unique task identifier
            *args, **kwargs: Task arguments

        Returns:
            Celery AsyncResult
        """
        # Create context for the task
        context_key = await self.create_task_context(task_id)

        # Launch task with context key as first parameter
        # The task wrapper expects: context_key, *task_args
        logger.info(f"Launching task with context_key: {context_key}")
        logger.info(f"Task args: {args}")
        logger.info(f"Task kwargs: {kwargs}")
        return celery_task.delay(context_key, *args, **kwargs)


# Global context manager instance
task_manager = TaskContextManager()
