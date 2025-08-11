-- Functions (subset needed early)

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_analysis_progress_detailed(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    content_hash TEXT,
    user_id UUID,
    current_step VARCHAR,
    progress_percent INTEGER,
    step_description TEXT,
    estimated_completion_minutes INTEGER,
    step_started_at TIMESTAMP WITH TIME ZONE,
    step_completed_at TIMESTAMP WITH TIME ZONE,
    total_elapsed_seconds INTEGER,
    status VARCHAR,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    contract_type contract_type,
    agent_version TEXT,
    analysis_status analysis_status
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ap.id,
        ap.content_hash,
        ap.user_id,
        ap.current_step,
        ap.progress_percent,
        ap.step_description,
        ap.estimated_completion_minutes,
        ap.step_started_at,
        ap.step_completed_at,
        ap.total_elapsed_seconds,
        ap.status,
        ap.error_message,
        ap.metadata,
        ap.created_at,
        ap.updated_at,
        c.contract_type,
        ca.agent_version,
        ca.status as analysis_status
    FROM analysis_progress ap
    LEFT JOIN contracts c ON ap.content_hash = c.content_hash
    LEFT JOIN contract_analyses ca ON ap.content_hash = ca.content_hash
    WHERE ap.user_id = p_user_id
    ORDER BY ap.updated_at DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION get_analysis_progress_detailed TO authenticated;

