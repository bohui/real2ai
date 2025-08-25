"""
LangSmith Integration for Evaluation System

This module provides enhanced LangSmith integration for the evaluation system,
enabling automatic dataset creation, advanced analytics, and sophisticated
A/B testing capabilities.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from uuid import uuid4

from ..core.langsmith_config import (
    get_langsmith_config,
    langsmith_trace,
    langsmith_session,
)
from .core.evaluation_storage import EvaluationStorage

logger = logging.getLogger(__name__)


@dataclass
class LangSmithDatasetConfig:
    """Configuration for LangSmith dataset creation."""

    dataset_name: str
    description: Optional[str] = None
    trace_filters: Dict[str, Any] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_examples: Optional[int] = None
    quality_threshold: float = 0.7


@dataclass
class LangSmithEvaluationConfig:
    """Configuration for LangSmith-enhanced evaluation."""

    evaluation_name: str
    dataset_config: LangSmithDatasetConfig
    model_configs: List[Dict[str, Any]]
    metrics_config: Dict[str, Any]
    ab_test_config: Optional[Dict[str, Any]] = None
    performance_monitoring: bool = True


class LangSmithEvaluationIntegration:
    """
    Enhanced evaluation integration with LangSmith.

    Features:
    - Automatic dataset creation from traces
    - Enhanced evaluation with rich metadata
    - Advanced performance monitoring
    - A/B testing with statistical analysis
    - Continuous evaluation pipeline
    """

    def __init__(self, storage: Optional[EvaluationStorage] = None):
        self.storage = storage
        self.config = get_langsmith_config()
        self._enabled = self.config.enabled

        if not self._enabled:
            logger.warning(
                "LangSmith integration disabled - limited functionality available"
            )

    @property
    def enabled(self) -> bool:
        """Check if LangSmith integration is enabled."""
        return self._enabled

    @langsmith_trace(name="create_langsmith_dataset", run_type="chain")
    async def create_dataset_from_traces(
        self, dataset_config: LangSmithDatasetConfig
    ) -> str:
        """
        Create a LangSmith dataset from existing traces.

        Args:
            dataset_config: Configuration for dataset creation

        Returns:
            Dataset ID
        """
        if not self.enabled:
            raise ValueError("LangSmith integration not enabled")

        async with langsmith_session(
            "create_dataset_from_traces",
            dataset_name=dataset_config.dataset_name,
            trace_filters=dataset_config.trace_filters,
        ) as session:

            try:
                # Create dataset in LangSmith
                dataset = self.config.client.create_dataset(
                    dataset_name=dataset_config.dataset_name,
                    description=dataset_config.description
                    or f"Auto-generated from traces",
                )

                # Query traces based on filters
                traces = self._query_traces(dataset_config)

                # Convert traces to examples
                example_count = 0
                for trace in traces:
                    if self._is_valid_trace_for_dataset(trace, dataset_config):
                        example = self._convert_trace_to_example(trace)
                        if example:
                            self.config.client.create_example(
                                dataset_id=dataset.id,
                                inputs=example["inputs"],
                                outputs=example["outputs"],
                            )
                            example_count += 1

                            if (
                                dataset_config.max_examples
                                and example_count >= dataset_config.max_examples
                            ):
                                break

                session.outputs = {
                    "dataset_id": dataset.id,
                    "example_count": example_count,
                    "total_traces_processed": len(traces),
                }

                logger.info(
                    f"Created LangSmith dataset {dataset.id} with {example_count} examples"
                )
                return dataset.id

            except Exception as e:
                session.error = str(e)
                logger.error(f"Failed to create dataset from traces: {e}")
                raise

    @langsmith_trace(name="enhanced_evaluation", run_type="chain")
    async def run_enhanced_evaluation(
        self, evaluation_config: LangSmithEvaluationConfig
    ) -> Dict[str, Any]:
        """
        Run enhanced evaluation with LangSmith integration.

        Args:
            evaluation_config: Configuration for enhanced evaluation

        Returns:
            Evaluation results with enhanced metadata
        """
        async with langsmith_session(
            "enhanced_evaluation",
            evaluation_name=evaluation_config.evaluation_name,
            model_count=len(evaluation_config.model_configs),
            metrics_enabled=list(evaluation_config.metrics_config.keys()),
        ) as session:

            try:
                # Create dataset from traces if needed
                if evaluation_config.dataset_config:
                    dataset_id = await self.create_dataset_from_traces(
                        evaluation_config.dataset_config
                    )
                else:
                    dataset_id = None

                # Run evaluation with enhanced tracing
                evaluation_results = await self._run_evaluation_with_tracing(
                    evaluation_config, dataset_id
                )

                # Analyze performance if enabled
                if evaluation_config.performance_monitoring:
                    performance_analysis = await self.analyze_evaluation_performance(
                        evaluation_results
                    )
                    evaluation_results["performance_analysis"] = performance_analysis

                # Update session with results
                session.outputs = {
                    "evaluation_results": evaluation_results,
                    "dataset_id": dataset_id,
                    "total_evaluations": len(evaluation_results.get("results", [])),
                    "average_score": evaluation_results.get("average_score", 0),
                }

                return evaluation_results

            except Exception as e:
                session.error = str(e)
                logger.error(f"Enhanced evaluation failed: {e}")
                raise

    @langsmith_trace(name="ab_test_experiment", run_type="chain")
    async def run_ab_test_with_langsmith(
        self,
        control_prompt: str,
        variant_prompt: str,
        test_dataset: List[Dict[str, Any]],
        ab_test_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run A/B test with enhanced LangSmith integration.

        Args:
            control_prompt: Control prompt for testing
            variant_prompt: Variant prompt for testing
            test_dataset: Test dataset
            ab_test_config: A/B test configuration

        Returns:
            A/B test results with statistical analysis
        """
        async with langsmith_session(
            "ab_test_experiment",
            control_prompt_hash=hash(control_prompt),
            variant_prompt_hash=hash(variant_prompt),
            test_dataset_size=len(test_dataset),
            duration_hours=ab_test_config.get("duration_hours", 24),
        ) as session:

            try:
                # Split dataset
                split_ratio = ab_test_config.get("split_ratio", 0.5)
                split_point = int(len(test_dataset) * split_ratio)

                control_cases = test_dataset[:split_point]
                variant_cases = test_dataset[split_point:]

                # Run control group
                control_results = await self._run_evaluation_group(
                    prompt=control_prompt,
                    test_cases=control_cases,
                    group_name="control",
                    model_configs=ab_test_config.get("model_configs", []),
                )

                # Run variant group
                variant_results = await self._run_evaluation_group(
                    prompt=variant_prompt,
                    test_cases=variant_cases,
                    group_name="variant",
                    model_configs=ab_test_config.get("model_configs", []),
                )

                # Perform statistical analysis
                statistical_analysis = await self._perform_statistical_analysis(
                    control_results, variant_results
                )

                # Generate recommendation
                recommendation = self._generate_ab_test_recommendation(
                    statistical_analysis, ab_test_config
                )

                # Compile results
                ab_test_results = {
                    "control_results": control_results,
                    "variant_results": variant_results,
                    "statistical_analysis": statistical_analysis,
                    "recommendation": recommendation,
                    "experiment_config": ab_test_config,
                }

                # Update session
                session.outputs = {
                    "control_performance": control_results.get("average_score", 0),
                    "variant_performance": variant_results.get("average_score", 0),
                    "statistical_significance": statistical_analysis.get("p_value", 0),
                    "recommendation": recommendation,
                }

                return ab_test_results

            except Exception as e:
                session.error = str(e)
                logger.error(f"A/B test failed: {e}")
                raise

    async def analyze_evaluation_performance(
        self,
        evaluation_results: Dict[str, Any],
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze evaluation performance using LangSmith data.

        Args:
            evaluation_results: Evaluation results to analyze
            time_range: Optional time range for analysis

        Returns:
            Performance analysis results
        """
        if not self.enabled:
            return {"error": "LangSmith not available"}

        try:
            # Get traces for the evaluation
            traces = self._get_evaluation_traces(evaluation_results, time_range)

            # Analyze performance metrics
            performance_data = {
                "total_traces": len(traces),
                "average_execution_time": 0,
                "success_rate": 0,
                "error_rate": 0,
                "cost_analysis": {},
                "model_performance": {},
                "metric_performance": {},
            }

            # Calculate metrics
            execution_times = []
            success_count = 0
            error_count = 0

            for trace in traces:
                if hasattr(trace, "execution_time") and trace.execution_time:
                    execution_times.append(trace.execution_time)

                if hasattr(trace, "error") and trace.error:
                    error_count += 1
                else:
                    success_count += 1

            if execution_times:
                performance_data["average_execution_time"] = sum(execution_times) / len(
                    execution_times
                )

            total_traces = len(traces)
            if total_traces > 0:
                performance_data["success_rate"] = success_count / total_traces
                performance_data["error_rate"] = error_count / total_traces

            return performance_data

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {"error": str(e)}

    async def create_continuous_evaluation_pipeline(
        self, pipeline_config: Dict[str, Any]
    ) -> str:
        """
        Create a continuous evaluation pipeline from LangSmith traces.

        Args:
            pipeline_config: Pipeline configuration

        Returns:
            Pipeline ID
        """
        if not self.enabled:
            raise ValueError("LangSmith integration not enabled")

        async with langsmith_session(
            "continuous_evaluation_pipeline",
            pipeline_name=pipeline_config.get("name", "auto_pipeline"),
        ) as session:

            try:
                # Create pipeline configuration
                pipeline_id = str(uuid4())

                # Set up monitoring
                monitoring_config = {
                    "pipeline_id": pipeline_id,
                    "evaluation_interval": pipeline_config.get(
                        "evaluation_interval", 3600
                    ),  # 1 hour
                    "alert_threshold": pipeline_config.get("alert_threshold", 0.7),
                    "metrics_to_monitor": pipeline_config.get(
                        "metrics_to_monitor", ["accuracy", "latency"]
                    ),
                }

                # Store pipeline configuration
                if self.storage:
                    await self.storage.save_pipeline_config(
                        pipeline_id, monitoring_config
                    )

                session.outputs = {
                    "pipeline_id": pipeline_id,
                    "monitoring_config": monitoring_config,
                }

                logger.info(f"Created continuous evaluation pipeline {pipeline_id}")
                return pipeline_id

            except Exception as e:
                session.error = str(e)
                logger.error(f"Failed to create continuous evaluation pipeline: {e}")
                raise

    # Helper methods

    def _query_traces(self, dataset_config: LangSmithDatasetConfig) -> List[Any]:
        """Query traces from LangSmith based on configuration."""
        if not self.enabled:
            return []

        try:
            # Build query filters
            filters = dataset_config.trace_filters or {}

            # Add time range if specified
            if dataset_config.time_range:
                start_time, end_time = dataset_config.time_range
                filters["start_time"] = start_time
                filters["end_time"] = end_time

            # Query traces
            traces = self.config.client.list_runs(
                project_name=self.config.project_name, **filters
            )

            return list(traces)

        except Exception as e:
            logger.error(f"Failed to query traces: {e}")
            return []

    def _is_valid_trace_for_dataset(
        self, trace: Any, dataset_config: LangSmithDatasetConfig
    ) -> bool:
        """Check if a trace is valid for dataset creation."""
        try:
            # Check if trace has required data
            if not hasattr(trace, "inputs") or not hasattr(trace, "outputs"):
                return False

            # Check quality threshold if specified
            if dataset_config.quality_threshold > 0:
                # This would need to be implemented based on your quality metrics
                pass

            return True

        except Exception:
            return False

    def _convert_trace_to_example(self, trace: Any) -> Optional[Dict[str, Any]]:
        """Convert a trace to a dataset example."""
        try:
            if not trace.inputs or not trace.outputs:
                return None

            return {"inputs": trace.inputs, "outputs": trace.outputs}

        except Exception as e:
            logger.error(f"Failed to convert trace to example: {e}")
            return None

    async def _run_evaluation_with_tracing(
        self, evaluation_config: LangSmithEvaluationConfig, dataset_id: Optional[str]
    ) -> Dict[str, Any]:
        """Run evaluation with enhanced tracing."""
        # This would integrate with your existing evaluation framework
        # For now, return a placeholder
        return {
            "evaluation_id": str(uuid4()),
            "dataset_id": dataset_id,
            "results": [],
            "average_score": 0.0,
            "status": "completed",
        }

    async def _run_evaluation_group(
        self,
        prompt: str,
        test_cases: List[Dict[str, Any]],
        group_name: str,
        model_configs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run evaluation for a specific group."""
        # This would integrate with your existing evaluation framework
        return {
            "group_name": group_name,
            "test_cases_processed": len(test_cases),
            "average_score": 0.0,
            "results": [],
        }

    async def _perform_statistical_analysis(
        self, control_results: Dict[str, Any], variant_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform statistical analysis on A/B test results."""
        # This would implement statistical significance testing
        # For now, return a placeholder
        return {
            "p_value": 0.05,
            "confidence_interval": [0.1, 0.2],
            "statistical_significance": True,
            "effect_size": 0.15,
        }

    def _generate_ab_test_recommendation(
        self, statistical_analysis: Dict[str, Any], ab_test_config: Dict[str, Any]
    ) -> str:
        """Generate recommendation based on A/B test results."""
        p_value = statistical_analysis.get("p_value", 1.0)
        effect_size = statistical_analysis.get("effect_size", 0.0)

        if p_value < 0.05 and effect_size > 0.1:
            return "recommend_variant"
        elif p_value < 0.05 and effect_size < -0.1:
            return "recommend_control"
        else:
            return "no_change"

    def _get_evaluation_traces(
        self,
        evaluation_results: Dict[str, Any],
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Any]:
        """Get traces for evaluation analysis."""
        if not self.enabled:
            return []

        try:
            # Query traces for the evaluation
            filters = {
                "run_type": "chain",
                "tags": [
                    f"evaluation:{evaluation_results.get('evaluation_id', 'unknown')}"
                ],
            }

            if time_range:
                start_time, end_time = time_range
                filters["start_time"] = start_time
                filters["end_time"] = end_time

            traces = self.config.client.list_runs(
                project_name=self.config.project_name, **filters
            )

            return list(traces)

        except Exception as e:
            logger.error(f"Failed to get evaluation traces: {e}")
            return []


# Factory function
async def get_langsmith_evaluation_integration(
    storage: Optional[EvaluationStorage] = None,
) -> LangSmithEvaluationIntegration:
    """Get LangSmith evaluation integration instance."""
    integration = LangSmithEvaluationIntegration(storage=storage)
    return integration
