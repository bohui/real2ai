"""
Database connection utilities for artifacts and user repositories
"""

import asyncio
import asyncpg
from typing import Dict, Optional
from uuid import UUID
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Database connection pool manager"""

    _service_pool: Optional[asyncpg.Pool] = None
    _user_pools: Dict[UUID, asyncpg.Pool] = {}

    @classmethod
    async def get_service_pool(cls) -> asyncpg.Pool:
        """Get service role connection pool"""
        if cls._service_pool is None:
            settings = get_settings()

            # Use database_url if available, otherwise construct from Supabase settings
            if settings.database_url:
                dsn = settings.database_url
            else:
                # Extract database URL from Supabase URL
                # Format: https://project.supabase.co -> postgresql://postgres:password@db.project.supabase.co:5432/postgres
                supabase_url = settings.supabase_url.replace("https://", "").replace(
                    "http://", ""
                )
                project_id = supabase_url.split(".")[0]
                dsn = f"postgresql://postgres:{settings.supabase_service_key}@db.{project_id}.supabase.co:5432/postgres"

            try:
                cls._service_pool = await asyncpg.create_pool(
                    dsn, min_size=1, max_size=10, command_timeout=60
                )
                logger.info("Service role connection pool created")
            except Exception as e:
                logger.error(f"Failed to create service role connection pool: {e}")
                raise

        return cls._service_pool

    @classmethod
    async def get_user_pool(cls, user_id: UUID) -> asyncpg.Pool:
        """Get user-specific connection pool (currently same as service pool)"""
        # For now, use service pool for all user operations
        # In the future, this could be enhanced to use per-user connection pools
        # with different authentication contexts
        return await cls.get_service_pool()

    @classmethod
    async def close_all(cls):
        """Close all connection pools"""
        pools_to_close = []

        if cls._service_pool:
            pools_to_close.append(cls._service_pool.close())
            cls._service_pool = None

        for pool in cls._user_pools.values():
            pools_to_close.append(pool.close())
        cls._user_pools.clear()

        if pools_to_close:
            await asyncio.gather(*pools_to_close, return_exceptions=True)
            logger.info("All connection pools closed")


async def get_service_role_connection() -> asyncpg.Connection:
    """
    Get a service role database connection.

    Returns:
        asyncpg.Connection with service role privileges
    """
    pool = await ConnectionPool.get_service_pool()
    return await pool.acquire()


async def get_user_connection(user_id: UUID) -> asyncpg.Connection:
    """
    Get a user-scoped database connection.

    Args:
        user_id: User ID for connection context

    Returns:
        asyncpg.Connection with user context
    """
    pool = await ConnectionPool.get_user_pool(user_id)
    return await pool.acquire()


async def release_connection(connection: asyncpg.Connection):
    """
    Release a database connection back to its pool.

    Args:
        connection: Connection to release
    """
    if connection and not connection.is_closed():
        await connection.close()


async def execute_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> any:
    """
    Execute raw SQL query.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        Query result
    """
    if user_id:
        connection = await get_user_connection(user_id)
    else:
        connection = await get_service_role_connection()

    try:
        return await connection.execute(query, *args)
    finally:
        await release_connection(connection)


async def fetch_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> list:
    """
    Fetch results from raw SQL query.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        List of query results
    """
    if user_id:
        connection = await get_user_connection(user_id)
    else:
        connection = await get_service_role_connection()

    try:
        return await connection.fetch(query, *args)
    finally:
        await release_connection(connection)


async def fetchrow_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> any:
    """
    Fetch single row from raw SQL query.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        Single query result row
    """
    if user_id:
        connection = await get_user_connection(user_id)
    else:
        connection = await get_service_role_connection()

    try:
        return await connection.fetchrow(query, *args)
    finally:
        await release_connection(connection)
