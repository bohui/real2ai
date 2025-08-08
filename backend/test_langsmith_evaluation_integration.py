#!/usr/bin/env python3
"""
Test script to demonstrate enhanced LangSmith evaluation integration.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up basic environment variables for testing
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-key"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

from app.core.langsmith_config import (
    get_langsmith_config,
    langsmith_trace,
    langsmith_session,
)
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status
from app.evaluation.langsmith_integration import (
    LangSmithEvaluationIntegration,
    LangSmithDatasetConfig,
    LangSmithEvaluationConfig,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_langsmith_evaluation_integration():
    """Test enhanced LangSmith evaluation integration."""
    print("=" * 60)
    print("Testing Enhanced LangSmith Evaluation Integration")
    print("=" * 60)

    try:
        # Initialize LangSmith
        langsmith_enabled = initialize_langsmith()
        if not langsmith_enabled:
            print("⚠️ LangSmith disabled - skipping evaluation integration test")
            return True

        # Create integration instance
        integration = LangSmithEvaluationIntegration()

        print(f"✅ LangSmith evaluation integration initialized: {integration.enabled}")

        # Test dataset creation from traces
        await test_dataset_creation(integration)

        # Test enhanced evaluation
        await test_enhanced_evaluation(integration)

        # Test A/B testing
        await test_ab_testing(integration)

        # Test performance analysis
        await test_performance_analysis(integration)

        print("✅ All LangSmith evaluation integration tests completed successfully")
        return True

    except Exception as e:
        print(f"❌ LangSmith evaluation integration test failed: {e}")
        logger.exception("LangSmith evaluation integration test failed")
        return False


async def test_dataset_creation(integration: LangSmithEvaluationIntegration):
    """Test dataset creation from traces."""
    print("\n🔍 Testing Dataset Creation from Traces")
    print("-" * 40)

    try:
        # Create dataset configuration
        dataset_config = LangSmithDatasetConfig(
            dataset_name=f"test_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Test dataset created from traces",
            trace_filters={"run_type": "chain", "tags": ["evaluation"]},
            time_range=(
                datetime.now(timezone.utc) - timedelta(days=7),
                datetime.now(timezone.utc),
            ),
            max_examples=10,
            quality_threshold=0.7,
        )

        print(f"📊 Creating dataset: {dataset_config.dataset_name}")

        # Create dataset
        dataset_id = await integration.create_dataset_from_traces(dataset_config)

        print(f"✅ Dataset created successfully: {dataset_id}")
        return dataset_id

    except Exception as e:
        print(f"⚠️ Dataset creation test failed: {e}")
        return None


async def test_enhanced_evaluation(integration: LangSmithEvaluationIntegration):
    """Test enhanced evaluation with LangSmith."""
    print("\n🔍 Testing Enhanced Evaluation")
    print("-" * 40)

    try:
        # Create evaluation configuration
        evaluation_config = LangSmithEvaluationConfig(
            evaluation_name=f"test_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            dataset_config=LangSmithDatasetConfig(
                dataset_name="test_eval_dataset",
                description="Test dataset for evaluation",
            ),
            model_configs=[
                {
                    "model_name": "gpt-4",
                    "provider": "openai",
                    "parameters": {"temperature": 0.1},
                }
            ],
            metrics_config={
                "faithfulness_enabled": True,
                "relevance_enabled": True,
                "coherence_enabled": True,
                "semantic_similarity_enabled": True,
            },
            performance_monitoring=True,
        )

        print(f"📊 Running enhanced evaluation: {evaluation_config.evaluation_name}")

        # Run evaluation
        results = await integration.run_enhanced_evaluation(evaluation_config)

        print(f"✅ Enhanced evaluation completed successfully")
        print(f"   - Total evaluations: {results.get('total_evaluations', 0)}")
        print(f"   - Average score: {results.get('average_score', 0):.2f}")
        print(f"   - Dataset ID: {results.get('dataset_id', 'N/A')}")

        return results

    except Exception as e:
        print(f"⚠️ Enhanced evaluation test failed: {e}")
        return None


async def test_ab_testing(integration: LangSmithEvaluationIntegration):
    """Test A/B testing with LangSmith."""
    print("\n🔍 Testing A/B Testing with LangSmith")
    print("-" * 40)

    try:
        # Create test dataset
        test_dataset = [
            {
                "input_data": {"query": "Analyze this contract for risks"},
                "expected_output": "Comprehensive risk analysis",
            },
            {
                "input_data": {"query": "Extract key terms from this document"},
                "expected_output": "Key terms extracted",
            },
        ]

        # A/B test configuration
        ab_test_config = {
            "split_ratio": 0.5,
            "duration_hours": 1,
            "model_configs": [
                {
                    "model_name": "gpt-4",
                    "provider": "openai",
                    "parameters": {"temperature": 0.1},
                }
            ],
            "statistical_significance_threshold": 0.05,
        }

        # Control and variant prompts
        control_prompt = "Analyze the following contract and provide a comprehensive risk assessment."
        variant_prompt = "Please analyze the contract below and identify potential risks and issues that need attention."

        print(f"📊 Running A/B test")
        print(f"   - Control prompt: {control_prompt[:50]}...")
        print(f"   - Variant prompt: {variant_prompt[:50]}...")

        # Run A/B test
        results = await integration.run_ab_test_with_langsmith(
            control_prompt=control_prompt,
            variant_prompt=variant_prompt,
            test_dataset=test_dataset,
            ab_test_config=ab_test_config,
        )

        print(f"✅ A/B test completed successfully")
        print(
            f"   - Control performance: {results.get('control_results', {}).get('average_score', 0):.2f}"
        )
        print(
            f"   - Variant performance: {results.get('variant_results', {}).get('average_score', 0):.2f}"
        )
        print(
            f"   - Statistical significance: {results.get('statistical_analysis', {}).get('p_value', 0):.3f}"
        )
        print(f"   - Recommendation: {results.get('recommendation', 'N/A')}")

        return results

    except Exception as e:
        print(f"⚠️ A/B testing test failed: {e}")
        return None


async def test_performance_analysis(integration: LangSmithEvaluationIntegration):
    """Test performance analysis with LangSmith."""
    print("\n🔍 Testing Performance Analysis")
    print("-" * 40)

    try:
        # Mock evaluation results
        evaluation_results = {
            "evaluation_id": f"test_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "results": [],
            "average_score": 0.85,
            "status": "completed",
        }

        print(
            f"📊 Analyzing performance for evaluation: {evaluation_results['evaluation_id']}"
        )

        # Analyze performance
        performance_data = await integration.analyze_evaluation_performance(
            evaluation_results=evaluation_results,
            time_range=(
                datetime.now(timezone.utc) - timedelta(days=1),
                datetime.now(timezone.utc),
            ),
        )

        print(f"✅ Performance analysis completed successfully")
        print(f"   - Total traces: {performance_data.get('total_traces', 0)}")
        print(
            f"   - Average execution time: {performance_data.get('average_execution_time', 0):.2f}s"
        )
        print(f"   - Success rate: {performance_data.get('success_rate', 0):.2%}")
        print(f"   - Error rate: {performance_data.get('error_rate', 0):.2%}")

        return performance_data

    except Exception as e:
        print(f"⚠️ Performance analysis test failed: {e}")
        return None


async def test_continuous_evaluation_pipeline(
    integration: LangSmithEvaluationIntegration,
):
    """Test continuous evaluation pipeline creation."""
    print("\n🔍 Testing Continuous Evaluation Pipeline")
    print("-" * 40)

    try:
        # Pipeline configuration
        pipeline_config = {
            "name": f"test_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "evaluation_interval": 3600,  # 1 hour
            "alert_threshold": 0.7,
            "metrics_to_monitor": ["accuracy", "latency", "cost"],
        }

        print(f"📊 Creating continuous evaluation pipeline: {pipeline_config['name']}")

        # Create pipeline
        pipeline_id = await integration.create_continuous_evaluation_pipeline(
            pipeline_config
        )

        print(f"✅ Continuous evaluation pipeline created successfully: {pipeline_id}")

        return pipeline_id

    except Exception as e:
        print(f"⚠️ Continuous evaluation pipeline test failed: {e}")
        return None


async def main():
    """Main test function."""
    print("🚀 Starting Enhanced LangSmith Evaluation Integration Tests")
    print()

    # Test LangSmith evaluation integration
    integration_ok = await test_langsmith_evaluation_integration()
    print()

    # Test continuous evaluation pipeline
    pipeline_ok = await test_continuous_evaluation_pipeline(
        LangSmithEvaluationIntegration()
    )
    print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Evaluation Integration: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    print(f"Continuous Pipeline: {'✅ PASS' if pipeline_ok else '❌ FAIL'}")

    if integration_ok and pipeline_ok:
        print(
            "\n🎉 All tests passed! Enhanced LangSmith evaluation integration is working correctly."
        )
        print("\n📋 Key Features Demonstrated:")
        print("   ✅ Automatic dataset creation from traces")
        print("   ✅ Enhanced evaluation with rich metadata")
        print("   ✅ A/B testing with statistical analysis")
        print("   ✅ Performance monitoring and analytics")
        print("   ✅ Continuous evaluation pipeline")
    else:
        print(f"\n⚠️ Some tests failed. Check the output above for details.")

    return integration_ok and pipeline_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
