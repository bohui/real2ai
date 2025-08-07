"""
Production Monitoring and Observability for LLM Evaluation System.

Comprehensive monitoring including:
- Performance metrics and alerting
- Health checks and system status
- Error tracking and logging
- Resource usage monitoring
- Business metrics and KPIs
"""

import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from contextlib import asynccontextmanager

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from app.core.config import get_settings
from app.clients.factory import get_supabase_client
from app.core.langsmith_config import get_langsmith_config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("evaluation_monitoring")

# Prometheus Metrics
EVALUATION_JOBS_TOTAL = Counter(
    "evaluation_jobs_total",
    "Total number of evaluation jobs",
    ["status", "user_id", "model"]
)

EVALUATION_DURATION = Histogram(
    "evaluation_job_duration_seconds",
    "Time spent on evaluation jobs",
    ["status", "model", "dataset_size"],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]  # 1s to 1h
)

EVALUATION_RESULTS_TOTAL = Counter(
    "evaluation_results_total", 
    "Total number of evaluation results",
    ["model", "status", "metric_quality"]
)

MODEL_PERFORMANCE_SCORE = Gauge(
    "model_performance_score",
    "Current model performance score",
    ["model", "metric", "dataset"]
)

API_REQUEST_DURATION = Histogram(
    "api_request_duration_seconds",
    "Time spent on API requests",
    ["method", "endpoint", "status_code"]
)

API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total number of API requests", 
    ["method", "endpoint", "status_code"]
)

ACTIVE_EVALUATION_JOBS = Gauge(
    "active_evaluation_jobs",
    "Number of currently active evaluation jobs"
)

QUEUE_SIZE = Gauge(
    "evaluation_queue_size", 
    "Number of jobs in evaluation queue",
    ["priority"]
)

TOKEN_USAGE_TOTAL = Counter(
    "token_usage_total",
    "Total tokens used",
    ["model", "operation_type"]
)

ERROR_COUNT = Counter(
    "evaluation_errors_total",
    "Total number of evaluation errors",
    ["error_type", "component", "severity"]
)

SYSTEM_INFO = Info(
    "evaluation_system",
    "Information about the evaluation system"
)


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    title: str
    description: str
    component: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class EvaluationMonitor:
    """Production monitoring system for LLM evaluation."""
    
    def __init__(self):
        self.settings = get_settings()
        self.active_alerts: Dict[str, Alert] = {}
        self.metrics_enabled = True
        self.health_checks = {}
        
        # Initialize OpenTelemetry
        self._init_telemetry()
        
        # Start Prometheus metrics server
        if self.settings.prometheus_port:
            start_http_server(self.settings.prometheus_port)
            logger.info(f"Started Prometheus metrics server on port {self.settings.prometheus_port}")
    
    def _init_telemetry(self):
        """Initialize OpenTelemetry tracing and metrics."""
        # Set up tracing
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer("evaluation_system")
        
        # Set up metrics
        metrics.set_meter_provider(MeterProvider())
        self.meter = metrics.get_meter("evaluation_system")
        
        # Update system info
        SYSTEM_INFO.info({
            "version": self.settings.app_version or "unknown",
            "environment": self.settings.environment or "development",
            "langsmith_enabled": str(get_langsmith_config().enabled)
        })
    
    async def record_job_started(
        self, 
        job_id: str, 
        user_id: str, 
        model_configs: List[Dict[str, Any]],
        dataset_size: int
    ):
        """Record when an evaluation job starts."""
        ACTIVE_EVALUATION_JOBS.inc()
        
        for config in model_configs:
            model_name = config.get("model_name", "unknown")
            EVALUATION_JOBS_TOTAL.labels(
                status="started",
                user_id=user_id[:8],  # Truncate for privacy
                model=model_name
            ).inc()
        
        logger.info(
            "evaluation_job_started",
            job_id=job_id,
            user_id=user_id[:8],
            models=[c.get("model_name") for c in model_configs],
            dataset_size=dataset_size
        )
    
    async def record_job_completed(
        self,
        job_id: str,
        user_id: str,
        model_configs: List[Dict[str, Any]],
        duration_seconds: float,
        dataset_size: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Record when an evaluation job completes."""
        ACTIVE_EVALUATION_JOBS.dec()
        
        # Categorize dataset size for metrics
        if dataset_size <= 10:
            size_category = "small"
        elif dataset_size <= 100:
            size_category = "medium"
        else:
            size_category = "large"
        
        for config in model_configs:
            model_name = config.get("model_name", "unknown")
            
            EVALUATION_JOBS_TOTAL.labels(
                status=status,
                user_id=user_id[:8],
                model=model_name
            ).inc()
            
            EVALUATION_DURATION.labels(
                status=status,
                model=model_name,
                dataset_size=size_category
            ).observe(duration_seconds)
        
        log_data = {
            "job_id": job_id,
            "user_id": user_id[:8],
            "models": [c.get("model_name") for c in model_configs],
            "duration_seconds": duration_seconds,
            "dataset_size": dataset_size,
            "status": status
        }
        
        if error_message:
            log_data["error_message"] = error_message
            ERROR_COUNT.labels(
                error_type="job_failure",
                component="orchestrator",
                severity="medium"
            ).inc()
        
        logger.info("evaluation_job_completed", **log_data)
    
    async def record_evaluation_result(
        self,
        job_id: str,
        model_name: str,
        metrics_scores: Dict[str, float],
        response_time_ms: int,
        token_usage: int,
        error_message: Optional[str] = None
    ):
        """Record individual evaluation result metrics."""
        status = "error" if error_message else "success"
        
        # Determine metric quality
        overall_score = metrics_scores.get("overall_score", 0.0)
        if overall_score >= 0.8:
            metric_quality = "high"
        elif overall_score >= 0.6:
            metric_quality = "medium" 
        else:
            metric_quality = "low"
        
        EVALUATION_RESULTS_TOTAL.labels(
            model=model_name,
            status=status,
            metric_quality=metric_quality
        ).inc()
        
        TOKEN_USAGE_TOTAL.labels(
            model=model_name,
            operation_type="evaluation"
        ).inc(token_usage)
        
        # Update model performance gauges
        for metric_name, score in metrics_scores.items():
            if isinstance(score, (int, float)):
                MODEL_PERFORMANCE_SCORE.labels(
                    model=model_name,
                    metric=metric_name,
                    dataset="current"  # Could be made more specific
                ).set(score)
        
        if error_message:
            ERROR_COUNT.labels(
                error_type="evaluation_failure",
                component="metrics_calculator",
                severity="low"
            ).inc()
        
        logger.info(
            "evaluation_result_recorded",
            job_id=job_id,
            model=model_name,
            overall_score=overall_score,
            response_time_ms=response_time_ms,
            token_usage=token_usage,
            status=status
        )
    
    async def record_api_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        user_id: Optional[str] = None
    ):
        """Record API request metrics."""
        API_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        API_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration_seconds)
        
        logger.info(
            "api_request",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_seconds=duration_seconds,
            user_id=user_id[:8] if user_id else None
        )
    
    async def update_queue_metrics(self):
        """Update queue size metrics."""
        try:
            supabase = await get_supabase_client()
            
            # Get queue sizes by priority
            for priority in range(1, 11):
                result = await supabase.table("evaluation_queue")\
                    .select("id", count="exact")\
                    .eq("priority", priority)\
                    .is_("claimed_at", "null")\
                    .execute()
                
                queue_size = result.count or 0
                QUEUE_SIZE.labels(priority=str(priority)).set(queue_size)
            
        except Exception as e:
            logger.error("Failed to update queue metrics", error=str(e))
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        try:
            # Database connectivity
            health_status["checks"]["database"] = await self._check_database_health()
            
            # LangSmith connectivity
            health_status["checks"]["langsmith"] = await self._check_langsmith_health()
            
            # Queue health
            health_status["checks"]["queue"] = await self._check_queue_health()
            
            # AI clients health
            health_status["checks"]["ai_clients"] = await self._check_ai_clients_health()
            
            # Resource usage
            health_status["checks"]["resources"] = await self._check_resource_health()
            
            # Determine overall status
            failed_checks = [
                name for name, check in health_status["checks"].items() 
                if not check.get("healthy", False)
            ]
            
            if failed_checks:
                health_status["status"] = "unhealthy"
                health_status["failed_checks"] = failed_checks
                
                # Create alerts for failed checks
                await self._create_health_alerts(failed_checks)
            
        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
            logger.error("Health check failed", error=str(e))
        
        return health_status
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            supabase = await get_supabase_client()
            
            # Simple query to test connectivity
            result = await supabase.table("evaluation_jobs")\
                .select("id")\
                .limit(1)\
                .execute()
            
            query_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "healthy": True,
                "query_time_ms": query_time,
                "responsive": query_time < 1000  # Less than 1 second
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_langsmith_health(self) -> Dict[str, Any]:
        """Check LangSmith connectivity."""
        config = get_langsmith_config()
        
        if not config.enabled:
            return {
                "healthy": True,
                "enabled": False,
                "status": "disabled"
            }
        
        try:
            # Simple health check for LangSmith
            client = config.client
            if client:
                # This would be a real health check in production
                return {
                    "healthy": True,
                    "enabled": True,
                    "project": config.project_name
                }
            else:
                return {
                    "healthy": False,
                    "enabled": True,
                    "error": "Client not initialized"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "enabled": True,
                "error": str(e)
            }
    
    async def _check_queue_health(self) -> Dict[str, Any]:
        """Check evaluation queue health."""
        try:
            supabase = await get_supabase_client()
            
            # Check for stuck jobs in queue
            stuck_threshold = datetime.utcnow() - timedelta(hours=1)
            stuck_jobs = await supabase.table("evaluation_queue")\
                .select("id", count="exact")\
                .is_not("claimed_at", "null")\
                .lt("claimed_at", stuck_threshold.isoformat())\
                .execute()
            
            stuck_count = stuck_jobs.count or 0
            
            # Check queue size
            queue_result = await supabase.table("evaluation_queue")\
                .select("id", count="exact")\
                .is_("claimed_at", "null")\
                .execute()
            
            queue_size = queue_result.count or 0
            
            return {
                "healthy": stuck_count == 0,
                "queue_size": queue_size,
                "stuck_jobs": stuck_count,
                "warning": stuck_count > 0
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_ai_clients_health(self) -> Dict[str, Any]:
        """Check AI clients health."""
        # This would integrate with the existing client health checks
        # For now, return a placeholder
        return {
            "healthy": True,
            "openai": {"status": "unknown"},
            "gemini": {"status": "unknown"},
            "note": "Client health checks not implemented"
        }
    
    async def _check_resource_health(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "healthy": cpu_percent < 80 and memory.percent < 80,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "warnings": [
                    f"High CPU usage: {cpu_percent}%" if cpu_percent > 70 else None,
                    f"High memory usage: {memory.percent}%" if memory.percent > 70 else None,
                    f"High disk usage: {disk.percent}%" if disk.percent > 80 else None
                ]
            }
            
        except ImportError:
            return {
                "healthy": True,
                "status": "psutil not available",
                "note": "Install psutil for resource monitoring"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _create_health_alerts(self, failed_checks: List[str]):
        """Create alerts for failed health checks."""
        for check_name in failed_checks:
            alert_id = f"health_check_{check_name}"
            
            if alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    severity=AlertSeverity.HIGH,
                    title=f"Health Check Failed: {check_name}",
                    description=f"The {check_name} health check is failing",
                    component=check_name,
                    timestamp=datetime.utcnow(),
                    metadata={"check_name": check_name}
                )
                
                self.active_alerts[alert_id] = alert
                await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Send alert notification."""
        # In production, this would integrate with alerting systems
        # like PagerDuty, Slack, email, etc.
        
        logger.warning(
            "alert_triggered",
            alert_id=alert.id,
            severity=alert.severity.value,
            title=alert.title,
            description=alert.description,
            component=alert.component,
            timestamp=alert.timestamp.isoformat()
        )
        
        # Could also store alerts in database for dashboard
        try:
            supabase = await get_supabase_client()
            await supabase.table("system_alerts").insert({
                "id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "component": alert.component,
                "metadata": alert.metadata,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            }).execute()
        except Exception as e:
            logger.error("Failed to store alert", error=str(e))
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            logger.info(
                "alert_resolved",
                alert_id=alert_id,
                resolved_at=alert.resolved_at.isoformat()
            )
            
            # Update in database
            try:
                supabase = await get_supabase_client()
                await supabase.table("system_alerts")\
                    .update({
                        "resolved": True,
                        "resolved_at": alert.resolved_at.isoformat()
                    })\
                    .eq("id", alert_id)\
                    .execute()
            except Exception as e:
                logger.error("Failed to update resolved alert", error=str(e))
            
            del self.active_alerts[alert_id]
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary for dashboard."""
        try:
            supabase = await get_supabase_client()
            
            # Recent jobs (last 24 hours)
            recent_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
            
            jobs_result = await supabase.table("evaluation_jobs")\
                .select("status", count="exact")\
                .gte("created_at", recent_time)\
                .execute()
            
            # Group by status
            status_counts = {}
            if jobs_result.data:
                for job in jobs_result.data:
                    status = job["status"]
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            # Recent results
            results_result = await supabase.table("evaluation_results")\
                .select("model_name, metrics_scores")\
                .gte("created_at", recent_time)\
                .execute()
            
            model_scores = {}
            if results_result.data:
                for result in results_result.data:
                    model = result["model_name"]
                    scores = json.loads(result["metrics_scores"])
                    overall_score = scores.get("overall_score", 0)
                    
                    if model not in model_scores:
                        model_scores[model] = []
                    model_scores[model].append(overall_score)
            
            # Calculate averages
            model_averages = {
                model: sum(scores) / len(scores) if scores else 0
                for model, scores in model_scores.items()
            }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "jobs_last_24h": {
                    "total": sum(status_counts.values()),
                    "by_status": status_counts
                },
                "model_performance": model_averages,
                "active_alerts": len(self.active_alerts),
                "system_status": "healthy" if not self.active_alerts else "degraded"
            }
            
        except Exception as e:
            logger.error("Failed to get metrics summary", error=str(e))
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }


# Global monitor instance
_monitor: Optional["EvaluationMonitor"] = None


def get_monitor() -> EvaluationMonitor:
    """Get global monitoring instance."""
    global _monitor
    if _monitor is None:
        _monitor = EvaluationMonitor()
    return _monitor


@asynccontextmanager
async def monitor_request(method: str, endpoint: str, user_id: Optional[str] = None):
    """Context manager for monitoring API requests."""
    start_time = time.time()
    status_code = 200
    
    try:
        yield
    except Exception as e:
        status_code = 500
        logger.error("Request failed", method=method, endpoint=endpoint, error=str(e))
        raise
    finally:
        duration = time.time() - start_time
        monitor = get_monitor()
        await monitor.record_api_request(method, endpoint, status_code, duration, user_id)


@asynccontextmanager  
async def monitor_evaluation_job(
    job_id: str, 
    user_id: str, 
    model_configs: List[Dict[str, Any]], 
    dataset_size: int
):
    """Context manager for monitoring evaluation jobs."""
    monitor = get_monitor()
    start_time = time.time()
    
    await monitor.record_job_started(job_id, user_id, model_configs, dataset_size)
    
    status = "completed"
    error_message = None
    
    try:
        yield
    except Exception as e:
        status = "failed"
        error_message = str(e)
        raise
    finally:
        duration = time.time() - start_time
        await monitor.record_job_completed(
            job_id, user_id, model_configs, duration, dataset_size, status, error_message
        )


# Export public interface
__all__ = [
    "EvaluationMonitor",
    "get_monitor", 
    "monitor_request",
    "monitor_evaluation_job",
    "Alert",
    "AlertSeverity"
]