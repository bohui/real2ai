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
from app.services.backend_token_service import BackendTokenService

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
        logger.info(
            f"Environment TASK_ENCRYPTION_KEY exists: {'TASK_ENCRYPTION_KEY' in os.environ}"
        )
        if "TASK_ENCRYPTION_KEY" in os.environ:
            logger.info(
                f"TASK_ENCRYPTION_KEY from env: {os.environ['TASK_ENCRYPTION_KEY'][:10]}..."
            )
        self.redis_client = None
        self.cipher = None
        self.default_ttl = timedelta(hours=4)  # Extended TTL for long-running tasks
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
            logger.info(
                f"Available settings attributes: {[attr for attr in dir(self.settings) if 'task' in attr.lower()]}"
            )

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
            self.redis_client.setex(context_key, ttl_seconds, encrypted_context)

            logger.info(
                f"Stored task context for task: {task_id}, TTL: {ttl_seconds}s, Key: {context_key}"
            )
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
                logger.error(
                    f"Context retrieval failed - Key exists: {bool(exists)}, TTL: {ttl}, Key: {context_key}"
                )
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
        self, context_key: str, additional_seconds: int = 14400
    ) -> bool:
        """
        Extend TTL for long-running tasks.

        Args:
            context_key: Key to extend TTL for
            additional_seconds: Additional seconds to extend (default 4 hours)

        Returns:
            True if extension successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = self.redis_client.expire(context_key, additional_seconds)
            if result:
                logger.info(
                    f"Extended TTL for context: {context_key} to {additional_seconds}s"
                )
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to extend TTL for {context_key}: {e}")
            return False

    async def refresh_context_ttl(self, context_key: str) -> bool:
        """
        Refresh TTL to the default duration for active tasks.

        Args:
            context_key: Key to refresh TTL for

        Returns:
            True if refresh successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            ttl_seconds = int(self.default_ttl.total_seconds())
            result = self.redis_client.expire(context_key, ttl_seconds)
            if result:
                logger.info(
                    f"Refreshed TTL for context: {context_key} to {ttl_seconds}s"
                )
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to refresh TTL for {context_key}: {e}")
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
async def task_auth_context(context_key: str, extend_ttl: bool = True):
    """
    Context manager for background task authentication.

    Args:
        context_key: Task context key for authentication
        extend_ttl: Whether to extend TTL at start for long-running tasks

    Usage:
        async with task_auth_context(context_key):
            # AuthContext is restored with user token
            # Use isolated client to prevent JWT token race conditions in concurrent tasks
            client = await AuthContext.get_authenticated_client(isolated=True)
            # Perform user-scoped operations
    """
    task_store = await get_task_store()

    success: bool = False
    try:
        # Extend TTL for long-running tasks before retrieval
        if extend_ttl:
            await task_store.extend_context_ttl(context_key)

        # Restore auth context
        auth_context = await task_store.retrieve_context(context_key)
        AuthContext.restore_task_context(auth_context)

        logger.debug(
            f"Restored task auth context for user: {AuthContext.get_user_id()}"
        )
        yield AuthContext
        # Mark success only after the context manager body finishes without exception
        success = True

    finally:
        # Clean up context
        AuthContext.clear_auth_context()
        if success:
            # Only delete stored context when the task completed successfully
            await task_store.cleanup_context(context_key)
            logger.debug("Cleaned up task auth context")
        else:
            # Preserve context for retries; it will expire via TTL if not used
            logger.debug(
                "Preserving task auth context for retry due to task error; cleanup deferred"
            )


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
            # Use isolated client to prevent JWT token race conditions in concurrent tasks
            client = await AuthContext.get_authenticated_client(isolated=True)
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

                    # Reuse a persistent loop per worker to avoid closing an event loop
                    # that asyncpg pools may still reference. Create once and keep it.
                    loop = getattr(self, "_persistent_loop", None)
                    if loop is None or loop.is_closed():
                        loop = asyncio.new_event_loop()
                        setattr(self, "_persistent_loop", loop)
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
                        # Do not close the persistent loop; keep it for future tasks
                        pass

                return async_wrapper
            else:

                @wraps(func)
                def sync_wrapper(self, *args, **kwargs):
                    # Extract context_key from args (first argument after self)
                    if not args:
                        raise TypeError("Missing context_key argument")
                    context_key = args[0]
                    remaining_args = args[1:]

                    loop = getattr(self, "_persistent_loop", None)
                    if loop is None or loop.is_closed():
                        loop = asyncio.new_event_loop()
                        setattr(self, "_persistent_loop", loop)
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
                        pass

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

                    loop = getattr(self, "_persistent_loop", None)
                    if loop is None or loop.is_closed():
                        loop = asyncio.new_event_loop()
                        setattr(self, "_persistent_loop", loop)
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _async_wrapper_async(
                                context_key, func, *remaining_args, **kwargs
                            )
                        )
                    finally:
                        pass

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

                    loop = getattr(self, "_persistent_loop", None)
                    if loop is None or loop.is_closed():
                        loop = asyncio.new_event_loop()
                        setattr(self, "_persistent_loop", loop)
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            _async_wrapper_sync(
                                context_key, func, *remaining_args, **kwargs
                            )
                        )
                    finally:
                        pass

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

        # Create recovery context with context_key for TTL refresh
        recovery_ctx = await create_recovery_context(
            user_id=user_id,
            recovery_priority=recovery_priority,
            checkpoint_frequency=checkpoint_frequency,
            context_key=context_key,
        )

        # Execute function inside RecoveryContext so task_registry transitions
        # from queued -> started and completes/records failures appropriately
        async with recovery_ctx:
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

        # Create recovery context with context_key for TTL refresh
        recovery_ctx = await create_recovery_context(
            user_id=user_id,
            recovery_priority=recovery_priority,
            checkpoint_frequency=checkpoint_frequency,
            context_key=context_key,
        )

        # Execute function inside RecoveryContext so task_registry transitions
        # from queued -> started and completes/records failures appropriately
        async with recovery_ctx:
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
            Context key for task execution
        """
        if not self.store:
            await self.initialize()

        # Get current auth context
        user_token = AuthContext.get_user_token()
        user_id = AuthContext.get_user_id()
        user_email = AuthContext.get_user_email()
        auth_metadata = AuthContext.get_auth_metadata()

        if not user_token or not user_id:
            raise ValueError("No authenticated user context available")

        # Enhanced token validation and logging
        logger.info(
            f"Creating task context for task {task_id}",
            extra={
                "task_id": task_id,
                "user_id": user_id,
                "user_email": user_email,
                "token_length": len(user_token),
                "token_type": (
                    "backend"
                    if BackendTokenService.is_backend_token(user_token)
                    else "supabase"
                ),
                "auth_metadata": auth_metadata,
            },
        )

        # Validate token expiration before storing
        try:
            if BackendTokenService.is_backend_token(user_token):
                claims = BackendTokenService.verify_backend_token(user_token)
                backend_exp = claims.get("exp")
                supa_exp = claims.get("supa_exp")
                now = int(time.time())

                if backend_exp:
                    time_to_backend_expiry = backend_exp - now
                    logger.info(
                        f"Backend token expiry analysis for task {task_id}",
                        extra={
                            "task_id": task_id,
                            "user_id": user_id,
                            "backend_exp": backend_exp,
                            "time_to_backend_expiry_seconds": time_to_backend_expiry,
                            "time_to_backend_expiry_minutes": (
                                time_to_backend_expiry / 60
                                if time_to_backend_expiry > 0
                                else 0
                            ),
                            "is_expired": time_to_backend_expiry <= 0,
                        },
                    )

                    if supa_exp:
                        time_to_supabase_expiry = supa_exp - now
                        buffer_time = supa_exp - backend_exp
                        logger.info(
                            f"Token coordination analysis for task {task_id}",
                            extra={
                                "task_id": task_id,
                                "user_id": user_id,
                                "supabase_exp": supa_exp,
                                "time_to_supabase_expiry_seconds": time_to_supabase_expiry,
                                "time_to_supabase_expiry_minutes": (
                                    time_to_supabase_expiry / 60
                                    if time_to_supabase_expiry > 0
                                    else 0
                                ),
                                "buffer_time_seconds": buffer_time,
                                "buffer_time_minutes": (
                                    buffer_time / 60 if buffer_time > 0 else 0
                                ),
                                "is_supabase_expired": time_to_supabase_expiry <= 0,
                            },
                        )

                        # Warn if buffer is too small for long-running tasks
                        if buffer_time < 300:  # Less than 5 minutes
                            logger.warning(
                                f"Small token buffer for task {task_id} - may cause expiration issues",
                                extra={
                                    "task_id": task_id,
                                    "user_id": user_id,
                                    "buffer_time_seconds": buffer_time,
                                    "recommendation": "Consider increasing backend_token_ttl_buffer_minutes or implementing proactive refresh",
                                },
                            )

                    # Warn if backend token expires soon
                    if time_to_backend_expiry <= 600:  # 10 minutes or less
                        logger.warning(
                            f"Backend token expires soon for task {task_id}",
                            extra={
                                "task_id": task_id,
                                "user_id": user_id,
                                "time_to_backend_expiry_seconds": time_to_backend_expiry,
                                "time_to_backend_expiry_minutes": (
                                    time_to_backend_expiry / 60
                                    if time_to_backend_expiry > 0
                                    else 0
                                ),
                                "recommendation": "Task may fail if execution takes longer than token lifetime",
                            },
                        )

                        # Check if we should proactively refresh
                        if time_to_backend_expiry <= 300:  # 5 minutes or less
                            logger.warning(
                                f"Backend token expires very soon for task {task_id} - attempting proactive refresh",
                                extra={
                                    "task_id": task_id,
                                    "user_id": user_id,
                                    "time_to_backend_expiry_seconds": time_to_backend_expiry,
                                },
                            )

                            try:
                                # Attempt to refresh the token before storing context
                                refreshed_token = await BackendTokenService.refresh_coordinated_tokens(
                                    user_token
                                )
                                if refreshed_token:
                                    user_token = refreshed_token
                                    logger.info(
                                        f"Successfully refreshed backend token for task {task_id}",
                                        extra={
                                            "task_id": task_id,
                                            "user_id": user_id,
                                            "old_token_length": len(user_token),
                                            "new_token_length": len(refreshed_token),
                                        },
                                    )
                                else:
                                    logger.warning(
                                        f"Failed to refresh backend token for task {task_id}",
                                        extra={
                                            "task_id": task_id,
                                            "user_id": user_id,
                                        },
                                    )
                            except Exception as refresh_error:
                                logger.error(
                                    f"Error during proactive token refresh for task {task_id}",
                                    extra={
                                        "task_id": task_id,
                                        "user_id": user_id,
                                        "error": str(refresh_error),
                                    },
                                    exc_info=True,
                                )
            else:
                # Supabase token - check expiration
                try:
                    import jwt

                    claims = jwt.decode(user_token, options={"verify_signature": False})
                    exp = claims.get("exp")
                    if exp:
                        now = int(time.time())
                        time_to_expiry = exp - now
                        logger.info(
                            f"Supabase token expiry analysis for task {task_id}",
                            extra={
                                "task_id": task_id,
                                "user_id": user_id,
                                "exp": exp,
                                "time_to_expiry_seconds": time_to_expiry,
                                "time_to_expiry_minutes": (
                                    time_to_expiry / 60 if time_to_expiry > 0 else 0
                                ),
                                "is_expired": time_to_expiry <= 0,
                            },
                        )

                        if time_to_expiry <= 600:  # 10 minutes or less
                            logger.warning(
                                f"Supabase token expires soon for task {task_id}",
                                extra={
                                    "task_id": task_id,
                                    "user_id": user_id,
                                    "time_to_expiry_seconds": time_to_expiry,
                                    "time_to_expiry_minutes": (
                                        time_to_expiry / 60 if time_to_expiry > 0 else 0
                                    ),
                                    "recommendation": "Consider using backend tokens for better coordination",
                                },
                            )
                except Exception as token_analysis_error:
                    logger.warning(
                        f"Could not analyze Supabase token expiry for task {task_id}",
                        extra={
                            "task_id": task_id,
                            "user_id": user_id,
                            "error": str(token_analysis_error),
                        },
                    )

        except Exception as validation_error:
            logger.error(
                f"Error validating token for task {task_id}",
                extra={
                    "task_id": task_id,
                    "user_id": user_id,
                    "error": str(validation_error),
                },
                exc_info=True,
            )
            # Continue with original token - let the task handle validation errors

        # Create task context
        task_context = {
            "user_id": user_id,
            "user_email": user_email,
            "user_token": user_token,
            "auth_metadata": auth_metadata,
            "refresh_token": AuthContext.get_refresh_token(),
            "created_at": datetime.now(UTC).isoformat(),
        }

        # If the token is a backend-issued token, exchange it for a Supabase access token
        try:
            if BackendTokenService.is_backend_token(user_token):
                exchanged = await BackendTokenService.ensure_supabase_access_token(
                    user_token
                )
                if exchanged:
                    # Replace token in context with Supabase access token
                    task_context["user_token"] = exchanged
                    # Attempt to include refresh token when available
                    mapping = await BackendTokenService.get_mapping(user_token) or {}
                    if mapping.get("supabase_refresh_token"):
                        task_context["refresh_token"] = mapping[
                            "supabase_refresh_token"
                        ]
                    logger.info(
                        "Exchanged backend token for Supabase token in task context"
                    )
                else:
                    logger.warning(
                        "Failed to exchange backend token for Supabase token before storing task context"
                    )
        except Exception as exchange_error:
            logger.warning(
                f"Token exchange error while preparing task context: {exchange_error}"
            )

        # Store context
        context_key = await self.store.store_context(task_id, task_context)

        logger.info(
            f"Created task context for task {task_id}, user: {task_context.get('user_id')}"
        )
        return context_key

    async def refresh_task_ttl(self, context_key: str) -> bool:
        """
        Refresh TTL for an active task - can be called during task execution.

        Args:
            context_key: Context key to refresh

        Returns:
            True if refresh successful
        """
        if not self.store:
            await self.initialize()

        return await self.store.refresh_context_ttl(context_key)

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


async def refresh_current_task_ttl(context_key: str) -> bool:
    """
    Utility function for tasks to refresh their context TTL during execution.
    This prevents context expiration for long-running tasks.

    Args:
        context_key: The task context key

    Returns:
        True if TTL refresh was successful
    """
    try:
        task_store = await get_task_store()
        result = await task_store.refresh_context_ttl(context_key)
        if result:
            logger.info(f"Successfully refreshed TTL for task context: {context_key}")
        else:
            logger.warning(f"Failed to refresh TTL for task context: {context_key}")
        return result
    except Exception as e:
        logger.error(f"Error refreshing TTL for task context {context_key}: {e}")
        return False


async def check_token_health(context_key: str) -> Dict[str, Any]:
    """
    Check the health of the current authentication token.
    This is useful for long-running tasks to monitor token status.

    Args:
        context_key: The task context key

    Returns:
        Dictionary containing token health information
    """
    try:
        from app.services.backend_token_service import BackendTokenService
        from app.core.auth_context import AuthContext

        current_token = AuthContext.get_user_token()
        user_id = AuthContext.get_user_id()

        if not current_token:
            return {
                "status": "no_token",
                "user_id": user_id,
                "message": "No authentication token available",
            }

        health_info = {
            "status": "unknown",
            "user_id": user_id,
            "token_length": len(current_token),
            "token_type": (
                "backend"
                if BackendTokenService.is_backend_token(current_token)
                else "supabase"
            ),
            "expiry_info": {},
            "recommendations": [],
        }

        try:
            if BackendTokenService.is_backend_token(current_token):
                # Analyze backend token
                claims = BackendTokenService.verify_backend_token(current_token)
                backend_exp = claims.get("exp")
                supa_exp = claims.get("supa_exp")
                now = int(time.time())

                if backend_exp:
                    time_to_backend_expiry = backend_exp - now
                    time_to_backend_expiry_minutes = (
                        time_to_backend_expiry / 60 if time_to_backend_expiry > 0 else 0
                    )

                    health_info["expiry_info"] = {
                        "backend_exp": backend_exp,
                        "time_to_backend_expiry_seconds": time_to_backend_expiry,
                        "time_to_backend_expiry_minutes": time_to_backend_expiry_minutes,
                        "is_expired": time_to_backend_expiry <= 0,
                    }

                    if time_to_backend_expiry <= 0:
                        health_info["status"] = "expired"
                        health_info["message"] = "Backend token is expired"
                        health_info["recommendations"].append(
                            "Token needs immediate refresh"
                        )
                    elif time_to_backend_expiry <= 300:  # 5 minutes
                        health_info["status"] = "critical"
                        health_info["message"] = "Backend token expires very soon"
                        health_info["recommendations"].append(
                            "Refresh token immediately"
                        )
                    elif time_to_backend_expiry <= 900:  # 15 minutes
                        health_info["status"] = "warning"
                        health_info["message"] = "Backend token expires soon"
                        health_info["recommendations"].append(
                            "Consider refreshing token"
                        )
                    else:
                        health_info["status"] = "healthy"
                        health_info["message"] = "Backend token is healthy"

                    if supa_exp:
                        time_to_supabase_expiry = supa_exp - now
                        buffer_time = supa_exp - backend_exp
                        buffer_time_minutes = buffer_time / 60 if buffer_time > 0 else 0

                        health_info["expiry_info"].update(
                            {
                                "supabase_exp": supa_exp,
                                "time_to_supabase_expiry_seconds": time_to_supabase_expiry,
                                "time_to_supabase_expiry_minutes": (
                                    time_to_supabase_expiry / 60
                                    if time_to_supabase_expiry > 0
                                    else 0
                                ),
                                "buffer_time_seconds": buffer_time,
                                "buffer_time_minutes": buffer_time_minutes,
                                "is_supabase_expired": time_to_supabase_expiry <= 0,
                            }
                        )

                        if buffer_time < 600:  # Less than 10 minutes
                            health_info["recommendations"].append(
                                "Token buffer is small - consider increasing backend_token_ttl_buffer_minutes"
                            )

                        if time_to_supabase_expiry <= 0:
                            health_info["status"] = "critical"
                            health_info["message"] = (
                                "Both backend and Supabase tokens are expired"
                            )
                            health_info["recommendations"].append(
                                "User needs to re-authenticate"
                            )

                # Check if refresh is needed
                if health_info["status"] in ["critical", "expired"]:
                    try:
                        refreshed_token = (
                            await BackendTokenService.refresh_coordinated_tokens(
                                current_token
                            )
                        )
                        if refreshed_token:
                            health_info["refresh_attempted"] = True
                            health_info["refresh_successful"] = True
                            health_info["new_token_length"] = len(refreshed_token)
                            health_info["message"] = "Token refreshed successfully"

                            # Update auth context with new token
                            AuthContext.set_auth_context(
                                token=refreshed_token,
                                user_id=user_id,
                                user_email=AuthContext.get_user_email(),
                                metadata=AuthContext.get_auth_metadata(),
                                refresh_token=AuthContext.get_refresh_token(),
                            )
                        else:
                            health_info["refresh_attempted"] = True
                            health_info["refresh_successful"] = False
                            health_info["message"] = "Token refresh failed"
                    except Exception as refresh_error:
                        health_info["refresh_attempted"] = True
                        health_info["refresh_successful"] = False
                        health_info["refresh_error"] = str(refresh_error)
                        health_info["message"] = f"Token refresh error: {refresh_error}"

            else:
                # Analyze Supabase token
                try:
                    import jwt

                    claims = jwt.decode(
                        current_token, options={"verify_signature": False}
                    )
                    exp = claims.get("exp")
                    if exp:
                        now = int(time.time())
                        time_to_expiry = exp - now
                        time_to_expiry_minutes = (
                            time_to_expiry / 60 if time_to_expiry > 0 else 0
                        )

                        health_info["expiry_info"] = {
                            "exp": exp,
                            "time_to_expiry_seconds": time_to_expiry,
                            "time_to_expiry_minutes": time_to_expiry_minutes,
                            "is_expired": time_to_expiry <= 0,
                        }

                        if time_to_expiry <= 0:
                            health_info["status"] = "expired"
                            health_info["message"] = "Supabase token is expired"
                            health_info["recommendations"].append(
                                "User needs to re-authenticate"
                            )
                        elif time_to_expiry <= 600:  # 10 minutes
                            health_info["status"] = "warning"
                            health_info["message"] = "Supabase token expires soon"
                            health_info["recommendations"].append(
                                "Consider using backend tokens for better coordination"
                            )
                        else:
                            health_info["status"] = "healthy"
                            health_info["message"] = "Supabase token is healthy"

                except Exception as token_analysis_error:
                    health_info["status"] = "error"
                    health_info["message"] = (
                        f"Could not analyze token: {token_analysis_error}"
                    )
                    health_info["token_analysis_error"] = str(token_analysis_error)

        except Exception as analysis_error:
            health_info["status"] = "error"
            health_info["message"] = f"Error analyzing token: {analysis_error}"
            health_info["analysis_error"] = str(analysis_error)

        # Log health status
        if health_info["status"] in ["critical", "expired"]:
            logger.error(
                f"Token health check critical for context {context_key}",
                extra={
                    "context_key": context_key,
                    "user_id": user_id,
                    "health_info": health_info,
                },
            )
        elif health_info["status"] == "warning":
            logger.warning(
                f"Token health check warning for context {context_key}",
                extra={
                    "context_key": context_key,
                    "user_id": user_id,
                    "health_info": health_info,
                },
            )
        else:
            logger.debug(
                f"Token health check for context {context_key}",
                extra={
                    "context_key": context_key,
                    "user_id": user_id,
                    "health_info": health_info,
                },
            )

        return health_info

    except Exception as e:
        logger.error(f"Error checking token health for context {context_key}: {e}")
        return {
            "status": "error",
            "message": f"Error checking token health: {e}",
            "error": str(e),
        }
