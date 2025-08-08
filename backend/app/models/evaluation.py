"""
Core evaluation models for the LLM evaluation framework.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class EvaluationStatus(str, Enum):
    """Evaluation run status."""
    CREATED = "created"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    COST = "cost"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    FAITHFULNESS = "faithfulness"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    AGGREGATE = "aggregate"


class ModelConfig(BaseModel):
    """Configuration for a model to be evaluated."""
    provider: str = Field(..., description="Model provider (openai, google)")
    model: str = Field(..., description="Model name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Model parameters")
    version: Optional[str] = Field(None, description="Model version")


class TestCase(BaseModel):
    """Individual test case for evaluation."""
    id: UUID = Field(default_factory=uuid4)
    input_data: Dict[str, Any] = Field(..., description="Input data for the test")
    expected_output: Optional[Dict[str, Any]] = Field(None, description="Expected output")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class ModelResponse(BaseModel):
    """Response from a model for a test case."""
    model_provider: str
    model_name: str
    response_text: str
    latency: float = Field(..., description="Response latency in seconds")
    token_usage: Dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    test_case_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


class MetricResult(BaseModel):
    """Result of a metric calculation."""
    metric_name: str
    metric_type: MetricType
    value: float
    details: Dict[str, Any] = Field(default_factory=dict)
    test_case_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


class EvaluationResult(BaseModel):
    """Complete result for a test case evaluation."""
    id: UUID = Field(default_factory=uuid4)
    test_case: Optional[TestCase] = None
    model_responses: List[ModelResponse] = Field(default_factory=list)
    metrics: List[MetricResult] = Field(default_factory=list)
    execution_time: float = Field(..., description="Total execution time in seconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    evaluation_run_id: UUID
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationConfig(BaseModel):
    """Configuration for an evaluation run."""
    name: str = Field(..., description="Name of the evaluation")
    description: Optional[str] = None
    models: List[ModelConfig] = Field(..., description="Models to evaluate")
    metrics: List[str] = Field(..., description="Metrics to calculate")
    test_suite_id: Optional[UUID] = None
    test_cases: Optional[List[TestCase]] = None
    batch_size: int = Field(10, description="Batch size for processing")
    max_concurrency: int = Field(5, description="Maximum concurrent executions")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationRun(BaseModel):
    """An evaluation run record."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    config: EvaluationConfig
    status: EvaluationStatus = EvaluationStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    test_case_count: int = 0
    model_configs: List[ModelConfig] = Field(default_factory=list)
    results_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None