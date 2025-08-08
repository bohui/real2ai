# Task Recovery Database Schema Design

## Core Recovery Tables

### 1. task_registry (Task State Persistence)
```sql
CREATE TABLE task_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) UNIQUE NOT NULL,  -- Celery task ID
    task_name VARCHAR(255) NOT NULL,       -- Task function name
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Task Arguments and Context
    task_args JSONB NOT NULL DEFAULT '{}',
    task_kwargs JSONB NOT NULL DEFAULT '{}',
    context_key VARCHAR(255),              -- For @user_aware_task context
    
    -- State Management
    current_state VARCHAR(50) NOT NULL DEFAULT 'queued',
    previous_state VARCHAR(50),
    state_history JSONB DEFAULT '[]',      -- State transition log
    
    -- Progress and Checkpoints
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    current_step VARCHAR(255),
    checkpoint_data JSONB DEFAULT '{}',    -- Recoverable state data
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Recovery Metadata
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    recovery_priority INTEGER DEFAULT 0,   -- Higher = more important
    auto_recovery_enabled BOOLEAN DEFAULT TRUE,
    
    -- Result and Error Tracking
    result_data JSONB,
    error_details JSONB,
    
    -- Timing
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    
    -- Auditing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_task_state CHECK (
        current_state IN ('queued', 'started', 'processing', 'checkpoint', 'paused', 
                         'completed', 'failed', 'cancelled', 'recovering', 'partial', 'orphaned')
    )
);
```

### 2. task_checkpoints (Recovery Points)
```sql
CREATE TABLE task_checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE NOT NULL,
    checkpoint_name VARCHAR(255) NOT NULL, -- e.g., "text_extraction_complete"
    
    -- Checkpoint State
    progress_percent INTEGER NOT NULL,
    step_description TEXT,
    recoverable_data JSONB NOT NULL DEFAULT '{}',  -- All data needed to resume
    
    -- Database State Snapshot
    database_state JSONB DEFAULT '{}',     -- Critical DB record IDs and states
    file_state JSONB DEFAULT '{}',         -- File processing status
    
    -- Validation
    checkpoint_hash VARCHAR(255),          -- Integrity check
    is_valid BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. recovery_queue (Recovery Orchestration)
```sql
CREATE TABLE recovery_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE NOT NULL,
    
    -- Recovery Strategy
    recovery_method VARCHAR(100) NOT NULL, -- 'resume_checkpoint', 'restart_clean', 'validate_only'
    recovery_priority INTEGER DEFAULT 0,
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started TIMESTAMP WITH TIME ZONE,
    processing_completed TIMESTAMP WITH TIME ZONE,
    
    -- State
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Results
    recovery_result JSONB,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Enhanced Existing Tables

### analysis_progress (Add Recovery Fields)
```sql
-- Add columns to existing analysis_progress table
ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE;

ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    is_recoverable BOOLEAN DEFAULT TRUE;

ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    recovery_data JSONB DEFAULT '{}';
```

### contract_analyses (Add Recovery Tracking)
```sql
-- Add columns to existing contract_analyses table  
ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE;

ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    processing_resumed_from VARCHAR(255); -- Checkpoint name if resumed

ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    recovery_metadata JSONB DEFAULT '{}';
```

## Indexes and Performance

```sql
-- Critical performance indexes
CREATE INDEX idx_task_registry_state ON task_registry(current_state);
CREATE INDEX idx_task_registry_user_state ON task_registry(user_id, current_state);
CREATE INDEX idx_task_registry_heartbeat ON task_registry(last_heartbeat) WHERE current_state IN ('started', 'processing', 'checkpoint');
CREATE INDEX idx_recovery_queue_scheduled ON recovery_queue(scheduled_for, status);
CREATE INDEX idx_task_checkpoints_task ON task_checkpoints(task_registry_id, created_at DESC);

-- Analysis progress recovery index
CREATE INDEX idx_analysis_progress_recovery ON analysis_progress(task_registry_id) WHERE is_recoverable = TRUE;
```

## Functions and Procedures

### Recovery Discovery Function
```sql
CREATE OR REPLACE FUNCTION discover_recoverable_tasks()
RETURNS TABLE(
    task_id VARCHAR(255),
    task_name VARCHAR(255), 
    user_id UUID,
    current_state VARCHAR(50),
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    recovery_priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tr.task_id,
        tr.task_name,
        tr.user_id,
        tr.current_state,
        tr.last_heartbeat,
        tr.recovery_priority
    FROM task_registry tr
    WHERE tr.auto_recovery_enabled = TRUE
    AND tr.current_state IN ('processing', 'checkpoint', 'partial', 'orphaned')
    AND (
        -- Tasks with old heartbeats (likely crashed)
        tr.last_heartbeat < NOW() - INTERVAL '10 minutes'
        OR 
        -- Explicitly marked as partial/orphaned
        tr.current_state IN ('partial', 'orphaned')
    )
    ORDER BY tr.recovery_priority DESC, tr.updated_at ASC;
END;
$$ LANGUAGE plpgsql;
```

### State Validation Function  
```sql
CREATE OR REPLACE FUNCTION validate_task_recovery(task_registry_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    task_record task_registry%ROWTYPE;
    analysis_record RECORD;
    validation_result JSONB := '{}';
BEGIN
    -- Get task record
    SELECT * INTO task_record FROM task_registry WHERE id = task_registry_uuid;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('valid', false, 'error', 'Task registry record not found');
    END IF;
    
    -- Validate based on task type
    CASE task_record.task_name
        WHEN 'comprehensive_document_analysis' THEN
            -- Check if analysis already completed
            SELECT * INTO analysis_record 
            FROM contract_analyses ca
            WHERE ca.task_registry_id = task_registry_uuid;
            
            IF FOUND AND analysis_record.status = 'completed' THEN
                validation_result := jsonb_build_object(
                    'valid', false,
                    'reason', 'already_completed',
                    'analysis_id', analysis_record.id
                );
            ELSE
                validation_result := jsonb_build_object('valid', true);
            END IF;
            
        ELSE
            validation_result := jsonb_build_object('valid', true);
    END CASE;
    
    RETURN validation_result;
END;
$$ LANGUAGE plpgsql;
```