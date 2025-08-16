"""
Example of how to use Enhanced Async Utils to fix LangGraph cross-loop issues.

This demonstrates the proper integration of the new utilities with existing tasks.
"""

from typing import Dict, Any
from app.core.async_utils import (
    LangGraphEventLoopContext,
    langgraph_safe_task,
    make_resilient_progress_callback
)
from app.core.celery import celery_app
from app.core.task_context import user_aware_task
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENHANCED TASK IMPLEMENTATION
# =============================================================================

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=2)
@langgraph_safe_task  # NEW: Add LangGraph protection
async def enhanced_comprehensive_document_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str,
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
):
    """
    Enhanced version of comprehensive document analysis with cross-loop protection.
    
    Key improvements:
    1. LangGraph event loop context management
    2. Resilient progress callbacks
    3. Automatic retry for cross-loop issues
    4. Better error detection and recovery
    """
    
    # ... existing setup code (user verification, services initialization) ...
    
    async def persist_progress(step: str, percent: int, description: str):
        """
        Original persist_progress function - now will be wrapped for resilience.
        """
        try:
            # 1) Persist user-facing progress (DB + WS/Redis)
            await update_analysis_progress(
                user_id, content_hash, progress_percent=percent,
                current_step=step, step_description=description,
                estimated_completion_minutes=None,
            )
            
            # 2) Update recovery registry progress
            await recovery_ctx.update_progress(
                progress_percent=percent,
                current_step=step,
                step_description=description,
            )
            
            # 3) Create checkpoint and refresh TTL
            # ... existing checkpoint code ...
            
        except Exception as e:
            logger.error(f"Progress persistence failed for {step}: {e}")
            raise
    
    # NEW: Create resilient version of progress callback
    resilient_progress_callback = make_resilient_progress_callback(persist_progress)
    
    # NEW: Execute contract analysis within LangGraph context
    async with LangGraphEventLoopContext() as ctx:
        logger.info("Starting contract analysis with enhanced async protection")
        
        try:
            # Initialize contract analysis service
            from app.services.contract_analysis_service import ContractAnalysisService
            
            analysis_service = ContractAnalysisService(
                websocket_manager=websocket_manager,
                openai_api_key=settings.openai_api_key,
                model_name=settings.openai_model_name,
                openai_api_base=settings.openai_api_base,
            )
            
            # Execute analysis with resilient progress callback
            result = await analysis_service.analyze_contract(
                document_data=document_data,
                user_id=user_id,
                australian_state=analysis_options.get("australian_state", "NSW"),
                user_preferences=analysis_options,
                session_id=contract_id,
                progress_callback=resilient_progress_callback,  # NEW: Use resilient callback
            )
            
            return result
            
        except Exception as e:
            # Enhanced error handling with cross-loop detection
            from app.core.async_utils import detect_cross_loop_issue
            
            if detect_cross_loop_issue(e):
                logger.error(f"Cross-loop issue detected in analysis: {e}")
                # The @langgraph_safe_task decorator will handle retries
                raise
            else:
                logger.error(f"Non-cross-loop error in analysis: {e}")
                raise


# =============================================================================
# ALTERNATIVE: PROGRESSIVE MIGRATION APPROACH
# =============================================================================

@celery_app.task(bind=True)
@user_aware_task(recovery_enabled=True)
async def progressive_enhanced_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str, 
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
):
    """
    Progressive enhancement - gradually add protections without major changes.
    
    This shows how to incrementally improve existing tasks.
    """
    
    # Original persist_progress function (unchanged)
    async def persist_progress(step: str, percent: int, description: str):
        try:
            await update_analysis_progress(user_id, content_hash, ...)
            await recovery_ctx.update_progress(...)
            # ... rest of original logic
        except Exception as e:
            # NEW: Add cross-loop detection
            from app.core.async_utils import detect_cross_loop_issue
            
            if detect_cross_loop_issue(e):
                logger.warning(f"Cross-loop issue detected in step {step}: {e}")
                # Continue with workflow, skip this progress update
                return
            else:
                # Re-raise non-cross-loop errors
                raise
    
    # NEW: Wrap just the LangGraph execution
    async with LangGraphEventLoopContext():
        # Execute contract analysis service
        analysis_service = ContractAnalysisService(...)
        result = await analysis_service.analyze_contract(
            ...,
            progress_callback=persist_progress,  # Keep original callback
        )
    
    return result


# =============================================================================
# MINIMAL CHANGE: JUST FIX PROGRESS CALLBACK
# =============================================================================

def create_protected_progress_callback(original_callback):
    """
    Minimal change approach - just wrap the existing callback.
    
    This can be added to existing code with minimal changes.
    """
    return make_resilient_progress_callback(original_callback)


# Example usage in existing comprehensive_document_analysis:
"""
# In the existing function, change:
async def persist_progress(step: str, percent: int, description: str):
    # ... existing logic ...

# To:
async def persist_progress(step: str, percent: int, description: str):
    # ... existing logic ...

# Then when passing to analysis service:
protected_callback = make_resilient_progress_callback(persist_progress)
result = await analysis_service.analyze_contract(
    ...,
    progress_callback=protected_callback,  # Use protected version
)
"""


# =============================================================================
# TESTING UTILITIES
# =============================================================================

async def test_cross_loop_detection():
    """Test the cross-loop detection functionality."""
    from app.core.async_utils import detect_cross_loop_issue
    
    # Test cases
    test_cases = [
        RuntimeError("Task got Future attached to a different loop"),
        RuntimeError("connection was closed in the middle of operation"), 
        ValueError("Some other error"),
        ConnectionError("Network issue"),
    ]
    
    for exc in test_cases:
        is_cross_loop = detect_cross_loop_issue(exc)
        print(f"Exception: {exc}")
        print(f"Is cross-loop: {is_cross_loop}")
        print()


async def test_resilient_callback():
    """Test the resilient progress callback."""
    call_count = 0
    
    async def failing_callback(step: str, percent: int, description: str):
        nonlocal call_count
        call_count += 1
        
        if call_count <= 2:
            # Simulate cross-loop failure for first 2 calls
            raise RuntimeError("Task got Future attached to a different loop")
        else:
            # Success on 3rd call
            print(f"Success: {step} at {percent}% - {description}")
    
    protected = make_resilient_progress_callback(failing_callback)
    
    # This should succeed after retries
    await protected("test_step", 50, "Testing resilient callback")
    
    print(f"Total calls made: {call_count}")


if __name__ == "__main__":
    import asyncio
    
    print("Testing Enhanced Async Utils...")
    
    asyncio.run(test_cross_loop_detection())
    asyncio.run(test_resilient_callback())
    
    print("Tests completed!")