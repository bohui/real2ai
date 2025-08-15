"""Evaluation and monitoring enums."""

from enum import Enum


class EvaluationStatus(str, Enum):
    """Evaluation status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Metric types"""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    OTHER = "other"


class EvaluationMode(Enum):
    """Evaluation modes"""

    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"
