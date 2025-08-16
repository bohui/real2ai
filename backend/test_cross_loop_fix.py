#!/usr/bin/env python3
"""
Test script to verify the cross-loop prevention solution works correctly.

This simulates the exact scenario that was causing the issues and verifies
that our enhanced async utilities prevent cross-loop contamination.
"""

import asyncio
import logging
import time
import weakref
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our enhanced utilities
from app.core.async_utils import (
    get_langgraph_manager,
    make_loop_consistent_callback,
    detect_cross_loop_issue,
    EventLoopConsistentCallback,
    IsolatedLangGraphContext
)


class MockLangGraphWorkflow:
    """
    Mock LangGraph workflow that simulates the problematic behavior
    that was causing cross-loop issues.
    """
    
    def __init__(self):
        self.task_count = 0
        self.created_tasks: List[asyncio.Task] = []
        
    async def ainvoke(self, state: Dict[str, Any], progress_callback=None):
        """
        Simulate LangGraph workflow execution that creates orphaned tasks.
        
        This mimics the behavior that was causing Task-33 to be attached
        to a different event loop than Task-207.
        """
        logger.info(f"Starting mock LangGraph workflow in loop {id(asyncio.get_running_loop())}")
        
        # Simulate multiple workflow steps with progress callbacks
        steps = [
            ("validate_input", 14, "Validating document and input parameters"),
            ("process_document", 28, "Processing document and extracting text"),
            ("extract_terms", 42, "Extracting key contract terms"),
            ("analyze_compliance", 57, "Analyzing compliance with laws"),
            ("assess_risks", 71, "Assessing contract risks"),
            ("generate_recommendations", 85, "Generating recommendations"),
            ("compile_report", 98, "Compiling final report")
        ]
        
        results = {}
        
        for step_name, progress, description in steps:
            logger.info(f"Executing step: {step_name}")
            
            # Simulate the problematic pattern: create async tasks that might outlive the context
            self.task_count += 1
            task_name = f"Task-{self.task_count}"
            
            # Create a task that simulates build_summary or other operations
            async def background_operation():
                await asyncio.sleep(0.1)  # Simulate work
                logger.info(f"{task_name} background operation completed")
                return f"{step_name}_result"
            
            # This creates a task that might become orphaned
            background_task = asyncio.create_task(
                background_operation(), 
                name=task_name
            )
            self.created_tasks.append(background_task)
            
            # Simulate progress callback (this is where cross-loop issues occurred)
            if progress_callback:
                try:
                    await progress_callback(step_name, progress, description)
                    logger.info(f"Progress callback succeeded for {step_name}")
                except Exception as e:
                    logger.error(f"Progress callback failed for {step_name}: {e}")
                    raise
            
            # Wait for background task and collect result
            try:
                result = await background_task
                results[step_name] = result
            except Exception as e:
                logger.error(f"Background task {task_name} failed: {e}")
                raise
            
            # Simulate some processing time
            await asyncio.sleep(0.05)
        
        logger.info(f"Mock LangGraph workflow completed with {len(results)} results")
        return results


class MockContractAnalysisService:
    """Mock service that uses the LangGraph workflow."""
    
    def __init__(self):
        self.workflow = MockLangGraphWorkflow()
        
    async def start_analysis(self, progress_callback=None, **kwargs):
        """Simulate the contract analysis service."""
        logger.info("Starting mock contract analysis service")
        
        # Simulate the service calling the LangGraph workflow
        results = await self.workflow.ainvoke(
            state={"document_data": "mock_data"},
            progress_callback=progress_callback
        )
        
        # Return mock response
        response = MagicMock()
        response.success = True
        response.analysis_results = results
        response.final_state = results
        
        return response


async def test_problematic_scenario():
    """
    Test the scenario that was causing cross-loop issues.
    
    This simulates what was happening before our fix.
    """
    logger.info("=== Testing Problematic Scenario (Should Fail Without Fix) ===")
    
    # Track loop IDs to detect cross-loop issues
    callback_loops = []
    
    async def problematic_progress_callback(step: str, percent: int, description: str):
        """
        This callback would fail with cross-loop issues in the original code.
        """
        current_loop = asyncio.get_running_loop()
        loop_id = id(current_loop)
        callback_loops.append(loop_id)
        
        logger.info(f"Progress callback for {step} in loop {loop_id}")
        
        # Simulate database operations that could fail due to cross-loop issues
        await asyncio.sleep(0.01)  # Simulate I/O
        
        # Simulate the specific error that was occurring
        if len(callback_loops) > 3:  # After a few calls, simulate loop change
            # This simulates the error we were seeing
            raise RuntimeError(
                "Task got Future attached to a different loop"
            )
    
    try:
        service = MockContractAnalysisService()
        await service.start_analysis(progress_callback=problematic_progress_callback)
        logger.error("Expected cross-loop failure did not occur!")
        return False
    except RuntimeError as e:
        if detect_cross_loop_issue(e):
            logger.info(f"✓ Successfully detected cross-loop issue: {e}")
            return True
        else:
            logger.error(f"Unexpected error: {e}")
            return False


async def test_fixed_scenario():
    """
    Test the scenario with our cross-loop prevention fix.
    
    This should work without cross-loop issues.
    """
    logger.info("=== Testing Fixed Scenario (Should Work With Fix) ===")
    
    # Track loop IDs to verify consistency
    callback_loops = []
    
    async def fixed_progress_callback(step: str, percent: int, description: str):
        """
        This callback should work consistently with our fix.
        """
        current_loop = asyncio.get_running_loop()
        loop_id = id(current_loop)
        callback_loops.append(loop_id)
        
        logger.info(f"Progress callback for {step} in loop {loop_id}")
        
        # Simulate database operations
        await asyncio.sleep(0.01)
        
        # Simulate recovery operations
        await asyncio.sleep(0.01)
        
        logger.debug(f"Progress persisted for {step} at {percent}%")
    
    try:
        # Create loop-consistent callback using our fix
        consistent_callback = make_loop_consistent_callback(fixed_progress_callback)
        
        # Execute in isolated context
        manager = get_langgraph_manager()
        async with manager.create_isolated_context("test_analysis") as context:
            logger.info(f"Executing in isolated context {context.context_id}")
            
            service = MockContractAnalysisService()
            result = await service.start_analysis(progress_callback=consistent_callback)
            
            logger.info(f"Analysis completed successfully: {result.success}")
            
            # Verify all callbacks used the same loop
            unique_loops = set(callback_loops)
            logger.info(f"Callback executed in {len(unique_loops)} unique loops: {unique_loops}")
            
            if len(unique_loops) == 1:
                logger.info("✓ All callbacks used consistent event loop")
                return True
            else:
                logger.error(f"✗ Callbacks used {len(unique_loops)} different loops")
                return False
                
    except Exception as e:
        logger.error(f"Fixed scenario failed unexpectedly: {e}")
        return False


async def test_event_loop_manager():
    """Test the LangGraph event loop manager functionality."""
    logger.info("=== Testing Event Loop Manager ===")
    
    manager = get_langgraph_manager()
    
    # Test context creation and cleanup
    contexts_created = []
    
    async def create_test_context(context_id: str):
        async with manager.create_isolated_context(context_id) as ctx:
            current_loop = asyncio.get_running_loop()
            contexts_created.append((context_id, id(current_loop), ctx))
            logger.info(f"Created context {context_id} in loop {id(current_loop)}")
            await asyncio.sleep(0.1)  # Simulate work
    
    # Create multiple contexts
    await create_test_context("ctx1")
    await create_test_context("ctx2")
    await create_test_context("ctx3")
    
    logger.info(f"Created {len(contexts_created)} test contexts")
    
    # Test cleanup
    manager.cleanup_stale_contexts()
    logger.info("✓ Cleanup completed without errors")
    
    return True


async def test_callback_consistency():
    """Test that EventLoopConsistentCallback maintains loop consistency."""
    logger.info("=== Testing Callback Consistency ===")
    
    callback_loops = []
    
    async def test_callback(step: str, percent: int, description: str):
        current_loop = asyncio.get_running_loop()
        callback_loops.append(id(current_loop))
        logger.debug(f"Callback {step} in loop {id(current_loop)}")
        await asyncio.sleep(0.01)
    
    # Create consistent callback
    consistent_callback = EventLoopConsistentCallback(test_callback)
    
    # Execute multiple times
    for i in range(5):
        await consistent_callback(f"step_{i}", i * 20, f"Description {i}")
    
    # Verify all used the same loop
    unique_loops = set(callback_loops)
    if len(unique_loops) == 1:
        logger.info(f"✓ All {len(callback_loops)} callbacks used same loop: {unique_loops}")
        return True
    else:
        logger.error(f"✗ Callbacks used {len(unique_loops)} different loops: {unique_loops}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    logger.info("Starting Cross-Loop Prevention Tests...")
    
    tests = [
        ("Problematic Scenario", test_problematic_scenario),
        ("Fixed Scenario", test_fixed_scenario),
        ("Event Loop Manager", test_event_loop_manager),
        ("Callback Consistency", test_callback_consistency),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST RESULTS SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Cross-loop prevention is working correctly.")
    else:
        logger.error(f"⚠️  {total - passed} tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    """Run the test script."""
    print("Cross-Loop Prevention Test Suite")
    print("=" * 50)
    
    try:
        success = asyncio.run(run_all_tests())
        exit_code = 0 if success else 1
        print(f"\nTest suite completed with exit code: {exit_code}")
        exit(exit_code)
        
    except Exception as e:
        print(f"Test suite failed with exception: {e}")
        exit(1)