"""Recovery and retry enums."""

from enum import Enum


class RecoveryMethod(str, Enum):
    """Recovery method types"""

    RESUME_CHECKPOINT = "resume_checkpoint"
    RESTART_CLEAN = "restart_clean"
    VALIDATE_ONLY = "validate_only"
    MANUAL_INTERVENTION = "manual_intervention"


class RetryStrategy(str, Enum):
    """Retry strategy types"""

    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
