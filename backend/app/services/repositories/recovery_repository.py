"""
Recovery Repository - Service-role recovery-related database operations.

This repository centralizes database access for the recovery system using the
shared connection layer instead of direct Supabase client table calls.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, timezone
from uuid import UUID

from app.database.connection import (
    get_service_role_connection,
    fetchrow_raw_sql,
    fetch_raw_sql,
    execute_raw_sql,
)

logger = logging.getLogger(__name__)


class RecoveryRepository:
    """Repository for recovery-related queries (service-role)."""

    async def verify_database_connectivity(self) -> bool:
        """Run a trivial query to verify database connectivity."""
        try:
            async with get_service_role_connection() as conn:
                _ = await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            return False

    async def get_analysis_progress_by_content_hash(
        self, content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch the latest analysis_progress row for a content_hash (any user)."""
        try:
            row = await fetchrow_raw_sql(
                """
                SELECT content_hash,
                       current_step,
                       progress_percent,
                       step_description,
                       status,
                       updated_at,
                       total_elapsed_seconds
                FROM analysis_progress
                WHERE content_hash = $1
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                content_hash,
            )
            return dict(row) if row else None
        except Exception as e:
            logger.warning(
                f"Failed to read analysis_progress for content_hash={content_hash}: {e}"
            )
            return None

    async def get_task_registry_row(
        self, registry_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Fetch task_registry row by id (service-role)."""
        try:
            row = await fetchrow_raw_sql(
                """
                SELECT id,
                       task_id,
                       task_name,
                       user_id,
                       current_state,
                       last_heartbeat,
                       recovery_priority,
                       progress_percent,
                       current_step,
                       task_args,
                       task_kwargs,
                       context_key
                FROM task_registry
                WHERE id = $1
                """,
                registry_id,
            )
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"Failed to load task_registry id={registry_id}: {e}")
            return None

    # -----------------------------
    # Aggregate counts for health
    # -----------------------------
    async def count_recovery_queue_pending(self) -> int:
        try:
            row = await fetchrow_raw_sql(
                "SELECT COUNT(*) AS c FROM recovery_queue WHERE status = 'pending'"
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to count pending recovery_queue: {e}")
            return 0

    async def count_recovery_queue_failed_since(self, since_iso: str) -> int:
        try:
            since_dt = _ensure_datetime(since_iso)
            row = await fetchrow_raw_sql(
                """
                SELECT COUNT(*) AS c
                FROM recovery_queue
                WHERE status = 'failed' AND created_at >= $1
                """,
                since_dt,
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(
                f"Failed to count failed recovery_queue since {since_iso}: {e}"
            )
            return 0

    async def count_task_registry_orphaned_before(self, cutoff_iso: str) -> int:
        try:
            cutoff_dt = _ensure_datetime(cutoff_iso)
            row = await fetchrow_raw_sql(
                """
                SELECT COUNT(*) AS c
                FROM task_registry
                WHERE current_state = 'orphaned' AND last_heartbeat < $1
                """,
                cutoff_dt,
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to count orphaned tasks before {cutoff_iso}: {e}")
            return 0

    async def count_task_registry_stuck_before(self, cutoff_iso: str) -> int:
        try:
            cutoff_dt = _ensure_datetime(cutoff_iso)
            row = await fetchrow_raw_sql(
                """
                SELECT COUNT(*) AS c
                FROM task_registry
                WHERE current_state IN ('processing','recovering')
                  AND last_heartbeat < $1
                """,
                cutoff_dt,
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to count stuck tasks before {cutoff_iso}: {e}")
            return 0

    async def count_recovery_queue_since(self, since_iso: str) -> int:
        try:
            since_dt = _ensure_datetime(since_iso)
            row = await fetchrow_raw_sql(
                "SELECT COUNT(*) AS c FROM recovery_queue WHERE created_at >= $1",
                since_dt,
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to count recovery_queue since {since_iso}: {e}")
            return 0

    async def count_recovery_queue_completed_since(self, since_iso: str) -> int:
        try:
            since_dt = _ensure_datetime(since_iso)
            row = await fetchrow_raw_sql(
                """
                SELECT COUNT(*) AS c
                FROM recovery_queue
                WHERE status = 'completed' AND created_at >= $1
                """,
                since_dt,
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.warning(
                f"Failed to count completed recovery_queue since {since_iso}: {e}"
            )
            return 0

    async def fetch_completed_recoveries_with_timings_since(
        self, since_iso: str
    ) -> List[Dict[str, Any]]:
        try:
            since_dt = _ensure_datetime(since_iso)
            rows = await fetch_raw_sql(
                """
                SELECT processing_started, processing_completed
                FROM recovery_queue
                WHERE status = 'completed'
                  AND created_at >= $1
                  AND processing_started IS NOT NULL
                  AND processing_completed IS NOT NULL
                """,
                since_dt,
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(
                f"Failed to fetch completed recoveries with timings since {since_iso}: {e}"
            )
            return []

    # -----------------------------
    # Cleanup helpers
    # -----------------------------
    async def delete_old_task_registry_completed_before(self, cutoff_iso: str) -> int:
        try:
            cutoff_dt = _ensure_datetime(cutoff_iso)
            result = await execute_raw_sql(
                """
                DELETE FROM task_registry
                WHERE current_state IN ('completed','failed')
                  AND updated_at < $1
                """,
                cutoff_dt,
            )
            try:
                return int(result.split()[-1])
            except Exception:
                return 0
        except Exception as e:
            logger.warning(
                f"Failed to delete old task_registry before {cutoff_iso}: {e}"
            )
            return 0

    async def delete_old_recovery_queue_before(self, cutoff_iso: str) -> int:
        try:
            cutoff_dt = _ensure_datetime(cutoff_iso)
            result = await execute_raw_sql(
                """
                DELETE FROM recovery_queue
                WHERE status IN ('completed','failed')
                  AND created_at < $1
                """,
                cutoff_dt,
            )
            try:
                return int(result.split()[-1])
            except Exception:
                return 0
        except Exception as e:
            logger.warning(
                f"Failed to delete old recovery_queue entries before {cutoff_iso}: {e}"
            )
            return 0

    async def cleanup_old_checkpoints(self, cutoff_iso: str) -> None:
        try:
            cutoff_dt = _ensure_datetime(cutoff_iso)
            await execute_raw_sql(
                """
                DELETE FROM task_checkpoints 
                WHERE task_registry_id NOT IN (
                    SELECT id FROM task_registry 
                    WHERE current_state NOT IN ('completed', 'failed')
                ) 
                AND created_at < $1
                """,
                cutoff_dt,
            )
        except Exception as e:
            logger.warning(
                f"Failed to cleanup old checkpoints before {cutoff_iso}: {e}"
            )


def _ensure_datetime(value: Union[str, datetime, date]) -> datetime:
    """Coerce an ISO string/date/datetime into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        # Normalize trailing Z to +00:00 for fromisoformat
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError(f"Unsupported datetime value type: {type(value)}")

    # Ensure tz-aware; assume UTC if naive
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
