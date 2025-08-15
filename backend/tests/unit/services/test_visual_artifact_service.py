"""
Unit tests for VisualArtifactService
"""

import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.services.visual_artifact_service import VisualArtifactService, VisualArtifactResult


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    service = MagicMock()
    service.upload_page_image_jpg = AsyncMock(
        return_value=("supabase://artifacts/test.jpg", "sha256_test")
    )
    return service


@pytest.fixture
def mock_artifacts_repo():
    """Create a mock artifacts repository."""
    repo = MagicMock()
    artifact = MagicMock()
    artifact.id = "test-artifact-id"
    repo.insert_unified_visual_artifact = AsyncMock(return_value=artifact)
    return repo


@pytest.fixture
def visual_service(mock_storage_service, mock_artifacts_repo):
    """Create a visual artifact service with mocked dependencies."""
    service = VisualArtifactService(
        storage_service=mock_storage_service,
        artifacts_repo=mock_artifacts_repo,
        cache_ttl=10  # Short TTL for testing
    )
    # Clear cache before each test
    service.clear_cache()
    return service


@pytest.mark.asyncio
async def test_store_visual_artifact_success(visual_service, mock_storage_service, mock_artifacts_repo):
    """Test successful storage of visual artifact."""
    # Arrange
    image_bytes = b"test_image_data"
    content_hmac = "test_hmac"
    algorithm_version = 1
    params_fingerprint = "test_fingerprint"
    page_number = 1
    diagram_key = "test_diagram"
    artifact_type = "diagram"
    diagram_meta = {"type": "floor_plan", "confidence": 0.95}
    
    # Act
    result = await visual_service.store_visual_artifact(
        image_bytes=image_bytes,
        content_hmac=content_hmac,
        algorithm_version=algorithm_version,
        params_fingerprint=params_fingerprint,
        page_number=page_number,
        diagram_key=diagram_key,
        artifact_type=artifact_type,
        diagram_meta=diagram_meta
    )
    
    # Assert
    assert isinstance(result, VisualArtifactResult)
    assert result.artifact_id == "test-artifact-id"
    assert result.image_uri == "supabase://artifacts/test.jpg"
    assert result.image_sha256 == "sha256_test"
    assert result.cache_hit is False
    
    # Verify storage service was called
    mock_storage_service.upload_page_image_jpg.assert_called_once_with(
        image_bytes, content_hmac, page_number
    )
    
    # Verify repository was called
    mock_artifacts_repo.insert_unified_visual_artifact.assert_called_once()


@pytest.mark.asyncio
async def test_store_visual_artifact_cache_hit(visual_service):
    """Test cache hit on second call with same parameters."""
    # Arrange
    image_bytes = b"test_image_data"
    params = {
        "image_bytes": image_bytes,
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram",
        "diagram_meta": {"type": "floor_plan"}
    }
    
    # Act - First call
    result1 = await visual_service.store_visual_artifact(**params)
    assert result1.cache_hit is False
    
    # Act - Second call with same parameters
    result2 = await visual_service.store_visual_artifact(**params)
    
    # Assert
    assert result2.cache_hit is True
    assert result2.artifact_id == result1.artifact_id
    assert result2.image_uri == result1.image_uri
    assert result2.image_sha256 == result1.image_sha256
    
    # Verify storage was only called once
    assert visual_service.storage_service.upload_page_image_jpg.call_count == 1
    assert visual_service.artifacts_repo.insert_unified_visual_artifact.call_count == 1


@pytest.mark.asyncio
async def test_store_visual_artifact_cache_miss_different_params(visual_service):
    """Test cache miss when parameters are different."""
    # Arrange
    base_params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram"
    }
    
    # Act - First call
    result1 = await visual_service.store_visual_artifact(**base_params)
    assert result1.cache_hit is False
    
    # Act - Second call with different page number
    params2 = {**base_params, "page_number": 2}
    result2 = await visual_service.store_visual_artifact(**params2)
    
    # Assert
    assert result2.cache_hit is False
    
    # Verify storage was called twice
    assert visual_service.storage_service.upload_page_image_jpg.call_count == 2
    assert visual_service.artifacts_repo.insert_unified_visual_artifact.call_count == 2


@pytest.mark.asyncio
async def test_store_visual_artifact_cache_expiry(visual_service):
    """Test cache expiry after TTL."""
    # Arrange
    visual_service.cache_ttl = 1  # 1 second TTL for testing
    params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram"
    }
    
    # Act - First call
    result1 = await visual_service.store_visual_artifact(**params)
    assert result1.cache_hit is False
    
    # Wait for cache to expire
    time.sleep(1.5)
    
    # Act - Second call after expiry
    result2 = await visual_service.store_visual_artifact(**params)
    
    # Assert
    assert result2.cache_hit is False
    
    # Verify storage was called twice
    assert visual_service.storage_service.upload_page_image_jpg.call_count == 2
    assert visual_service.artifacts_repo.insert_unified_visual_artifact.call_count == 2


@pytest.mark.asyncio
async def test_store_visual_artifact_error_handling(visual_service, mock_storage_service):
    """Test error handling when storage fails."""
    # Arrange
    mock_storage_service.upload_page_image_jpg.side_effect = Exception("Storage error")
    
    params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram"
    }
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await visual_service.store_visual_artifact(**params)
    
    assert "Storage error" in str(exc_info.value)
    
    # Verify artifact repo was not called
    assert visual_service.artifacts_repo.insert_unified_visual_artifact.call_count == 0
    
    # Verify cache was not updated
    cache_stats = visual_service.get_cache_stats()
    assert cache_stats["total_entries"] == 0


@pytest.mark.asyncio
async def test_cache_key_generation_deterministic(visual_service):
    """Test that cache key generation is deterministic."""
    # Arrange
    params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram",
        "diagram_meta": {"type": "floor_plan", "confidence": 0.95},
        "image_metadata": {"format": "jpeg", "quality": "high"}
    }
    
    # Act
    key1 = visual_service._generate_cache_key(**params)
    key2 = visual_service._generate_cache_key(**params)
    
    # Assert
    assert key1 == key2
    assert len(key1) == 64  # SHA256 hash length in hex


@pytest.mark.asyncio
async def test_cache_key_different_for_different_inputs(visual_service):
    """Test that cache keys are different for different inputs."""
    # Arrange
    base_params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram"
    }
    
    # Act
    key1 = visual_service._generate_cache_key(**base_params)
    key2 = visual_service._generate_cache_key(**{**base_params, "page_number": 2})
    key3 = visual_service._generate_cache_key(**{**base_params, "image_bytes": b"different"})
    key4 = visual_service._generate_cache_key(**{**base_params, "diagram_meta": {"type": "test"}})
    
    # Assert
    assert key1 != key2
    assert key1 != key3
    assert key1 != key4
    assert key2 != key3
    assert key2 != key4
    assert key3 != key4


def test_clear_cache(visual_service):
    """Test cache clearing functionality."""
    # Arrange - Add some items to cache manually
    result = VisualArtifactResult(
        artifact_id="test",
        image_uri="test_uri",
        image_sha256="test_hash",
        cache_hit=False
    )
    visual_service._add_to_cache("test_key", result)
    
    # Verify cache has items
    stats = visual_service.get_cache_stats()
    assert stats["total_entries"] == 1
    
    # Act
    visual_service.clear_cache()
    
    # Assert
    stats = visual_service.get_cache_stats()
    assert stats["total_entries"] == 0


def test_cache_stats(visual_service):
    """Test cache statistics functionality."""
    # Arrange - Add items with different expiry times
    current_time = time.time()
    
    # Active entry
    with visual_service._cache_lock:
        visual_service._cache["key1"] = (
            VisualArtifactResult("id1", "uri1", "hash1", False),
            current_time + 100  # Future expiry
        )
        
        # Expired entry
        visual_service._cache["key2"] = (
            VisualArtifactResult("id2", "uri2", "hash2", False),
            current_time - 100  # Past expiry
        )
    
    # Act
    stats = visual_service.get_cache_stats()
    
    # Assert
    assert stats["total_entries"] == 2
    assert stats["active_entries"] == 1
    assert stats["expired_entries"] == 1


@pytest.mark.asyncio
async def test_store_visual_artifact_with_image_metadata(visual_service):
    """Test storing visual artifact with image metadata."""
    # Arrange
    params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "page_jpg_1",
        "artifact_type": "image_jpg",
        "image_metadata": {
            "format": "jpeg",
            "quality": "high",
            "dpi": "144"
        }
    }
    
    # Act
    result = await visual_service.store_visual_artifact(**params)
    
    # Assert
    assert result.cache_hit is False
    
    # Verify repository was called with correct metadata
    call_args = visual_service.artifacts_repo.insert_unified_visual_artifact.call_args
    assert call_args.kwargs["image_metadata"] == params["image_metadata"]


@pytest.mark.asyncio
async def test_concurrent_cache_access(visual_service):
    """Test thread-safe concurrent cache access."""
    import asyncio
    
    # Arrange
    params = {
        "image_bytes": b"test_image_data",
        "content_hmac": "test_hmac",
        "algorithm_version": 1,
        "params_fingerprint": "test_fingerprint",
        "page_number": 1,
        "diagram_key": "test_diagram",
        "artifact_type": "diagram"
    }
    
    # Act - Multiple concurrent calls
    tasks = [
        visual_service.store_visual_artifact(**params)
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)
    
    # Assert
    # First call should be cache miss
    cache_misses = sum(1 for r in results if not r.cache_hit)
    cache_hits = sum(1 for r in results if r.cache_hit)
    
    # Due to concurrency, we might have 1-5 cache misses
    # but storage should be called at least once
    assert cache_misses >= 1
    assert visual_service.storage_service.upload_page_image_jpg.call_count >= 1
    
    # All results should have same data
    for result in results:
        assert result.artifact_id == "test-artifact-id"
        assert result.image_uri == "supabase://artifacts/test.jpg"
        assert result.image_sha256 == "sha256_test"


@pytest.mark.asyncio
async def test_cache_size_management(visual_service):
    """Test cache size management and eviction."""
    # Set small cache size for testing
    visual_service._max_cache_size = 3
    
    # Fill cache beyond capacity
    for i in range(5):
        params = {
            "image_bytes": f"test_image_{i}".encode(),
            "content_hmac": "test_hmac",
            "algorithm_version": 1,
            "params_fingerprint": "test_fingerprint",
            "page_number": i + 1,
            "diagram_key": f"test_diagram_{i}",
            "artifact_type": "diagram"
        }
        await visual_service.store_visual_artifact(**params)
    
    # Cache should not exceed max size
    stats = visual_service.get_cache_stats()
    assert stats["total_entries"] <= visual_service._max_cache_size


def test_cache_eviction_logic(visual_service):
    """Test the cache eviction logic."""
    import time
    
    # Set small cache size
    visual_service._max_cache_size = 2
    
    current_time = time.time()
    
    # Add entries manually to test eviction
    with visual_service._cache_lock:
        # Add expired entry
        visual_service._cache["expired"] = (
            VisualArtifactResult("id1", "uri1", "hash1", False),
            current_time - 100  # Expired
        )
        
        # Add active entry
        visual_service._cache["active"] = (
            VisualArtifactResult("id2", "uri2", "hash2", False),
            current_time + 100  # Future expiry
        )
        
        # Fill to capacity
        visual_service._cache["new"] = (
            VisualArtifactResult("id3", "uri3", "hash3", False),
            current_time + 200
        )
    
    # Trigger eviction by adding another entry
    result = VisualArtifactResult("id4", "uri4", "hash4", False)
    visual_service._add_to_cache("another", result)
    
    # Should have evicted expired entry first
    assert "expired" not in visual_service._cache
    assert len(visual_service._cache) <= visual_service._max_cache_size


@pytest.mark.asyncio 
async def test_cache_cleanup_expired_method(visual_service):
    """Test the _cleanup_expired_cache method."""
    import time
    
    current_time = time.time()
    
    # Add expired and active entries
    with visual_service._cache_lock:
        visual_service._cache["expired1"] = (
            VisualArtifactResult("id1", "uri1", "hash1", False),
            current_time - 100
        )
        visual_service._cache["expired2"] = (
            VisualArtifactResult("id2", "uri2", "hash2", False),
            current_time - 50
        )
        visual_service._cache["active"] = (
            VisualArtifactResult("id3", "uri3", "hash3", False),
            current_time + 100
        )
    
    # Call cleanup
    visual_service._cleanup_expired_cache()
    
    # Only active entry should remain
    stats = visual_service.get_cache_stats()
    assert stats["total_entries"] == 1
    assert stats["active_entries"] == 1
    assert stats["expired_entries"] == 0