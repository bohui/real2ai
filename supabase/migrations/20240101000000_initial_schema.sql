-- Initial schema migration for Real2.AI
-- Creates all core tables, relationships, and security policies

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create custom types
CREATE TYPE australian_state AS ENUM ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT');
CREATE TYPE user_type AS ENUM ('buyer', 'investor', 'agent');
CREATE TYPE subscription_status AS ENUM ('free', 'basic', 'premium', 'enterprise');
CREATE TYPE contract_type AS ENUM ('purchase_agreement', 'lease_agreement', 'off_plan', 'auction');
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'processed', 'failed');
CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- User profiles table (extends auth.users)
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

-- Documents table for file management
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    status document_status NOT NULL DEFAULT 'uploaded',
    upload_metadata JSONB DEFAULT '{}',
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contracts table for contract metadata
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    contract_type contract_type NOT NULL DEFAULT 'purchase_agreement',
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    contract_terms JSONB DEFAULT '{}',
    raw_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contract analyses table for AI analysis results
CREATE TABLE contract_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    agent_version TEXT NOT NULL DEFAULT '1.0',
    status analysis_status NOT NULL DEFAULT 'pending',
    
    -- Analysis results structure
    executive_summary JSONB DEFAULT '{}',
    risk_assessment JSONB DEFAULT '{}',
    compliance_check JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    
    -- Metrics
    overall_risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (overall_risk_score >= 0.0 AND overall_risk_score <= 10.0),
    confidence_level DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_level >= 0.0 AND confidence_level <= 1.0),
    processing_time_seconds DECIMAL(10,3) DEFAULT 0.0,
    
    -- Metadata
    analysis_metadata JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage logs for tracking and billing
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    action_type TEXT NOT NULL,
    credits_used INTEGER NOT NULL DEFAULT 0,
    credits_remaining INTEGER NOT NULL DEFAULT 0,
    resource_used TEXT, -- contract_analysis, document_upload, etc.
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property data table for enhanced property analysis
CREATE TABLE property_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Property details
    address TEXT NOT NULL,
    suburb TEXT,
    state australian_state,
    postcode TEXT,
    property_type TEXT,
    
    -- Property features
    bedrooms INTEGER,
    bathrooms INTEGER,
    car_spaces INTEGER,
    land_size DECIMAL(10,2),
    building_size DECIMAL(10,2),
    
    -- Financial data
    purchase_price DECIMAL(15,2),
    market_value DECIMAL(15,2),
    
    -- Analysis data
    market_analysis JSONB DEFAULT '{}',
    property_insights JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscription plans table
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    price_monthly DECIMAL(8,2) NOT NULL,
    price_annually DECIMAL(8,2),
    credits_per_month INTEGER NOT NULL,
    max_file_size_mb INTEGER DEFAULT 50,
    features JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User subscriptions table
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    plan_id UUID REFERENCES subscription_plans(id) NOT NULL,
    stripe_subscription_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'past_due', 'unpaid', 'trialing')),
    trial_end TIMESTAMP WITH TIME ZONE,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis progress tracking for real-time updates
CREATE TABLE analysis_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES contract_analyses(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    current_step TEXT NOT NULL,
    total_steps INTEGER NOT NULL DEFAULT 1,
    completed_steps INTEGER NOT NULL DEFAULT 0,
    progress_percentage DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    status_message TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance indexes
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_australian_state ON profiles(australian_state);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_profiles_onboarding_completed ON profiles(onboarding_completed);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

CREATE INDEX idx_contracts_user_id ON contracts(user_id);
CREATE INDEX idx_contracts_document_id ON contracts(document_id);
CREATE INDEX idx_contracts_type_state ON contracts(contract_type, australian_state);

CREATE INDEX idx_contract_analyses_contract_id ON contract_analyses(contract_id);
CREATE INDEX idx_contract_analyses_user_id ON contract_analyses(user_id);
CREATE INDEX idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX idx_contract_analyses_timestamp ON contract_analyses(analysis_timestamp DESC);
CREATE INDEX idx_contract_analyses_risk_score ON contract_analyses(overall_risk_score);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_action_type ON usage_logs(action_type);

CREATE INDEX idx_property_data_contract_id ON property_data(contract_id);
CREATE INDEX idx_property_data_location ON property_data(suburb, state, postcode);
CREATE INDEX idx_property_data_property_type ON property_data(property_type);

CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);

CREATE INDEX idx_analysis_progress_analysis_id ON analysis_progress(analysis_id);
CREATE INDEX idx_analysis_progress_user_id ON analysis_progress(user_id);

-- Create composite indexes for common queries
CREATE INDEX idx_documents_user_status ON documents(user_id, status);
CREATE INDEX idx_contracts_user_type ON contracts(user_id, contract_type);
CREATE INDEX idx_analyses_user_status ON contract_analyses(user_id, status);
CREATE INDEX idx_usage_logs_user_timestamp ON usage_logs(user_id, timestamp DESC);