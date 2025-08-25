"""
Task Recovery System - Core Components
Provides automatic task recovery, checkpointing, and state management for Celery tasks.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from celery import current_task

from app.core.auth_context import AuthContext
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task state enumeration matching database enum"""

    QUEUED = "queued"
    STARTED = "started"
    PROCESSING = "processing"
    CHECKPOINT = "checkpoint"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERING = "recovering"
    PARTIAL = "partial"
    ORPHANED = "orphaned"


class RecoveryMethod(Enum):
    """Recovery method enumeration"""

    RESUME_CHECKPOINT = "resume_checkpoint"
    RESTART_CLEAN = "restart_clean"
    VALIDATE_ONLY = "validate_only"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class CheckpointData:
    """Checkpoint data structure"""

    checkpoint_name: str
    progress_percent: int
    step_description: str
    recoverable_data: Dict[str, Any]
    database_state: Dict[str, Any] = None
    file_state: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_name": self.checkpoint_name,
            "progress_percent": self.progress_percent,
            "step_description": self.step_description,
            "recoverable_data": self.recoverable_data,
            "database_state": self.database_state or {},
            "file_state": self.file_state or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointData":
        """Create CheckpointData from dictionary"""
        return cls(
            checkpoint_name=data["checkpoint_name"],
            progress_percent=data["progress_percent"],
            step_description=data["step_description"],
            recoverable_data=data["recoverable_data"],
            database_state=data.get("database_state", {}),
            file_state=data.get("file_state", {}),
        )


@dataclass
class RecoverableTask:
    """Recoverable task data structure"""

    registry_id: str
    task_id: str
    task_name: str
    user_id: str
    current_state: TaskState
    last_heartbeat: datetime
    recovery_priority: int
    progress_percent: int
    current_step: str
    task_args: tuple
    task_kwargs: Dict[str, Any]
    context_key: str = None


class TaskRegistry:
    """Manages task registry operations"""

    def __init__(self):
        self.settings = get_settings()

    async def create_entry(
        self,
        task_id: str,
        task_name: str,
        user_id: str,
        task_args: tuple = (),
        task_kwargs: Dict[str, Any] = None,
        context_key: str = None,
        recovery_priority: int = 0,
        auto_recovery_enabled: bool = True,
    ) -> str:
        """Create task registry entry"""

        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        client = await AuthContext.get_authenticated_client(isolated=True)

        result = await client.execute_rpc(
            "upsert_task_registry",
            {
                "p_task_id": task_id,
                "p_task_name": task_name,
                "p_user_id": user_id,
                "p_task_args": json.dumps(task_args),
                "p_task_kwargs": json.dumps(task_kwargs or {}),
                "p_context_key": context_key,
                "p_recovery_priority": recovery_priority,
                "p_auto_recovery_enabled": auto_recovery_enabled,
            },
        )

        # Robustly parse RPC return (string UUID, dict, or list of dicts)
        registry_id = None
        if result:
            try:
                if isinstance(result, str):
                    registry_id = result
                elif isinstance(result, dict):
                    registry_id = result.get("upsert_task_registry") or result.get("id")
                elif isinstance(result, list) and len(result) > 0:
                    first_item = result[0]
                    if isinstance(first_item, dict):
                        registry_id = first_item.get(
                            "upsert_task_registry"
                        ) or first_item.get("id")
                    elif isinstance(first_item, str):
                        registry_id = first_item
            except Exception as parse_error:
                logger.debug(
                    f"Could not parse upsert_task_registry RPC result: {parse_error}"
                )
        if not registry_id:
            raise Exception("Failed to create task registry entry")

        logger.info(f"Created task registry entry: {registry_id} for task {task_id}")
        return registry_id

    async def update_state(
        self,
        task_id: str,
        new_state: TaskState,
        progress_percent: int = None,
        current_step: str = None,
        checkpoint_data: Dict[str, Any] = None,
        error_details: Dict[str, Any] = None,
        result_data: Dict[str, Any] = None,
    ) -> bool:
        """Update task registry state"""

        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        client = await AuthContext.get_authenticated_client(isolated=True)

        result = await client.execute_rpc(
            "update_task_registry_state",
            {
                "p_task_id": task_id,
                "p_new_state": new_state.value,
                "p_progress_percent": progress_percent,
                "p_current_step": current_step,
                "p_checkpoint_data": (
                    json.dumps(checkpoint_data) if checkpoint_data else None
                ),
                "p_error_details": json.dumps(error_details) if error_details else None,
                "p_result_data": json.dumps(result_data) if result_data else None,
            },
        )

        # Robustly parse boolean result from RPC
        success = False
        if result is not None:
            if isinstance(result, bool):
                success = result
            elif isinstance(result, dict):
                success = bool(result.get("update_task_registry_state", False))
            elif isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, bool):
                    success = first_item
                elif isinstance(first_item, dict):
                    success = bool(first_item.get("update_task_registry_state", False))

        if success:
            logger.debug(f"Updated task {task_id} state to {new_state.value}")
        else:
            logger.error(f"Failed to update task {task_id} state")

        return success

    async def create_checkpoint(self, task_id: str, checkpoint: CheckpointData) -> str:
        """Create task checkpoint"""

        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        client = await AuthContext.get_authenticated_client(isolated=True)

        result = await client.execute_rpc(
            "create_task_checkpoint",
            {
                "p_task_id": task_id,
                "p_checkpoint_name": checkpoint.checkpoint_name,
                "p_progress_percent": checkpoint.progress_percent,
                "p_step_description": checkpoint.step_description,
                "p_recoverable_data": json.dumps(checkpoint.recoverable_data),
                "p_database_state": json.dumps(checkpoint.database_state or {}),
                "p_file_state": json.dumps(checkpoint.file_state or {}),
            },
        )

        # Extract UUID regardless of return shape
        checkpoint_id = None
        if result:
            if isinstance(result, str):
                checkpoint_id = result
            elif isinstance(result, dict):
                checkpoint_id = result.get("create_task_checkpoint") or result.get("id")
            elif isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict):
                    checkpoint_id = first_item.get(
                        "create_task_checkpoint"
                    ) or first_item.get("id")
                elif isinstance(first_item, str):
                    checkpoint_id = first_item
        if not checkpoint_id:
            raise Exception("Failed to create checkpoint")

        logger.info(
            f"Created checkpoint {checkpoint.checkpoint_name} for task {task_id}"
        )
        return checkpoint_id

    async def get_latest_checkpoint(self, task_id: str) -> Optional[CheckpointData]:
        """Get latest checkpoint for task"""

        # Use isolated client to prevent JWT token race conditions in concurrent tasks
        client = await AuthContext.get_authenticated_client(isolated=True)

        result = await client.execute_rpc(
            "get_latest_checkpoint", {"p_task_id": task_id}
        )

        if not result:
            return None

        row = result[0]
        return CheckpointData(
            checkpoint_name=row["checkpoint_name"],
            progress_percent=row["progress_percent"],
            step_description=row["step_description"],
            recoverable_data=(
                json.loads(row["recoverable_data"]) if row["recoverable_data"] else {}
            ),
            database_state=(
                json.loads(row["database_state"]) if row["database_state"] else {}
            ),
            file_state=json.loads(row["file_state"]) if row["file_state"] else {},
        )


class RecoveryContext:
    """Context manager for task recovery operations"""

    def __init__(self, task_id: str, registry: TaskRegistry, context_key: str = None):
        self.task_id = task_id
        self.registry = registry
        self.context_key = context_key
        self.checkpoints_created = []
        self._started = False

    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._finish(exc_type, exc_val, exc_tb)

    async def _start(self):
        """Start the recovery context"""
        if not self._started:
            await self.registry.update_state(self.task_id, TaskState.STARTED)
            self._started = True

    async def _finish(self, exc_type, exc_val, exc_tb):
        """Finish the recovery context"""
        if exc_type is None:
            # Task completed successfully
            await self.registry.update_state(
                self.task_id, TaskState.COMPLETED, progress_percent=100
            )
        else:
            # Task failed
            error_details = {
                "error_type": exc_type.__name__ if exc_type else "Unknown",
                "error_message": str(exc_val) if exc_val else "Unknown error",
                "traceback": traceback.format_exc(),
                "recoverable": self._is_recoverable_error(exc_type, exc_val),
            }

            new_state = (
                TaskState.PARTIAL if error_details["recoverable"] else TaskState.FAILED
            )
            await self.registry.update_state(
                self.task_id, new_state, error_details=error_details
            )

    async def ensure_started(self):
        """Ensure the recovery context is started (for non-context-manager usage)"""
        if not self._started:
            await self._start()

    async def create_checkpoint(self, checkpoint: CheckpointData) -> str:
        """Create checkpoint within recovery context"""
        await self.ensure_started()
        checkpoint_id = await self.registry.create_checkpoint(self.task_id, checkpoint)
        self.checkpoints_created.append(checkpoint_id)
        return checkpoint_id

    async def update_progress(
        self, progress_percent: int, current_step: str, step_description: str = None
    ):
        """Update task progress"""
        await self.ensure_started()
        await self.registry.update_state(
            self.task_id,
            TaskState.PROCESSING,
            progress_percent=progress_percent,
            current_step=current_step,
        )

        # Log progress for monitoring
        logger.info(
            f"Task {self.task_id} progress: {progress_percent}% - {current_step}"
        )

        # Auto-refresh TTL at key progress points to prevent context expiration
        if self.context_key and progress_percent % 25 == 0:  # Refresh every 25%
            await self.refresh_context_ttl()

    async def refresh_context_ttl(self) -> bool:
        """
        Refresh the task context TTL to prevent expiration during long-running tasks.

        Returns:
            True if TTL refresh was successful
        """
        if not self.context_key:
            logger.warning(
                f"Task {self.task_id}: No context_key available for TTL refresh"
            )
            return False

        try:
            # Import here to avoid circular imports
            from app.core.task_context import refresh_current_task_ttl

            result = await refresh_current_task_ttl(self.context_key)
            if result:
                logger.info(f"Task {self.task_id}: Successfully refreshed context TTL")
            else:
                logger.warning(f"Task {self.task_id}: Failed to refresh context TTL")
            return result
        except Exception as e:
            logger.error(f"Task {self.task_id}: Error refreshing context TTL: {e}")
            return False

    def _is_recoverable_error(self, exc_type, exc_val) -> bool:
        """Determine if error is recoverable"""
        if not exc_type:
            return False

        recoverable_errors = [
            "ConnectionError",
            "TimeoutError",
            "TemporaryFailure",
            "RetryableError",
        ]

        return exc_type.__name__ in recoverable_errors


async def create_recovery_context(
    user_id: str,
    recovery_priority: int = 0,
    checkpoint_frequency: int = None,
    context_key: str = None,
) -> "RecoveryContext":
    """
    Create a recovery context for a task.
    This function is called from user_aware_task after auth context is restored.
    """
    try:
        if not current_task:
            # If not in a Celery task, return a no-op context
            logger.debug("No current Celery task, returning no-op recovery context")
            return NoOpRecoveryContext()

        task_id = current_task.request.id
        # Get the task name as a string
        task_name = str(current_task.name) if current_task.name else "unknown_task"

        # Get task arguments from Celery request
        task_args = current_task.request.args[1:]  # Skip context_key
        task_kwargs = current_task.request.kwargs.copy()

        # Initialize task registry
        registry = TaskRegistry()
        registry_id = await registry.create_entry(
            task_id=task_id,
            task_name=task_name,
            user_id=user_id,
            task_args=task_args,
            task_kwargs=task_kwargs,
            recovery_priority=recovery_priority,
            auto_recovery_enabled=True,
        )

        # Create recovery context with context_key for TTL refresh
        recovery_ctx = RecoveryContext(task_id, registry, context_key)

        # Check if this is a recovered task
        latest_checkpoint = await registry.get_latest_checkpoint(task_id)
        if latest_checkpoint:
            logger.info(
                f"Resuming task {task_id} from checkpoint: {latest_checkpoint.checkpoint_name}"
            )
            # Add recovery checkpoint to kwargs so task can access it
            # Note: This won't affect the original kwargs, just our copy
            task_kwargs["_recovery_checkpoint"] = latest_checkpoint.to_dict()

        logger.debug(f"Created recovery context for task {task_id}")
        return recovery_ctx

    except Exception as e:
        logger.error(f"Failed to create recovery context: {e}")
        # Return no-op context on error to prevent task failure
        return NoOpRecoveryContext()


class NoOpRecoveryContext:
    """No-op recovery context for tasks not running under Celery"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def create_checkpoint(self, checkpoint: CheckpointData) -> str:
        logger.debug("No-op checkpoint creation outside Celery task")
        return "noop"

    async def update_progress(
        self, progress_percent: int, current_step: str, step_description: str = None
    ):
        logger.debug(f"No-op progress update: {progress_percent}% - {current_step}")

    async def refresh_context_ttl(self) -> bool:
        """No-op TTL refresh outside Celery task"""
        logger.debug("No-op context TTL refresh outside Celery task")
        return True


# async def extract_user_id_from_context(context_key: str) -> str:
#     """Extract user ID from task context"""
#     try:
#         # This would integrate with your existing task context system
#         from app.core.task_context import task_auth_context

#         # Get user ID from context without full restoration
#         # Implementation depends on your context storage format
#         context_store = await get_task_store()
#         context_data = await context_store.retrieve_context(context_key)
#         return context_data.get("user_id")

#     except Exception as e:
#         logger.error(f"Failed to extract user_id from context {context_key}: {e}")
#         raise Exception(f"Could not extract user_id from task context: {e}")


def is_recoverable_error(exc: Exception) -> bool:
    """Determine if an exception indicates a recoverable failure"""
    recoverable_error_types = [
        ConnectionError,
        TimeoutError,
        OSError,  # File system issues
        MemoryError,  # Resource exhaustion
    ]

    recoverable_messages = [
        "connection reset",
        "timeout",
        "temporary failure",
        "rate limit",
        "service unavailable",
    ]

    # Check exception type
    if any(isinstance(exc, error_type) for error_type in recoverable_error_types):
        return True

    # Check exception message
    error_msg = str(exc).lower()
    return any(msg in error_msg for msg in recoverable_messages)
