"""
Visual Artifact Service - Unified service for storing visual artifacts with caching.

This service ensures atomic storage operations (upload + metadata) and prevents
duplicate operations through in-memory caching with TTL.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Any

from app.services.repositories.artifacts_repository import ArtifactsRepository
from app.utils.storage_utils import ArtifactStorageService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class VisualArtifactResult:
    """Result of visual artifact storage operation."""
    artifact_id: str
    image_uri: str
    image_sha256: str
    cache_hit: bool  # Indicates if result came from cache


class VisualArtifactService:
    """
    Unified service for storing visual artifacts with in-memory caching.
    Ensures atomic storage operations and prevents duplicates.
    """
    
    # Class-level cache with TTL tracking
    _cache: Dict[str, tuple[VisualArtifactResult, float]] = {}
    _cache_lock = Lock()
    _max_cache_size = 1000  # Maximum cache entries
    
    def __init__(
        self,
        storage_service: Optional[ArtifactStorageService] = None,
        artifacts_repo: Optional[ArtifactsRepository] = None,
        cache_ttl: Optional[int] = None
    ):
        """
        Initialize the visual artifact service.
        
        Args:
            storage_service: Storage service for uploading images
            artifacts_repo: Repository for storing metadata
            cache_ttl: Cache time-to-live in seconds
        """
        self.storage_service = storage_service or ArtifactStorageService()
        self.artifacts_repo = artifacts_repo or ArtifactsRepository()
        self.cache_ttl = cache_ttl or self._get_cache_ttl()
    
    def _get_cache_ttl(self) -> int:
        """Get cache TTL from settings."""
        settings = get_settings()
        return getattr(settings, 'visual_artifact_cache_ttl', 600)  # Default 10 minutes
    
    def _generate_cache_key(
        self,
        image_bytes: bytes,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        diagram_key: str,
        artifact_type: str,
        diagram_meta: Optional[Dict[str, Any]] = None,
        image_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate deterministic cache key from all inputs.
        
        Returns:
            Hash of all inputs for uniqueness
        """
        # Create deterministic representation of all inputs
        cache_data = {
            "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
            "content_hmac": content_hmac,
            "algorithm_version": algorithm_version,
            "params_fingerprint": params_fingerprint,
            "page_number": page_number,
            "diagram_key": diagram_key,
            "artifact_type": artifact_type,
            "diagram_meta": json.dumps(diagram_meta or {}, sort_keys=True),
            "image_metadata": json.dumps(image_metadata or {}, sort_keys=True)
        }
        
        # Create stable hash of all parameters
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_string.encode()).hexdigest()
        
        return cache_hash
    
    def _get_from_cache(self, cache_key: str) -> Optional[VisualArtifactResult]:
        """Get result from cache if exists and not expired."""
        with self._cache_lock:
            if cache_key in self._cache:
                result, expiry_time = self._cache[cache_key]
                if time.time() < expiry_time:
                    return result
                else:
                    # Expired, remove from cache
                    del self._cache[cache_key]
        return None
    
    def _add_to_cache(self, cache_key: str, result: VisualArtifactResult):
        """Add result to cache with TTL and size management."""
        expiry_time = time.time() + self.cache_ttl
        with self._cache_lock:
            # Check if cache is at capacity
            if len(self._cache) >= self._max_cache_size:
                self._evict_expired_or_oldest()
            
            self._cache[cache_key] = (result, expiry_time)
    
    def _evict_expired_or_oldest(self):
        """Evict expired entries, or oldest if none expired."""
        current_time = time.time()
        
        # First, remove expired entries
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() 
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]
        
        # If still at capacity, remove oldest entries (simple FIFO)
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest 10% of entries
            to_remove = max(1, len(self._cache) // 10)
            oldest_keys = list(self._cache.keys())[:to_remove]
            for key in oldest_keys:
                del self._cache[key]
    
    def _cleanup_expired_cache(self):
        """Remove expired entries from cache (optional periodic cleanup)."""
        current_time = time.time()
        with self._cache_lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items() 
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
    
    async def store_visual_artifact(
        self,
        image_bytes: bytes,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        diagram_key: str,
        artifact_type: str,  # "diagram" or "image_jpg"
        diagram_meta: Optional[Dict[str, Any]] = None,
        image_metadata: Optional[Dict[str, Any]] = None
    ) -> VisualArtifactResult:
        """
        Store visual artifact with caching to prevent duplicate operations.
        
        Process:
        1. Generate deterministic cache key from all inputs
        2. Check in-memory cache for existing result
        3. If cache miss, perform atomic storage operations
        4. Cache successful result with TTL
        5. Return result (from cache or newly created)
        
        Args:
            image_bytes: The image content as bytes
            content_hmac: Content hash for the document
            algorithm_version: Algorithm version for processing
            params_fingerprint: Parameters fingerprint
            page_number: Page number in document
            diagram_key: Unique key for the diagram
            artifact_type: Type of artifact ("diagram" or "image_jpg")
            diagram_meta: Optional metadata for diagrams
            image_metadata: Optional metadata for images
            
        Returns:
            VisualArtifactResult with storage details and cache status
            
        Raises:
            Exception: If storage or database operations fail
        """
        # 1. Generate cache key
        cache_key = self._generate_cache_key(
            image_bytes=image_bytes,
            content_hmac=content_hmac,
            algorithm_version=algorithm_version,
            params_fingerprint=params_fingerprint,
            page_number=page_number,
            diagram_key=diagram_key,
            artifact_type=artifact_type,
            diagram_meta=diagram_meta,
            image_metadata=image_metadata
        )
        
        # 2. Check cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(
                f"Cache hit for visual artifact: page={page_number}, "
                f"diagram_key={diagram_key}, artifact_type={artifact_type}"
            )
            return VisualArtifactResult(
                artifact_id=cached_result.artifact_id,
                image_uri=cached_result.image_uri,
                image_sha256=cached_result.image_sha256,
                cache_hit=True
            )
        
        # 3. Perform atomic operations
        logger.info(
            f"Cache miss, storing visual artifact: page={page_number}, "
            f"diagram_key={diagram_key}, artifact_type={artifact_type}"
        )
        
        try:
            # Upload image to storage
            image_uri, image_sha256 = await self.storage_service.upload_page_image_jpg(
                image_bytes, content_hmac, page_number
            )
            
            # Store metadata in database
            artifact = await self.artifacts_repo.insert_unified_visual_artifact(
                content_hmac=content_hmac,
                algorithm_version=algorithm_version,
                params_fingerprint=params_fingerprint,
                page_number=page_number,
                diagram_key=diagram_key,
                artifact_type=artifact_type,
                image_uri=image_uri,
                image_sha256=image_sha256,
                diagram_meta=diagram_meta,
                image_metadata=image_metadata
            )
            
            # 4. Create result
            result = VisualArtifactResult(
                artifact_id=str(artifact.id),
                image_uri=image_uri,
                image_sha256=image_sha256,
                cache_hit=False
            )
            
            # 5. Cache successful result
            self._add_to_cache(cache_key, result)
            
            logger.info(
                f"Successfully stored visual artifact: artifact_id={result.artifact_id}, "
                f"cached for {self.cache_ttl} seconds"
            )
            
            return result
            
        except Exception as e:
            # Don't cache failures
            logger.error(
                f"Failed to store visual artifact for page {page_number}: {e}",
                exc_info=True
            )
            raise
    
    def clear_cache(self):
        """Clear all cached entries (useful for testing)."""
        with self._cache_lock:
            self._cache.clear()
            logger.info("Visual artifact cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._cache_lock:
            total_entries = len(self._cache)
            current_time = time.time()
            active_entries = sum(
                1 for _, expiry in self._cache.values() 
                if current_time < expiry
            )
            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": total_entries - active_entries
            }