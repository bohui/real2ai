"""
Unified Cache Service - Coordinates caching across all external API calls with intelligent strategies.
"""

import asyncio
import json
import logging
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """Enumeration for cache policies."""
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    COST_OPTIMIZED = "cost_optimized"
    TIME_SENSITIVE = "time_sensitive"


class CachePriority(Enum):
    """Enumeration for cache priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CacheMetrics:
    """Data class for cache performance metrics."""
    hit_rate: float
    miss_rate: float
    eviction_rate: float
    average_response_time: float
    cost_savings: float
    storage_efficiency: float
    
    def __post_init__(self):
        """Validate metrics after initialization."""
        self.hit_rate = max(0.0, min(1.0, self.hit_rate))
        self.miss_rate = max(0.0, min(1.0, self.miss_rate))


@dataclass
class CacheStrategy:
    """Data class defining caching strategy for specific operations."""
    operation_type: str
    base_ttl: int
    priority: CachePriority
    cost_factor: float
    invalidation_triggers: List[str]
    warming_conditions: List[str]
    size_limit_mb: int = 10
    
    def calculate_ttl(self, context: Dict[str, Any]) -> int:
        """Calculate TTL based on context and cost factor."""
        base = self.base_ttl
        
        # Adjust TTL based on cost (higher cost = longer TTL)
        cost_multiplier = 1 + (self.cost_factor - 1) * 0.5
        
        # Adjust based on data volatility
        volatility = context.get("data_volatility", 0.5)  # 0-1 scale
        volatility_multiplier = 2 - volatility  # More volatile = shorter TTL
        
        # Adjust based on accuracy requirements
        accuracy_requirement = context.get("accuracy_requirement", 0.5)  # 0-1 scale
        accuracy_multiplier = 2 - accuracy_requirement  # Higher accuracy = shorter TTL
        
        calculated_ttl = int(base * cost_multiplier * volatility_multiplier * accuracy_multiplier)
        
        # Apply bounds
        min_ttl = 300  # 5 minutes minimum
        max_ttl = 604800  # 7 days maximum
        
        return max(min_ttl, min(max_ttl, calculated_ttl))


class UnifiedCacheService:
    """
    Unified caching service that coordinates caching across all external API clients.
    Provides intelligent caching strategies, analytics, and performance optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logger
        
        # Cache storage backends
        self._memory_cache: Dict[str, Any] = {}
        self._persistent_cache: Optional[Any] = None  # Redis/database integration
        
        # Service configuration
        self.service_config = {
            "max_memory_mb": self.config.get("max_memory_mb", 500),
            "enable_persistent_cache": self.config.get("enable_persistent_cache", False),
            "enable_cache_warming": self.config.get("enable_cache_warming", True),
            "enable_predictive_caching": self.config.get("enable_predictive_caching", True),
            "analytics_retention_days": self.config.get("analytics_retention_days", 30),
            "cleanup_interval_seconds": self.config.get("cleanup_interval_seconds", 300)
        }
        
        # Cache strategies for different operation types
        self.cache_strategies = {
            # Property valuation strategies
            "domain_valuation": CacheStrategy(
                operation_type="domain_valuation",
                base_ttl=3600,  # 1 hour
                priority=CachePriority.MEDIUM,
                cost_factor=2.0,
                invalidation_triggers=["property_update", "market_change"],
                warming_conditions=["high_traffic_property", "recent_inquiry"]
            ),
            "corelogic_valuation": CacheStrategy(
                operation_type="corelogic_valuation",
                base_ttl=7200,  # 2 hours
                priority=CachePriority.HIGH,
                cost_factor=5.0,  # High cost operation
                invalidation_triggers=["property_update", "market_change"],
                warming_conditions=["premium_client", "bulk_request"]
            ),
            
            # Market data strategies
            "market_analytics": CacheStrategy(
                operation_type="market_analytics",
                base_ttl=1800,  # 30 minutes
                priority=CachePriority.MEDIUM,
                cost_factor=1.5,
                invalidation_triggers=["market_update", "new_sales_data"],
                warming_conditions=["popular_suburb", "active_analysis"]
            ),
            "comparable_sales": CacheStrategy(
                operation_type="comparable_sales",
                base_ttl=3600,  # 1 hour
                priority=CachePriority.LOW,
                cost_factor=1.2,
                invalidation_triggers=["new_sale", "price_update"],
                warming_conditions=["frequent_requests"]
            ),
            
            # Risk assessment strategies
            "risk_assessment": CacheStrategy(
                operation_type="risk_assessment",
                base_ttl=14400,  # 4 hours
                priority=CachePriority.HIGH,
                cost_factor=3.0,
                invalidation_triggers=["policy_change", "economic_indicator"],
                warming_conditions=["investment_analysis", "lending_request"]
            ),
            
            # Property details strategies
            "property_details": CacheStrategy(
                operation_type="property_details",
                base_ttl=86400,  # 24 hours
                priority=CachePriority.LOW,
                cost_factor=1.0,
                invalidation_triggers=["property_update", "ownership_change"],
                warming_conditions=["listing_view", "inquiry"]
            )
        }
        
        # Performance tracking
        self._performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
            "total_requests": 0,
            "cost_savings": 0.0,
            "response_times": [],
            "operation_stats": {}
        }
        
        # Locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._warming_task: Optional[asyncio.Task] = None
        
        # Start background tasks
        asyncio.create_task(self._start_background_tasks())
    
    async def get_cached_data(
        self,
        operation_type: str,
        operation_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached data for an operation.
        
        Args:
            operation_type: Type of operation (e.g., 'domain_valuation')
            operation_params: Parameters for the operation
            context: Additional context for cache decision making
            
        Returns:
            Cached data if available and valid, None otherwise
        """
        start_time = time.time()
        
        try:
            cache_key = self._generate_cache_key(operation_type, operation_params)
            
            async with self._cache_lock:
                # Check memory cache first
                cached_entry = self._memory_cache.get(cache_key)
                
                if cached_entry and self._is_cache_valid(cached_entry, operation_type, context):
                    # Update access statistics
                    cached_entry["access_count"] += 1
                    cached_entry["last_accessed"] = time.time()
                    
                    await self._update_metrics("hit", operation_type, time.time() - start_time)
                    
                    self.logger.debug(f"Cache hit for {operation_type}: {cache_key}")
                    return cached_entry["data"]
                
                # Check persistent cache if enabled
                if self.service_config["enable_persistent_cache"] and self._persistent_cache:
                    persistent_data = await self._get_from_persistent_cache(cache_key)
                    if persistent_data and self._is_cache_valid(persistent_data, operation_type, context):
                        # Promote to memory cache
                        await self._store_in_memory_cache(cache_key, persistent_data, operation_type)
                        
                        await self._update_metrics("hit", operation_type, time.time() - start_time)
                        return persistent_data["data"]
                
                await self._update_metrics("miss", operation_type, time.time() - start_time)
                return None
                
        except Exception as e:
            self.logger.error(f"Cache retrieval error for {operation_type}: {e}")
            await self._update_metrics("miss", operation_type, time.time() - start_time)
            return None
    
    async def store_cached_data(
        self,
        operation_type: str,
        operation_params: Dict[str, Any],
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        custom_ttl: Optional[int] = None
    ) -> bool:
        """
        Store data in cache with intelligent TTL calculation.
        
        Args:
            operation_type: Type of operation
            operation_params: Parameters for the operation
            data: Data to cache
            context: Additional context for cache decision making
            custom_ttl: Override TTL if specified
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(operation_type, operation_params)
            strategy = self.cache_strategies.get(operation_type)
            
            if not strategy:
                self.logger.warning(f"No cache strategy defined for {operation_type}")
                return False
            
            # Calculate TTL
            ttl = custom_ttl or strategy.calculate_ttl(context or {})
            
            # Create cache entry
            cache_entry = {
                "data": data,
                "cached_at": time.time(),
                "expires_at": time.time() + ttl,
                "ttl": ttl,
                "operation_type": operation_type,
                "operation_params": operation_params,
                "context": context or {},
                "access_count": 0,
                "last_accessed": time.time(),
                "size_bytes": self._calculate_size(data),
                "priority": strategy.priority.value
            }
            
            async with self._cache_lock:
                # Store in memory cache
                await self._store_in_memory_cache(cache_key, cache_entry, operation_type)
                
                # Store in persistent cache if enabled
                if self.service_config["enable_persistent_cache"] and self._persistent_cache:
                    await self._store_in_persistent_cache(cache_key, cache_entry)
                
                self.logger.debug(f"Cached data for {operation_type}: {cache_key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            self.logger.error(f"Cache storage error for {operation_type}: {e}")
            return False
    
    async def invalidate_cache(
        self,
        operation_type: Optional[str] = None,
        cache_key: Optional[str] = None,
        invalidation_trigger: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries based on various criteria.
        
        Args:
            operation_type: Invalidate all entries for this operation type
            cache_key: Invalidate specific cache key
            invalidation_trigger: Trigger-based invalidation
            
        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0
        
        try:
            async with self._cache_lock:
                keys_to_remove = []
                
                for key, entry in self._memory_cache.items():
                    should_invalidate = False
                    
                    # Specific key invalidation
                    if cache_key and key == cache_key:
                        should_invalidate = True
                    
                    # Operation type invalidation
                    elif operation_type and entry.get("operation_type") == operation_type:
                        should_invalidate = True
                    
                    # Trigger-based invalidation
                    elif invalidation_trigger:
                        entry_operation_type = entry.get("operation_type")
                        strategy = self.cache_strategies.get(entry_operation_type)
                        if strategy and invalidation_trigger in strategy.invalidation_triggers:
                            should_invalidate = True
                    
                    if should_invalidate:
                        keys_to_remove.append(key)
                
                # Remove invalidated entries
                for key in keys_to_remove:
                    del self._memory_cache[key]
                    invalidated_count += 1
                
                # Also invalidate persistent cache if enabled
                if self.service_config["enable_persistent_cache"] and self._persistent_cache:
                    await self._invalidate_persistent_cache(keys_to_remove)
                
                self.logger.info(f"Invalidated {invalidated_count} cache entries")
                return invalidated_count
                
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {e}")
            return 0
    
    async def warm_cache(
        self,
        operation_type: str,
        warming_params: List[Dict[str, Any]],
        warming_function: Callable
    ) -> int:
        """
        Warm cache with precomputed data for expected requests.
        
        Args:
            operation_type: Type of operation to warm
            warming_params: List of parameter sets to warm
            warming_function: Async function to call for data generation
            
        Returns:
            Number of entries warmed
        """
        if not self.service_config["enable_cache_warming"]:
            return 0
        
        warmed_count = 0
        
        try:
            for params in warming_params:
                # Check if already cached
                cached_data = await self.get_cached_data(operation_type, params)
                if cached_data is not None:
                    continue
                
                try:
                    # Generate data using warming function
                    data = await warming_function(params)
                    
                    # Store in cache
                    context = {"warming": True, "data_volatility": 0.3}  # Warmed data is less volatile
                    success = await self.store_cached_data(
                        operation_type, 
                        params, 
                        data,
                        context
                    )
                    
                    if success:
                        warmed_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Cache warming failed for {operation_type}: {e}")
                    continue
            
            self.logger.info(f"Warmed {warmed_count} cache entries for {operation_type}")
            return warmed_count
            
        except Exception as e:
            self.logger.error(f"Cache warming error: {e}")
            return 0
    
    async def get_cache_metrics(self) -> CacheMetrics:
        """Get comprehensive cache performance metrics."""
        async with self._metrics_lock:
            total_requests = self._performance_metrics["total_requests"]
            hits = self._performance_metrics["cache_hits"]
            misses = self._performance_metrics["cache_misses"]
            
            hit_rate = hits / total_requests if total_requests > 0 else 0
            miss_rate = misses / total_requests if total_requests > 0 else 0
            eviction_rate = self._performance_metrics["cache_evictions"] / total_requests if total_requests > 0 else 0
            
            response_times = self._performance_metrics["response_times"]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Calculate storage efficiency (hit rate weighted by storage cost)
            memory_usage = sum(entry.get("size_bytes", 0) for entry in self._memory_cache.values())
            max_memory_bytes = self.service_config["max_memory_mb"] * 1024 * 1024
            storage_efficiency = hit_rate * (1 - memory_usage / max_memory_bytes) if max_memory_bytes > 0 else 0
            
            return CacheMetrics(
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                eviction_rate=eviction_rate,
                average_response_time=avg_response_time,
                cost_savings=self._performance_metrics["cost_savings"],
                storage_efficiency=storage_efficiency
            )
    
    async def get_cache_analytics(self) -> Dict[str, Any]:
        """Get detailed cache analytics and insights."""
        metrics = await self.get_cache_metrics()
        
        analytics = {
            "performance_metrics": {
                "hit_rate": metrics.hit_rate,
                "miss_rate": metrics.miss_rate,
                "eviction_rate": metrics.eviction_rate,
                "average_response_time_ms": metrics.average_response_time * 1000,
                "cost_savings_dollars": metrics.cost_savings,
                "storage_efficiency": metrics.storage_efficiency
            },
            "cache_size": {
                "total_entries": len(self._memory_cache),
                "memory_usage_mb": sum(entry.get("size_bytes", 0) for entry in self._memory_cache.values()) / (1024 * 1024),
                "max_memory_mb": self.service_config["max_memory_mb"]
            },
            "operation_breakdown": {},
            "recommendations": []
        }
        
        # Operation-specific analytics
        async with self._metrics_lock:
            for operation, stats in self._performance_metrics["operation_stats"].items():
                analytics["operation_breakdown"][operation] = {
                    "requests": stats.get("requests", 0),
                    "hits": stats.get("hits", 0),
                    "misses": stats.get("misses", 0),
                    "hit_rate": stats.get("hits", 0) / max(stats.get("requests", 1), 1),
                    "avg_response_time_ms": stats.get("avg_response_time", 0) * 1000
                }
        
        # Generate recommendations
        if metrics.hit_rate < 0.6:
            analytics["recommendations"].append("Consider increasing cache TTL or warming strategies")
        
        if metrics.storage_efficiency < 0.5:
            analytics["recommendations"].append("Review cache eviction policies and size limits")
        
        if metrics.eviction_rate > 0.1:
            analytics["recommendations"].append("Consider increasing memory allocation or implementing tiered storage")
        
        return analytics
    
    def _generate_cache_key(self, operation_type: str, params: Dict[str, Any]) -> str:
        """Generate a consistent cache key."""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{operation_type}:{sorted_params}"
        
        # Create hash of the key data
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]  # Use shorter hash
        return f"unified_cache:{operation_type}:{key_hash}"
    
    def _is_cache_valid(
        self, 
        cache_entry: Dict[str, Any], 
        operation_type: str, 
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if cache entry is still valid."""
        current_time = time.time()
        
        # Check expiration
        if cache_entry.get("expires_at", 0) < current_time:
            return False
        
        # Check context-based invalidation
        if context:
            # High accuracy requirement may invalidate cache earlier
            accuracy_requirement = context.get("accuracy_requirement", 0.5)
            if accuracy_requirement > 0.8:
                # Reduce effective TTL for high accuracy requirements
                adjusted_expires_at = cache_entry.get("cached_at", 0) + (cache_entry.get("ttl", 0) * 0.5)
                if adjusted_expires_at < current_time:
                    return False
        
        return True
    
    async def _store_in_memory_cache(
        self, 
        cache_key: str, 
        cache_entry: Dict[str, Any], 
        operation_type: str
    ) -> None:
        """Store cache entry in memory cache with size management."""
        # Check memory limits and evict if necessary
        await self._manage_memory_limits(cache_entry.get("size_bytes", 0))
        
        # Store the entry
        self._memory_cache[cache_key] = cache_entry
    
    async def _manage_memory_limits(self, new_entry_size: int) -> None:
        """Manage memory limits by evicting entries if necessary."""
        max_memory_bytes = self.service_config["max_memory_mb"] * 1024 * 1024
        current_memory = sum(entry.get("size_bytes", 0) for entry in self._memory_cache.values())
        
        if current_memory + new_entry_size > max_memory_bytes:
            # Evict entries using LRU with priority consideration
            entries_by_score = []
            
            for key, entry in self._memory_cache.items():
                # Calculate eviction score (lower = more likely to evict)
                priority_weight = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(
                    entry.get("priority", "medium"), 2
                )
                access_recency = time.time() - entry.get("last_accessed", 0)
                access_frequency = entry.get("access_count", 0)
                
                eviction_score = priority_weight * (1 + access_frequency) / (1 + access_recency)
                entries_by_score.append((eviction_score, key, entry))
            
            # Sort by eviction score (ascending = evict first)
            entries_by_score.sort()
            
            # Evict entries until we have enough space
            memory_to_free = (current_memory + new_entry_size) - max_memory_bytes
            freed_memory = 0
            
            for score, key, entry in entries_by_score:
                if freed_memory >= memory_to_free:
                    break
                
                freed_memory += entry.get("size_bytes", 0)
                del self._memory_cache[key]
                self._performance_metrics["cache_evictions"] += 1
    
    async def _get_from_persistent_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from persistent cache (Redis/database)."""
        # Placeholder for persistent cache implementation
        # In production, this would interface with Redis, database, etc.
        return None
    
    async def _store_in_persistent_cache(self, cache_key: str, cache_entry: Dict[str, Any]) -> None:
        """Store data in persistent cache."""
        # Placeholder for persistent cache implementation
        pass
    
    async def _invalidate_persistent_cache(self, cache_keys: List[str]) -> None:
        """Invalidate entries in persistent cache."""
        # Placeholder for persistent cache implementation
        pass
    
    def _calculate_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes."""
        try:
            return len(json.dumps(data, default=str))
        except (TypeError, ValueError):
            return 1024  # Default estimate
    
    async def _update_metrics(self, metric_type: str, operation_type: str, response_time: float) -> None:
        """Update performance metrics."""
        async with self._metrics_lock:
            self._performance_metrics["total_requests"] += 1
            self._performance_metrics["response_times"].append(response_time)
            
            # Keep only recent response times (last 1000)
            if len(self._performance_metrics["response_times"]) > 1000:
                self._performance_metrics["response_times"] = self._performance_metrics["response_times"][-1000:]
            
            if metric_type == "hit":
                self._performance_metrics["cache_hits"] += 1
            elif metric_type == "miss":
                self._performance_metrics["cache_misses"] += 1
            
            # Update operation-specific stats
            if operation_type not in self._performance_metrics["operation_stats"]:
                self._performance_metrics["operation_stats"][operation_type] = {
                    "requests": 0,
                    "hits": 0,
                    "misses": 0,
                    "response_times": []
                }
            
            op_stats = self._performance_metrics["operation_stats"][operation_type]
            op_stats["requests"] += 1
            op_stats["response_times"].append(response_time)
            
            if metric_type == "hit":
                op_stats["hits"] += 1
            elif metric_type == "miss":
                op_stats["misses"] += 1
            
            # Calculate average response time
            if op_stats["response_times"]:
                op_stats["avg_response_time"] = statistics.mean(op_stats["response_times"])
    
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        if self.service_config["enable_cache_warming"] and not self._warming_task:
            self._warming_task = asyncio.create_task(self._periodic_cache_warming())
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(self.service_config["cleanup_interval_seconds"])
                
                async with self._cache_lock:
                    expired_keys = []
                    current_time = time.time()
                    
                    for key, entry in self._memory_cache.items():
                        if entry.get("expires_at", 0) < current_time:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._memory_cache[key]
                    
                    if expired_keys:
                        self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
    
    async def _periodic_cache_warming(self) -> None:
        """Periodic cache warming for popular operations."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Analyze access patterns and warm frequently accessed but expired entries
                # This is a simplified implementation - production would use more sophisticated ML
                
                popular_operations = {}
                
                async with self._metrics_lock:
                    for operation_type, stats in self._performance_metrics["operation_stats"].items():
                        if stats["requests"] > 10:  # Minimum threshold for warming
                            popular_operations[operation_type] = stats["requests"]
                
                # Log warming opportunity (actual warming would require operation-specific functions)
                if popular_operations:
                    self.logger.info(f"Cache warming opportunities identified: {list(popular_operations.keys())}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache warming error: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the cache service and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        
        # Clear caches
        async with self._cache_lock:
            self._memory_cache.clear()
        
        self.logger.info("Unified cache service shutdown complete")


# Factory function for creating the service
def create_unified_cache_service(config: Optional[Dict[str, Any]] = None) -> UnifiedCacheService:
    """
    Factory function to create UnifiedCacheService.
    
    Args:
        config: Cache service configuration
        
    Returns:
        Initialized UnifiedCacheService
    """
    default_config = {
        "max_memory_mb": 500,
        "enable_persistent_cache": False,
        "enable_cache_warming": True,
        "enable_predictive_caching": True,
        "analytics_retention_days": 30,
        "cleanup_interval_seconds": 300
    }
    
    if config:
        default_config.update(config)
    
    return UnifiedCacheService(default_config)