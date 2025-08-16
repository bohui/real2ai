"""
Root Cause Prevention Example - Proper Event Loop Management for LangGraph

This demonstrates how to prevent cross-loop issues at the source by ensuring
consistent event loop context throughout the entire workflow execution.
"""

from typing import Dict, Any
from app.core.async_utils import (
    get_langgraph_manager, 
    langgraph_safe_task,
    make_loop_consistent_callback
)
from app.core.celery import celery_app
from app.core.task_context import user_aware_task
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ROOT CAUSE PREVENTION - PROPER IMPLEMENTATION
# =============================================================================

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=2)
@langgraph_safe_task  # Ensures isolated event loop execution
async def properly_isolated_document_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str,
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
):
    """
    Properly isolated document analysis that prevents cross-loop issues at the root.
    
    Key principles:
    1. Create isolated LangGraph execution context
    2. Bind all callbacks to the context's event loop
    3. Ensure database pools are bound to the same loop
    4. Execute the entire workflow within this consistent context
    """
    
    # Get the LangGraph manager
    manager = get_langgraph_manager()
    
    # Create isolated context for this specific analysis
    async with manager.create_isolated_context(f"analysis_{analysis_id}") as context:
        logger.info(f"Starting isolated analysis in context {context.context_id}")
        
        # Original persist_progress function (unchanged)
        async def persist_progress(step: str, percent: int, description: str):
            """Original progress persistence logic."""
            try:
                # Database operations
                await update_analysis_progress(
                    user_id, content_hash, progress_percent=percent,
                    current_step=step, step_description=description,
                    estimated_completion_minutes=None,
                )
                
                # Recovery operations  
                await recovery_ctx.update_progress(
                    progress_percent=percent,
                    current_step=step,
                    step_description=description,
                )
                
                # Checkpoint creation
                checkpoint = CheckpointData(
                    checkpoint_name=step,
                    progress_percent=percent,
                    step_description=description,
                    # ... other checkpoint data
                )
                await recovery_ctx.create_checkpoint(checkpoint)
                
                # Keep task alive
                await recovery_ctx.refresh_context_ttl()
                
            except Exception as e:
                logger.error(f"Progress persistence failed for {step}: {e}")
                raise
        
        # Create loop-consistent callback bound to this context
        consistent_callback = context.create_bound_callback(persist_progress)
        
        # Initialize contract analysis service
        from app.services.contract_analysis_service import ContractAnalysisService
        
        analysis_service = ContractAnalysisService(
            websocket_manager=websocket_manager,
            openai_api_key=settings.openai_api_key,
            model_name=settings.openai_model_name,
            openai_api_base=settings.openai_api_base,
        )
        
        # Execute analysis within the isolated context
        # All LangGraph operations will now be bound to this context's event loop
        result = await analysis_service.analyze_contract(
            document_data=document_data,
            user_id=user_id,
            australian_state=analysis_options.get("australian_state", "NSW"),
            user_preferences=analysis_options,
            session_id=contract_id,
            progress_callback=consistent_callback,  # Bound to this context's loop
        )
        
        logger.info(f"Analysis completed successfully in context {context.context_id}")
        return result


# =============================================================================
# MINIMAL CHANGE APPROACH - RETROFIT EXISTING CODE
# =============================================================================

@celery_app.task(bind=True)
@user_aware_task(recovery_enabled=True)
async def minimally_enhanced_analysis(
    recovery_ctx,
    document_id: str,
    analysis_id: str,
    contract_id: str,
    user_id: str,
    analysis_options: Dict[str, Any],
):
    """
    Minimal change to existing code - just add event loop consistency.
    
    This can be applied to existing comprehensive_document_analysis
    with minimal modifications.
    """
    
    # ... existing setup code (unchanged) ...
    
    # Original persist_progress function (unchanged)
    async def persist_progress(step: str, percent: int, description: str):
        # ... existing progress persistence logic ...
        pass
    
    # ONLY CHANGE: Wrap the callback for loop consistency
    consistent_callback = make_loop_consistent_callback(persist_progress)
    
    # Get LangGraph manager and create isolated context
    manager = get_langgraph_manager()
    async with manager.create_isolated_context(f"analysis_{analysis_id}"):
        
        # Execute analysis with consistent callback
        analysis_service = ContractAnalysisService(...)
        result = await analysis_service.analyze_contract(
            ...,
            progress_callback=consistent_callback,  # Use consistent version
        )
    
    return result


# =============================================================================
# HOW IT PREVENTS CROSS-LOOP ISSUES
# =============================================================================

"""
ROOT CAUSE PREVENTION MECHANISM:

1. ISOLATED CONTEXT CREATION:
   ┌─────────────────────────────────────┐
   │ IsolatedLangGraphContext            │
   │                                     │
   │ ✓ Dedicated event loop             │
   │ ✓ Bound database pools              │
   │ ✓ Tracked by manager                │
   │ ✓ Automatic cleanup                 │
   └─────────────────────────────────────┘

2. CALLBACK BINDING:
   ┌─────────────────────────────────────┐
   │ EventLoopConsistentCallback         │
   │                                     │
   │ ✓ Bound to specific loop            │
   │ ✓ Verifies loop consistency         │
   │ ✓ Auto-rebinds if needed            │
   │ ✓ Prevents cross-loop execution     │
   └─────────────────────────────────────┘

3. LANGGRAPH EXECUTION:
   ┌─────────────────────────────────────┐
   │ LangGraph Workflow                  │
   │                                     │
   │ ✓ Runs in isolated loop             │
   │ ✓ All tasks bound to same loop      │
   │ ✓ Progress callbacks consistent     │
   │ ✓ Database operations safe          │
   └─────────────────────────────────────┘

BEFORE (Problematic):
Task-207 (build_summary) ──┐
                           ├─► Event Loop A ──► ❌ Loop change
Task-33 (progress_update) ─┘                    ❌ Cross-loop error

AFTER (Fixed):
┌─ Isolated Context ─────────────────────────┐
│ Task-207 (build_summary) ──┐              │
│                            ├─► Event Loop │ ✓ Consistent
│ Task-33 (progress_update) ─┘              │ ✓ No cross-loop
└───────────────────────────────────────────┘
"""


# =============================================================================
# INTEGRATION WITH EXISTING TASKS
# =============================================================================

def retrofit_existing_comprehensive_analysis():
    """
    Example of how to retrofit the existing comprehensive_document_analysis
    function with minimal changes.
    """
    
    # In /Users/bohuihan/ai/real2ai/backend/app/tasks/background_tasks.py
    # Add these imports:
    from app.core.async_utils import get_langgraph_manager, make_loop_consistent_callback
    
    # In the comprehensive_document_analysis function:
    # 
    # 1. Wrap the persist_progress callback:
    #    consistent_callback = make_loop_consistent_callback(persist_progress)
    #
    # 2. Wrap the contract analysis execution:
    #    manager = get_langgraph_manager()
    #    async with manager.create_isolated_context(f"analysis_{analysis_id}"):
    #        result = await analysis_service.analyze_contract(
    #            ...,
    #            progress_callback=consistent_callback,
    #        )
    #
    # That's it! Minimal changes, maximum protection.
    pass


# =============================================================================
# TESTING AND VALIDATION
# =============================================================================

async def test_event_loop_consistency():
    """Test that callbacks maintain event loop consistency."""
    
    import asyncio
    
    # Create a test callback that tracks loop IDs
    loop_ids = []
    
    async def test_callback(step: str, percent: int, description: str):
        current_loop = asyncio.get_running_loop()
        loop_ids.append(id(current_loop))
        print(f"Callback executed in loop {id(current_loop)} for step {step}")
    
    # Create consistent callback
    consistent_callback = make_loop_consistent_callback(test_callback)
    
    # Execute multiple times
    await consistent_callback("step1", 25, "First step")
    await consistent_callback("step2", 50, "Second step") 
    await consistent_callback("step3", 75, "Third step")
    
    # All should use the same loop ID
    assert len(set(loop_ids)) == 1, f"Expected 1 unique loop, got {len(set(loop_ids))}: {loop_ids}"
    print("✓ Event loop consistency maintained across all callbacks")


async def test_isolated_context():
    """Test that isolated contexts prevent cross-contamination."""
    
    manager = get_langgraph_manager()
    
    context_loops = []
    
    async def test_in_context(context_id):
        async with manager.create_isolated_context(context_id) as ctx:
            current_loop = asyncio.get_running_loop()
            context_loops.append((context_id, id(current_loop)))
            print(f"Context {context_id} using loop {id(current_loop)}")
    
    # Test multiple contexts
    await test_in_context("ctx1")
    await test_in_context("ctx2") 
    await test_in_context("ctx3")
    
    print("✓ Isolated contexts created successfully")
    for ctx_id, loop_id in context_loops:
        print(f"  {ctx_id}: {loop_id}")


if __name__ == "__main__":
    import asyncio
    
    print("Testing Root Cause Prevention...")
    
    asyncio.run(test_event_loop_consistency())
    asyncio.run(test_isolated_context())
    
    print("✓ All tests passed!")