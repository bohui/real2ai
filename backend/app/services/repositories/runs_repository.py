"""
Repository for document processing runs and steps tracking (FIXED VERSION)

This version properly uses context managers for connection management
instead of storing connections, preventing pool misuse.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime, timedelta
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
    """
    Repository for processing runs and steps tracking.
    
    FIXED: Now uses proper context managers for all database operations
    instead of storing connections. This ensures connections are properly
    released back to the pool instead of being closed.
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize runs repository.
        
        Args:
            user_id: Optional user ID (uses auth context if not provided)
        """
        self.user_id = user_id
        # No stored connection! Each method uses its own context manager

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
        
        # Use context manager for proper connection management
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO document_processing_runs (
                    run_id, document_id, user_id, status
                ) VALUES ($1, $2, $3, $4)
                RETURNING run_id, document_id, user_id, status, last_step,
                          error, created_at, updated_at
                """,
                run_id, document_id, 
                self.user_id or "(current_setting('request.jwt.claim.sub'))::uuid",
                status.value
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
        """
        Get processing run by ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            ProcessingRun or None
        """
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT run_id, document_id, user_id, status, last_step,
                       error, created_at, updated_at
                FROM document_processing_runs
                WHERE run_id = $1
                """,
                run_id
            )
            
            if not row:
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
        """
        Get all runs for a document.
        
        Args:
            document_id: Document ID
            limit: Maximum number of runs to return
            
        Returns:
            List of ProcessingRun
        """
        async with get_user_connection(self.user_id) as conn:
            rows = await conn.fetch(
                """
                SELECT run_id, document_id, user_id, status, last_step,
                       error, created_at, updated_at
                FROM document_processing_runs
                WHERE document_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                document_id, limit
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
        Update run status and optionally last step.
        
        Args:
            run_id: Run ID
            status: New status
            last_step: Optional last step name
            error: Optional error details
            
        Returns:
            True if update successful
        """
        async with get_user_connection(self.user_id) as conn:
            # Build dynamic query
            set_clauses = ["status = $1", "updated_at = now()"]
            params = [status.value]
            param_count = 1
            
            if last_step is not None:
                param_count += 1
                set_clauses.append(f"last_step = ${param_count}")
                params.append(last_step)
                
            if error is not None:
                param_count += 1
                set_clauses.append(f"error = ${param_count}")
                params.append(error)
            
            param_count += 1
            params.append(run_id)
            
            query = f"""
                UPDATE document_processing_runs 
                SET {', '.join(set_clauses)}
                WHERE run_id = ${param_count}
            """
            
            result = await conn.execute(query, *params)
            return result.split()[-1] == '1'

    async def mark_run_completed(self, run_id: UUID) -> bool:
        """Mark run as completed."""
        return await self.update_run_status(run_id, RunStatus.COMPLETED)

    async def mark_run_failed(
        self,
        run_id: UUID,
        error: Dict[str, Any]
    ) -> bool:
        """Mark run as failed with error details."""
        return await self.update_run_status(
            run_id, 
            RunStatus.FAILED,
            error=error
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
        error: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """
        Upsert processing step status.
        
        Args:
            run_id: Run ID
            step_name: Step name
            status: Step status
            state_snapshot: Optional state snapshot
            error: Optional error details
            
        Returns:
            ProcessingStep
        """
        async with get_user_connection(self.user_id) as conn:
            # Set timestamps based on status
            started_at = datetime.utcnow() if status == StepStatus.STARTED else None
            completed_at = datetime.utcnow() if status in [StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED] else None
            
            row = await conn.fetchrow(
                """
                INSERT INTO document_processing_steps (
                    run_id, step_name, status, state_snapshot, error,
                    started_at, completed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (run_id, step_name) DO UPDATE SET
                    status = EXCLUDED.status,
                    state_snapshot = COALESCE(EXCLUDED.state_snapshot, document_processing_steps.state_snapshot),
                    error = COALESCE(EXCLUDED.error, document_processing_steps.error),
                    started_at = COALESCE(document_processing_steps.started_at, EXCLUDED.started_at),
                    completed_at = COALESCE(EXCLUDED.completed_at, document_processing_steps.completed_at)
                RETURNING run_id, step_name, status, state_snapshot, error,
                          started_at, completed_at
                """,
                run_id, step_name, status.value, state_snapshot, error,
                started_at, completed_at
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
        """Mark step as started."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.STARTED, state_snapshot
        )

    async def mark_step_success(
        self,
        run_id: UUID,
        step_name: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark step as successful."""
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
        """Mark step as failed."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.FAILED, state_snapshot, error
        )

    async def mark_step_skipped(
        self,
        run_id: UUID,
        step_name: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> ProcessingStep:
        """Mark step as skipped."""
        return await self.upsert_step_status(
            run_id, step_name, StepStatus.SKIPPED, state_snapshot
        )

    async def get_run_steps(self, run_id: UUID) -> List[ProcessingStep]:
        """
        Get all steps for a run.
        
        Args:
            run_id: Run ID
            
        Returns:
            List of ProcessingStep
        """
        async with get_user_connection(self.user_id) as conn:
            rows = await conn.fetch(
                """
                SELECT run_id, step_name, status, state_snapshot, error,
                       started_at, completed_at
                FROM document_processing_steps
                WHERE run_id = $1
                ORDER BY started_at
                """,
                run_id
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
        """
        Get specific step for a run.
        
        Args:
            run_id: Run ID
            step_name: Step name
            
        Returns:
            ProcessingStep or None
        """
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT run_id, step_name, status, state_snapshot, error,
                       started_at, completed_at
                FROM document_processing_steps
                WHERE run_id = $1 AND step_name = $2
                """,
                run_id, step_name
            )
            
            if not row:
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
        """
        Get the last successful run for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            ProcessingRun or None
        """
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT run_id, document_id, user_id, status, last_step,
                       error, created_at, updated_at
                FROM document_processing_runs
                WHERE document_id = $1 AND status = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                document_id, RunStatus.COMPLETED.value
            )
            
            if not row:
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
        Get run progress summary.
        
        Args:
            run_id: Run ID
            
        Returns:
            Progress summary dict
        """
        async with get_user_connection(self.user_id) as conn:
            # Get run status
            run = await self.get_run(run_id)
            if not run:
                return {
                    'run_id': run_id,
                    'status': 'not_found',
                    'total_steps': 0,
                    'completed_steps': 0,
                    'progress_percent': 0
                }
            
            # Get steps summary (need to re-acquire connection)
            async with get_user_connection(self.user_id) as conn2:
                step_summary = await conn2.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_steps,
                        COUNT(*) FILTER (WHERE status IN ('success', 'skipped')) as completed_steps,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed_steps
                    FROM document_processing_steps
                    WHERE run_id = $1
                    """,
                    run_id
                )
            
            total = step_summary['total_steps'] or 0
            completed = step_summary['completed_steps'] or 0
            failed = step_summary['failed_steps'] or 0
            
            return {
                'run_id': run_id,
                'status': run.status.value,
                'total_steps': total,
                'completed_steps': completed,
                'failed_steps': failed,
                'progress_percent': (completed / total * 100) if total > 0 else 0,
                'last_step': run.last_step,
                'error': run.error
            }

    async def cleanup_old_runs(
        self,
        document_id: UUID,
        keep_count: int = 5,
        older_than_days: int = 30
    ) -> int:
        """
        Clean up old runs for a document.
        
        Args:
            document_id: Document ID
            keep_count: Number of recent runs to keep
            older_than_days: Delete runs older than this many days
            
        Returns:
            Number of runs deleted
        """
        async with get_user_connection(self.user_id) as conn:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            # Delete old runs, keeping the most recent ones
            result = await conn.execute(
                """
                DELETE FROM document_processing_runs
                WHERE document_id = $1
                AND created_at < $2
                AND run_id NOT IN (
                    SELECT run_id
                    FROM document_processing_runs
                    WHERE document_id = $1
                    ORDER BY created_at DESC
                    LIMIT $3
                )
                """,
                document_id, cutoff_date, keep_count
            )
            
            deleted_count = int(result.split()[-1])
            return deleted_count