-- Task recovery tables and indexes

CREATE TYPE task_state AS ENUM (
    'queued', 'started', 'processing', 'checkpoint', 'paused',
    'completed', 'failed', 'cancelled', 'recovering', 'partial', 'orphaned'
);

CREATE TYPE recovery_method AS ENUM (
    'resume_checkpoint', 'restart_clean', 'validate_only', 'manual_intervention'
);

CREATE TABLE task_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    task_args JSONB NOT NULL DEFAULT '{}',
    task_kwargs JSONB NOT NULL DEFAULT '{}',
    context_key VARCHAR(255),
    current_state task_state NOT NULL DEFAULT 'queued',
    previous_state task_state,
    state_history JSONB DEFAULT '[]',
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    current_step VARCHAR(255),
    checkpoint_data JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    recovery_priority INTEGER DEFAULT 0,
    auto_recovery_enabled BOOLEAN DEFAULT TRUE,
    result_data JSONB,
    error_details JSONB,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE task_checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE NOT NULL,
    checkpoint_name VARCHAR(255) NOT NULL,
    progress_percent INTEGER NOT NULL,
    step_description TEXT,
    recoverable_data JSONB NOT NULL DEFAULT '{}',
    database_state JSONB DEFAULT '{}',
    file_state JSONB DEFAULT '{}',
    checkpoint_hash VARCHAR(255),
    is_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recovery_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_registry_id UUID REFERENCES task_registry(id) ON DELETE CASCADE NOT NULL,
    recovery_method recovery_method NOT NULL DEFAULT 'resume_checkpoint',
    recovery_priority INTEGER DEFAULT 0,
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started TIMESTAMP WITH TIME ZONE,
    processing_completed TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    recovery_result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_task_registry_state ON task_registry(current_state);
CREATE INDEX idx_task_registry_user_state ON task_registry(user_id, current_state);
CREATE INDEX idx_task_registry_heartbeat ON task_registry(last_heartbeat) WHERE current_state IN ('started', 'processing', 'checkpoint');
CREATE INDEX idx_task_registry_task_id ON task_registry(task_id);
CREATE INDEX idx_recovery_queue_scheduled ON recovery_queue(scheduled_for, status);
CREATE INDEX idx_task_checkpoints_task ON task_checkpoints(task_registry_id, created_at DESC);

