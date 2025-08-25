"""
Unit tests for UserPropertyViewsRepository

Tests verify that the repository correctly handles user property view
tracking with RLS enforcement.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.repositories.user_property_views_repository import (
    UserPropertyViewsRepository
)


class TestUserPropertyViewsRepository:
    """Test UserPropertyViewsRepository operations"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = str(uuid4())
        self.property_hash = "test_property_hash_123"
        self.property_address = "123 Test Street, Sydney NSW 2000"
        self.repo = UserPropertyViewsRepository()

    @pytest.mark.asyncio
    async def test_create_property_view_success(self):
        """Test successful property view creation"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": uuid4()}
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.create_property_view(
                user_id=self.user_id,
                property_hash=self.property_hash,
                property_address=self.property_address,
                source="search"
            )
            
        assert result is True
        
        # Verify query parameters
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args[0]
        assert "INSERT INTO user_property_views" in call_args[0]
        assert isinstance(call_args[1], UUID)  # user_id
        assert call_args[2] == self.property_hash
        assert call_args[3] == self.property_address
        assert call_args[4] == "search"

    @pytest.mark.asyncio
    async def test_create_property_view_failure(self):
        """Test handling of property view creation failure"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("Database error")
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.create_property_view(
                user_id=self.user_id,
                property_hash=self.property_hash
            )
            
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_property_views(self):
        """Test retrieving user property view history"""
        
        mock_rows = [
            {
                "id": uuid4(),
                "user_id": UUID(self.user_id),
                "property_hash": self.property_hash,
                "property_address": self.property_address,
                "source": "search",
                "viewed_at": datetime.now(),
                "created_at": datetime.now()
            }
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            results = await self.repo.get_user_property_views(self.user_id, limit=10)
            
        assert len(results) == 1
        assert results[0]["property_hash"] == self.property_hash
        assert results[0]["property_address"] == self.property_address
        assert results[0]["source"] == "search"
        
        # Verify query parameters
        mock_conn.fetch.assert_called_once()
        call_args = mock_conn.fetch.call_args[0]
        assert "SELECT" in call_args[0]
        assert "FROM user_property_views" in call_args[0]
        assert isinstance(call_args[1], UUID)  # user_id
        assert call_args[2] == 10  # limit

    @pytest.mark.asyncio
    async def test_get_property_view_by_hash(self):
        """Test retrieving specific property view by hash"""
        
        mock_row = {
            "id": uuid4(),
            "user_id": UUID(self.user_id),
            "property_hash": self.property_hash,
            "property_address": self.property_address,
            "source": "bookmark",
            "viewed_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.get_property_view_by_hash(
                self.user_id, self.property_hash
            )
            
        assert result is not None
        assert result["property_hash"] == self.property_hash
        assert result["source"] == "bookmark"
        
        # Verify query parameters
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args[0]
        assert "WHERE user_id = $1 AND property_hash = $2" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_property_view_by_hash_not_found(self):
        """Test handling when property view is not found"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.get_property_view_by_hash(
                self.user_id, "nonexistent_hash"
            )
            
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_property_view(self):
        """Test deleting a property view"""
        
        view_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.delete_property_view(view_id)
            
        assert result is True
        
        # Verify delete query
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "DELETE FROM user_property_views" in call_args[0]
        assert call_args[1] == view_id

    @pytest.mark.asyncio
    async def test_get_property_view_stats(self):
        """Test getting property view statistics"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"total": 10}
        mock_conn.fetch.return_value = [
            {"source": "search", "count": 7},
            {"source": "bookmark", "count": 3}
        ]
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            stats = await self.repo.get_property_view_stats(self.user_id)
            
        assert stats["total_views"] == 10
        assert stats["by_source"]["search"] == 7
        assert stats["by_source"]["bookmark"] == 3

    @pytest.mark.asyncio
    async def test_uuid_conversion(self):
        """Test that string user_id is properly converted to UUID"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": uuid4()}
        
        with patch('app.services.repositories.user_property_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            await self.repo.create_property_view(
                user_id=self.user_id,  # String ID
                property_hash=self.property_hash
            )
            
        # Verify UUID was passed to get_user_connection
        call_args = mock_get_conn.call_args[0]
        assert isinstance(call_args[0], UUID)
        assert str(call_args[0]) == self.user_id