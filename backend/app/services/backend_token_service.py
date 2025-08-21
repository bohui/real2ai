"""
Backend token service

Redis-backed implementation for issuing and exchanging backend API tokens
for Supabase user tokens. Avoids exposing Supabase access tokens to the client.
"""

from __future__ import annotations

import logging
import time
import json
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

import jwt
import redis.asyncio as redis

from app.core.config import get_settings
from app.clients.factory import get_service_supabase_client
import base64


logger = logging.getLogger(__name__)


class BackendTokenService:
    """
    Issues backend JWTs and maps them to Supabase user sessions (access/refresh tokens).
    Uses Redis for persistent token storage across backend restarts.
    """

    _redis_client: Optional[redis.Redis] = None
    _redis_prefix = "backend_token:"

    @classmethod
    async def _get_redis_client(cls) -> redis.Redis:
        """Get or create Redis client."""
        if cls._redis_client is None:
            settings = get_settings()
            cls._redis_client = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            # Test connection
            try:
                await cls._redis_client.ping()
                logger.debug("Redis connection established for token service")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._redis_client

    @classmethod
    async def _store_token_data(
        cls, backend_token: str, token_data: Dict[str, Any]
    ) -> bool:
        """Store token data in Redis with appropriate TTL."""
        try:
            client = await cls._get_redis_client()
            key = f"{cls._redis_prefix}{backend_token}"

            # Store as JSON string
            json_data = json.dumps(token_data)

            # Set TTL based on backend token expiry
            ttl_seconds = token_data.get("backend_exp", 0) - int(time.time())
            if ttl_seconds > 0:
                await client.setex(key, ttl_seconds, json_data)
                logger.debug(f"Stored token data in Redis with TTL {ttl_seconds}s")
                return True
            else:
                logger.warning("Token already expired, not storing in Redis")
                return False

        except Exception as e:
            logger.error(f"Failed to store token data in Redis: {e}")
            return False

    @classmethod
    async def _get_token_data(cls, backend_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve token data from Redis."""
        try:
            client = await cls._get_redis_client()
            key = f"{cls._redis_prefix}{backend_token}"

            json_data = await client.get(key)
            if json_data:
                token_data = json.loads(json_data)
                logger.debug(
                    f"Retrieved token data from Redis for token: {backend_token[:10]}..."
                )
                return token_data
            else:
                logger.debug(
                    f"No token data found in Redis for token: {backend_token[:10]}..."
                )
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve token data from Redis: {e}")
            return None

    @classmethod
    async def _delete_token_data(cls, backend_token: str) -> bool:
        """Delete token data from Redis."""
        try:
            client = await cls._get_redis_client()
            key = f"{cls._redis_prefix}{backend_token}"

            result = await client.delete(key)
            if result:
                logger.debug(
                    f"Deleted token data from Redis for token: {backend_token[:10]}..."
                )
                return True
            else:
                logger.debug(
                    f"No token data found to delete in Redis for token: {backend_token[:10]}..."
                )
                return False

        except Exception as e:
            logger.error(f"Failed to delete token data from Redis: {e}")
            return False

    @staticmethod
    def _get_secret_and_alg() -> Tuple[str, str]:
        settings = get_settings()
        secret = settings.jwt_secret_key or settings.supabase_anon_key
        alg = settings.jwt_algorithm or "HS256"
        return secret, alg

    @classmethod
    def _extract_supabase_expiry(cls, supabase_access_token: str) -> Optional[int]:
        """Extract expiry timestamp from Supabase access token."""
        try:
            # JWT has 3 parts: header.payload.signature
            parts = supabase_access_token.split(".")
            if len(parts) != 3:
                return None

            # Decode payload (add padding if needed)
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))

            return payload.get("exp")
        except Exception as e:
            logger.debug(f"Failed to extract Supabase token expiry: {e}")
            return None

    @classmethod
    async def issue_backend_token(
        cls,
        user_id: str,
        email: str,
        supabase_access_token: str,
        supabase_refresh_token: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        coordinate_expiry: bool = True,
    ) -> str:
        """Create backend API token coordinated with Supabase token expiry.

        Args:
            user_id: User ID
            email: User email
            supabase_access_token: Supabase access token
            supabase_refresh_token: Optional Supabase refresh token
            ttl_seconds: Optional TTL in seconds (if None, uses coordinated expiry)
            coordinate_expiry: If True, coordinates expiry with Supabase token
        """
        settings = get_settings()
        secret, alg = cls._get_secret_and_alg()
        now = int(time.time())

        # Extract Supabase token expiry for coordination
        supa_exp = cls._extract_supabase_expiry(supabase_access_token)

        # Determine backend token expiry
        if ttl_seconds is not None:
            # Use explicit TTL if provided
            backend_exp = now + ttl_seconds
        elif coordinate_expiry and supa_exp:
            # Backend token expires before Supabase token (with buffer)
            buffer_seconds = settings.backend_token_ttl_buffer_minutes * 60
            backend_exp = supa_exp - buffer_seconds
            # Ensure minimum token lifetime of 5 minutes
            min_exp = now + 300
            if backend_exp < min_exp:
                backend_exp = min_exp
                logger.warning(
                    f"Supabase token expires too soon ({supa_exp - now}s), "
                    f"using minimum TTL of 5 minutes for backend token"
                )
        else:
            # Fall back to configured default
            backend_exp = now + (settings.jwt_expiration_hours * 3600)

        payload = {
            "sub": user_id,
            "email": email,
            "type": "api",
            "iat": now,
            "exp": backend_exp,
            "supa_exp": supa_exp,  # Track Supabase expiry for monitoring
        }
        backend_token = jwt.encode(payload, secret, algorithm=alg)

        # Store token mapping in Redis
        token_data = {
            "user_id": user_id,
            "email": email,
            "supabase_access_token": supabase_access_token,
            "supabase_refresh_token": supabase_refresh_token,
            "supabase_exp": supa_exp,
            "backend_exp": backend_exp,
            "issued_at": now,
        }

        try:
            await cls._store_token_data(backend_token, token_data)
        except Exception as e:
            logger.error(f"Failed to store token mapping in Redis: {e}")
            # Continue with token issuance even if storage fails

        # Log token coordination details
        if supa_exp:
            logger.info(
                f"Issued coordinated backend token for user_id={user_id}: "
                f"backend expires in {backend_exp - now}s, "
                f"Supabase expires in {supa_exp - now}s, "
                f"buffer: {supa_exp - backend_exp}s"
            )
        else:
            logger.info(
                f"Issued backend token for user_id={user_id}: "
                f"expires in {backend_exp - now}s (no Supabase expiry coordination)"
            )

        return backend_token

    @classmethod
    def verify_backend_token(cls, token: str) -> Dict[str, Any]:
        """Verify backend JWT signature and expiry and return claims."""
        secret, alg = cls._get_secret_and_alg()
        return jwt.decode(token, secret, algorithms=[alg])

    @classmethod
    def is_backend_token(cls, token: str) -> bool:
        try:
            claims = cls.verify_backend_token(token)
            return claims.get("type") == "api"
        except Exception:
            return False

    @classmethod
    def get_identity(cls, backend_token: str) -> Optional[Tuple[str, str]]:
        try:
            claims = cls.verify_backend_token(backend_token)
            return claims.get("sub"), claims.get("email")
        except Exception:
            return None

    @classmethod
    async def ensure_supabase_access_token(cls, backend_token: str) -> Optional[str]:
        """
        Return a valid Supabase access token for the backend token.
        Refresh via Supabase refresh token if the access token is expired and a refresh exists.
        """
        logger.info("Looking up backend token in Redis store")
        entry = await cls._get_token_data(backend_token)
        if not entry:
            logger.warning(f"Backend token not found in Redis store")
            return None

        access = entry.get("supabase_access_token")
        supa_exp = entry.get("supabase_exp")
        refresh = entry.get("supabase_refresh_token")

        now = int(time.time())
        if supa_exp and supa_exp - 30 > now:
            # Access still valid
            return access

        if not refresh:
            logger.warning("No refresh token available to renew Supabase session")
            return access

        try:
            client = await get_service_supabase_client()
            result = client.auth.refresh_session(refresh)
            if result.session and result.user:
                new_access = result.session.access_token
                new_refresh = result.session.refresh_token
                # Update store
                new_exp = None
                try:
                    supa_claims = jwt.decode(
                        new_access, options={"verify_signature": False}
                    )
                    new_exp = (
                        int(supa_claims.get("exp")) if supa_claims.get("exp") else None
                    )
                except Exception:
                    pass

                # Update token data in Redis
                updated_entry = entry.copy()
                updated_entry["supabase_access_token"] = new_access
                updated_entry["supabase_refresh_token"] = new_refresh
                updated_entry["supabase_exp"] = new_exp

                try:
                    await cls._store_token_data(backend_token, updated_entry)
                    logger.info(
                        "Refreshed Supabase access token via backend token exchange"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to update token data in Redis after refresh: {e}"
                    )

                return new_access

        except Exception as e:
            logger.error(f"Failed to refresh Supabase session: {e}")

        return entry.get("supabase_access_token")

    @classmethod
    def is_near_expiry(cls, token: str, threshold_minutes: int = 10) -> bool:
        """Check if a backend token is near expiry."""
        try:
            claims = cls.verify_backend_token(token)
            exp = claims.get("exp")
            if not exp:
                return False

            now = int(time.time())
            time_to_expiry = exp - now
            threshold_seconds = threshold_minutes * 60

            return time_to_expiry <= threshold_seconds
        except Exception:
            return False

    @classmethod
    async def refresh_coordinated_tokens(cls, backend_token: str) -> Optional[str]:
        """Refresh both Supabase and backend tokens in coordination."""
        entry = await cls._get_token_data(backend_token)
        if not entry:
            logger.warning("Backend token not found for coordinated refresh")
            return None

        refresh_token = entry.get("supabase_refresh_token")
        if not refresh_token:
            logger.warning("No refresh token available for coordinated refresh")
            return None

        try:
            # Refresh Supabase token first
            client = await get_service_supabase_client()
            result = client.auth.refresh_session(refresh_token)

            if result.session and result.user:
                # Issue new coordinated backend token
                new_backend_token = await cls.issue_backend_token(
                    user_id=result.user.id,
                    email=result.user.email,
                    supabase_access_token=result.session.access_token,
                    supabase_refresh_token=result.session.refresh_token,
                    coordinate_expiry=True,
                )

                # Clean up old token from Redis
                await cls._delete_token_data(backend_token)

                logger.info("Successfully refreshed coordinated tokens")
                return new_backend_token

        except Exception as e:
            logger.error(f"Failed to refresh coordinated tokens: {e}")

        return None

    @classmethod
    async def reissue_backend_token(
        cls, backend_token: str, ttl_seconds: Optional[int] = None
    ) -> Optional[str]:
        """Reissue a fresh backend token using the stored mapping for the given backend token."""
        entry = await cls._get_token_data(backend_token)
        if not entry:
            return None
        user_id = entry.get("user_id")
        email = entry.get("email")
        access = entry.get("supabase_access_token")
        refresh = entry.get("supabase_refresh_token")
        if not user_id or not email or not access:
            return None
        return await cls.issue_backend_token(
            user_id=user_id,
            email=email,
            supabase_access_token=access,
            supabase_refresh_token=refresh,
            ttl_seconds=ttl_seconds,
            coordinate_expiry=True,
        )

    @classmethod
    async def get_mapping(cls, backend_token: str) -> Optional[Dict[str, Any]]:
        """Return stored mapping for diagnostics or downstream use."""
        return await cls._get_token_data(backend_token)

    @classmethod
    async def get_store_stats(cls) -> dict:
        """Get statistics about the token store."""
        try:
            client = await cls._get_redis_client()

            # Get all keys with our prefix
            pattern = f"{cls._redis_prefix}*"
            keys = await client.keys(pattern)

            total_count = len(keys)

            # Count expired tokens (those with TTL <= 0)
            expired_count = 0
            for key in keys:
                ttl = await client.ttl(key)
                if ttl <= 0:
                    expired_count += 1

            stats = {
                "total_tokens": total_count,
                "expired_tokens": expired_count,
                "active_tokens": total_count - expired_count,
                "storage_type": "redis",
            }

            logger.debug(f"Token store stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting store stats: {e}")
            return {
                "total_tokens": 0,
                "expired_tokens": 0,
                "active_tokens": 0,
                "storage_type": "redis",
                "error": str(e),
            }

    @classmethod
    async def cleanup_expired_tokens(cls) -> int:
        """Clean up expired tokens from the store."""
        try:
            client = await cls._get_redis_client()

            # Get all keys with our prefix
            pattern = f"{cls._redis_prefix}*"
            keys = await client.keys(pattern)

            deleted_count = 0
            for key in keys:
                ttl = await client.ttl(key)
                if ttl <= 0:
                    await client.delete(key)
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired tokens from Redis")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
            return 0
