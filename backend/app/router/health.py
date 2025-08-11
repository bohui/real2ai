"""Health check and WebSocket router."""

from fastapi import APIRouter
from datetime import datetime, timezone
import logging
from typing import Dict, Any

from app.core.config import get_settings
from app.core.langsmith_init import get_langsmith_status
from app.services.communication.redis_pubsub import redis_pubsub_service
from app.clients.factory import get_supabase_client
from app.database.connection import ConnectionPoolManager

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
    
    # Check JWT configuration status
    try:
        from app.core.auth import validate_jwt_configuration
        jwt_validation = validate_jwt_configuration()
        
        jwt_health = {
            "status": "healthy" if jwt_validation["status"] == "valid" else jwt_validation["status"],
            "environment": jwt_validation["environment"],
            "is_production": jwt_validation["is_production"],
            "has_secret_configured": bool(settings.jwt_secret_key),
            "algorithm": settings.jwt_algorithm
        }
        
        if jwt_validation["status"] != "valid":
            jwt_health["issues"] = jwt_validation.get("issues", [])
            jwt_health["warnings"] = jwt_validation.get("warnings", [])
            jwt_health["recommendations"] = jwt_validation.get("recommendations", [])
            
            # If JWT config is critical, mark overall health as degraded
            if jwt_validation["status"] == "critical":
                health_status["status"] = "degraded"
        
        health_status["services"]["jwt_configuration"] = jwt_health
        
    except Exception as e:
        health_status["services"]["jwt_configuration"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check task recovery system
    try:
        from app.services.recovery_monitor import recovery_monitor
        recovery_health = await recovery_monitor.get_recovery_health_status()
        health_status["services"]["task_recovery"] = recovery_health
        
        if recovery_health.get("overall_health") in ["degraded", "critical"]:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["services"]["task_recovery"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/recovery")
async def recovery_health_check() -> Dict[str, Any]:
    """Task recovery system health check"""
    try:
        from app.services.recovery_monitor import recovery_monitor
        return await recovery_monitor.get_recovery_health_status()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health/recovery/metrics")
async def recovery_metrics() -> Dict[str, Any]:
    """Task recovery system detailed metrics"""
    try:
        from app.services.recovery_monitor import recovery_monitor
        return await recovery_monitor.get_recovery_metrics()
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """Database connection pool health and metrics"""
    try:
        # Get pool metrics
        metrics = ConnectionPoolManager.get_metrics()
        
        # Calculate derived metrics
        total_pools = metrics["active_user_pools"] + (1 if hasattr(ConnectionPoolManager, '_service_pool') and ConnectionPoolManager._service_pool else 0)
        hit_rate = 0
        if metrics["pool_hits"] + metrics["pool_misses"] > 0:
            hit_rate = metrics["pool_hits"] / (metrics["pool_hits"] + metrics["pool_misses"])
        
        # Determine health status
        status = "healthy"
        issues = []
        
        # Check for potential issues
        if hit_rate < 0.8:  # Less than 80% hit rate
            status = "degraded"
            issues.append(f"Low pool hit rate: {hit_rate:.1%}")
        
        if metrics["active_user_pools"] >= settings.db_max_active_user_pools * 0.9:  # Near capacity
            status = "degraded" 
            issues.append(f"Pool capacity near limit: {metrics['active_user_pools']}/{settings.db_max_active_user_pools}")
        
        if metrics["evictions"] > 100:  # High eviction count
            issues.append(f"High eviction count: {metrics['evictions']}")
        
        health_info = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_mode": settings.db_pool_mode,
            "configuration": {
                "max_active_user_pools": settings.db_max_active_user_pools,
                "user_pool_min_size": settings.db_user_pool_min_size,
                "user_pool_max_size": settings.db_user_pool_max_size,
                "user_pool_idle_ttl_seconds": settings.db_user_pool_idle_ttl_seconds,
                "eviction_policy": settings.db_pool_eviction_policy
            },
            "metrics": {
                "active_user_pools": metrics["active_user_pools"],
                "total_pools": total_pools,
                "pool_hits": metrics["pool_hits"],
                "pool_misses": metrics["pool_misses"],
                "evictions": metrics["evictions"],
                "hit_rate": f"{hit_rate:.1%}",
                "hit_rate_decimal": round(hit_rate, 3)
            }
        }
        
        if issues:
            health_info["issues"] = issues
        
        return health_info
        
    except Exception as e:
        logger.exception("Database health check failed")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/metrics/database")
async def database_metrics() -> Dict[str, Any]:
    """Database connection pool metrics for monitoring systems"""
    try:
        metrics = ConnectionPoolManager.get_metrics()
        
        # Calculate additional metrics
        hit_rate = 0
        if metrics["pool_hits"] + metrics["pool_misses"] > 0:
            hit_rate = metrics["pool_hits"] / (metrics["pool_hits"] + metrics["pool_misses"])
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_mode": settings.db_pool_mode,
            "active_user_pools": metrics["active_user_pools"],
            "max_active_user_pools": settings.db_max_active_user_pools,
            "pool_utilization": metrics["active_user_pools"] / settings.db_max_active_user_pools,
            "pool_hits": metrics["pool_hits"],
            "pool_misses": metrics["pool_misses"],
            "evictions": metrics["evictions"],
            "hit_rate": hit_rate,
            "configuration": {
                "user_pool_min_size": settings.db_user_pool_min_size,
                "user_pool_max_size": settings.db_user_pool_max_size,
                "user_pool_idle_ttl_seconds": settings.db_user_pool_idle_ttl_seconds,
                "eviction_policy": settings.db_pool_eviction_policy
            }
        }
        
    except Exception as e:
        logger.exception("Database metrics collection failed")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
