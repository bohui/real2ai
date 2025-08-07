-- Initial schema migration for Real2.AI
-- Creates all core tables, relationships, and enhanced features
-- Includes: onboarding tracking, analysis progress with real-time updates, and comprehensive functions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create custom types
CREATE TYPE australian_state AS ENUM ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT');
CREATE TYPE user_type AS ENUM ('buyer', 'investor', 'agent');
CREATE TYPE subscription_status AS ENUM ('free', 'basic', 'premium', 'enterprise');
CREATE TYPE contract_type AS ENUM ('purchase_agreement', 'lease_agreement', 'off_plan', 'auction');
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'basic_complete', 'analysis_pending', 'analysis_complete', 'failed');
CREATE TYPE content_type AS ENUM ('text', 'diagram', 'table', 'signature', 'mixed', 'empty');
CREATE TYPE diagram_type AS ENUM ('site_plan', 'sewer_diagram', 'flood_map', 'bushfire_map', 'title_plan', 'survey_diagram', 'floor_plan', 'elevation', 'unknown');
CREATE TYPE entity_type AS ENUM ('address', 'property_reference', 'date', 'financial_amount', 'party_name', 'legal_reference', 'contact_info', 'property_details');
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

-- Documents table for file management (enhanced with comprehensive processing fields)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    original_filename TEXT NOT NULL, -- Renamed from filename
    storage_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    content_hash TEXT, -- SHA-256 hash for duplicate detection and integrity verification
    processing_status TEXT NOT NULL DEFAULT 'uploaded', -- Renamed from status, flexible text type
    upload_metadata JSONB DEFAULT '{}',
    processing_results JSONB DEFAULT '{}',
    
    -- Processing timing
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Quality and extraction metrics
    overall_quality_score FLOAT DEFAULT 0.0,
    extraction_confidence FLOAT DEFAULT 0.0,
    text_extraction_method VARCHAR(100),
    
    -- Document content metrics
    total_pages INTEGER DEFAULT 0,
    total_text_length INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    has_diagrams BOOLEAN DEFAULT FALSE,
    diagram_count INTEGER DEFAULT 0,
    
    -- Classification
    document_type VARCHAR(100),
    australian_state VARCHAR(10),
    contract_type VARCHAR(100),
    
    -- Processing metadata
    processing_errors JSONB,
    processing_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contracts table for contract metadata
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    content_hash TEXT, -- Hash-based caching support
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
    content_hash TEXT, -- Hash-based caching support
    agent_version TEXT NOT NULL DEFAULT '1.0',
    status analysis_status NOT NULL DEFAULT 'pending',
    
    -- Analysis results structure (compatible with both old and new code)
    analysis_result JSONB DEFAULT '{}',
    executive_summary JSONB DEFAULT '{}',
    risk_assessment JSONB DEFAULT '{}',
    compliance_check JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    
    -- Metrics (compatible with both old and new code)
    risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
    overall_risk_score DECIMAL(3,2) DEFAULT 0.0 CHECK (overall_risk_score >= 0.0 AND overall_risk_score <= 10.0),
    confidence_score DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_level DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_level >= 0.0 AND confidence_level <= 1.0),
    processing_time DECIMAL(10,3) DEFAULT 0.0,
    processing_time_seconds DECIMAL(10,3) DEFAULT 0.0,
    
    -- Metadata
    analysis_metadata JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document pages table for page-level analysis
CREATE TABLE document_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    content_hash TEXT, -- Hash-based caching support
    page_number INTEGER NOT NULL,
    
    -- Content analysis
    content_summary TEXT,
    text_content TEXT,
    text_length INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    
    -- Content classification
    content_types TEXT[],  -- Array of content types
    primary_content_type content_type DEFAULT 'empty',
    
    -- Quality metrics
    extraction_confidence FLOAT DEFAULT 0.0,
    content_quality_score FLOAT DEFAULT 0.0,
    
    -- Layout analysis
    has_header BOOLEAN DEFAULT FALSE,
    has_footer BOOLEAN DEFAULT FALSE,
    has_signatures BOOLEAN DEFAULT FALSE,
    has_handwriting BOOLEAN DEFAULT FALSE,
    has_diagrams BOOLEAN DEFAULT FALSE,
    has_tables BOOLEAN DEFAULT FALSE,
    
    -- Processing metadata
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_method VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document entities table for extracted entities
CREATE TABLE document_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    content_hash TEXT, -- Hash-based caching support
    page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    
    -- Entity data
    entity_type entity_type NOT NULL,
    entity_value TEXT NOT NULL,
    normalized_value TEXT,
    
    -- Context and quality
    context TEXT,
    confidence FLOAT DEFAULT 0.0,
    extraction_method VARCHAR(100),
    
    -- Location metadata
    position_data JSONB,
    
    -- Processing metadata
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document diagrams table for diagram analysis
CREATE TABLE document_diagrams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    content_hash TEXT, -- Hash-based caching support
    page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    
    -- Classification
    diagram_type diagram_type DEFAULT 'unknown',
    classification_confidence FLOAT DEFAULT 0.0,
    
    -- Storage and processing
    extracted_image_path VARCHAR(1024),
    basic_analysis_completed BOOLEAN DEFAULT FALSE,
    detailed_analysis_completed BOOLEAN DEFAULT FALSE,
    
    -- Analysis results
    basic_analysis JSONB,
    
    -- Quality metrics
    image_quality_score FLOAT DEFAULT 0.0,
    clarity_score FLOAT DEFAULT 0.0,
    
    -- Metadata
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    basic_analysis_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document analyses table for comprehensive document analysis (separate from contract analysis)
CREATE TABLE document_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    
    -- Analysis metadata
    analysis_type VARCHAR(100) DEFAULT 'contract_analysis',
    analysis_version VARCHAR(50) DEFAULT 'v1.0',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Analysis status
    status VARCHAR(50) DEFAULT 'pending',
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    current_step VARCHAR(100),
    
    -- Results
    detailed_entities JSONB,
    diagram_analyses JSONB,
    compliance_results JSONB,
    risk_assessment JSONB,
    recommendations JSONB,
    
    -- Quality and confidence
    overall_confidence FLOAT DEFAULT 0.0,
    analysis_quality_score FLOAT DEFAULT 0.0,
    
    -- Processing metadata
    processing_time_seconds FLOAT DEFAULT 0.0,
    langgraph_workflow_id VARCHAR(255),
    
    -- Errors and issues
    analysis_errors JSONB,
    analysis_warnings JSONB,
    
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
-- Enhanced table with comprehensive progress tracking and timing
CREATE TABLE analysis_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE NOT NULL,
    analysis_id UUID REFERENCES contract_analyses(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Progress tracking
    current_step TEXT NOT NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    step_description TEXT,
    estimated_completion_minutes INTEGER,
    
    -- Timing information
    step_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    step_completed_at TIMESTAMP WITH TIME ZONE,
    total_elapsed_seconds INTEGER DEFAULT 0,
    
    -- Status and metadata
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance indexes
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

CREATE INDEX idx_analysis_progress_contract_id ON analysis_progress(contract_id);
CREATE INDEX idx_analysis_progress_analysis_id ON analysis_progress(analysis_id);
CREATE INDEX idx_analysis_progress_user_id ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_status ON analysis_progress(status);
CREATE INDEX idx_analysis_progress_created_at ON analysis_progress(created_at);

-- Indexes for new document processing tables
CREATE INDEX idx_document_pages_document_id ON document_pages(document_id);
CREATE INDEX idx_document_pages_page_number ON document_pages(page_number);
CREATE INDEX idx_document_pages_content_type ON document_pages(primary_content_type);

CREATE INDEX idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX idx_document_entities_page_id ON document_entities(page_id);
CREATE INDEX idx_document_entities_page_number ON document_entities(page_number);
CREATE INDEX idx_document_entities_type ON document_entities(entity_type);

CREATE INDEX idx_document_diagrams_document_id ON document_diagrams(document_id);
CREATE INDEX idx_document_diagrams_page_id ON document_diagrams(page_id);
CREATE INDEX idx_document_diagrams_page_number ON document_diagrams(page_number);
CREATE INDEX idx_document_diagrams_type ON document_diagrams(diagram_type);

CREATE INDEX idx_document_analyses_document_id ON document_analyses(document_id);
CREATE INDEX idx_document_analyses_status ON document_analyses(status);
CREATE INDEX idx_document_analyses_analysis_type ON document_analyses(analysis_type);

-- Create partial index for active progress tracking
CREATE INDEX idx_analysis_progress_active ON analysis_progress(contract_id, updated_at) 
WHERE status = 'in_progress';

-- Create composite indexes for common queries
CREATE INDEX idx_documents_user_status ON documents(user_id, processing_status);
CREATE INDEX idx_contracts_user_type ON contracts(user_id, contract_type);
CREATE INDEX idx_analyses_user_status ON contract_analyses(user_id, status);
CREATE INDEX idx_usage_logs_user_timestamp ON usage_logs(user_id, timestamp DESC);

-- Views for enhanced data access
-- View for analysis progress with contract and analysis details
CREATE OR REPLACE VIEW analysis_progress_detailed AS
SELECT 
    ap.*,
    c.contract_type,
    ca.agent_version,
    ca.status as analysis_status,
    d.original_filename as document_filename,
    d.file_type as document_file_type
FROM analysis_progress ap
JOIN contracts c ON ap.contract_id = c.id
JOIN contract_analyses ca ON ap.analysis_id = ca.id
JOIN documents d ON c.document_id = d.id;

-- Grant permissions on the view
GRANT SELECT ON analysis_progress_detailed TO authenticated;

-- Grant permissions on new document processing tables
GRANT ALL ON document_pages TO authenticated;
GRANT ALL ON document_entities TO authenticated;
GRANT ALL ON document_diagrams TO authenticated;
GRANT ALL ON document_analyses TO authenticated;

-- Comments for documentation
COMMENT ON TABLE analysis_progress IS 'Real-time progress tracking for contract analyses with comprehensive timing and status information';
COMMENT ON COLUMN analysis_progress.contract_id IS 'Reference to the contract being analyzed';
COMMENT ON COLUMN analysis_progress.current_step IS 'Current analysis step (validating_input, processing_document, etc.)';
COMMENT ON COLUMN analysis_progress.progress_percent IS 'Completion percentage (0-100)';
COMMENT ON COLUMN analysis_progress.step_description IS 'Human-readable description of current step';
COMMENT ON COLUMN analysis_progress.estimated_completion_minutes IS 'Estimated minutes to completion';
COMMENT ON COLUMN analysis_progress.total_elapsed_seconds IS 'Total processing time elapsed';
COMMENT ON COLUMN analysis_progress.status IS 'Overall status (in_progress, completed, failed, cancelled)';

COMMENT ON COLUMN profiles.onboarding_completed IS 'Tracks if user has completed initial onboarding process';
COMMENT ON COLUMN profiles.onboarding_completed_at IS 'Timestamp when user completed onboarding';
COMMENT ON COLUMN profiles.onboarding_preferences IS 'Preferences collected during onboarding process';

-- Comments for new document processing tables
COMMENT ON TABLE document_pages IS 'Individual page metadata and content from document processing';
COMMENT ON TABLE document_entities IS 'Basic entities extracted from documents (addresses, dates, amounts, etc.)';
COMMENT ON TABLE document_diagrams IS 'Diagram detection and basic analysis results';
COMMENT ON TABLE document_analyses IS 'Comprehensive document analysis results (separate from contract-specific analysis)';

COMMENT ON COLUMN documents.processing_status IS 'Document processing status (uploaded, processing, basic_complete, analysis_pending, analysis_complete, failed)';
COMMENT ON COLUMN documents.overall_quality_score IS 'Overall document quality score (0.0-1.0)';
COMMENT ON COLUMN documents.extraction_confidence IS 'Text extraction confidence score (0.0-1.0)';
COMMENT ON COLUMN documents.text_extraction_method IS 'Method used for text extraction (pymupdf, tesseract_ocr, gemini_ocr, etc.)';

-- Storage bucket management function
-- Ensures Supabase storage bucket exists for document uploads
CREATE OR REPLACE FUNCTION ensure_bucket_exists(bucket_name TEXT)
RETURNS JSON AS $$
DECLARE
    bucket_exists BOOLEAN;
    result JSON;
BEGIN
    -- Check if bucket exists
    SELECT EXISTS(
        SELECT 1 FROM storage.buckets WHERE id = bucket_name
    ) INTO bucket_exists;
    
    IF bucket_exists THEN
        -- Bucket already exists
        result := json_build_object(
            'created', false,
            'bucket_name', bucket_name,
            'message', 'Bucket already exists'
        );
    ELSE
        -- Create the bucket
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            bucket_name,
            bucket_name,
            false,  -- Private bucket
            52428800,  -- 50MB limit
            ARRAY[
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain',
                'image/jpeg',
                'image/png',
                'image/gif',
                'image/webp'
            ]
        );
        
        result := json_build_object(
            'created', true,
            'bucket_name', bucket_name,
            'message', 'Bucket created successfully'
        );
    END IF;
    
    RETURN result;
EXCEPTION
    WHEN OTHERS THEN
        -- Return error information
        result := json_build_object(
            'created', false,
            'bucket_name', bucket_name,
            'error', SQLERRM,
            'message', 'Failed to create bucket'
        );
        RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions on bucket function
GRANT EXECUTE ON FUNCTION ensure_bucket_exists(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ensure_bucket_exists(TEXT) TO service_role;

-- =====================================================
-- CACHE ARCHITECTURE EXTENSION
-- =====================================================
-- Hash-based content caching with RLS for user privacy
-- Transforms existing document/contract processing to support shared analysis results

-- Content hash columns now included directly in table definitions above
-- This eliminates the need for ALTER TABLE statements

-- =====================================================
-- PROPERTY INTELLIGENCE SCHEMA
-- =====================================================
-- Comprehensive property data, market analysis, and user tracking

-- Property core data tables
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address_full TEXT NOT NULL,
    unit_number TEXT,
    street_number TEXT NOT NULL,
    street_name TEXT NOT NULL,
    street_type TEXT NOT NULL,
    suburb TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT')),
    postcode TEXT NOT NULL CHECK (postcode ~ '^\d{4}$'),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    map_certainty INTEGER,
    property_type TEXT NOT NULL CHECK (property_type IN ('House', 'Unit', 'Apartment', 'Townhouse', 'Villa', 'Land')),
    bedrooms INTEGER,
    bathrooms INTEGER,
    carspaces INTEGER,
    land_area DECIMAL(10, 2), -- in sqm
    building_area DECIMAL(10, 2), -- in sqm
    year_built INTEGER,
    features JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(address_full, suburb, state, postcode)
);

-- Property valuations from different sources
CREATE TABLE IF NOT EXISTS property_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    valuation_source TEXT NOT NULL CHECK (valuation_source IN ('domain', 'corelogic', 'combined')),
    valuation_type TEXT NOT NULL CHECK (valuation_type IN ('avm', 'desktop', 'professional')),
    estimated_value DECIMAL(15, 2) NOT NULL,
    valuation_range_lower DECIMAL(15, 2),
    valuation_range_upper DECIMAL(15, 2),
    confidence DECIMAL(3, 2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    methodology TEXT,
    valuation_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    api_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data and analytics
CREATE TABLE IF NOT EXISTS property_market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    suburb TEXT NOT NULL,
    state TEXT NOT NULL,
    data_source TEXT NOT NULL CHECK (data_source IN ('domain', 'corelogic', 'combined')),
    median_price DECIMAL(15, 2),
    price_growth_12_month DECIMAL(5, 2), -- percentage
    price_growth_3_year DECIMAL(5, 2), -- percentage
    days_on_market INTEGER,
    sales_volume_12_month INTEGER,
    market_outlook TEXT CHECK (market_outlook IN ('declining', 'stable', 'growing', 'strong_growth')),
    median_rent DECIMAL(10, 2), -- weekly
    rental_yield DECIMAL(5, 2), -- percentage
    vacancy_rate DECIMAL(5, 2), -- percentage
    data_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk assessment data
CREATE TABLE IF NOT EXISTS property_risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    overall_risk TEXT NOT NULL CHECK (overall_risk IN ('low', 'medium', 'high', 'critical')),
    liquidity_risk TEXT NOT NULL CHECK (liquidity_risk IN ('low', 'medium', 'high', 'critical')),
    market_risk TEXT NOT NULL CHECK (market_risk IN ('low', 'medium', 'high', 'critical')),
    structural_risk TEXT NOT NULL CHECK (structural_risk IN ('low', 'medium', 'high', 'critical')),
    risk_factors JSONB DEFAULT '[]',
    risk_score DECIMAL(5, 2) CHECK (risk_score >= 0.0 AND risk_score <= 100.0),
    confidence DECIMAL(3, 2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    assessment_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    assessment_methodology TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comparable sales data
CREATE TABLE IF NOT EXISTS comparable_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    comparable_address TEXT NOT NULL,
    comparable_property_id UUID REFERENCES properties(id),
    sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sale_price DECIMAL(15, 2) NOT NULL,
    sale_type TEXT CHECK (sale_type IN ('Sold', 'Auction', 'Private Sale', 'Tender')),
    days_on_market INTEGER,
    bedrooms INTEGER,
    bathrooms INTEGER,
    carspaces INTEGER,
    land_area DECIMAL(10, 2),
    building_area DECIMAL(10, 2),
    similarity_score DECIMAL(3, 2) CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0),
    adjusted_price DECIMAL(15, 2),
    adjustments JSONB DEFAULT '{}',
    distance_meters INTEGER,
    data_source TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property sales history
CREATE TABLE IF NOT EXISTS property_sales_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sale_price DECIMAL(15, 2) NOT NULL,
    sale_type TEXT CHECK (sale_type IN ('Sold', 'Auction', 'Private Sale', 'Tender', 'Withdrawn')),
    days_on_market INTEGER,
    listing_agent TEXT,
    data_source TEXT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property rental history
CREATE TABLE IF NOT EXISTS property_rental_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    lease_date TIMESTAMP WITH TIME ZONE NOT NULL,
    weekly_rent DECIMAL(10, 2) NOT NULL,
    lease_type TEXT CHECK (lease_type IN ('Leased', 'Relisted', 'Available', 'Withdrawn')),
    lease_duration TEXT,
    bond_amount DECIMAL(10, 2),
    data_source TEXT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User saved properties and watchlists
CREATE TABLE IF NOT EXISTS user_saved_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    tags JSONB DEFAULT '[]',
    alert_preferences JSONB DEFAULT '{}', -- price change alerts, market updates, etc.
    is_favorite BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, property_id)
);

-- Property search history and analytics
CREATE TABLE IF NOT EXISTS property_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    search_filters JSONB DEFAULT '{}',
    results_count INTEGER,
    search_location TEXT,
    search_type TEXT CHECK (search_type IN ('address', 'suburb', 'filters', 'map_bounds')),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property reports cache
CREATE TABLE IF NOT EXISTS property_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL CHECK (report_type IN ('basic', 'standard', 'premium', 'investment')),
    report_data JSONB NOT NULL,
    data_sources_used JSONB DEFAULT '[]',
    processing_time DECIMAL(10, 3),
    total_cost DECIMAL(10, 2),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_public BOOLEAN DEFAULT FALSE
);

-- API usage tracking for external services
CREATE TABLE IF NOT EXISTS property_api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    api_provider TEXT NOT NULL CHECK (api_provider IN ('domain', 'corelogic', 'google_maps')),
    endpoint TEXT NOT NULL,
    request_type TEXT NOT NULL,
    cost_aud DECIMAL(10, 4),
    response_time_ms INTEGER,
    request_successful BOOLEAN NOT NULL,
    error_message TEXT,
    request_metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market insights and trends cache
CREATE TABLE IF NOT EXISTS market_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suburb TEXT NOT NULL,
    state TEXT NOT NULL,
    property_type TEXT,
    insight_type TEXT NOT NULL CHECK (insight_type IN ('trend', 'forecast', 'comparison', 'hotspot')),
    insight_data JSONB NOT NULL,
    confidence_score DECIMAL(3, 2),
    data_sources JSONB DEFAULT '[]',
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(suburb, state, property_type, insight_type, valid_from)
);

-- Property intelligence indexes for performance
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(suburb, state, postcode);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_coords ON properties(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_properties_address_full ON properties USING gin(to_tsvector('english', address_full));

CREATE INDEX IF NOT EXISTS idx_valuations_property_source ON property_valuations(property_id, valuation_source);
CREATE INDEX IF NOT EXISTS idx_valuations_date ON property_valuations(valuation_date DESC);
CREATE INDEX IF NOT EXISTS idx_valuations_expires ON property_valuations(expires_at);

CREATE INDEX IF NOT EXISTS idx_market_data_location ON property_market_data(suburb, state);
CREATE INDEX IF NOT EXISTS idx_market_data_date ON property_market_data(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_expires ON property_market_data(expires_at);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_property ON property_risk_assessments(property_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_date ON property_risk_assessments(assessment_date DESC);

CREATE INDEX IF NOT EXISTS idx_comparable_sales_property ON comparable_sales(property_id);
CREATE INDEX IF NOT EXISTS idx_comparable_sales_date ON comparable_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_comparable_sales_similarity ON comparable_sales(similarity_score DESC);

CREATE INDEX IF NOT EXISTS idx_sales_history_property ON property_sales_history(property_id);
CREATE INDEX IF NOT EXISTS idx_sales_history_date ON property_sales_history(sale_date DESC);

CREATE INDEX IF NOT EXISTS idx_rental_history_property ON property_rental_history(property_id);
CREATE INDEX IF NOT EXISTS idx_rental_history_date ON property_rental_history(lease_date DESC);

CREATE INDEX IF NOT EXISTS idx_saved_properties_user ON user_saved_properties(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_properties_saved_at ON user_saved_properties(saved_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_properties_favorite ON user_saved_properties(user_id, is_favorite) WHERE is_favorite = true;

CREATE INDEX IF NOT EXISTS idx_property_searches_user ON property_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_property_searches_date ON property_searches(executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_property_reports_property ON property_reports(property_id);
CREATE INDEX IF NOT EXISTS idx_property_reports_user ON property_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_property_reports_expires ON property_reports(expires_at);

CREATE INDEX IF NOT EXISTS idx_api_usage_user_timestamp ON property_api_usage(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON property_api_usage(api_provider, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_market_insights_location ON market_insights(suburb, state, property_type);
CREATE INDEX IF NOT EXISTS idx_market_insights_valid ON market_insights(valid_from, valid_until);

-- Hot Properties Cache (No RLS - Shared across users)
CREATE TABLE IF NOT EXISTS hot_properties_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_hash TEXT NOT NULL UNIQUE, -- Hash of normalized address
    property_address TEXT NOT NULL,
    normalized_address TEXT NOT NULL, -- For consistent hashing
    analysis_result JSONB NOT NULL,
    popularity_score INTEGER DEFAULT 1,
    access_count INTEGER DEFAULT 1,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hot Contracts Cache (No RLS - Shared across users)
CREATE TABLE IF NOT EXISTS hot_contracts_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL UNIQUE,
    contract_analysis JSONB NOT NULL,
    property_address TEXT,
    contract_type TEXT,
    access_count INTEGER DEFAULT 1,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Property Views (With RLS - User's search history)
CREATE TABLE IF NOT EXISTS user_property_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    property_hash TEXT NOT NULL,
    property_address TEXT NOT NULL,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT DEFAULT 'search' CHECK (source IN ('search', 'bookmark', 'analysis')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Contract Views (With RLS - User's contract analysis history)
CREATE TABLE IF NOT EXISTS user_contract_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    property_address TEXT,
    analysis_id UUID, -- References contract_analyses.id for permanent storage
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT DEFAULT 'upload' CHECK (source IN ('upload', 'cache_hit', 'shared')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on user-specific tables
ALTER TABLE user_property_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_contract_views ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_property_views
CREATE POLICY "Users can view own property searches" 
ON user_property_views FOR ALL 
USING (auth.uid() = user_id);

-- RLS Policies for user_contract_views
CREATE POLICY "Users can view own contract history" 
ON user_contract_views FOR ALL 
USING (auth.uid() = user_id);

-- Remove RLS from shared data tables (allow cross-user access to processed data)
ALTER TABLE document_pages DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_diagrams DISABLE ROW LEVEL SECURITY;
ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;
ALTER TABLE contract_analyses DISABLE ROW LEVEL SECURITY;

-- Hot caches indexes
CREATE INDEX IF NOT EXISTS idx_hot_properties_hash ON hot_properties_cache(property_hash);
CREATE INDEX IF NOT EXISTS idx_hot_properties_expires ON hot_properties_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_hot_properties_popularity ON hot_properties_cache(popularity_score DESC);
CREATE INDEX IF NOT EXISTS idx_hot_properties_address ON hot_properties_cache(property_address);

CREATE INDEX IF NOT EXISTS idx_hot_contracts_hash ON hot_contracts_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_hot_contracts_expires ON hot_contracts_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_hot_contracts_access ON hot_contracts_cache(access_count DESC);
CREATE INDEX IF NOT EXISTS idx_hot_contracts_property ON hot_contracts_cache(property_address);

-- User history indexes
CREATE INDEX IF NOT EXISTS idx_user_property_views_user ON user_property_views(user_id);
CREATE INDEX IF NOT EXISTS idx_user_property_views_hash ON user_property_views(property_hash);
CREATE INDEX IF NOT EXISTS idx_user_property_views_viewed ON user_property_views(viewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_contract_views_user ON user_contract_views(user_id);
CREATE INDEX IF NOT EXISTS idx_user_contract_views_content_hash ON user_contract_views(content_hash);
CREATE INDEX IF NOT EXISTS idx_user_contract_views_viewed ON user_contract_views(viewed_at DESC);

-- Composite index for efficient user + content_hash lookups
CREATE INDEX IF NOT EXISTS idx_user_contract_views_user_hash ON user_contract_views(user_id, content_hash);

-- Content-hash based lookup indexes for shared tables (primary cache lookup method)
CREATE INDEX IF NOT EXISTS idx_document_pages_content_hash ON document_pages(content_hash);
CREATE INDEX IF NOT EXISTS idx_document_entities_content_hash ON document_entities(content_hash);
CREATE INDEX IF NOT EXISTS idx_document_diagrams_content_hash ON document_diagrams(content_hash);
CREATE INDEX IF NOT EXISTS idx_contracts_content_hash ON contracts(content_hash);
CREATE INDEX IF NOT EXISTS idx_contract_analyses_content_hash ON contract_analyses(content_hash);

-- Keep document_id indexes for user-specific operations (when user owns document)
CREATE INDEX IF NOT EXISTS idx_document_pages_document_id ON document_pages(document_id);
CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_document_diagrams_document_id ON document_diagrams(document_id);
CREATE INDEX IF NOT EXISTS idx_contracts_document_id ON contracts(document_id);

-- Composite indexes for efficient cache + user operations
CREATE INDEX IF NOT EXISTS idx_document_pages_content_hash_user ON document_pages(content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_content_hash_user ON contracts(content_hash, user_id) WHERE content_hash IS NOT NULL;

-- Function to normalize addresses for consistent hashing
CREATE OR REPLACE FUNCTION normalize_address(address TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Normalize address for consistent hashing
    RETURN LOWER(
        TRIM(
            REGEXP_REPLACE(
                REGEXP_REPLACE(address, '[^\w\s]', '', 'g'), -- Remove punctuation
                '\s+', ' ', 'g' -- Normalize whitespace
            )
        )
    );
END;
$$;

-- Function to generate property hash
CREATE OR REPLACE FUNCTION generate_property_hash(address TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN ENCODE(SHA256(normalize_address(address)::bytea), 'hex');
END;
$$;

-- Function to cleanup expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS TABLE(
    properties_deleted INTEGER,
    contracts_deleted INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    props_deleted INTEGER;
    contracts_deleted INTEGER;
BEGIN
    -- Clean expired property cache
    DELETE FROM hot_properties_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS props_deleted = ROW_COUNT;
    
    -- Clean expired contract cache
    DELETE FROM hot_contracts_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS contracts_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT props_deleted, contracts_deleted;
END;
$$;

-- Function to update cache popularity
CREATE OR REPLACE FUNCTION increment_cache_popularity(
    cache_type TEXT,
    hash_value TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    IF cache_type = 'property' THEN
        UPDATE hot_properties_cache 
        SET 
            popularity_score = popularity_score + 1,
            access_count = access_count + 1,
            expires_at = GREATEST(expires_at, NOW() + INTERVAL '2 days'),
            updated_at = NOW()
        WHERE property_hash = hash_value;
        
        RETURN FOUND;
        
    ELSIF cache_type = 'contract' THEN
        UPDATE hot_contracts_cache 
        SET 
            access_count = access_count + 1,
            expires_at = GREATEST(expires_at, NOW() + INTERVAL '1 day'),
            updated_at = NOW()
        WHERE content_hash = hash_value;
        
        RETURN FOUND;
    END IF;
    
    RETURN FALSE;
END;
$$;

-- Grant permissions on cache tables
GRANT SELECT, INSERT, UPDATE ON hot_properties_cache TO authenticated;
GRANT SELECT, INSERT, UPDATE ON hot_contracts_cache TO authenticated;
GRANT ALL ON user_property_views TO authenticated;
GRANT ALL ON user_contract_views TO authenticated;

-- Function to process cache hits (runs with elevated privileges)
-- Simplified to use only content_hash for consistency
CREATE OR REPLACE FUNCTION process_contract_cache_hit(
    p_user_id UUID,
    p_content_hash TEXT,
    p_filename TEXT DEFAULT 'Cached Document',
    p_file_size BIGINT DEFAULT 0,
    p_mime_type TEXT DEFAULT 'application/pdf',
    p_property_address TEXT DEFAULT NULL
) RETURNS TABLE(
    document_id UUID,
    analysis_id UUID,
    view_id UUID
)
LANGUAGE plpgsql
SECURITY DEFINER -- Run with elevated privileges
AS $$
DECLARE
    new_doc_id UUID;
    analysis_rec RECORD;
    new_view_id UUID;
BEGIN
    -- Create user's document record for cache hit
    INSERT INTO documents (
        user_id, 
        content_hash, 
        original_filename, 
        storage_path, 
        file_type, 
        file_size,
        processing_status,
        processing_completed_at
    ) VALUES (
        p_user_id, 
        p_content_hash, 
        p_filename, 
        'cache/' || p_content_hash, 
        p_mime_type, 
        p_file_size,
        'analysis_complete',
        NOW()
    ) RETURNING id INTO new_doc_id;
    
    -- Get the cached analysis
    SELECT ca.id, ca.* INTO analysis_rec 
    FROM contract_analyses ca 
    WHERE ca.content_hash = p_content_hash 
    LIMIT 1;
    
    -- Create user's contract record
    INSERT INTO contracts (
        document_id, 
        user_id, 
        content_hash,
        contract_type,
        australian_state,
        contract_terms,
        raw_text
    ) 
    SELECT 
        new_doc_id,
        p_user_id,
        p_content_hash,
        COALESCE(analysis_rec.analysis_result->>'contract_type', 'purchase_agreement')::contract_type,
        COALESCE(analysis_rec.analysis_result->>'state', 'NSW')::australian_state,
        analysis_rec.analysis_result->'contract_terms',
        analysis_rec.analysis_result->>'raw_text'
    WHERE analysis_rec.id IS NOT NULL;
    
    -- Create user's analysis record (duplicate from cache)
    INSERT INTO contract_analyses (
        contract_id,
        user_id,
        content_hash,
        agent_version,
        status,
        analysis_result,
        executive_summary,
        risk_assessment,
        compliance_check,
        recommendations,
        risk_score,
        overall_risk_score,
        confidence_score,
        confidence_level,
        processing_time,
        processing_time_seconds,
        analysis_metadata
    )
    SELECT 
        (SELECT id FROM contracts WHERE document_id = new_doc_id AND user_id = p_user_id),
        p_user_id,
        p_content_hash,
        analysis_rec.agent_version,
        analysis_rec.status,
        analysis_rec.analysis_result,
        analysis_rec.executive_summary,
        analysis_rec.risk_assessment,
        analysis_rec.compliance_check,
        analysis_rec.recommendations,
        analysis_rec.risk_score,
        analysis_rec.overall_risk_score,
        analysis_rec.confidence_score,
        analysis_rec.confidence_level,
        analysis_rec.processing_time,
        analysis_rec.processing_time_seconds,
        analysis_rec.analysis_metadata || jsonb_build_object('cached_from', analysis_rec.id)
    WHERE analysis_rec.id IS NOT NULL
    RETURNING id INTO analysis_rec.id;
    
    -- Log user's contract view
    INSERT INTO user_contract_views (
        user_id, 
        content_hash, 
        property_address, 
        analysis_id, 
        source
    ) VALUES (
        p_user_id, 
        p_content_hash, 
        p_property_address, 
        analysis_rec.id, 
        'cache_hit'
    ) RETURNING id INTO new_view_id;
    
    RETURN QUERY SELECT new_doc_id, analysis_rec.id, new_view_id;
    
EXCEPTION WHEN OTHERS THEN
    -- Log error and re-raise
    RAISE NOTICE 'Cache hit processing error: %', SQLERRM;
    RAISE;
END;
$$;

-- Property intelligence functions
-- Function to find or create property by address
CREATE OR REPLACE FUNCTION find_or_create_property(
    p_address_full TEXT,
    p_unit_number TEXT DEFAULT NULL,
    p_street_number TEXT DEFAULT NULL,
    p_street_name TEXT DEFAULT NULL,
    p_street_type TEXT DEFAULT NULL,
    p_suburb TEXT DEFAULT NULL,
    p_state TEXT DEFAULT NULL,
    p_postcode TEXT DEFAULT NULL,
    p_property_type TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    property_id UUID;
BEGIN
    -- Try to find existing property
    SELECT id INTO property_id 
    FROM properties 
    WHERE address_full = p_address_full 
    AND suburb = p_suburb 
    AND state = p_state 
    AND postcode = p_postcode;
    
    -- If not found, create new property
    IF property_id IS NULL THEN
        INSERT INTO properties (
            address_full, unit_number, street_number, street_name, street_type,
            suburb, state, postcode, property_type
        ) VALUES (
            p_address_full, p_unit_number, p_street_number, p_street_name, p_street_type,
            p_suburb, p_state, p_postcode, COALESCE(p_property_type, 'House')
        )
        RETURNING id INTO property_id;
    END IF;
    
    RETURN property_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean expired property cache data
CREATE OR REPLACE FUNCTION cleanup_expired_property_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    temp_count INTEGER;
BEGIN
    -- Clean expired valuations
    DELETE FROM property_valuations WHERE expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean expired market data
    DELETE FROM property_market_data WHERE expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean expired risk assessments
    DELETE FROM property_risk_assessments WHERE expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean expired reports
    DELETE FROM property_reports WHERE expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean expired market insights
    DELETE FROM market_insights WHERE valid_until < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions on cache functions
GRANT EXECUTE ON FUNCTION cleanup_expired_cache() TO service_role;
GRANT EXECUTE ON FUNCTION normalize_address(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION generate_property_hash(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_cache_popularity(TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION process_contract_cache_hit(UUID, TEXT, TEXT, BIGINT, TEXT, TEXT) TO service_role;

-- Grant permissions on property intelligence functions
GRANT EXECUTE ON FUNCTION find_or_create_property TO authenticated;
GRANT EXECUTE ON FUNCTION find_or_create_property TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_property_data TO service_role;

-- View combining user contract views with analysis data
CREATE OR REPLACE VIEW user_contract_history AS
SELECT 
    ucv.*,
    ca.analysis_result,
    ca.risk_score,
    ca.overall_risk_score,
    ca.confidence_score,
    ca.status as analysis_status,
    ca.analysis_timestamp,
    d.original_filename,
    d.file_type,
    d.file_size
FROM user_contract_views ucv
LEFT JOIN contract_analyses ca ON ucv.analysis_id = ca.id
LEFT JOIN documents d ON ucv.content_hash = d.content_hash AND d.user_id = ucv.user_id;

-- View for user property search history
CREATE OR REPLACE VIEW user_property_history AS
SELECT 
    upv.*,
    hpc.analysis_result,
    hpc.popularity_score,
    hpc.access_count
FROM user_property_views upv
LEFT JOIN hot_properties_cache hpc ON upv.property_hash = hpc.property_hash;

-- Grant permissions on views
GRANT SELECT ON user_contract_history TO authenticated;
GRANT SELECT ON user_property_history TO authenticated;

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Comments for improved cache architecture
COMMENT ON TABLE hot_properties_cache IS 'Shared cache for property analysis results with TTL expiration';
COMMENT ON TABLE hot_contracts_cache IS 'Shared cache for contract analysis results with TTL expiration';
COMMENT ON TABLE user_property_views IS 'User''s property search history with RLS for privacy';
COMMENT ON TABLE user_contract_views IS 'User''s contract analysis history with RLS for privacy';

COMMENT ON COLUMN hot_properties_cache.property_hash IS 'SHA-256 hash of normalized property address';
COMMENT ON COLUMN hot_properties_cache.popularity_score IS 'Popularity score based on access frequency';
COMMENT ON COLUMN hot_properties_cache.expires_at IS 'Cache expiration timestamp (typically 1-3 days)';

COMMENT ON COLUMN hot_contracts_cache.content_hash IS 'SHA-256 hash of document content - primary cache key';
COMMENT ON COLUMN hot_contracts_cache.access_count IS 'Number of times this cached analysis was accessed';
COMMENT ON COLUMN hot_contracts_cache.expires_at IS 'Cache expiration timestamp (typically 1-3 days)';

-- Cache architecture improvements:
-- 1. Simplified to use only content_hash (removed document_hash redundancy)
-- 2. Primary indexes on content_hash for fast cache lookups
-- 3. Secondary indexes on document_id for user-specific operations
-- 4. Composite indexes for efficient cache + user queries
COMMENT ON FUNCTION cleanup_expired_cache IS 'Removes expired cache entries and returns deletion counts';
COMMENT ON FUNCTION normalize_address IS 'Normalizes address strings for consistent hashing';
COMMENT ON FUNCTION generate_property_hash IS 'Generates consistent hash for property addresses';
COMMENT ON FUNCTION process_contract_cache_hit IS 'Creates user records from cached analysis (simplified content_hash only)';

-- Property intelligence function comments
COMMENT ON FUNCTION find_or_create_property IS 'Finds existing property or creates new one by address';
COMMENT ON FUNCTION cleanup_expired_property_data IS 'Removes expired property cache data and returns deletion counts';

-- Property table triggers
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();