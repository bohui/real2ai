-- Core tables
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone_number TEXT,
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    user_type user_type NOT NULL DEFAULT 'buyer',
    user_role TEXT NOT NULL DEFAULT 'user' CHECK (user_role IN ('user','admin')),
    subscription_status subscription_status NOT NULL DEFAULT 'free',
    credits_remaining INTEGER NOT NULL DEFAULT 1,
    organization TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_completed_at TIMESTAMP WITH TIME ZONE,
    onboarding_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    content_hash TEXT,
    processing_status TEXT NOT NULL DEFAULT 'uploaded',
    upload_metadata JSONB DEFAULT '{}'::jsonb,
    processing_results JSONB DEFAULT '{}'::jsonb,
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    overall_quality_score FLOAT DEFAULT 0.0,
    extraction_confidence FLOAT DEFAULT 0.0,
    text_extraction_method VARCHAR(100),
    total_pages INTEGER DEFAULT 0,
    total_text_length INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    has_diagrams BOOLEAN DEFAULT FALSE,
    diagram_count INTEGER DEFAULT 0,
    document_type VARCHAR(100),
    australian_state VARCHAR(10),
    contract_type contract_type DEFAULT 'unknown',
    processing_errors JSONB,
    processing_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS artifact_text_id UUID;

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL,
    contract_type contract_type NOT NULL DEFAULT 'unknown',
    state australian_state NOT NULL DEFAULT 'NSW',
    purchase_method purchase_method,
    use_category use_category,
    ocr_confidence JSONB DEFAULT '{}'::jsonb,
    contract_terms JSONB DEFAULT '{}'::jsonb,
    extracted_entity JSONB DEFAULT '{}'::jsonb,
    raw_text TEXT,
    property_address TEXT,
    updated_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Validation function and constraints for contract taxonomy
CREATE OR REPLACE FUNCTION validate_contract_taxonomy(
    p_contract_type contract_type,
    p_purchase_method purchase_method,
    p_use_category use_category
) RETURNS boolean AS $$
BEGIN
    -- Purchase agreements must have purchase_method; use_category optional
    IF p_contract_type = 'purchase_agreement' THEN
        IF p_purchase_method IS NULL THEN
            RETURN FALSE;
        END IF;
        RETURN TRUE;
    END IF;

    -- Lease agreements must not have purchase_method; use_category optional
    IF p_contract_type = 'lease_agreement' THEN
        IF p_purchase_method IS NOT NULL THEN
            RETURN FALSE;
        END IF;
        RETURN TRUE;
    END IF;

    -- Option to purchase must not have purchase_method or use_category
    IF p_contract_type = 'option_to_purchase' THEN
        IF p_purchase_method IS NOT NULL OR p_use_category IS NOT NULL THEN
            RETURN FALSE;
        END IF;
        RETURN TRUE;
    END IF;

    -- Unknown allows any combination
    IF p_contract_type = 'unknown' THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE contracts 
ADD CONSTRAINT contracts_purchase_method_dependency_check 
CHECK (
    (contract_type = 'purchase_agreement' AND purchase_method IS NOT NULL) OR
    (contract_type != 'purchase_agreement' AND purchase_method IS NULL)
);

ALTER TABLE contracts 
ADD CONSTRAINT contracts_use_category_dependency_check 
CHECK (
    (contract_type = 'option_to_purchase' AND use_category IS NULL) OR
    (contract_type != 'option_to_purchase')
);

ALTER TABLE contracts 
ADD CONSTRAINT contracts_taxonomy_validation_check 
CHECK (validate_contract_taxonomy(contract_type, purchase_method, use_category));

-- Indexes and comments for taxonomy fields
CREATE INDEX idx_contracts_purchase_method ON contracts(purchase_method);
CREATE INDEX idx_contracts_use_category ON contracts(use_category);
CREATE INDEX idx_contracts_taxonomy ON contracts(contract_type, purchase_method, use_category);

COMMENT ON COLUMN contracts.contract_type IS 'Authoritative user-provided contract classification';
COMMENT ON COLUMN contracts.purchase_method IS 'OCR-inferred purchase method, only when contract_type = purchase_agreement';
COMMENT ON COLUMN contracts.use_category IS 'OCR-inferred property use category. Applied to purchase_agreement and lease_agreement types. Null for option_to_purchase.';
COMMENT ON COLUMN contracts.ocr_confidence IS 'Confidence scores for OCR-inferred fields';

-- Create analyses table for tracking analysis operations
-- This table stores analysis operations that can be shared across users
CREATE TABLE analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    agent_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_details JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    user_id UUID REFERENCES profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    
    -- Create unique constraint on content_hash and agent_version
    -- This allows the upsert pattern in the repository
    UNIQUE(content_hash, agent_version)
);

CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    credits_used INTEGER DEFAULT 0,
    credits_remaining INTEGER DEFAULT 0,
    resource_used TEXT, -- contract_analysis, document_upload, etc.
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    price_monthly FLOAT NOT NULL DEFAULT 0,
    price_annually FLOAT,
    credits_per_month INTEGER NOT NULL DEFAULT 0,
    max_file_size_mb INTEGER NOT NULL DEFAULT 50,
    features JSONB DEFAULT '{}'::jsonb,
    limits JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    plan_id UUID REFERENCES subscription_plans(id) NOT NULL,
    stripe_subscription_id TEXT,
    stripe_customer_id TEXT,
    status TEXT NOT NULL,
    trial_end TIMESTAMP WITH TIME ZONE,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);




-- RLS Configuration
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Enable RLS on user-specific tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" 
    ON profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON profiles FOR UPDATE 
    USING (auth.uid() = id)
    WITH CHECK (
        user_role = (SELECT user_role FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can insert own profile on signup" 
    ON profiles FOR INSERT 
    WITH CHECK (auth.uid() = id AND user_role = 'user');

-- Documents policies
CREATE POLICY "Users can view own documents" 
    ON documents FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents" 
    ON documents FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents" 
    ON documents FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents" 
    ON documents FOR DELETE 
    USING (auth.uid() = user_id);

-- Usage logs policies
CREATE POLICY "Users can view own usage logs" 
    ON usage_logs FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service can insert usage logs" 
    ON usage_logs FOR INSERT 
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role' OR auth.uid() = user_id);

-- User subscriptions policies
CREATE POLICY "Users can view own subscriptions" 
    ON user_subscriptions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service can manage subscriptions" 
    ON user_subscriptions FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Subscription plans are publicly readable (no RLS needed)
CREATE POLICY "Anyone can view active subscription plans" 
    ON subscription_plans FOR SELECT 
    TO anon, authenticated
    USING (active = true);

-- Possession-gated SELECT policies for shared tables
CREATE POLICY "read_if_user_has_hash"
    ON contracts FOR SELECT
    USING (
        -- Service role can access all contracts
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Users can access contracts they have access to through documents
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.user_id = auth.uid()
              AND d.content_hash = contracts.content_hash
        )
    );

-- Analyses policies
-- Policy: Users can see analyses they created or analyses without user_id (shared)
CREATE POLICY "Users can view own analyses or shared analyses" ON analyses
    FOR SELECT USING (
        user_id IS NULL OR 
        user_id = (current_setting('request.jwt.claim.sub'))::uuid
    );

-- Policy: Users can insert analyses 
CREATE POLICY "Users can create analyses" ON analyses
    FOR INSERT WITH CHECK (
        user_id IS NULL OR 
        user_id = (current_setting('request.jwt.claim.sub'))::uuid
    );

-- Policy: Users can update their own analyses or shared analyses
CREATE POLICY "Users can update own analyses or shared analyses" ON analyses
    FOR UPDATE USING (
        user_id IS NULL OR 
        user_id = (current_setting('request.jwt.claim.sub'))::uuid
    );

-- Policy: Users can delete their own analyses
CREATE POLICY "Users can delete own analyses" ON analyses
    FOR DELETE USING (
        user_id = (current_setting('request.jwt.claim.sub'))::uuid
    );

-- Create security definer functions for admin operations
CREATE OR REPLACE FUNCTION get_user_analytics(target_user_id UUID)
RETURNS JSON
SECURITY DEFINER
SET search_path = public, pg_temp
LANGUAGE plpgsql
AS $$
DECLARE
    result JSON;
BEGIN
    -- Only allow service role to access this function
    IF auth.jwt() ->> 'role' != 'service_role' THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    SELECT json_build_object(
        'total_documents', COUNT(d.id),
        'total_analyses', COUNT(a.id),
        'credits_used', COALESCE(SUM(ul.credits_used), 0),
        'last_activity', MAX(GREATEST(d.created_at, a.created_at))
    ) INTO result
    FROM profiles p
    LEFT JOIN documents d ON p.id = d.user_id
    LEFT JOIN analyses a ON a.user_id = p.id
    LEFT JOIN usage_logs ul ON p.id = ul.user_id
    WHERE p.id = target_user_id
    GROUP BY p.id;

    RETURN result;
END;
$$;

-- Function to safely update user credits (prevents race conditions)
CREATE OR REPLACE FUNCTION update_user_credits(
    target_user_id UUID,
    credit_change INTEGER,
    action_description TEXT DEFAULT 'Credit adjustment'
)
RETURNS INTEGER
SECURITY DEFINER
SET search_path = public, pg_temp
LANGUAGE plpgsql
AS $$
DECLARE
    new_credits INTEGER;
    current_credits INTEGER;
BEGIN
    -- Lock the user record to prevent concurrent updates
    SELECT credits_remaining INTO current_credits
    FROM profiles
    WHERE id = target_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found';
    END IF;

    -- Calculate new credits (cannot go below 0)
    new_credits := GREATEST(0, current_credits + credit_change);

    -- Update the user's credits
    UPDATE profiles
    SET credits_remaining = new_credits,
        updated_at = NOW()
    WHERE id = target_user_id;

    -- Log the credit change
    INSERT INTO usage_logs (user_id, action_type, credits_used, credits_remaining, metadata)
    VALUES (
        target_user_id,
        action_description,
        -credit_change, -- Negative for credits added, positive for credits used
        new_credits,
        json_build_object('previous_credits', current_credits, 'credit_change', credit_change)
    );

    RETURN new_credits;
END;
$$;

-- Function to check if user has sufficient credits
CREATE OR REPLACE FUNCTION check_user_credits(
    target_user_id UUID,
    required_credits INTEGER DEFAULT 1
)
RETURNS BOOLEAN
SECURITY DEFINER
SET search_path = public, pg_temp
LANGUAGE plpgsql
AS $$
DECLARE
    current_credits INTEGER;
BEGIN
    SELECT credits_remaining INTO current_credits
    FROM profiles
    WHERE id = target_user_id;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    RETURN current_credits >= required_credits;
END;
$$;

-- Trigger function for updating timestamps
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

COMMENT ON FUNCTION update_updated_at_column() IS 
'Automatically updates updated_at timestamp on row updates and preserves created_at';

-- Function to create a user profile after auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp
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
            MAX(created_at) FILTER (WHERE status = 'completed') as last_analysis_date
        FROM analyses
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


-- Trigger to automatically create profile on user signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Triggers for updated_at columns
CREATE TRIGGER update_profiles_updated_at 
    BEFORE UPDATE ON public.profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at 
    BEFORE UPDATE ON contracts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analyses_updated_at 
    BEFORE UPDATE ON analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


CREATE TRIGGER update_user_subscriptions_updated_at 
    BEFORE UPDATE ON user_subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Revoke direct access to shared tables and grant selective access
REVOKE ALL ON TABLE public.contracts FROM anon;
REVOKE ALL ON TABLE public.contracts FROM authenticated;

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON analyses TO authenticated;

-- Grant SELECT to authenticated so RLS policies can apply
GRANT SELECT ON TABLE public.contracts TO authenticated;
GRANT SELECT ON TABLE public.subscription_plans TO anon, authenticated;

-- Indexes for core tables
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_australian_state ON profiles(australian_state);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_profiles_onboarding_completed ON profiles(onboarding_completed);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_australian_state ON documents(australian_state);
CREATE INDEX idx_documents_contract_type ON documents(contract_type);
CREATE INDEX idx_documents_has_diagrams ON documents(has_diagrams);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_user_status ON documents(user_id, processing_status);

CREATE INDEX idx_contracts_content_hash ON contracts(content_hash);
CREATE INDEX idx_contracts_type_state ON contracts(contract_type, state);

-- Create indexes for better performance on analyses table
CREATE INDEX idx_analyses_content_hash ON analyses(content_hash);
CREATE INDEX idx_analyses_status ON analyses(status);
CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);
CREATE INDEX idx_analyses_agent_version ON analyses(agent_version);

-- Add comments for analyses table
COMMENT ON TABLE analyses IS 'Stores analysis operations with caching support based on content hash and agent version';
COMMENT ON COLUMN analyses.content_hash IS 'SHA-256 hash of the analyzed content for deduplication';
COMMENT ON COLUMN analyses.agent_version IS 'Version of the analysis agent used';
COMMENT ON COLUMN analyses.status IS 'Current status: pending, in_progress, completed, failed';
COMMENT ON COLUMN analyses.result IS 'Analysis result in JSON format';
COMMENT ON COLUMN analyses.error_details IS 'Error details if analysis failed';
COMMENT ON COLUMN analyses.user_id IS 'User who initiated analysis, null for shared analyses';

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_action_type ON usage_logs(action_type);


CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);

