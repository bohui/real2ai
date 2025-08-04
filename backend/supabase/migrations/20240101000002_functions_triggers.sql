-- Database functions and triggers for Real2.AI
-- Handles automated tasks, data validation, and business logic

-- Function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all relevant tables
CREATE TRIGGER update_profiles_updated_at 
    BEFORE UPDATE ON public.profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at 
    BEFORE UPDATE ON contracts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contract_analyses_updated_at 
    BEFORE UPDATE ON contract_analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_data_updated_at 
    BEFORE UPDATE ON property_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_subscriptions_updated_at 
    BEFORE UPDATE ON user_subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_progress_updated_at 
    BEFORE UPDATE ON analysis_progress 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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