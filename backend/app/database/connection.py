"""
Database connection utilities with JWT-based RLS enforcement
"""

import asyncio
import asyncpg
import json
import time
from collections import OrderedDict
from typing import Dict, Optional, Any, AsyncContextManager, AsyncGenerator
from uuid import UUID
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.core.auth_context import AuthContext

logger = logging.getLogger(__name__)


class UserPoolInfo:
    """Information about a user-specific connection pool"""

    def __init__(self, pool: asyncpg.Pool, user_id: UUID):
        self.pool = pool
        self.user_id = user_id
        self.last_accessed = time.time()
        self.created_at = time.time()

    def touch(self):
        """Update last accessed time"""
        self.last_accessed = time.time()


class ConnectionPoolManager:
    """Enhanced database connection pool manager with JWT-based RLS enforcement"""

    _service_pool: Optional[asyncpg.Pool] = None
    _user_pools: OrderedDict[UUID, UserPoolInfo] = OrderedDict()
    _pool_lock = asyncio.Lock()
    _metrics: Dict[str, int] = {
        "active_user_pools": 0,
        "evictions": 0,
        "pool_hits": 0,
        "pool_misses": 0,
    }

    @classmethod
    async def get_service_pool(cls) -> asyncpg.Pool:
        """Get service role connection pool"""
        if cls._service_pool is None:
            settings = get_settings()
            dsn = cls._get_database_dsn()

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
        """Get user-specific connection pool based on configured mode"""
        settings = get_settings()

        if settings.db_pool_mode == "per_user":
            return await cls._get_per_user_pool(user_id)
        else:
            # Shared mode - use service pool with session GUCs
            return await cls.get_service_pool()

    @classmethod
    async def _get_per_user_pool(cls, user_id: UUID) -> asyncpg.Pool:
        """Get or create per-user connection pool"""
        async with cls._pool_lock:
            settings = get_settings()

            # Check if pool exists and touch it
            if user_id in cls._user_pools:
                pool_info = cls._user_pools[user_id]
                pool_info.touch()
                # Move to end for LRU
                cls._user_pools.move_to_end(user_id)
                cls._metrics["pool_hits"] += 1
                return pool_info.pool

            cls._metrics["pool_misses"] += 1

            # Enforce max pools limit
            if len(cls._user_pools) >= settings.db_max_active_user_pools:
                await cls._evict_least_recently_used()

            # Create new pool
            dsn = cls._get_database_dsn()

            try:
                pool = await asyncpg.create_pool(
                    dsn,
                    min_size=settings.db_user_pool_min_size,
                    max_size=settings.db_user_pool_max_size,
                    command_timeout=60,
                )

                pool_info = UserPoolInfo(pool, user_id)
                cls._user_pools[user_id] = pool_info
                cls._metrics["active_user_pools"] = len(cls._user_pools)

                logger.info(f"Created per-user connection pool for user {user_id}")
                return pool

            except Exception as e:
                logger.error(f"Failed to create user pool for {user_id}: {e}")
                # Fallback to service pool
                return await cls.get_service_pool()

    @classmethod
    async def _evict_least_recently_used(cls):
        """Evict the least recently used pool"""
        if not cls._user_pools:
            return

        settings = get_settings()
        current_time = time.time()

        # First, try to evict idle pools
        to_evict = []
        for user_id, pool_info in cls._user_pools.items():
            if (
                current_time - pool_info.last_accessed
                > settings.db_user_pool_idle_ttl_seconds
            ):
                to_evict.append(user_id)

        if to_evict:
            for user_id in to_evict:
                await cls._close_user_pool(user_id)
        else:
            # No idle pools, evict LRU
            oldest_user_id = next(iter(cls._user_pools))
            await cls._close_user_pool(oldest_user_id)

    @classmethod
    async def _close_user_pool(cls, user_id: UUID):
        """Close and remove a specific user pool"""
        if user_id in cls._user_pools:
            pool_info = cls._user_pools.pop(user_id)
            try:
                await pool_info.pool.close()
                cls._metrics["evictions"] += 1
                cls._metrics["active_user_pools"] = len(cls._user_pools)
                logger.info(f"Evicted connection pool for user {user_id}")
            except Exception as e:
                logger.error(f"Error closing user pool for {user_id}: {e}")

    @classmethod
    def _get_database_dsn(cls) -> str:
        """Get database DSN from settings"""
        settings = get_settings()

        if settings.database_url:
            return settings.database_url

        # Extract database URL from Supabase URL
        supabase_url = settings.supabase_url.replace("https://", "").replace(
            "http://", ""
        )
        project_id = supabase_url.split(".")[0]
        return f"postgresql://postgres:{settings.supabase_service_key}@db.{project_id}.supabase.co:5432/postgres"

    @classmethod
    async def cleanup_expired_pools(cls):
        """Clean up expired pools based on TTL"""
        async with cls._pool_lock:
            settings = get_settings()
            current_time = time.time()
            expired_users = []

            for user_id, pool_info in cls._user_pools.items():
                if (
                    current_time - pool_info.last_accessed
                    > settings.db_user_pool_idle_ttl_seconds
                ):
                    expired_users.append(user_id)

            for user_id in expired_users:
                await cls._close_user_pool(user_id)

    @classmethod
    async def close_all(cls):
        """Close all connection pools"""
        async with cls._pool_lock:
            pools_to_close = []

            if cls._service_pool:
                pools_to_close.append(cls._service_pool.close())
                cls._service_pool = None

            for pool_info in cls._user_pools.values():
                pools_to_close.append(pool_info.pool.close())
            cls._user_pools.clear()

            if pools_to_close:
                await asyncio.gather(*pools_to_close, return_exceptions=True)

            cls._metrics = {
                "active_user_pools": 0,
                "evictions": 0,
                "pool_hits": 0,
                "pool_misses": 0,
            }
            logger.info("All connection pools closed")

    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        """Get connection pool metrics"""
        cls._metrics["active_user_pools"] = len(cls._user_pools)
        return cls._metrics.copy()


async def _setup_user_session(
    connection: asyncpg.Connection, user_id: Optional[UUID] = None
):
    """
    Set up user session with JWT claims for RLS enforcement.

    Args:
        connection: Database connection
        user_id: Optional user ID (uses auth context if not provided)
    """
    if user_id is None:
        user_id_str = AuthContext.get_user_id()
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                logger.warning(f"Invalid user ID format in auth context: {user_id_str}")
                user_id = None

    # Get user token from auth context
    user_token = AuthContext.get_user_token()

    if user_token and user_id:
        try:
            # Parse JWT token to extract claims
            import jwt
            from app.core.config import get_settings

            settings = get_settings()
            # Decode without verification for now (Supabase handles verification)
            claims = jwt.decode(user_token, options={"verify_signature": False})

            # Set session GUCs for RLS
            await connection.execute(
                "SELECT set_config('request.jwt.claims', $1, false)", json.dumps(claims)
            )
            await connection.execute(
                "SELECT set_config('role', $1, false)", "authenticated"
            )
            await connection.execute(
                "SELECT set_config('request.jwt.claim.sub', $1, false)", str(user_id)
            )

            logger.debug(f"Set user session context for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to set user session context: {e}")
            # Set minimal auth context
            await connection.execute(
                "SELECT set_config('role', $1, false)", "authenticated"
            )
            await connection.execute(
                "SELECT set_config('request.jwt.claim.sub', $1, false)", str(user_id)
            )
    else:
        # No user context - set anonymous role
        await connection.execute("SELECT set_config('role', $1, false)", "anon")


async def _reset_session_gucs(connection: asyncpg.Connection):
    """
    Reset session GUCs to prevent claim bleed-over in shared pools.

    Args:
        connection: Database connection
    """
    try:
        await connection.execute("SELECT set_config('request.jwt.claims', NULL, false)")
        await connection.execute("SELECT set_config('role', 'anon', false)")
        await connection.execute(
            "SELECT set_config('request.jwt.claim.sub', NULL, false)"
        )
    except Exception as e:
        logger.error(f"Failed to reset session GUCs: {e}")


async def _setup_service_session(connection: asyncpg.Connection):
    """
    Set up a service-role session so RLS policies that rely on auth.jwt() pass.

    Supabase RLS policies often check auth.jwt()->>'role' = 'service_role'. When
    connecting directly to Postgres (asyncpg), we must set the same GUCs that
    PostgREST would set.
    """
    try:
        claims = {"role": "service_role"}
        await connection.execute(
            "SELECT set_config('request.jwt.claims', $1, false)", json.dumps(claims)
        )
        await connection.execute("SELECT set_config('role', $1, false)", "service_role")
        logger.debug("Set service-role session context for connection")
    except Exception as e:
        logger.error(f"Failed to set service session context: {e}")


@asynccontextmanager
async def get_service_role_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get a service role database connection with context management.

    Returns:
        AsyncContextManager[asyncpg.Connection] with service role privileges
    """
    pool = await ConnectionPoolManager.get_service_pool()
    connection = await pool.acquire()

    try:
        # Ensure service-role RLS context is present for this connection
        await _setup_service_session(connection)
        yield connection
    finally:
        await pool.release(connection)


@asynccontextmanager
async def get_user_connection(
    user_id: Optional[UUID] = None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get a user-scoped database connection with JWT-based RLS enforcement.

    Args:
        user_id: User ID for connection context (uses auth context if not provided)

    Returns:
        AsyncContextManager[asyncpg.Connection] with user RLS context
    """
    settings = get_settings()

    # Determine user ID
    if user_id is None:
        user_id_str = AuthContext.get_user_id()
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                logger.warning(f"Invalid user ID format in auth context: {user_id_str}")
                raise ValueError("Invalid user ID format")
        else:
            raise ValueError("No user ID provided and none in auth context")

    pool = await ConnectionPoolManager.get_user_pool(user_id)
    connection = await pool.acquire()

    try:
        # Set up user session context
        await _setup_user_session(connection, user_id)
        yield connection
    finally:
        # Reset GUCs in shared mode to prevent bleed-over
        if settings.db_pool_mode == "shared":
            await _reset_session_gucs(connection)

        await pool.release(connection)


async def execute_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> Any:
    """
    Execute raw SQL query with proper context management.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        Query result
    """
    if user_id is not None or AuthContext.get_user_id():
        async with get_user_connection(user_id) as connection:
            return await connection.execute(query, *args)
    else:
        async with get_service_role_connection() as connection:
            return await connection.execute(query, *args)


async def fetch_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> list:
    """
    Fetch results from raw SQL query with proper context management.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        List of query results
    """
    if user_id is not None or AuthContext.get_user_id():
        async with get_user_connection(user_id) as connection:
            return await connection.fetch(query, *args)
    else:
        async with get_service_role_connection() as connection:
            return await connection.fetch(query, *args)


async def fetchrow_raw_sql(query: str, *args, user_id: Optional[UUID] = None) -> Any:
    """
    Fetch single row from raw SQL query with proper context management.

    Args:
        query: SQL query string
        *args: Query parameters
        user_id: Optional user ID for user-scoped queries

    Returns:
        Single query result row
    """
    if user_id is not None or AuthContext.get_user_id():
        async with get_user_connection(user_id) as connection:
            return await connection.fetchrow(query, *args)
    else:
        async with get_service_role_connection() as connection:
            return await connection.fetchrow(query, *args)
