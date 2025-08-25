"""
Unit tests for UserContractViewsRepository

Tests verify that the repository correctly handles user contract view
tracking with RLS enforcement.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.repositories.user_contract_views_repository import (
    UserContractViewsRepository
)


class TestUserContractViewsRepository:
    """Test UserContractViewsRepository operations"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = str(uuid4())
        self.content_hash = "test_content_hash_contract_456"
        self.property_address = "456 Contract Ave, Melbourne VIC 3000"
        self.repo = UserContractViewsRepository()

    @pytest.mark.asyncio
    async def test_create_contract_view_success(self):
        """Test successful contract view creation"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": uuid4()}
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.create_contract_view(
                user_id=self.user_id,
                content_hash=self.content_hash,
                property_address=self.property_address,
                source="upload"
            )
            
        assert result is True
        
        # Verify query parameters
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args[0]
        assert "INSERT INTO user_contract_views" in call_args[0]
        assert "ON CONFLICT (user_id, content_hash)" in call_args[0]
        assert isinstance(call_args[1], UUID)  # user_id
        assert call_args[2] == self.content_hash
        assert call_args[3] == self.property_address
        assert call_args[4] == "upload"

    @pytest.mark.asyncio
    async def test_create_contract_view_upsert(self):
        """Test that contract view creation handles conflicts properly"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": uuid4()}
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Create twice with same user_id and content_hash
            result1 = await self.repo.create_contract_view(
                user_id=self.user_id,
                content_hash=self.content_hash
            )
            result2 = await self.repo.create_contract_view(
                user_id=self.user_id,
                content_hash=self.content_hash
            )
            
        assert result1 is True
        assert result2 is True
        
        # Should have been called twice
        assert mock_conn.fetchrow.call_count == 2

    @pytest.mark.asyncio
    async def test_create_contract_view_failure(self):
        """Test handling of contract view creation failure"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("Database error")
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.create_contract_view(
                user_id=self.user_id,
                content_hash=self.content_hash
            )
            
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_contract_views(self):
        """Test retrieving user contract view history"""
        
        mock_rows = [
            {
                "id": uuid4(),
                "user_id": UUID(self.user_id),
                "content_hash": self.content_hash,
                "property_address": self.property_address,
                "source": "analysis",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            results = await self.repo.get_user_contract_views(self.user_id, limit=20)
            
        assert len(results) == 1
        assert results[0]["content_hash"] == self.content_hash
        assert results[0]["property_address"] == self.property_address
        assert results[0]["source"] == "analysis"
        
        # Verify query parameters
        mock_conn.fetch.assert_called_once()
        call_args = mock_conn.fetch.call_args[0]
        assert "SELECT" in call_args[0]
        assert "FROM user_contract_views" in call_args[0]
        assert isinstance(call_args[1], UUID)  # user_id
        assert call_args[2] == 20  # limit

    @pytest.mark.asyncio
    async def test_get_contract_view_by_hash(self):
        """Test retrieving specific contract view by content hash"""
        
        mock_row = {
            "id": uuid4(),
            "user_id": UUID(self.user_id),
            "content_hash": self.content_hash,
            "property_address": self.property_address,
            "source": "upload",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.get_contract_view_by_hash(
                self.user_id, self.content_hash
            )
            
        assert result is not None
        assert result["content_hash"] == self.content_hash
        assert result["source"] == "upload"
        
        # Verify query parameters
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args[0]
        assert "WHERE user_id = $1 AND content_hash = $2" in call_args[0]

    @pytest.mark.asyncio
    async def test_update_contract_view(self):
        """Test updating a contract view"""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.update_contract_view(
                user_id=self.user_id,
                content_hash=self.content_hash,
                property_address="789 New Street",
                source="updated"
            )
            
        assert result is True
        
        # Verify update query
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "UPDATE user_contract_views" in call_args[0]
        assert "SET" in call_args[0]
        assert "property_address" in call_args[0]
        assert "source" in call_args[0]

    @pytest.mark.asyncio
    async def test_update_contract_view_not_found(self):
        """Test updating a non-existent contract view"""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 0"
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.update_contract_view(
                user_id=self.user_id,
                content_hash="nonexistent_hash"
            )
            
        assert result is False

    @pytest.mark.asyncio
    async def test_check_user_has_access(self):
        """Test checking if user has access to content"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            has_access = await self.repo.check_user_has_access(
                self.user_id, self.content_hash
            )
            
        assert has_access is True
        
        # Verify EXISTS query
        mock_conn.fetchval.assert_called_once()
        call_args = mock_conn.fetchval.call_args[0]
        assert "SELECT EXISTS" in call_args[0]
        assert "FROM user_contract_views" in call_args[0]

    @pytest.mark.asyncio
    async def test_check_user_has_no_access(self):
        """Test checking user access when no access exists"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = False
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            has_access = await self.repo.check_user_has_access(
                self.user_id, "restricted_content_hash"
            )
            
        assert has_access is False

    @pytest.mark.asyncio
    async def test_delete_contract_view(self):
        """Test deleting a contract view"""
        
        view_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await self.repo.delete_contract_view(view_id)
            
        assert result is True
        
        # Verify delete query
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "DELETE FROM user_contract_views" in call_args[0]
        assert call_args[1] == view_id

    @pytest.mark.asyncio
    async def test_get_contract_view_stats(self):
        """Test getting contract view statistics"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"total": 25}
        mock_conn.fetch.return_value = [
            {"source": "upload", "count": 15},
            {"source": "analysis", "count": 10}
        ]
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            stats = await self.repo.get_contract_view_stats(self.user_id)
            
        assert stats["total_views"] == 25
        assert stats["by_source"]["upload"] == 15
        assert stats["by_source"]["analysis"] == 10

    @pytest.mark.asyncio
    async def test_uuid_conversion(self):
        """Test that string user_id is properly converted to UUID"""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": uuid4()}
        
        with patch('app.services.repositories.user_contract_views_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            await self.repo.create_contract_view(
                user_id=self.user_id,  # String ID
                content_hash=self.content_hash
            )
            
        # Verify UUID was passed to get_user_connection
        call_args = mock_get_conn.call_args[0]
        assert isinstance(call_args[0], UUID)
        assert str(call_args[0]) == self.user_id