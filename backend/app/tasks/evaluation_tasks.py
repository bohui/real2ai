"""
Background Tasks for LLM Evaluation System.

Production-ready Celery tasks for:
- Batch evaluation processing
- Scheduled evaluation jobs
- A/B test management
- Performance monitoring
- Data cleanup and maintenance
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from celery import Celery
from celery.schedules import crontab
import json

from app.core.config import get_settings
from app.services.evaluation_service import get_evaluation_orchestrator, EvaluationStatus
from app.dependencies.supabase import get_supabase_client
from app.core.langsmith_config import langsmith_trace

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
settings = get_settings()
celery_app = Celery(
    "evaluation_tasks",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0"
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-cache": {
        "task": "app.tasks.evaluation_tasks.cleanup_expired_cache",
        "schedule": crontab(minute=0),  # Every hour
    },
    "monitor-stuck-jobs": {
        "task": "app.tasks.evaluation_tasks.monitor_stuck_jobs", 
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "generate-daily-reports": {
        "task": "app.tasks.evaluation_tasks.generate_daily_reports",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    "cleanup-old-results": {
        "task": "app.tasks.evaluation_tasks.cleanup_old_results",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Weekly on Sunday
    },
}


def run_async_task(async_func):
    """Decorator to run async functions in Celery tasks."""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


@celery_app.task(bind=True, name="evaluation_tasks.process_evaluation_job")
@run_async_task
async def process_evaluation_job(self, job_id: str):
    """Process a single evaluation job."""
    try:
        logger.info(f"Starting evaluation job {job_id}")
        
        # Update task metadata
        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "status": "initializing"}
        )
        
        orchestrator = await get_evaluation_orchestrator()
        
        # Execute the job
        await orchestrator._execute_evaluation_job(job_id)
        
        self.update_state(
            state="SUCCESS",
            meta={"job_id": job_id, "status": "completed"}
        )
        
        logger.info(f"Completed evaluation job {job_id}")
        return {"job_id": job_id, "status": "completed"}
        
    except Exception as e:
        logger.error(f"Failed to process evaluation job {job_id}: {e}")
        
        self.update_state(
            state="FAILURE",
            meta={"job_id": job_id, "error": str(e)}
        )
        
        # Update job status in database
        supabase = await get_supabase_client()
        await supabase.table("evaluation_jobs")\
            .update({
                "status": EvaluationStatus.FAILED.value,
                "error_message": str(e),
                "completed_at": datetime.utcnow().isoformat()
            })\
            .eq("id", job_id)\
            .execute()
        
        raise


@celery_app.task(bind=True, name="evaluation_tasks.batch_evaluate_prompts")
@run_async_task
async def batch_evaluate_prompts(
    self,
    prompt_ids: List[str],
    dataset_id: str,
    model_configs: List[Dict[str, Any]],
    metrics_config: Dict[str, Any],
    user_id: str
):
    """Batch evaluate multiple prompts against a dataset."""
    try:
        logger.info(f"Starting batch evaluation for {len(prompt_ids)} prompts")
        
        orchestrator = await get_evaluation_orchestrator()
        job_ids = []
        
        total_jobs = len(prompt_ids)
        completed_jobs = 0
        
        # Create jobs for each prompt
        for i, prompt_id in enumerate(prompt_ids):
            try:
                job_name = f"Batch Evaluation {i+1}/{total_jobs}"
                
                job_id = await orchestrator.create_evaluation_job(
                    name=job_name,
                    prompt_template_id=prompt_id,
                    dataset_id=dataset_id,
                    model_configs=model_configs,
                    metrics_config=metrics_config,
                    user_id=user_id
                )
                
                job_ids.append(job_id)
                completed_jobs += 1
                
                # Update progress
                progress = (completed_jobs / total_jobs) * 100
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "completed_jobs": completed_jobs,
                        "total_jobs": total_jobs,
                        "progress": progress,
                        "job_ids": job_ids
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to create job for prompt {prompt_id}: {e}")
                continue
        
        logger.info(f"Created {len(job_ids)} batch evaluation jobs")
        
        return {
            "created_jobs": len(job_ids),
            "total_prompts": total_jobs,
            "job_ids": job_ids
        }
        
    except Exception as e:
        logger.error(f"Batch evaluation failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="evaluation_tasks.schedule_ab_test")
@run_async_task
async def schedule_ab_test(
    test_id: str,
    start_time: str,
    end_time: Optional[str] = None
):
    """Schedule an A/B test to start and optionally stop."""
    try:
        supabase = await get_supabase_client()
        
        # Update test status to active
        await supabase.table("ab_tests")\
            .update({
                "status": "active",
                "start_date": start_time
            })\
            .eq("id", test_id)\
            .execute()
        
        logger.info(f"Started A/B test {test_id}")
        
        # Schedule end task if end time provided
        if end_time:
            stop_ab_test.apply_async(
                args=[test_id],
                eta=datetime.fromisoformat(end_time)
            )
        
        return {"test_id": test_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Failed to schedule A/B test {test_id}: {e}")
        raise


@celery_app.task(name="evaluation_tasks.stop_ab_test")
@run_async_task
async def stop_ab_test(test_id: str):
    """Stop an A/B test and generate final report."""
    try:
        supabase = await get_supabase_client()
        
        # Update test status to completed
        await supabase.table("ab_tests")\
            .update({
                "status": "completed",
                "end_date": datetime.utcnow().isoformat()
            })\
            .eq("id", test_id)\
            .execute()
        
        # Generate final analysis report
        await generate_ab_test_report.delay(test_id)
        
        logger.info(f"Stopped A/B test {test_id}")
        return {"test_id": test_id, "status": "completed"}
        
    except Exception as e:
        logger.error(f"Failed to stop A/B test {test_id}: {e}")
        raise


@celery_app.task(name="evaluation_tasks.generate_ab_test_report")
@run_async_task
async def generate_ab_test_report(test_id: str):
    """Generate statistical analysis report for A/B test."""
    try:
        supabase = await get_supabase_client()
        
        # Get test configuration
        test_result = await supabase.table("ab_tests")\
            .select("*")\
            .eq("id", test_id)\
            .single()\
            .execute()
        
        test_data = test_result.data
        
        # Get all interactions
        interactions_result = await supabase.table("ab_test_interactions")\
            .select("*")\
            .eq("test_id", test_id)\
            .execute()
        
        interactions = interactions_result.data
        
        if not interactions:
            logger.warning(f"No interactions found for A/B test {test_id}")
            return
        
        # Perform statistical analysis
        control_interactions = [i for i in interactions if i["variant"] == "control"]
        variant_interactions = [i for i in interactions if i["variant"] == "variant"]
        
        # Calculate metrics
        control_metrics = _calculate_variant_metrics(control_interactions)
        variant_metrics = _calculate_variant_metrics(variant_interactions)
        
        # Statistical significance test (simplified)
        significance_result = _perform_statistical_test(
            control_metrics,
            variant_metrics,
            test_data["significance_level"]
        )
        
        # Store report
        report_data = {
            "test_id": test_id,
            "control_sample_size": len(control_interactions),
            "variant_sample_size": len(variant_interactions),
            "control_metrics": control_metrics,
            "variant_metrics": variant_metrics,
            "statistical_significance": significance_result,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        await supabase.table("ab_test_reports")\
            .insert(report_data)\
            .execute()
        
        logger.info(f"Generated A/B test report for {test_id}")
        return report_data
        
    except Exception as e:
        logger.error(f"Failed to generate A/B test report {test_id}: {e}")
        raise


def _calculate_variant_metrics(interactions: List[Dict]) -> Dict[str, float]:
    """Calculate metrics for a variant in A/B test."""
    if not interactions:
        return {}
    
    total_interactions = len(interactions)
    total_response_time = sum(i["response_time_ms"] for i in interactions)
    conversions = sum(1 for i in interactions if i.get("conversion_event", False))
    
    return {
        "sample_size": total_interactions,
        "avg_response_time": total_response_time / total_interactions,
        "conversion_rate": conversions / total_interactions,
        "total_conversions": conversions
    }


def _perform_statistical_test(
    control_metrics: Dict[str, float],
    variant_metrics: Dict[str, float],
    significance_level: float
) -> Dict[str, Any]:
    """Perform statistical significance test (simplified implementation)."""
    # This is a simplified implementation
    # In production, use proper statistical libraries like scipy
    
    control_conversion_rate = control_metrics.get("conversion_rate", 0)
    variant_conversion_rate = variant_metrics.get("conversion_rate", 0)
    
    # Calculate difference
    difference = variant_conversion_rate - control_conversion_rate
    relative_improvement = (difference / control_conversion_rate * 100) if control_conversion_rate > 0 else 0
    
    # Simplified significance test (normally would use proper statistical test)
    sample_sizes_adequate = (
        control_metrics.get("sample_size", 0) >= 100 and
        variant_metrics.get("sample_size", 0) >= 100
    )
    
    # Placeholder for proper statistical test
    is_significant = sample_sizes_adequate and abs(relative_improvement) > 5  # Simplified
    
    return {
        "is_significant": is_significant,
        "p_value": 0.05 if is_significant else 0.1,  # Placeholder
        "confidence_level": 1 - significance_level,
        "difference": difference,
        "relative_improvement": relative_improvement,
        "sample_sizes_adequate": sample_sizes_adequate
    }


@celery_app.task(name="evaluation_tasks.cleanup_expired_cache")
@run_async_task
async def cleanup_expired_cache():
    """Clean up expired cache entries."""
    try:
        supabase = await get_supabase_client()
        
        # Clean up expired model performance cache
        result = await supabase.table("model_performance_cache")\
            .delete()\
            .lt("expires_at", datetime.utcnow().isoformat())\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"Cleaned up {deleted_count} expired cache entries")
        
        return {"deleted_entries": deleted_count}
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise


@celery_app.task(name="evaluation_tasks.monitor_stuck_jobs")
@run_async_task
async def monitor_stuck_jobs():
    """Monitor and handle stuck evaluation jobs."""
    try:
        supabase = await get_supabase_client()
        
        # Find jobs that have been running for more than 1 hour
        cutoff_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        stuck_jobs = await supabase.table("evaluation_jobs")\
            .select("id, name, started_at")\
            .eq("status", "running")\
            .lt("started_at", cutoff_time)\
            .execute()
        
        if not stuck_jobs.data:
            return {"stuck_jobs": 0}
        
        # Mark stuck jobs as failed
        for job in stuck_jobs.data:
            await supabase.table("evaluation_jobs")\
                .update({
                    "status": EvaluationStatus.FAILED.value,
                    "error_message": "Job timeout - exceeded maximum runtime",
                    "completed_at": datetime.utcnow().isoformat()
                })\
                .eq("id", job["id"])\
                .execute()
            
            logger.warning(f"Marked stuck job {job['id']} as failed")
        
        return {"stuck_jobs": len(stuck_jobs.data)}
        
    except Exception as e:
        logger.error(f"Stuck job monitoring failed: {e}")
        raise


@celery_app.task(name="evaluation_tasks.generate_daily_reports")
@run_async_task
async def generate_daily_reports():
    """Generate daily evaluation reports."""
    try:
        supabase = await get_supabase_client()
        
        # Calculate date range for yesterday
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        start_date = datetime.combine(yesterday, datetime.min.time())
        end_date = datetime.combine(yesterday, datetime.max.time())
        
        # Get daily statistics
        stats_query = """
        SELECT 
            COUNT(DISTINCT ej.id) as total_jobs,
            COUNT(DISTINCT ej.created_by) as active_users,
            COUNT(er.id) as total_evaluations,
            AVG(CAST(er.metrics_scores->>'overall_score' AS DECIMAL)) as avg_score,
            SUM(er.token_usage) as total_tokens,
            AVG(er.response_time_ms) as avg_response_time
        FROM evaluation_jobs ej
        LEFT JOIN evaluation_results er ON ej.id = er.job_id
        WHERE ej.created_at >= %s AND ej.created_at <= %s
        """
        
        # Note: This would need to be adapted for Supabase's specific SQL execution method
        # For now, we'll use a simpler approach
        
        jobs_result = await supabase.table("evaluation_jobs")\
            .select("id, created_by")\
            .gte("created_at", start_date.isoformat())\
            .lte("created_at", end_date.isoformat())\
            .execute()
        
        jobs = jobs_result.data or []
        
        # Generate report
        daily_report = {
            "date": yesterday.isoformat(),
            "total_jobs": len(jobs),
            "active_users": len(set(job["created_by"] for job in jobs)),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store report
        await supabase.table("daily_evaluation_reports")\
            .insert(daily_report)\
            .execute()
        
        logger.info(f"Generated daily report for {yesterday}")
        return daily_report
        
    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")
        raise


@celery_app.task(name="evaluation_tasks.cleanup_old_results")
@run_async_task
async def cleanup_old_results():
    """Clean up old evaluation results to manage database size."""
    try:
        supabase = await get_supabase_client()
        
        # Delete results older than 90 days
        cutoff_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        
        result = await supabase.table("evaluation_results")\
            .delete()\
            .lt("created_at", cutoff_date)\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"Cleaned up {deleted_count} old evaluation results")
        
        return {"deleted_results": deleted_count}
        
    except Exception as e:
        logger.error(f"Old results cleanup failed: {e}")
        raise


@celery_app.task(name="evaluation_tasks.update_model_performance_cache")
@run_async_task
async def update_model_performance_cache(
    model_name: str,
    dataset_id: Optional[str] = None,
    days_back: int = 7
):
    """Update model performance cache for dashboard optimization."""
    try:
        supabase = await get_supabase_client()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Build query
        query = supabase.table("evaluation_results")\
            .select("*")\
            .eq("model_name", model_name)\
            .gte("created_at", start_date.isoformat())\
            .lte("created_at", end_date.isoformat())
        
        if dataset_id:
            # Join with jobs to filter by dataset
            query = query.in_("job_id", 
                supabase.table("evaluation_jobs")
                .select("id")
                .eq("dataset_id", dataset_id)
            )
        
        result = await query.execute()
        results = result.data or []
        
        if not results:
            return {"model": model_name, "cached_results": 0}
        
        # Calculate performance metrics
        total_evaluations = len(results)
        successful_results = [r for r in results if not r.get("error_message")]
        
        if not successful_results:
            return {"model": model_name, "cached_results": 0}
        
        avg_response_time = sum(r["response_time_ms"] for r in successful_results) / len(successful_results)
        total_tokens = sum(r["token_usage"] for r in results)
        
        # Calculate average metrics
        metrics_sum = {}
        for result in successful_results:
            metrics = json.loads(result["metrics_scores"])
            for metric_name, score in metrics.items():
                if isinstance(score, (int, float)):
                    if metric_name not in metrics_sum:
                        metrics_sum[metric_name] = []
                    metrics_sum[metric_name].append(score)
        
        metrics_breakdown = {}
        for metric_name, scores in metrics_sum.items():
            metrics_breakdown[f"avg_{metric_name}"] = sum(scores) / len(scores)
        
        # Estimate cost (simplified)
        cost_usd = total_tokens * 0.00002  # Rough estimate
        
        # Store in cache
        cache_data = {
            "model_name": model_name,
            "dataset_id": dataset_id,
            "date_range_start": start_date.isoformat(),
            "date_range_end": end_date.isoformat(),
            "total_evaluations": total_evaluations,
            "avg_overall_score": metrics_breakdown.get("avg_overall_score"),
            "avg_response_time": avg_response_time,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "metrics_breakdown": metrics_breakdown,
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        # Upsert cache entry
        await supabase.table("model_performance_cache")\
            .upsert(cache_data)\
            .execute()
        
        logger.info(f"Updated performance cache for model {model_name}")
        return {"model": model_name, "cached_results": total_evaluations}
        
    except Exception as e:
        logger.error(f"Performance cache update failed for {model_name}: {e}")
        raise


@celery_app.task(name="evaluation_tasks.warm_up_caches")
@run_async_task
async def warm_up_caches():
    """Warm up performance caches for popular models and datasets."""
    try:
        supabase = await get_supabase_client()
        
        # Get top models by usage
        models_result = await supabase.table("evaluation_results")\
            .select("model_name")\
            .gte("created_at", (datetime.utcnow() - timedelta(days=7)).isoformat())\
            .execute()
        
        if not models_result.data:
            return {"warmed_models": 0}
        
        # Count model usage
        model_counts = {}
        for result in models_result.data:
            model_name = result["model_name"]
            model_counts[model_name] = model_counts.get(model_name, 0) + 1
        
        # Get top 5 models
        top_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Warm up cache for each model
        warmed_count = 0
        for model_name, _ in top_models:
            try:
                await update_model_performance_cache.delay(model_name)
                warmed_count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for {model_name}: {e}")
        
        logger.info(f"Warmed up {warmed_count} model caches")
        return {"warmed_models": warmed_count}
        
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")
        raise


# Task routing configuration
celery_app.conf.task_routes = {
    "evaluation_tasks.process_evaluation_job": {"queue": "evaluation"},
    "evaluation_tasks.batch_evaluate_prompts": {"queue": "batch"},
    "evaluation_tasks.schedule_ab_test": {"queue": "ab_tests"},
    "evaluation_tasks.stop_ab_test": {"queue": "ab_tests"},
    "evaluation_tasks.generate_ab_test_report": {"queue": "reports"},
    "evaluation_tasks.cleanup_expired_cache": {"queue": "maintenance"},
    "evaluation_tasks.monitor_stuck_jobs": {"queue": "monitoring"},
    "evaluation_tasks.generate_daily_reports": {"queue": "reports"},
    "evaluation_tasks.cleanup_old_results": {"queue": "maintenance"},
    "evaluation_tasks.update_model_performance_cache": {"queue": "cache"},
    "evaluation_tasks.warm_up_caches": {"queue": "cache"},
}

# Export the Celery app
__all__ = ["celery_app"]