"""
Evaluation and testing schema models for Real2.AI platform.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PromptTemplateCreate(BaseModel):
    """Create new prompt template"""
    
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template: str = Field(..., description="Prompt template content")
    category: str = Field("general", description="Template category")


class PromptTemplateUpdate(BaseModel):
    """Update prompt template"""
    
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateResponse(BaseModel):
    """Prompt template response"""
    
    id: str
    name: str
    description: str
    template: str
    category: str
    created_at: datetime
    updated_at: datetime
    version: int
    is_active: bool


class TestDatasetCreate(BaseModel):
    """Create test dataset"""
    
    name: str
    description: str
    test_cases: List[Dict[str, Any]]


class TestDatasetResponse(BaseModel):
    """Test dataset response"""
    
    id: str
    name: str
    description: str
    test_cases: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    test_case_count: int


class TestCaseCreate(BaseModel):
    """Create individual test case"""
    
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class TestCaseResponse(BaseModel):
    """Test case response"""
    
    id: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime


class ModelConfig(BaseModel):
    """Model configuration for evaluation"""
    
    model_name: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    additional_params: Dict[str, Any] = {}


class MetricsConfig(BaseModel):
    """Metrics configuration for evaluation"""
    
    accuracy: bool = True
    precision: bool = True
    recall: bool = True
    f1_score: bool = True
    custom_metrics: List[str] = []
    evaluation_criteria: Dict[str, Any] = {}


class EvaluationJobCreate(BaseModel):
    """Create evaluation job"""
    
    name: str
    prompt_template_id: str
    test_dataset_id: str
    model_config: ModelConfig
    metrics_config: MetricsConfig


class EvaluationJobResponse(BaseModel):
    """Evaluation job response"""
    
    id: str
    name: str
    status: str  # pending, running, completed, failed
    prompt_template_id: str
    test_dataset_id: str
    model_config: ModelConfig
    metrics_config: MetricsConfig
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: int = 0
    error_message: Optional[str] = None


class EvaluationResultResponse(BaseModel):
    """Evaluation result response"""
    
    job_id: str
    overall_score: float
    metric_scores: Dict[str, float]
    test_case_results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    recommendations: List[str]
    completed_at: datetime
    execution_time_seconds: float


class ABTestCreate(BaseModel):
    """Create A/B test"""
    
    name: str
    description: str
    variant_a_template_id: str
    variant_b_template_id: str
    test_dataset_id: str
    traffic_split: float = 0.5  # 50/50 split by default


class ABTestResponse(BaseModel):
    """A/B test response"""
    
    id: str
    name: str
    description: str
    status: str  # draft, running, completed, paused
    variant_a_template_id: str
    variant_b_template_id: str
    test_dataset_id: str
    traffic_split: float
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ModelComparisonResponse(BaseModel):
    """Model comparison response"""
    
    comparison_id: str
    models_compared: List[str]
    metrics: Dict[str, Dict[str, float]]  # model -> metric -> score
    winner: Optional[str] = None
    confidence_score: float
    recommendations: List[str]


class JobSummaryResponse(BaseModel):
    """Job summary response"""
    
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    recent_jobs: List[EvaluationJobResponse]