"""
Tests for the clear_data.py script functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.clear_data import DatabaseCleaner, normalize_tables


class TestNormalizeTables:
    """Test the normalize_tables function"""

    def test_normalize_tables_with_none(self):
        """Test normalizing tables with None input returns default order"""
        result = normalize_tables(None)
        
        # Should return all default tables in dependency order
        assert isinstance(result, list)
        assert len(result) > 0
        assert "documents" in result
        assert "contracts" in result
        assert "artifacts_full_text" in result

    def test_normalize_tables_with_comma_separated(self):
        """Test normalizing tables with comma-separated input"""
        result = normalize_tables("documents,contracts")
        
        assert result == ["contracts", "documents"]  # Should be sorted by dependency order

    def test_normalize_tables_with_unknown_table(self):
        """Test normalizing tables with unknown table raises ValueError"""
        with pytest.raises(ValueError) as excinfo:
            normalize_tables("documents,unknown_table")
        
        assert "Unknown tables requested" in str(excinfo.value)
        assert "unknown_table" in str(excinfo.value)

    def test_normalize_tables_with_whitespace(self):
        """Test normalizing tables handles whitespace correctly"""
        result = normalize_tables(" documents , contracts ")
        
        assert result == ["contracts", "documents"]


class TestDatabaseCleaner:
    """Test the DatabaseCleaner class"""

    def test_database_cleaner_init(self):
        """Test DatabaseCleaner initialization"""
        cleaner = DatabaseCleaner(
            db_url="test://url",
            use_service_role=False,
            clear_storage=True
        )
        
        assert cleaner.db_url == "test://url"
        assert cleaner.use_service_role is False
        assert cleaner.clear_storage is True

    def test_database_cleaner_default_values(self):
        """Test DatabaseCleaner default values"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        assert cleaner.use_service_role is True
        assert cleaner.clear_storage is False

    @pytest.mark.asyncio
    async def test_table_exists_true(self):
        """Test _table_exists returns True for existing table"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        
        result = await cleaner._table_exists(mock_conn, "documents")
        
        assert result is True
        mock_conn.fetchval.assert_called_once_with(
            "SELECT to_regclass($1) IS NOT NULL", "documents"
        )

    @pytest.mark.asyncio
    async def test_table_exists_false(self):
        """Test _table_exists returns False for non-existing table"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = False
        
        result = await cleaner._table_exists(mock_conn, "nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_table_exists_exception(self):
        """Test _table_exists returns False on exception"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("Database error")
        
        result = await cleaner._table_exists(mock_conn, "documents")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_row_count_success(self):
        """Test _get_row_count returns correct count"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"count": 42}
        
        result = await cleaner._get_row_count(mock_conn, "documents")
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_row_count_exception(self):
        """Test _get_row_count returns -1 on exception"""
        cleaner = DatabaseCleaner(db_url="test://url")
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("Database error")
        
        result = await cleaner._get_row_count(mock_conn, "documents")
        
        assert result == -1

    @pytest.mark.asyncio
    async def test_clear_storage_bucket_disabled(self):
        """Test clear_storage_bucket when storage clearing is disabled"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=False)
        
        result = await cleaner.clear_storage_bucket()
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_clear_storage_bucket_empty(self):
        """Test clear_storage_bucket when bucket is empty"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        with patch("scripts.clear_data.get_service_supabase_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_storage = MagicMock()
            mock_storage.list.return_value = []
            mock_client.storage.return_value.from_.return_value = mock_storage
            mock_get_client.return_value = mock_client
            
            result = await cleaner.clear_storage_bucket()
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_clear_storage_bucket_with_files(self):
        """Test clear_storage_bucket successfully deletes files"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        # Mock file objects
        mock_file1 = MagicMock()
        mock_file1.name = "file1.txt"
        mock_file2 = MagicMock()
        mock_file2.name = "file2.pdf"
        
        with patch("scripts.clear_data.get_service_supabase_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_storage = MagicMock()
            mock_storage.list.return_value = [mock_file1, mock_file2]
            mock_storage.remove.return_value = True
            mock_client.storage.return_value.from_.return_value = mock_storage
            mock_get_client.return_value = mock_client
            
            result = await cleaner.clear_storage_bucket()
            
            assert result == 2
            mock_storage.remove.assert_called()

    @pytest.mark.asyncio
    async def test_clear_storage_bucket_import_error(self):
        """Test clear_storage_bucket handles import error gracefully"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        with patch("scripts.clear_data.get_service_supabase_client", side_effect=ImportError):
            result = await cleaner.clear_storage_bucket()
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_clear_storage_bucket_not_found(self):
        """Test clear_storage_bucket handles bucket not found"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        with patch("scripts.clear_data.get_service_supabase_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_storage = MagicMock()
            mock_storage.list.side_effect = Exception("bucket not found")
            mock_client.storage.return_value.from_.return_value = mock_storage
            mock_get_client.return_value = mock_client
            
            result = await cleaner.clear_storage_bucket()
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_clear_with_delete_calls_storage_clear(self):
        """Test that clear_with_delete calls storage clearing when enabled"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        with patch.object(cleaner, "clear_storage_bucket", return_value=5) as mock_clear_storage, \
             patch("scripts.clear_data.get_service_role_connection") as mock_conn:
            
            # Mock database connection
            mock_context = AsyncMock()
            mock_conn.return_value = mock_context
            mock_context.__aenter__.return_value = AsyncMock()
            
            await cleaner.clear_with_delete([])
            
            mock_clear_storage.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_with_truncate_calls_storage_clear(self):
        """Test that clear_with_truncate calls storage clearing when enabled"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=True)
        
        with patch.object(cleaner, "clear_storage_bucket", return_value=5) as mock_clear_storage, \
             patch("scripts.clear_data.get_service_role_connection") as mock_conn:
            
            # Mock database connection
            mock_context = AsyncMock()
            mock_conn.return_value = mock_context
            mock_context.__aenter__.return_value = AsyncMock()
            
            await cleaner.clear_with_truncate([])
            
            mock_clear_storage.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_with_delete_skips_storage_when_disabled(self):
        """Test that clear_with_delete skips storage clearing when disabled"""
        cleaner = DatabaseCleaner(db_url="test://url", clear_storage=False)
        
        with patch.object(cleaner, "clear_storage_bucket") as mock_clear_storage, \
             patch("scripts.clear_data.get_service_role_connection") as mock_conn:
            
            # Mock database connection
            mock_context = AsyncMock()
            mock_conn.return_value = mock_context
            mock_context.__aenter__.return_value = AsyncMock()
            
            await cleaner.clear_with_delete([])
            
            mock_clear_storage.assert_not_called()