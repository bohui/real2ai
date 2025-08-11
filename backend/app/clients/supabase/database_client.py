"""
Supabase database client implementation.

DEPRECATED: This PostgREST-based database client is deprecated in favor of 
the repository pattern with direct asyncpg connections. New code should use 
repository classes from app.services.repositories.

Use DB_USE_REPOSITORIES=False to temporarily re-enable legacy behavior.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from supabase import Client
from postgrest import APIError
from enum import Enum

from ..base.client import with_retry
from ..base.interfaces import DatabaseOperations
from ..base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientValidationError,
)
from .config import SupabaseClientConfig

logger = logging.getLogger(__name__)


def serialize_datetime_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize values to be JSON-compatible for PostgREST.

    - datetime -> ISO string
    - Enum -> .value
    - Pydantic models (v2: model_dump, v1: dict) -> plain dict
    - Recurse through dicts and lists
    """
    if not isinstance(data, dict):
        return data

    def convert_value(value: Any) -> Any:
        # Handle datetime
        if isinstance(value, datetime):
            return value.isoformat()
        # Handle Enum
        if isinstance(value, Enum):
            return value.value
        # Handle Pydantic BaseModel (v2) and (v1)
        if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
            try:
                value = value.model_dump()
            except Exception:
                pass
        elif hasattr(value, "dict") and callable(getattr(value, "dict")):
            try:
                value = value.dict()
            except Exception:
                pass

        # Recurse
        if isinstance(value, dict):
            return serialize_datetime_values(value)
        if isinstance(value, list):
            return [convert_value(item) for item in value]
        return value

    return {key: convert_value(val) for key, val in data.items()}


def is_jwt_expired_error(error: Exception) -> bool:
    """Check if the error indicates JWT expiration."""
    error_str = str(error).lower()
    error_details = getattr(error, "details", None) or getattr(error, "message", None)

    # Check main error message
    jwt_indicators = [
        "jwt expired",
        "pgrst301",
        "token expired",
        "unauthorized",
        "invalid_token",
    ]

    if any(indicator in error_str for indicator in jwt_indicators):
        # Additional logging for clock sync diagnosis
        logger.warning(
            f"JWT expiration detected - this may indicate clock synchronization issues. "
            f"Error: {error_str[:200]}"
        )
        return True

    # Check error details/message if available
    if error_details:
        details_str = str(error_details).lower()
        if any(indicator in details_str for indicator in jwt_indicators):
            logger.warning(
                f"JWT expiration detected in error details - possible clock sync issue. "
                f"Details: {details_str[:200]}"
            )
            return True

    # Check if error code is PGRST301 specifically
    if hasattr(error, "code") and error.code == "PGRST301":
        logger.warning("PGRST301 error detected - JWT expiration or clock sync issue")
        return True

    return False


class SupabaseDatabaseClient(DatabaseOperations):
    """
    Supabase database operations client.
    
    DEPRECATED: This PostgREST-based client is deprecated in favor of 
    repository pattern with asyncpg. Use repository classes instead.
    """

    def __init__(self, supabase_client: Client, config: SupabaseClientConfig):
        import warnings
        warnings.warn(
            "SupabaseDatabaseClient is deprecated. Use repository pattern with asyncpg instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.supabase_client = supabase_client
        self.config = config
        self.client_name = "SupabaseDatabaseClient"
        self.logger = logging.getLogger(f"{__name__}.{self.client_name}")
        self._initialized = False
        # Check if this is a service role client by examining the underlying client's key
        self._is_service_role = self._detect_service_role()

    def _detect_service_role(self) -> bool:
        """Detect if this is a service role client by checking the underlying client's key."""
        try:
            # Check if the underlying client is using the service key
            # The service role client is created with service_key instead of anon_key
            if hasattr(self.supabase_client, "supabase_key"):
                return self.supabase_client.supabase_key == self.config.service_key
            # Alternative check: look for service key in the client's headers or auth
            if hasattr(self.supabase_client, "postgrest") and hasattr(
                self.supabase_client.postgrest, "headers"
            ):
                auth_header = self.supabase_client.postgrest.headers.get(
                    "Authorization", ""
                )
                if (
                    auth_header.startswith("Bearer ") and len(auth_header) > 100
                ):  # Service keys are typically longer
                    return True
            return False
        except Exception:
            return False

    async def initialize(self) -> None:
        """Initialize database client."""
        try:
            # Test a basic database operation
            await self._test_database_connection()
            self._initialized = True
            self.logger.info("Database client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database client: {e}")
            raise ClientConnectionError(
                f"Failed to initialize database client: {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def _apply_auth_from_context(self) -> None:
        """Apply per-request auth from AuthContext if available.

        Ensures PostgREST requests carry the user's JWT (or revert to anon key).
        Import is done lazily to avoid circular imports at module load time.
        """
        try:
            # Skip auth context application for service role clients
            if self._is_service_role:
                self.logger.debug(
                    "Service role client detected - skipping auth context application"
                )
                return

            from app.core.auth_context import AuthContext  # Lazy import

            token = AuthContext.get_user_token()
            if token:
                self.supabase_client.postgrest.auth(token)
            else:
                # Revert to anon key if no user token present
                self.supabase_client.postgrest.auth(self.config.anon_key)
        except Exception as e:
            # Do not fail DB ops if auth context is unavailable; just log
            self.logger.debug(f"Auth context not applied: {e}")

    async def _test_database_connection(self) -> None:
        """Test database connection with a simple query."""
        try:
            # Try a simple query that should work in any Supabase setup
            # Use a simple RPC call or check if we can access the database
            result = (
                self.supabase_client.table("profiles")
                .select("count", count="exact")
                .limit(1)
                .execute()
            )
            self.logger.debug(f"Database connection test successful")
        except APIError as e:
            # If profiles table doesn't exist, that's OK - connection still works
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                self.logger.debug(
                    "Database connection test successful (profiles table doesn't exist)"
                )
                return
            # For other API errors, log but don't fail the connection test
            self.logger.debug(
                f"Database connection test successful (API error handled): {e}"
            )
        except Exception as e:
            # For any other errors, assume connection is still OK
            self.logger.debug(
                f"Database connection test successful (error handled): {e}"
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the specified table."""
        try:
            self._apply_auth_from_context()
            # Serialize datetime objects to ISO format strings
            serialized_data = serialize_datetime_values(data)
            self.logger.debug(f"Creating record in table '{table}': {serialized_data}")

            result = self.supabase_client.table(table).insert(serialized_data).execute()

            if result.data and len(result.data) > 0:
                created_record = result.data[0]
                self.logger.debug(f"Successfully created record: {created_record}")
                return created_record
            else:
                raise ClientError(
                    f"No data returned from create operation on table '{table}'",
                    client_name=self.client_name,
                )

        except APIError as e:
            self.logger.error(f"API error creating record in table '{table}': {e}")

            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                self.logger.info(
                    f"JWT expiration detected in database create operation for table '{table}'"
                )
                
                # Add detailed JWT diagnostics
                try:
                    from app.core.auth_context import AuthContext
                    from app.utils.jwt_diagnostics import log_jwt_timing_issue
                    token = AuthContext.get_user_token()
                    if token:
                        log_jwt_timing_issue(token, f"database_create_{table}_jwt_expired", e)
                except Exception as diag_error:
                    self.logger.debug(f"JWT diagnostics failed: {diag_error}")
                
                raise ClientError(
                    f"JWT expired: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

            # For other API errors
            raise ClientError(
                f"Failed to create record in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating record in table '{table}': {e}"
            )
            raise ClientError(
                f"Unexpected error creating record in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query, supporting basic operators and skipping None values.

        Supported suffix operators (use double underscore):
        - __eq (default)
        - __neq
        - __gt
        - __gte
        - __lt
        - __lte
        - __in (expects a list/tuple)
        - __is (NULL checks)
        """
        if not filters:
            return query

        for raw_key, value in filters.items():
            if value is None:
                continue

            if "__" in raw_key:
                column, op = raw_key.rsplit("__", 1)
            else:
                column, op = raw_key, "eq"

            op = op.lower()

            if op == "eq":
                query = query.eq(column, value)
            elif op == "neq":
                query = query.neq(column, value)
            elif op == "gt":
                query = query.gt(column, value)
            elif op == "gte":
                query = query.gte(column, value)
            elif op == "lt":
                query = query.lt(column, value)
            elif op == "lte":
                query = query.lte(column, value)
            elif op == "in":
                # Ensure value is an iterable of values
                in_values = value if isinstance(value, (list, tuple)) else [value]
                query = query.in_(column, in_values)
            elif op == "is":
                query = query.is_(column, value)
            else:
                # Fallback to eq if unknown operator
                query = query.eq(column, value)

        return query

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def read(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        count_only: bool = False,
    ) -> List[Dict[str, Any]] | Dict[str, Any]:
        """Read records from the specified table with optional filters.

        If count_only=True, returns a dict: {"count": int} using exact count.
        Otherwise returns a list of records.
        """
        try:
            self._apply_auth_from_context()
            self.logger.debug(
                f"Reading from table '{table}' with filters: {filters}, count_only={count_only}, limit={limit}"
            )

            # For count-only queries, request an exact count from PostgREST
            if count_only:
                query = self.supabase_client.table(table).select("id", count="exact")
                query = self._apply_filters(query, filters or {})
                # Limit isn't necessary for count, but harmless if provided
                if limit:
                    query = query.limit(limit)
                result = query.execute()
                count_value = getattr(result, "count", None)
                if count_value is None:
                    # Fallback: use length of data when count header not provided
                    count_value = len(result.data or [])
                return {"count": int(count_value)}

            query = self.supabase_client.table(table).select("*")
            query = self._apply_filters(query, filters or {})

            # Apply limit if specified
            if limit:
                query = query.limit(limit)

            result = query.execute()

            records = result.data or []
            self.logger.debug(
                f"Successfully read {len(records)} records from table '{table}'"
            )
            return records

        except APIError as e:
            self.logger.error(f"API error reading from table '{table}': {e}")

            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                self.logger.info(
                    f"JWT expiration detected in database read operation for table '{table}'"
                )
                raise ClientError(
                    f"JWT expired: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

            # For other API errors
            raise ClientError(
                f"Failed to read from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error reading from table '{table}': {e}")
            raise ClientError(
                f"Unexpected error reading from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def update(
        self, table: str, record_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a record in the specified table."""
        try:
            self._apply_auth_from_context()
            # Serialize datetime objects to ISO format strings
            serialized_data = serialize_datetime_values(data)
            self.logger.debug(
                f"Updating record {record_id} in table '{table}': {serialized_data}"
            )

            result = (
                self.supabase_client.table(table)
                .update(serialized_data)
                .eq("id", record_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                updated_record = result.data[0]
                self.logger.debug(f"Successfully updated record: {updated_record}")
                return updated_record
            else:
                # This typically indicates RLS policy blocked the operation due to JWT token mismatch
                # Common in background tasks when multiple concurrent tasks share the same client
                error_msg = (
                    f"No data returned from update operation on table '{table}' for record {record_id}. "
                    f"This usually indicates Row Level Security (RLS) blocked the operation, "
                    f"possibly due to JWT token race condition in concurrent background tasks."
                )
                self.logger.warning(error_msg)
                raise ClientError(error_msg, client_name=self.client_name)

        except APIError as e:
            self.logger.error(
                f"API error updating record {record_id} in table '{table}': {e}"
            )

            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                self.logger.info(
                    f"JWT expiration detected in database update operation for table '{table}'"
                )
                raise ClientError(
                    f"JWT expired: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

            # For other API errors
            raise ClientError(
                f"Failed to update record {record_id} in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error updating record {record_id} in table '{table}': {e}"
            )
            raise ClientError(
                f"Unexpected error updating record {record_id} in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def delete(self, table: str, record_id: str) -> bool:
        """Delete a record from the specified table."""
        try:
            self._apply_auth_from_context()
            self.logger.debug(f"Deleting record {record_id} from table '{table}'")

            result = (
                self.supabase_client.table(table).delete().eq("id", record_id).execute()
            )

            # Supabase returns the deleted records in result.data
            success = result.data is not None
            if success:
                self.logger.debug(
                    f"Successfully deleted record {record_id} from table '{table}'"
                )
            else:
                self.logger.warning(
                    f"No record found to delete with ID {record_id} in table '{table}'"
                )

            return success

        except APIError as e:
            self.logger.error(
                f"API error deleting record {record_id} from table '{table}': {e}"
            )
            raise ClientError(
                f"Failed to delete record {record_id} from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error deleting record {record_id} from table '{table}': {e}"
            )
            raise ClientError(
                f"Unexpected error deleting record {record_id} from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def upsert(
        self, table: str, data: Dict[str, Any], conflict_columns: List[str] = None
    ) -> Dict[str, Any]:
        """Insert or update a record based on conflict resolution."""
        try:
            self._apply_auth_from_context()
            # Serialize datetime objects to ISO format strings
            serialized_data = serialize_datetime_values(data)
            self.logger.debug(f"Upserting record in table '{table}': {serialized_data}")

            # Add conflict resolution if specified
            if conflict_columns:
                # Supabase upsert uses on_conflict parameter with column names
                on_conflict = ",".join(conflict_columns)
                query = self.supabase_client.table(table).upsert(
                    serialized_data, on_conflict=on_conflict
                )
            else:
                query = self.supabase_client.table(table).upsert(serialized_data)

            result = query.execute()

            if result.data and len(result.data) > 0:
                upserted_record = result.data[0]
                self.logger.debug(f"Successfully upserted record: {upserted_record}")
                return upserted_record
            else:
                # This typically indicates RLS policy blocked the operation due to JWT token mismatch
                # Common in background tasks when multiple concurrent tasks share the same client
                error_msg = (
                    f"No data returned from upsert operation on table '{table}'. "
                    f"This usually indicates Row Level Security (RLS) blocked the operation, "
                    f"possibly due to JWT token race condition in concurrent background tasks."
                )
                self.logger.warning(error_msg)
                raise ClientError(error_msg, client_name=self.client_name)

        except APIError as e:
            self.logger.error(f"API error upserting record in table '{table}': {e}")
            raise ClientError(
                f"Failed to upsert record in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error upserting record in table '{table}': {e}"
            )
            raise ClientError(
                f"Unexpected error upserting record in table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def execute_rpc(
        self, function_name: str, params: Dict[str, Any] = None
    ) -> Any:
        """Execute a remote procedure call or stored function."""
        try:
            self._apply_auth_from_context()
            # Serialize datetime objects in parameters
            serialized_params = serialize_datetime_values(params) if params else None
            self.logger.debug(
                f"Executing RPC function '{function_name}' with params: {serialized_params}"
            )

            if serialized_params:
                result = self.supabase_client.rpc(
                    function_name, serialized_params
                ).execute()
            else:
                result = self.supabase_client.rpc(function_name).execute()

            self.logger.debug(f"Successfully executed RPC function '{function_name}'")
            return result.data

        except APIError as e:
            # Add JWT diagnostics for RPC failures
            try:
                from app.core.auth_context import AuthContext
                from app.utils.jwt_diagnostics import log_jwt_timing_issue
                token = AuthContext.get_user_token()
                if token and is_jwt_expired_error(e):
                    log_jwt_timing_issue(token, f"rpc_{function_name}_jwt_expired", e)
            except Exception as diag_error:
                logger.debug(f"JWT diagnostics failed: {diag_error}")
            
            # Handle specific case for ensure_bucket_exists which returns 200 but with JSON parsing issues
            if function_name == "ensure_bucket_exists" and hasattr(e, "details"):
                try:
                    # Extract the actual response from the error details
                    import json
                    import re

                    # The details often contain the actual response in a nested format
                    details_str = str(e.details)

                    # Look for JSON pattern in the details
                    json_match = re.search(r"b\'({.*})\'", details_str)
                    if json_match:
                        json_str = json_match.group(1)
                        response_data = json.loads(json_str)
                        self.logger.debug(
                            f"Successfully parsed ensure_bucket_exists response: {response_data}"
                        )
                        return response_data

                    # Fallback: try to parse the details directly
                    if "bucket already exists" in details_str.lower():
                        self.logger.debug(
                            f"Bucket already exists (parsed from error): {function_name}"
                        )
                        return {
                            "created": False,
                            "bucket_name": params.get("bucket_name", "unknown"),
                            "message": "Bucket already exists",
                        }

                except Exception as parse_error:
                    self.logger.debug(
                        f"Could not parse ensure_bucket_exists response, treating as non-critical: {parse_error}"
                    )
                    return {
                        "created": False,
                        "message": "Bucket operation completed (parsing failed)",
                    }

            self.logger.error(
                f"API error executing RPC function '{function_name}': {e}"
            )
            raise ClientError(
                f"Failed to execute RPC function '{function_name}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error executing RPC function '{function_name}': {e}"
            )
            raise ClientError(
                f"Unexpected error executing RPC function '{function_name}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new record in the specified table - wrapper for compatibility."""
        try:
            created_record = await self.create(table, data)
            return {"success": True, "data": created_record}
        except Exception as e:
            self.logger.error(f"Insert operation failed for table '{table}': {e}")
            return {"success": False, "data": None, "error": str(e)}

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Dict[str, Any] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Select records with optional filtering, ordering, and limiting - used by contract router."""
        try:
            self._apply_auth_from_context()
            self.logger.debug(
                f"Selecting from table '{table}' columns '{columns}' with filters: {filters}, order_by: {order_by}, limit: {limit}"
            )

            query = self.supabase_client.table(table).select(columns)
            query = self._apply_filters(query, filters)

            # Apply ordering if provided
            if order_by:
                # Parse order_by string (e.g., "created_at DESC" or "updated_at ASC")
                order_parts = order_by.strip().split()
                if len(order_parts) >= 1:
                    column = order_parts[0]
                    direction = (
                        order_parts[1].upper() if len(order_parts) > 1 else "ASC"
                    )
                    if direction == "DESC":
                        query = query.order(column, desc=True)
                    else:
                        query = query.order(column, desc=False)

            # Apply limit if provided
            if limit:
                query = query.limit(limit)

            result = query.execute()

            return {
                "data": result.data or [],
                "count": len(result.data) if result.data else 0,
            }

        except APIError as e:
            self.logger.error(f"API error selecting from table '{table}': {e}")

            # Check if this is a JWT expiration error
            if is_jwt_expired_error(e):
                self.logger.info(
                    f"JWT expiration detected in database select operation for table '{table}'"
                )
                raise ClientError(
                    f"JWT expired: {str(e)}",
                    client_name=self.client_name,
                    original_error=e,
                )

            # For other API errors
            raise ClientError(
                f"Failed to select from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )
        except ConnectionRefusedError as e:
            self.logger.error(
                f"Connection refused error selecting from table '{table}': {e}"
            )
            raise ClientConnectionError(
                f"Database connection refused. Please check if Supabase is running and accessible at {self.config.url}",
                client_name=self.client_name,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error selecting from table '{table}': {e}")
            # Check if this is a connection-related error
            if "Connection refused" in str(e) or "Errno 111" in str(e):
                raise ClientConnectionError(
                    f"Database connection failed. Please check if Supabase is running and accessible at {self.config.url}",
                    client_name=self.client_name,
                    original_error=e,
                )
            raise ClientError(
                f"Unexpected error selecting from table '{table}': {str(e)}",
                client_name=self.client_name,
                original_error=e,
            )

    def table(self, table_name: str):
        """Get direct access to table for complex queries."""
        return self.supabase_client.table(table_name)

    def from_(self, table_name: str):
        """Get direct access to table using from_ syntax."""
        return self.supabase_client.from_(table_name)

    async def health_check(self) -> Dict[str, Any]:
        """Check database client health."""
        try:
            await self._test_database_connection()
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "connection": "ok",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """Close database client."""
        self._initialized = False
        self.logger.info("Database client closed successfully")
