"""
Caching layer for CoreLogic API client with cost-aware caching strategies.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta
import hashlib

from ..base.interfaces import PropertyCacheOperations

logger = logging.getLogger(__name__)


class CoreLogicCacheManager:
    """
    Advanced caching manager for CoreLogic API responses.
    
    Features:
    - Cost-aware caching with longer TTL for expensive operations
    - Tiered caching based on data type and cost
    - Automatic cache warming for high-value properties
    - Cache analytics and optimization
    """
    
    def __init__(self, config, cache_backend=None):
        self.config = config
        self.cache_backend = cache_backend or {}  # Default to in-memory dict
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Cache configuration
        self.default_ttl = config.cache_ttl_seconds
        self.market_data_ttl = config.market_data_cache_ttl
        self.risk_assessment_ttl = config.risk_assessment_cache_ttl
        
        # Cache tiers based on operation cost
        self.tier_ttls = {
            "tier1": 3600,      # Low cost operations (1 hour)
            "tier2": 86400,     # Medium cost operations (24 hours)
            "tier3": 259200,    # High cost operations (3 days)
            "tier4": 604800     # Very high cost operations (7 days)
        }
        
        # Operation to tier mapping
        self.operation_tiers = {
            "comparable_sales": "tier1",
            "property_details": "tier1",
            "avm_valuation": "tier2",
            "desktop_valuation": "tier3",
            "professional_valuation": "tier4",
            "market_analytics": "tier2",
            "risk_assessment": "tier3",
            "yield_analysis": "tier2",
            "bulk_valuation": "tier2",
            "property_report": "tier4"
        }
        
        # Cache statistics
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "cost_saved": 0.0,
            "operations": {}
        }
        
        # Locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
    
    def _get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate a consistent cache key for the operation and parameters."""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{operation}:{sorted_params}"
        
        # Create hash of the key data
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"corelogic:{operation}:{key_hash}"
    
    def _get_ttl_for_operation(self, operation: str) -> int:
        """Get TTL for a specific operation based on its tier."""
        tier = self.operation_tiers.get(operation, "tier1")
        return self.tier_ttls.get(tier, self.default_ttl)
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid."""
        if not cached_data:
            return False
        
        cached_at = cached_data.get("cached_at", 0)
        ttl = cached_data.get("ttl", self.default_ttl)
        
        return time.time() - cached_at < ttl
    
    async def get_cached_response(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached response for an operation."""
        if not self.config.enable_caching:
            return None
        
        cache_key = self._get_cache_key(operation, params)
        
        async with self._cache_lock:
            cached_data = self.cache_backend.get(cache_key)
            
            if cached_data and self._is_cache_valid(cached_data):
                # Update statistics
                await self._update_cache_stats("hit", operation, cached_data.get("operation_cost", 0.0))
                
                self.logger.debug(f"Cache hit for {operation}")
                return cached_data.get("response")
            
            # Cache miss
            await self._update_cache_stats("miss", operation, 0.0)
            self.logger.debug(f"Cache miss for {operation}")
            return None
    
    async def cache_response(self, operation: str, params: Dict[str, Any], 
                           response: Dict[str, Any], operation_cost: float = 0.0) -> None:
        """Cache a response with appropriate TTL based on operation type."""
        if not self.config.enable_caching:
            return
        
        cache_key = self._get_cache_key(operation, params)
        ttl = self._get_ttl_for_operation(operation)
        
        cached_data = {
            "response": response,
            "cached_at": time.time(),
            "ttl": ttl,
            "operation": operation,
            "operation_cost": operation_cost,
            "params_hash": hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        }
        
        async with self._cache_lock:
            self.cache_backend[cache_key] = cached_data
            
            # Implement cache size limit (optional)
            await self._enforce_cache_size_limit()
        
        self.logger.debug(f"Cached response for {operation} (TTL: {ttl}s, Cost: ${operation_cost:.2f})")
    
    async def invalidate_cache(self, operation: str = None, params: Dict[str, Any] = None) -> int:
        """Invalidate cache entries."""
        if not self.config.enable_caching:
            return 0
        
        async with self._cache_lock:
            if operation and params:
                # Invalidate specific cache entry
                cache_key = self._get_cache_key(operation, params)
                if cache_key in self.cache_backend:
                    del self.cache_backend[cache_key]
                    return 1
            
            elif operation:
                # Invalidate all entries for an operation
                keys_to_delete = [
                    key for key in self.cache_backend.keys()
                    if key.startswith(f"corelogic:{operation}:")
                ]
                for key in keys_to_delete:
                    del self.cache_backend[key]
                return len(keys_to_delete)
            
            else:
                # Invalidate all cache
                count = len(self.cache_backend)
                self.cache_backend.clear()
                return count
    
    async def warm_cache_for_property(self, property_id: str, 
                                    operations: List[str] = None) -> Dict[str, Any]:
        """Pre-populate cache for a property with commonly requested operations."""
        if not operations:
            operations = ["property_details", "comparable_sales", "avm_valuation"]
        
        warming_results = {
            "property_id": property_id,
            "operations_warmed": [],
            "operations_failed": [],
            "total_cost": 0.0
        }
        
        for operation in operations:
            try:
                # This would be called by the client to warm the cache
                # The actual implementation would depend on the client integration
                self.logger.info(f"Cache warming requested for {operation} on property {property_id}")
                warming_results["operations_warmed"].append(operation)
            
            except Exception as e:
                self.logger.error(f"Cache warming failed for {operation}: {e}")
                warming_results["operations_failed"].append({
                    "operation": operation,
                    "error": str(e)
                })
        
        return warming_results
    
    async def warm_cache_for_area(self, suburb: str, state: str, 
                                operations: List[str] = None) -> Dict[str, Any]:
        """Pre-populate cache for high-traffic area data."""
        if not operations:
            operations = ["market_analytics", "demographics"]
        
        warming_results = {
            "location": f"{suburb}, {state}",
            "operations_warmed": [],
            "operations_failed": [],
            "total_cost": 0.0
        }
        
        for operation in operations:
            try:
                # Area-specific cache warming
                self.logger.info(f"Area cache warming requested for {operation} in {suburb}, {state}")
                warming_results["operations_warmed"].append(operation)
            
            except Exception as e:
                self.logger.error(f"Area cache warming failed for {operation}: {e}")
                warming_results["operations_failed"].append({
                    "operation": operation,
                    "error": str(e)
                })
        
        return warming_results
    
    async def _update_cache_stats(self, event_type: str, operation: str, cost_saved: float) -> None:
        """Update cache statistics."""
        async with self._stats_lock:
            if event_type == "hit":
                self._cache_stats["hits"] += 1
                self._cache_stats["cost_saved"] += cost_saved
            elif event_type == "miss":
                self._cache_stats["misses"] += 1
            
            # Update operation-specific stats
            if operation not in self._cache_stats["operations"]:
                self._cache_stats["operations"][operation] = {
                    "hits": 0,
                    "misses": 0,
                    "cost_saved": 0.0
                }
            
            self._cache_stats["operations"][operation][f"{event_type}s"] += 1
            if event_type == "hit":
                self._cache_stats["operations"][operation]["cost_saved"] += cost_saved
    
    async def _enforce_cache_size_limit(self, max_entries: int = 10000) -> None:
        """Enforce cache size limit by removing oldest entries."""
        if len(self.cache_backend) <= max_entries:
            return
        
        # Sort by cached_at timestamp and remove oldest entries
        sorted_entries = sorted(
            self.cache_backend.items(),
            key=lambda x: x[1].get("cached_at", 0)
        )
        
        entries_to_remove = len(self.cache_backend) - max_entries
        for i in range(entries_to_remove):
            key, _ = sorted_entries[i]
            del self.cache_backend[key]
        
        self.logger.info(f"Removed {entries_to_remove} old cache entries")
    
    async def cleanup_expired_entries(self) -> int:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = []
        
        async with self._cache_lock:
            for key, cached_data in self.cache_backend.items():
                if not self._is_cache_valid(cached_data):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache_backend[key]
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / max(total_requests, 1)) * 100
        
        return {
            "hit_rate_percentage": round(hit_rate, 2),
            "total_hits": self._cache_stats["hits"],
            "total_misses": self._cache_stats["misses"],
            "total_requests": total_requests,
            "cost_saved_aud": round(self._cache_stats["cost_saved"], 2),
            "cache_size": len(self.cache_backend),
            "operation_stats": self._cache_stats["operations"].copy()
        }
    
    def get_cache_efficiency_report(self) -> Dict[str, Any]:
        """Generate a detailed cache efficiency report."""
        stats = self.get_cache_stats()
        
        # Calculate efficiency metrics per operation
        operation_efficiency = {}
        for operation, op_stats in stats["operation_stats"].items():
            total_ops = op_stats["hits"] + op_stats["misses"]
            hit_rate = (op_stats["hits"] / max(total_ops, 1)) * 100
            
            operation_efficiency[operation] = {
                "hit_rate_percentage": round(hit_rate, 2),
                "requests": total_ops,
                "cost_saved": op_stats["cost_saved"],
                "tier": self.operation_tiers.get(operation, "tier1"),
                "ttl_hours": self._get_ttl_for_operation(operation) / 3600
            }
        
        # Identify optimization opportunities
        optimization_recommendations = []
        
        for operation, efficiency in operation_efficiency.items():
            if efficiency["hit_rate_percentage"] < 20 and efficiency["requests"] > 10:
                optimization_recommendations.append({
                    "operation": operation,
                    "issue": "Low hit rate",
                    "recommendation": "Consider increasing TTL or improving cache key consistency"
                })
        
        return {
            "overall_stats": stats,
            "operation_efficiency": operation_efficiency,
            "optimization_recommendations": optimization_recommendations,
            "cache_configuration": {
                "enabled": self.config.enable_caching,
                "default_ttl_hours": self.default_ttl / 3600,
                "tier_configuration": {
                    tier: ttl / 3600 for tier, ttl in self.tier_ttls.items()
                }
            }
        }


class CoreLogicPropertyCacheOperations(PropertyCacheOperations):
    """CoreLogic-specific implementation of property cache operations."""
    
    def __init__(self, cache_manager: CoreLogicCacheManager):
        self.cache_manager = cache_manager
    
    async def cache_property_profile(self, address: str, profile_data: Dict[str, Any], 
                                   ttl: int = 3600) -> bool:
        """Cache property profile data."""
        try:
            params = {"address": address}
            await self.cache_manager.cache_response(
                "property_profile", params, profile_data, 0.0
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache property profile for {address}: {e}")
            return False
    
    async def get_cached_property_profile(self, address: str) -> Optional[Dict[str, Any]]:
        """Get cached property profile data."""
        params = {"address": address}
        return await self.cache_manager.get_cached_response("property_profile", params)
    
    async def cache_market_data(self, location_key: str, market_data: Dict[str, Any], 
                              ttl: int = 86400) -> bool:
        """Cache market data with longer TTL."""
        try:
            params = {"location": location_key}
            await self.cache_manager.cache_response(
                "market_analytics", params, market_data, 0.0
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache market data for {location_key}: {e}")
            return False
    
    async def get_cached_market_data(self, location_key: str) -> Optional[Dict[str, Any]]:
        """Get cached market data."""
        params = {"location": location_key}
        return await self.cache_manager.get_cached_response("market_analytics", params)
    
    async def invalidate_property_cache(self, address: str) -> bool:
        """Invalidate cached property data."""
        try:
            # Invalidate all property-related cache entries
            operations = ["property_profile", "property_details", "avm_valuation", 
                         "comparable_sales", "risk_assessment"]
            
            total_invalidated = 0
            for operation in operations:
                params = {"address": address}
                count = await self.cache_manager.invalidate_cache(operation, params)
                total_invalidated += count
            
            logger.info(f"Invalidated {total_invalidated} cache entries for {address}")
            return total_invalidated > 0
        
        except Exception as e:
            logger.error(f"Failed to invalidate property cache for {address}: {e}")
            return False
    
    async def warm_cache_for_area(self, suburb: str, state: str) -> Dict[str, Any]:
        """Pre-populate cache for high-traffic areas."""
        return await self.cache_manager.warm_cache_for_area(suburb, state)