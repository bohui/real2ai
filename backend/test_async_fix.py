#!/usr/bin/env python3
"""
Test script to validate the async event loop fix for Celery + LangGraph + asyncpg.

This script tests the event loop handling without requiring a full Celery setup.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import our fixed components
from app.core.async_utils import celery_async_task, ensure_async_pool_initialization
from app.database.connection import ConnectionPoolManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockCeleryTask:
    """Mock Celery task to simulate the problematic scenario."""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self._persistent_loop = None
    
    def update_state(self, state: str, meta: Dict[str, Any]):
        """Mock Celery update_state method."""
        logger.info(f"Task {self.task_name} state: {state}, meta: {meta}")


@celery_async_task
async def mock_document_processing_workflow(
    task_self,
    document_id: str,
    user_id: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Mock version of the problematic document processing workflow.
    
    This simulates the same async operations that cause the event loop conflict.
    """
    logger.info(f"Starting mock document processing for {document_id}")
    
    # Update task progress (simulating Celery task)
    task_self.update_state(
        state="PROCESSING",
        meta={
            "status": "Starting document processing",
            "progress": 10,
        }
    )
    
    # Simulate database operations that caused the original error
    try:
        # This would normally cause the "Future attached to different loop" error
        await ensure_async_pool_initialization()
        logger.info("✅ Database pool initialization successful")
        
        # Simulate some async database work
        await asyncio.sleep(0.1)  # Mock database operation
        logger.info("✅ Mock database operations completed")
        
        # Simulate LangGraph workflow execution
        await mock_langgraph_workflow()
        logger.info("✅ Mock LangGraph workflow completed")
        
        task_self.update_state(
            state="PROCESSING",
            meta={
                "status": "Processing completed successfully",
                "progress": 100,
            }
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "processing_time": 0.5,
            "message": "Document processing completed successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Mock document processing failed: {e}")
        task_self.update_state(
            state="FAILURE",
            meta={
                "status": "Processing failed",
                "error": str(e),
                "progress": 0,
            }
        )
        raise


async def mock_langgraph_workflow():
    """
    Mock LangGraph workflow that simulates ainvoke() operations.
    
    This is where the original event loop conflict occurred.
    """
    logger.info("Running mock LangGraph workflow")
    
    # Simulate the workflow steps that involve database calls
    for step in ["fetch_document", "extract_text", "process_diagrams", "generate_summary"]:
        logger.info(f"  Executing workflow step: {step}")
        
        # Each step would normally involve database operations
        await simulate_database_operation()
        
        # Simulate processing time
        await asyncio.sleep(0.05)
    
    logger.info("Mock LangGraph workflow completed")


async def simulate_database_operation():
    """Simulate the database operations that caused the original error."""
    try:
        # This simulates the connection pool access that failed before
        ConnectionPoolManager._ensure_loop_bound()
        
        # Simulate async database call
        await asyncio.sleep(0.01)
        
    except Exception as e:
        logger.error(f"Database operation simulation failed: {e}")
        raise


def test_single_event_loop():
    """Test that our fix ensures single event loop usage."""
    logger.info("🧪 Testing single event loop handling...")
    
    # Create mock task
    mock_task = MockCeleryTask("test_document_processing")
    
    # Test the fixed workflow
    try:
        result = mock_document_processing_workflow(
            mock_task,
            document_id="test-doc-123",
            user_id="test-user-456",
            use_llm=True
        )
        
        logger.info(f"✅ Test completed successfully: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def test_multiple_concurrent_tasks():
    """Test multiple concurrent tasks to ensure no event loop conflicts."""
    logger.info("🧪 Testing multiple concurrent tasks...")
    
    async def run_concurrent_tests():
        tasks = []
        for i in range(3):
            mock_task = MockCeleryTask(f"concurrent_task_{i}")
            task = mock_document_processing_workflow(
                mock_task,
                document_id=f"doc-{i}",
                user_id=f"user-{i}"
            )
            tasks.append(task)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Concurrent task {i} failed: {result}")
            else:
                logger.info(f"✅ Concurrent task {i} succeeded")
                success_count += 1
        
        return success_count == len(tasks)
    
    try:
        return asyncio.run(run_concurrent_tests())
    except Exception as e:
        logger.error(f"❌ Concurrent test setup failed: {e}")
        return False


def main():
    """Run all tests to validate the async event loop fix."""
    logger.info("🚀 Starting async event loop fix validation tests...")
    
    tests = [
        ("Single Event Loop", test_single_event_loop),
        ("Multiple Concurrent Tasks", test_multiple_concurrent_tasks),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info('='*50)
        
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info('='*50)
    
    if passed == total:
        logger.info("🎉 All tests passed! The async event loop fix is working correctly.")
        return 0
    else:
        logger.error("💥 Some tests failed. Please review the event loop handling.")
        return 1


if __name__ == "__main__":
    sys.exit(main())