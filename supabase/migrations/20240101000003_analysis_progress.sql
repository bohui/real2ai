-- Analysis progress

CREATE TABLE analysis_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    current_step VARCHAR(100) NOT NULL,
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    step_description TEXT,
    estimated_completion_minutes INTEGER CHECK (estimated_completion_minutes >= 0),
    step_started_at TIMESTAMP WITH TIME ZONE,
    step_completed_at TIMESTAMP WITH TIME ZONE,
    total_elapsed_seconds INTEGER DEFAULT 0 CHECK (total_elapsed_seconds >= 0),
    status VARCHAR(50) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_analysis_progress UNIQUE (content_hash, user_id),
    CONSTRAINT valid_progress_percent CHECK (progress_percent BETWEEN 0 AND 100)
);

-- Indexes for analysis_progress
CREATE INDEX idx_analysis_progress_content_hash ON analysis_progress(content_hash);
CREATE INDEX idx_analysis_progress_user_id ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_status ON analysis_progress(status);
CREATE INDEX idx_analysis_progress_created_at ON analysis_progress(created_at);
CREATE INDEX idx_analysis_progress_active ON analysis_progress(content_hash, user_id, updated_at) 
WHERE status = 'in_progress';

