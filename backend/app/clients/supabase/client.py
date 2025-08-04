"""
Main Supabase client implementation.
"""

import logging
from typing import Any, Dict, Optional
from supabase import create_client, Client
from postgrest import APIError

from ..base.client import BaseClient, with_retry
from ..base.exceptions import (
    ClientConnectionError,
    ClientAuthenticationError,
    ClientError,
)
from .config import SupabaseClientConfig
from .auth_client import SupabaseAuthClient
from .database_client import SupabaseDatabaseClient

logger = logging.getLogger(__name__)


class SupabaseClient(BaseClient):
    """Supabase client wrapper providing database and auth operations."""
    
    def __init__(self, config: SupabaseClientConfig):
        super().__init__(config, "SupabaseClient")
        self.config: SupabaseClientConfig = config
        self._supabase_client: Optional[Client] = None
        self._auth_client: Optional[SupabaseAuthClient] = None
        self._db_client: Optional[SupabaseDatabaseClient] = None
    
    @property
    def supabase_client(self) -> Client:
        """Get the underlying Supabase client."""
        if not self._supabase_client:
            raise ClientError("Supabase client not initialized", self.client_name)
        return self._supabase_client
    
    @property
    def auth(self) -> SupabaseAuthClient:
        """Get the auth client."""
        if not self._auth_client:
            raise ClientError("Auth client not initialized", self.client_name)
        return self._auth_client
    
    @property
    def database(self) -> SupabaseDatabaseClient:
        """Get the database client."""
        if not self._db_client:
            raise ClientError("Database client not initialized", self.client_name)
        return self._db_client
    
    @with_retry(max_retries=3, backoff_factor=1.0)
    async def initialize(self) -> None:
        """Initialize Supabase client and sub-clients."""
        try:
            self.logger.info("Initializing Supabase client...")
            
            # Create main Supabase client
            self._supabase_client = create_client(
                self.config.url,
                self.config.anon_key
            )
            
            # Test connection with a simple query
            await self._test_connection()
            
            # Initialize sub-clients
            self._auth_client = SupabaseAuthClient(self._supabase_client, self.config)
            self._db_client = SupabaseDatabaseClient(self._supabase_client, self.config)
            
            await self._auth_client.initialize()
            await self._db_client.initialize()
            
            self._initialized = True
            self.logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize Supabase client: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def _test_connection(self) -> None:
        """Test Supabase connection."""
        try:
            # Try a simple query to test connection
            # Use profiles table as it's likely to exist
            result = self._supabase_client.table("profiles").select("count", count="exact").limit(1).execute()
            self.logger.debug(f"Connection test successful: {result.count is not None}")
            
        except APIError as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                # Table doesn't exist but connection works
                self.logger.debug("Connection test successful (table doesn't exist but connection works)")
                return
            raise ClientConnectionError(
                f"Supabase connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
        except Exception as e:
            raise ClientConnectionError(
                f"Supabase connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Supabase client."""
        try:
            # Test connection
            await self._test_connection()
            
            # Check sub-clients
            auth_health = await self._auth_client.health_check() if self._auth_client else {"status": "not_initialized"}
            db_health = await self._db_client.health_check() if self._db_client else {"status": "not_initialized"}
            
            overall_status = "healthy"
            if auth_health.get("status") != "healthy" or db_health.get("status") != "healthy":
                overall_status = "degraded"
            
            return {
                "status": overall_status,
                "client_name": self.client_name,
                "initialized": self._initialized,
                "connection": "ok",
                "auth_status": auth_health.get("status", "unknown"),
                "database_status": db_health.get("status", "unknown"),
                "config": {
                    "url": self.config.url[:50] + "..." if len(self.config.url) > 50 else self.config.url,
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                }
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }
    
    async def close(self) -> None:
        """Close Supabase client and clean up resources."""
        try:
            if self._auth_client:
                await self._auth_client.close()
                self._auth_client = None
            
            if self._db_client:
                await self._db_client.close()
                self._db_client = None
            
            if self._supabase_client:
                # Supabase client doesn't require explicit closing
                self._supabase_client = None
            
            self._initialized = False
            self.logger.info("Supabase client closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing Supabase client: {e}")
            raise ClientError(
                f"Error closing Supabase client: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    # Convenience methods that delegate to sub-clients
    
    def table(self, table_name: str):
        """Get table client (database operation)."""
        return self.database.table(table_name)
    
    def from_(self, table_name: str):
        """Get table client using from_ syntax."""
        return self.database.from_(table_name)
    
    def storage(self):
        """Get storage client."""
        return self.supabase_client.storage
    
    async def execute_rpc(self, function_name: str, params: Dict[str, Any] = None):
        """Execute RPC function."""
        return await self.database.execute_rpc(function_name, params)
    
    async def authenticate_user(self, token: str):
        """Authenticate user with token."""
        return await self.auth.authenticate_user(token)
    
    async def get_user(self, user_id: str):
        """Get user by ID."""
        return await self.auth.get_user(user_id)