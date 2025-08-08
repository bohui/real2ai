"""
Celery configuration and app instance
Centralized Celery setup for the application
"""

from celery import Celery
from app.core.config import get_settings

# Get settings
settings = get_settings()

# Create Celery app instance
celery_app = Celery(
    "real2ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ocr_tasks",
        "app.tasks.background_tasks",
        "app.tasks.cleanup_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    # Connection resilience
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=100,
    result_backend_always_retry=True,
    task_routes={
        "app.tasks.ocr_tasks.process_document_ocr": {"queue": "ocr_queue"},
        "app.tasks.ocr_tasks.batch_process_documents": {"queue": "batch_queue"},
        "app.tasks.ocr_tasks.priority_ocr_processing": {"queue": "priority_queue"},
    },
    task_default_queue="default",
    task_create_missing_queues=True,
)

# Optional: Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    "health-check": {
        "task": "app.tasks.ocr_tasks.health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-failed-tasks": {
        "task": "app.tasks.ocr_tasks.cleanup_failed_tasks",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-orphaned-documents": {
        "task": "app.tasks.cleanup_tasks.cleanup_orphaned_documents",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "cleanup-failed-analyses": {
        "task": "app.tasks.cleanup_tasks.cleanup_failed_analyses",
        "schedule": 86400.0,  # Every 24 hours
    },
    "verify-storage-consistency": {
        "task": "app.tasks.cleanup_tasks.verify_storage_consistency",
        "schedule": 21600.0,  # Every 6 hours
    },
}
