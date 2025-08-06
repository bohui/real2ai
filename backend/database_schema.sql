-- OBSOLETE: Real2.AI Database Schema for Supabase
-- This file is outdated and kept for reference only
-- Use supabase/migrations/*.sql files for the actual schema
-- Australian Real Estate AI Assistant

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret-key';

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- User profiles table
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    australian_state TEXT NOT NULL CHECK (australian_state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT')),
    user_type TEXT NOT NULL CHECK (user_type IN ('buyer', 'investor', 'agent')) DEFAULT 'buyer',
    subscription_status TEXT NOT NULL DEFAULT 'free' CHECK (subscription_status IN ('free', 'basic', 'premium', 'enterprise')),
    credits_remaining INTEGER NOT NULL DEFAULT 1,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'queued_for_ocr', 'processing_ocr', 'reprocessing_ocr', 'ocr_failed')),
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contracts table
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    contract_type TEXT NOT NULL DEFAULT 'purchase_agreement' CHECK (contract_type IN ('purchase_agreement', 'lease_agreement', 'off_plan', 'auction')),
    australian_state TEXT NOT NULL CHECK (australian_state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT')),
    contract_terms JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contract analyses table
CREATE TABLE IF NOT EXISTS contract_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE NOT NULL,
    agent_version TEXT NOT NULL DEFAULT '1.0',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    analysis_result JSONB DEFAULT '{}',
    risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
    processing_time DECIMAL(10,3) DEFAULT 0.0,
    confidence_score DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OCR processing logs table
CREATE TABLE IF NOT EXISTS ocr_processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    task_id TEXT,
    processing_method TEXT NOT NULL DEFAULT 'gemini_2.5_pro',
    processing_options JSONB DEFAULT '{}',
    contract_context JSONB DEFAULT '{}',
    extraction_confidence DECIMAL(3,2) DEFAULT 0.0,
    character_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    processing_time_seconds DECIMAL(10,3) DEFAULT 0.0,
    cost_estimate_usd DECIMAL(8,4) DEFAULT 0.0,
    gemini_features_used JSONB DEFAULT '{}',
    contract_elements_found JSONB DEFAULT '{}',
    quality_metrics JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Batch processing logs table
CREATE TABLE IF NOT EXISTS batch_processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    document_ids JSONB NOT NULL,
    batch_options JSONB DEFAULT '{}',
    processing_options JSONB DEFAULT '{}',
    total_documents INTEGER NOT NULL,
    completed_documents INTEGER DEFAULT 0,
    failed_documents INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0.0,
    average_confidence DECIMAL(3,2) DEFAULT 0.0,
    total_processing_time_seconds DECIMAL(10,3) DEFAULT 0.0,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'partially_failed')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage logs table for tracking and billing
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    credits_used INTEGER NOT NULL DEFAULT 0,
    remaining_credits INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property data table (for future property analysis features)
CREATE TABLE IF NOT EXISTS property_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    suburb TEXT,
    state TEXT CHECK (state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT')),
    postcode TEXT,
    property_type TEXT,
    bedrooms INTEGER,
    bathrooms INTEGER,
    car_spaces INTEGER,
    land_size DECIMAL(10,2),
    building_size DECIMAL(10,2),
    market_value DECIMAL(15,2),
    market_analysis JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscription plans table
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    price_monthly DECIMAL(8,2) NOT NULL,
    price_annually DECIMAL(8,2),
    credits_per_month INTEGER NOT NULL,
    features JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    plan_id UUID REFERENCES subscription_plans(id) NOT NULL,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'past_due', 'unpaid')),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_contracts_user_id ON contracts(user_id);
CREATE INDEX IF NOT EXISTS idx_contracts_document_id ON contracts(document_id);
CREATE INDEX IF NOT EXISTS idx_contract_analyses_contract_id ON contract_analyses(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_ocr_logs_document_id ON ocr_processing_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_logs_user_id ON ocr_processing_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ocr_logs_status ON ocr_processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_ocr_logs_started_at ON ocr_processing_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_batch_logs_batch_id ON batch_processing_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_logs_user_id ON batch_processing_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_batch_logs_status ON batch_processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_property_data_address ON property_data(address, suburb, state);

-- Row Level Security Policies

-- Profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own documents" ON documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own documents" ON documents FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own documents" ON documents FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own documents" ON documents FOR DELETE USING (auth.uid() = user_id);

-- Contracts
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own contracts" ON contracts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own contracts" ON contracts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own contracts" ON contracts FOR UPDATE USING (auth.uid() = user_id);

-- Contract analyses
ALTER TABLE contract_analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own analyses" ON contract_analyses FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM contracts 
        WHERE contracts.id = contract_analyses.contract_id 
        AND contracts.user_id = auth.uid()
    )
);
CREATE POLICY "Users can insert own analyses" ON contract_analyses FOR INSERT WITH CHECK (
    EXISTS (
        SELECT 1 FROM contracts 
        WHERE contracts.id = contract_analyses.contract_id 
        AND contracts.user_id = auth.uid()
    )
);
CREATE POLICY "Users can update own analyses" ON contract_analyses FOR UPDATE USING (
    EXISTS (
        SELECT 1 FROM contracts 
        WHERE contracts.id = contract_analyses.contract_id 
        AND contracts.user_id = auth.uid()
    )
);

-- Usage logs
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own usage logs" ON usage_logs FOR SELECT USING (auth.uid() = user_id);

-- Property data
ALTER TABLE property_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own property data" ON property_data FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM contracts 
        WHERE contracts.id = property_data.contract_id 
        AND contracts.user_id = auth.uid()
    )
);

-- User subscriptions
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own subscriptions" ON user_subscriptions FOR SELECT USING (auth.uid() = user_id);

-- Functions

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contract_analyses_updated_at BEFORE UPDATE ON contract_analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_property_data_updated_at BEFORE UPDATE ON property_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_subscriptions_updated_at BEFORE UPDATE ON user_subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to validate Australian postcodes
CREATE OR REPLACE FUNCTION validate_australian_postcode(postcode TEXT, state TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    CASE state
        WHEN 'NSW' THEN RETURN postcode ~ '^(1|2)\d{3}$';
        WHEN 'ACT' THEN RETURN postcode ~ '^(0200|02\d{2}|26\d{2}|29\d{2}|291[0-9])$';
        WHEN 'VIC' THEN RETURN postcode ~ '^(3|8)\d{3}$';
        WHEN 'QLD' THEN RETURN postcode ~ '^(4|9)\d{3}$';
        WHEN 'SA' THEN RETURN postcode ~ '^5\d{3}$';
        WHEN 'WA' THEN RETURN postcode ~ '^6\d{3}$';
        WHEN 'TAS' THEN RETURN postcode ~ '^7\d{3}$';
        WHEN 'NT' THEN RETURN postcode ~ '^(08\d{2}|09\d{2})$';
        ELSE RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Insert default subscription plans
INSERT INTO subscription_plans (name, price_monthly, price_annually, credits_per_month, features) VALUES
('Free', 0.00, 0.00, 1, '{"features": ["1 contract analysis", "Basic risk assessment", "Standard support"]}'),
('Basic', 29.99, 299.99, 10, '{"features": ["10 contract analyses", "Advanced risk assessment", "Email support", "PDF reports"]}'),
('Premium', 79.99, 799.99, 50, '{"features": ["50 contract analyses", "Premium risk assessment", "Priority support", "Advanced reports", "Property insights"]}'),
('Enterprise', 199.99, 1999.99, 200, '{"features": ["200 contract analyses", "Enterprise risk assessment", "Dedicated support", "Custom reports", "API access", "White-label options"]}')
ON CONFLICT (name) DO NOTHING;

-- Create storage bucket policy (run this in Supabase dashboard)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('documents', 'documents', false);

-- Storage policy for documents bucket
-- CREATE POLICY "Users can upload own documents" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
-- CREATE POLICY "Users can view own documents" ON storage.objects FOR SELECT USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
-- CREATE POLICY "Users can delete own documents" ON storage.objects FOR DELETE USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);