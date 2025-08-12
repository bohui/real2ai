"""
Recovery Orchestrator - Manages task recovery on container startup
Discovers interrupted tasks, validates their state, and executes recovery strategies.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.core.auth_context import AuthContext
from app.clients.factory import get_service_supabase_client
from app.services.repositories.recovery_repository import RecoveryRepository
from app.core.task_recovery import TaskState, RecoveryMethod, RecoverableTask
from app.core.celery import celery_app
from app.tasks import background_tasks
from app.services.repositories.analyses_repository import AnalysesRepository

logger = logging.getLogger(__name__)


@dataclass
class RecoveryResult:
    """Result of a recovery operation"""

    success: bool
    strategy: str
    message: str
    celery_task_id: str = None
    resumed_from: str = None
    estimated_time_saved: int = 0
    error: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy,
            "message": self.message,
            "celery_task_id": self.celery_task_id,
            "resumed_from": self.resumed_from,
            "estimated_time_saved": self.estimated_time_saved,
            "error": self.error,
        }


@dataclass
class RecoveryResults:
    """Aggregated recovery results"""

    discovered_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    total_time_saved: int = 0
    results: List[RecoveryResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    def add_success(self, task_id: str, result: RecoveryResult):
        self.success_count += 1
        self.total_time_saved += result.estimated_time_saved
        self.results.append(result)

    def add_failure(self, task_id: str, error: str):
        self.failure_count += 1
        self.results.append(
            RecoveryResult(
                success=False,
                strategy="failed",
                message=f"Recovery failed for {task_id}",
                error=error,
            )
        )

    def add_skip(self, task_id: str, reason: str):
        self.skipped_count += 1
        self.results.append(
            RecoveryResult(
                success=True, strategy="skipped", message=f"Skipped {task_id}: {reason}"
            )
        )

    @property
    def summary(self) -> str:
        return (
            f"Recovery completed: {self.discovered_count} discovered, "
            f"{self.success_count} recovered, {self.failure_count} failed, "
            f"{self.skipped_count} skipped, {self.total_time_saved}s saved"
        )


class RecoveryStrategy(ABC):
    """Base class for recovery strategies"""

    @abstractmethod
    async def recover_task(self, task: RecoverableTask) -> RecoveryResult:
        """Execute recovery strategy for task"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name"""
        pass


class CheckpointResumeStrategy(RecoveryStrategy):
    """Resume task from last valid checkpoint"""

    def get_strategy_name(self) -> str:
        return "checkpoint_resume"

    async def recover_task(self, task: RecoverableTask) -> RecoveryResult:
        """Resume from last checkpoint"""
        try:
            # Get latest checkpoint
            client = await get_service_supabase_client()
            checkpoint_result = await client.execute_rpc(
                "get_latest_checkpoint", {"p_task_id": task.task_id}
            )

            if not checkpoint_result:
                raise Exception("No valid checkpoint found")

            checkpoint = checkpoint_result[0]

            # Restore task context and submit to Celery
            new_task_id = await self._submit_recovered_task(task, checkpoint)

            estimated_time_saved = self._calculate_time_saved(
                checkpoint["progress_percent"]
            )

            return RecoveryResult(
                success=True,
                strategy=self.get_strategy_name(),
                message=f"Resumed from checkpoint: {checkpoint['checkpoint_name']}",
                celery_task_id=new_task_id,
                resumed_from=checkpoint["checkpoint_name"],
                estimated_time_saved=estimated_time_saved,
            )

        except Exception as e:
            logger.error(f"Checkpoint resume failed for task {task.task_id}: {e}")
            return RecoveryResult(
                success=False,
                strategy=self.get_strategy_name(),
                message="Checkpoint resume failed",
                error=str(e),
            )

    async def _submit_recovered_task(
        self, task: RecoverableTask, checkpoint: Dict
    ) -> str:
        """Submit recovered task to Celery"""

        # Get the task function
        task_func = self._get_task_function(task.task_name)
        if not task_func:
            raise Exception(f"Task function not found: {task.task_name}")

        # Modify kwargs to include recovery information
        recovery_kwargs = task.task_kwargs.copy()
        recovery_kwargs["_is_recovery"] = True
        recovery_kwargs["_recovery_checkpoint"] = {
            "checkpoint_name": checkpoint["checkpoint_name"],
            "progress_percent": checkpoint["progress_percent"],
            "recoverable_data": (
                json.loads(checkpoint["recoverable_data"])
                if checkpoint["recoverable_data"]
                else {}
            ),
            "database_state": (
                json.loads(checkpoint["database_state"])
                if checkpoint["database_state"]
                else {}
            ),
            "file_state": (
                json.loads(checkpoint["file_state"]) if checkpoint["file_state"] else {}
            ),
        }

        # Submit to Celery
        result = task_func.delay(task.context_key, *task.task_args, **recovery_kwargs)

        return result.id

    def _get_task_function(self, task_name: str):
        """Get Celery task function by name"""
        task_map = {
            "comprehensive_document_analysis": background_tasks.comprehensive_document_analysis,
            # "process_document_background": background_tasks.process_document_background,
            # "analyze_contract_background": background_tasks.analyze_contract_background,
        }
        return task_map.get(task_name)

    def _calculate_time_saved(self, progress_percent: int) -> int:
        """Estimate time saved by resuming from checkpoint"""
        # Rough estimation: assume linear progress and 30-minute total task time
        base_time_minutes = 30
        saved_percent = progress_percent / 100.0
        return int(base_time_minutes * saved_percent * 60)  # Return seconds


class CleanRestartStrategy(RecoveryStrategy):
    """Restart task cleanly but skip completed work"""

    def get_strategy_name(self) -> str:
        return "clean_restart"

    async def recover_task(self, task: RecoverableTask) -> RecoveryResult:
        """Restart task cleanly"""
        try:
            # Analyze completed work
            completed_work = await self._analyze_completed_work(task)

            # Create modified args that skip completed work
            modified_kwargs = await self._create_skip_completed_args(
                task.task_kwargs, completed_work
            )

            # Submit new task
            new_task_id = await self._submit_clean_restart(task, modified_kwargs)

            return RecoveryResult(
                success=True,
                strategy=self.get_strategy_name(),
                message="Restarted cleanly with skip flags",
                celery_task_id=new_task_id,
                estimated_time_saved=completed_work.get("estimated_time_saved", 0),
            )

        except Exception as e:
            logger.error(f"Clean restart failed for task {task.task_id}: {e}")
            return RecoveryResult(
                success=False,
                strategy=self.get_strategy_name(),
                message="Clean restart failed",
                error=str(e),
            )

    async def _analyze_completed_work(self, task: RecoverableTask) -> Dict[str, Any]:
        """Analyze what work was already completed"""
        completed_work = {
            "documents_processed": [],
            "analyses_completed": [],
            "estimated_time_saved": 0,
        }

        try:
            # For comprehensive_document_analysis tasks
            if task.task_name == "comprehensive_document_analysis":
                # Check if document processing was completed
                analysis_options = task.task_kwargs.get("analysis_options", {})
                content_hash = analysis_options.get("content_hash")

                if content_hash:
                    # Check analysis progress via repository
                    repo = RecoveryRepository()
                    progress = await repo.get_analysis_progress_by_content_hash(
                        content_hash
                    )

                    if progress and progress.get("progress_percent", 0) >= 75:
                        completed_work["documents_processed"].append(content_hash)
                        completed_work["estimated_time_saved"] = 600  # 10 minutes

        except Exception as e:
            logger.warning(f"Failed to analyze completed work for {task.task_id}: {e}")

        return completed_work

    async def _create_skip_completed_args(
        self, kwargs: Dict, completed_work: Dict
    ) -> Dict:
        """Create modified arguments that skip completed work"""
        modified_kwargs = kwargs.copy()

        # Add skip flags based on completed work
        if completed_work["documents_processed"]:
            modified_kwargs["_skip_document_processing"] = True
            modified_kwargs["_completed_documents"] = completed_work[
                "documents_processed"
            ]

        if completed_work["analyses_completed"]:
            modified_kwargs["_skip_analysis"] = True
            modified_kwargs["_completed_analyses"] = completed_work[
                "analyses_completed"
            ]

        return modified_kwargs

    async def _submit_clean_restart(
        self, task: RecoverableTask, modified_kwargs: Dict
    ) -> str:
        """Submit clean restart task"""
        strategy = CheckpointResumeStrategy()
        task_func = strategy._get_task_function(task.task_name)

        if not task_func:
            raise Exception(f"Task function not found: {task.task_name}")

        result = task_func.delay(task.context_key, *task.task_args, **modified_kwargs)
        return result.id


class ValidationOnlyStrategy(RecoveryStrategy):
    """Validate if task actually completed successfully"""

    def get_strategy_name(self) -> str:
        return "validation_only"

    async def recover_task(self, task: RecoverableTask) -> RecoveryResult:
        """Validate task completion status"""
        try:
            validation_result = await self._validate_completion(task)

            if validation_result["is_complete"]:
                # Mark as completed in registry
                await self._mark_task_completed(task, validation_result["result_data"])

                return RecoveryResult(
                    success=True,
                    strategy=self.get_strategy_name(),
                    message="Task was already completed",
                    estimated_time_saved=validation_result.get(
                        "estimated_time_saved", 0
                    ),
                )
            else:
                # Task needs proper recovery
                return RecoveryResult(
                    success=False,
                    strategy=self.get_strategy_name(),
                    message="Task validation failed - needs full recovery",
                    error="Incomplete task state",
                )

        except Exception as e:
            logger.error(f"Validation failed for task {task.task_id}: {e}")
            return RecoveryResult(
                success=False,
                strategy=self.get_strategy_name(),
                message="Validation failed",
                error=str(e),
            )

    async def _validate_completion(self, task: RecoverableTask) -> Dict[str, Any]:
        """Check if task actually completed"""
        try:
            client = await get_service_supabase_client()

            if task.task_name == "comprehensive_document_analysis":
                # Check if analysis completed via content_hash using repository
                analysis_options = task.task_kwargs.get("analysis_options", {})
                content_hash = analysis_options.get("content_hash")

                if content_hash:
                    analyses_repo = AnalysesRepository(use_service_role=True)
                    analysis = await analyses_repo.get_analysis_by_content_hash(
                        content_hash, status="completed"
                    )

                    if analysis:
                        return {
                            "is_complete": True,
                            "result_data": {
                                "id": str(analysis.id),
                                "content_hash": analysis.content_hash,
                                "status": analysis.status,
                                "result": analysis.result,
                                "created_at": (
                                    analysis.created_at.isoformat()
                                    if analysis.created_at
                                    else None
                                ),
                            },
                            "estimated_time_saved": 1800,  # 30 minutes
                        }

            return {"is_complete": False}

        except Exception as e:
            logger.error(f"Failed to validate completion for {task.task_id}: {e}")
            return {"is_complete": False}

    async def _mark_task_completed(self, task: RecoverableTask, result_data: Dict):
        """Mark task as completed in registry"""
        client = await get_service_supabase_client()

        await client.execute_rpc(
            "update_task_registry_state",
            {
                "p_task_id": task.task_id,
                "p_new_state": TaskState.COMPLETED.value,
                "p_progress_percent": 100,
                "p_result_data": json.dumps(result_data),
            },
        )


class RecoveryOrchestrator:
    """Main orchestrator for task recovery operations"""

    def __init__(self):
        self.strategies = {
            RecoveryMethod.RESUME_CHECKPOINT: CheckpointResumeStrategy(),
            RecoveryMethod.RESTART_CLEAN: CleanRestartStrategy(),
            RecoveryMethod.VALIDATE_ONLY: ValidationOnlyStrategy(),
        }

    async def startup_recovery_sequence(self) -> RecoveryResults:
        """Execute complete recovery sequence on container startup"""
        logger.info("Starting recovery sequence...")

        try:
            # Phase 1: System health check
            await self._validate_system_health()

            # Phase 2: Discover recoverable tasks
            recoverable_tasks = await self._discover_recoverable_tasks()
            logger.info(
                f"Discovered {len(recoverable_tasks)} potentially recoverable tasks"
            )

            # Phase 3: Validate and plan recovery
            validated_tasks = await self._validate_and_plan_recovery(recoverable_tasks)
            logger.info(f"Validated {len(validated_tasks)} tasks for recovery")

            # Phase 4: Execute recovery
            results = await self._execute_recovery_plan(validated_tasks)

            logger.info(f"Recovery sequence completed: {results.summary}")
            return results

        except Exception as e:
            logger.error(f"Recovery sequence failed: {e}")
            return RecoveryResults()

    async def _validate_system_health(self):
        """Validate system health before recovery"""
        # Check database connectivity
        try:
            repo = RecoveryRepository()
            ok = await repo.verify_database_connectivity()
            if not ok:
                raise Exception("Database connectivity check returned False")
            logger.info("Database connectivity verified")
        except Exception as e:
            raise Exception(f"Database connectivity check failed: {e}")

        # Check Celery broker connectivity
        try:
            celery_inspect = celery_app.control.inspect()
            active_tasks = celery_inspect.active()
            logger.info("Celery broker connectivity verified")
        except Exception as e:
            logger.warning(f"Celery broker check failed: {e}")

    async def _discover_recoverable_tasks(self) -> List[RecoverableTask]:
        """Discover tasks that need recovery"""
        try:
            client = await get_service_supabase_client()
            result = await client.execute_rpc("discover_recoverable_tasks")

            recoverable_tasks = []
            for row in result:
                task = RecoverableTask(
                    registry_id=row["registry_id"],
                    task_id=row["task_id"],
                    task_name=row["task_name"],
                    user_id=row["user_id"],
                    current_state=TaskState(row["current_state"]),
                    last_heartbeat=row["last_heartbeat"],
                    recovery_priority=row["recovery_priority"],
                    progress_percent=row["progress_percent"] or 0,
                    current_step=row["current_step"] or "",
                    task_args=(),  # Will be loaded separately if needed
                    task_kwargs={},  # Will be loaded separately if needed
                )
                recoverable_tasks.append(task)

            return recoverable_tasks

        except Exception as e:
            logger.error(f"Failed to discover recoverable tasks: {e}")
            return []

    async def _validate_and_plan_recovery(
        self, tasks: List[RecoverableTask]
    ) -> List[tuple]:
        """Validate tasks and determine recovery strategies"""
        validated_plans = []

        for task in tasks:
            try:
                # Validate task can be recovered
                client = await get_service_supabase_client()
                validation = await client.execute_rpc(
                    "validate_task_recovery", {"task_registry_uuid": task.registry_id}
                )

                validation_data = validation[0] if validation else {"valid": False}

                if validation_data.get("valid", False):
                    # Determine recovery strategy
                    strategy = await self._determine_recovery_strategy(task)
                    validated_plans.append((task, strategy))

                    logger.info(
                        f"Task {task.task_id} validated for recovery with {strategy.get_strategy_name()}"
                    )
                else:
                    reason = validation_data.get("reason", "validation_failed")
                    logger.info(f"Task {task.task_id} skipped: {reason}")

            except Exception as e:
                logger.error(f"Failed to validate task {task.task_id}: {e}")

        return validated_plans

    async def _determine_recovery_strategy(
        self, task: RecoverableTask
    ) -> RecoveryStrategy:
        """Determine best recovery strategy for task"""

        # First check if task might be already completed
        if task.progress_percent >= 95:
            return self.strategies[RecoveryMethod.VALIDATE_ONLY]

        # Check if we have valid checkpoints
        try:
            client = await get_service_supabase_client()
            checkpoint_result = await client.execute_rpc(
                "get_latest_checkpoint", {"p_task_id": task.task_id}
            )

            if checkpoint_result and task.progress_percent >= 25:
                # Has checkpoint and significant progress
                return self.strategies[RecoveryMethod.RESUME_CHECKPOINT]

        except Exception as e:
            logger.warning(f"Failed to check checkpoints for {task.task_id}: {e}")

        # Default to clean restart
        return self.strategies[RecoveryMethod.RESTART_CLEAN]

    async def _execute_recovery_plan(
        self, validated_plans: List[tuple]
    ) -> RecoveryResults:
        """Execute recovery for all validated tasks"""
        results = RecoveryResults()
        results.discovered_count = len(validated_plans)

        # Sort by priority
        validated_plans.sort(key=lambda x: x[0].recovery_priority, reverse=True)

        # Process in small batches to avoid overwhelming system
        batch_size = 3
        for i in range(0, len(validated_plans), batch_size):
            batch = validated_plans[i : i + batch_size]

            # Execute batch concurrently
            tasks = [
                self._recover_single_task(task, strategy) for task, strategy in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for j, result in enumerate(batch_results):
                task, strategy = batch[j]

                if isinstance(result, Exception):
                    results.add_failure(task.task_id, str(result))
                    logger.error(f"Recovery failed for {task.task_id}: {result}")
                elif result.success:
                    results.add_success(task.task_id, result)
                    logger.info(
                        f"Recovery succeeded for {task.task_id}: {result.message}"
                    )
                else:
                    results.add_failure(task.task_id, result.error or "Unknown error")
                    logger.error(
                        f"Recovery failed for {task.task_id}: {result.message}"
                    )

            # Small delay between batches
            if i + batch_size < len(validated_plans):
                await asyncio.sleep(2)

        return results

    async def _recover_single_task(
        self, task: RecoverableTask, strategy: RecoveryStrategy
    ) -> RecoveryResult:
        """Recover a single task using specified strategy"""
        try:
            # Load full task data
            task = await self._load_full_task_data(task)

            # Execute recovery strategy
            result = await strategy.recover_task(task)

            # Update recovery queue if this was queued
            if result.success:
                await self._update_recovery_queue_success(task, result)
            else:
                await self._update_recovery_queue_failure(task, result.error)

            return result

        except Exception as e:
            logger.error(f"Single task recovery failed for {task.task_id}: {e}")
            await self._update_recovery_queue_failure(task, str(e))
            raise

    async def _load_full_task_data(self, task: RecoverableTask) -> RecoverableTask:
        """Load full task data including args and kwargs"""
        try:
            repo = RecoveryRepository()
            row = await repo.get_task_registry_row(task.registry_id)

            if row:
                task.task_args = tuple(
                    json.loads(row["task_args"]) if row["task_args"] else []
                )
                task.task_kwargs = (
                    json.loads(row["task_kwargs"]) if row["task_kwargs"] else {}
                )
                task.context_key = row["context_key"]

            return task

        except Exception as e:
            logger.error(f"Failed to load full task data for {task.task_id}: {e}")
            return task

    async def _update_recovery_queue_success(
        self, task: RecoverableTask, result: RecoveryResult
    ):
        """Update recovery queue on successful recovery"""
        # Implementation would update recovery_queue table
        pass

    async def _update_recovery_queue_failure(self, task: RecoverableTask, error: str):
        """Update recovery queue on failed recovery"""
        # Implementation would update recovery_queue table
        pass


# Global orchestrator instance
recovery_orchestrator = RecoveryOrchestrator()
