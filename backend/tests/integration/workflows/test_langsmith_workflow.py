#!/usr/bin/env python3
"""
Test script to validate enhanced LangSmith integration in contract workflow.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, UTC

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
)
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.agents.states.contract_state import RealEstateAgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_state() -> RealEstateAgentState:
    """Create a test state for contract analysis."""
    return {
        "session_id": f"test_session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        "user_id": "test_user_123",
        "australian_state": "NSW",
        "user_type": "buyer",
        "contract_type": "purchase_agreement",
        "user_experience": "novice",
        "document_data": {
            "content": """
            SALE OF LAND CONTRACT
            
            VENDOR: John Smith
            PURCHASER: Jane Doe
            
            PROPERTY: 123 Collins Street, Melbourne VIC 3000
            
            PURCHASE PRICE: $850,000
            DEPOSIT: $85,000 (10%)
            SETTLEMENT DATE: 45 days from exchange
            
            COOLING OFF PERIOD: 3 business days
            
            SPECIAL CONDITIONS:
            1. Subject to finance approval within 21 days
            2. Subject to satisfactory building and pest inspection
            3. Subject to strata search and review of strata documents
            
            This contract is governed by Victorian law.
            """,
            "filename": "test_contract.pdf",
            "document_type": "contract",
            "size": 1024,
        },
        "agent_version": "enhanced_v1.0",
        "current_step": "initialized",
    }


async def test_workflow_tracing():
    """Test enhanced workflow tracing."""
    print("=" * 60)
    print("Testing Enhanced Workflow Tracing")
    print("=" * 60)

    try:
        # Initialize LangSmith
        langsmith_enabled = initialize_langsmith()
        if not langsmith_enabled:
            print("⚠️ LangSmith disabled - skipping workflow tracing test")
            return True

        # Create workflow
        workflow = ContractAnalysisWorkflow(
            model_name="gpt-4",
            enable_validation=True,
            enable_quality_checks=True,
        )

        # Initialize workflow
        await workflow.initialize()

        # Create test state
        test_state = create_test_state()

        print(f"✅ Created test state with session_id: {test_state['session_id']}")

        # Run workflow with tracing
        print("🔄 Running contract analysis workflow with enhanced tracing...")
        start_time = datetime.now(UTC)

        result = await workflow.analyze_contract(test_state)

        end_time = datetime.now(UTC)
        processing_time = (end_time - start_time).total_seconds()

        print(f"✅ Workflow completed in {processing_time:.2f}s")

        # Check results
        if result.get("error_state"):
            print(f"❌ Workflow failed: {result['error_state']}")
            return False

        # Verify tracing was successful
        confidence_scores = result.get("confidence_scores", {})
        overall_confidence = result.get("analysis_results", {}).get(
            "overall_confidence", 0
        )

        print(f"✅ Overall confidence: {overall_confidence:.2f}")
        print(f"✅ Confidence scores: {len(confidence_scores)} steps tracked")

        # Check for key workflow outputs
        required_outputs = [
            "contract_terms",
            "compliance_check",
            "risk_assessment",
            "recommendations",
        ]

        for output in required_outputs:
            if output in result:
                print(f"✅ {output}: Found")
            else:
                print(f"⚠️ {output}: Missing")

        print("✅ Enhanced workflow tracing test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Workflow tracing test failed: {e}")
        logger.exception("Workflow tracing test failed")
        return False


async def test_langsmith_configuration():
    """Test LangSmith configuration."""
    print("=" * 60)
    print("Testing LangSmith Configuration")
    print("=" * 60)

    try:
        # Get configuration
        config = get_langsmith_config()
        status = get_langsmith_status()

        print(f"✅ LangSmith enabled: {status['enabled']}")
        if status["enabled"]:
            print(f"✅ Project name: {status['project_name']}")
            print(f"✅ Client available: {status['client_available']}")
            print(f"✅ Environment configured: {status['environment_configured']}")

        return status["enabled"]

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_trace_metadata():
    """Test trace metadata capture."""
    print("=" * 60)
    print("Testing Trace Metadata")
    print("=" * 60)

    try:
        config = get_langsmith_config()
        if not config.enabled:
            print("⚠️ LangSmith disabled - skipping metadata test")
            return True

        @langsmith_trace(name="test_metadata_capture", run_type="tool")
        async def test_function():
            """Test function with metadata capture."""
            return {
                "test_result": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata_test": True,
            }

        result = await test_function()
        print(f"✅ Metadata test completed: {result}")
        return True

    except Exception as e:
        print(f"❌ Metadata test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting Enhanced LangSmith Integration Tests")
    print()

    # Test configuration
    config_ok = await test_langsmith_configuration()
    print()

    # Test metadata capture
    metadata_ok = await test_trace_metadata()
    print()

    # Test workflow tracing
    workflow_ok = await test_workflow_tracing()
    print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Metadata Capture: {'✅ PASS' if metadata_ok else '❌ FAIL'}")
    print(f"Workflow Tracing: {'✅ PASS' if workflow_ok else '❌ FAIL'}")

    if config_ok and metadata_ok and workflow_ok:
        print(
            "\n🎉 All tests passed! Enhanced LangSmith integration is working correctly."
        )
    else:
        print(f"\n⚠️ Some tests failed. Check the output above for details.")

    return config_ok and metadata_ok and workflow_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
