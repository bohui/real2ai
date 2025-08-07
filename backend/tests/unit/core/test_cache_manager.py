"""
Unit tests for cache manager.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.cache_manager import CacheManager


@pytest.fixture
def cache_manager():
    """Create a cache manager instance for testing."""
    with patch('app.core.cache_manager.redis.Redis') as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.return_value = mock_redis_instance
        cache_mgr = CacheManager(redis_client=mock_redis_instance)
        cache_mgr.redis = mock_redis_instance
        return cache_mgr


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.mark.asyncio
    async def test_set_get_basic(self, cache_manager):
        """Test basic set/get operations."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value", "timestamp": "2024-01-01T12:00:00"}
        serialized_value = json.dumps(value)
        
        cache_manager.redis.set = AsyncMock()
        cache_manager.redis.get = AsyncMock(return_value=serialized_value)
        
        # Act
        await cache_manager.set(key, value, ttl=300)
        result = await cache_manager.get(key)
        
        # Assert
        cache_manager.redis.set.assert_called_once_with(key, serialized_value, ex=300)
        cache_manager.redis.get.assert_called_once_with(key)
        assert result == value

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_manager):
        """Test getting a non-existent key returns None."""
        # Arrange
        cache_manager.redis.get = AsyncMock(return_value=None)
        
        # Act
        result = await cache_manager.get("nonexistent")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_key(self, cache_manager):
        """Test deleting a key."""
        # Arrange
        key = "test_key"
        cache_manager.redis.delete = AsyncMock(return_value=1)
        
        # Act
        result = await cache_manager.delete(key)
        
        # Assert
        cache_manager.redis.delete.assert_called_once_with(key)
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_key(self, cache_manager):
        """Test checking if key exists."""
        # Arrange
        key = "existing_key"
        cache_manager.redis.exists = AsyncMock(return_value=1)
        
        # Act
        result = await cache_manager.exists(key)
        
        # Assert
        cache_manager.redis.exists.assert_called_once_with(key)
        assert result is True

    @pytest.mark.asyncio
    async def test_expire_key(self, cache_manager):
        """Test setting expiration on a key."""
        # Arrange
        key = "test_key"
        ttl = 3600
        cache_manager.redis.expire = AsyncMock(return_value=True)
        
        # Act
        result = await cache_manager.expire(key, ttl)
        
        # Assert
        cache_manager.redis.expire.assert_called_once_with(key, ttl)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_ttl(self, cache_manager):
        """Test getting TTL of a key."""
        # Arrange
        key = "test_key"
        expected_ttl = 1800
        cache_manager.redis.ttl = AsyncMock(return_value=expected_ttl)
        
        # Act
        result = await cache_manager.get_ttl(key)
        
        # Assert
        cache_manager.redis.ttl.assert_called_once_with(key)
        assert result == expected_ttl

    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache_manager):
        """Test clearing keys by pattern."""
        # Arrange
        pattern = "user:*"
        matching_keys = [b"user:1", b"user:2", b"user:3"]
        cache_manager.redis.scan_iter = MagicMock(return_value=iter(matching_keys))
        cache_manager.redis.delete = AsyncMock()
        
        # Act
        count = await cache_manager.clear_pattern(pattern)
        
        # Assert
        cache_manager.redis.scan_iter.assert_called_once_with(match=pattern, count=1000)
        cache_manager.redis.delete.assert_called_once_with(*matching_keys)
        assert count == 3

    @pytest.mark.asyncio
    async def test_serialization_error_handling(self, cache_manager):
        """Test handling of serialization errors."""
        # Arrange
        key = "test_key"
        invalid_data = object()  # Object that can't be JSON serialized
        cache_manager.redis.set = AsyncMock()
        
        # Act & Assert
        with pytest.raises(TypeError):
            await cache_manager.set(key, invalid_data)

    @pytest.mark.asyncio
    async def test_deserialization_error_handling(self, cache_manager):
        """Test handling of deserialization errors."""
        # Arrange
        key = "test_key"
        invalid_json = "invalid json string"
        cache_manager.redis.get = AsyncMock(return_value=invalid_json)
        
        # Act
        result = await cache_manager.get(key)
        
        # Assert - Should return None on deserialization error
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, cache_manager):
        """Test handling of Redis connection errors."""
        # Arrange
        key = "test_key"
        cache_manager.redis.get = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Act
        result = await cache_manager.get(key)
        
        # Assert - Should return None on connection error
        assert result is None

    @pytest.mark.asyncio
    async def test_increment_counter(self, cache_manager):
        """Test incrementing a counter."""
        # Arrange
        key = "counter:test"
        cache_manager.redis.incr = AsyncMock(return_value=5)
        
        # Act
        result = await cache_manager.increment(key)
        
        # Assert
        cache_manager.redis.incr.assert_called_once_with(key)
        assert result == 5

    @pytest.mark.asyncio
    async def test_increment_counter_with_amount(self, cache_manager):
        """Test incrementing a counter by specific amount."""
        # Arrange
        key = "counter:test"
        amount = 10
        cache_manager.redis.incrby = AsyncMock(return_value=25)
        
        # Act
        result = await cache_manager.increment(key, amount)
        
        # Assert
        cache_manager.redis.incrby.assert_called_once_with(key, amount)
        assert result == 25

    @pytest.mark.asyncio
    async def test_batch_operations(self, cache_manager):
        """Test batch get/set operations."""
        # Arrange
        keys = ["key1", "key2", "key3"]
        values = ["value1", "value2", "value3"]
        cache_data = {k: v for k, v in zip(keys, values)}
        
        # Mock pipeline
        mock_pipeline = AsyncMock()
        cache_manager.redis.pipeline = MagicMock(return_value=mock_pipeline)
        mock_pipeline.mget = AsyncMock(return_value=[json.dumps(v) for v in values])
        
        # Act - batch get
        result = await cache_manager.get_many(keys)
        
        # Assert
        assert len(result) == 3
        assert result["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_cache_health_check(self, cache_manager):
        """Test cache health check functionality."""
        # Arrange
        cache_manager.redis.ping = AsyncMock(return_value=True)
        
        # Act
        is_healthy = await cache_manager.health_check()
        
        # Assert
        cache_manager.redis.ping.assert_called_once()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test getting cache statistics."""
        # Arrange
        mock_info = {
            'used_memory': 1024000,
            'connected_clients': 5,
            'keyspace_hits': 1000,
            'keyspace_misses': 100
        }
        cache_manager.redis.info = AsyncMock(return_value=mock_info)
        
        # Act
        stats = await cache_manager.get_stats()
        
        # Assert
        assert stats['memory_used'] == 1024000
        assert stats['connected_clients'] == 5
        assert stats['hit_rate'] > 0.9  # 1000/(1000+100) = 90.9%