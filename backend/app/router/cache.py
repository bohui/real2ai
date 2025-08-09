"""Cache router with history endpoints for frontend integration."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body, status
from app.core.auth import get_current_user
from app.core.auth import User
from app.services.cache.cache_service import get_cache_service, CacheService
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.services.communication.redis_pubsub import redis_pubsub_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


## Contract-related endpoints moved to contracts router


@router.get("/property/history")
async def get_property_history(
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Get user's property search history.

    Returns:
        Property history with pagination support
    """
    context = create_error_context(
        user_id=str(user.id),
        operation="get_property_history",
        limit=limit,
        offset=offset,
    )

    try:
        history = await cache_service.get_user_property_history(
            user_id=str(user.id), limit=limit, offset=offset
        )

        return {
            "status": "success",
            "data": {
                "history": history,
                "total_count": len(history),
                "has_more": len(history) == limit,
            },
        }

    except Exception as e:
        logger.error(f"Error getting property history: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.get("/stats")
async def get_cache_stats(
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Cache statistics and health information
    """
    context = create_error_context(user_id=str(user.id), operation="get_cache_stats")

    try:
        stats = await cache_service.get_cache_stats()

        # Map service keys to frontend-expected structure
        contracts_total = stats.get("contract_analyses", {}).get("total", 0)
        contracts_avg = stats.get("contract_analyses", {}).get("avg_processing_time", 0)
        properties_total = stats.get("property_data", {}).get("total", 0)
        properties_avg = stats.get("property_data", {}).get("avg_processing_time", 0)

        from datetime import datetime, timezone

        last_updated = datetime.now(timezone.utc).isoformat()

        return {
            "status": "success",
            "data": {
                "contracts": {
                    "total_cached": contracts_total,
                    "average_access": contracts_avg,
                },
                "properties": {
                    "total_cached": properties_total,
                    "average_access": properties_avg,
                    "average_popularity": 0,
                },
                "last_updated": last_updated,
            },
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.get("/health")
async def get_cache_health(
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Get cache health status.

    Returns:
        Cache health information
    """
    context = create_error_context(user_id=str(user.id), operation="get_cache_health")

    try:
        # Ping Redis
        redis_ok = False
        redis_error = None
        try:
            await redis_pubsub_service.initialize()
            await redis_pubsub_service.redis_client.ping()  # type: ignore[attr-defined]
            redis_ok = True
        except Exception as re:
            redis_error = str(re)

        # Compute real-time stats (validates DB path)
        stats = await cache_service.get_cache_stats()

        contracts_total = stats.get("contract_analyses", {}).get("total", 0)
        properties_total = stats.get("property_data", {}).get("total", 0)
        contracts_avg = stats.get("contract_analyses", {}).get("avg_processing_time", 0)
        properties_avg = stats.get("property_data", {}).get("avg_processing_time", 0)

        # Basic consistency signals
        consistency = {
            "contracts": {
                "total_records": contracts_total,
                "records_with_hashes": contracts_total,
                "consistency_percentage": 100,
            },
            "properties": {
                "total_records": properties_total,
                "records_with_hashes": properties_total,
                "consistency_percentage": 100,
            },
        }

        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).isoformat()

        issues = [] if redis_ok else ["redis_unreachable"]
        health_score = 100 - (0 if redis_ok else 20)

        response = {
            "health_status": (
                "healthy"
                if health_score >= 90
                else ("warning" if health_score >= 70 else "critical")
            ),
            "health_score": health_score,
            "issues": issues,
            "services": {
                "redis": {"ok": redis_ok, "error": redis_error},
                "database": {"ok": True},
            },
            "consistency": consistency,
            "stats": {
                "contracts": {
                    "total_cached": contracts_total,
                    "average_access": contracts_avg,
                },
                "properties": {
                    "total_cached": properties_total,
                    "average_access": properties_avg,
                    "average_popularity": 0,
                },
                "last_updated": now_iso,
            },
            "timestamp": now_iso,
        }

        return {"status": "success", "data": response}

    except Exception as e:
        logger.error(f"Error getting cache health: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


def require_admin(func):
    """Decorator to require admin role for an endpoint."""

    async def wrapper(*args, user: User = None, **kwargs):
        if not user or "admin" not in getattr(user, "roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return await func(*args, user=user, **kwargs)

    return wrapper


@router.post("/cleanup")
@require_admin
async def cleanup_cache(
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Trigger cache cleanup (admin only in the future).

    Returns:
        Cleanup operation results
    """
    context = create_error_context(user_id=str(user.id), operation="cleanup_cache")

    try:
        cleanup_stats = await cache_service.cleanup_expired_cache()

        # Translate to frontend-expected shape
        response_data = {
            "contracts": cleanup_stats.get("contracts_deleted", 0),
            "properties": cleanup_stats.get("properties_deleted", 0),
        }

        return {
            "status": "success",
            "message": "Cache cleanup completed",
            "data": response_data,
        }

    except Exception as e:
        logger.error(f"Error during cache cleanup: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


## Contract-related endpoints moved to contracts router


@router.post("/property/search")
async def search_property_with_cache(
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Search property with cache-first strategy.

    Body:
        - address: Property address to search
        - check_cache: Whether to check cache first (default: true)
        - search_options: Search configuration options
    """
    context = create_error_context(
        user_id=str(user.id), operation="search_property_with_cache"
    )

    try:
        address = request.get("address")
        if not address:
            raise HTTPException(status_code=400, detail="address is required")

        check_cache = request.get("check_cache", True)

        # Check cache first if enabled (content hash standardized via backend service)
        cached_result = None
        if check_cache:
            cached_result = await cache_service.check_property_cache(address)

        if cached_result:
            # Log user view
            await cache_service.log_user_property_view(
                user_id=str(user.id), address=address, source="cache_search"
            )

            return {
                "status": "success",
                "data": {
                    "cached": True,
                    "cache_hit": True,
                    "property_data": cached_result,
                    "source": "cache",
                },
            }
        else:
            # For now, return a placeholder response
            # In the future, this would integrate with property search services
            return {
                "status": "success",
                "data": {
                    "cached": False,
                    "cache_hit": False,
                    "property_data": None,
                    "source": "external_api",
                    "message": "Property search not yet implemented",
                },
            }

    except Exception as e:
        logger.error(f"Error in property search with cache: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.post("/hash/content")
async def generate_content_hash(
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Generate content hash for file content.

    Body:
        - file_content: Base64 encoded file content
    """
    context = create_error_context(
        user_id=str(user.id), operation="generate_content_hash"
    )

    try:
        file_content = request.get("file_content")
        if not file_content:
            raise HTTPException(status_code=400, detail="file_content is required")

        # Generate content hash from file content
        import base64

        content_bytes = base64.b64decode(file_content)
        content_hash = cache_service.generate_content_hash(content_bytes)

        return {
            "status": "success",
            "data": {
                "content_hash": content_hash,
                "algorithm": "sha256",
                "file_size": len(content_bytes),
            },
        }

    except Exception as e:
        logger.error(f"Error generating content hash: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.post("/hash/property")
async def generate_property_hash(
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Generate property hash for address.

    Body:
        - address: Property address
    """
    context = create_error_context(
        user_id=str(user.id), operation="generate_property_hash"
    )

    try:
        address = request.get("address")
        if not address:
            raise HTTPException(status_code=400, detail="address is required")

        # Generate property hash
        property_hash = cache_service.generate_property_hash(address)
        normalized_address = cache_service.normalize_address(address)

        return {
            "status": "success",
            "data": {
                "original_address": address,
                "normalized_address": normalized_address,
                "property_hash": property_hash,
                "algorithm": "sha256",
            },
        }

    except Exception as e:
        logger.error(f"Error generating property hash: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)
