"""
Unit tests for cache manager.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.core.cache_manager import CacheManager


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    service = AsyncMock()
    # Add all methods we need to mock
    service.get_cache_stats = AsyncMock()
    service.validate_hash_consistency = AsyncMock()
    service.cleanup_expired_cache = AsyncMock()
    service.db_client = AsyncMock()
    return service


@pytest.fixture
def cache_manager(mock_cache_service):
    """Create a cache manager instance for testing."""
    with patch('app.core.cache_manager.get_supabase_client'):
        cache_mgr = CacheManager()
        cache_mgr.cache_service = mock_cache_service
        cache_mgr.initialized = True
        return cache_mgr


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful cache manager initialization."""
        # Arrange
        with patch('app.core.cache_manager.get_supabase_client') as mock_client, \
             patch('app.core.cache_manager.CacheService') as mock_service_class:
            
            mock_db_client = AsyncMock()
            mock_client.return_value = mock_db_client
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            cache_mgr = CacheManager()
            
            # Act
            await cache_mgr.initialize()
            
            # Assert
            assert cache_mgr.initialized is True
            assert cache_mgr.cache_service is not None
            mock_client.assert_called_once_with(use_service_role=True)
            mock_service.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_manager, mock_cache_service):
        """Test getting cache statistics."""
        # Arrange
        expected_stats = {
            'cache_hit_rate': 0.85,
            'total_entries': 1000,
            'memory_usage': '100MB'
        }
        expected_consistency = {
            'total_documents': 500,
            'consistent_hashes': 495,
            'inconsistencies': 5
        }
        
        mock_cache_service.get_cache_stats.return_value = expected_stats
        mock_cache_service.validate_hash_consistency.return_value = expected_consistency
        
        # Act
        result = await cache_manager.get_stats()
        
        # Assert
        mock_cache_service.get_cache_stats.assert_called_once()
        mock_cache_service.validate_hash_consistency.assert_called_once()
        assert 'cache_stats' in result
        assert 'hash_consistency' in result
        assert 'timestamp' in result
        assert result['cache_stats'] == expected_stats
        assert result['hash_consistency'] == expected_consistency

    def test_ensure_initialized_not_initialized(self):
        """Test that operations fail when not initialized."""
        # Arrange
        cache_mgr = CacheManager()
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Cache manager not initialized"):
            cache_mgr._ensure_initialized()

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache_manager, mock_cache_service):
        """Test cleaning up expired cache entries."""
        # Arrange
        expected_result = {
            'deleted_count': 25,
            'tables_cleaned': ['analyses_cache', 'property_cache']
        }
        mock_cache_service.cleanup_expired_cache.return_value = expected_result
        
        # Act
        result = await cache_manager.cleanup_expired()
        
        # Assert
        mock_cache_service.cleanup_expired_cache.assert_called_once()
        assert result == expected_result
        assert result['deleted_count'] == 25

    @pytest.mark.asyncio
    async def test_validate_integrity(self, cache_manager, mock_cache_service):
        """Test cache integrity validation."""
        # Arrange
        expected_stats = {
            'analyses': {'total': 100},
            'property_data': {'total': 50}
        }
        expected_consistency = {
            'table1': {'consistency_percentage': 95},
            'table2': {'consistency_percentage': 100}
        }
        
        mock_cache_service.get_cache_stats.return_value = expected_stats
        mock_cache_service.validate_hash_consistency.return_value = expected_consistency
        
        # Act
        result = await cache_manager.validate_integrity()
        
        # Assert
        mock_cache_service.get_cache_stats.assert_called_once()
        mock_cache_service.validate_hash_consistency.assert_called_once()
        assert 'status' in result
        assert 'issues' in result
        assert 'warnings' in result
        assert 'timestamp' in result
        # Should have warning due to table1 having 95% consistency
        assert len(result['warnings']) > 0

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test initialization failure handling."""
        # Arrange
        with patch('app.core.cache_manager.get_supabase_client') as mock_client:
            mock_client.side_effect = Exception("Database connection failed")
            cache_mgr = CacheManager()
            
            # Act & Assert
            with pytest.raises(Exception, match="Database connection failed"):
                await cache_mgr.initialize()
                
            assert cache_mgr.initialized is False
    
    @pytest.mark.asyncio
    async def test_rebuild_cache(self, cache_manager, mock_cache_service):
        """Test cache rebuilding functionality."""
        # Arrange
        mock_cache_service.db_client = AsyncMock()
        mock_cache_service.db_client.rpc.return_value = 150
        
        # Act
        result = await cache_manager.rebuild_cache(
            min_confidence=0.8,
            days_back=14,
            max_entries=500
        )
        
        # Assert
        mock_cache_service.db_client.rpc.assert_called_once_with(
            "rebuild_contract_cache",
            {
                "min_confidence": 0.8,
                "days_back": 14,
                "max_entries": 500
            }
        )
        assert result == 150