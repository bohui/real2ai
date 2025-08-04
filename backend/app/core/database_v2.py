"""
Migrated Database client for Real2.AI using decoupled client architecture
This replaces the direct Supabase instantiation with the new client factory system
"""

from typing import Optional, Any, Dict
import asyncio
import logging

from app.clients.factory import get_supabase_client
from app.clients.base.interfaces import DatabaseOperations
from app.clients.base.exceptions import ClientError

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service using decoupled client architecture"""
    
    def __init__(self, supabase_client: DatabaseOperations = None):
        """Initialize with optional dependency injection for testing"""
        self._supabase_client = supabase_client
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database service"""
        try:
            if not self._supabase_client:
                self._supabase_client = await get_supabase_client()
            
            # Test connection through the decoupled client
            await self._test_connection()
            self._initialized = True
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database service: {str(e)}")
            raise
    
    async def _test_connection(self) -> None:
        """Test database connection using decoupled client"""
        try:
            # Use the standardized interface method
            result = await self._supabase_client.database.read(
                table="profiles", 
                filters={}, 
                limit=1
            )
            logger.info("Database connection test successful")
        except ClientError as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {str(e)}")
            raise ClientError(f"Database connection test failed: {str(e)}")
    
    async def close(self) -> None:
        """Close database connections"""
        if self._supabase_client and hasattr(self._supabase_client, 'close'):
            await self._supabase_client.close()
        self._initialized = False
        logger.info("Database service closed")
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized and self._supabase_client is not None
    
    @property
    def database(self) -> DatabaseOperations:
        """Get database client with initialization check"""
        if not self.is_initialized:
            raise RuntimeError("Database service not initialized. Call initialize() first.")
        return self._supabase_client.database
    
    @property 
    def auth(self):
        """Get auth client"""
        if not self.is_initialized:
            raise RuntimeError("Database service not initialized. Call initialize() first.")
        return self._supabase_client.auth
    
    @property
    def storage(self):
        """Get storage client"""  
        if not self.is_initialized:
            raise RuntimeError("Database service not initialized. Call initialize() first.")
        return self._supabase_client.storage
    
    # Convenience methods using the decoupled interface
    async def create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a record using decoupled client"""
        try:
            return await self.database.create(table, data)
        except ClientError as e:
            logger.error(f"Failed to create record in {table}: {str(e)}")
            raise
    
    async def read_records(self, table: str, filters: Dict[str, Any] = None, limit: Optional[int] = None) -> list:
        """Read records using decoupled client"""
        try:
            filters = filters or {}
            return await self.database.read(table, filters, limit)
        except ClientError as e:
            logger.error(f"Failed to read records from {table}: {str(e)}")
            raise
    
    async def update_record(self, table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record using decoupled client"""
        try:
            return await self.database.update(table, record_id, data)
        except ClientError as e:
            logger.error(f"Failed to update record {record_id} in {table}: {str(e)}")
            raise
    
    async def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record using decoupled client"""
        try:
            return await self.database.delete(table, record_id)
        except ClientError as e:
            logger.error(f"Failed to delete record {record_id} from {table}: {str(e)}")
            raise
    
    async def upsert_record(self, table: str, data: Dict[str, Any], conflict_columns: list = None) -> Dict[str, Any]:
        """Upsert a record using decoupled client"""
        try:
            return await self.database.upsert(table, data, conflict_columns)
        except ClientError as e:
            logger.error(f"Failed to upsert record in {table}: {str(e)}")
            raise
    
    async def execute_rpc(self, function_name: str, params: Dict[str, Any] = None) -> Any:
        """Execute RPC using decoupled client"""
        try:
            return await self.database.execute_rpc(function_name, params)
        except ClientError as e:
            logger.error(f"Failed to execute RPC {function_name}: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on database service"""
        try:
            if not self.is_initialized:
                return {
                    "status": "unhealthy",
                    "error": "Service not initialized"
                }
            
            # Test a simple query
            await self.read_records("profiles", {}, 1)
            
            return {
                "status": "healthy",
                "service": "database_service_v2",
                "client_architecture": "decoupled",
                "features": [
                    "dependency_injection",
                    "error_handling", 
                    "circuit_breakers",
                    "automatic_retries",
                    "connection_pooling"
                ]
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }


# Global service instance
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get database service singleton"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service


async def init_database() -> None:
    """Initialize database service"""
    service = get_database_service()
    await service.initialize()


async def close_database() -> None:
    """Close database service"""
    global _database_service
    if _database_service:
        await _database_service.close()
        _database_service = None


# Backward compatibility functions
def get_database_client() -> DatabaseService:
    """Backward compatibility: Get database service"""
    return get_database_service()