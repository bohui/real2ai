"""
Main Supabase client implementation.
"""

import logging
from typing import Any, Dict, Optional, List
import asyncio
import aiohttp
import time
from urllib.parse import urlsplit, urlunsplit
from supabase import create_client, Client
from postgrest import APIError

from ..base.client import BaseClient, with_retry
from ..base.exceptions import (
    ClientConnectionError,
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
            self._supabase_client = create_client(self.config.url, self.config.anon_key)

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
                original_error=e,
            )

    async def _test_connection(self) -> None:
        """Test Supabase connection."""
        try:
            # Try a simple query to test connection
            # Use profiles table as it's likely to exist
            result = (
                self._supabase_client.table("profiles")
                .select("count", count="exact")
                .limit(1)
                .execute()
            )
            self.logger.debug(f"Connection test successful: {result.count is not None}")

        except APIError as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                # Table doesn't exist but connection works
                self.logger.debug(
                    "Connection test successful (table doesn't exist but connection works)"
                )
                return
            raise ClientConnectionError(
                f"Supabase connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            raise ClientConnectionError(
                f"Supabase connection test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Supabase client."""
        try:
            # Test connection
            await self._test_connection()

            # Check sub-clients
            auth_health = (
                await self._auth_client.health_check()
                if self._auth_client
                else {"status": "not_initialized"}
            )
            db_health = (
                await self._db_client.health_check()
                if self._db_client
                else {"status": "not_initialized"}
            )

            overall_status = "healthy"
            if (
                auth_health.get("status") != "healthy"
                or db_health.get("status") != "healthy"
            ):
                overall_status = "degraded"

            return {
                "status": overall_status,
                "client_name": self.client_name,
                "initialized": self._initialized,
                "connection": "ok",
                "auth_status": auth_health.get("status", "unknown"),
                "database_status": db_health.get("status", "unknown"),
                "config": {
                    "url": (
                        self.config.url[:50] + "..."
                        if len(self.config.url) > 50
                        else self.config.url
                    ),
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                },
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
                original_error=e,
            )

    # Convenience methods that delegate to sub-clients

    def table(self, table_name: str) -> Any:
        """Get table client (database operation)."""
        return self.database.table(table_name)

    def from_(self, table_name: str) -> Any:
        """Get table client using from_ syntax."""
        return self.database.from_(table_name)

    def storage(self) -> Any:
        """Get storage client."""
        return self.supabase_client.storage

    async def execute_rpc(
        self, function_name: str, params: Dict[str, Any] = None
    ) -> Any:
        """Execute RPC function."""
        return await self.database.execute_rpc(function_name, params)

    async def authenticate_user(self, token: str) -> Any:
        """Authenticate user with token."""
        return await self.auth.authenticate_user(token)

    async def get_user(self, user_id: str) -> Any:
        """Get user by ID."""
        return await self.auth.get_user(user_id)

    def set_user_token(self, token: str, refresh_token: Optional[str] = None) -> None:
        """Set user JWT token (and optional refresh token) for RLS-enabled operations."""
        try:
            # Set the auth header for all subsequent requests
            if self._supabase_client:
                # For JWT token authentication, set auth for PostgREST
                self._supabase_client.postgrest.auth(token)

                # For storage operations, we need to create a proper auth session
                # The Supabase client handles storage auth through the session
                try:
                    # Try using the token directly with the auth client
                    # This should work for both database and storage operations
                    self._supabase_client.auth._set_auth(token)
                    self.logger.info("Auth token set directly on auth client")
                except AttributeError:
                    # If _set_auth doesn't exist, try the session approach
                    try:

                        # The set_session method expects positional arguments: (access_token, refresh_token)
                        self._supabase_client.auth.set_session(
                            token, refresh_token or ""
                        )
                        self.logger.info("User session set for storage operations")
                    except Exception as session_error:
                        self.logger.warning(f"Session method failed: {session_error}")
                        # Fallback: set headers directly if session method fails
                        self._set_storage_headers_directly(token)
                except Exception as auth_error:
                    self.logger.warning(f"Direct auth method failed: {auth_error}")
                    # Fallback: set headers directly
                    self._set_storage_headers_directly(token)

                self.logger.debug("User JWT token set for RLS operations")
            else:
                raise ClientError("Supabase client not initialized", self.client_name)
        except Exception as e:
            self.logger.error(f"Failed to set user token: {e}")
            raise ClientError(f"Failed to set user token: {str(e)}", self.client_name)

    def _set_storage_headers_directly(self, token: str) -> None:
        """Helper method to set storage headers directly."""
        try:
            # Use the suggested approach: client.storage.session.headers.update()
            if hasattr(self._supabase_client.storage, "session") and hasattr(
                self._supabase_client.storage.session, "headers"
            ):
                self._supabase_client.storage.session.headers.update(
                    {"Authorization": f"Bearer {token}"}
                )
                self.logger.info(
                    "Set Authorization header via storage.session.headers.update()"
                )
                return

            # Fallback approaches if the above doesn't work
            if hasattr(self._supabase_client, "_storage"):
                storage_client = self._supabase_client._storage
            else:
                storage_client = self._supabase_client.storage

            # Try to set headers directly on the storage client
            if hasattr(storage_client, "_headers"):
                storage_client._headers["Authorization"] = f"Bearer {token}"
                self.logger.info("Set Authorization header via _headers")
            elif hasattr(storage_client, "headers"):
                storage_client.headers["Authorization"] = f"Bearer {token}"
                self.logger.info("Set Authorization header via headers")
            else:
                # Try to access the underlying HTTP client
                if hasattr(storage_client, "_client") and hasattr(
                    storage_client._client, "headers"
                ):
                    storage_client._client.headers["Authorization"] = f"Bearer {token}"
                    self.logger.info("Set Authorization header via _client.headers")
                else:
                    self.logger.warning(
                        "Could not find a way to set storage headers directly"
                    )
        except Exception as e:
            self.logger.error(f"Failed to set storage headers directly: {e}")

    def set_auth_token(self, token: str, refresh_token: Optional[str] = None) -> None:
        """Alias for set_user_token for consistency with auth context."""
        self.set_user_token(token, refresh_token)

    def clear_auth_token(self) -> None:
        """Clear the auth token to revert to anon key."""
        try:
            if self._supabase_client:
                # Clear auth by setting back to anon key for PostgREST
                self._supabase_client.postgrest.auth(self.config.anon_key)

                # Clear the auth session to revert to anon access
                try:
                    self._supabase_client.auth.sign_out()
                    self.logger.debug("User session cleared")
                except Exception as session_error:
                    self.logger.warning(f"Session clear failed: {session_error}")

                self.logger.debug("Auth token cleared, using anon key")
        except Exception as e:
            self.logger.error(f"Failed to clear auth token: {e}")
            raise ClientError(f"Failed to clear auth token: {str(e)}", self.client_name)

    # Storage operations
    async def upload_file(
        self, bucket: str, path: str, file: bytes, content_type: str = None
    ) -> Dict[str, Any]:
        """Upload a file to Supabase storage."""
        try:
            self.logger.info(
                f"Uploading file to bucket '{bucket}' at path '{path}' (size: {len(file)} bytes)"
            )

            # Debug: Check current auth state
            try:
                current_session = self._supabase_client.auth.get_session()
                self.logger.info(f"Current auth session: {current_session is not None}")
                if current_session and hasattr(current_session, "access_token"):
                    self.logger.info(
                        f"Access token present: {bool(current_session.access_token)}"
                    )
            except Exception as auth_debug_error:
                self.logger.warning(f"Could not check auth session: {auth_debug_error}")

            # Get storage client
            storage = self.storage()

            # Debug: Check storage client auth headers
            try:
                if hasattr(storage, "_client") and hasattr(storage._client, "headers"):
                    auth_header = storage._client.headers.get(
                        "Authorization", "No auth header"
                    )
                    self.logger.info(
                        f"Storage client auth header: {auth_header[:20]}..."
                        if auth_header != "No auth header"
                        else auth_header
                    )
            except Exception as header_debug_error:
                self.logger.warning(
                    f"Could not check storage headers: {header_debug_error}"
                )

            # Upload file using Supabase storage API (run sync SDK call in a thread)
            self.logger.info(
                f"Attempting upload with storage.from_('{bucket}').upload('{path}', file)"
            )
            result = await asyncio.to_thread(storage.from_(bucket).upload, path, file)

            self.logger.info(f"File uploaded successfully to '{path}': {result}")
            return {"success": True, "path": path}

        except Exception as e:
            self.logger.error(f"Failed to upload file to '{path}': {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            return {"success": False, "error": str(e)}

    async def download_file(self, bucket: str, path: str) -> bytes:
        """Download a file from Supabase storage."""
        # Resilient download with signed URL + aiohttp (longer timeout, retries),
        # with fallback to the SDK's direct download.
        self.logger.debug(f"Downloading file from bucket '{bucket}' at path '{path}'")

        # Determine effective timeout (allow larger for big PDFs)
        effective_timeout_seconds = max(getattr(self.config, "timeout", 30), 120)
        max_retries = max(getattr(self.config, "max_retries", 3), 3)
        backoff_factor = max(getattr(self.config, "backoff_factor", 1.0), 1.0)

        last_error: Optional[Exception] = None

        # Attempt 1: Signed URL + aiohttp streaming download
        for attempt in range(max_retries + 1):
            try:
                # Generate a short-lived signed URL
                storage = self.storage()
                signed = storage.from_(bucket).create_signed_url(path, 600)

                # Try multiple shapes: attribute, dict, nested
                signed_url = None
                try:
                    # Common attribute
                    signed_url = getattr(signed, "signed_url", None)
                    # Alternative attributes
                    if not signed_url:
                        signed_url = getattr(signed, "signedURL", None)
                    if not signed_url:
                        signed_url = getattr(signed, "signedUrl", None)
                    # Dict-like
                    if not signed_url and isinstance(signed, dict):
                        for key in ("signed_url", "signedURL", "signedUrl"):
                            if key in signed:
                                signed_url = signed[key]
                                break
                        # Try nested under 'data'
                        if not signed_url and isinstance(signed.get("data"), dict):
                            for key in ("signed_url", "signedURL", "signedUrl"):
                                if key in signed["data"]:
                                    signed_url = signed["data"][key]
                                    break
                    # Object with 'data' attr
                    if (
                        not signed_url
                        and hasattr(signed, "data")
                        and isinstance(getattr(signed, "data"), dict)
                    ):
                        data_obj = getattr(signed, "data")
                        for key in ("signed_url", "signedURL", "signedUrl"):
                            if key in data_obj:
                                signed_url = data_obj[key]
                                break
                except Exception as extraction_err:
                    self.logger.debug(
                        f"Signed URL extraction raised: {type(extraction_err).__name__}: {extraction_err}"
                    )

                if not signed_url:
                    # Log response shape for debugging, with redaction
                    try:
                        shape_info = {
                            "type": type(signed).__name__,
                            "has_signed_url_attr": hasattr(signed, "signed_url"),
                            "has_signedURL_attr": hasattr(signed, "signedURL"),
                            "has_signedUrl_attr": hasattr(signed, "signedUrl"),
                            "has_data_attr": hasattr(signed, "data"),
                            "is_dict": isinstance(signed, dict),
                            "keys": (
                                list(signed.keys())[:10]
                                if isinstance(signed, dict)
                                else None
                            ),
                        }
                        self.logger.debug(
                            f"create_signed_url response shape: {shape_info}"
                        )
                    except Exception as log_err:
                        self.logger.debug(
                            f"Unable to log signed response shape: {type(log_err).__name__}: {log_err}"
                        )
                    raise RuntimeError("Failed to generate signed URL for download")

                # Normalize host for local environments: replace localhost/127.0.0.1
                # with the configured Supabase URL host (e.g., host.docker.internal)
                try:
                    cfg_parts = urlsplit(self.config.url)
                    su_parts = urlsplit(signed_url)
                    if su_parts.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
                        normalized = urlunsplit(
                            (
                                cfg_parts.scheme or su_parts.scheme,
                                cfg_parts.netloc,
                                su_parts.path,
                                su_parts.query,
                                su_parts.fragment,
                            )
                        )
                        self.logger.debug(
                            f"Normalized signed URL host from {su_parts.netloc} to {cfg_parts.netloc}"
                        )
                        signed_url = normalized
                except Exception as norm_err:
                    self.logger.debug(
                        f"Signed URL normalization skipped: {type(norm_err).__name__}: {norm_err}"
                    )

                # Use aiohttp with generous timeout
                timeout = aiohttp.ClientTimeout(
                    total=effective_timeout_seconds,
                    connect=min(15, effective_timeout_seconds),
                    sock_read=effective_timeout_seconds,
                )

                start_time = time.time()
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(signed_url) as resp:
                        if resp.status == 404:
                            raise FileNotFoundError(f"File not found: {bucket}/{path}")
                        if resp.status in (401, 403):
                            raise PermissionError(
                                f"Access denied for: {bucket}/{path} (status {resp.status})"
                            )
                        if resp.status >= 400:
                            text = await resp.text()
                            raise RuntimeError(
                                f"HTTP {resp.status} while downloading {bucket}/{path}: {text[:200]}"
                            )

                        # Stream into memory
                        data = bytearray()
                        async for chunk in resp.content.iter_chunked(1 << 20):  # 1MB
                            if chunk:
                                data.extend(chunk)

                duration = time.time() - start_time
                try:
                    # Redact token in logs if present
                    redacted_url = signed_url
                    if isinstance(redacted_url, str) and "token=" in redacted_url:
                        redacted_url = (
                            redacted_url.split("token=")[0] + "token=[REDACTED]"
                        )
                except Exception:
                    redacted_url = "<unavailable>"
                self.logger.info(
                    f"Downloaded {bucket}/{path} via signed URL in {duration:.2f}s, size={len(data)} bytes (url={redacted_url})"
                )
                return bytes(data)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    self.logger.warning(
                        f"Signed URL download attempt {attempt+1}/{max_retries+1} failed for {bucket}/{path}: {e}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                break
            except Exception as e:
                # Non-retryable or fatal — break to fallback
                last_error = e
                self.logger.warning(
                    f"Signed URL path failed for {bucket}/{path}: {e}. Will try SDK fallback."
                )
                break

        # Fallback: SDK direct download (may block; run in thread to avoid event loop blocking)
        try:
            storage = self.storage()
            self.logger.info(
                f"Falling back to SDK download for {bucket}/{path} (timeout may be limited)"
            )
            result = await asyncio.to_thread(storage.from_(bucket).download, path)
            self.logger.debug(
                f"File downloaded successfully from '{path}' via SDK fallback"
            )
            return result
        except Exception as e:
            self.logger.error(
                f"Failed to download file from '{path}' (signed URL + SDK fallback): {e}. Last signed-url error: {last_error}"
            )
            raise ValueError(
                f"Failed to download file: {str(e) if str(e) else type(e).__name__}"
            )

    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete a file from Supabase storage."""
        try:
            self.logger.debug(f"Deleting file from bucket '{bucket}' at path '{path}'")

            # Get storage client
            storage = self.storage()

            # Delete file using Supabase storage API
            # The correct method is storage.from_(bucket).remove([path])
            storage.from_(bucket).remove([path])

            self.logger.debug(f"File deleted successfully from '{path}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete file from '{path}': {e}")
            return False

    async def list_files(
        self, bucket: str, prefix: str = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List files in a bucket with optional prefix filter."""
        try:
            self.logger.debug(
                f"Listing files in bucket '{bucket}' with prefix '{prefix}'"
            )

            # Get storage client
            storage = self.storage()

            # List files using Supabase storage API (wrap sync SDK in thread)
            # The correct method is storage.from_(bucket).list(path=prefix)
            result = await asyncio.to_thread(storage.from_(bucket).list, prefix or "")

            files = []
            for item in result:
                files.append(
                    {
                        "name": item.name,
                        "id": item.id,
                        "updated_at": item.updated_at,
                        "created_at": item.created_at,
                        "last_accessed_at": item.last_accessed_at,
                        "metadata": item.metadata,
                    }
                )

            # Apply limit if specified
            if limit:
                files = files[:limit]

            self.logger.debug(f"Found {len(files)} files in bucket '{bucket}'")
            return files

        except Exception as e:
            self.logger.error(f"Failed to list files in bucket '{bucket}': {e}")
            return []

    async def generate_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str:
        """Generate a signed URL for file access."""
        try:
            self.logger.debug(
                f"Generating signed URL for '{path}' in bucket '{bucket}'"
            )

            # Get storage client
            storage = self.storage()

            # Generate signed URL using Supabase storage API (wrap sync SDK in thread)
            # The correct method is storage.from_(bucket).create_signed_url(path, expires_in)
            result = await asyncio.to_thread(
                storage.from_(bucket).create_signed_url, path, expires_in
            )

            self.logger.debug(f"Generated signed URL for '{path}'")
            return result.signed_url

        except Exception as e:
            self.logger.error(f"Failed to generate signed URL for '{path}': {e}")
            raise ValueError(f"Failed to generate signed URL: {str(e)}")

    async def get_file_info(self, bucket: str, path: str) -> Dict[str, Any]:
        """Get file metadata and information."""
        try:
            self.logger.debug(f"Getting file info for '{path}' in bucket '{bucket}'")

            # Get storage client
            storage = self.storage()

            # Get file info using Supabase storage API (wrap sync SDK in thread)
            # The correct method is storage.from_(bucket).list(path=path)
            result = await asyncio.to_thread(storage.from_(bucket).list, path)

            if not result:
                raise ValueError(f"File not found: {path}")

            file_info = result[0]
            return {
                "name": file_info.name,
                "id": file_info.id,
                "updated_at": file_info.updated_at,
                "created_at": file_info.created_at,
                "last_accessed_at": file_info.last_accessed_at,
                "metadata": file_info.metadata,
            }

        except Exception as e:
            self.logger.error(f"Failed to get file info for '{path}': {e}")
            raise ValueError(f"Failed to get file info: {str(e)}")
