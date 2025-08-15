-- LLM Evaluation System Database Schema
-- Production-ready schema with proper indexes, constraints, and optimization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enum types
CREATE TYPE evaluation_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE ab_test_status AS ENUM ('draft', 'active', 'paused', 'completed', 'archived');

-- Prompt Templates Table
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '{}'::jsonb,
    description TEXT,
    tags TEXT[],
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT prompt_templates_name_version_key UNIQUE (name, version),
    CONSTRAINT prompt_templates_template_content_check CHECK (LENGTH(template_content) > 0)
);

-- Test Datasets Table
CREATE TABLE test_datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    domain VARCHAR(100),
    size INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT test_datasets_size_check CHECK (size >= 0)
);

-- Test Cases Table
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id UUID NOT NULL REFERENCES test_datasets(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL,
    expected_output TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT test_cases_input_data_check CHECK (input_data IS NOT NULL AND input_data != '{}')
);

-- Evaluation Jobs Table
CREATE TABLE evaluation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_template_id UUID NOT NULL REFERENCES prompt_templates(id),
    dataset_id UUID NOT NULL REFERENCES test_datasets(id),
    model_configs JSONB NOT NULL,
    metrics_config JSONB NOT NULL,
    status evaluation_status DEFAULT 'pending',
    progress DECIMAL(5,2) DEFAULT 0.0,
    estimated_duration INTEGER, -- seconds
    priority INTEGER DEFAULT 5, -- 1 (highest) to 10 (lowest)
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Constraints
    CONSTRAINT evaluation_jobs_progress_check CHECK (progress >= 0.0 AND progress <= 100.0),
    CONSTRAINT evaluation_jobs_priority_check CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT evaluation_jobs_duration_check CHECK (estimated_duration IS NULL OR estimated_duration > 0)
);

-- Evaluation Results Table
CREATE TABLE evaluation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES evaluation_jobs(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES test_cases(id),
    model_name VARCHAR(100) NOT NULL,
    prompt_used TEXT NOT NULL,
    generated_response TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    token_usage INTEGER NOT NULL DEFAULT 0,
    metrics_scores JSONB NOT NULL,
    langsmith_run_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT evaluation_results_response_time_check CHECK (response_time_ms >= 0),
    CONSTRAINT evaluation_results_token_usage_check CHECK (token_usage >= 0)
);

-- Evaluation Job Summaries Table (for quick analytics)
CREATE TABLE evaluation_job_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES evaluation_jobs(id) ON DELETE CASCADE,
    total_evaluations INTEGER NOT NULL,
    successful_evaluations INTEGER NOT NULL,
    success_rate DECIMAL(5,4) NOT NULL,
    avg_response_time DECIMAL(10,2),
    total_tokens INTEGER,
    avg_overall_score DECIMAL(5,4),
    avg_faithfulness DECIMAL(5,4),
    avg_relevance DECIMAL(5,4),
    avg_coherence DECIMAL(5,4),
    avg_semantic_similarity DECIMAL(5,4),
    avg_bleu DECIMAL(5,4),
    avg_rouge1 DECIMAL(5,4),
    avg_rouge2 DECIMAL(5,4),
    avg_rougeL DECIMAL(5,4),
    best_model VARCHAR(100),
    worst_model VARCHAR(100),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT job_summaries_success_rate_check CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    CONSTRAINT job_summaries_evaluations_check CHECK (successful_evaluations <= total_evaluations)
);

-- A/B Tests Table
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    control_prompt_id UUID NOT NULL REFERENCES prompt_templates(id),
    variant_prompt_id UUID NOT NULL REFERENCES prompt_templates(id),
    traffic_split DECIMAL(3,2) DEFAULT 0.5,
    status ab_test_status DEFAULT 'draft',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    target_sample_size INTEGER,
    significance_level DECIMAL(3,2) DEFAULT 0.05,
    primary_metric VARCHAR(100) NOT NULL DEFAULT 'overall_score',
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ab_tests_traffic_split_check CHECK (traffic_split > 0.0 AND traffic_split < 1.0),
    CONSTRAINT ab_tests_significance_check CHECK (significance_level > 0.0 AND significance_level < 1.0),
    CONSTRAINT ab_tests_dates_check CHECK (end_date IS NULL OR start_date IS NULL OR end_date > start_date),
    CONSTRAINT ab_tests_different_prompts_check CHECK (control_prompt_id != variant_prompt_id)
);

-- A/B Test Interactions Table
CREATE TABLE ab_test_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    user_session VARCHAR(255) NOT NULL,
    variant VARCHAR(50) NOT NULL, -- 'control' or 'variant'
    prompt_used TEXT NOT NULL,
    response_generated TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    user_feedback JSONB,
    performance_metrics JSONB,
    conversion_event BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ab_interactions_variant_check CHECK (variant IN ('control', 'variant')),
    CONSTRAINT ab_interactions_response_time_check CHECK (response_time_ms >= 0)
);

-- Model Performance Cache Table (for dashboard optimization)
CREATE TABLE model_performance_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL,
    dataset_id UUID REFERENCES test_datasets(id),
    date_range_start TIMESTAMPTZ NOT NULL,
    date_range_end TIMESTAMPTZ NOT NULL,
    total_evaluations INTEGER NOT NULL,
    avg_overall_score DECIMAL(5,4),
    avg_response_time DECIMAL(10,2),
    total_tokens INTEGER,
    cost_usd DECIMAL(10,4),
    metrics_breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 hour'),
    
    -- Constraints
    CONSTRAINT model_cache_date_range_check CHECK (date_range_end >= date_range_start),
    CONSTRAINT model_cache_total_evaluations_check CHECK (total_evaluations > 0)
);

-- Evaluation Queue Table (for job scheduling)
CREATE TABLE evaluation_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES evaluation_jobs(id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 5,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    claimed_at TIMESTAMPTZ,
    claimed_by VARCHAR(255), -- worker identifier
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT queue_priority_check CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT queue_retry_check CHECK (retry_count <= max_retries)
);

-- Indexes for Performance Optimization

-- Prompt Templates
CREATE INDEX idx_prompt_templates_name_active ON prompt_templates(name) WHERE is_active = TRUE;
CREATE INDEX idx_prompt_templates_created_by ON prompt_templates(created_by);
CREATE INDEX idx_prompt_templates_tags ON prompt_templates USING GIN(tags);

-- Test Datasets
CREATE INDEX idx_test_datasets_domain ON test_datasets(domain);
CREATE INDEX idx_test_datasets_created_by ON test_datasets(created_by);
CREATE INDEX idx_test_datasets_name_trgm ON test_datasets USING GIN(name gin_trgm_ops);

-- Test Cases
CREATE INDEX idx_test_cases_dataset_id ON test_cases(dataset_id);
CREATE INDEX idx_test_cases_input_data ON test_cases USING GIN(input_data);
CREATE INDEX idx_test_cases_tags ON test_cases USING GIN(tags);

-- Evaluation Jobs
CREATE INDEX idx_evaluation_jobs_status ON evaluation_jobs(status);
CREATE INDEX idx_evaluation_jobs_created_by ON evaluation_jobs(created_by);
CREATE INDEX idx_evaluation_jobs_created_at ON evaluation_jobs(created_at DESC);
CREATE INDEX idx_evaluation_jobs_priority_status ON evaluation_jobs(priority, status);
CREATE INDEX idx_evaluation_jobs_template_dataset ON evaluation_jobs(prompt_template_id, dataset_id);

-- Evaluation Results
CREATE INDEX idx_evaluation_results_job_id ON evaluation_results(job_id);
CREATE INDEX idx_evaluation_results_model_name ON evaluation_results(model_name);
CREATE INDEX idx_evaluation_results_created_at ON evaluation_results(created_at DESC);
CREATE INDEX idx_evaluation_results_metrics ON evaluation_results USING GIN(metrics_scores);
CREATE INDEX idx_evaluation_results_langsmith ON evaluation_results(langsmith_run_id) WHERE langsmith_run_id IS NOT NULL;

-- A/B Tests
CREATE INDEX idx_ab_tests_status ON ab_tests(status);
CREATE INDEX idx_ab_tests_created_by ON ab_tests(created_by);
CREATE INDEX idx_ab_tests_date_range ON ab_tests(start_date, end_date);
CREATE INDEX idx_ab_tests_active ON ab_tests(status, start_date, end_date) WHERE status = 'active';

-- A/B Test Interactions
CREATE INDEX idx_ab_interactions_test_id ON ab_test_interactions(test_id);
CREATE INDEX idx_ab_interactions_user_session ON ab_test_interactions(user_session);
CREATE INDEX idx_ab_interactions_variant ON ab_test_interactions(variant);
CREATE INDEX idx_ab_interactions_created_at ON ab_test_interactions(created_at DESC);

-- Model Performance Cache
CREATE INDEX idx_model_cache_model_name ON model_performance_cache(model_name);
CREATE INDEX idx_model_cache_expires ON model_performance_cache(expires_at);
CREATE INDEX idx_model_cache_lookup ON model_performance_cache(model_name, dataset_id, date_range_start, date_range_end);

-- Evaluation Queue
CREATE INDEX idx_evaluation_queue_priority ON evaluation_queue(priority, scheduled_at) WHERE claimed_at IS NULL;
CREATE INDEX idx_evaluation_queue_claimed ON evaluation_queue(claimed_by, claimed_at) WHERE claimed_at IS NOT NULL;

-- Functions and Triggers

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_datasets_updated_at
    BEFORE UPDATE ON test_datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update dataset size trigger
CREATE OR REPLACE FUNCTION update_dataset_size()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE test_datasets 
        SET size = size + 1 
        WHERE id = NEW.dataset_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE test_datasets 
        SET size = size - 1 
        WHERE id = OLD.dataset_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_dataset_size
    AFTER INSERT OR DELETE ON test_cases
    FOR EACH ROW EXECUTE FUNCTION update_dataset_size();

-- Cleanup expired cache entries function
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM model_performance_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Views for Common Queries

-- Active jobs with progress
CREATE VIEW active_evaluation_jobs AS
SELECT 
    j.*,
    t.name as template_name,
    d.name as dataset_name,
    d.size as dataset_size,
    CASE 
        WHEN j.started_at IS NOT NULL AND j.completed_at IS NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - j.started_at))
        ELSE NULL 
    END as runtime_seconds
FROM evaluation_jobs j
JOIN prompt_templates t ON j.prompt_template_id = t.id
JOIN test_datasets d ON j.dataset_id = d.id
WHERE j.status IN ('pending', 'running');

-- Model comparison summary
CREATE VIEW model_comparison_summary AS
SELECT 
    er.model_name,
    COUNT(*) as total_evaluations,
    AVG(CAST(er.metrics_scores->>'overall_score' AS DECIMAL)) as avg_overall_score,
    AVG(er.response_time_ms) as avg_response_time,
    SUM(er.token_usage) as total_tokens,
    MIN(er.created_at) as first_evaluation,
    MAX(er.created_at) as last_evaluation
FROM evaluation_results er
WHERE er.error_message IS NULL
GROUP BY er.model_name;

-- Recent job results
CREATE VIEW recent_job_results AS
SELECT 
    j.id as job_id,
    j.name as job_name,
    j.status,
    j.progress,
    j.created_at,
    j.completed_at,
    COUNT(er.id) as total_results,
    AVG(CAST(er.metrics_scores->>'overall_score' AS DECIMAL)) as avg_score,
    STRING_AGG(DISTINCT er.model_name, ', ') as models_tested
FROM evaluation_jobs j
LEFT JOIN evaluation_results er ON j.id = er.job_id
WHERE j.created_at >= NOW() - INTERVAL '30 days'
GROUP BY j.id, j.name, j.status, j.progress, j.created_at, j.completed_at
ORDER BY j.created_at DESC;

-- Row Level Security (RLS) Policies
-- Enable RLS on sensitive tables
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;

-- Create policies (assuming users table exists with id field)
-- Users can only see their own resources
CREATE POLICY prompt_templates_user_policy ON prompt_templates
    FOR ALL TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY test_datasets_user_policy ON test_datasets
    FOR ALL TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY evaluation_jobs_user_policy ON evaluation_jobs
    FOR ALL TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY ab_tests_user_policy ON ab_tests
    FOR ALL TO authenticated
    USING (created_by = auth.uid());

-- Comments for Documentation
COMMENT ON TABLE prompt_templates IS 'Stores versioned prompt templates for LLM evaluation';
COMMENT ON TABLE test_datasets IS 'Stores test datasets used for evaluation';
COMMENT ON TABLE test_cases IS 'Individual test cases within datasets';
COMMENT ON TABLE evaluation_jobs IS 'Tracks evaluation job execution and status';
COMMENT ON TABLE evaluation_results IS 'Stores individual evaluation results';
COMMENT ON TABLE evaluation_job_summaries IS 'Pre-computed job summaries for fast analytics';
COMMENT ON TABLE ab_tests IS 'A/B test configurations and metadata';
COMMENT ON TABLE ab_test_interactions IS 'Individual A/B test interactions and results';
COMMENT ON TABLE model_performance_cache IS 'Cached performance metrics for dashboard optimization';
COMMENT ON TABLE evaluation_queue IS 'Job queue for evaluation scheduling';

COMMENT ON COLUMN prompt_templates.variables IS 'JSON schema defining template variables';
COMMENT ON COLUMN test_cases.input_data IS 'Input variables for prompt template';
COMMENT ON COLUMN evaluation_jobs.model_configs IS 'Array of model configurations to test';
COMMENT ON COLUMN evaluation_jobs.metrics_config IS 'Configuration for metrics calculation';
COMMENT ON COLUMN evaluation_results.metrics_scores IS 'Calculated metric scores for this evaluation';
COMMENT ON COLUMN ab_test_interactions.performance_metrics IS 'Performance metrics for this interaction';
COMMENT ON COLUMN model_performance_cache.metrics_breakdown IS 'Detailed breakdown of all metrics';

-- Initial data for development/testing
INSERT INTO prompt_templates (name, version, template_content, description, created_by)
VALUES 
(
    'default_property_analysis',
    '1.0',
    'Analyze the following property data and provide insights: {property_data}',
    'Default template for property analysis tasks',
    '00000000-0000-0000-0000-000000000000'
),
(
    'contract_review',
    '1.0', 
    'Review this contract for key terms and potential issues: {contract_text}',
    'Template for contract review and analysis',
    '00000000-0000-0000-0000-000000000000'
);

INSERT INTO test_datasets (name, description, domain, created_by)
VALUES 
(
    'sample_property_data',
    'Sample property data for testing analysis prompts',
    'real_estate',
    '00000000-0000-0000-0000-000000000000'
),
(
    'contract_samples',
    'Sample contracts for testing review prompts',
    'legal',
    '00000000-0000-0000-0000-000000000000'
);

-- Grant permissions for application user
-- Note: Adjust user/role names based on your setup
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO real2ai_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO real2ai_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO real2ai_app;