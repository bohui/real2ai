"""
Database connection utilities with JWT-based RLS enforcement
"""

import asyncio
import asyncpg
import json
import time
import weakref
import threading
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


class LoopPoolRegistry:
    """Per-loop pool registry for concurrent dual-loop operation"""
    
    def __init__(self):
        self.service_pool: Optional[asyncpg.Pool] = None
        self.user_pools: OrderedDict[UUID, UserPoolInfo] = OrderedDict()
        self.lock: Optional[asyncio.Lock] = None
        self.loop_ref: Optional[weakref.ref] = None
        self.created_at = time.time()
        self.last_accessed = time.time()
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = time.time()
    
    def is_loop_alive(self) -> bool:
        """Check if the event loop is still alive"""
        if self.loop_ref is None:
            return False
        loop = self.loop_ref()
        return loop is not None and not loop.is_closed()
    
    async def close_all_pools(self):
        """Close all pools in this registry"""
        pools_to_close = []
        
        if self.service_pool:
            pools_to_close.append(self.service_pool.close())
            self.service_pool = None
        
        for pool_info in self.user_pools.values():
            pools_to_close.append(pool_info.pool.close())
        self.user_pools.clear()
        
        if pools_to_close:
            await asyncio.gather(*pools_to_close, return_exceptions=True)


class ConnectionPoolManager:
    """Enhanced database connection pool manager with per-loop pool registry for concurrent operation"""

    # Per-loop pool registry for true concurrent dual-loop operation
    _pools_by_loop: Dict[int, LoopPoolRegistry] = {}
    _registry_lock = threading.Lock()  # Thread-safe registry access
    _last_cleanup = time.time()
    _cleanup_interval = 300  # 5 minutes
    _metrics: Dict[str, int] = {
        "active_loops": 0,
        "active_user_pools": 0,
        "evictions": 0,
        "pool_hits": 0,
        "pool_misses": 0,
        "registry_cleanups": 0,
    }

    @classmethod
    def _get_loop_registry(cls, current_loop: Optional[asyncio.AbstractEventLoop] = None) -> LoopPoolRegistry:
        """Get or create pool registry for the current event loop"""
        if current_loop is None:
            current_loop = asyncio.get_running_loop()
        
        current_loop_id = id(current_loop)
        
        with cls._registry_lock:
            # Check if registry exists for this loop
            if current_loop_id not in cls._pools_by_loop:
                # Create new registry for this loop
                registry = LoopPoolRegistry()
                registry.loop_ref = weakref.ref(current_loop)
                cls._pools_by_loop[current_loop_id] = registry
                cls._metrics["active_loops"] = len(cls._pools_by_loop)
                
                logger.debug(f"[POOL-REGISTRY] Created new pool registry for loop {current_loop_id}")
            else:
                registry = cls._pools_by_loop[current_loop_id]
                registry.touch()
                
            # Perform periodic cleanup of stale registries
            cls._cleanup_stale_registries()
            
        return registry
    
    @classmethod
    def _cleanup_stale_registries(cls):
        """Clean up registries for dead event loops (called with _registry_lock held)"""
        current_time = time.time()
        if current_time - cls._last_cleanup < cls._cleanup_interval:
            return
        
        stale_loop_ids = []
        for loop_id, registry in cls._pools_by_loop.items():
            if not registry.is_loop_alive() or (current_time - registry.last_accessed) > 1800:  # 30 min idle
                stale_loop_ids.append(loop_id)
        
        for loop_id in stale_loop_ids:
            registry = cls._pools_by_loop.pop(loop_id, None)
            if registry:
                # Schedule async cleanup in background (best effort)
                try:
                    # We can't await here since we're in a sync context
                    # The pools will be cleaned up by garbage collection
                    logger.debug(f"[POOL-REGISTRY] Marked stale registry for cleanup: loop {loop_id}")
                except Exception as e:
                    logger.debug(f"[POOL-REGISTRY] Error during stale registry cleanup: {e}")
        
        if stale_loop_ids:
            cls._metrics["registry_cleanups"] += 1
            cls._metrics["active_loops"] = len(cls._pools_by_loop)
            logger.debug(f"[POOL-REGISTRY] Cleaned up {len(stale_loop_ids)} stale registries")
        
        cls._last_cleanup = current_time

    @classmethod
    async def get_service_pool(cls) -> asyncpg.Pool:
        """Get service role connection pool for current event loop"""
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
        registry = cls._get_loop_registry(current_loop)
        
        # Ensure lock exists for this loop
        if registry.lock is None:
            registry.lock = asyncio.Lock()
        
        async with registry.lock:
            if registry.service_pool is None:
                settings = get_settings()
                dsn = cls._get_database_dsn()

                try:
                    # Optimized service pool for lightweight operations (progress, auth, etc.)
                    registry.service_pool = await asyncpg.create_pool(
                        dsn, 
                        min_size=2,           # Always ready for progress updates
                        max_size=8,           # Small pool for lightweight operations
                        command_timeout=30,   # Fast timeout for service operations
                        server_settings={
                            'application_name': f'service_pool_loop_{current_loop_id}',
                            'statement_timeout': '30s'
                        }
                    )
                    logger.info(f"[POOL-REGISTRY] Service pool created for loop {current_loop_id} (optimized for lightweight operations)")
                except Exception as e:
                    logger.error(f"[POOL-REGISTRY] Failed to create service pool for loop {current_loop_id}: {e}")
                    raise
            
            registry.touch()
            return registry.service_pool

    @classmethod
    async def get_user_pool(cls, user_id: UUID) -> asyncpg.Pool:
        """Get user-specific connection pool for current event loop based on configured mode"""
        settings = get_settings()

        if settings.db_pool_mode == "per_user":
            return await cls._get_per_user_pool(user_id)
        else:
            # Shared mode - use service pool with session GUCs
            return await cls.get_service_pool()

    @classmethod
    async def _get_per_user_pool(cls, user_id: UUID) -> asyncpg.Pool:
        """Get or create per-user connection pool for current event loop"""
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
        registry = cls._get_loop_registry(current_loop)
        
        # Ensure lock exists for this loop
        if registry.lock is None:
            registry.lock = asyncio.Lock()
            
        async with registry.lock:
            settings = get_settings()

            # Check if pool exists and touch it
            if user_id in registry.user_pools:
                pool_info = registry.user_pools[user_id]
                pool_info.touch()
                # Move to end for LRU
                registry.user_pools.move_to_end(user_id)
                cls._metrics["pool_hits"] += 1
                registry.touch()
                return pool_info.pool

            cls._metrics["pool_misses"] += 1

            # Enforce max pools limit
            if len(registry.user_pools) >= settings.db_max_active_user_pools:
                await cls._evict_least_recently_used_in_registry(registry)

            # Create new pool
            dsn = cls._get_database_dsn()

            try:
                # Optimized workflow pool for heavy LangGraph operations
                pool = await asyncpg.create_pool(
                    dsn,
                    min_size=max(3, settings.db_user_pool_min_size),  # Ready for parallel node execution
                    max_size=max(15, settings.db_user_pool_max_size), # Handle concurrent workflow operations
                    command_timeout=120,  # Longer timeout for LLM/analysis operations
                    server_settings={
                        'application_name': f'workflow_pool_loop_{current_loop_id}_user_{str(user_id)[:8]}',
                        'statement_timeout': '120s'
                    }
                )

                pool_info = UserPoolInfo(pool, user_id)
                registry.user_pools[user_id] = pool_info
                
                # Update metrics (sum across all loops)
                total_user_pools = sum(len(reg.user_pools) for reg in cls._pools_by_loop.values())
                cls._metrics["active_user_pools"] = total_user_pools

                logger.info(f"[POOL-REGISTRY] Created per-user pool for user {user_id} in loop {current_loop_id}")
                registry.touch()
                return pool

            except Exception as e:
                logger.error(f"[POOL-REGISTRY] Failed to create user pool for {user_id} in loop {current_loop_id}: {e}")
                # Fallback to service pool
                return await cls.get_service_pool()

    @classmethod
    async def _evict_least_recently_used_in_registry(cls, registry: LoopPoolRegistry):
        """Evict the least recently used pool in a specific registry"""
        if not registry.user_pools:
            return

        settings = get_settings()
        current_time = time.time()

        # First, try to evict idle pools
        to_evict = []
        for user_id, pool_info in registry.user_pools.items():
            if (
                current_time - pool_info.last_accessed
                > settings.db_user_pool_idle_ttl_seconds
            ):
                to_evict.append(user_id)

        if to_evict:
            for user_id in to_evict:
                await cls._close_user_pool_in_registry(registry, user_id)
        else:
            # No idle pools, evict LRU
            oldest_user_id = next(iter(registry.user_pools))
            await cls._close_user_pool_in_registry(registry, oldest_user_id)

    @classmethod
    async def _close_user_pool_in_registry(cls, registry: LoopPoolRegistry, user_id: UUID):
        """Close and remove a specific user pool from a registry"""
        if user_id in registry.user_pools:
            pool_info = registry.user_pools.pop(user_id)
            try:
                await pool_info.pool.close()
                cls._metrics["evictions"] += 1
                
                # Update metrics (sum across all loops)
                total_user_pools = sum(len(reg.user_pools) for reg in cls._pools_by_loop.values())
                cls._metrics["active_user_pools"] = total_user_pools
                
                logger.info(f"[POOL-REGISTRY] Evicted connection pool for user {user_id}")
            except Exception as e:
                logger.error(f"[POOL-REGISTRY] Error closing user pool for {user_id}: {e}")

    @classmethod
    def _get_database_dsn(cls) -> str:
        """Get database DSN from settings - require DATABASE_URL in production"""
        settings = get_settings()

        if settings.database_url:
            return settings.database_url

        # In production, DATABASE_URL is required (validated at startup)
        if settings.environment == "production":
            raise ValueError(
                "DATABASE_URL is required in production environment. "
                "Service key DSN fallback is not allowed."
            )

        # Non-production: Log warning and use fallback
        logger.error("DATABASE_URL not configured - using service key fallback")
        logger.warning(
            "Security risk: Consider using proper DATABASE_URL instead of service key"
        )

        # Fallback: Extract database URL from Supabase URL (legacy, non-production only)
        supabase_url = settings.supabase_url.replace("https://", "").replace(
            "http://", ""
        )
        project_id = supabase_url.split(".")[0]
        return f"postgresql://postgres:{settings.supabase_service_key}@db.{project_id}.supabase.co:5432/postgres"

    @classmethod
    async def cleanup_expired_pools(cls):
        """Clean up expired pools based on TTL for current event loop"""
        current_loop = asyncio.get_running_loop()
        registry = cls._get_loop_registry(current_loop)
        
        if registry.lock is None:
            registry.lock = asyncio.Lock()
            
        async with registry.lock:
            settings = get_settings()
            current_time = time.time()
            expired_users = []

            for user_id, pool_info in registry.user_pools.items():
                if (
                    current_time - pool_info.last_accessed
                    > settings.db_user_pool_idle_ttl_seconds
                ):
                    expired_users.append(user_id)

            for user_id in expired_users:
                await cls._close_user_pool_in_registry(registry, user_id)

    @classmethod
    async def close_all(cls):
        """Close all connection pools for current event loop"""
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
        
        with cls._registry_lock:
            if current_loop_id not in cls._pools_by_loop:
                logger.debug(f"[POOL-REGISTRY] No pools to close for loop {current_loop_id}")
                return
            
            registry = cls._pools_by_loop.pop(current_loop_id)
        
        # Close all pools in this registry
        await registry.close_all_pools()
        
        # Update global metrics
        with cls._registry_lock:
            cls._metrics["active_loops"] = len(cls._pools_by_loop)
            total_user_pools = sum(len(reg.user_pools) for reg in cls._pools_by_loop.values())
            cls._metrics["active_user_pools"] = total_user_pools
        
        logger.info(f"[POOL-REGISTRY] All connection pools closed for loop {current_loop_id}")
    
    @classmethod 
    async def close_all_loops(cls):
        """Close all connection pools for all event loops (used for shutdown)"""
        with cls._registry_lock:
            registries = list(cls._pools_by_loop.values())
            cls._pools_by_loop.clear()
        
        # Close all registries
        close_tasks = []
        for registry in registries:
            close_tasks.append(registry.close_all_pools())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Reset metrics
        cls._metrics = {
            "active_loops": 0,
            "active_user_pools": 0,
            "evictions": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "registry_cleanups": 0,
        }
        
        logger.info("[POOL-REGISTRY] All connection pools closed for all loops")

    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        """Get connection pool metrics across all loops"""
        with cls._registry_lock:
            # Update metrics with current counts
            cls._metrics["active_loops"] = len(cls._pools_by_loop)
            total_user_pools = sum(len(reg.user_pools) for reg in cls._pools_by_loop.values())
            cls._metrics["active_user_pools"] = total_user_pools
            
            # Add detailed per-loop metrics
            detailed_metrics = cls._metrics.copy()
            for loop_id, registry in cls._pools_by_loop.items():
                detailed_metrics[f"loop_{loop_id}_user_pools"] = len(registry.user_pools)
                detailed_metrics[f"loop_{loop_id}_has_service_pool"] = 1 if registry.service_pool else 0
                detailed_metrics[f"loop_{loop_id}_last_accessed"] = int(registry.last_accessed)
            
        return detailed_metrics


async def _setup_user_session(
    connection: asyncpg.Connection, 
    user_id: Optional[UUID] = None, 
    user_token: Optional[str] = None
):
    """
    Set up user session with JWT claims for RLS enforcement using transaction-local GUCs.

    Args:
        connection: Database connection
        user_id: User ID (uses auth context if not provided)
        user_token: JWT token (uses auth context if not provided)
    """
    # Use provided user_id/token or fall back to auth context as last resort
    if user_id is None:
        user_id_str = AuthContext.get_user_id()
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                logger.warning(f"Invalid user ID format in auth context: {user_id_str}")
                user_id = None

    if user_token is None:
        user_token = AuthContext.get_user_token()

    if user_token and user_id:
        try:
            # Parse JWT token to extract claims
            import jwt
            from app.core.config import get_settings

            settings = get_settings()

            # Debug diagnostics (no secrets)
            try:
                unverified_header = jwt.get_unverified_header(user_token)
            except Exception as header_error:
                unverified_header = {"_error": str(header_error)}
            try:
                unverified_claims = jwt.decode(
                    user_token, options={"verify_signature": False}
                )
            except Exception as claims_error:
                unverified_claims = {"_error": str(claims_error)}

            exp_ts = (
                unverified_claims.get("exp")
                if isinstance(unverified_claims, dict)
                else None
            )
            now_ts = int(time.time())
            ttl_seconds = (exp_ts - now_ts) if isinstance(exp_ts, int) else None

            # Compute a short fingerprint of the secret for diagnostics (non-reversible)
            try:
                import hashlib

                secret_fingerprint = (
                    hashlib.sha256(
                        (settings.supabase_jwt_secret or "").encode("utf-8")
                    ).hexdigest()[:8]
                    if settings.supabase_jwt_secret
                    else None
                )
            except Exception:
                secret_fingerprint = None

            logger.debug(
                "[DB][JWT] Token diagnostics before verification",
                extra={
                    "user_id": str(user_id),
                    "token_len": len(user_token),
                    "has_supabase_jwt_secret": bool(settings.supabase_jwt_secret),
                    "supabase_jwt_secret_len": (
                        len(settings.supabase_jwt_secret)
                        if settings.supabase_jwt_secret
                        else 0
                    ),
                    "supabase_jwt_secret_sha256_8": secret_fingerprint,
                    "header_alg": (
                        unverified_header.get("alg")
                        if isinstance(unverified_header, dict)
                        else None
                    ),
                    "header_kid": (
                        unverified_header.get("kid")
                        if isinstance(unverified_header, dict)
                        else None
                    ),
                    "claim_iss": (
                        unverified_claims.get("iss")
                        if isinstance(unverified_claims, dict)
                        else None
                    ),
                    "claim_aud": (
                        unverified_claims.get("aud")
                        if isinstance(unverified_claims, dict)
                        else None
                    ),
                    "claim_sub": (
                        unverified_claims.get("sub")
                        if isinstance(unverified_claims, dict)
                        else None
                    ),
                    "claim_role": (
                        unverified_claims.get("role")
                        if isinstance(unverified_claims, dict)
                        else None
                    ),
                    "token_ttl_seconds": ttl_seconds,
                },
            )

            # Verify token signature before setting RLS context
            if not settings.supabase_jwt_secret:
                logger.error("JWT secret not configured - cannot verify token for RLS")
                raise ValueError("JWT verification not configured")

            header_alg = (
                unverified_header.get("alg")
                if isinstance(unverified_header, dict)
                else None
            )
            if header_alg and header_alg.upper() != "HS256":
                logger.warning(
                    f"[DB][JWT] Token alg is {header_alg}; only HS256 is supported"
                )

            try:
                # Verify token with Supabase JWT secret (disable audience check)
                claims = jwt.decode(
                    user_token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                logger.debug(
                    "[DB][JWT] Token verified with HS256",
                    extra={
                        "user_id": str(user_id),
                        "claim_sub": claims.get("sub"),
                        "claim_role": claims.get("role"),
                    },
                )
            except jwt.InvalidTokenError as e:
                logger.error(
                    f"[DB][JWT] HS256 verification failed: {e}. user_id={user_id}, alg={header_alg}, token_len={len(user_token)}"
                )
                raise ValueError(f"Invalid token: {e}")

            # Set transaction-local GUCs for RLS (auto-reset on commit/rollback)
            logger.debug(
                "[DB] Setting user transaction-local GUCs",
                extra={
                    "user_id": str(user_id),
                    "has_claims": True,
                },
            )
            await connection.execute(
                "SELECT set_config('request.jwt.claims', $1, true)", json.dumps(claims)
            )
            await connection.execute(
                "SELECT set_config('role', $1, true)", "authenticated"
            )
            await connection.execute(
                "SELECT set_config('request.jwt.claim.sub', $1, true)", str(user_id)
            )

            logger.debug(f"Set user session context for user {user_id}")

        except Exception as e:
            logger.error(
                f"Failed to set user session context: {e}",
                extra={
                    "user_id": str(user_id) if user_id else None,
                    "event_loop_closed": True,
                },
            )
            # Set minimal auth context (transaction-local)
            await connection.execute(
                "SELECT set_config('role', $1, true)", "authenticated"
            )
            await connection.execute(
                "SELECT set_config('request.jwt.claim.sub', $1, true)", str(user_id)
            )
    else:
        # No user context - set anonymous role (transaction-local)
        await connection.execute("SELECT set_config('role', $1, true)", "anon")


async def _reset_session_gucs(connection: asyncpg.Connection):
    """
    Reset session GUCs to prevent claim bleed-over in shared pools.

    Args:
        connection: Database connection
    """
    try:
        logger.debug("[DB] Resetting session GUCs to anon")
        await connection.execute("SELECT set_config('request.jwt.claims', NULL, false)")
        await connection.execute("SELECT set_config('role', 'anon', false)")
        await connection.execute(
            "SELECT set_config('request.jwt.claim.sub', NULL, false)"
        )
    except Exception as e:
        logger.error(f"Failed to reset session GUCs: {e}")


async def _setup_service_session(connection: asyncpg.Connection):
    """
    Set up a service-role session using transaction-local GUCs so RLS policies that rely on auth.jwt() pass.

    Supabase RLS policies often check auth.jwt()->>'role' = 'service_role'. When
    connecting directly to Postgres (asyncpg), we must set the same GUCs that
    PostgREST would set. Using transaction-local GUCs prevents session bleed.
    """
    try:
        claims = {"role": "service_role"}
        await connection.execute(
            "SELECT set_config('request.jwt.claims', $1, true)", json.dumps(claims)
        )
        await connection.execute("SELECT set_config('role', $1, true)", "service_role")
        logger.debug("Set service-role transaction-local context for connection")
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
    
    # Track acquisition time to detect pool starvation
    import time
    start_time = time.time()
    
    try:
        # Acquire with timeout to prevent hanging
        connection = await asyncio.wait_for(pool.acquire(), timeout=10.0)
        
        acquisition_time = time.time() - start_time
        if acquisition_time > 2.0:
            logger.warning(f"[DB] Slow service pool acquisition: {acquisition_time:.2f}s")
        else:
            logger.debug(f"[DB] Acquired service-role connection in {acquisition_time:.3f}s")
            
    except asyncio.TimeoutError:
        logger.error("[DB] Service pool acquisition timeout - possible pool starvation")
        raise

    try:
        # Wrap in transaction with service-role RLS context
        async with connection.transaction():
            await _setup_service_session(connection)
            yield connection
    finally:
        try:
            # Reset connection state before releasing to pool
            await _reset_session_gucs(connection)
            await pool.release(connection)
            logger.debug("[DB] Released service-role connection back to pool with state reset")
        except (RuntimeError, Exception) as e:
            logger.error(f"Failed to release service role connection: {e}")
            # Force close connection if reset/release fails
            try:
                if hasattr(connection, "close") and not connection.is_closed():
                    await connection.close()
                    logger.warning("[DB] Force-closed service connection due to release failure")
            except Exception:
                pass  # Ignore final cleanup errors


@asynccontextmanager
async def get_user_connection(
    user_id: Optional[UUID] = None,
    user_token: Optional[str] = None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get a user-scoped database connection with JWT-based RLS enforcement using transaction-local GUCs.

    Args:
        user_id: User ID for connection context (uses auth context if not provided)
        user_token: JWT token (uses auth context if not provided)

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
    
    # Track acquisition time to detect pool starvation
    start_time = time.time()
    
    try:
        # Acquire with timeout to prevent hanging
        connection = await asyncio.wait_for(pool.acquire(), timeout=15.0)
        
        acquisition_time = time.time() - start_time
        if acquisition_time > 3.0:
            logger.warning(f"[DB] Slow user pool acquisition: {acquisition_time:.2f}s for user {user_id}")
        else:
            logger.debug(f"[DB] Acquired user connection in {acquisition_time:.3f}s for user {user_id}")
            
    except asyncio.TimeoutError:
        logger.error(f"[DB] User pool acquisition timeout for user {user_id} - possible pool starvation")
        raise

    try:
        # Wrap in transaction with user session context (transaction-local GUCs)
        async with connection.transaction():
            await _setup_user_session(connection, user_id, user_token)
            yield connection
    except Exception as e:
        logger.error(
            f"Error using user connection for user {user_id}: {e}",
            extra={"user_id": str(user_id), "error_type": type(e).__name__},
        )
        raise
    finally:
        try:
            # Check if we can still run async operations
            try:
                # Always reset connection state for safety (not just in shared mode)
                # This prevents session state bleed-over between operations
                await _reset_session_gucs(connection)
                logger.debug(f"[DB] Reset session state for user {user_id}")
            except (RuntimeError, Exception) as e:
                # Event loop might be closed or other async context issues
                logger.warning(f"Failed to reset session GUCs for user {user_id}: {e}")
        except Exception as e:
            logger.warning(f"Error in GUC cleanup for user {user_id}: {e}")

        try:
            # Attempt to release connection gracefully
            await pool.release(connection)
            logger.debug(
                "[DB] Released user connection with state reset",
                extra={"user_id": str(user_id), "pool_mode": settings.db_pool_mode},
            )
        except (RuntimeError, Exception) as e:
            # Event loop closed or connection already released
            logger.error(f"Failed to release connection for user {user_id}: {e}")
            # In extreme cases, force close the connection if possible
            try:
                if hasattr(connection, "close") and not connection.is_closed():
                    connection.close()
            except Exception:
                pass  # Ignore final cleanup errors


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
    # Basic retry on transient connection issues
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if user_id is not None or AuthContext.get_user_id():
                async with get_user_connection(user_id) as connection:
                    return await connection.execute(query, *args)
            else:
                async with get_service_role_connection() as connection:
                    return await connection.execute(query, *args)
        except asyncpg.exceptions.ConnectionDoesNotExistError:
            logger.error(
                "Connection closed during execute; retrying (%s/%s)",
                attempt + 1,
                max_attempts,
            )
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


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
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if user_id is not None or AuthContext.get_user_id():
                async with get_user_connection(user_id) as connection:
                    return await connection.fetch(query, *args)
            else:
                async with get_service_role_connection() as connection:
                    return await connection.fetch(query, *args)
        except asyncpg.exceptions.ConnectionDoesNotExistError:
            logger.error(
                "Connection closed during fetch; retrying (%s/%s)",
                attempt + 1,
                max_attempts,
            )
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


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
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if user_id is not None or AuthContext.get_user_id():
                async with get_user_connection(user_id) as connection:
                    return await connection.fetchrow(query, *args)
            else:
                async with get_service_role_connection() as connection:
                    return await connection.fetchrow(query, *args)
        except asyncpg.exceptions.ConnectionDoesNotExistError:
            logger.error(
                "Connection closed during fetchrow; retrying (%s/%s)",
                attempt + 1,
                max_attempts,
            )
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


# Alias for new safe repository pattern
@asynccontextmanager
async def get_service_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get a service connection for lightweight read operations.
    
    This is an alias for get_service_role_connection() that follows the new
    safe repository pattern where operations explicitly pass user_id in queries
    rather than relying on session state. Uses transaction-local GUCs for safety.
    
    Features:
    - Uses service pool optimized for lightweight operations
    - Transaction-local GUCs prevent session state bleed
    - Automatic connection reset on release (belt-and-suspenders)
    - Works in any event loop context (single or dual pool architecture)
    """
    async with get_service_role_connection() as conn:
        yield conn
