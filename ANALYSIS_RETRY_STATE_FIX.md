# Analysis Retry State Management Fix

## Problem Summary

**Issue**: When a contract analysis fails at 42% progress with "extract_terms_failed" status and user clicks retry, the progress unexpectedly resets to 5% with "queued" status instead of maintaining progress continuity from the failure point.

## Root Cause Analysis

### **1. Where Progress Resets**
The issue occurs because the backend creates a **completely new analysis task** when retrying, rather than resuming the existing one:

**Flow**:
1. Analysis fails at 42% → `extract_terms_failed` 
2. User clicks retry → Frontend calls `triggerAnalysisRetry()`
3. Backend `handle_retry_analysis_request()` → Calls `_dispatch_analysis_task()`
4. New background task starts → **Always** sends "queued" at 5% progress
5. Progress jumps from 42% → 5%

### **2. Backend Issues**
- **WebSocket Handler** (`websockets.py` lines 798-936): Creates new task instead of resuming
- **Background Task** (`background_tasks.py` lines 245-272): Always starts with "queued" at 5% regardless of retry context
- **Resume Logic Ignored**: The `resume_from_step` parameter is detected but not used for progress continuity

### **3. Frontend Issues** 
- **State Management** (`analysisStore.ts` lines 367-371): Clears `retryInFlight` flag on any progress update, even when progress decreases
- **No Validation**: Frontend doesn't validate that retry progress should advance, not reset

## Complete Solution

### **Frontend Fixes Applied**

**File**: `/Users/bohuihan/ai/real2ai/frontend/src/store/analysisStore.ts`

**Changes**: Modified progress update logic in 3 locations to preserve retry state when progress resets:

```typescript
// Before: Always cleared retryInFlight on any progress
retryInFlight: prev.retryInFlight ? false : prev.retryInFlight,

// After: Only clear retryInFlight when progress actually advances
const isRetryProgressing = prev.retryInFlight && 
  prev.analysisProgress && 
  progressData.progress_percent >= prev.analysisProgress.progress_percent;

const shouldClearRetryFlag = prev.retryInFlight && 
  (isRetryProgressing || progressData.progress_percent > 10);

retryInFlight: shouldClearRetryFlag ? false : prev.retryInFlight,
```

**Locations Fixed**:
- Lines 363-381: Document WebSocket handler
- Lines 648-666: Contract WebSocket handler  
- Lines 952-967: `updateProgress()` method

### **Backend Fixes Applied**

**File**: `/Users/bohuihan/ai/real2ai/backend/app/tasks/background_tasks.py`

**Changes**: Modified task startup to respect retry context and preserve progress continuity:

```python
# Before: Always started with "queued" at 5%
await update_analysis_progress(
    user_id, content_hash, 
    progress_percent=5,
    current_step="queued",
    step_description="Queued for AI contract analysis...",
)

# After: Check retry context and preserve progress
is_retry = analysis_options.get("is_retry", False)
resume_from_step = analysis_options.get("resume_from_step")

if is_retry and resume_from_step:
    # Preserve previous progress for retry operations
    previous_progress = latest_progress["data"][0]["progress_percent"] if latest_progress.get("data") else 5
    await update_analysis_progress(
        user_id, content_hash,
        progress_percent=previous_progress,  # Maintain progress level
        current_step="retrying",
        step_description=f"Resuming analysis from {resume_from_step}...",
    )
else:
    # Normal startup: new analysis
    await update_analysis_progress(
        user_id, content_hash,
        progress_percent=5,
        current_step="queued", 
        step_description="Queued for AI contract analysis...",
    )
```

## Expected Behavior After Fix

### **Normal Analysis**
1. Start → "queued" at 5%
2. Processing → Various steps advancing to 100%
3. Complete → Results displayed

### **Retry Operation**  
1. Analysis fails → "extract_terms_failed" at 42%
2. User clicks retry → "retrying" at 42% (progress preserved)
3. Resume processing → Continue from failure point
4. Complete → Results displayed

### **Frontend State Management**
- `retryInFlight` flag only clears when progress actually advances
- Error messages preserved until real progress is made
- Progress continuity maintained across retry operations

## Technical Details

### **Data Flow**
```
Failed Analysis (42%) → Retry Click → Backend Retry Handler → 
New Task with is_retry=true → Progress Preserved at 42% → 
Frontend Receives "retrying" Step → Progress Continuity Maintained
```

### **Key State Variables**
- `retryInFlight`: Tracks active retry operation
- `analysisProgress`: Current progress data
- `retryAvailable`: Whether retry option is available
- `analysisError`: Error message preserved until progress advances

### **Progress Validation Logic**
- **Retry Progressing**: New progress ≥ previous progress
- **Allow Tolerance**: Progress > 10% (handles legitimate restarts)
- **Clear Retry Flag**: Only when confident progress is advancing

## Testing Scenarios

1. **Normal Analysis**: Should start at 5% and progress normally
2. **First Retry**: Should maintain 42% progress and show "retrying" 
3. **Multiple Retries**: Should preserve progress across attempts
4. **Legitimate Restart**: Should handle cases where full restart is needed
5. **Edge Cases**: Handle missing progress data gracefully

## Files Modified

### Frontend
- `/Users/bohuihan/ai/real2ai/frontend/src/store/analysisStore.ts`
  - Lines 363-381: Document WebSocket progress handler
  - Lines 648-666: Contract WebSocket progress handler
  - Lines 952-967: updateProgress method

### Backend  
- `/Users/bohuihan/ai/real2ai/backend/app/tasks/background_tasks.py`
  - Lines 245-272: Task startup progress logic

## Monitoring Points

- **WebSocket Messages**: Verify "retrying" messages at correct progress levels
- **Progress Continuity**: Ensure no unexpected progress resets during retry
- **Error Handling**: Confirm errors preserved until legitimate progress
- **Performance**: Validate retry operations don't cause performance issues

## Future Enhancements

1. **Smart Resume Points**: Resume from actual step boundaries rather than arbitrary progress
2. **Progress Validation**: Server-side validation of progress advancement
3. **Retry Limits**: Implement maximum retry attempts with backoff
4. **User Feedback**: Enhanced UI feedback for retry operations