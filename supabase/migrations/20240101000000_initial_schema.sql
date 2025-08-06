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
CREATE INDEX idx_documents_created_at ON documents(upload_timestamp DESC);

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

-- Triggers and Functions for analysis progress
-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_analysis_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER analysis_progress_updated_at_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW EXECUTE FUNCTION update_analysis_progress_updated_at();

-- Create update triggers for new document processing tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_document_pages_updated_at BEFORE UPDATE ON document_pages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_document_entities_updated_at BEFORE UPDATE ON document_entities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_document_diagrams_updated_at BEFORE UPDATE ON document_diagrams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_document_analyses_updated_at BEFORE UPDATE ON document_analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

-- Views for enhanced data access
-- View for analysis progress with contract and analysis details
CREATE OR REPLACE VIEW analysis_progress_detailed AS
SELECT 
    ap.*,
    c.contract_type,
    ca.agent_version,
    ca.status as analysis_status,
    d.filename as document_filename,
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