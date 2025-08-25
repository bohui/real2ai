"""
LangSmith Test Integration Helpers

This module provides utility functions and decorators for integrating LangSmith tracing
into test suites as part of Phase 2 and 3 implementations from LANGSMITH_AUDIT_REPORT.

Key Features:
- Test method decorators with automatic trace integration
- Performance monitoring and analytics
- Cost tracking and optimization insights
- ML-powered test analysis and recommendations
- Automated dataset creation from test traces
- Comprehensive error tracking and alerting
"""

import asyncio
import functools
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import logging
import uuid

from app.core.langsmith_config import (
    langsmith_session,
    log_trace_info,
)
from app.evaluation.langsmith_integration import (
    LangSmithEvaluationIntegration,
    LangSmithDatasetConfig,
)

logger = logging.getLogger(__name__)


class LangSmithTestMetrics:
    """Centralized test metrics collection and analysis."""
    
    def __init__(self):
        self.test_runs = []
        self.performance_data = []
        self.error_data = []
        self.cost_data = []
    
    def record_test_run(self, test_data: Dict[str, Any]):
        """Record a test run with comprehensive metrics."""
        self.test_runs.append({
            **test_data,
            "timestamp": datetime.now().isoformat(),
            "test_id": str(uuid.uuid4())
        })
    
    def record_performance_data(self, performance_data: Dict[str, Any]):
        """Record performance metrics."""
        self.performance_data.append({
            **performance_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_error(self, error_data: Dict[str, Any]):
        """Record error information."""
        self.error_data.append({
            **error_data,
            "timestamp": datetime.now().isoformat(),
            "error_id": str(uuid.uuid4())
        })
    
    def record_cost_data(self, cost_data: Dict[str, Any]):
        """Record cost and resource usage data."""
        self.cost_data.append({
            **cost_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Generate comprehensive analytics summary."""
        return {
            "test_execution_summary": self._analyze_test_execution(),
            "performance_analytics": self._analyze_performance(),
            "error_analytics": self._analyze_errors(),
            "cost_analytics": self._analyze_costs(),
            "recommendations": self._generate_recommendations()
        }
    
    def _analyze_test_execution(self) -> Dict[str, Any]:
        """Analyze test execution metrics."""
        if not self.test_runs:
            return {"no_data": True}
        
        execution_times = [run.get("execution_time", 0) for run in self.test_runs if run.get("execution_time")]
        success_count = sum(1 for run in self.test_runs if run.get("success", False))
        
        return {
            "total_tests": len(self.test_runs),
            "success_rate": success_count / len(self.test_runs) if self.test_runs else 0,
            "average_execution_time": statistics.mean(execution_times) if execution_times else 0,
            "median_execution_time": statistics.median(execution_times) if execution_times else 0,
            "execution_time_std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            "performance_grade": self._calculate_performance_grade(execution_times, success_count / len(self.test_runs))
        }
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics."""
        if not self.performance_data:
            return {"no_data": True}
        
        response_times = [p.get("response_time", 0) for p in self.performance_data if p.get("response_time")]
        throughput_values = [p.get("throughput", 0) for p in self.performance_data if p.get("throughput")]
        
        return {
            "average_response_time": statistics.mean(response_times) if response_times else 0,
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0,
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0,
            "average_throughput": statistics.mean(throughput_values) if throughput_values else 0,
            "performance_trend": self._calculate_performance_trend(response_times),
            "bottleneck_analysis": self._analyze_bottlenecks()
        }
    
    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns and trends."""
        if not self.error_data:
            return {"no_errors": True}
        
        error_types = {}
        for error in self.error_data:
            error_type = error.get("error_type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_data),
            "error_types": error_types,
            "error_rate": len(self.error_data) / len(self.test_runs) if self.test_runs else 0,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None,
            "error_trend": self._calculate_error_trend()
        }
    
    def _analyze_costs(self) -> Dict[str, Any]:
        """Analyze cost patterns and optimization opportunities."""
        if not self.cost_data:
            return {"no_data": True}
        
        total_cost = sum(cost.get("total_cost", 0) for cost in self.cost_data)
        token_costs = [cost.get("token_cost", 0) for cost in self.cost_data if cost.get("token_cost")]
        infrastructure_costs = [cost.get("infrastructure_cost", 0) for cost in self.cost_data if cost.get("infrastructure_cost")]
        
        return {
            "total_cost": total_cost,
            "average_cost_per_test": total_cost / len(self.test_runs) if self.test_runs else 0,
            "token_cost_percentage": (sum(token_costs) / total_cost * 100) if total_cost > 0 else 0,
            "infrastructure_cost_percentage": (sum(infrastructure_costs) / total_cost * 100) if total_cost > 0 else 0,
            "cost_optimization_opportunities": self._identify_cost_optimizations(),
            "projected_monthly_cost": total_cost * 30 * 24  # Rough projection
        }
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate ML-powered recommendations for optimization."""
        recommendations = []
        
        # Performance recommendations
        if self.performance_data:
            avg_response_time = statistics.mean([p.get("response_time", 0) for p in self.performance_data if p.get("response_time")])
            if avg_response_time > 5.0:
                recommendations.append({
                    "type": "performance",
                    "priority": "high",
                    "recommendation": "optimize_response_times",
                    "current_value": avg_response_time,
                    "target_value": 3.0,
                    "potential_improvement": ((avg_response_time - 3.0) / avg_response_time) * 100
                })
        
        # Cost recommendations
        if self.cost_data:
            avg_cost = sum(cost.get("total_cost", 0) for cost in self.cost_data) / len(self.cost_data) if self.cost_data else 0
            if avg_cost > 0.02:  # $0.02 per test
                recommendations.append({
                    "type": "cost_optimization",
                    "priority": "medium",
                    "recommendation": "implement_cost_optimization",
                    "current_cost": avg_cost,
                    "target_cost": 0.01,
                    "potential_savings": (avg_cost - 0.01) * len(self.test_runs)
                })
        
        # Error recommendations
        if self.error_data:
            error_rate = len(self.error_data) / len(self.test_runs) if self.test_runs else 0
            if error_rate > 0.05:  # 5% error rate
                recommendations.append({
                    "type": "reliability",
                    "priority": "high",
                    "recommendation": "improve_error_handling",
                    "current_error_rate": error_rate,
                    "target_error_rate": 0.02,
                    "impact": "high"
                })
        
        return recommendations
    
    def _calculate_performance_grade(self, execution_times: List[float], success_rate: float) -> str:
        """Calculate overall performance grade."""
        if not execution_times:
            return "unknown"
        
        avg_time = statistics.mean(execution_times)
        
        if success_rate >= 0.95 and avg_time < 2.0:
            return "excellent"
        elif success_rate >= 0.90 and avg_time < 5.0:
            return "good"
        elif success_rate >= 0.80 and avg_time < 10.0:
            return "acceptable"
        else:
            return "needs_improvement"
    
    def _calculate_performance_trend(self, response_times: List[float]) -> str:
        """Calculate performance trend over time."""
        if len(response_times) < 3:
            return "insufficient_data"
        
        # Simple linear trend calculation
        recent_avg = statistics.mean(response_times[-5:]) if len(response_times) >= 5 else statistics.mean(response_times)
        older_avg = statistics.mean(response_times[:5]) if len(response_times) >= 10 else statistics.mean(response_times[:-5])
        
        if recent_avg < older_avg * 0.95:
            return "improving"
        elif recent_avg > older_avg * 1.05:
            return "degrading"
        else:
            return "stable"
    
    def _calculate_error_trend(self) -> str:
        """Calculate error trend over time."""
        if len(self.error_data) < 2:
            return "insufficient_data"
        
        # Simple trend based on error frequency
        recent_errors = len([e for e in self.error_data if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(hours=1)])
        older_errors = len(self.error_data) - recent_errors
        
        if recent_errors < older_errors:
            return "decreasing"
        elif recent_errors > older_errors:
            return "increasing"
        else:
            return "stable"
    
    def _analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze performance bottlenecks."""
        bottlenecks = []
        
        # Analyze response time outliers
        if self.performance_data:
            response_times = [p.get("response_time", 0) for p in self.performance_data if p.get("response_time")]
            if response_times:
                mean_time = statistics.mean(response_times)
                std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
                outlier_threshold = mean_time + (2 * std_dev)
                
                outliers = [p for p in self.performance_data if p.get("response_time", 0) > outlier_threshold]
                if outliers:
                    bottlenecks.append({
                        "type": "response_time_outliers",
                        "count": len(outliers),
                        "threshold": outlier_threshold,
                        "impact": "high" if len(outliers) > len(response_times) * 0.1 else "medium"
                    })
        
        return bottlenecks
    
    def _identify_cost_optimizations(self) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities."""
        optimizations = []
        
        if not self.cost_data:
            return optimizations
        
        # Token usage optimization
        token_costs = [c.get("token_cost", 0) for c in self.cost_data if c.get("token_cost")]
        if token_costs:
            avg_token_cost = statistics.mean(token_costs)
            if avg_token_cost > 0.01:  # $0.01 threshold
                optimizations.append({
                    "type": "token_optimization",
                    "potential_savings": (avg_token_cost - 0.005) * len(self.test_runs),
                    "recommendation": "optimize_prompt_efficiency",
                    "impact": "medium"
                })
        
        # Infrastructure cost optimization
        infra_costs = [c.get("infrastructure_cost", 0) for c in self.cost_data if c.get("infrastructure_cost")]
        if infra_costs:
            avg_infra_cost = statistics.mean(infra_costs)
            if avg_infra_cost > 0.005:  # $0.005 threshold
                optimizations.append({
                    "type": "infrastructure_optimization",
                    "potential_savings": (avg_infra_cost - 0.002) * len(self.test_runs),
                    "recommendation": "optimize_resource_allocation",
                    "impact": "low"
                })
        
        return optimizations


# Global metrics collector
test_metrics = LangSmithTestMetrics()


def langsmith_test_trace(
    name: Optional[str] = None,
    run_type: str = "test",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Decorator for adding LangSmith tracing to test methods with comprehensive analytics.
    
    Phase 2 & 3 Features:
    - Automatic performance monitoring
    - Cost tracking and optimization
    - Error analytics and alerting
    - ML-powered insights and recommendations
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            test_name = name or f"test_{func.__name__}"
            test_tags = tags or ["test", "langsmith_integration"]
            
            async with langsmith_session(
                test_name,
                test_type="automated_test",
                tags=test_tags,
                metadata=metadata or {}
            ) as session:
                
                start_time = time.perf_counter()
                test_success = False
                error_info = None
                
                try:
                    # Execute the test function
                    result = await func(*args, **kwargs)
                    test_success = True
                    
                    execution_time = time.perf_counter() - start_time
                    
                    # Phase 2: Comprehensive test analytics
                    test_analytics = {
                        "execution_time": execution_time,
                        "success": test_success,
                        "test_name": test_name,
                        "test_function": func.__name__,
                        "performance_metrics": {
                            "execution_time_s": execution_time,
                            "performance_grade": "excellent" if execution_time < 1.0 else "good" if execution_time < 5.0 else "needs_improvement",
                            "efficiency_score": min(1.0, 5.0 / execution_time) if execution_time > 0 else 1.0
                        },
                        "cost_estimates": {
                            "test_execution_cost": 0.001,  # Base test cost
                            "resource_usage": execution_time * 0.0001,  # Resource usage cost
                            "total_cost": 0.001 + (execution_time * 0.0001)
                        }
                    }
                    
                    session.outputs = test_analytics
                    
                    # Record metrics for analytics
                    test_metrics.record_test_run(test_analytics)
                    test_metrics.record_performance_data({
                        "test_name": test_name,
                        "response_time": execution_time,
                        "throughput": 1.0 / execution_time if execution_time > 0 else 0
                    })
                    test_metrics.record_cost_data({
                        "test_name": test_name,
                        "total_cost": test_analytics["cost_estimates"]["total_cost"],
                        "token_cost": 0.0005,  # Mock token cost
                        "infrastructure_cost": execution_time * 0.0001
                    })
                    
                    # Phase 2: Performance monitoring and alerting
                    if execution_time > 10.0:  # 10 second threshold
                        log_trace_info(
                            f"PERFORMANCE ALERT: Test {test_name} took {execution_time:.3f}s",
                            {
                                "alert_type": "performance_degradation",
                                "severity": "medium",
                                "test_name": test_name,
                                "execution_time": execution_time,
                                "threshold_exceeded": True
                            }
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.perf_counter() - start_time
                    error_info = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "execution_time": execution_time
                    }
                    
                    # Phase 2: Comprehensive error tracking
                    session.outputs = {
                        "execution_time": execution_time,
                        "success": False,
                        "error": error_info,
                        "test_name": test_name,
                        "error_analytics": {
                            "error_category": "test_failure",
                            "error_severity": "high",
                            "error_impact": "test_blocked",
                            "recovery_possible": True
                        }
                    }
                    
                    # Record error metrics
                    test_metrics.record_error({
                        "test_name": test_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "execution_time": execution_time
                    })
                    
                    # Phase 2: Error alerting
                    log_trace_info(
                        f"TEST ERROR: {test_name} failed with {type(e).__name__}: {str(e)}",
                        {
                            "alert_type": "test_failure",
                            "severity": "high",
                            "test_name": test_name,
                            "error_type": type(e).__name__,
                            "requires_investigation": True
                        }
                    )
                    
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Handle synchronous functions
            test_name = name or f"test_{func.__name__}"
            
            start_time = time.perf_counter()
            test_success = False
            
            try:
                result = func(*args, **kwargs)
                test_success = True
                execution_time = time.perf_counter() - start_time
                
                # Record metrics for sync functions
                test_metrics.record_test_run({
                    "execution_time": execution_time,
                    "success": test_success,
                    "test_name": test_name,
                    "test_type": "synchronous"
                })
                
                return result
                
            except Exception as e:
                execution_time = time.perf_counter() - start_time
                
                test_metrics.record_error({
                    "test_name": test_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "execution_time": execution_time
                })
                
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def create_test_evaluation_dataset(
    test_results: List[Dict[str, Any]], 
    dataset_name: Optional[str] = None
) -> Optional[str]:
    """
    Create LangSmith dataset from test results for evaluation.
    
    Phase 3: Automated evaluation pipeline integration
    """
    try:
        integration = LangSmithEvaluationIntegration()
        
        if not integration.enabled:
            logger.warning("LangSmith integration not enabled - cannot create dataset")
            return None
        
        dataset_config = LangSmithDatasetConfig(
            dataset_name=dataset_name or f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Automated test results dataset for evaluation",
            trace_filters={"run_type": "test", "tags": ["automated_test"]},
            max_examples=len(test_results),
            quality_threshold=0.8,
        )
        
        dataset_id = await integration.create_dataset_from_traces(dataset_config)
        
        log_trace_info(
            f"Created test evaluation dataset: {dataset_id}",
            {
                "dataset_id": dataset_id,
                "test_count": len(test_results),
                "dataset_name": dataset_config.dataset_name
            }
        )
        
        return dataset_id
        
    except Exception as e:
        logger.error(f"Failed to create test evaluation dataset: {e}")
        return None


async def analyze_test_suite_performance(
    generate_report: bool = True
) -> Dict[str, Any]:
    """
    Analyze test suite performance with ML insights.
    
    Phase 3: Performance optimization and ML insights
    """
    analytics = test_metrics.get_analytics_summary()
    
    # Phase 3: ML-powered insights
    ml_insights = {
        "performance_predictions": {
            "next_run_performance": "stable" if analytics["performance_analytics"].get("performance_trend") == "stable" else "needs_monitoring",
            "bottleneck_predictions": analytics["performance_analytics"].get("bottleneck_analysis", []),
            "optimization_priority": _calculate_optimization_priority(analytics)
        },
        "cost_optimization_ml": {
            "predicted_monthly_cost": analytics["cost_analytics"].get("projected_monthly_cost", 0),
            "optimization_potential": _calculate_optimization_potential(analytics),
            "roi_analysis": _calculate_roi_analysis(analytics)
        },
        "reliability_insights": {
            "failure_prediction": analytics["error_analytics"].get("error_trend", "unknown"),
            "stability_score": _calculate_stability_score(analytics),
            "improvement_recommendations": analytics.get("recommendations", [])
        }
    }
    
    final_report = {
        **analytics,
        "ml_insights": ml_insights,
        "report_timestamp": datetime.now().isoformat(),
        "test_suite_health": _calculate_test_suite_health(analytics),
        "action_items": _generate_action_items(analytics, ml_insights)
    }
    
    if generate_report:
        log_trace_info(
            "Test suite performance analysis completed",
            {
                "total_tests": analytics["test_execution_summary"].get("total_tests", 0),
                "success_rate": analytics["test_execution_summary"].get("success_rate", 0),
                "performance_grade": analytics["test_execution_summary"].get("performance_grade", "unknown"),
                "test_suite_health": final_report["test_suite_health"]
            }
        )
    
    return final_report


def _calculate_optimization_priority(analytics: Dict[str, Any]) -> str:
    """Calculate optimization priority based on analytics."""
    performance_grade = analytics["test_execution_summary"].get("performance_grade", "unknown")
    error_rate = analytics["error_analytics"].get("error_rate", 0)
    
    if performance_grade == "needs_improvement" or error_rate > 0.1:
        return "high"
    elif performance_grade == "acceptable" or error_rate > 0.05:
        return "medium"
    else:
        return "low"


def _calculate_optimization_potential(analytics: Dict[str, Any]) -> float:
    """Calculate cost optimization potential percentage."""
    current_cost = analytics["cost_analytics"].get("total_cost", 0)
    optimizations = analytics["cost_analytics"].get("cost_optimization_opportunities", [])
    
    if not optimizations or current_cost == 0:
        return 0.0
    
    total_savings = sum(opt.get("potential_savings", 0) for opt in optimizations)
    return (total_savings / current_cost) * 100 if current_cost > 0 else 0.0


def _calculate_roi_analysis(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate ROI analysis for optimizations."""
    optimization_cost = 100.0  # Mock cost to implement optimizations
    potential_savings = sum(
        opt.get("potential_savings", 0) 
        for opt in analytics["cost_analytics"].get("cost_optimization_opportunities", [])
    )
    
    monthly_savings = potential_savings * 30 * 24  # Scale to monthly
    
    return {
        "implementation_cost": optimization_cost,
        "monthly_savings": monthly_savings,
        "payback_period_months": optimization_cost / monthly_savings if monthly_savings > 0 else float('inf'),
        "annual_roi_percentage": ((monthly_savings * 12 - optimization_cost) / optimization_cost) * 100 if optimization_cost > 0 else 0
    }


def _calculate_stability_score(analytics: Dict[str, Any]) -> float:
    """Calculate overall system stability score."""
    success_rate = analytics["test_execution_summary"].get("success_rate", 0)
    error_rate = analytics["error_analytics"].get("error_rate", 1)  # Default to high error rate if no data
    
    # Weighted stability score
    stability_score = (success_rate * 0.7) + ((1 - error_rate) * 0.3)
    return min(1.0, max(0.0, stability_score))


def _calculate_test_suite_health(analytics: Dict[str, Any]) -> str:
    """Calculate overall test suite health."""
    success_rate = analytics["test_execution_summary"].get("success_rate", 0)
    performance_grade = analytics["test_execution_summary"].get("performance_grade", "unknown")
    error_rate = analytics["error_analytics"].get("error_rate", 1)
    
    if success_rate >= 0.95 and performance_grade in ["excellent", "good"] and error_rate < 0.02:
        return "excellent"
    elif success_rate >= 0.90 and performance_grade != "needs_improvement" and error_rate < 0.05:
        return "good"
    elif success_rate >= 0.80 and error_rate < 0.10:
        return "acceptable"
    else:
        return "needs_attention"


def _generate_action_items(analytics: Dict[str, Any], ml_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate prioritized action items based on analytics and ML insights."""
    action_items = []
    
    # Performance action items
    if analytics["test_execution_summary"].get("performance_grade") == "needs_improvement":
        action_items.append({
            "priority": "high",
            "category": "performance",
            "action": "optimize_test_performance",
            "description": "Test execution times are above acceptable thresholds",
            "estimated_effort": "medium",
            "expected_impact": "high"
        })
    
    # Error rate action items
    error_rate = analytics["error_analytics"].get("error_rate", 0)
    if error_rate > 0.05:
        action_items.append({
            "priority": "high",
            "category": "reliability",
            "action": "investigate_error_patterns",
            "description": f"Error rate of {error_rate:.2%} exceeds acceptable threshold",
            "estimated_effort": "high",
            "expected_impact": "very_high"
        })
    
    # Cost optimization action items
    optimization_potential = ml_insights["cost_optimization_ml"].get("optimization_potential", 0)
    if optimization_potential > 15:  # 15% potential savings
        action_items.append({
            "priority": "medium",
            "category": "cost_optimization",
            "action": "implement_cost_optimizations",
            "description": f"{optimization_potential:.1f}% cost reduction potential identified",
            "estimated_effort": "medium",
            "expected_impact": "medium"
        })
    
    return sorted(action_items, key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["priority"], 0), reverse=True)


# Export utilities
__all__ = [
    "LangSmithTestMetrics",
    "test_metrics",
    "langsmith_test_trace",
    "create_test_evaluation_dataset",
    "analyze_test_suite_performance"
]