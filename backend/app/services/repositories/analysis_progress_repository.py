"""
Analysis Progress Repository - Progress tracking operations

This repository handles analysis progress operations with proper RLS enforcement.
Progress records are user-scoped and this repository provides CRUD operations
with integrated JWT-based authentication.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import logging

from app.database.connection import get_user_connection

logger = logging.getLogger(__name__)


@dataclass
class AnalysisProgress:
    """Analysis Progress model aligned with current `analysis_progress` schema."""

    id: UUID
    content_hash: str
    user_id: UUID
    current_step: str
    progress_percent: int
    step_description: Optional[str] = None
    estimated_completion_minutes: Optional[int] = None
    step_started_at: Optional[datetime] = None
    step_completed_at: Optional[datetime] = None
    total_elapsed_seconds: int = 0
    status: str = "in_progress"
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnalysisProgressRepository:
    """Repository for user-scoped analysis progress operations"""

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize analysis progress repository.

        Args:
            user_id: Optional user ID (uses auth context if not provided)
        """
        self.user_id = user_id

    async def upsert_progress(
        self, content_hash: str, user_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """
        Upsert analysis progress record with content_hash + user_id unique constraint.

        Args:
            content_hash: Content hash for the analysis
            user_id: User ID as string
            progress_data: Progress data dictionary containing:
                - current_step: str
                - progress_percent: int
                - step_description: Optional[str]
                - estimated_completion_minutes: Optional[int]
                - status: str
                - error_message: Optional[str]

        Returns:
            True if upsert successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            try:
                # Diagnostic logging for parameter types and values
                step_started_at = progress_data.get("step_started_at")
                logger.debug(
                    "[AnalysisProgressRepository] Upsert called",
                    extra={
                        "content_hash": content_hash,
                        "user_id": user_id,
                        "current_step": progress_data.get("current_step"),
                        "progress_percent": progress_data.get("progress_percent"),
                        "status": progress_data.get("status"),
                        "step_started_at_type": type(step_started_at).__name__,
                        "has_error_message": bool(progress_data.get("error_message")),
                    },
                )
                # Normalize datetime: ensure step_started_at is a datetime instance
                norm_step_started_at = progress_data.get("step_started_at")
                if isinstance(norm_step_started_at, str):
                    try:
                        norm_step_started_at = norm_step_started_at.replace(
                            "Z", "+00:00"
                        )
                        norm_step_started_at = datetime.fromisoformat(
                            norm_step_started_at
                        )
                    except Exception:
                        norm_step_started_at = None

                await conn.execute(
                    """
                    INSERT INTO analysis_progress (
                        content_hash, user_id, current_step, progress_percent,
                        step_description, step_started_at, estimated_completion_minutes,
                        status, error_message, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT (content_hash, user_id) 
                    DO UPDATE SET
                        current_step = EXCLUDED.current_step,
                        progress_percent = EXCLUDED.progress_percent,
                        step_description = EXCLUDED.step_description,
                        step_started_at = EXCLUDED.step_started_at,
                        estimated_completion_minutes = EXCLUDED.estimated_completion_minutes,
                        status = EXCLUDED.status,
                        error_message = EXCLUDED.error_message,
                        updated_at = NOW()
                    """,
                    content_hash,
                    UUID(user_id),
                    progress_data.get("current_step"),
                    progress_data.get("progress_percent"),
                    progress_data.get("step_description"),
                    norm_step_started_at,
                    progress_data.get("estimated_completion_minutes"),
                    progress_data.get("status", "in_progress"),
                    progress_data.get("error_message"),
                )
                logger.debug(
                    "[AnalysisProgressRepository] Upsert succeeded",
                    extra={
                        "content_hash": content_hash,
                        "user_id": user_id,
                        "current_step": progress_data.get("current_step"),
                    },
                )
                return True
            except Exception as e:
                logger.error(
                    f"Failed to upsert analysis progress: {e}",
                    extra={
                        "content_hash": content_hash,
                        "user_id": user_id,
                        "step_started_at_repr": repr(
                            progress_data.get("step_started_at")
                        ),
                        "progress_keys": list(progress_data.keys()),
                    },
                )
                return False

    async def get_latest_progress(
        self, content_hash: str, user_id: str, columns: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest progress record for content_hash and user_id.

        Args:
            content_hash: Content hash for the analysis
            user_id: User ID as string
            columns: Optional column specification (default: all columns)

        Returns:
            Progress record dictionary or None if not found
        """
        if columns is None:
            columns = (
                "current_step, progress_percent, updated_at, status, error_message"
            )

        async with get_user_connection(self.user_id) as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    SELECT {columns}
                    FROM analysis_progress
                    WHERE content_hash = $1 AND user_id = $2
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    content_hash,
                    UUID(user_id),
                )

                if not row:
                    return None

                return dict(row)
            except Exception as e:
                logger.error(f"Failed to get latest progress: {e}")
                return None

    async def get_progress_records(
        self,
        filters: Dict[str, Any],
        columns: Optional[str] = None,
        order_by: str = "updated_at DESC",
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get progress records with flexible filtering.

        Args:
            filters: Dictionary of filters (content_hash, user_id, status, etc.)
            columns: Optional column specification (default: all columns)
            order_by: Order by clause
            limit: Optional limit

        Returns:
            List of progress record dictionaries
        """
        if columns is None:
            columns = "*"

        async with get_user_connection(self.user_id) as conn:
            try:
                # Build WHERE clause dynamically
                where_clauses = []
                params = []
                param_count = 0

                for key, value in filters.items():
                    param_count += 1
                    where_clauses.append(f"{key} = ${param_count}")
                    if key == "user_id" and isinstance(value, str):
                        params.append(UUID(value))
                    else:
                        params.append(value)

                where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

                query = f"""
                    SELECT {columns}
                    FROM analysis_progress
                    WHERE {where_clause}
                    ORDER BY {order_by}
                """

                if limit:
                    query += f" LIMIT {limit}"

                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get progress records: {e}")
                return []

    async def delete_progress(self, content_hash: str, user_id: str) -> bool:
        """
        Delete progress record for content_hash and user_id.

        Args:
            content_hash: Content hash for the analysis
            user_id: User ID as string

        Returns:
            True if deletion successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            try:
                result = await conn.execute(
                    """
                    DELETE FROM analysis_progress 
                    WHERE content_hash = $1 AND user_id = $2
                    """,
                    content_hash,
                    UUID(user_id),
                )
                return result.split()[-1] == "1"
            except Exception as e:
                logger.error(f"Failed to delete progress record: {e}")
                return False

    async def update_progress_status(
        self,
        content_hash: str,
        user_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update progress status for content_hash and user_id.

        Args:
            content_hash: Content hash for the analysis
            user_id: User ID as string
            status: New status (in_progress, completed, failed, cancelled)
            error_message: Optional error message

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            try:
                if error_message is not None:
                    result = await conn.execute(
                        """
                        UPDATE analysis_progress 
                        SET status = $3, error_message = $4, updated_at = NOW()
                        WHERE content_hash = $1 AND user_id = $2
                        """,
                        content_hash,
                        UUID(user_id),
                        status,
                        error_message,
                    )
                else:
                    result = await conn.execute(
                        """
                        UPDATE analysis_progress 
                        SET status = $3, updated_at = NOW()
                        WHERE content_hash = $1 AND user_id = $2
                        """,
                        content_hash,
                        UUID(user_id),
                        status,
                    )
                return result.split()[-1] == "1"
            except Exception as e:
                logger.error(f"Failed to update progress status: {e}")
                return False

    async def get_active_analyses(
        self, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active (in_progress) analyses for a user.

        Args:
            user_id: Optional user ID filter (uses repository user_id if not provided)

        Returns:
            List of active progress records
        """
        filters = {"status": "in_progress"}
        if user_id:
            filters["user_id"] = user_id
        elif self.user_id:
            filters["user_id"] = str(self.user_id)

        return await self.get_progress_records(filters, order_by="updated_at DESC")
    
    async def clear_progress_for_content_hash(
        self, content_hash: str, user_id: str
    ) -> int:
        """
        Clear all progress records for a specific content hash and user.
        
        This is used when processing fails and needs to restart cleanly.
        
        Args:
            content_hash: Content hash to clear progress for
            user_id: User ID as string
            
        Returns:
            Number of records deleted
        """
        async with get_user_connection(self.user_id) as conn:
            try:
                result = await conn.execute(
                    """
                    DELETE FROM analysis_progress 
                    WHERE content_hash = $1 AND user_id = $2
                    """,
                    content_hash,
                    UUID(user_id),
                )
                # Extract number of affected rows from result
                affected_rows = int(result.split()[-1]) if result.split() else 0
                logger.info(
                    f"Cleared {affected_rows} progress records for content_hash {content_hash}"
                )
                return affected_rows
            except Exception as e:
                logger.error(f"Failed to clear progress records: {e}")
                return 0
    
    async def clear_stale_progress(
        self, cutoff_time: datetime, user_id: Optional[str] = None
    ) -> int:
        """
        Clear stale progress records older than the cutoff time.
        
        Args:
            cutoff_time: Delete records older than this time
            user_id: Optional user ID filter (clears for all users if not provided)
            
        Returns:
            Number of records deleted
        """
        async with get_user_connection(self.user_id) as conn:
            try:
                if user_id:
                    result = await conn.execute(
                        """
                        DELETE FROM analysis_progress 
                        WHERE updated_at < $1 AND user_id = $2
                        """,
                        cutoff_time,
                        UUID(user_id),
                    )
                else:
                    result = await conn.execute(
                        """
                        DELETE FROM analysis_progress 
                        WHERE updated_at < $1
                        """,
                        cutoff_time,
                    )
                
                # Extract number of affected rows from result
                affected_rows = int(result.split()[-1]) if result.split() else 0
                logger.info(
                    f"Cleared {affected_rows} stale progress records older than {cutoff_time}"
                )
                return affected_rows
            except Exception as e:
                logger.error(f"Failed to clear stale progress records: {e}")
                return 0
