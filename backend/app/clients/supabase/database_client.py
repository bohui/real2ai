"""Supabase database client wrapper providing database operations."""

import logging
from typing import Any, Dict, List, Optional, Union

from supabase import Client
from postgrest.exceptions import APIError

from ..base import BaseClient
from .config import SupabaseClientConfig

logger = logging.getLogger(__name__)


class SupabaseDatabaseClient(BaseClient):
    """Supabase database client for database operations."""

    def __init__(self, supabase_client: Client, config: SupabaseClientConfig):
        """Initialize the database client."""
        super().__init__(config)
        self._supabase_client = supabase_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database client."""
        if self._initialized:
            return

        try:
            # Test connection by running a simple query
            await self.execute_rpc("version", {})
            self._initialized = True
            logger.info("Database client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database client: {e}")
            raise

    def table(self, table_name: str):
        """Get a table reference for queries."""
        return self._supabase_client.table(table_name)

    async def execute_rpc(self, function_name: str, params: Dict[str, Any]) -> Any:
        """Execute an RPC function."""
        try:
            response = self._supabase_client.rpc(function_name, params).execute()
            return response.data
        except APIError as e:
            logger.error(f"RPC call failed for {function_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in RPC call {function_name}: {e}")
            raise

    async def select(
        self,
        table_name: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        desc: bool = False,
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query."""
        try:
            query = self.table(table_name).select(columns)

            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            if order_by:
                query = query.order(order_by, desc=desc)

            if limit:
                query = query.limit(limit)

            if offset:
                query = query.offset(offset)

            response = query.execute()
            return response.data

        except APIError as e:
            logger.error(f"SELECT query failed for table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SELECT query for {table_name}: {e}")
            raise

    async def insert(
        self, table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Execute an INSERT query."""
        try:
            response = self.table(table_name).insert(data).execute()
            return response.data
        except APIError as e:
            logger.error(f"INSERT query failed for table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in INSERT query for {table_name}: {e}")
            raise

    async def update(
        self, table_name: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute an UPDATE query."""
        try:
            query = self.table(table_name).update(data)

            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()
            return response.data

        except APIError as e:
            logger.error(f"UPDATE query failed for table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in UPDATE query for {table_name}: {e}")
            raise

    async def delete(
        self, table_name: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a DELETE query."""
        try:
            query = self.table(table_name).delete()

            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()
            return response.data

        except APIError as e:
            logger.error(f"DELETE query failed for table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in DELETE query for {table_name}: {e}")
            raise

    async def upsert(
        self,
        table_name: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute an UPSERT query."""
        try:
            # supabase-py upsert supports on_conflict as an argument
            if on_conflict:
                response = (
                    self.table(table_name)
                    .upsert(data, on_conflict=on_conflict)
                    .execute()
                )
            else:
                response = self.table(table_name).upsert(data).execute()
            return response.data

        except APIError as e:
            logger.error(f"UPSERT query failed for table {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in UPSERT query for {table_name}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            await self.execute_rpc("version", {})
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the database client."""
        # Supabase client doesn't require explicit closing
        self._initialized = False
        logger.info("Database client closed")
