# Task Recovery System

The task recovery system provides automatic task recovery capabilities for Celery background tasks, ensuring that work is not lost when containers restart.

## Features

- **Automatic Discovery**: Finds interrupted tasks on container startup
- **Smart Recovery**: Multiple recovery strategies (checkpoint resume, clean restart, validation)
- **Progress Preservation**: Checkpointing system to avoid duplicate work
- **User Context Handling**: Maintains authentication context through recovery
- **Monitoring**: Comprehensive health monitoring and alerting

## Usage

### Enable Recovery for Tasks

Use the enhanced `@user_aware_task` decorator with recovery parameters:

```python
@celery_app.task(bind=True)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=25, recovery_priority=2)
async def my_long_running_task(recovery_ctx, self, document_id: str, user_id: str):
    """
    A long-running task with recovery capabilities
    
    Args:
        recovery_ctx: Recovery context for checkpointing (only present if recovery_enabled=True)
        self: Celery task instance
        document_id: Document to process
        user_id: User ID for context
    """
    
    # Update progress and create checkpoints
    await recovery_ctx.update_progress(
        progress_percent=25,
        current_step="processing_phase_1",
        step_description="Extracting data from document"
    )
    
    # Do some work...
    extraction_result = await extract_document_data(document_id)
    
    # Create checkpoint after major work completion
    from app.core.task_recovery import CheckpointData
    checkpoint = CheckpointData(
        checkpoint_name="extraction_complete",
        progress_percent=50,
        step_description="Document extraction completed",
        recoverable_data={
            "extraction_result": extraction_result,
            "document_id": document_id
        },
        database_state={
            "document_status": "extracted"
        }
    )
    await recovery_ctx.create_checkpoint(checkpoint)
    
    # Continue with more work...
    analysis_result = await analyze_document(extraction_result)
    
    return analysis_result
```

### Recovery Parameters

- `recovery_enabled`: Enable automatic recovery (default: False)
- `checkpoint_frequency`: Create checkpoints every N percent progress (optional)
- `recovery_priority`: Priority for recovery (0-10, higher = more important)

### Recovery Context Methods

When `recovery_enabled=True`, your task receives a `recovery_ctx` parameter with these methods:

- `update_progress(progress_percent, current_step, step_description)`: Update task progress
- `create_checkpoint(checkpoint_data)`: Create a recovery checkpoint

## Recovery Strategies

The system automatically selects the best recovery strategy:

### 1. Checkpoint Resume
- **When**: Task has valid checkpoints and significant progress (>25%)
- **Action**: Resumes from the last checkpoint
- **Benefits**: Saves the most time by avoiding duplicate work

### 2. Clean Restart
- **When**: No valid checkpoints or minimal progress
- **Action**: Restarts task but skips any completed work
- **Benefits**: Ensures clean state while avoiding unnecessary re-processing

### 3. Validation Only
- **When**: Task appears nearly complete (>95% progress)
- **Action**: Validates if task actually completed successfully
- **Benefits**: Handles cases where task completed but state wasn't updated

## Monitoring

### Health Endpoints

- `GET /health/recovery` - Recovery system health status
- `GET /health/recovery/metrics` - Detailed recovery metrics
- `GET /health/detailed` - Includes recovery status in overall health

### Example Health Response

```json
{
  "overall_health": "healthy",
  "recovery_queue_depth": 2,
  "recent_failure_count": 0,
  "orphaned_task_count": 0,
  "stuck_task_count": 0,
  "timestamp": "2024-01-07T15:30:00Z"
}
```

### Metrics Response

```json
{
  "task_state_distribution": {
    "completed": 150,
    "processing": 3,
    "failed": 2,
    "orphaned": 0
  },
  "recovery_success_rate_24h": 95.5,
  "total_recovery_attempts_24h": 22,
  "successful_recoveries_24h": 21,
  "average_recovery_time_seconds": 45.2
}
```

## Container Startup Process

When a container starts:

1. **System Health Check** - Validates database and broker connectivity
2. **Task Discovery** - Finds tasks that were interrupted (processing/orphaned states)
3. **Validation** - Checks if tasks can be recovered and aren't already complete
4. **Recovery Execution** - Runs recovery strategies in priority order
5. **Monitoring Setup** - Starts background health monitoring

## Database Schema

The recovery system adds these tables:

- `task_registry` - Comprehensive task state tracking
- `task_checkpoints` - Recovery checkpoints with state data
- `recovery_queue` - Recovery orchestration and scheduling

Existing tables are enhanced with recovery tracking fields.

## Best Practices

### For Task Authors

1. **Create Meaningful Checkpoints**: Checkpoint after major work phases
2. **Include Recovery Data**: Store all data needed to resume processing
3. **Handle Recovery Flag**: Check for `_recovery_checkpoint` in kwargs
4. **Update Progress Regularly**: Use `recovery_ctx.update_progress()` frequently
5. **Make Operations Idempotent**: Ensure operations can be safely repeated

### For Operations

1. **Monitor Health Endpoints**: Set up alerting on recovery system health
2. **Review Recovery Metrics**: Track success rates and identify problems
3. **Clean Up Regularly**: Use the cleanup functionality to remove old records
4. **Tune Recovery Settings**: Adjust priorities and frequencies based on usage

### Example Recovery-Aware Task

```python
@celery_app.task(bind=True)
@user_aware_task(recovery_enabled=True, checkpoint_frequency=20, recovery_priority=1)
async def process_large_dataset(recovery_ctx, self, dataset_id: str, user_id: str):
    # Check if this is a recovery
    recovery_checkpoint = self.request.kwargs.get('_recovery_checkpoint')
    skip_to_step = None
    
    if recovery_checkpoint:
        skip_to_step = recovery_checkpoint['checkpoint_name']
        logger.info(f"Resuming from: {skip_to_step}")
    
    # Phase 1: Data Loading
    if not skip_to_step or skip_to_step == "data_loading":
        await recovery_ctx.update_progress(10, "data_loading", "Loading dataset")
        dataset = await load_dataset(dataset_id)
        
        checkpoint = CheckpointData(
            checkpoint_name="data_loaded", 
            progress_percent=25,
            step_description="Dataset loaded successfully",
            recoverable_data={"dataset_size": len(dataset)}
        )
        await recovery_ctx.create_checkpoint(checkpoint)
    else:
        logger.info("Skipping data loading - already completed")
        dataset = await load_dataset(dataset_id)  # Still need the data
    
    # Phase 2: Processing
    if not skip_to_step or skip_to_step in ["data_loading", "processing"]:
        await recovery_ctx.update_progress(50, "processing", "Processing data")
        results = await process_data(dataset)
        
        checkpoint = CheckpointData(
            checkpoint_name="processing_complete",
            progress_percent=75, 
            step_description="Data processing completed",
            recoverable_data={"results": results}
        )
        await recovery_ctx.create_checkpoint(checkpoint)
    else:
        logger.info("Skipping processing - already completed")
        # Load results from checkpoint if available
        if recovery_checkpoint:
            results = recovery_checkpoint['recoverable_data'].get('results')
    
    # Phase 3: Finalization  
    await recovery_ctx.update_progress(90, "finalizing", "Saving results")
    await save_results(results)
    
    return {"status": "completed", "processed_items": len(results)}
```

## Troubleshooting

### Common Issues

1. **Tasks Not Recovering**: Check task registry for entries and validate auto_recovery_enabled
2. **Checkpoint Failures**: Verify recoverable_data is JSON serializable  
3. **Context Issues**: Ensure user authentication context is properly maintained
4. **High Recovery Queue**: Check for stuck tasks or system resource constraints

### Debugging

Check logs for recovery-related messages:
- Container startup recovery sequence
- Individual task recovery attempts
- Checkpoint creation and validation
- Recovery strategy selection

Use health endpoints to monitor system status and identify issues before they become critical.