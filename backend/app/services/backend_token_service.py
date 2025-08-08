"""
Backend token service

Dev-friendly in-memory implementation for issuing and exchanging backend API tokens
for Supabase user tokens. Avoids exposing Supabase access tokens to the client.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple, Any

import jwt

from app.core.config import get_settings
from app.clients.factory import get_service_supabase_client


logger = logging.getLogger(__name__)


class BackendTokenService:
    """
    Issues backend JWTs and maps them to Supabase user sessions (access/refresh tokens).
    In dev, an in-memory map is sufficient. For prod, replace with Redis or DB store.
    """

    _token_store: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _get_secret_and_alg() -> Tuple[str, str]:
        settings = get_settings()
        secret = settings.jwt_secret_key or settings.supabase_anon_key
        alg = settings.jwt_algorithm or "HS256"
        return secret, alg

    @classmethod
    def issue_backend_token(
        cls,
        user_id: str,
        email: str,
        supabase_access_token: str,
        supabase_refresh_token: Optional[str] = None,
        ttl_seconds: int = 60 * 60 * 24,
    ) -> str:
        """Create backend API token and store mapping to Supabase tokens."""
        secret, alg = cls._get_secret_and_alg()
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "type": "api",
            "iat": now,
            "exp": now + ttl_seconds,
        }
        backend_token = jwt.encode(payload, secret, algorithm=alg)

        # Decode supabase access to capture its exp if available (best-effort)
        supa_exp: Optional[int] = None
        try:
            supa_claims = jwt.decode(
                supabase_access_token,
                options={"verify_signature": False, "verify_exp": False},
            )
            supa_exp = int(supa_claims.get("exp")) if supa_claims.get("exp") else None
        except Exception:
            pass

        cls._token_store[backend_token] = {
            "user_id": user_id,
            "email": email,
            "supabase_access_token": supabase_access_token,
            "supabase_refresh_token": supabase_refresh_token,
            "supabase_exp": supa_exp,
        }

        logger.info(f"Issued backend token for user_id={user_id}")
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
        logger.info(f"Looking up backend token in store (total entries: {len(cls._token_store)})")
        entry = cls._token_store.get(backend_token)
        if not entry:
            logger.warning(f"Backend token not found in store. Available tokens: {len(cls._token_store)}")
            # Debug: Show first few characters of available tokens
            for i, stored_token in enumerate(list(cls._token_store.keys())[:3]):
                logger.warning(f"Stored token {i+1}: {stored_token[:50]}...")
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

                entry["supabase_access_token"] = new_access
                entry["supabase_refresh_token"] = new_refresh
                entry["supabase_exp"] = new_exp
                logger.info(
                    "Refreshed Supabase access token via backend token exchange"
                )
                return new_access

        except Exception as e:
            logger.error(f"Failed to refresh Supabase session: {e}")

        return entry.get("supabase_access_token")

    @classmethod
    def reissue_backend_token(
        cls, backend_token: str, ttl_seconds: int = 60 * 60 * 24
    ) -> Optional[str]:
        """Reissue a fresh backend token using the stored mapping for the given backend token."""
        entry = cls._token_store.get(backend_token)
        if not entry:
            return None
        user_id = entry.get("user_id")
        email = entry.get("email")
        access = entry.get("supabase_access_token")
        refresh = entry.get("supabase_refresh_token")
        if not user_id or not email or not access:
            return None
        return cls.issue_backend_token(
            user_id=user_id,
            email=email,
            supabase_access_token=access,
            supabase_refresh_token=refresh,
            ttl_seconds=ttl_seconds,
        )

    @classmethod
    def get_mapping(cls, backend_token: str) -> Optional[Dict[str, Any]]:
        """Return stored mapping for diagnostics or downstream use."""
        return cls._token_store.get(backend_token)
