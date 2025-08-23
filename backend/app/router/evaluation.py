"""
LLM Evaluation API Router.

Production-ready REST API for LLM evaluation system including:
- Prompt template management
- Test dataset management
- Evaluation job execution
- A/B testing
- Analytics and reporting
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
    BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import csv
import io
import uuid

from app.core.auth import get_admin_user
from app.schema.auth import UserResponse as User
from app.services.evaluation_service import (
    get_evaluation_orchestrator,
    EvaluationStatus,
)
from app.clients.factory import get_supabase_client

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])
logger = logging.getLogger(__name__)

# Pydantic Models for API


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="1.0", max_length=50)
    template_content: str = Field(..., min_length=1)
    variables: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class PromptTemplateUpdate(BaseModel):
    template_content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PromptTemplateResponse(BaseModel):
    id: str
    name: str
    version: str
    template_content: str
    variables: Optional[Dict[str, Any]]
    description: Optional[str]
    tags: Optional[List[str]]
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


class TestDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TestDatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    domain: Optional[str]
    size: int
    metadata: Optional[Dict[str, Any]]
    created_by: str
    created_at: datetime
    is_active: bool


class TestCaseCreate(BaseModel):
    input_data: Dict[str, Any] = Field(..., min_length=1)
    expected_output: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class TestCaseResponse(BaseModel):
    id: str
    dataset_id: str
    input_data: Dict[str, Any]
    expected_output: Optional[str]
    metadata: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    created_at: datetime


class ModelConfig(BaseModel):
    model_name: str
    provider: str = Field(..., pattern="^(openai|gemini)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MetricsConfig(BaseModel):
    bleu_enabled: bool = False
    rouge_enabled: bool = False
    semantic_similarity_enabled: bool = True
    faithfulness_enabled: bool = True
    relevance_enabled: bool = True
    coherence_enabled: bool = True
    custom_metrics: List[str] = Field(default_factory=list)
    metric_weights: Dict[str, float] = Field(default_factory=dict)


class EvaluationJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    prompt_template_id: str
    dataset_id: str
    model_configs: List[ModelConfig] = Field(..., min_items=1)
    metrics_config: MetricsConfig
    priority: int = Field(default=5, ge=1, le=10)


class EvaluationJobResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    prompt_template_id: str
    dataset_id: str
    model_configs: List[Dict[str, Any]]
    metrics_config: Dict[str, Any]
    status: str
    progress: float
    priority: int
    estimated_duration: Optional[int]
    created_by: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class EvaluationResultResponse(BaseModel):
    id: str
    job_id: str
    test_case_id: str
    model_name: str
    prompt_used: str
    generated_response: str
    response_time_ms: int
    token_usage: int
    metrics_scores: Dict[str, float]
    langsmith_run_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime


class ABTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    control_prompt_id: str
    variant_prompt_id: str
    traffic_split: float = Field(default=0.5, gt=0.0, lt=1.0)
    target_sample_size: Optional[int] = Field(None, gt=0)
    significance_level: float = Field(default=0.05, gt=0.0, lt=1.0)
    primary_metric: str = Field(default="overall_score")


class ABTestResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    control_prompt_id: str
    variant_prompt_id: str
    traffic_split: float
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    target_sample_size: Optional[int]
    significance_level: float
    primary_metric: str
    created_by: str
    created_at: datetime


class ModelComparisonResponse(BaseModel):
    model_name: str
    total_evaluations: int
    avg_overall_score: float
    avg_response_time: float
    total_tokens: int
    first_evaluation: datetime
    last_evaluation: datetime


class JobSummaryResponse(BaseModel):
    job_id: str
    total_evaluations: int
    successful_evaluations: int
    success_rate: float
    avg_response_time: Optional[float]
    total_tokens: int
    avg_overall_score: Optional[float]
    metrics_breakdown: Dict[str, float]
    generated_at: datetime


# Prompt Template Endpoints


@router.post("/prompts", response_model=PromptTemplateResponse)
async def create_prompt_template(
    prompt: PromptTemplateCreate, current_user: User = Depends(get_admin_user)
):
    """Create a new prompt template."""
    supabase = await get_supabase_client()

    # Check if name/version combination already exists
    existing = (
        await supabase.table("prompt_templates")
        .select("id")
        .eq("name", prompt.name)
        .eq("version", prompt.version)
        .eq("created_by", current_user.id)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt template '{prompt.name}' version '{prompt.version}' already exists",
        )

    # Create template
    template_data = {
        "name": prompt.name,
        "version": prompt.version,
        "template_content": prompt.template_content,
        "variables": prompt.variables or {},
        "description": prompt.description,
        "tags": prompt.tags or [],
        "created_by": current_user.id,
    }

    result = supabase.table("prompt_templates").insert(template_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create prompt template")

    return PromptTemplateResponse(**result.data[0])


@router.get("/prompts", response_model=List[PromptTemplateResponse])
async def list_prompt_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, min_length=1),
    tag: Optional[str] = Query(None),
    is_active: bool = Query(True),
    current_user: User = Depends(get_admin_user),
):
    """List prompt templates with filtering and pagination."""
    try:
        supabase = await get_supabase_client()

        query = (
            supabase.table("prompt_templates")
            .select("*")
            .eq("created_by", current_user.id)
            .eq("is_active", is_active)
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
        )

        if search:
            query = query.ilike("name", f"%{search}%")

        if tag:
            query = query.contains("tags", [tag])

        result = query.execute()

        return [PromptTemplateResponse(**item) for item in result.data]
    except Exception as e:
        # If table doesn't exist or other database error, return empty list
        # This prevents 500 errors when the evaluation tables haven't been created yet
        logger.warning(f"Error fetching prompt templates: {e}. Returning empty list.")
        return []


@router.get("/prompts/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt_template(
    prompt_id: str, current_user: User = Depends(get_admin_user)
):
    """Get a specific prompt template."""
    supabase = await get_supabase_client()

    result = (
        await supabase.table("prompt_templates")
        .select("*")
        .eq("id", prompt_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    return PromptTemplateResponse(**result.data)


@router.put("/prompts/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt_template(
    prompt_id: str,
    prompt_update: PromptTemplateUpdate,
    current_user: User = Depends(get_admin_user),
):
    """Update a prompt template."""
    supabase = await get_supabase_client()

    # Verify ownership
    existing = (
        await supabase.table("prompt_templates")
        .select("id")
        .eq("id", prompt_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    # Update template
    update_data = {k: v for k, v in prompt_update.dict().items() if v is not None}

    result = (
        await supabase.table("prompt_templates")
        .update(update_data)
        .eq("id", prompt_id)
        .execute()
    )

    return PromptTemplateResponse(**result.data[0])


@router.delete("/prompts/{prompt_id}")
async def delete_prompt_template(
    prompt_id: str, current_user: User = Depends(get_admin_user)
):
    """Delete a prompt template (soft delete by setting is_active=false)."""
    supabase = await get_supabase_client()

    result = (
        await supabase.table("prompt_templates")
        .update({"is_active": False})
        .eq("id", prompt_id)
        .eq("created_by", current_user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    return {"message": "Prompt template deleted successfully"}


# Test Dataset Endpoints


@router.post("/datasets", response_model=TestDatasetResponse)
async def create_dataset(
    dataset: TestDatasetCreate, current_user: User = Depends(get_admin_user)
):
    """Create a new test dataset."""
    supabase = await get_supabase_client()

    # Check if name already exists
    existing = (
        await supabase.table("test_datasets")
        .select("id")
        .eq("name", dataset.name)
        .eq("created_by", current_user.id)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=400, detail=f"Test dataset '{dataset.name}' already exists"
        )

    dataset_data = {
        "name": dataset.name,
        "description": dataset.description,
        "domain": dataset.domain,
        "metadata": dataset.metadata or {},
        "created_by": current_user.id,
    }

    result = supabase.table("test_datasets").insert(dataset_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create test dataset")

    return TestDatasetResponse(**result.data[0])


@router.get("/datasets", response_model=List[TestDatasetResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    domain: Optional[str] = Query(None),
    current_user: User = Depends(get_admin_user),
):
    """List test datasets with filtering and pagination."""
    supabase = await get_supabase_client()

    query = (
        supabase.table("test_datasets")
        .select("*")
        .eq("created_by", current_user.id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
    )

    if domain:
        query = query.eq("domain", domain)

    result = query.execute()

    return [TestDatasetResponse(**item) for item in result.data]


@router.post("/datasets/{dataset_id}/test-cases", response_model=TestCaseResponse)
async def add_test_case(
    dataset_id: str,
    test_case: TestCaseCreate,
    current_user: User = Depends(get_admin_user),
):
    """Add a test case to a dataset."""
    supabase = await get_supabase_client()

    # Verify dataset ownership
    dataset_result = (
        await supabase.table("test_datasets")
        .select("id")
        .eq("id", dataset_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not dataset_result.data:
        raise HTTPException(status_code=404, detail="Test dataset not found")

    test_case_data = {
        "dataset_id": dataset_id,
        "input_data": test_case.input_data,
        "expected_output": test_case.expected_output,
        "metadata": test_case.metadata or {},
        "tags": test_case.tags or [],
    }

    result = supabase.table("test_cases").insert(test_case_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create test case")

    return TestCaseResponse(**result.data[0])


@router.get("/datasets/{dataset_id}/test-cases", response_model=List[TestCaseResponse])
async def get_test_cases(
    dataset_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_admin_user),
):
    """Get test cases for a dataset."""
    supabase = await get_supabase_client()

    # Verify dataset ownership
    dataset_result = (
        await supabase.table("test_datasets")
        .select("id")
        .eq("id", dataset_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not dataset_result.data:
        raise HTTPException(status_code=404, detail="Test dataset not found")

    result = (
        await supabase.table("test_cases")
        .select("*")
        .eq("dataset_id", dataset_id)
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )

    return [TestCaseResponse(**item) for item in result.data]


@router.post("/datasets/{dataset_id}/import")
async def import_dataset(
    dataset_id: str,
    file: UploadFile = File(...),
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: User = Depends(get_admin_user),
):
    """Import test cases from file (CSV, JSON)."""
    supabase = await get_supabase_client()

    # Verify dataset ownership
    dataset_result = (
        await supabase.table("test_datasets")
        .select("id")
        .eq("id", dataset_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not dataset_result.data:
        raise HTTPException(status_code=404, detail="Test dataset not found")

    try:
        content = await file.read()

        if format == "csv":
            # Parse CSV
            csv_content = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_content))
            test_cases = []

            for row in reader:
                # Convert row to test case format
                input_data = {
                    k: v for k, v in row.items() if not k.startswith("expected_")
                }
                expected_output = row.get("expected_output")

                test_cases.append(
                    {
                        "dataset_id": dataset_id,
                        "input_data": input_data,
                        "expected_output": expected_output,
                        "metadata": {},
                        "tags": [],
                    }
                )

        elif format == "json":
            # Parse JSON
            json_data = json.loads(content.decode("utf-8"))

            if not isinstance(json_data, list):
                raise HTTPException(
                    status_code=400, detail="JSON must be an array of test cases"
                )

            test_cases = []
            for item in json_data:
                test_cases.append(
                    {
                        "dataset_id": dataset_id,
                        "input_data": item.get("input_data", {}),
                        "expected_output": item.get("expected_output"),
                        "metadata": item.get("metadata", {}),
                        "tags": item.get("tags", []),
                    }
                )

        # Batch insert test cases
        if test_cases:
            result = supabase.table("test_cases").insert(test_cases).execute()
            imported_count = len(result.data) if result.data else 0
        else:
            imported_count = 0

        return {
            "message": f"Successfully imported {imported_count} test cases",
            "imported_count": imported_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to import dataset: {str(e)}"
        )


# Evaluation Job Endpoints


@router.post("/jobs", response_model=EvaluationJobResponse)
async def create_evaluation_job(
    job: EvaluationJobCreate, current_user: User = Depends(get_admin_user)
):
    """Create and start a new evaluation job."""
    orchestrator = await get_evaluation_orchestrator()

    try:
        job_id = await orchestrator.create_evaluation_job(
            name=job.name,
            prompt_template_id=job.prompt_template_id,
            dataset_id=job.dataset_id,
            model_configs=[config.dict() for config in job.model_configs],
            metrics_config=job.metrics_config.dict(),
            user_id=current_user.id,
        )

        # Get created job details
        job_status = await orchestrator.get_job_status(job_id)
        return EvaluationJobResponse(**job_status)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create evaluation job: {str(e)}"
        )


@router.get("/jobs", response_model=List[EvaluationJobResponse])
async def list_evaluation_jobs(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_admin_user),
):
    """List evaluation jobs with optional filtering."""
    try:
        supabase = await get_supabase_client()

        query = (
            supabase.table("evaluation_jobs")
            .select("*")
            .eq("created_by", current_user.id)
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
        )

        if status:
            query = query.eq("status", status)

        result = query.execute()

        return [
            EvaluationJobResponse(
                **item,
                model_configs=json.loads(item["model_configs"]),
                metrics_config=json.loads(item["metrics_config"]),
            )
            for item in result.data
        ]
    except Exception as e:
        # If table doesn't exist or other database error, return empty list
        # This prevents 500 errors when the evaluation tables haven't been created yet
        logger.warning(f"Error fetching evaluation jobs: {e}. Returning empty list.")
        return []


@router.get("/jobs/{job_id}", response_model=EvaluationJobResponse)
async def get_evaluation_job(job_id: str, current_user: User = Depends(get_admin_user)):
    """Get evaluation job details."""
    orchestrator = await get_evaluation_orchestrator()

    job_status = await orchestrator.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    # Verify ownership
    if job_status.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return EvaluationJobResponse(
        **job_status,
        model_configs=json.loads(job_status["model_configs"]),
        metrics_config=json.loads(job_status["metrics_config"]),
    )


@router.get("/jobs/{job_id}/results", response_model=List[EvaluationResultResponse])
async def get_evaluation_results(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    model_name: Optional[str] = Query(None),
    current_user: User = Depends(get_admin_user),
):
    """Get results for an evaluation job."""
    supabase = await get_supabase_client()

    # Verify job ownership
    job_result = (
        await supabase.table("evaluation_jobs")
        .select("id")
        .eq("id", job_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not job_result.data:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    query = (
        supabase.table("evaluation_results")
        .select("*")
        .eq("job_id", job_id)
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
    )

    if model_name:
        query = query.eq("model_name", model_name)

    result = query.execute()

    return [
        EvaluationResultResponse(
            **item, metrics_scores=json.loads(item["metrics_scores"])
        )
        for item in result.data
    ]


@router.post("/jobs/{job_id}/cancel")
async def cancel_evaluation_job(
    job_id: str, current_user: User = Depends(get_admin_user)
):
    """Cancel a running evaluation job."""
    supabase = await get_supabase_client()

    # Verify job ownership
    job_result = (
        await supabase.table("evaluation_jobs")
        .select("id, status")
        .eq("id", job_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not job_result.data:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    if job_result.data["status"] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    orchestrator = await get_evaluation_orchestrator()
    success = await orchestrator.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel job")

    return {"message": "Job cancelled successfully"}


# Analytics and Reporting Endpoints


@router.get("/analytics/model-comparison", response_model=List[ModelComparisonResponse])
async def get_model_comparison_analytics(
    dataset_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_admin_user),
):
    """Get model performance comparison analytics."""
    supabase = await get_supabase_client()

    # Use the pre-created view for performance
    query = supabase.rpc(
        "get_model_comparison_for_user",
        {
            "user_id": current_user.id,
            "dataset_filter": dataset_id,
            "date_from_filter": date_from.isoformat() if date_from else None,
            "date_to_filter": date_to.isoformat() if date_to else None,
        },
    )

    result = query.execute()

    return [ModelComparisonResponse(**item) for item in result.data or []]


@router.get("/analytics/job-summary/{job_id}", response_model=JobSummaryResponse)
async def get_job_summary(job_id: str, current_user: User = Depends(get_admin_user)):
    """Get summary analytics for a specific job."""
    supabase = await get_supabase_client()

    # Verify job ownership
    job_result = (
        await supabase.table("evaluation_jobs")
        .select("id")
        .eq("id", job_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not job_result.data:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    # Get job summary
    summary_result = (
        await supabase.table("evaluation_job_summaries")
        .select("*")
        .eq("job_id", job_id)
        .single()
        .execute()
    )

    if not summary_result.data:
        raise HTTPException(status_code=404, detail="Job summary not found")

    summary = summary_result.data

    # Build metrics breakdown
    metrics_breakdown = {}
    for key, value in summary.items():
        if key.startswith("avg_") and value is not None:
            metric_name = key.replace("avg_", "")
            metrics_breakdown[metric_name] = value

    return JobSummaryResponse(**summary, metrics_breakdown=metrics_breakdown)


@router.get("/analytics/dashboard")
async def get_evaluation_dashboard(current_user: User = Depends(get_admin_user)):
    """Get dashboard data for evaluation overview."""
    try:
        supabase = await get_supabase_client()

        # Get summary statistics
        stats_result = supabase.rpc(
            "get_user_evaluation_stats", {"user_id": current_user.id}
        ).execute()

        stats = stats_result.data[0] if stats_result.data else {}

        # Get recent jobs
        recent_jobs = (
            await supabase.table("evaluation_jobs")
            .select("id, name, status, progress, created_at")
            .eq("created_by", current_user.id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return {
            "stats": {
                "total_prompts": stats.get("total_prompts", 0),
                "total_datasets": stats.get("total_datasets", 0),
                "total_jobs": stats.get("total_jobs", 0),
                "total_evaluations": stats.get("total_evaluations", 0),
                "avg_overall_score": stats.get("avg_overall_score", 0.0),
            },
            "recent_jobs": recent_jobs.data,
            "generated_at": datetime.utcnow(),
        }
    except Exception as e:
        # If tables don't exist or other database error, return empty dashboard
        # This prevents 500 errors when the evaluation tables haven't been created yet
        logger.warning(
            f"Error fetching evaluation dashboard: {e}. Returning empty dashboard."
        )
        return {
            "stats": {
                "total_prompts": 0,
                "total_datasets": 0,
                "total_jobs": 0,
                "total_evaluations": 0,
                "avg_overall_score": 0.0,
            },
            "recent_jobs": [],
            "generated_at": datetime.utcnow(),
        }


# Export Endpoints


@router.get("/jobs/{job_id}/export")
async def export_evaluation_results(
    job_id: str,
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: User = Depends(get_admin_user),
):
    """Export evaluation results to CSV or JSON."""
    supabase = await get_supabase_client()

    # Verify job ownership
    job_result = (
        await supabase.table("evaluation_jobs")
        .select("id, name")
        .eq("id", job_id)
        .eq("created_by", current_user.id)
        .single()
        .execute()
    )

    if not job_result.data:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    # Get all results
    results = (
        await supabase.table("evaluation_results")
        .select("*")
        .eq("job_id", job_id)
        .execute()
    )

    if not results.data:
        raise HTTPException(status_code=404, detail="No results found")

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        fieldnames = [
            "id",
            "model_name",
            "response_time_ms",
            "token_usage",
            "generated_response",
            "error_message",
            "created_at",
        ]

        # Add metric columns
        if results.data:
            metrics = json.loads(results.data[0]["metrics_scores"])
            fieldnames.extend([f"metric_{k}" for k in metrics.keys()])

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for result in results.data:
            row = {k: v for k, v in result.items() if k in fieldnames}

            # Add metrics
            metrics = json.loads(result["metrics_scores"])
            for k, v in metrics.items():
                row[f"metric_{k}"] = v

            writer.writerow(row)

        content = output.getvalue()
        filename = f"evaluation_results_{job_id}.csv"
        media_type = "text/csv"

    elif format == "json":
        # Generate JSON
        export_data = []
        for result in results.data:
            export_item = result.copy()
            export_item["metrics_scores"] = json.loads(result["metrics_scores"])
            export_data.append(export_item)

        content = json.dumps(export_data, indent=2, default=str)
        filename = f"evaluation_results_{job_id}.json"
        media_type = "application/json"

    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
