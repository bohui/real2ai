-- Migration: Evaluation System Tables
-- Description: Creates tables for LLM evaluation system including prompt templates, test datasets, evaluation jobs, and results

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Prompt Templates Table
CREATE TABLE IF NOT EXISTS public.prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Ensure unique name/version combination per user
    UNIQUE(name, version, created_by)
);

-- Test Datasets Table
CREATE TABLE IF NOT EXISTS public.test_datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    domain VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    size INTEGER DEFAULT 0,
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Ensure unique name per user
    UNIQUE(name, created_by)
);

-- Test Cases Table
CREATE TABLE IF NOT EXISTS public.test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id UUID NOT NULL REFERENCES public.test_datasets(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL,
    expected_output TEXT,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation Jobs Table
CREATE TABLE IF NOT EXISTS public.evaluation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_template_id UUID NOT NULL REFERENCES public.prompt_templates(id) ON DELETE CASCADE,
    dataset_id UUID NOT NULL REFERENCES public.test_datasets(id) ON DELETE CASCADE,
    model_configs JSONB NOT NULL,
    metrics_config JSONB NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress DECIMAL(5,4) DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Evaluation Results Table
CREATE TABLE IF NOT EXISTS public.evaluation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES public.evaluation_jobs(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES public.test_cases(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    prompt_used TEXT NOT NULL,
    generated_response TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    token_usage INTEGER,
    metrics_scores JSONB NOT NULL DEFAULT '{}',
    langsmith_run_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation Job Summaries Table
CREATE TABLE IF NOT EXISTS public.evaluation_job_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES public.evaluation_jobs(id) ON DELETE CASCADE,
    total_test_cases INTEGER NOT NULL,
    completed_test_cases INTEGER DEFAULT 0,
    failed_test_cases INTEGER DEFAULT 0,
    avg_response_time_ms DECIMAL(10,2),
    total_token_usage INTEGER,
    avg_overall_score DECIMAL(5,4),
    avg_bleu_score DECIMAL(5,4),
    avg_rouge_score DECIMAL(5,4),
    avg_semantic_similarity DECIMAL(5,4),
    avg_faithfulness DECIMAL(5,4),
    avg_relevance DECIMAL(5,4),
    avg_coherence DECIMAL(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(job_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_prompt_templates_created_by ON public.prompt_templates(created_by);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON public.prompt_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_test_datasets_created_by ON public.test_datasets(created_by);
CREATE INDEX IF NOT EXISTS idx_test_datasets_domain ON public.test_datasets(domain);
CREATE INDEX IF NOT EXISTS idx_test_cases_dataset_id ON public.test_cases(dataset_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_jobs_created_by ON public.evaluation_jobs(created_by);
CREATE INDEX IF NOT EXISTS idx_evaluation_jobs_status ON public.evaluation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_evaluation_jobs_created_at ON public.evaluation_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_job_id ON public.evaluation_results(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_model_name ON public.evaluation_results(model_name);
CREATE INDEX IF NOT EXISTS idx_evaluation_job_summaries_job_id ON public.evaluation_job_summaries(job_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_job_summaries ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Prompt Templates: Users can only see their own templates
CREATE POLICY "Users can view their own prompt templates" ON public.prompt_templates
    FOR SELECT USING (auth.uid() = created_by);

CREATE POLICY "Users can insert their own prompt templates" ON public.prompt_templates
    FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update their own prompt templates" ON public.prompt_templates
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own prompt templates" ON public.prompt_templates
    FOR DELETE USING (auth.uid() = created_by);

-- Test Datasets: Users can only see their own datasets
CREATE POLICY "Users can view their own test datasets" ON public.test_datasets
    FOR SELECT USING (auth.uid() = created_by);

CREATE POLICY "Users can insert their own test datasets" ON public.test_datasets
    FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update their own test datasets" ON public.test_datasets
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own test datasets" ON public.test_datasets
    FOR DELETE USING (auth.uid() = created_by);

-- Test Cases: Users can only see test cases from their own datasets
CREATE POLICY "Users can view test cases from their datasets" ON public.test_cases
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.test_datasets 
            WHERE id = test_cases.dataset_id AND created_by = auth.uid()
        )
    );

CREATE POLICY "Users can insert test cases to their datasets" ON public.test_cases
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.test_datasets 
            WHERE id = test_cases.dataset_id AND created_by = auth.uid()
        )
    );

-- Evaluation Jobs: Users can only see their own jobs
CREATE POLICY "Users can view their own evaluation jobs" ON public.evaluation_jobs
    FOR SELECT USING (auth.uid() = created_by);

CREATE POLICY "Users can insert their own evaluation jobs" ON public.evaluation_jobs
    FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update their own evaluation jobs" ON public.evaluation_jobs
    FOR UPDATE USING (auth.uid() = created_by);

-- Evaluation Results: Users can only see results from their own jobs
CREATE POLICY "Users can view results from their jobs" ON public.evaluation_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.evaluation_jobs 
            WHERE id = evaluation_results.job_id AND created_by = auth.uid()
        )
    );

CREATE POLICY "Users can insert results to their jobs" ON public.evaluation_results
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.evaluation_jobs 
            WHERE id = evaluation_results.job_id AND created_by = auth.uid()
        )
    );

-- Evaluation Job Summaries: Users can only see summaries from their own jobs
CREATE POLICY "Users can view summaries from their jobs" ON public.evaluation_job_summaries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.evaluation_jobs 
            WHERE id = evaluation_job_summaries.job_id AND created_by = auth.uid()
        )
    );

CREATE POLICY "Users can insert summaries to their jobs" ON public.evaluation_job_summaries
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.evaluation_jobs 
            WHERE id = evaluation_job_summaries.job_id AND created_by = auth.uid()
        )
    );

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.prompt_templates TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.test_datasets TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.test_cases TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evaluation_jobs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evaluation_results TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evaluation_job_summaries TO authenticated;

-- Create function to update dataset size when test cases are added/removed
CREATE OR REPLACE FUNCTION public.update_dataset_size()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.test_datasets 
        SET size = size + 1 
        WHERE id = NEW.dataset_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.test_datasets 
        SET size = size - 1 
        WHERE id = OLD.dataset_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update dataset size
CREATE TRIGGER trigger_update_dataset_size
    AFTER INSERT OR DELETE ON public.test_cases
    FOR EACH ROW
    EXECUTE FUNCTION public.update_dataset_size();

-- Create function to update job summary when results are added
CREATE OR REPLACE FUNCTION public.update_job_summary()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update job summary
    INSERT INTO public.evaluation_job_summaries (
        job_id,
        total_test_cases,
        completed_test_cases,
        failed_test_cases,
        avg_response_time_ms,
        total_token_usage,
        avg_overall_score,
        avg_bleu_score,
        avg_rouge_score,
        avg_semantic_similarity,
        avg_faithfulness,
        avg_relevance,
        avg_coherence,
        updated_at
    )
    SELECT 
        NEW.job_id,
        COUNT(DISTINCT er.test_case_id) as total_test_cases,
        COUNT(*) as completed_test_cases,
        COUNT(CASE WHEN er.error_message IS NOT NULL THEN 1 END) as failed_test_cases,
        AVG(er.response_time_ms) as avg_response_time_ms,
        SUM(COALESCE(er.token_usage, 0)) as total_token_usage,
        AVG(COALESCE((er.metrics_scores->>'overall_score')::DECIMAL, 0)) as avg_overall_score,
        AVG(COALESCE((er.metrics_scores->>'bleu')::DECIMAL, 0)) as avg_bleu_score,
        AVG(COALESCE((er.metrics_scores->>'rouge')::DECIMAL, 0)) as avg_rouge_score,
        AVG(COALESCE((er.metrics_scores->>'semantic_similarity')::DECIMAL, 0)) as avg_semantic_similarity,
        AVG(COALESCE((er.metrics_scores->>'faithfulness')::DECIMAL, 0)) as avg_faithfulness,
        AVG(COALESCE((er.metrics_scores->>'relevance')::DECIMAL, 0)) as avg_relevance,
        AVG(COALESCE((er.metrics_scores->>'coherence')::DECIMAL, 0)) as avg_coherence,
        NOW() as updated_at
    FROM public.evaluation_results er
    WHERE er.job_id = NEW.job_id
    GROUP BY er.job_id
    ON CONFLICT (job_id) DO UPDATE SET
        total_test_cases = EXCLUDED.total_test_cases,
        completed_test_cases = EXCLUDED.completed_test_cases,
        failed_test_cases = EXCLUDED.failed_test_cases,
        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
        total_token_usage = EXCLUDED.total_token_usage,
        avg_overall_score = EXCLUDED.avg_overall_score,
        avg_bleu_score = EXCLUDED.avg_bleu_score,
        avg_rouge_score = EXCLUDED.avg_rouge_score,
        avg_semantic_similarity = EXCLUDED.avg_semantic_similarity,
        avg_faithfulness = EXCLUDED.avg_faithfulness,
        avg_relevance = EXCLUDED.avg_relevance,
        avg_coherence = EXCLUDED.avg_coherence,
        updated_at = EXCLUDED.updated_at;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update job summary when results are added
CREATE TRIGGER trigger_update_job_summary
    AFTER INSERT OR UPDATE ON public.evaluation_results
    FOR EACH ROW
    EXECUTE FUNCTION public.update_job_summary();

-- Create function to get model comparison data
CREATE OR REPLACE FUNCTION public.get_model_comparison_for_user(
    user_id UUID,
    dataset_filter UUID DEFAULT NULL,
    date_from_filter TIMESTAMPTZ DEFAULT NULL,
    date_to_filter TIMESTAMPTZ DEFAULT NULL
)
RETURNS TABLE (
    model_name VARCHAR(255),
    total_evaluations BIGINT,
    avg_overall_score DECIMAL(5,4),
    avg_response_time_ms DECIMAL(10,2),
    avg_token_usage DECIMAL(10,2),
    last_evaluation TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        er.model_name,
        COUNT(*) as total_evaluations,
        AVG(COALESCE((er.metrics_scores->>'overall_score')::DECIMAL, 0)) as avg_overall_score,
        AVG(er.response_time_ms) as avg_response_time_ms,
        AVG(COALESCE(er.token_usage, 0)) as avg_token_usage,
        MAX(er.created_at) as last_evaluation
    FROM public.evaluation_results er
    JOIN public.evaluation_jobs ej ON er.job_id = ej.id
    WHERE ej.created_by = user_id
        AND (dataset_filter IS NULL OR ej.dataset_id = dataset_filter)
        AND (date_from_filter IS NULL OR er.created_at >= date_from_filter)
        AND (date_to_filter IS NULL OR er.created_at <= date_to_filter)
    GROUP BY er.model_name
    ORDER BY avg_overall_score DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION public.get_model_comparison_for_user(UUID, UUID, TIMESTAMPTZ, TIMESTAMPTZ) TO authenticated;

-- Create function to get user evaluation stats
CREATE OR REPLACE FUNCTION public.get_user_evaluation_stats(user_id UUID)
RETURNS TABLE (
    total_prompts BIGINT,
    total_datasets BIGINT,
    total_jobs BIGINT,
    total_evaluations BIGINT,
    avg_overall_score DECIMAL(5,4),
    first_evaluation TIMESTAMPTZ,
    last_evaluation TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT pt.id) as total_prompts,
        COUNT(DISTINCT td.id) as total_datasets,
        COUNT(DISTINCT ej.id) as total_jobs,
        COUNT(er.id) as total_evaluations,
        AVG(COALESCE((er.metrics_scores->>'overall_score')::DECIMAL, 0)) as avg_overall_score,
        MIN(er.created_at) as first_evaluation,
        MAX(er.created_at) as last_evaluation
    FROM public.prompt_templates pt
    FULL OUTER JOIN public.test_datasets td ON pt.created_by = td.created_by
    FULL OUTER JOIN public.evaluation_jobs ej ON td.created_by = ej.created_by
    FULL OUTER JOIN public.evaluation_results er ON ej.id = er.job_id
    WHERE pt.created_by = user_id OR td.created_by = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION public.get_user_evaluation_stats(UUID) TO authenticated;