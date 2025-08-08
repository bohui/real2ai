-- Database functions and triggers for Real2.AI
-- Handles automated tasks, data validation, and business logic

-- Enhanced trigger function with better error handling
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Set updated_at to current timestamp
    NEW.updated_at = NOW();
    
    -- Ensure created_at is never modified after initial insert
    IF TG_OP = 'UPDATE' AND OLD.created_at IS NOT NULL THEN
        NEW.created_at = OLD.created_at;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comment for documentation
COMMENT ON FUNCTION update_updated_at_column() IS 
'Automatically updates updated_at timestamp on row updates and preserves created_at';

-- Function to update analysis progress updated_at timestamp
CREATE OR REPLACE FUNCTION update_analysis_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest progress for a contract
CREATE OR REPLACE FUNCTION get_latest_analysis_progress(contract_uuid UUID)
RETURNS analysis_progress AS $$
DECLARE
    progress_record analysis_progress;
BEGIN
    SELECT * INTO progress_record
    FROM analysis_progress
    WHERE contract_id = contract_uuid
    ORDER BY updated_at DESC
    LIMIT 1;
    
    RETURN progress_record;
END;
$$ LANGUAGE plpgsql;

-- Function to update analysis progress
CREATE OR REPLACE FUNCTION update_analysis_progress(
    p_contract_id UUID,
    p_analysis_id UUID,
    p_user_id UUID,
    p_current_step TEXT,
    p_progress_percent INTEGER,
    p_step_description TEXT DEFAULT NULL,
    p_estimated_completion_minutes INTEGER DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    progress_id UUID;
    existing_progress analysis_progress;
    elapsed_seconds INTEGER := 0;
BEGIN
    -- Get existing progress record
    SELECT * INTO existing_progress
    FROM analysis_progress
    WHERE contract_id = p_contract_id
    AND analysis_id = p_analysis_id
    ORDER BY updated_at DESC
    LIMIT 1;
    
    -- Calculate elapsed time if previous step exists
    IF existing_progress.id IS NOT NULL THEN
        elapsed_seconds := EXTRACT(EPOCH FROM (NOW() - existing_progress.step_started_at))::INTEGER;
        
        -- Update previous step completion time
        UPDATE analysis_progress
        SET step_completed_at = NOW(),
            total_elapsed_seconds = elapsed_seconds
        WHERE id = existing_progress.id;
    END IF;
    
    -- Insert new progress record
    INSERT INTO analysis_progress (
        contract_id,
        analysis_id,
        user_id,
        current_step,
        progress_percent,
        step_description,
        estimated_completion_minutes,
        total_elapsed_seconds
    ) VALUES (
        p_contract_id,
        p_analysis_id,
        p_user_id,
        p_current_step,
        p_progress_percent,
        p_step_description,
        p_estimated_completion_minutes,
        COALESCE(existing_progress.total_elapsed_seconds, 0) + COALESCE(elapsed_seconds, 0)
    )
    RETURNING id INTO progress_id;
    
    RETURN progress_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark analysis as completed
CREATE OR REPLACE FUNCTION complete_analysis_progress(
    p_contract_id UUID,
    p_analysis_id UUID,
    p_final_status TEXT DEFAULT 'completed'
)
RETURNS BOOLEAN AS $$
DECLARE
    latest_progress analysis_progress;
    total_time INTEGER;
BEGIN
    -- Get latest progress
    SELECT * INTO latest_progress
    FROM analysis_progress
    WHERE contract_id = p_contract_id
    AND analysis_id = p_analysis_id
    ORDER BY updated_at DESC
    LIMIT 1;
    
    IF latest_progress.id IS NOT NULL THEN
        -- Calculate total processing time
        total_time := EXTRACT(EPOCH FROM (NOW() - latest_progress.created_at))::INTEGER;
        
        -- Update final progress record
        UPDATE analysis_progress
        SET status = p_final_status,
            progress_percent = CASE WHEN p_final_status = 'completed' THEN 100 ELSE progress_percent END,
            step_completed_at = NOW(),
            total_elapsed_seconds = total_time
        WHERE id = latest_progress.id;
        
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all relevant tables
-- Use DROP TRIGGER IF EXISTS to handle cases where triggers already exist from initial schema

-- Profiles
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at 
    BEFORE UPDATE ON public.profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Documents (already exists in initial schema)
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Contracts
DROP TRIGGER IF EXISTS update_contracts_updated_at ON contracts;
CREATE TRIGGER update_contracts_updated_at 
    BEFORE UPDATE ON contracts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Contract analyses
DROP TRIGGER IF EXISTS update_contract_analyses_updated_at ON contract_analyses;
CREATE TRIGGER update_contract_analyses_updated_at 
    BEFORE UPDATE ON contract_analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Property data
DROP TRIGGER IF EXISTS update_property_data_updated_at ON property_data;
CREATE TRIGGER update_property_data_updated_at 
    BEFORE UPDATE ON property_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- User subscriptions
DROP TRIGGER IF EXISTS update_user_subscriptions_updated_at ON user_subscriptions;
CREATE TRIGGER update_user_subscriptions_updated_at 
    BEFORE UPDATE ON user_subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analysis progress
DROP TRIGGER IF EXISTS update_analysis_progress_updated_at ON analysis_progress;
CREATE TRIGGER update_analysis_progress_updated_at 
    BEFORE UPDATE ON analysis_progress 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document pages
DROP TRIGGER IF EXISTS update_document_pages_updated_at ON document_pages;
CREATE TRIGGER update_document_pages_updated_at 
    BEFORE UPDATE ON document_pages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document entities
DROP TRIGGER IF EXISTS update_document_entities_updated_at ON document_entities;
CREATE TRIGGER update_document_entities_updated_at 
    BEFORE UPDATE ON document_entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document diagrams
DROP TRIGGER IF EXISTS update_document_diagrams_updated_at ON document_diagrams;
CREATE TRIGGER update_document_diagrams_updated_at 
    BEFORE UPDATE ON document_diagrams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document analyses
DROP TRIGGER IF EXISTS update_document_analyses_updated_at ON document_analyses;
CREATE TRIGGER update_document_analyses_updated_at 
    BEFORE UPDATE ON document_analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analysis progress updated_at trigger
DROP TRIGGER IF EXISTS analysis_progress_updated_at_trigger ON analysis_progress;
CREATE TRIGGER analysis_progress_updated_at_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW EXECUTE FUNCTION update_analysis_progress_updated_at();

-- Function to verify all timestamp columns have proper defaults
CREATE OR REPLACE FUNCTION verify_timestamp_defaults()
RETURNS TABLE(
    table_name TEXT,
    created_at_default TEXT,
    updated_at_default TEXT,
    has_trigger BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        COALESCE(c_created.column_default, 'NO DEFAULT')::TEXT as created_at_default,
        COALESCE(c_updated.column_default, 'NO DEFAULT')::TEXT as updated_at_default,
        EXISTS(
            SELECT 1 FROM pg_trigger tr 
            WHERE tr.tgname = 'update_' || t.table_name || '_updated_at'
        ) as has_trigger
    FROM information_schema.tables t
    LEFT JOIN information_schema.columns c_created ON (
        c_created.table_name = t.table_name 
        AND c_created.column_name = 'created_at'
        AND c_created.table_schema = 'public'
    )
    LEFT JOIN information_schema.columns c_updated ON (
        c_updated.table_name = t.table_name 
        AND c_updated.column_name = 'updated_at'
        AND c_updated.table_schema = 'public'
    )
    WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
    AND (c_created.column_name IS NOT NULL OR c_updated.column_name IS NOT NULL)
    ORDER BY t.table_name;
END;
$$ LANGUAGE plpgsql;

-- Function to create timestamps on existing records (if needed)
CREATE OR REPLACE FUNCTION backfill_timestamps(target_table TEXT)
RETURNS INTEGER AS $$
DECLARE
    rows_updated INTEGER := 0;
    sql_query TEXT;
BEGIN
    -- Update records where created_at is NULL
    sql_query := format('UPDATE %I SET created_at = NOW() WHERE created_at IS NULL', target_table);
    EXECUTE sql_query;
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    
    -- Update records where updated_at is NULL  
    sql_query := format('UPDATE %I SET updated_at = created_at WHERE updated_at IS NULL', target_table);
    EXECUTE sql_query;
    
    RETURN rows_updated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add helpful comments to all timestamp columns
DO $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    LOOP
        -- Add comments for created_at columns
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = table_record.table_name 
            AND column_name = 'created_at' 
            AND table_schema = 'public'
        ) THEN
            EXECUTE format('COMMENT ON COLUMN %I.created_at IS %L', 
                table_record.table_name, 
                'Automatically set on record creation (DEFAULT NOW())');
        END IF;

        -- Add comments for updated_at columns
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = table_record.table_name 
            AND column_name = 'updated_at' 
            AND table_schema = 'public'
        ) THEN
            EXECUTE format('COMMENT ON COLUMN %I.updated_at IS %L', 
                table_record.table_name, 
                'Automatically updated on record modification (trigger managed)');
        END IF;
    END LOOP;
END $$;

-- Create a view for monitoring timestamp management
CREATE OR REPLACE VIEW timestamp_management_status AS
SELECT 
    table_name,
    created_at_default,
    updated_at_default,
    has_trigger,
    CASE 
        WHEN created_at_default LIKE '%now()%' 
        AND updated_at_default LIKE '%now()%' 
        AND has_trigger THEN 'OPTIMAL'
        WHEN has_trigger THEN 'GOOD'
        ELSE 'NEEDS_ATTENTION'
    END as status
FROM verify_timestamp_defaults();

-- Grant permissions
GRANT SELECT ON timestamp_management_status TO authenticated;
GRANT EXECUTE ON FUNCTION verify_timestamp_defaults() TO authenticated;
GRANT EXECUTE ON FUNCTION backfill_timestamps(TEXT) TO service_role;

-- Add indexes for timestamp queries (if they don't exist)
DO $$
BEGIN
    -- Index for created_at queries on main tables
    CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_contracts_created_at ON contracts(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_contract_analyses_created_at ON contract_analyses(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
    
    -- Index for updated_at queries (useful for sync operations)
    CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_contracts_updated_at ON contracts(updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_contract_analyses_updated_at ON contract_analyses(updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_profiles_updated_at ON profiles(updated_at DESC);

EXCEPTION WHEN duplicate_table THEN
    -- Indexes already exist, continue
    NULL;
END $$;

-- Example usage functions for application code
CREATE OR REPLACE FUNCTION get_recent_records(
    table_name TEXT, 
    hours_back INTEGER DEFAULT 24,
    limit_count INTEGER DEFAULT 100
)
RETURNS SETOF RECORD AS $$
DECLARE
    sql_query TEXT;
BEGIN
    sql_query := format(
        'SELECT * FROM %I WHERE created_at > NOW() - INTERVAL ''%s hours'' ORDER BY created_at DESC LIMIT %s',
        table_name, hours_back, limit_count
    );
    RETURN QUERY EXECUTE sql_query;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_recently_updated_records(
    table_name TEXT, 
    minutes_back INTEGER DEFAULT 60,
    limit_count INTEGER DEFAULT 100
)
RETURNS SETOF RECORD AS $$
DECLARE
    sql_query TEXT;
BEGIN
    sql_query := format(
        'SELECT * FROM %I WHERE updated_at > NOW() - INTERVAL ''%s minutes'' ORDER BY updated_at DESC LIMIT %s',
        table_name, minutes_back, limit_count
    );
    RETURN QUERY EXECUTE sql_query;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate Australian postcodes by state
CREATE OR REPLACE FUNCTION validate_australian_postcode(postcode TEXT, state TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Handle null or empty inputs
    IF postcode IS NULL OR state IS NULL OR LENGTH(TRIM(postcode)) = 0 THEN
        RETURN FALSE;
    END IF;

    -- Validate postcode format by state
    CASE UPPER(state)
        WHEN 'NSW' THEN 
            RETURN postcode ~ '^(1|2)\d{3}$';
        WHEN 'ACT' THEN 
            RETURN postcode ~ '^(0200|02[0-9]{2}|26[0-9]{2}|29[0-9]{2})$';
        WHEN 'VIC' THEN 
            RETURN postcode ~ '^(3|8)\d{3}$';
        WHEN 'QLD' THEN 
            RETURN postcode ~ '^(4|9)\d{3}$';
        WHEN 'SA' THEN 
            RETURN postcode ~ '^5\d{3}$';
        WHEN 'WA' THEN 
            RETURN postcode ~ '^6\d{3}$';
        WHEN 'TAS' THEN 
            RETURN postcode ~ '^7\d{3}$';
        WHEN 'NT' THEN 
            RETURN postcode ~ '^(08[0-9]{2}|09[0-9]{2})$';
        ELSE 
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Function to create a user profile after auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY definer set search_path = ''
AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
    );
    RETURN NEW;
END;
$$;

-- Trigger to automatically create profile on user signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Function to log usage and deduct credits
CREATE OR REPLACE FUNCTION log_usage_and_deduct_credits(
    user_id UUID,
    action_type TEXT,
    credits_to_deduct INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'
)
RETURNS BOOLEAN AS $$
DECLARE
    current_credits INTEGER;
    new_credits INTEGER;
BEGIN
    -- Get current credits with row lock
    SELECT credits_remaining INTO current_credits
    FROM public.profiles
    WHERE id = user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found: %', user_id;
    END IF;

    -- Check if user has sufficient credits
    IF current_credits < credits_to_deduct THEN
        RAISE EXCEPTION 'Insufficient credits. Required: %, Available: %', credits_to_deduct, current_credits;
    END IF;

    -- Deduct credits
    new_credits := current_credits - credits_to_deduct;
    
    UPDATE public.profiles
    SET credits_remaining = new_credits
    WHERE id = user_id;

    -- Log the usage
    INSERT INTO usage_logs (user_id, action_type, credits_used, credits_remaining, metadata)
    VALUES (user_id, action_type, credits_to_deduct, new_credits, metadata);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to calculate analysis completion percentage
CREATE OR REPLACE FUNCTION calculate_analysis_progress(
    analysis_id UUID,
    current_step TEXT,
    total_steps INTEGER DEFAULT 6
)
RETURNS DECIMAL AS $$
DECLARE
    step_mapping JSONB;
    step_number INTEGER;
    progress_percentage DECIMAL;
BEGIN
    -- Define step mapping
    step_mapping := '{
        "document_parsing": 1,
        "text_extraction": 2,
        "risk_assessment": 3,
        "compliance_check": 4,
        "recommendations": 5,
        "finalization": 6
    }';

    -- Get step number
    step_number := (step_mapping ->> current_step)::INTEGER;
    
    IF step_number IS NULL THEN
        step_number := 1;
    END IF;

    -- Calculate progress percentage
    progress_percentage := (step_number::DECIMAL / total_steps::DECIMAL) * 100;

    -- Update progress table
    INSERT INTO analysis_progress (analysis_id, current_step, total_steps, completed_steps, progress_percentage)
    VALUES (analysis_id, current_step, total_steps, step_number - 1, progress_percentage)
    ON CONFLICT (analysis_id) DO UPDATE SET
        current_step = EXCLUDED.current_step,
        completed_steps = EXCLUDED.completed_steps,
        progress_percentage = EXCLUDED.progress_percentage,
        updated_at = NOW();

    RETURN progress_percentage;
END;
$$ LANGUAGE plpgsql;

-- Function to validate contract analysis data
CREATE OR REPLACE FUNCTION validate_analysis_result(analysis_result JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required fields exist
    IF NOT (analysis_result ? 'executive_summary' AND 
            analysis_result ? 'risk_assessment' AND 
            analysis_result ? 'compliance_check') THEN
        RETURN FALSE;
    END IF;

    -- Validate executive summary structure
    IF NOT (analysis_result->'executive_summary' ? 'overall_risk_score' AND
            analysis_result->'executive_summary' ? 'confidence_level') THEN
        RETURN FALSE;
    END IF;

    -- Validate risk score is within bounds
    IF (analysis_result->'executive_summary'->>'overall_risk_score')::DECIMAL NOT BETWEEN 0.0 AND 10.0 THEN
        RETURN FALSE;
    END IF;

    -- Validate confidence level is within bounds
    IF (analysis_result->'executive_summary'->>'confidence_level')::DECIMAL NOT BETWEEN 0.0 AND 1.0 THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to update analysis with results
CREATE OR REPLACE FUNCTION update_analysis_with_results(
    analysis_id UUID,
    analysis_result JSONB,
    processing_time DECIMAL DEFAULT 0.0
)
RETURNS BOOLEAN AS $$
DECLARE
    risk_score DECIMAL;
    confidence DECIMAL;
BEGIN
    -- Validate the analysis result
    IF NOT validate_analysis_result(analysis_result) THEN
        RAISE EXCEPTION 'Invalid analysis result structure';
    END IF;

    -- Extract metrics
    risk_score := (analysis_result->'executive_summary'->>'overall_risk_score')::DECIMAL;
    confidence := (analysis_result->'executive_summary'->>'confidence_level')::DECIMAL;

    -- Update the analysis record
    UPDATE contract_analyses
    SET 
        status = 'completed',
        executive_summary = analysis_result->'executive_summary',
        risk_assessment = analysis_result->'risk_assessment',
        compliance_check = analysis_result->'compliance_check',
        recommendations = COALESCE(analysis_result->'recommendations', '[]'::JSONB),
        overall_risk_score = risk_score,
        confidence_level = confidence,
        processing_time_seconds = processing_time,
        analysis_timestamp = NOW()
    WHERE id = analysis_id;

    -- Update progress to 100%
    PERFORM calculate_analysis_progress(analysis_id, 'finalization', 6);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up old analysis progress records
CREATE OR REPLACE FUNCTION cleanup_old_analysis_progress()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete progress records older than 7 days for completed analyses
    DELETE FROM analysis_progress
    WHERE updated_at < NOW() - INTERVAL '7 days'
    AND analysis_id IN (
        SELECT id FROM contract_analyses 
        WHERE status IN ('completed', 'failed')
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user statistics
CREATE OR REPLACE FUNCTION get_user_statistics(user_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    stats JSONB;
BEGIN
    -- Only allow users to get their own stats or service role
    IF auth.uid() != user_uuid AND auth.jwt() ->> 'role' != 'service_role' THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    SELECT jsonb_build_object(
        'total_documents', COALESCE(doc_stats.total_documents, 0),
        'total_analyses', COALESCE(analysis_stats.total_analyses, 0),
        'completed_analyses', COALESCE(analysis_stats.completed_analyses, 0),
        'avg_risk_score', COALESCE(analysis_stats.avg_risk_score, 0),
        'credits_used_this_month', COALESCE(usage_stats.credits_used_this_month, 0),
        'last_analysis_date', analysis_stats.last_analysis_date,
        'subscription_status', p.subscription_status,
        'credits_remaining', p.credits_remaining
    ) INTO stats
    FROM public.profiles p
    LEFT JOIN (
        SELECT 
            user_id,
            COUNT(*) as total_documents
        FROM documents
        WHERE user_id = user_uuid
        GROUP BY user_id
    ) doc_stats ON p.id = doc_stats.user_id
    LEFT JOIN (
        SELECT 
            user_id,
            COUNT(*) as total_analyses,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_analyses,
            AVG(overall_risk_score) FILTER (WHERE status = 'completed') as avg_risk_score,
            MAX(analysis_timestamp) FILTER (WHERE status = 'completed') as last_analysis_date
        FROM contract_analyses
        WHERE user_id = user_uuid
        GROUP BY user_id
    ) analysis_stats ON p.id = analysis_stats.user_id
    LEFT JOIN (
        SELECT 
            user_id,
            SUM(credits_used) as credits_used_this_month
        FROM usage_logs
        WHERE user_id = user_uuid
        AND timestamp >= date_trunc('month', CURRENT_DATE)
        GROUP BY user_id
    ) usage_stats ON p.id = usage_stats.user_id
    WHERE p.id = user_uuid;

    RETURN stats;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Final verification and status report for timestamp management
DO $$
DECLARE
    status_record RECORD;
    total_tables INTEGER := 0;
    optimal_tables INTEGER := 0;
BEGIN
    RAISE NOTICE 'Timestamp Management Migration Complete';
    RAISE NOTICE '=====================================';
    
    FOR status_record IN 
        SELECT table_name, status FROM timestamp_management_status ORDER BY table_name
    LOOP
        total_tables := total_tables + 1;
        IF status_record.status = 'OPTIMAL' THEN
            optimal_tables := optimal_tables + 1;
        END IF;
        
        RAISE NOTICE 'Table: % - Status: %', status_record.table_name, status_record.status;
    END LOOP;
    
    RAISE NOTICE '=====================================';
    RAISE NOTICE 'Summary: %/% tables have optimal timestamp management', optimal_tables, total_tables;
    RAISE NOTICE 'Run "SELECT * FROM timestamp_management_status;" to verify configuration';
END $$;

-- Function to handle upsert for contract_analyses (prevents duplicate key errors)
CREATE OR REPLACE FUNCTION upsert_contract_analysis(
    p_content_hash TEXT,
    p_agent_version TEXT DEFAULT '1.0',
    p_status analysis_status DEFAULT 'pending',
    p_analysis_result JSONB DEFAULT '{}',
    p_error_message TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_analysis_id UUID;
BEGIN
    -- Try to insert new record
    INSERT INTO contract_analyses (
        content_hash,
        agent_version,
        status,
        analysis_result,
        error_message,
        analysis_timestamp,
        created_at,
        updated_at
    ) VALUES (
        p_content_hash,
        p_agent_version,
        p_status,
        p_analysis_result,
        p_error_message,
        NOW(),
        NOW(),
        NOW()
    ) ON CONFLICT (content_hash) DO UPDATE SET
        status = EXCLUDED.status,
        analysis_result = EXCLUDED.analysis_result,
        error_message = EXCLUDED.error_message,
        updated_at = NOW()
    RETURNING id INTO v_analysis_id;
    
    RETURN v_analysis_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to safely retry analysis
CREATE OR REPLACE FUNCTION retry_contract_analysis(
    p_content_hash TEXT,
    p_user_id UUID
) RETURNS UUID AS $$
DECLARE
    v_analysis_id UUID;
    v_existing_status analysis_status;
BEGIN
    -- Check if analysis already exists
    SELECT id, status INTO v_analysis_id, v_existing_status
    FROM contract_analyses
    WHERE content_hash = p_content_hash;
    
    -- If analysis exists and failed or was cancelled, reset it for retry
    -- Note: Successfully completed analyses should NOT be retried
    IF v_analysis_id IS NOT NULL AND v_existing_status IN ('failed', 'cancelled') THEN
        UPDATE contract_analyses
        SET 
            status = 'pending',
            error_message = NULL,
            analysis_result = '{}',
            executive_summary = NULL,
            risk_assessment = NULL,
            compliance_check = NULL,
            recommendations = NULL,
            risk_score = 0,
            overall_risk_score = 0,
            processing_time = NULL,
            processing_completed_at = NULL,
            updated_at = NOW()
        WHERE id = v_analysis_id;
    -- If analysis doesn't exist, create new one
    ELSIF v_analysis_id IS NULL THEN
        v_analysis_id := upsert_contract_analysis(p_content_hash);
    -- If analysis exists and is completed, don't retry - return the existing ID
    ELSIF v_existing_status = 'completed' THEN
        -- Analysis already completed successfully, no retry needed
        -- Return existing analysis_id without modification
        NULL; -- No action needed
    END IF;
    
    RETURN v_analysis_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comments for documentation
COMMENT ON FUNCTION upsert_contract_analysis IS 'Upsert function for contract analyses to handle duplicate content_hash';
COMMENT ON FUNCTION retry_contract_analysis IS 'Safely retry analysis by checking existing status - only retries failed/cancelled analyses, not completed ones';

-- Safely cancel user's analysis without mutating shared rows
-- Scopes cancellation to user-owned progress; avoids direct writes to shared contract_analyses
CREATE OR REPLACE FUNCTION cancel_user_contract_analysis(
    p_content_hash TEXT,
    p_user_id UUID
)
RETURNS VOID AS $$
BEGIN
    -- Cancel any in-progress user-scoped analysis progress rows
    UPDATE analysis_progress
    SET status = 'cancelled',
        error_message = 'Analysis cancelled by user'
    WHERE content_hash = p_content_hash
      AND user_id = p_user_id
      AND status = 'in_progress';

    -- Do NOT mutate shared contract_analyses here to prevent cross-user impact
    -- Optionally, we could insert an audit log if needed.
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION cancel_user_contract_analysis(TEXT, UUID) IS 'Cancel user-scoped analysis progress; leaves shared contract_analyses untouched.';