"""
Analyses Repository - Analysis operations with flexible scoping

This repository handles analysis operations with support for both user-scoped
and shared analyses depending on table RLS configuration.
"""

from typing import Dict, List, Optional, Any
import json
from uuid import UUID
from datetime import datetime
import logging

from app.database.connection import get_user_connection, get_service_role_connection
from app.models.supabase_models import Analysis
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


class AnalysesRepository:
    """Repository for analysis operations with flexible scoping"""

    def __init__(self, user_id: Optional[UUID] = None, use_service_role: bool = False):
        """
        Initialize analyses repository.

        Args:
            user_id: Optional user ID for user-scoped operations
            use_service_role: If True, use service role for shared analyses
        """
        self.user_id = user_id
        self.use_service_role = use_service_role

    async def upsert_analysis(
        self,
        content_hash: str,
        agent_version: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> Analysis:
        """
        Upsert analysis by content hash and agent version.

        Args:
            content_hash: SHA-256 hash of analyzed content
            agent_version: Version of analysis agent
            status: Analysis status
            result: Optional analysis result
            error_details: Optional error details
            started_at: Optional analysis start time
            completed_at: Optional analysis completion time

        Returns:
            Analysis: Existing or newly created analysis
        """
        # Build dynamic query based on provided parameters
        set_clauses = ["status = EXCLUDED.status", "updated_at = now()"]
        insert_columns = ["content_hash", "agent_version", "status"]
        insert_values = ["$1", "$2", "$3"]
        params = [content_hash, agent_version, status]
        param_count = 3

        if result is not None:
            param_count += 1
            insert_columns.append("result")
            insert_values.append(f"${param_count}::jsonb")
            set_clauses.append(f"result = EXCLUDED.result")
            params.append(json.dumps(result))

        if error_details is not None:
            param_count += 1
            insert_columns.append("error_details")
            insert_values.append(f"${param_count}::jsonb")
            set_clauses.append(f"error_details = EXCLUDED.error_details")
            params.append(json.dumps(error_details))

        if started_at is not None:
            param_count += 1
            insert_columns.append("started_at")
            insert_values.append(f"${param_count}")
            set_clauses.append(
                f"started_at = COALESCE(analyses.started_at, EXCLUDED.started_at)"
            )
            params.append(started_at)

        if completed_at is not None:
            param_count += 1
            insert_columns.append("completed_at")
            insert_values.append(f"${param_count}")
            set_clauses.append(f"completed_at = EXCLUDED.completed_at")
            params.append(completed_at)

        # Add user_id if not using service role
        if not self.use_service_role:
            param_count += 1
            insert_columns.append("user_id")
            insert_values.append(
                f"COALESCE(${param_count}::uuid, (current_setting('request.jwt.claim.sub'))::uuid)"
            )
            params.append(self.user_id)

        query = f"""
            INSERT INTO analyses (
                {', '.join(insert_columns)}
            ) VALUES ({', '.join(insert_values)})
            ON CONFLICT (content_hash, agent_version) DO UPDATE SET
                {', '.join(set_clauses)}
            RETURNING id, content_hash, agent_version, status, result, 
                     error_details, started_at, completed_at, user_id,
                     created_at, updated_at
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(query, *params)
        else:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(query, *params)

        return Analysis(
            id=row["id"],
            content_hash=row["content_hash"],
            agent_version=row["agent_version"],
            status=row["status"],
            result=safe_json_loads(row["result"]),
            error_details=safe_json_loads(row["error_details"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_analysis_by_content_hash(
        self, content_hash: str, agent_version: Optional[str] = None
    ) -> Optional[Analysis]:
        """
        Get analysis by content hash and optional agent version.

        Args:
            content_hash: SHA-256 hash of analyzed content
            agent_version: Optional specific agent version

        Returns:
            Analysis or None if not found
        """
        if agent_version:
            query = f"""
                SELECT id, content_hash, agent_version, status, result, 
                       error_details, started_at, completed_at, user_id,
                       created_at, updated_at
                FROM analyses
                WHERE content_hash = $1 AND agent_version = $2
            """
            params = [content_hash, agent_version]
        else:
            # Get latest analysis for this content hash
            query = f"""
                SELECT id, content_hash, agent_version, status, result, 
                       error_details, started_at, completed_at, user_id,
                       created_at, updated_at
                FROM analyses
                WHERE content_hash = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = [content_hash]

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(query, *params)
        else:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(query, *params)

        if not row:
            return None

        return Analysis(
            id=row["id"],
            content_hash=row["content_hash"],
            agent_version=row["agent_version"],
            status=row["status"],
            result=safe_json_loads(row["result"]),
            error_details=safe_json_loads(row["error_details"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_analysis_by_id(self, analysis_id: UUID) -> Optional[Analysis]:
        """
        Get analysis by ID.

        Args:
            analysis_id: Analysis ID

        Returns:
            Analysis or None if not found
        """
        query = f"""
            SELECT id, content_hash, agent_version, status, result, 
                   error_details, started_at, completed_at, user_id,
                   created_at, updated_at
            FROM analyses
            WHERE id = $1
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(query, analysis_id)
        else:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(query, analysis_id)

        if not row:
            return None

        return Analysis(
            id=row["id"],
            content_hash=row["content_hash"],
            agent_version=row["agent_version"],
            status=row["status"],
            result=safe_json_loads(row["result"]),
            error_details=safe_json_loads(row["error_details"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_analysis_status(
        self,
        analysis_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update analysis status and result.

        Args:
            analysis_id: Analysis ID
            status: New status
            result: Optional analysis result
            error_details: Optional error details
            completed_at: Optional completion time

        Returns:
            True if update successful, False otherwise
        """
        # Build dynamic query based on provided parameters
        set_clauses = ["status = $1", "updated_at = now()"]
        params = [status]
        param_count = 1

        if result is not None:
            param_count += 1
            set_clauses.append(f"result = ${param_count}::jsonb")
            params.append(json.dumps(result))

        if error_details is not None:
            param_count += 1
            set_clauses.append(f"error_details = ${param_count}::jsonb")
            params.append(json.dumps(error_details))

        if completed_at is not None:
            param_count += 1
            set_clauses.append(f"completed_at = ${param_count}")
            params.append(completed_at)

        # Add WHERE clause parameters
        param_count += 1
        params.append(analysis_id)

        query = f"""
            UPDATE analyses 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                result = await conn.execute(query, *params)
        else:
            async with get_user_connection(self.user_id) as conn:
                result = await conn.execute(query, *params)

        return result.split()[-1] == "1"

    async def list_analyses_by_status(
        self, status: str, limit: int = 50, offset: int = 0
    ) -> List[Analysis]:
        """
        List analyses by status.

        Args:
            status: Analysis status to filter by
            limit: Maximum number of analyses to return
            offset: Offset for pagination

        Returns:
            List of Analysis objects
        """
        query = f"""
            SELECT id, content_hash, agent_version, status, result, 
                   error_details, started_at, completed_at, user_id,
                   created_at, updated_at
            FROM analyses
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                rows = await conn.fetch(query, status, limit, offset)
        else:
            async with get_user_connection(self.user_id) as conn:
                rows = await conn.fetch(query, status, limit, offset)

        return [
            Analysis(
                id=row["id"],
                content_hash=row["content_hash"],
                agent_version=row["agent_version"],
                status=row["status"],
                result=safe_json_loads(row["result"]),
                error_details=safe_json_loads(row["error_details"]),
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                user_id=row["user_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def list_analyses_by_agent_version(
        self, agent_version: str, limit: int = 50, offset: int = 0
    ) -> List[Analysis]:
        """
        List analyses by agent version.

        Args:
            agent_version: Agent version to filter by
            limit: Maximum number of analyses to return
            offset: Offset for pagination

        Returns:
            List of Analysis objects
        """
        query = f"""
            SELECT id, content_hash, agent_version, status, result, 
                   error_details, started_at, completed_at, user_id,
                   created_at, updated_at
            FROM analyses
            WHERE agent_version = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                rows = await conn.fetch(query, agent_version, limit, offset)
        else:
            async with get_user_connection(self.user_id) as conn:
                rows = await conn.fetch(query, agent_version, limit, offset)

        return [
            Analysis(
                id=row["id"],
                content_hash=row["content_hash"],
                agent_version=row["agent_version"],
                status=row["status"],
                result=safe_json_loads(row["result"]),
                error_details=safe_json_loads(row["error_details"]),
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                user_id=row["user_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def delete_analysis(self, analysis_id: UUID) -> bool:
        """
        Delete an analysis.

        Args:
            analysis_id: Analysis ID

        Returns:
            True if deletion successful, False otherwise
        """
        query = "DELETE FROM analyses WHERE id = $1"

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                result = await conn.execute(query, analysis_id)
        else:
            async with get_user_connection(self.user_id) as conn:
                result = await conn.execute(query, analysis_id)

        return result.split()[-1] == "1"

    async def get_analysis_stats(self) -> Dict[str, Any]:
        """
        Get analysis statistics.

        Returns:
            Dictionary with analysis statistics
        """
        total_query = "SELECT COUNT(*) as total FROM analyses"
        status_query = f"""
            SELECT status, COUNT(*) as count
            FROM analyses
            GROUP BY status
            ORDER BY count DESC
        """
        agent_query = """
            SELECT agent_version, COUNT(*) as count
            FROM analyses
            GROUP BY agent_version
            ORDER BY count DESC
        """

        if self.use_service_role:
            async with get_service_role_connection() as conn:
                total_row = await conn.fetchrow(total_query)
                status_rows = await conn.fetch(status_query)
                agent_rows = await conn.fetch(agent_query)
        else:
            async with get_user_connection(self.user_id) as conn:
                total_row = await conn.fetchrow(total_query)
                status_rows = await conn.fetch(status_query)
                agent_rows = await conn.fetch(agent_query)

        return {
            "total_analyses": total_row["total"],
            "by_status": {row["status"]: row["count"] for row in status_rows},
            "by_agent_version": {
                row["agent_version"]: row["count"] for row in agent_rows
            },
        }

    async def retry_contract_analysis(
        self, content_hash: str, user_id: str
    ) -> Optional[UUID]:
        """
        Retry contract analysis by calling the database RPC function.

        Args:
            content_hash: Content hash for the analysis
            user_id: User ID as string

        Returns:
            Analysis ID if successful, None otherwise
        """
        # Use service role for RPC function execution since it typically requires elevated permissions
        async with get_service_role_connection() as conn:
            try:
                result = await conn.fetchval(
                    "SELECT retry_contract_analysis($1, $2)",
                    content_hash,
                    UUID(user_id) if isinstance(user_id, str) else user_id,
                )
                return result if result else None
            except Exception as e:
                # If the RPC is missing, emulate a retry by ensuring an analyses row exists
                logger.error(
                    f"Failed to retry contract analysis via RPC: {e}. Falling back to upsert.",
                    exc_info=True,
                )

                try:
                    # Create or reset a pending analysis for the latest agent_version
                    # We use the same upsert mechanism as upsert_analysis but minimal fields
                    upsert_sql = """
                        INSERT INTO analyses (content_hash, agent_version, status, result, error_details)
                        VALUES ($1, $2, 'pending', '{}'::jsonb, NULL)
                        ON CONFLICT (content_hash, agent_version) DO UPDATE SET
                            status = 'pending',
                            result = '{}'::jsonb,
                            error_details = NULL,
                            started_at = NULL,
                            completed_at = NULL,
                            updated_at = now()
                        RETURNING id
                        """
                    analysis_id = await conn.fetchval(
                        upsert_sql,
                        content_hash,
                        "1.0",
                    )
                    return analysis_id
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback analysis upsert failed: {fallback_error}",
                        exc_info=True,
                    )
                    return None
