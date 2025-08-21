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
from app.services.backend_token_service import BackendTokenService
from app.clients.factory import get_service_supabase_client

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
    # Pools must be used only with the event loop they were created with.
    # We bind pools to a specific loop id and recreate them if the loop changes.
    _loop_id: Optional[int] = None
    _pool_lock: Optional[asyncio.Lock] = None
    _metrics: Dict[str, int] = {
        "active_user_pools": 0,
        "evictions": 0,
        "pool_hits": 0,
        "pool_misses": 0,
    }

    @classmethod
    def _ensure_loop_bound(cls) -> None:
        """Ensure pools are bound to the current event loop. Reset when loop changes."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback to get_event_loop for older contexts
            current_loop = asyncio.get_event_loop()

        current_loop_id = id(current_loop)
        if cls._loop_id is None:
            cls._loop_id = current_loop_id
            if cls._pool_lock is None:
                cls._pool_lock = asyncio.Lock()
            return

        if cls._loop_id != current_loop_id:
            # Event loop changed; make existing pools unavailable immediately to avoid races
            # Capture references for background close, then null out class refs synchronously
            old_service_pool = cls._service_pool
            old_user_pools = list(cls._user_pools.values())
            cls._service_pool = None
            cls._user_pools.clear()
            cls._metrics = {
                "active_user_pools": 0,
                "evictions": 0,
                "pool_hits": 0,
                "pool_misses": 0,
            }

            async def _close_captured():
                try:
                    close_ops = []
                    if old_service_pool is not None:
                        close_ops.append(old_service_pool.close())
                    for pool_info in old_user_pools:
                        try:
                            close_ops.append(pool_info.pool.close())
                        except Exception:
                            # Ignore close scheduling errors for individual pools
                            pass
                    if close_ops:
                        await asyncio.gather(*close_ops, return_exceptions=True)
                finally:
                    logger.info(
                        "Closed pools from previous event loop after loop change"
                    )

            try:
                if current_loop.is_running():
                    current_loop.create_task(_close_captured())
                else:
                    current_loop.run_until_complete(_close_captured())
            except Exception:
                # Best-effort cleanup; leaked resources will be cleaned by driver/GC
                pass

            # Rebind to new loop and create a fresh lock
            cls._loop_id = current_loop_id
            cls._pool_lock = asyncio.Lock()

    @classmethod
    async def get_service_pool(cls) -> asyncpg.Pool:
        """Get service role connection pool"""
        cls._ensure_loop_bound()
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
        cls._ensure_loop_bound()
        settings = get_settings()

        if settings.db_pool_mode == "per_user":
            return await cls._get_per_user_pool(user_id)
        else:
            # Shared mode - use service pool with session GUCs
            return await cls.get_service_pool()

    @classmethod
    async def _get_per_user_pool(cls, user_id: UUID) -> asyncpg.Pool:
        """Get or create per-user connection pool"""
        cls._ensure_loop_bound()
        # mypy: _pool_lock is ensured in _ensure_loop_bound
        async with cls._pool_lock:  # type: ignore[arg-type]
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
        """Clean up expired pools based on TTL"""
        cls._ensure_loop_bound()
        async with cls._pool_lock:  # type: ignore[arg-type]
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
        # Guard against None lock in startup/cleanup races
        if cls._pool_lock is None:
            cls._pool_lock = asyncio.Lock()
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
            # Reset loop binding to allow rebind on next use
            cls._loop_id = None
            logger.info("All connection pools closed")

    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        """Get connection pool metrics"""
        cls._metrics["active_user_pools"] = len(cls._user_pools)
        return cls._metrics.copy()


async def _setup_user_session(
    connection: asyncpg.Connection, user_id: Optional[str]
) -> None:
    """
    Set up user session context for RLS enforcement.

    Args:
        connection: Database connection
        user_id: Optional user ID (if None, sets anonymous role)
    """
    # Import JWT at the top level to avoid scope issues
    try:
        import jwt
    except ImportError:
        logger.error("JWT library not available - cannot verify tokens")
        raise ValueError("JWT verification not available")

    # Get settings for JWT verification
    settings = get_settings()

    if user_id:
        try:
            # Get user token from auth context
            user_token = AuthContext.get_user_token()
            if not user_token:
                logger.warning(
                    f"No user token available for user {user_id} - setting anonymous role"
                )
                await connection.execute("SELECT set_config('role', $1, false)", "anon")
                return

            # Enhanced token analysis and logging
            logger.info(
                f"Setting up user session for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "token_length": len(user_token),
                    "token_type": (
                        "backend"
                        if BackendTokenService.is_backend_token(user_token)
                        else "supabase"
                    ),
                    "connection_id": id(connection),
                    "event_loop_closed": getattr(
                        asyncio.get_event_loop(), "is_closed", lambda: None
                    )(),
                },
            )

            # Analyze token before attempting to use it
            try:
                if BackendTokenService.is_backend_token(user_token):
                    # Analyze backend token
                    claims = BackendTokenService.verify_backend_token(user_token)
                    backend_exp = claims.get("exp")
                    supa_exp = claims.get("supa_exp")
                    now = int(time.time())

                    if backend_exp:
                        time_to_backend_expiry = backend_exp - now
                        logger.info(
                            f"Backend token analysis for user {user_id}",
                            extra={
                                "user_id": str(user_id),
                                "backend_exp": backend_exp,
                                "time_to_backend_expiry_seconds": time_to_backend_expiry,
                                "time_to_backend_expiry_minutes": (
                                    time_to_backend_expiry / 60
                                    if time_to_backend_expiry > 0
                                    else 0
                                ),
                                "is_expired": time_to_backend_expiry <= 0,
                                "connection_id": id(connection),
                            },
                        )

                        if time_to_backend_expiry <= 0:
                            logger.error(
                                f"Backend token is expired for user {user_id}",
                                extra={
                                    "user_id": str(user_id),
                                    "backend_exp": backend_exp,
                                    "current_time": now,
                                    "connection_id": id(connection),
                                    "recommendation": "Token should have been refreshed before database access",
                                },
                            )
                            raise ValueError("Backend token is expired")

                        if supa_exp:
                            time_to_supabase_expiry = supa_exp - now
                            buffer_time = supa_exp - backend_exp
                            logger.info(
                                f"Token coordination status for user {user_id}",
                                extra={
                                    "user_id": str(user_id),
                                    "supabase_exp": supa_exp,
                                    "time_to_supabase_expiry_seconds": time_to_supabase_expiry,
                                    "time_to_supabase_expiry_minutes": (
                                        time_to_supabase_expiry / 60
                                        if time_to_supabase_expiry > 0
                                        else 0
                                    ),
                                    "buffer_time_seconds": buffer_time,
                                    "buffer_time_minutes": (
                                        buffer_time / 60 if buffer_time > 0 else 0
                                    ),
                                    "connection_id": id(connection),
                                },
                            )

                            # Check if we need to refresh the token
                            if time_to_backend_expiry <= 300:  # 5 minutes or less
                                logger.warning(
                                    f"Backend token expires soon for user {user_id} - attempting refresh",
                                    extra={
                                        "user_id": str(user_id),
                                        "time_to_backend_expiry_seconds": time_to_backend_expiry,
                                        "connection_id": id(connection),
                                    },
                                )

                                try:
                                    # Attempt to refresh the token
                                    refreshed_token = await BackendTokenService.refresh_coordinated_tokens(
                                        user_token
                                    )
                                    if refreshed_token:
                                        user_token = refreshed_token
                                        logger.info(
                                            f"Successfully refreshed backend token for user {user_id}",
                                            extra={
                                                "user_id": str(user_id),
                                                "old_token_length": len(user_token),
                                                "new_token_length": len(
                                                    refreshed_token
                                                ),
                                                "connection_id": id(connection),
                                            },
                                        )

                                        # Update auth context with new token
                                        AuthContext.set_auth_context(
                                            token=refreshed_token,
                                            user_id=user_id,
                                            user_email=AuthContext.get_user_email(),
                                            metadata=AuthContext.get_auth_metadata(),
                                            refresh_token=AuthContext.get_refresh_token(),
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed to refresh backend token for user {user_id}",
                                            extra={
                                                "user_id": str(user_id),
                                                "connection_id": id(connection),
                                            },
                                        )
                                except Exception as refresh_error:
                                    logger.error(
                                        f"Error during token refresh for user {user_id}",
                                        extra={
                                            "user_id": str(user_id),
                                            "error": str(refresh_error),
                                            "connection_id": id(connection),
                                        },
                                        exc_info=True,
                                    )
                                    # Continue with original token - let the verification process handle it
                else:
                    # Analyze Supabase token
                    try:
                        import jwt

                        claims = jwt.decode(
                            user_token, options={"verify_signature": False}
                        )
                        exp = claims.get("exp")
                        if exp:
                            now = int(time.time())
                            time_to_expiry = exp - now
                            logger.info(
                                f"Supabase token analysis for user {user_id}",
                                extra={
                                    "user_id": str(user_id),
                                    "exp": exp,
                                    "time_to_expiry_seconds": time_to_expiry,
                                    "time_to_expiry_minutes": (
                                        time_to_expiry / 60 if time_to_expiry > 0 else 0
                                    ),
                                    "is_expired": time_to_expiry <= 0,
                                    "connection_id": id(connection),
                                },
                            )

                            if time_to_expiry <= 0:
                                logger.error(
                                    f"Supabase token is expired for user {user_id}",
                                    extra={
                                        "user_id": str(user_id),
                                        "exp": exp,
                                        "current_time": now,
                                        "connection_id": id(connection),
                                        "recommendation": "Attempting to refresh using stored refresh token before database access",
                                    },
                                )
                                # Attempt to refresh using stored refresh token
                                try:
                                    refresh_token = AuthContext.get_refresh_token()
                                    if refresh_token:
                                        client = await get_service_supabase_client()
                                        refresh_result = client.auth.refresh_session(
                                            refresh_token
                                        )
                                        if (
                                            refresh_result.session
                                            and refresh_result.user
                                        ):
                                            new_access = (
                                                refresh_result.session.access_token
                                            )
                                            new_refresh = (
                                                refresh_result.session.refresh_token
                                            )
                                            # Update auth context and continue with refreshed token
                                            AuthContext.set_auth_context(
                                                token=new_access,
                                                user_id=str(user_id),
                                                user_email=AuthContext.get_user_email(),
                                                metadata=AuthContext.get_auth_metadata(),
                                                refresh_token=new_refresh,
                                            )
                                            user_token = new_access
                                            logger.info(
                                                "Successfully refreshed Supabase access token for expired session; continuing",
                                                extra={
                                                    "user_id": str(user_id),
                                                    "connection_id": id(connection),
                                                },
                                            )
                                        else:
                                            logger.warning(
                                                "Supabase refresh returned no session or user; cannot recover expired token",
                                                extra={
                                                    "user_id": str(user_id),
                                                    "connection_id": id(connection),
                                                },
                                            )
                                            raise ValueError(
                                                "Supabase token is expired"
                                            )
                                    else:
                                        logger.warning(
                                            "No refresh token available in auth context; cannot recover expired Supabase token",
                                            extra={
                                                "user_id": str(user_id),
                                                "connection_id": id(connection),
                                            },
                                        )
                                        raise ValueError("Supabase token is expired")
                                except Exception as refresh_error:
                                    logger.error(
                                        f"Error while attempting Supabase token refresh: {refresh_error}",
                                        extra={
                                            "user_id": str(user_id),
                                            "connection_id": id(connection),
                                        },
                                        exc_info=True,
                                    )
                                    # Bubble up as invalid token so caller can handle/retry
                                    raise ValueError("Supabase token is expired")

                            if time_to_expiry <= 600:  # 10 minutes or less
                                logger.warning(
                                    f"Supabase token expires soon for user {user_id}",
                                    extra={
                                        "user_id": str(user_id),
                                        "time_to_expiry_seconds": time_to_expiry,
                                        "time_to_expiry_minutes": (
                                            time_to_expiry / 60
                                            if time_to_expiry > 0
                                            else 0
                                        ),
                                        "connection_id": id(connection),
                                        "recommendation": "Consider using backend tokens for better coordination",
                                    },
                                )
                    except Exception as token_analysis_error:
                        logger.warning(
                            f"Could not analyze Supabase token expiry for user {user_id}",
                            extra={
                                "user_id": str(user_id),
                                "error": str(token_analysis_error),
                                "connection_id": id(connection),
                            },
                        )
                        # Continue with original token - let the verification process handle it

            except Exception as token_analysis_error:
                logger.error(
                    f"Error analyzing token for user {user_id}",
                    extra={
                        "user_id": str(user_id),
                        "error": str(token_analysis_error),
                        "connection_id": id(connection),
                    },
                    exc_info=True,
                )
                # Continue with original token - let the verification process handle it

            # Extract JWT header for algorithm check
            try:
                header = jwt.get_unverified_header(user_token)
                header_alg = header.get("alg") if header else None
            except Exception as header_error:
                logger.warning(
                    f"Could not extract JWT header for user {user_id}: {header_error}"
                )
                header_alg = None

            if header_alg and header_alg.upper() != "HS256":
                logger.warning(
                    f"[DB][JWT] Token alg is {header_alg}; only HS256 is supported"
                )

            try:
                # Verify token with Supabase JWT secret (disable audience check)
                logger.debug(
                    f"Verifying JWT token for user {user_id}",
                    extra={
                        "user_id": str(user_id),
                        "token_length": len(user_token),
                        "header_alg": header_alg,
                        "connection_id": id(connection),
                    },
                )

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
                        "connection_id": id(connection),
                    },
                )
            except jwt.InvalidTokenError as e:
                logger.error(
                    f"[DB][JWT] HS256 verification failed: {e}. user_id={user_id}, alg={header_alg}, token_len={len(user_token)}"
                )
                raise ValueError(f"Invalid token: {e}")

            # Set session GUCs for RLS
            logger.debug(
                "[DB] Setting user session GUCs",
                extra={
                    "user_id": str(user_id),
                    "has_claims": True,
                    "loop_is_closed": getattr(
                        asyncio.get_event_loop(), "is_closed", lambda: None
                    )(),
                    "connection_id": id(connection),
                },
            )
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
            logger.error(
                f"Failed to set user session context: {e}",
                extra={
                    "user_id": str(user_id) if user_id else None,
                    "event_loop_closed": True,
                    "connection_id": id(connection),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            # Auth/token failures: do not impersonate; bubble up
            try:
                import jwt as _jwt  # type: ignore

                if isinstance(e, _jwt.InvalidTokenError) or "Invalid token" in str(e):
                    raise
            except Exception:
                # If jwt import/type check fails, continue to other checks
                pass

            # Connection-level issues: bubble up for retry with a fresh connection
            if isinstance(
                e,
                (
                    asyncpg.InterfaceError,
                    asyncpg.exceptions.ConnectionDoesNotExistError,
                ),
            ):
                raise

            # Safe fallback: attempt anon role; ignore any failures, then re-raise
            try:
                await connection.execute("SELECT set_config('role', $1, false)", "anon")
            except Exception:
                pass
            # Re-raise to let caller handle/retry
            raise
    else:
        # No user context - set anonymous role
        try:
            await connection.execute("SELECT set_config('role', $1, false)", "anon")
        except Exception:
            pass


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
    logger.debug("[DB] Acquired service-role connection from pool")

    try:
        # Ensure service-role RLS context is present for this connection
        await _setup_service_session(connection)
        yield connection
    finally:
        try:
            await pool.release(connection)
            logger.debug("[DB] Released service-role connection back to pool")
        except (RuntimeError, Exception) as e:
            logger.error(f"Failed to release service role connection: {e}")
            # Force close if event loop is dead
            try:
                if hasattr(connection, "close") and not connection.is_closed():
                    connection.close()
            except Exception:
                pass  # Ignore final cleanup errors


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
    logger.debug(
        "[DB] Acquired user connection",
        extra={"user_id": str(user_id), "pool_mode": settings.db_pool_mode},
    )

    try:
        # Set up user session context
        await _setup_user_session(connection, user_id)
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
                # Reset GUCs in shared mode to prevent bleed-over
                if settings.db_pool_mode == "shared":
                    await _reset_session_gucs(connection)
            except (RuntimeError, Exception) as e:
                # Event loop might be closed or other async context issues
                logger.warning(f"Failed to reset session GUCs for user {user_id}: {e}")
        except Exception as e:
            logger.warning(f"Error in GUC cleanup for user {user_id}: {e}")

        try:
            # Attempt to release connection gracefully
            await pool.release(connection)
            logger.debug(
                "[DB] Released user connection",
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
