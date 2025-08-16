#!/usr/bin/env python3
"""
Test script to demonstrate different isolation approaches for LangGraph execution.

This script shows the difference between:
1. No isolation (original approach)
2. Context-based isolation (current implementation) 
3. Forced thread isolation (new implementation)
4. Process-based isolation (nuclear option)

Run this to verify that isolation is working correctly.
"""

import asyncio
import logging
import threading
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_isolation_approaches():
    """Test different isolation approaches."""
    
    logger.info("=== Testing LangGraph Isolation Approaches ===")
    
    # Import here to ensure we can run this test
    try:
        from app.core.async_utils import (
            get_langgraph_manager, 
            make_loop_consistent_callback,
            execute_langgraph_in_process
        )
    except ImportError as e:
        logger.error(f"Failed to import isolation utilities: {e}")
        return
    
    # Test data
    test_workflow_config = {
        'user_id': 'test_user',
        'session_id': 'test_session', 
        'document_data': {'content': 'test document'},
        'australian_state': 'NSW',
        'user_preferences': {},
        'user_type': 'buyer'
    }
    
    # Get baseline info
    main_thread = threading.current_thread()
    main_pid = os.getpid()
    main_loop = asyncio.get_running_loop()
    main_loop_id = id(main_loop)
    
    logger.info(f"BASELINE - Thread: {main_thread.name} ({main_thread.ident}), PID: {main_pid}, Loop: {main_loop_id}")
    
    # Test 1: Process Isolation (nuclear option)
    logger.info("\n=== TEST 1: Process Isolation ===")
    try:
        process_result = await execute_langgraph_in_process(
            workflow_config=test_workflow_config,
            context_id="test_process_isolation"
        )
        logger.info(f"Process isolation result: {process_result.get('execution_mode')} - Success: {process_result.get('success')}")
    except Exception as e:
        logger.error(f"Process isolation failed: {e}")
    
    # Test 2: Forced Thread Isolation
    logger.info("\n=== TEST 2: Forced Thread Isolation ===")
    try:
        manager = get_langgraph_manager()
        
        async def mock_analysis():
            """Mock contract analysis function."""
            current_thread = threading.current_thread()
            current_pid = os.getpid()
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
            
            logger.info(f"FORCED-THREAD - Thread: {current_thread.name} ({current_thread.ident}), PID: {current_pid}, Loop: {current_loop_id}")
            
            # Verify we're in a different thread
            if current_thread.ident != main_thread.ident:
                logger.info("✅ SUCCESS: Forced thread isolation achieved!")
            else:
                logger.error("❌ FAILED: No thread isolation!")
            
            # Verify we're in a different loop
            if current_loop_id != main_loop_id:
                logger.info("✅ SUCCESS: Event loop isolation achieved!")
            else:
                logger.error("❌ FAILED: No event loop isolation!")
            
            # Simulate some async work
            await asyncio.sleep(0.1)
            
            return {
                'success': True,
                'execution_mode': 'forced_thread_isolated',
                'thread_isolated': current_thread.ident != main_thread.ident,
                'loop_isolated': current_loop_id != main_loop_id
            }
        
        thread_result = await manager.execute_in_isolated_thread(
            mock_analysis,
            context_id="test_thread_isolation"
        )
        logger.info(f"Thread isolation result: {thread_result}")
        
    except Exception as e:
        logger.error(f"Forced thread isolation failed: {e}")
    
    # Test 3: Context Isolation (current approach)
    logger.info("\n=== TEST 3: Context Isolation ===")
    try:
        manager = get_langgraph_manager()
        
        async with manager.create_isolated_context("test_context_isolation") as context:
            context_thread = threading.current_thread()
            context_pid = os.getpid()
            context_loop = asyncio.get_running_loop()
            context_loop_id = id(context_loop)
            
            logger.info(f"CONTEXT - Thread: {context_thread.name} ({context_thread.ident}), PID: {context_pid}, Loop: {context_loop_id}")
            logger.info(f"Context created new loop: {context.created_new_loop}")
            
            # Check isolation
            if context_thread.ident != main_thread.ident:
                logger.info("✅ SUCCESS: Context thread isolation achieved!")
            else:
                logger.error("❌ FAILED: No context thread isolation!")
            
            if context_loop_id != main_loop_id:
                logger.info("✅ SUCCESS: Context event loop isolation achieved!")
            else:
                logger.error("❌ FAILED: No context event loop isolation!")
                
    except Exception as e:
        logger.error(f"Context isolation failed: {e}")
    
    # Test 4: No Isolation (original approach)
    logger.info("\n=== TEST 4: No Isolation (Original) ===")
    
    no_isolation_thread = threading.current_thread()
    no_isolation_pid = os.getpid()
    no_isolation_loop = asyncio.get_running_loop()
    no_isolation_loop_id = id(no_isolation_loop)
    
    logger.info(f"NO-ISOLATION - Thread: {no_isolation_thread.name} ({no_isolation_thread.ident}), PID: {no_isolation_pid}, Loop: {no_isolation_loop_id}")
    
    # This should be the same as baseline
    if no_isolation_thread.ident == main_thread.ident and no_isolation_loop_id == main_loop_id:
        logger.info("✅ EXPECTED: No isolation - same thread and loop as baseline")
    else:
        logger.error("❌ UNEXPECTED: Thread/loop changed without isolation!")
    
    logger.info("\n=== Isolation Test Summary ===")
    logger.info("Process isolation: Completely separate process (strongest isolation)")
    logger.info("Forced thread isolation: Separate thread with new event loop")
    logger.info("Context isolation: May or may not create separate thread (depends on decorator)")
    logger.info("No isolation: Same thread and event loop (original behavior)")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_isolation_approaches())