"""Workflow and processing enums."""

from enum import Enum


class WorkflowStepStatus(Enum):
    """Workflow step status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Run status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskState(str, Enum):
    """Task state"""

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


class ProcessingPriority(Enum):
    """Processing priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
