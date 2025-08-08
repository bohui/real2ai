-- Task Recovery System Migration
-- Adds comprehensive task recovery capabilities with checkpoint support

-- Create task recovery state enum
CREATE TYPE task_state AS ENUM (
    'queued', 'started', 'processing', 'checkpoint', 'paused',
    'completed', 'failed', 'cancelled', 'recovering', 'partial', 'orphaned'
);

-- Create recovery method enum
CREATE TYPE recovery_method AS ENUM (
    'resume_checkpoint', 'restart_clean', 'validate_only', 'manual_intervention'
);

-- Task registry for comprehensive task state tracking
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
    current_state task_state NOT NULL DEFAULT 'queued',
    previous_state task_state,
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task checkpoints for recovery points
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

-- Recovery queue for orchestration
CREATE TABLE recovery_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE NOT NULL,
    
    -- Recovery Strategy
    recovery_method recovery_method NOT NULL DEFAULT 'resume_checkpoint',
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

-- Add recovery tracking to existing analysis_progress table
ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE;

ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    is_recoverable BOOLEAN DEFAULT TRUE;

ALTER TABLE analysis_progress ADD COLUMN IF NOT EXISTS 
    recovery_data JSONB DEFAULT '{}';

-- Add recovery tracking to existing contract_analyses table
ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE;

ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    processing_resumed_from VARCHAR(255); -- Checkpoint name if resumed

ALTER TABLE contract_analyses ADD COLUMN IF NOT EXISTS 
    recovery_metadata JSONB DEFAULT '{}';

-- Performance indexes
CREATE INDEX idx_task_registry_state ON task_registry(current_state);
CREATE INDEX idx_task_registry_user_state ON task_registry(user_id, current_state);
CREATE INDEX idx_task_registry_heartbeat ON task_registry(last_heartbeat) WHERE current_state IN ('started', 'processing', 'checkpoint');
CREATE INDEX idx_task_registry_task_id ON task_registry(task_id);
CREATE INDEX idx_recovery_queue_scheduled ON recovery_queue(scheduled_for, status);
CREATE INDEX idx_task_checkpoints_task ON task_checkpoints(task_registry_id, created_at DESC);
CREATE INDEX idx_analysis_progress_recovery ON analysis_progress(task_registry_id) WHERE is_recoverable = TRUE;

-- Functions for recovery operations

-- Discover recoverable tasks function
CREATE OR REPLACE FUNCTION discover_recoverable_tasks()
RETURNS TABLE(
    registry_id UUID,
    task_id VARCHAR(255),
    task_name VARCHAR(255), 
    user_id UUID,
    current_state task_state,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    recovery_priority INTEGER,
    progress_percent INTEGER,
    current_step VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tr.id,
        tr.task_id,
        tr.task_name,
        tr.user_id,
        tr.current_state,
        tr.last_heartbeat,
        tr.recovery_priority,
        tr.progress_percent,
        tr.current_step
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

-- Validate task recovery function
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
            -- Check if analysis already completed via content_hash
            SELECT ca.*, ca.id as analysis_id INTO analysis_record 
            FROM contract_analyses ca
            WHERE ca.task_registry_id = task_registry_uuid
            OR (ca.content_hash IS NOT NULL AND ca.content_hash = (task_record.task_kwargs->>'analysis_options')::JSONB->>'content_hash');
            
            IF FOUND AND analysis_record.status = 'completed' THEN
                validation_result := jsonb_build_object(
                    'valid', false,
                    'reason', 'already_completed',
                    'analysis_id', analysis_record.analysis_id,
                    'completed_at', analysis_record.updated_at
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

-- Create or update task registry entry
CREATE OR REPLACE FUNCTION upsert_task_registry(
    p_task_id VARCHAR(255),
    p_task_name VARCHAR(255),
    p_user_id UUID,
    p_task_args JSONB DEFAULT '{}',
    p_task_kwargs JSONB DEFAULT '{}',
    p_context_key VARCHAR(255) DEFAULT NULL,
    p_recovery_priority INTEGER DEFAULT 0,
    p_auto_recovery_enabled BOOLEAN DEFAULT TRUE
) RETURNS UUID AS $$
DECLARE
    registry_id UUID;
BEGIN
    INSERT INTO task_registry (
        task_id, task_name, user_id, task_args, task_kwargs, 
        context_key, recovery_priority, auto_recovery_enabled,
        current_state, scheduled_at
    ) VALUES (
        p_task_id, p_task_name, p_user_id, p_task_args, p_task_kwargs,
        p_context_key, p_recovery_priority, p_auto_recovery_enabled,
        'queued', NOW()
    )
    ON CONFLICT (task_id) DO UPDATE SET
        current_state = EXCLUDED.current_state,
        updated_at = NOW()
    RETURNING id INTO registry_id;
    
    RETURN registry_id;
END;
$$ LANGUAGE plpgsql;

-- Update task registry state
CREATE OR REPLACE FUNCTION update_task_registry_state(
    p_task_id VARCHAR(255),
    p_new_state task_state,
    p_progress_percent INTEGER DEFAULT NULL,
    p_current_step VARCHAR(255) DEFAULT NULL,
    p_checkpoint_data JSONB DEFAULT NULL,
    p_error_details JSONB DEFAULT NULL,
    p_result_data JSONB DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    old_state task_state;
    updated_count INTEGER;
BEGIN
    -- Get current state for history
    SELECT current_state INTO old_state FROM task_registry WHERE task_id = p_task_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Update registry with state transition
    UPDATE task_registry SET
        previous_state = old_state,
        current_state = p_new_state,
        progress_percent = COALESCE(p_progress_percent, progress_percent),
        current_step = COALESCE(p_current_step, current_step),
        checkpoint_data = COALESCE(p_checkpoint_data, checkpoint_data),
        error_details = COALESCE(p_error_details, error_details),
        result_data = COALESCE(p_result_data, result_data),
        last_heartbeat = NOW(),
        updated_at = NOW(),
        state_history = state_history || jsonb_build_object(
            'from_state', old_state,
            'to_state', p_new_state,
            'timestamp', NOW(),
            'progress', COALESCE(p_progress_percent, progress_percent)
        ),
        -- Set timestamps based on state
        started_at = CASE 
            WHEN p_new_state = 'started' AND started_at IS NULL THEN NOW()
            ELSE started_at
        END,
        completed_at = CASE 
            WHEN p_new_state IN ('completed', 'failed', 'cancelled') THEN NOW()
            ELSE completed_at
        END
    WHERE task_id = p_task_id;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Create task checkpoint
CREATE OR REPLACE FUNCTION create_task_checkpoint(
    p_task_id VARCHAR(255),
    p_checkpoint_name VARCHAR(255),
    p_progress_percent INTEGER,
    p_step_description TEXT,
    p_recoverable_data JSONB DEFAULT '{}',
    p_database_state JSONB DEFAULT '{}',
    p_file_state JSONB DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    registry_id UUID;
    checkpoint_id UUID;
    checkpoint_hash_value VARCHAR(255);
BEGIN
    -- Get task registry ID
    SELECT id INTO registry_id FROM task_registry WHERE task_id = p_task_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Task registry not found for task_id: %', p_task_id;
    END IF;
    
    -- Create hash for integrity check
    checkpoint_hash_value := encode(digest(
        p_checkpoint_name || p_progress_percent::text || p_recoverable_data::text,
        'sha256'
    ), 'hex');
    
    -- Insert checkpoint
    INSERT INTO task_checkpoints (
        task_registry_id, checkpoint_name, progress_percent, 
        step_description, recoverable_data, database_state, 
        file_state, checkpoint_hash
    ) VALUES (
        registry_id, p_checkpoint_name, p_progress_percent,
        p_step_description, p_recoverable_data, p_database_state,
        p_file_state, checkpoint_hash_value
    ) RETURNING id INTO checkpoint_id;
    
    -- Update task registry with checkpoint state
    PERFORM update_task_registry_state(
        p_task_id, 
        'checkpoint',
        p_progress_percent,
        p_checkpoint_name,
        jsonb_build_object(
            'last_checkpoint', p_checkpoint_name,
            'checkpoint_id', checkpoint_id
        )
    );
    
    RETURN checkpoint_id;
END;
$$ LANGUAGE plpgsql;

-- Get latest checkpoint for task
CREATE OR REPLACE FUNCTION get_latest_checkpoint(p_task_id VARCHAR(255))
RETURNS TABLE(
    checkpoint_id UUID,
    checkpoint_name VARCHAR(255),
    progress_percent INTEGER,
    step_description TEXT,
    recoverable_data JSONB,
    database_state JSONB,
    file_state JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.id,
        tc.checkpoint_name,
        tc.progress_percent,
        tc.step_description,
        tc.recoverable_data,
        tc.database_state,
        tc.file_state,
        tc.created_at
    FROM task_checkpoints tc
    JOIN task_registry tr ON tr.id = tc.task_registry_id
    WHERE tr.task_id = p_task_id
    AND tc.is_valid = TRUE
    ORDER BY tc.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Add recovery queue entry
CREATE OR REPLACE FUNCTION add_to_recovery_queue(
    p_task_id VARCHAR(255),
    p_recovery_method recovery_method DEFAULT 'resume_checkpoint',
    p_priority INTEGER DEFAULT 0,
    p_scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) RETURNS UUID AS $$
DECLARE
    registry_id UUID;
    queue_id UUID;
BEGIN
    -- Get task registry ID
    SELECT id INTO registry_id FROM task_registry WHERE task_id = p_task_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Task registry not found for task_id: %', p_task_id;
    END IF;
    
    -- Insert into recovery queue
    INSERT INTO recovery_queue (
        task_registry_id, recovery_method, recovery_priority,
        scheduled_for, status
    ) VALUES (
        registry_id, p_recovery_method, p_priority,
        p_scheduled_for, 'pending'
    ) RETURNING id INTO queue_id;
    
    RETURN queue_id;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_task_registry_updated_at 
    BEFORE UPDATE ON task_registry
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recovery_queue_updated_at
    BEFORE UPDATE ON recovery_queue  
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON task_registry TO postgres, anon, authenticated, service_role;
GRANT ALL PRIVILEGES ON task_checkpoints TO postgres, anon, authenticated, service_role;  
GRANT ALL PRIVILEGES ON recovery_queue TO postgres, anon, authenticated, service_role;

-- RLS Policies for task_registry
ALTER TABLE task_registry ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own task registry entries" ON task_registry
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own task registry entries" ON task_registry
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own task registry entries" ON task_registry
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all task registry entries" ON task_registry
    FOR ALL USING (auth.role() = 'service_role');

-- RLS Policies for task_checkpoints  
ALTER TABLE task_checkpoints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view checkpoints for own tasks" ON task_checkpoints
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM task_registry tr 
            WHERE tr.id = task_checkpoints.task_registry_id 
            AND tr.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all checkpoints" ON task_checkpoints
    FOR ALL USING (auth.role() = 'service_role');

-- RLS Policies for recovery_queue
ALTER TABLE recovery_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view recovery queue for own tasks" ON recovery_queue
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM task_registry tr 
            WHERE tr.id = recovery_queue.task_registry_id 
            AND tr.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all recovery queue entries" ON recovery_queue
    FOR ALL USING (auth.role() = 'service_role');