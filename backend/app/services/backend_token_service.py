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
import base64
import json


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
    def _extract_supabase_expiry(cls, supabase_access_token: str) -> Optional[int]:
        """Extract expiry timestamp from Supabase access token."""
        try:
            # JWT has 3 parts: header.payload.signature
            parts = supabase_access_token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (add padding if needed)
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
                
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            return payload.get('exp')
        except Exception as e:
            logger.debug(f"Failed to extract Supabase token expiry: {e}")
            return None

    @classmethod
    def issue_backend_token(
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

        cls._token_store[backend_token] = {
            "user_id": user_id,
            "email": email,
            "supabase_access_token": supabase_access_token,
            "supabase_refresh_token": supabase_refresh_token,
            "supabase_exp": supa_exp,
            "backend_exp": backend_exp,
            "issued_at": now,
        }

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
    async def refresh_coordinated_tokens(
        cls, backend_token: str
    ) -> Optional[str]:
        """Refresh both Supabase and backend tokens in coordination."""
        entry = cls._token_store.get(backend_token)
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
                new_backend_token = cls.issue_backend_token(
                    user_id=result.user.id,
                    email=result.user.email,
                    supabase_access_token=result.session.access_token,
                    supabase_refresh_token=result.session.refresh_token,
                    coordinate_expiry=True,
                )
                
                # Clean up old token from store
                del cls._token_store[backend_token]
                
                logger.info("Successfully refreshed coordinated tokens")
                return new_backend_token
                
        except Exception as e:
            logger.error(f"Failed to refresh coordinated tokens: {e}")
        
        return None

    @classmethod
    def reissue_backend_token(
        cls, backend_token: str, ttl_seconds: Optional[int] = None
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
            coordinate_expiry=True,
        )

    @classmethod
    def get_mapping(cls, backend_token: str) -> Optional[Dict[str, Any]]:
        """Return stored mapping for diagnostics or downstream use."""
        return cls._token_store.get(backend_token)
