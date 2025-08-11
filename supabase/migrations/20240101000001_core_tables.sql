-- Core tables
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone_number TEXT,
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    user_type user_type NOT NULL DEFAULT 'buyer',
    subscription_status subscription_status NOT NULL DEFAULT 'free',
    credits_remaining INTEGER NOT NULL DEFAULT 1,
    organization TEXT,
    preferences JSONB DEFAULT '{}',
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_completed_at TIMESTAMP WITH TIME ZONE,
    onboarding_preferences JSONB DEFAULT '{}',
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
    upload_metadata JSONB DEFAULT '{}',
    processing_results JSONB DEFAULT '{}',
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    overall_quality_score FLOAT DEFAULT 0.0,
    extraction_confidence FLOAT DEFAULT 0.0,
    text_extraction_method VARCHAR(100),
    full_text TEXT,
    total_pages INTEGER DEFAULT 0,
    total_text_length INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    has_diagrams BOOLEAN DEFAULT FALSE,
    diagram_count INTEGER DEFAULT 0,
    document_type VARCHAR(100),
    australian_state VARCHAR(10),
    contract_type VARCHAR(100),
    processing_errors JSONB,
    processing_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS artifact_text_id UUID;

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL,
    contract_type contract_type NOT NULL DEFAULT 'purchase_agreement',
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    contract_terms JSONB DEFAULT '{}',
    raw_text TEXT,
    property_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE contract_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL,
    agent_version TEXT NOT NULL DEFAULT '1.0',
    status analysis_status NOT NULL DEFAULT 'pending',
    analysis_result JSONB DEFAULT '{}',
    executive_summary JSONB DEFAULT '{}',
    risk_assessment JSONB DEFAULT '{}',
    compliance_check JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
    overall_risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (overall_risk_score >= 0.0 AND overall_risk_score <= 10.0),
    confidence_score DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_level DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_level >= 0.0 AND confidence_level <= 1.0),
    processing_time DECIMAL(10,3) DEFAULT 0.0,
    processing_time_seconds DECIMAL(10,3) DEFAULT 0.0,
    analysis_metadata JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    error_message TEXT,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    credits_used INTEGER DEFAULT 0,
    credits_remaining INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
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
    features JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{}',
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
ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;
ALTER TABLE contract_analyses DISABLE ROW LEVEL SECURITY;

-- Enable RLS on user-specific tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" 
    ON profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON profiles FOR UPDATE 
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile on signup" 
    ON profiles FOR INSERT 
    WITH CHECK (auth.uid() = id);

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

CREATE POLICY "read_if_user_has_hash"
    ON contract_analyses FOR SELECT
    USING (
        -- Service role can access all contract analyses
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Users can access analyses they have access to through documents
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.user_id = auth.uid()
              AND d.content_hash = contract_analyses.content_hash
        )
    );

-- Create security definer functions for admin operations
CREATE OR REPLACE FUNCTION get_user_analytics(target_user_id UUID)
RETURNS JSON
SECURITY DEFINER
SET search_path = public
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
        'total_analyses', COUNT(ca.id),
        'credits_used', COALESCE(SUM(ul.credits_used), 0),
        'avg_risk_score', COALESCE(AVG(ca.overall_risk_score), 0),
        'last_activity', MAX(GREATEST(d.created_at, ca.created_at))
    ) INTO result
    FROM profiles p
    LEFT JOIN documents d ON p.id = d.user_id
    LEFT JOIN contract_analyses ca ON p.id = ca.user_id
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
SET search_path = public
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
SET search_path = public
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

CREATE TRIGGER update_contract_analyses_updated_at 
    BEFORE UPDATE ON contract_analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


CREATE TRIGGER update_user_subscriptions_updated_at 
    BEFORE UPDATE ON user_subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Revoke direct access to shared tables and grant selective access
REVOKE ALL ON TABLE public.contract_analyses FROM anon;
REVOKE ALL ON TABLE public.contract_analyses FROM authenticated;
REVOKE ALL ON TABLE public.contracts FROM anon;
REVOKE ALL ON TABLE public.contracts FROM authenticated;

-- Grant SELECT to authenticated so RLS policies can apply
GRANT SELECT ON TABLE public.contracts TO authenticated;
GRANT SELECT ON TABLE public.contract_analyses TO authenticated;

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
CREATE INDEX idx_contracts_type_state ON contracts(contract_type, australian_state);

CREATE INDEX idx_contract_analyses_content_hash ON contract_analyses(content_hash);
CREATE INDEX idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX idx_contract_analyses_timestamp ON contract_analyses(analysis_timestamp DESC);
CREATE INDEX idx_contract_analyses_risk_score ON contract_analyses(overall_risk_score);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_action_type ON usage_logs(action_type);


CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);

