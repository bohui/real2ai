"""Health check and WebSocket router."""

from fastapi import APIRouter
from datetime import datetime, timezone
import logging
from typing import Dict, Any

from app.core.config import get_settings
from app.core.langsmith_init import get_langsmith_status
from app.services.redis_pubsub import redis_pubsub_service
from app.clients.factory import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Initialize services
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
    }


@router.get("/health/langsmith")
async def langsmith_health_check():
    """LangSmith health check endpoint"""
    langsmith_status = get_langsmith_status()
    
    return {
        "status": "healthy" if langsmith_status.get("enabled", False) else "disabled",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "langsmith": langsmith_status,
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Comprehensive health check for all backend services"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
        "services": {}
    }
    
    # Check Redis pub/sub service
    try:
        if hasattr(redis_pubsub_service, 'redis_client') and redis_pubsub_service.redis_client:
            await redis_pubsub_service.redis_client.ping()
            health_status["services"]["redis_pubsub"] = {
                "status": "healthy",
                "initialized": redis_pubsub_service._initialized,
                "active_subscriptions": len(redis_pubsub_service.subscriptions)
            }
        else:
            health_status["services"]["redis_pubsub"] = {
                "status": "not_initialized",
                "initialized": False,
                "active_subscriptions": 0
            }
    except Exception as e:
        health_status["services"]["redis_pubsub"] = {
            "status": "error",
            "error": str(e),
            "initialized": False
        }
        health_status["status"] = "degraded"
    
    # Check Supabase connection
    try:
        supabase_client = await get_supabase_client()
        # Test basic connection
        result = await supabase_client.execute_rpc("health_check", {})
        health_status["services"]["supabase"] = {
            "status": "healthy",
            "connection": "ok",
            "rpc_test": "passed"
        }
    except Exception as e:
        health_status["services"]["supabase"] = {
            "status": "error",
            "error": str(e),
            "connection": "failed"
        }
        health_status["status"] = "degraded"
    
    # Check storage bucket accessibility
    try:
        supabase_client = await get_supabase_client()
        result = await supabase_client.execute_rpc("ensure_bucket_exists", {"bucket_name": "documents"})
        health_status["services"]["storage"] = {
            "status": "healthy",
            "documents_bucket": "accessible",
            "bucket_check": "passed"
        }
    except Exception as e:
        health_status["services"]["storage"] = {
            "status": "error",
            "error": str(e),
            "documents_bucket": "inaccessible"
        }
        health_status["status"] = "degraded"
    
    # Add LangSmith status
    langsmith_status = get_langsmith_status()
    health_status["services"]["langsmith"] = {
        "status": "enabled" if langsmith_status.get("enabled", False) else "disabled",
        "details": langsmith_status
    }
    
    return health_status
