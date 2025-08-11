"""
Repository for document processing runs and steps tracking
"""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncpg

from app.database.connection import get_user_connection


class RunStatus(str, Enum):
    """Processing run status"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Processing step status"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingRun:
    """Processing run model"""
    run_id: UUID
    document_id: UUID
    user_id: UUID
    status: RunStatus
    last_step: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ProcessingStep:
    """Processing step model"""
    run_id: UUID
    step_name: str
    status: StepStatus
    state_snapshot: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunsRepository:
    """Repository for processing runs and steps tracking"""

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        self._connection = None

    async def _get_connection(self) -> asyncpg.Connection:
        """Get user database connection"""
        if self._connection is None:
            self._connection = await get_user_connection(self.user_id)
        return self._connection

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    # ================================
    # PROCESSING RUNS
    # ================================

    async def create_run(
        self,
        document_id: UUID,
        run_id: Optional[UUID] = None,
        status: RunStatus = RunStatus.QUEUED
    ) -> ProcessingRun:
        """
        Create a new processing run.
        
        Args:
            document_id: Document ID
            run_id: Optional run ID (generates if not provided)
            status: Initial status
            
        Returns:
            ProcessingRun
        """
        if run_id is None:
            run_id = uuid4()
            
        conn = await self._get_connection()
        
        row = await conn.fetchrow(
            """
            INSERT INTO document_processing_runs (
                run_id, document_id, user_id, status
            ) VALUES ($1, $2, $3, $4)
            RETURNING run_id, document_id, user_id, status, last_step,
                      error, created_at, updated_at
            """,
            run_id, document_id, self.user_id, status.value
        )
        
        return ProcessingRun(
            run_id=row['run_id'],
            document_id=row['document_id'],
            user_id=row['user_id'],
            status=RunStatus(row['status']),
            last_step=row['last_step'],
            error=row['error'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    async def get_run(self, run_id: UUID) -> Optional[ProcessingRun]:
        """Get processing run by ID."""
        conn = await self._get_connection()
        
        row = await conn.fetchrow(
            """
            SELECT run_id, document_id, user_id, status, last_step,
                   error, created_at, updated_at
            FROM document_processing_runs
            WHERE run_id = $1 AND user_id = $2
            """,
            run_id, self.user_id
        )
        
        if row is None:
            return None
            
        return ProcessingRun(
            run_id=row['run_id'],
            document_id=row['document_id'],
            user_id=row['user_id'],
            status=RunStatus(row['status']),
            last_step=row['last_step'],
            error=row['error'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    async def get_document_runs(
        self,
        document_id: UUID,
        limit: int = 10
    ) -> List[ProcessingRun]:
        """Get processing runs for a document."""
        conn = await self._get_connection()
        
        rows = await conn.fetch(
            """
            SELECT run_id, document_id, user_id, status, last_step,
                   error, created_at, updated_at
            FROM document_processing_runs
            WHERE document_id = $1 AND user_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            document_id, self.user_id, limit
        )
        
        return [
            ProcessingRun(
                run_id=row['run_id'],
                document_id=row['document_id'],
                user_id=row['user_id'],
                status=RunStatus(row['status']),
                last_step=row['last_step'],
                error=row['error'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]

    async def update_run_status(
        self,
        run_id: UUID,
        status: RunStatus,
        last_step: Optional[str] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update processing run status.
        
        Args:
            run_id: Run ID
            status: New status
            last_step: Last completed step
            error: Error information (if failed)
            
        Returns:
            True if update successful, False otherwise
        """
        conn = await self._get_connection()
        
        result = await conn.execute(
            """
            UPDATE document_processing_runs 
            SET status = $1,
                last_step = COALESCE($2, last_step),
                error = $3,
                updated_at = now()
            WHERE run_id = $4 AND user_id = $5
            """,
            status.value, last_step, error, run_id, self.user_id
        )
        
        return result.split()[-1] == '1'

    async def mark_run_completed(self, run_id: UUID) -> bool:
        """Mark processing run as completed."""
        return await self.update_run_status(run_id, RunStatus.COMPLETED)

    async def mark_run_failed(
        self,
        run_id: UUID,
        error: Dict[str, Any],
        last_step: Optional[str] = None
    ) -> bool:
        """Mark processing run as failed with error."""
        return await self.update_run_status(
            run_id, RunStatus.FAILED, last_step, error
        )

    # ================================
    # PROCESSING STEPS
    # ================================

    async def upsert_step_status(
        self,
        run_id: UUID,
        step_name: str,
        status: StepStatus,
        state_snapshot: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None
    ) -> ProcessingStep:
        """
        Upsert processing step status.
        
        Args:
            run_id: Run ID
            step_name: Step name
            status: Step status
            state_snapshot: Optional state snapshot (keep minimal)
            error: Error information (if failed)
            completed_at: Completion timestamp (auto-set if None and status is SUCCESS/FAILED)
            
        Returns:
            ProcessingStep
        """
        conn = await self._get_connection()
        
        # Auto-set completed_at for terminal states
        if completed_at is None and status in (StepStatus.SUCCESS, StepStatus.FAILED):
            completed_at = datetime.utcnow()
        
        row = await conn.fetchrow(
            """
            INSERT INTO document_processing_steps (
                run_id, step_name, status, state_snapshot, error, completed_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (run_id, step_name) DO UPDATE SET
                status = EXCLUDED.status,
                state_snapshot = COALESCE(EXCLUDED.state_snapshot, document_processing_steps.state_snapshot),
                error = EXCLUDED.error,
                completed_at = COALESCE(EXCLUDED.completed_at, document_processing_steps.completed_at)
            RETURNING run_id, step_name, status, state_snapshot, error,
                      started_at, completed_at
            """,
            run_id, step_name, status.value, state_snapshot, error, completed_at
        )
        
        return ProcessingStep(
            run_id=row['run_id'],
            step_name=row['step_name'],
            status=StepStatus(row['status']),
            state_snapshot=row['state_snapshot'],
            error=row['error'],
            started_at=row['started_at'],
            completed_at=row['completed_at']
        )

    async def mark_step_started(
        self,
        run_id: UUID,
        step_name: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark processing step as started."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.STARTED, state_snapshot
        )

    async def mark_step_success(
        self,
        run_id: UUID,
        step_name: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark processing step as successful."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.SUCCESS, state_snapshot
        )

    async def mark_step_failed(
        self,
        run_id: UUID,
        step_name: str,
        error: Dict[str, Any],
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark processing step as failed."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.FAILED, state_snapshot, error
        )

    async def mark_step_skipped(
        self,
        run_id: UUID,
        step_name: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark processing step as skipped."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.SKIPPED, state_snapshot
        )

    async def get_run_steps(self, run_id: UUID) -> List[ProcessingStep]:
        """Get all steps for a processing run."""
        conn = await self._get_connection()
        
        rows = await conn.fetch(
            """
            SELECT s.run_id, s.step_name, s.status, s.state_snapshot, s.error,
                   s.started_at, s.completed_at
            FROM document_processing_steps s
            JOIN document_processing_runs r ON s.run_id = r.run_id
            WHERE s.run_id = $1 AND r.user_id = $2
            ORDER BY s.started_at
            """,
            run_id, self.user_id
        )
        
        return [
            ProcessingStep(
                run_id=row['run_id'],
                step_name=row['step_name'],
                status=StepStatus(row['status']),
                state_snapshot=row['state_snapshot'],
                error=row['error'],
                started_at=row['started_at'],
                completed_at=row['completed_at']
            )
            for row in rows
        ]

    async def get_step(self, run_id: UUID, step_name: str) -> Optional[ProcessingStep]:
        """Get specific processing step."""
        conn = await self._get_connection()
        
        row = await conn.fetchrow(
            """
            SELECT s.run_id, s.step_name, s.status, s.state_snapshot, s.error,
                   s.started_at, s.completed_at
            FROM document_processing_steps s
            JOIN document_processing_runs r ON s.run_id = r.run_id
            WHERE s.run_id = $1 AND s.step_name = $2 AND r.user_id = $3
            """,
            run_id, step_name, self.user_id
        )
        
        if row is None:
            return None
            
        return ProcessingStep(
            run_id=row['run_id'],
            step_name=row['step_name'],
            status=StepStatus(row['status']),
            state_snapshot=row['state_snapshot'],
            error=row['error'],
            started_at=row['started_at'],
            completed_at=row['completed_at']
        )

    # ================================
    # UTILITY METHODS
    # ================================

    async def get_last_successful_run(self, document_id: UUID) -> Optional[ProcessingRun]:
        """Get last successful processing run for a document."""
        conn = await self._get_connection()
        
        row = await conn.fetchrow(
            """
            SELECT run_id, document_id, user_id, status, last_step,
                   error, created_at, updated_at
            FROM document_processing_runs
            WHERE document_id = $1 AND user_id = $2 AND status = $3
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            document_id, self.user_id, RunStatus.COMPLETED.value
        )
        
        if row is None:
            return None
            
        return ProcessingRun(
            run_id=row['run_id'],
            document_id=row['document_id'],
            user_id=row['user_id'],
            status=RunStatus(row['status']),
            last_step=row['last_step'],
            error=row['error'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    async def get_run_progress(self, run_id: UUID) -> Dict[str, Any]:
        """
        Get processing run progress summary.
        
        Args:
            run_id: Run ID
            
        Returns:
            Dictionary with run status and step progress
        """
        conn = await self._get_connection()
        
        # Get run info
        run = await self.get_run(run_id)
        if run is None:
            return {"error": "Run not found"}
        
        # Get step summary
        step_summary = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_steps,
                COUNT(*) FILTER (WHERE status = 'success') as completed_steps,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_steps,
                COUNT(*) FILTER (WHERE status = 'started') as running_steps,
                COUNT(*) FILTER (WHERE status = 'skipped') as skipped_steps
            FROM document_processing_steps s
            JOIN document_processing_runs r ON s.run_id = r.run_id
            WHERE s.run_id = $1 AND r.user_id = $2
            """,
            run_id, self.user_id
        )
        
        return {
            "run_id": str(run.run_id),
            "document_id": str(run.document_id),
            "status": run.status.value,
            "last_step": run.last_step,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
            "error": run.error,
            "steps": {
                "total": step_summary['total_steps'],
                "completed": step_summary['completed_steps'],
                "failed": step_summary['failed_steps'],
                "running": step_summary['running_steps'],
                "skipped": step_summary['skipped_steps']
            }
        }

    async def cleanup_old_runs(
        self,
        document_id: UUID,
        keep_count: int = 5
    ) -> int:
        """
        Clean up old processing runs, keeping the most recent N runs.
        
        Args:
            document_id: Document ID
            keep_count: Number of recent runs to keep
            
        Returns:
            Number of runs deleted
        """
        conn = await self._get_connection()
        
        result = await conn.execute(
            """
            DELETE FROM document_processing_runs
            WHERE document_id = $1 AND user_id = $2 AND run_id NOT IN (
                SELECT run_id FROM document_processing_runs
                WHERE document_id = $1 AND user_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            )
            """,
            document_id, self.user_id, keep_count
        )
        
        return int(result.split()[-1])