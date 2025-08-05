"""
Database client for Real2.AI using Supabase
"""

from typing import Optional, Any, Dict
import asyncio
import logging
from supabase import create_client, Client
from postgrest import APIError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Supabase database client wrapper"""
    
    def __init__(self, use_service_role: bool = False):
        self._client: Optional[Client] = None
        self._settings = get_settings()
        self._use_service_role = use_service_role
    
    async def initialize(self):
        """Initialize database connection"""
        try:
            # Use service role key for background tasks to bypass RLS
            api_key = (
                self._settings.supabase_service_key 
                if self._use_service_role 
                else self._settings.supabase_anon_key
            )
            
            self._client = create_client(
                self._settings.supabase_url,
                api_key
            )
            
            # Test connection
            await self._test_connection()
            connection_type = "service role" if self._use_service_role else "anon"
            logger.info(f"Database connection established ({connection_type})")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def _test_connection(self):
        """Test database connection"""
        try:
            # Simple query to test connection
            result = self._client.table("profiles").select("count", count="exact").limit(1).execute()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self._client:
            # Supabase client doesn't require explicit closing
            self._client = None
            logger.info("Database connection closed")
    
    @property
    def client(self) -> Client:
        """Get Supabase client"""
        if not self._client:
            raise RuntimeError("Database client not initialized")
        return self._client
    
    @property
    def auth(self):
        """Get Supabase auth client"""
        return self.client.auth
    
    def table(self, table_name: str):
        """Get table client"""
        return self.client.table(table_name)
    
    def storage(self):
        """Get storage client"""
        return self.client.storage
    
    def from_(self, table_name: str):
        """Get table client (alternative syntax)"""
        return self.client.from_(table_name)
    
    async def execute_rpc(self, function_name: str, params: Dict[str, Any] = None):
        """Execute stored procedure/function"""
        try:
            if params:
                result = self.client.rpc(function_name, params).execute()
            else:
                result = self.client.rpc(function_name).execute()
            return result
        except APIError as e:
            logger.error(f"RPC execution failed: {str(e)}")
            raise


# Global database client instances
_db_client: Optional[DatabaseClient] = None
_service_db_client: Optional[DatabaseClient] = None


def get_database_client() -> DatabaseClient:
    """Get database client singleton (anon key)"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient(use_service_role=False)
    return _db_client


def get_service_database_client() -> DatabaseClient:
    """Get service role database client singleton for background tasks"""
    global _service_db_client
    if _service_db_client is None:
        _service_db_client = DatabaseClient(use_service_role=True)
    return _service_db_client


async def init_database():
    """Initialize database connection"""
    client = get_database_client()
    await client.initialize()


async def close_database():
    """Close database connections"""
    global _db_client, _service_db_client
    if _db_client:
        await _db_client.close()
        _db_client = None
    if _service_db_client:
        await _service_db_client.close()
        _service_db_client = None