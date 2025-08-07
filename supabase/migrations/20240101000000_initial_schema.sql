-- Initial schema migration for Real2.AI
-- Creates all core tables, relationships, and enhanced features
-- Includes: onboarding tracking, analysis progress with real-time updates, and comprehensive functions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- For digest function used in hashing

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

-- Contracts table for contract metadata (shared resource, no user_id)
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL, -- Primary key for shared caching
    contract_type contract_type NOT NULL DEFAULT 'purchase_agreement',
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    contract_terms JSONB DEFAULT '{}',
    raw_text TEXT,
    property_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contract analyses table for AI analysis results (shared resource, no user_id)
CREATE TABLE contract_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL, -- Primary key for shared caching
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

-- Document pages table for page-level analysis (shared resource)
CREATE TABLE document_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL, -- Hash-based caching, no document_id
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

-- Document entities table for extracted entities (shared resource)
CREATE TABLE document_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL, -- Hash-based caching, no document_id
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
    
    -- Cache key (primary identifier for shared resource)
    property_hash TEXT UNIQUE NOT NULL, -- Hash of normalized address for caching
    
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
    analysis_result JSONB DEFAULT '{}', -- Cached analysis result
    processing_time FLOAT,
    
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
-- Note: Uses content_hash to link to shared resources
CREATE TABLE analysis_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL, -- Links to shared analysis content
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Progress tracking fields
    current_step VARCHAR(100) NOT NULL,
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    step_description TEXT,
    estimated_completion_minutes INTEGER CHECK (estimated_completion_minutes >= 0),
    
    -- Timing information
    step_started_at TIMESTAMP WITH TIME ZONE,
    step_completed_at TIMESTAMP WITH TIME ZONE,
    total_elapsed_seconds INTEGER DEFAULT 0 CHECK (total_elapsed_seconds >= 0),
    
    -- Status and error handling
    status VARCHAR(50) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps (managed by triggers)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints  
    CONSTRAINT unique_analysis_progress UNIQUE (content_hash, user_id),
    CONSTRAINT valid_progress_percent CHECK (progress_percent BETWEEN 0 AND 100)
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

CREATE INDEX idx_contracts_content_hash ON contracts(content_hash);
CREATE INDEX idx_contracts_type_state ON contracts(contract_type, australian_state);

CREATE INDEX idx_contract_analyses_content_hash ON contract_analyses(content_hash);
-- Contract analyses indexes (user_id removed, now shared resource)
CREATE INDEX idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX idx_contract_analyses_timestamp ON contract_analyses(analysis_timestamp DESC);
CREATE INDEX idx_contract_analyses_risk_score ON contract_analyses(overall_risk_score);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_action_type ON usage_logs(action_type);

-- Property data indexes
CREATE INDEX idx_property_data_location ON property_data(suburb, state, postcode);
CREATE INDEX idx_property_data_property_type ON property_data(property_type);
CREATE INDEX idx_property_data_property_hash ON property_data(property_hash);

CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);

CREATE INDEX idx_analysis_progress_content_hash ON analysis_progress(content_hash);
CREATE INDEX idx_analysis_progress_user ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_user_id ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_status ON analysis_progress(status);
CREATE INDEX idx_analysis_progress_created_at ON analysis_progress(created_at);

-- Indexes for new document processing tables
CREATE INDEX idx_document_pages_content_hash ON document_pages(content_hash);
CREATE INDEX idx_document_pages_page_number ON document_pages(page_number);
CREATE INDEX idx_document_pages_content_type ON document_pages(primary_content_type);

CREATE INDEX idx_document_entities_content_hash ON document_entities(content_hash);
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
CREATE INDEX idx_analysis_progress_active ON analysis_progress(content_hash, user_id, updated_at) 
WHERE status = 'in_progress';

-- Create composite indexes for common queries
CREATE INDEX idx_documents_user_status ON documents(user_id, processing_status);
-- Contracts indexes (user_id removed, now shared resource)
-- Contract analyses composite indexes (user_id removed)
CREATE INDEX idx_usage_logs_user_timestamp ON usage_logs(user_id, timestamp DESC);

-- Replace view with SECURITY DEFINER function due to schema changes
-- analysis_progress table may also need refactoring for shared resource model
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

-- Grant permissions on the function
GRANT EXECUTE ON FUNCTION get_analysis_progress_detailed TO authenticated;

-- Grant permissions on new document processing tables
GRANT ALL ON document_pages TO authenticated;
GRANT ALL ON document_entities TO authenticated;
GRANT ALL ON document_diagrams TO authenticated;
GRANT ALL ON document_analyses TO authenticated;

-- Comments for documentation
COMMENT ON TABLE analysis_progress IS 'Real-time progress tracking for document analysis and contract processing';
COMMENT ON COLUMN analysis_progress.contract_id IS 'Reference to the contract being analyzed';
COMMENT ON COLUMN analysis_progress.analysis_id IS 'Reference to the specific analysis instance';
COMMENT ON COLUMN analysis_progress.current_step IS 'Current processing step (e.g., text_extraction, contract_analysis)';
COMMENT ON COLUMN analysis_progress.progress_percent IS 'Progress percentage from 0 to 100';
COMMENT ON COLUMN analysis_progress.step_description IS 'Human-readable description of current step';
COMMENT ON COLUMN analysis_progress.estimated_completion_minutes IS 'Estimated minutes until completion';
COMMENT ON COLUMN analysis_progress.total_elapsed_seconds IS 'Total time elapsed since analysis started';
COMMENT ON COLUMN analysis_progress.status IS 'Overall status: in_progress, completed, failed, or cancelled';
COMMENT ON COLUMN analysis_progress.error_message IS 'Error message if analysis fails';
COMMENT ON COLUMN analysis_progress.metadata IS 'Additional metadata for progress tracking';

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

-- Function to process contract cache hits (creates user records from cached analysis)
CREATE OR REPLACE FUNCTION process_contract_cache_hit(
    p_user_id UUID,
    p_content_hash TEXT,
    p_filename TEXT,
    p_file_size BIGINT,
    p_mime_type TEXT,
    p_property_address TEXT DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    analysis_id UUID,
    view_id UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_document_id UUID;
    v_analysis_id UUID;
    v_view_id UUID;
BEGIN
    -- Create document record for user (documents are still user-owned)
    INSERT INTO documents (
        user_id,
        original_filename,
        storage_path,
        file_type,
        file_size,
        content_hash,
        processing_status
    ) VALUES (
        p_user_id,
        p_filename,
        'cache_hit/' || p_content_hash, -- Virtual path for cached items
        p_mime_type,
        p_file_size,
        p_content_hash,
        'completed'
    )
    RETURNING id INTO v_document_id;
    
    -- Get existing analysis ID from shared table
    SELECT id INTO v_analysis_id
    FROM contract_analyses
    WHERE content_hash = p_content_hash
    AND status = 'completed'
    LIMIT 1;
    
    -- Note: contracts table is now shared, so we don't create new records
    -- The shared contract record should already exist with the content_hash
    
    -- Log the view for user history (user-specific table)
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
        v_analysis_id,
        'cache_hit'
    )
    RETURNING id INTO v_view_id;
    
    RETURN QUERY SELECT v_document_id, v_analysis_id, v_view_id;
END;
$$;

-- Grant permissions on property intelligence functions
GRANT EXECUTE ON FUNCTION find_or_create_property TO authenticated;
GRANT EXECUTE ON FUNCTION find_or_create_property TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_property_data TO service_role;
GRANT EXECUTE ON FUNCTION process_contract_cache_hit TO service_role;

-- User tracking tables for cache history
-- User property search history (Private with RLS)
CREATE TABLE user_property_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_hash TEXT NOT NULL,
    property_address TEXT NOT NULL,
    source TEXT DEFAULT 'search',
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for user property views
ALTER TABLE user_property_views ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own property views
CREATE POLICY "Users can view own property views" ON user_property_views
    FOR ALL USING (auth.uid() = user_id);

-- User contract analysis history (Private with RLS)
CREATE TABLE user_contract_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    property_address TEXT,
    analysis_id UUID, -- References contract_analyses
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT CHECK (source IN ('upload', 'cache_hit')) DEFAULT 'upload',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for user contract views
ALTER TABLE user_contract_views ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own contract views
CREATE POLICY "Users can view own contract views" ON user_contract_views
    FOR ALL USING (auth.uid() = user_id);

-- Create indexes for user view tables
CREATE INDEX idx_user_property_views_user_id ON user_property_views(user_id);
CREATE INDEX idx_user_property_views_property_hash ON user_property_views(property_hash);
CREATE INDEX idx_user_contract_views_user_id ON user_contract_views(user_id);
CREATE INDEX idx_user_contract_views_content_hash ON user_contract_views(content_hash);

-- Function to get user contract history (bypasses RLS issues with views)
CREATE OR REPLACE FUNCTION get_user_contract_history(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    content_hash TEXT,
    property_address TEXT,
    analysis_id UUID,
    viewed_at TIMESTAMP WITH TIME ZONE,
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    analysis_result JSONB,
    risk_score DECIMAL,
    overall_risk_score INTEGER,
    confidence_score FLOAT,
    analysis_status TEXT,
    analysis_timestamp TIMESTAMP WITH TIME ZONE,
    original_filename TEXT,
    file_type TEXT,
    file_size BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ucv.id,
        ucv.user_id,
        ucv.content_hash,
        ucv.property_address,
        ucv.analysis_id,
        ucv.viewed_at,
        ucv.source,
        ucv.created_at,
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
    LEFT JOIN documents d ON ucv.content_hash = d.content_hash AND d.user_id = ucv.user_id
    WHERE ucv.user_id = p_user_id
    ORDER BY ucv.viewed_at DESC;
END;
$$;

-- Function to get user property history (bypasses RLS issues with views)
CREATE OR REPLACE FUNCTION get_user_property_history(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    property_hash TEXT,
    property_address TEXT,
    source TEXT,
    viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    analysis_result JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        upv.id,
        upv.user_id,
        upv.property_hash,
        upv.property_address,
        upv.source,
        upv.viewed_at,
        upv.created_at,
        pd.analysis_result
    FROM user_property_views upv
    LEFT JOIN property_data pd ON upv.property_hash = pd.property_hash
    WHERE upv.user_id = p_user_id
    ORDER BY upv.viewed_at DESC;
END;
$$;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION get_user_contract_history TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_property_history TO authenticated;

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Utility functions for address normalization and hashing
CREATE OR REPLACE FUNCTION normalize_address(address TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Remove extra whitespace, convert to lowercase, remove punctuation
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                TRIM(address),
                '[^a-zA-Z0-9\s]', '', 'g'  -- Remove punctuation
            ),
            '\s+', ' ', 'g'  -- Normalize whitespace
        )
    );
END;
$$;

CREATE OR REPLACE FUNCTION generate_property_hash(address TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Generate SHA-256 hash of normalized address
    RETURN encode(
        digest(normalize_address(address), 'sha256'),
        'hex'
    );
END;
$$;

-- Disable RLS on shared resource tables for cross-user cache sharing
ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;
ALTER TABLE contract_analyses DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE property_data DISABLE ROW LEVEL SECURITY;

-- Comments for user view tables (still private with RLS)
COMMENT ON TABLE user_property_views IS 'User''s property search history with RLS for privacy';
COMMENT ON TABLE user_contract_views IS 'User''s contract analysis history with RLS for privacy';

-- Comments for shared resource tables (RLS disabled)
COMMENT ON TABLE contracts IS 'Contract metadata - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE contract_analyses IS 'Contract analysis results - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE document_pages IS 'Document pages - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE document_entities IS 'Document entities - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE property_data IS 'Property analysis data - shared resource, RLS disabled, accessed by property_hash';

-- Cache architecture improvements:
-- 1. Simplified to use only content_hash (removed document_hash redundancy)
-- 2. Primary indexes on content_hash for fast cache lookups
-- 3. Secondary indexes on document_id for user-specific operations
-- 4. Composite indexes for efficient cache + user queries
COMMENT ON FUNCTION normalize_address IS 'Normalizes address strings for consistent hashing';
COMMENT ON FUNCTION generate_property_hash IS 'Generates consistent hash for property addresses';

-- Property intelligence function comments
COMMENT ON FUNCTION find_or_create_property IS 'Finds existing property or creates new one by address';
COMMENT ON FUNCTION cleanup_expired_property_data IS 'Removes expired property cache data and returns deletion counts';

-- Property table triggers
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analysis progress triggers
CREATE TRIGGER update_analysis_progress_updated_at_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically update total_elapsed_seconds
CREATE OR REPLACE FUNCTION calculate_analysis_progress_elapsed_time()
RETURNS TRIGGER AS $$
BEGIN
    -- If step is being completed, calculate elapsed time
    IF NEW.step_completed_at IS NOT NULL AND OLD.step_completed_at IS NULL THEN
        NEW.total_elapsed_seconds = COALESCE(OLD.total_elapsed_seconds, 0) + 
            EXTRACT(EPOCH FROM (NEW.step_completed_at - COALESCE(NEW.step_started_at, NEW.created_at)))::INTEGER;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_analysis_progress_elapsed_time_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW
    EXECUTE FUNCTION calculate_analysis_progress_elapsed_time();