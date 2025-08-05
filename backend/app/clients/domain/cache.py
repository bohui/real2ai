"""
Caching layer for Domain API client with intelligent cache management.
"""

import asyncio
import json
import logging
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached data entry."""
    
    key: str
    data: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    size_bytes: int = 0
    
    def __post_init__(self):
        """Calculate entry size."""
        try:
            self.size_bytes = len(json.dumps(self.data, default=str))
        except (TypeError, ValueError):
            self.size_bytes = 1024  # Default estimate
    
    def is_expired(self, current_time: float = None) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        
        current_time = current_time or time.time()
        return current_time > self.expires_at
    
    def is_stale(self, max_age_seconds: int) -> bool:
        """Check if cache entry is stale based on age."""
        current_time = time.time()
        return (current_time - self.created_at) > max_age_seconds
    
    def update_access(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class InMemoryCache:
    """In-memory cache with LRU eviction and intelligent management."""
    
    def __init__(
        self,
        max_size_mb: int = 100,
        default_ttl_seconds: int = 3600,
        max_entries: int = 10000,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        
        self._cache: Dict[str, CacheEntry] = {}
        self._size_bytes = 0
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "cleanups": 0,
            "size_evictions": 0,
            "expired_evictions": 0
        }
        
        logger.info(f"Cache initialized: max_size={max_size_mb}MB, max_entries={max_entries}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        async with self._lock:
            await self._cleanup_if_needed()
            
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return default
            
            if entry.is_expired():
                await self._remove_entry(key)
                self._stats["misses"] += 1
                self._stats["expired_evictions"] += 1
                return default
            
            entry.update_access()
            self._stats["hits"] += 1
            return entry.data
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: List[str] = None
    ) -> bool:
        """Set value in cache."""
        async with self._lock:
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = time.time() + ttl if ttl > 0 else None
            
            entry = CacheEntry(
                key=key,
                data=value,
                created_at=time.time(),
                expires_at=expires_at,
                tags=tags or []
            )
            
            # Check if we need to evict entries
            await self._ensure_space(entry.size_bytes)
            
            # Remove existing entry if present
            if key in self._cache:
                await self._remove_entry(key)
            
            # Add new entry
            self._cache[key] = entry
            self._size_bytes += entry.size_bytes
            
            logger.debug(f"Cached {key} ({entry.size_bytes} bytes, TTL: {ttl}s)")
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                await self._remove_entry(key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache (and is not expired)."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired():
                await self._remove_entry(key)
                return False
            
            return True
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._size_bytes = 0
            logger.info("Cache cleared")
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate entries by tags."""
        async with self._lock:
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                await self._remove_entry(key)
            
            logger.info(f"Invalidated {len(keys_to_remove)} entries by tags: {tags}")
            return len(keys_to_remove)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "entries": len(self._cache),
                "size_bytes": self._size_bytes,
                "size_mb": self._size_bytes / (1024 * 1024),
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                **self._stats
            }
    
    async def _remove_entry(self, key: str) -> None:
        """Remove entry and update size."""
        entry = self._cache.pop(key, None)
        if entry:
            self._size_bytes -= entry.size_bytes
    
    async def _ensure_space(self, required_bytes: int) -> None:
        """Ensure there's space for new entry."""
        # Check size limit
        while (self._size_bytes + required_bytes > self.max_size_bytes or 
               len(self._cache) >= self.max_entries):
            
            if not self._cache:
                break
            
            # Find LRU entry to evict
            lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
            await self._remove_entry(lru_key)
            self._stats["evictions"] += 1
            self._stats["size_evictions"] += 1
    
    async def _cleanup_if_needed(self) -> None:
        """Clean up expired entries if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired(current_time):
                expired_keys.append(key)
        
        for key in expired_keys:
            await self._remove_entry(key)
            self._stats["expired_evictions"] += 1
        
        self._last_cleanup = current_time
        self._stats["cleanups"] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")


class PropertyDataCache:
    """Specialized cache for property data with domain-aware caching strategies."""
    
    def __init__(
        self,
        cache: InMemoryCache,
        property_ttl: int = 3600,  # 1 hour
        market_data_ttl: int = 86400,  # 24 hours
        search_results_ttl: int = 1800,  # 30 minutes
        valuation_ttl: int = 7200  # 2 hours
    ):
        self.cache = cache
        self.property_ttl = property_ttl
        self.market_data_ttl = market_data_ttl
        self.search_results_ttl = search_results_ttl
        self.valuation_ttl = valuation_ttl
        
        logger.info("Property data cache initialized with domain-specific TTLs")
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Create cache key from prefix and parameters."""
        # Create deterministic key from arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(json.dumps(arg, sort_keys=True, default=str))
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(json.dumps(sorted_kwargs, default=str))
        
        # Hash for consistent length
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get_property_profile(self, address: str) -> Optional[Dict[str, Any]]:
        """Get cached property profile."""
        key = self._make_key("property_profile", address.lower().strip())
        return await self.cache.get(key)
    
    async def cache_property_profile(
        self,
        address: str,
        profile_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache property profile data."""
        key = self._make_key("property_profile", address.lower().strip())
        tags = ["property_profile", f"address:{address.lower()}"]
        
        return await self.cache.set(
            key,
            profile_data,
            ttl or self.property_ttl,
            tags
        )
    
    async def get_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get cached property details."""
        key = self._make_key("property_details", property_id)
        return await self.cache.get(key)
    
    async def cache_property_details(
        self,
        property_id: str,
        details_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache property details."""
        key = self._make_key("property_details", property_id)
        tags = ["property_details", f"property_id:{property_id}"]
        
        return await self.cache.set(
            key,
            details_data,
            ttl or self.property_ttl,
            tags
        )
    
    async def get_search_results(self, search_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        key = self._make_key("search_results", search_params)
        return await self.cache.get(key)
    
    async def cache_search_results(
        self,
        search_params: Dict[str, Any],
        results_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache search results."""
        key = self._make_key("search_results", search_params)
        tags = ["search_results"]
        
        # Add location-based tags
        if "locations" in search_params:
            for location in search_params["locations"]:
                if "suburb" in location:
                    tags.append(f"suburb:{location['suburb'].lower()}")
                if "state" in location:
                    tags.append(f"state:{location['state'].lower()}")
        
        return await self.cache.set(
            key,
            results_data,
            ttl or self.search_results_ttl,
            tags
        )
    
    async def get_market_analytics(
        self,
        location: Dict[str, str],
        property_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached market analytics."""
        key = self._make_key("market_analytics", location, property_type)
        return await self.cache.get(key)
    
    async def cache_market_analytics(
        self,
        location: Dict[str, str],
        property_type: str,
        analytics_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache market analytics."""
        key = self._make_key("market_analytics", location, property_type)
        tags = ["market_analytics"]
        
        if "suburb" in location:
            tags.append(f"suburb:{location['suburb'].lower()}")
        if "state" in location:
            tags.append(f"state:{location['state'].lower()}")
        if property_type:
            tags.append(f"property_type:{property_type.lower()}")
        
        return await self.cache.set(
            key,
            analytics_data,
            ttl or self.market_data_ttl,
            tags
        )
    
    async def get_valuation(
        self,
        address: str,
        property_details: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached valuation."""
        key = self._make_key("valuation", address.lower().strip(), property_details)
        return await self.cache.get(key)
    
    async def cache_valuation(
        self,
        address: str,
        property_details: Dict[str, Any],
        valuation_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache valuation data."""
        key = self._make_key("valuation", address.lower().strip(), property_details)
        tags = ["valuation", f"address:{address.lower()}"]
        
        return await self.cache.set(
            key,
            valuation_data,
            ttl or self.valuation_ttl,
            tags
        )
    
    async def invalidate_property_data(self, address: str) -> int:
        """Invalidate all cached data for a property."""
        tags = [f"address:{address.lower()}"]
        return await self.cache.invalidate_by_tags(tags)
    
    async def invalidate_location_data(self, suburb: str, state: str) -> int:
        """Invalidate all cached data for a location."""
        tags = [f"suburb:{suburb.lower()}", f"state:{state.lower()}"]
        return await self.cache.invalidate_by_tags(tags)
    
    async def warm_cache_for_area(
        self,
        suburb: str,
        state: str,
        client_instance: Any
    ) -> Dict[str, Any]:
        """Pre-populate cache for high-traffic areas."""
        logger.info(f"Warming cache for {suburb}, {state}")
        
        results = {
            "suburb": suburb,
            "state": state,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "operations": []
        }
        
        try:
            # Warm market analytics
            location = {"suburb": suburb, "state": state}
            
            # Check if already cached
            if not await self.get_market_analytics(location):
                try:
                    analytics = await client_instance.get_market_analytics(location)
                    await self.cache_market_analytics(location, None, analytics)
                    results["operations"].append("market_analytics_cached")
                except Exception as e:
                    logger.warning(f"Failed to warm market analytics cache: {e}")
                    results["operations"].append(f"market_analytics_failed: {str(e)}")
            
            # Warm search results for common queries
            common_searches = [
                {"locations": [location], "listingType": "Sale", "pageSize": 20},
                {"locations": [location], "listingType": "Rent", "pageSize": 20}
            ]
            
            for search_params in common_searches:
                if not await self.get_search_results(search_params):
                    try:
                        search_results = await client_instance.search_properties(search_params)
                        await self.cache_search_results(search_params, search_results)
                        results["operations"].append(f"search_cached_{search_params['listingType']}")
                    except Exception as e:
                        logger.warning(f"Failed to warm search cache: {e}")
                        results["operations"].append(f"search_failed_{search_params['listingType']}: {str(e)}")
            
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            results["success"] = True
            
        except Exception as e:
            logger.error(f"Cache warming failed for {suburb}, {state}: {e}")
            results["error"] = str(e)
            results["success"] = False
        
        return results
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics with property-specific metrics."""
        base_stats = await self.cache.get_stats()
        
        # Count entries by type
        entry_types = {}
        async with self.cache._lock:
            for key, entry in self.cache._cache.items():
                for tag in entry.tags:
                    entry_types[tag] = entry_types.get(tag, 0) + 1
        
        return {
            **base_stats,
            "entry_types": entry_types,
            "ttl_settings": {
                "property_ttl": self.property_ttl,
                "market_data_ttl": self.market_data_ttl,
                "search_results_ttl": self.search_results_ttl,
                "valuation_ttl": self.valuation_ttl
            }
        }