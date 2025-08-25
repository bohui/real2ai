"""Database Performance Optimization Module for Real2.AI Platform.

This module provides optimized database query patterns and performance monitoring
for contract analysis operations. Implements the performance improvements to achieve
75% reduction in query response times (200-500ms → 50-100ms).

Key Optimizations:
- Consolidated queries (4 separate queries → 1 JOIN)
- Optimized access validation patterns
- Performance monitoring and metrics
- Query result caching
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from typing import TYPE_CHECKING
from app.services.repositories.analyses_repository import AnalysesRepository

# Avoid importing heavy client modules at runtime to prevent circular imports
# and optional dependency issues. Only import for type checking.
if TYPE_CHECKING:  # pragma: no cover - type-checking only
    from app.clients.supabase.client import (
        SupabaseClient as UserAuthenticatedClient,
    )
else:
    # At runtime, treat as Any to avoid import-time side effects
    UserAuthenticatedClient = Any  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for database queries."""

    query_name: str
    execution_time_ms: float
    rows_returned: int
    cache_hit: bool = False
    optimization_applied: bool = False

    def is_within_target(self, target_ms: float = 100.0) -> bool:
        """Check if query performance meets target."""
        return self.execution_time_ms <= target_ms


@dataclass
class UserAccessResult:
    """Result of user access validation with performance data."""

    contract_id: str
    content_hash: str
    has_access: bool
    access_source: str
    analysis_id: Optional[str] = None
    analysis_status: Optional[str] = None
    analysis_created_at: Optional[str] = None
    analysis_updated_at: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    analysis_metadata: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[QueryPerformanceMetrics] = None


class DatabaseOptimizer:
    """Database performance optimizer for contract operations."""

    def __init__(self):
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache
        self._performance_log: List[QueryPerformanceMetrics] = []
        self._enable_monitoring = True

    @asynccontextmanager
    async def performance_monitor(self, query_name: str):
        """Context manager for monitoring query performance."""
        start_time = time.perf_counter()
        rows_returned = 0
        cache_hit = False

        def set_metrics(rows: int = 0, cached: bool = False) -> None:
            nonlocal rows_returned, cache_hit
            rows_returned = rows
            cache_hit = cached

        try:
            yield set_metrics
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            metrics = QueryPerformanceMetrics(
                query_name=query_name,
                execution_time_ms=execution_time_ms,
                rows_returned=rows_returned,
                cache_hit=cache_hit,
                optimization_applied=True,
            )

            if self._enable_monitoring:
                self._performance_log.append(metrics)
                logger.info(
                    f"Query {query_name}: {execution_time_ms:.1f}ms, "
                    f"{rows_returned} rows, cached={cache_hit}"
                )

            # Log warning if performance target not met
            if not metrics.is_within_target():
                logger.warning(
                    f"Query {query_name} exceeded target: {execution_time_ms:.1f}ms > 100ms"
                )

    def _get_cache_key(self, operation: str, **params) -> str:
        """Generate cache key for operation and parameters."""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{operation}_{param_str}"

    def _is_cache_valid(self, cached_time: float) -> bool:
        """Check if cached result is still valid."""
        return time.time() - cached_time < self._cache_ttl_seconds

    async def get_user_contract_access_optimized(
        self,
        db_client: UserAuthenticatedClient,
        user_id: str,
        contract_id: str,
        use_cache: bool = True,
    ) -> UserAccessResult:
        """Optimized single query for user contract access validation.

        This replaces the original 4 separate queries:
        1. user_contract_views access check
        2. documents access check
        3. contracts existence check
        4. analyses status check

        With a single optimized database function call that uses JOINs and indexes.

        Args:
            db_client: Authenticated database client
            user_id: User UUID
            contract_id: Contract UUID
            use_cache: Whether to use query result caching

        Returns:
            UserAccessResult with all validation and analysis data

        Performance Target: <100ms (vs original 200-500ms)
        """

        cache_key = self._get_cache_key(
            "user_contract_access", user_id=user_id, contract_id=contract_id
        )

        # Check cache first
        if use_cache and cache_key in self._query_cache:
            result, cached_time = self._query_cache[cache_key]
            if self._is_cache_valid(cached_time):
                result.performance_metrics = QueryPerformanceMetrics(
                    query_name="get_user_contract_access_optimized",
                    execution_time_ms=1.0,  # Cache hit
                    rows_returned=1,
                    cache_hit=True,
                    optimization_applied=True,
                )
                return result

        async with self.performance_monitor(
            "get_user_contract_access_optimized"
        ) as set_metrics:
            try:
                # Single optimized query using the database function
                result = await db_client.database.execute_rpc(
                    "get_user_contract_access_optimized",
                    {"p_user_id": user_id, "p_contract_id": contract_id},
                )

                if not result or not result.get("data"):
                    set_metrics(0, False)
                    return UserAccessResult(
                        contract_id=contract_id,
                        content_hash="",
                        has_access=False,
                        access_source="none",
                    )

                # Parse the optimized result
                data = result["data"][0] if result["data"] else {}

                access_result = UserAccessResult(
                    contract_id=data.get("contract_id", contract_id),
                    content_hash=data.get("content_hash", ""),
                    has_access=data.get("has_access", False),
                    access_source=data.get("access_source", "none"),
                    analysis_id=data.get("analysis_id"),
                    analysis_status=data.get("analysis_status"),
                    analysis_created_at=data.get("analysis_created_at"),
                    analysis_updated_at=data.get("analysis_updated_at"),
                    processing_time=data.get("processing_time"),
                    error_message=data.get("error_message"),
                    analysis_metadata=data.get("analysis_metadata"),
                )

                set_metrics(1, False)

                # Cache successful result
                if use_cache and access_result.has_access:
                    self._query_cache[cache_key] = (access_result, time.time())

                return access_result

            except Exception as e:
                logger.error(f"Optimized query failed: {str(e)}")
                set_metrics(0, False)

                # Fallback to original pattern if optimized query fails
                return await self._fallback_user_access_validation(
                    db_client, user_id, contract_id
                )

    async def _fallback_user_access_validation(
        self, db_client: UserAuthenticatedClient, user_id: str, contract_id: str
    ) -> UserAccessResult:
        """Fallback to original query pattern if optimized version fails."""

        async with self.performance_monitor(
            "fallback_user_access_validation"
        ) as set_metrics:
            try:
                # Original pattern: 4 separate queries (preserved for fallback)
                logger.warning(
                    "Using fallback query pattern - performance may be degraded"
                )

                # Query 1: user_contract_views
                access_result = (
                    db_client.table("user_contract_views")
                    .select("content_hash")
                    .eq("user_id", user_id)
                    .execute()
                )

                user_content_hashes = []
                if access_result.data:
                    user_content_hashes = [
                        view["content_hash"]
                        for view in access_result.data
                        if view.get("content_hash")
                    ]

                # Query 2: documents
                doc_access_result = (
                    db_client.table("documents")
                    .select("content_hash")
                    .eq("user_id", user_id)
                    .execute()
                )

                if doc_access_result.data:
                    doc_content_hashes = [
                        doc["content_hash"]
                        for doc in doc_access_result.data
                        if doc.get("content_hash")
                    ]
                    user_content_hashes.extend(doc_content_hashes)

                if not user_content_hashes:
                    set_metrics(0, False)
                    return UserAccessResult(
                        contract_id=contract_id,
                        content_hash="",
                        has_access=False,
                        access_source="none",
                    )

                # Remove duplicates
                user_content_hashes = list(set(user_content_hashes))

                # Query 3: contracts
                contract_result = (
                    db_client.table("contracts")
                    .select("id, content_hash")
                    .eq("id", contract_id)
                    .execute()
                )

                if not contract_result.data:
                    set_metrics(0, False)
                    return UserAccessResult(
                        contract_id=contract_id,
                        content_hash="",
                        has_access=False,
                        access_source="contract_not_found",
                    )

                contract = contract_result.data[0]
                content_hash = contract["content_hash"]

                # Verify access
                if content_hash not in user_content_hashes:
                    set_metrics(1, False)
                    return UserAccessResult(
                        contract_id=contract_id,
                        content_hash=content_hash,
                        has_access=False,
                        access_source="access_denied",
                    )

                # Query 4: analyses using repository
                analyses_repo = AnalysesRepository(use_service_role=True)
                analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)
                
                analysis_data = {}
                if analysis:
                    analysis_data = {
                        "id": str(analysis.id),
                        "status": analysis.status,
                        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
                        "error_message": analysis.error_details.get("error_message") if analysis.error_details else None,
                        "analysis_metadata": analysis.result,
                    }

                set_metrics(len(user_content_hashes), False)

                return UserAccessResult(
                    contract_id=contract_id,
                    content_hash=content_hash,
                    has_access=True,
                    access_source="fallback_validation",
                    analysis_id=analysis_data.get("id"),
                    analysis_status=analysis_data.get("status"),
                    analysis_created_at=analysis_data.get("created_at"),
                    analysis_updated_at=analysis_data.get("updated_at"),
                    processing_time=analysis_data.get("processing_time"),
                    error_message=analysis_data.get("error_message"),
                    analysis_metadata=analysis_data.get("analysis_metadata"),
                )

            except Exception as e:
                logger.error(f"Fallback validation failed: {str(e)}")
                set_metrics(0, False)
                raise ValueError(f"Database access validation failed: {str(e)}")

    async def get_user_contracts_bulk(
        self, db_client: UserAuthenticatedClient, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get bulk user contract access information with optimization."""

        async with self.performance_monitor("get_user_contracts_bulk") as set_metrics:
            try:
                result = await db_client.database.execute_rpc(
                    "get_user_contracts_bulk_access",
                    {"p_user_id": user_id, "p_limit": limit},
                )

                data = result.get("data", []) if result else []
                set_metrics(len(data), False)

                return data

            except Exception as e:
                logger.error(f"Bulk contract query failed: {str(e)}")
                set_metrics(0, False)
                return []

    async def get_performance_report(self, db_client: UserAuthenticatedClient) -> str:
        """Generate database performance report."""

        try:
            result = await db_client.database.execute_rpc(
                "generate_contract_performance_report", {}
            )

            return result if isinstance(result, str) else str(result)

        except Exception as e:
            logger.error(f"Performance report generation failed: {str(e)}")
            return f"Performance report unavailable: {str(e)}"

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for current session."""

        if not self._performance_log:
            return {"status": "no_data", "message": "No queries executed yet"}

        total_queries = len(self._performance_log)
        avg_time = (
            sum(m.execution_time_ms for m in self._performance_log) / total_queries
        )
        cache_hits = sum(1 for m in self._performance_log if m.cache_hit)
        within_target = sum(1 for m in self._performance_log if m.is_within_target())

        return {
            "total_queries": total_queries,
            "average_time_ms": round(avg_time, 2),
            "cache_hit_rate": round((cache_hits / total_queries) * 100, 2),
            "target_compliance_rate": round((within_target / total_queries) * 100, 2),
            "performance_status": (
                "excellent" if avg_time <= 100 else "needs_improvement"
            ),
            "recent_queries": [
                {
                    "query": m.query_name,
                    "time_ms": m.execution_time_ms,
                    "rows": m.rows_returned,
                    "cached": m.cache_hit,
                }
                for m in self._performance_log[-5:]  # Last 5 queries
            ],
        }

    def clear_cache(self) -> None:
        """Clear query result cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")

    def clear_performance_log(self) -> None:
        """Clear performance metrics log."""
        self._performance_log.clear()
        logger.info("Performance log cleared")


# Global optimizer instance
_optimizer_instance: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get singleton database optimizer instance."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = DatabaseOptimizer()
    return _optimizer_instance
