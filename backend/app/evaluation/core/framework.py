"""
Core LLM Evaluation Framework

Provides the main orchestration engine for running evaluations, managing test cases,
and coordinating between different evaluation components.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4, UUID

from ..models.evaluation import (
    EvaluationRun,
    EvaluationConfig,
    TestCase,
    EvaluationResult,
    MetricResult,
    ModelResponse,
    EvaluationStatus
)
from ..models.metrics import BaseMetric, MetricType
from ..clients.evaluation_client import EvaluationClient
from .evaluation_storage import EvaluationStorage
from ..metrics.registry import MetricRegistry
from ...core.langsmith_config import langsmith_trace, langsmith_session

logger = logging.getLogger(__name__)


class EvaluationMode(Enum):
    """Evaluation execution modes."""
    SEQUENTIAL = "sequential"  # Run test cases one by one
    PARALLEL = "parallel"     # Run test cases in parallel
    BATCH = "batch"           # Run in optimized batches


@dataclass
class EvaluationContext:
    """Context information for an evaluation run."""
    run_id: UUID
    config: EvaluationConfig
    storage: EvaluationStorage
    metrics: List[BaseMetric]
    test_cases: List[TestCase]
    client_factory: Any
    langsmith_enabled: bool = True
    
    # Runtime state
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[EvaluationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class EvaluationFramework:
    """
    Main LLM evaluation framework orchestrating test execution and result collection.
    
    Features:
    - Multi-model comparison (OpenAI, Gemini)
    - Prompt variation testing
    - A/B testing capabilities
    - Comprehensive metrics (accuracy, latency, cost)
    - LangSmith integration for tracing
    - Batch processing optimization
    - Real-time progress tracking
    """
    
    def __init__(
        self,
        storage: Optional[EvaluationStorage] = None,
        metric_registry: Optional[MetricRegistry] = None,
        client_factory: Optional[Any] = None
    ):
        self.storage = storage
        self.metric_registry = metric_registry or MetricRegistry()
        self.client_factory = client_factory
        self.evaluation_client = EvaluationClient()
        
        # Runtime state
        self._active_runs: Dict[UUID, EvaluationContext] = {}
        self._progress_callbacks: Dict[UUID, List[Callable]] = {}
        
        logger.info("LLM Evaluation Framework initialized")
    
    async def initialize(self) -> None:
        """Initialize the evaluation framework."""
        if not self.client_factory:
            from ...clients.factory import get_client_factory
            self.client_factory = get_client_factory()
        
        await self.evaluation_client.initialize()
        
        if self.storage:
            await self.storage.initialize()
        
        logger.info("Evaluation framework initialized successfully")
    
    async def create_evaluation(self, config: EvaluationConfig) -> UUID:
        """
        Create a new evaluation run.
        
        Args:
            config: Evaluation configuration
            
        Returns:
            UUID of the created evaluation run
        """
        run_id = uuid4()
        
        # Validate configuration
        await self._validate_config(config)
        
        # Load test cases
        test_cases = await self._load_test_cases(config)
        
        # Initialize metrics
        metrics = await self._initialize_metrics(config.metrics)
        
        # Create evaluation context
        context = EvaluationContext(
            run_id=run_id,
            config=config,
            storage=self.storage,
            metrics=metrics,
            test_cases=test_cases,
            client_factory=self.client_factory
        )
        
        self._active_runs[run_id] = context
        
        # Store in database if storage is available
        if self.storage:
            evaluation_run = EvaluationRun(
                id=run_id,
                name=config.name,
                description=config.description,
                config=config,
                status=EvaluationStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                test_case_count=len(test_cases),
                model_configs=config.models
            )
            await self.storage.save_evaluation_run(evaluation_run)
        
        logger.info(f"Created evaluation run {run_id} with {len(test_cases)} test cases")
        return run_id
    
    @langsmith_trace(name="run_evaluation", run_type="chain")
    async def run_evaluation(
        self,
        run_id: UUID,
        mode: EvaluationMode = EvaluationMode.SEQUENTIAL,
        max_concurrency: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> EvaluationResult:
        """
        Execute an evaluation run.
        
        Args:
            run_id: UUID of the evaluation run
            mode: Execution mode (sequential, parallel, batch)
            max_concurrency: Maximum concurrent executions for parallel mode
            progress_callback: Optional callback for progress updates
            
        Returns:
            Overall evaluation result
        """
        if run_id not in self._active_runs:
            raise ValueError(f"Evaluation run {run_id} not found")
        
        context = self._active_runs[run_id]
        
        # Register progress callback
        if progress_callback:
            if run_id not in self._progress_callbacks:
                self._progress_callbacks[run_id] = []
            self._progress_callbacks[run_id].append(progress_callback)
        
        try:
            # Update status to running
            await self._update_run_status(run_id, EvaluationStatus.RUNNING)
            
            context.start_time = datetime.now(timezone.utc)
            
            async with langsmith_session(
                f"evaluation_run_{run_id}",
                run_id=str(run_id),
                test_case_count=len(context.test_cases),
                mode=mode.value
            ):
                # Execute based on mode
                if mode == EvaluationMode.SEQUENTIAL:
                    await self._run_sequential(context)
                elif mode == EvaluationMode.PARALLEL:
                    await self._run_parallel(context, max_concurrency)
                elif mode == EvaluationMode.BATCH:
                    await self._run_batch(context)
                
                context.end_time = datetime.now(timezone.utc)
                
                # Calculate overall results
                overall_result = await self._calculate_overall_results(context)
                
                # Update status to completed
                await self._update_run_status(run_id, EvaluationStatus.COMPLETED)
                
                logger.info(
                    f"Evaluation {run_id} completed successfully in "
                    f"{(context.end_time - context.start_time).total_seconds():.2f}s"
                )
                
                return overall_result
                
        except Exception as e:
            context.errors.append(str(e))
            await self._update_run_status(run_id, EvaluationStatus.FAILED)
            logger.error(f"Evaluation {run_id} failed: {e}")
            raise
    
    async def _run_sequential(self, context: EvaluationContext) -> None:
        """Run test cases sequentially."""
        for i, test_case in enumerate(context.test_cases):
            try:
                result = await self._execute_test_case(context, test_case)
                context.results.append(result)
                
                # Report progress
                await self._report_progress(
                    context.run_id, 
                    (i + 1) / len(context.test_cases),
                    f"Completed test case {i + 1}/{len(context.test_cases)}"
                )
                
            except Exception as e:
                logger.error(f"Test case {test_case.id} failed: {e}")
                context.errors.append(f"Test case {test_case.id}: {str(e)}")
    
    async def _run_parallel(self, context: EvaluationContext, max_concurrency: int) -> None:
        """Run test cases in parallel with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrency)
        completed = 0
        
        async def execute_with_semaphore(test_case: TestCase):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._execute_test_case(context, test_case)
                    context.results.append(result)
                except Exception as e:
                    logger.error(f"Test case {test_case.id} failed: {e}")
                    context.errors.append(f"Test case {test_case.id}: {str(e)}")
                finally:
                    completed += 1
                    await self._report_progress(
                        context.run_id,
                        completed / len(context.test_cases),
                        f"Completed {completed}/{len(context.test_cases)} test cases"
                    )
        
        # Execute all test cases
        tasks = [execute_with_semaphore(tc) for tc in context.test_cases]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_batch(self, context: EvaluationContext) -> None:
        """Run test cases in optimized batches."""
        # Group test cases by model and configuration for batch optimization
        batches = self._create_batches(context.test_cases, context.config)
        
        completed = 0
        for batch in batches:
            try:
                batch_results = await self._execute_batch(context, batch)
                context.results.extend(batch_results)
                completed += len(batch)
                
                await self._report_progress(
                    context.run_id,
                    completed / len(context.test_cases),
                    f"Completed batch {len(batches)} - {completed}/{len(context.test_cases)} total"
                )
                
            except Exception as e:
                logger.error(f"Batch execution failed: {e}")
                context.errors.append(f"Batch execution: {str(e)}")
    
    @langsmith_trace(name="execute_test_case", run_type="llm")
    async def _execute_test_case(
        self, 
        context: EvaluationContext, 
        test_case: TestCase
    ) -> EvaluationResult:
        """Execute a single test case across all configured models."""
        start_time = time.time()
        model_responses = []
        
        # Execute on each model
        for model_config in context.config.models:
            try:
                response = await self.evaluation_client.execute_model_test(
                    model_config=model_config,
                    test_case=test_case,
                    client_factory=context.client_factory
                )
                model_responses.append(response)
                
            except Exception as e:
                logger.error(f"Model {model_config.provider}:{model_config.model} failed on test case {test_case.id}: {e}")
                # Create error response
                error_response = ModelResponse(
                    model_provider=model_config.provider,
                    model_name=model_config.model,
                    response_text=f"ERROR: {str(e)}",
                    latency=0.0,
                    token_usage={},
                    error=str(e),
                    test_case_id=test_case.id
                )
                model_responses.append(error_response)
        
        execution_time = time.time() - start_time
        
        # Calculate metrics for all model responses
        metric_results = []
        for metric in context.metrics:
            try:
                metric_result = await metric.calculate(
                    test_case=test_case,
                    model_responses=model_responses
                )
                metric_results.append(metric_result)
            except Exception as e:
                logger.error(f"Metric {metric.name} calculation failed: {e}")
                # Create error metric result
                error_metric = MetricResult(
                    metric_name=metric.name,
                    metric_type=metric.metric_type,
                    value=0.0,
                    details={"error": str(e)},
                    test_case_id=test_case.id
                )
                metric_results.append(error_metric)
        
        # Create evaluation result
        result = EvaluationResult(
            id=uuid4(),
            test_case=test_case,
            model_responses=model_responses,
            metrics=metric_results,
            execution_time=execution_time,
            timestamp=datetime.now(timezone.utc),
            evaluation_run_id=context.run_id
        )
        
        # Store result if storage is available
        if context.storage:
            await context.storage.save_evaluation_result(result)
        
        return result
    
    async def _execute_batch(
        self, 
        context: EvaluationContext, 
        batch: List[TestCase]
    ) -> List[EvaluationResult]:
        """Execute a batch of test cases with optimization."""
        # For now, execute sequentially within batch
        # Future optimization: group by model and use batch APIs
        results = []
        for test_case in batch:
            result = await self._execute_test_case(context, test_case)
            results.append(result)
        return results
    
    def _create_batches(
        self, 
        test_cases: List[TestCase], 
        config: EvaluationConfig
    ) -> List[List[TestCase]]:
        """Create optimized batches of test cases."""
        # Simple batching by batch_size for now
        batch_size = getattr(config, 'batch_size', 10)
        batches = []
        
        for i in range(0, len(test_cases), batch_size):
            batch = test_cases[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    async def _validate_config(self, config: EvaluationConfig) -> None:
        """Validate evaluation configuration."""
        if not config.models:
            raise ValueError("At least one model configuration is required")
        
        if not config.test_suite_id and not config.test_cases:
            raise ValueError("Either test_suite_id or test_cases must be provided")
        
        # Validate model configurations
        for model_config in config.models:
            if not model_config.provider or not model_config.model:
                raise ValueError(f"Invalid model configuration: {model_config}")
    
    async def _load_test_cases(self, config: EvaluationConfig) -> List[TestCase]:
        """Load test cases for the evaluation."""
        if config.test_cases:
            return config.test_cases
        
        if config.test_suite_id and self.storage:
            return await self.storage.get_test_cases_by_suite(config.test_suite_id)
        
        raise ValueError("No test cases could be loaded")
    
    async def _initialize_metrics(self, metric_names: List[str]) -> List[BaseMetric]:
        """Initialize metrics for the evaluation."""
        metrics = []
        for metric_name in metric_names:
            metric = self.metric_registry.get_metric(metric_name)
            if metric:
                metrics.append(metric)
            else:
                logger.warning(f"Metric {metric_name} not found in registry")
        
        if not metrics:
            # Add default metrics if none specified
            metrics = [
                self.metric_registry.get_metric("accuracy"),
                self.metric_registry.get_metric("latency"),
                self.metric_registry.get_metric("token_efficiency")
            ]
        
        return [m for m in metrics if m is not None]
    
    async def _calculate_overall_results(self, context: EvaluationContext) -> EvaluationResult:
        """Calculate overall results for the evaluation run."""
        if not context.results:
            raise ValueError("No results to calculate overall metrics")
        
        # Aggregate metrics across all test cases
        aggregated_metrics = {}
        
        for result in context.results:
            for metric_result in result.metrics:
                metric_name = metric_result.metric_name
                if metric_name not in aggregated_metrics:
                    aggregated_metrics[metric_name] = []
                aggregated_metrics[metric_name].append(metric_result.value)
        
        # Calculate summary metrics
        summary_metrics = []
        for metric_name, values in aggregated_metrics.items():
            if values:
                avg_value = sum(values) / len(values)
                summary_metric = MetricResult(
                    metric_name=f"{metric_name}_average",
                    metric_type=MetricType.AGGREGATE,
                    value=avg_value,
                    details={
                        "individual_values": values,
                        "count": len(values),
                        "min": min(values),
                        "max": max(values)
                    },
                    test_case_id=None  # This is an aggregate metric
                )
                summary_metrics.append(summary_metric)
        
        # Create overall result
        overall_result = EvaluationResult(
            id=uuid4(),
            test_case=None,  # This represents the overall evaluation
            model_responses=[],  # Aggregated separately
            metrics=summary_metrics,
            execution_time=(context.end_time - context.start_time).total_seconds(),
            timestamp=context.end_time,
            evaluation_run_id=context.run_id,
            metadata={
                "total_test_cases": len(context.test_cases),
                "successful_results": len(context.results),
                "errors": len(context.errors),
                "models_tested": len(context.config.models)
            }
        )
        
        return overall_result
    
    async def _update_run_status(self, run_id: UUID, status: EvaluationStatus) -> None:
        """Update the status of an evaluation run."""
        if self.storage:
            await self.storage.update_evaluation_status(run_id, status)
        
        # Update in-memory context
        if run_id in self._active_runs:
            # This would be part of a more complete status tracking system
            pass
    
    async def _report_progress(self, run_id: UUID, progress: float, message: str) -> None:
        """Report progress to registered callbacks."""
        if run_id in self._progress_callbacks:
            for callback in self._progress_callbacks[run_id]:
                try:
                    await callback(run_id, progress, message)
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
    
    async def get_evaluation_status(self, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the current status of an evaluation run."""
        if run_id not in self._active_runs:
            # Try to load from storage
            if self.storage:
                return await self.storage.get_evaluation_run_status(run_id)
            return None
        
        context = self._active_runs[run_id]
        completed_tests = len(context.results)
        total_tests = len(context.test_cases)
        
        return {
            "run_id": str(run_id),
            "status": "running",
            "progress": completed_tests / total_tests if total_tests > 0 else 0,
            "completed_tests": completed_tests,
            "total_tests": total_tests,
            "errors": len(context.errors),
            "start_time": context.start_time.isoformat() if context.start_time else None,
            "elapsed_time": (
                (datetime.now(timezone.utc) - context.start_time).total_seconds()
                if context.start_time else 0
            )
        }
    
    async def cancel_evaluation(self, run_id: UUID) -> bool:
        """Cancel a running evaluation."""
        if run_id not in self._active_runs:
            return False
        
        # Update status
        await self._update_run_status(run_id, EvaluationStatus.CANCELLED)
        
        # Clean up context
        del self._active_runs[run_id]
        if run_id in self._progress_callbacks:
            del self._progress_callbacks[run_id]
        
        logger.info(f"Evaluation {run_id} cancelled")
        return True
    
    async def cleanup(self) -> None:
        """Clean up framework resources."""
        # Cancel all active runs
        for run_id in list(self._active_runs.keys()):
            await self.cancel_evaluation(run_id)
        
        # Close storage connection
        if self.storage:
            await self.storage.close()
        
        logger.info("Evaluation framework cleanup completed")