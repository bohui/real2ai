-- Property Management System Tables
-- Contains all property-related tables for Real2.AI property analysis

-- Main properties table for Australian property data
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_hash TEXT UNIQUE,
    address_full TEXT NOT NULL CHECK (length(address_full) <= 500),
    street_number TEXT CHECK (length(street_number) <= 20),
    street_name TEXT CHECK (length(street_name) <= 200),
    suburb TEXT CHECK (length(suburb) <= 100),
    state TEXT CHECK (length(state) <= 10),
    postcode TEXT CHECK (length(postcode) <= 10),
    property_type TEXT CHECK (length(property_type) <= 50),
    
    -- Location data
    latitude DECIMAL(10,8) CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(11,8) CHECK (longitude >= -180 AND longitude <= 180),
    
    -- Property features
    bedrooms INTEGER CHECK (bedrooms >= 0),
    bathrooms INTEGER CHECK (bathrooms >= 0),
    car_spaces INTEGER CHECK (car_spaces >= 0),
    land_size DECIMAL(10,2) CHECK (land_size >= 0),
    building_size DECIMAL(10,2) CHECK (building_size >= 0),
    year_built INTEGER CHECK (year_built >= 1800 AND year_built <= 2030),
    
    -- Property identifiers
    lot_number TEXT CHECK (length(lot_number) <= 20),
    plan_number TEXT CHECK (length(plan_number) <= 50),
    title_reference TEXT CHECK (length(title_reference) <= 100),
    council_property_id TEXT CHECK (length(council_property_id) <= 100),
    
    -- Data quality and verification
    address_verified BOOLEAN DEFAULT FALSE,
    coordinates_verified BOOLEAN DEFAULT FALSE,
    property_features_verified BOOLEAN DEFAULT FALSE,
    data_source TEXT CHECK (length(data_source) <= 100),
    last_updated_source TEXT CHECK (length(last_updated_source) <= 100),
    
    -- Metadata
    property_metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Property valuations from various sources
CREATE TABLE property_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    valuation_source TEXT NOT NULL CHECK (length(valuation_source) <= 50),
    valuation_type TEXT NOT NULL CHECK (length(valuation_type) <= 50),
    estimated_value DECIMAL(12,2) NOT NULL CHECK (estimated_value >= 0),
    valuation_range_lower DECIMAL(12,2) CHECK (valuation_range_lower >= 0),
    valuation_range_upper DECIMAL(12,2) CHECK (valuation_range_upper >= 0),
    confidence DECIMAL(3,2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    methodology TEXT,
    valuation_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    api_response JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data and analytics for properties
CREATE TABLE property_market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    suburb TEXT NOT NULL CHECK (length(suburb) <= 100),
    state TEXT NOT NULL CHECK (length(state) <= 10),
    data_source TEXT NOT NULL CHECK (length(data_source) <= 50),
    median_price DECIMAL(12,2) CHECK (median_price >= 0),
    price_growth_12_month DECIMAL(5,2),
    price_growth_3_year DECIMAL(5,2),
    days_on_market INTEGER CHECK (days_on_market >= 0),
    sales_volume_12_month INTEGER CHECK (sales_volume_12_month >= 0),
    market_outlook TEXT CHECK (length(market_outlook) <= 50),
    median_rent DECIMAL(8,2) CHECK (median_rent >= 0),
    rental_yield DECIMAL(5,2) CHECK (rental_yield >= 0),
    vacancy_rate DECIMAL(5,2) CHECK (vacancy_rate >= 0),
    data_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk assessment data for properties
CREATE TABLE property_risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    overall_risk TEXT NOT NULL CHECK (overall_risk IN ('low', 'medium', 'high', 'very_high')),
    liquidity_risk TEXT NOT NULL CHECK (liquidity_risk IN ('low', 'medium', 'high', 'very_high')),
    market_risk TEXT NOT NULL CHECK (market_risk IN ('low', 'medium', 'high', 'very_high')),
    structural_risk TEXT NOT NULL CHECK (structural_risk IN ('low', 'medium', 'high', 'very_high')),
    risk_factors JSONB DEFAULT '[]'::jsonb,
    risk_score DECIMAL(5,2) CHECK (risk_score >= 0.0 AND risk_score <= 100.0),
    confidence DECIMAL(3,2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    assessment_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    assessment_methodology TEXT,
    mitigation_strategies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comparable sales data for property analysis
CREATE TABLE comparable_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    comparable_address TEXT NOT NULL CHECK (length(comparable_address) <= 500),
    sale_price DECIMAL(12,2) NOT NULL CHECK (sale_price >= 0),
    sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
    days_on_market INTEGER CHECK (days_on_market >= 0),
    
    -- Property comparison features
    bedrooms INTEGER CHECK (bedrooms >= 0),
    bathrooms INTEGER CHECK (bathrooms >= 0),
    car_spaces INTEGER CHECK (car_spaces >= 0),
    land_size DECIMAL(10,2) CHECK (land_size >= 0),
    building_size DECIMAL(10,2) CHECK (building_size >= 0),
    
    -- Similarity metrics
    distance_km DECIMAL(8,2) CHECK (distance_km >= 0),
    similarity_score DECIMAL(3,2) CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0),
    price_per_sqm DECIMAL(10,2) CHECK (price_per_sqm >= 0),
    
    -- Data source and verification
    data_source TEXT NOT NULL CHECK (length(data_source) <= 50),
    verified BOOLEAN DEFAULT FALSE,
    sale_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Historical sales data for properties
CREATE TABLE property_sales_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    sale_price DECIMAL(12,2) NOT NULL CHECK (sale_price >= 0),
    sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sale_type TEXT CHECK (length(sale_type) <= 50),
    days_on_market INTEGER CHECK (days_on_market >= 0),
    
    -- Market conditions at time of sale
    median_suburb_price DECIMAL(12,2) CHECK (median_suburb_price >= 0),
    price_vs_median DECIMAL(5,2),
    
    -- Data source
    data_source TEXT NOT NULL CHECK (length(data_source) <= 50),
    verified BOOLEAN DEFAULT FALSE,
    sale_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Rental history data for properties
CREATE TABLE property_rental_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    weekly_rent DECIMAL(8,2) NOT NULL CHECK (weekly_rent >= 0),
    lease_date TIMESTAMP WITH TIME ZONE NOT NULL,
    lease_duration_months INTEGER CHECK (lease_duration_months >= 1),
    
    -- Rental analysis
    rental_yield DECIMAL(5,2) CHECK (rental_yield >= 0),
    rent_vs_median DECIMAL(5,2),
    
    -- Data source
    data_source TEXT NOT NULL CHECK (length(data_source) <= 50),
    verified BOOLEAN DEFAULT FALSE,
    rental_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User saved properties
CREATE TABLE user_saved_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    is_favorite BOOLEAN DEFAULT FALSE,
    notes TEXT,
    saved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    alert_enabled BOOLEAN DEFAULT FALSE,
    alert_criteria JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, property_id)
);

-- User property search history
CREATE TABLE property_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    search_criteria JSONB DEFAULT '{}'::jsonb,
    results_count INTEGER DEFAULT 0 CHECK (results_count >= 0),
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    search_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Generated property reports
CREATE TABLE property_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL CHECK (length(report_type) <= 100),
    report_data JSONB DEFAULT '{}'::jsonb,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    report_version TEXT DEFAULT '1.0' CHECK (length(report_version) <= 50),
    generation_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track API usage for billing
CREATE TABLE property_api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    api_provider TEXT NOT NULL CHECK (length(api_provider) <= 100),
    endpoint TEXT NOT NULL CHECK (length(endpoint) <= 200),
    request_type TEXT NOT NULL CHECK (length(request_type) <= 100),
    cost_aud DECIMAL(8,2) CHECK (cost_aud >= 0),
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    request_successful BOOLEAN NOT NULL,
    error_message TEXT,
    request_metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market insights and trends cache
CREATE TABLE market_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suburb TEXT NOT NULL CHECK (length(suburb) <= 100),
    state TEXT NOT NULL CHECK (length(state) <= 10),
    property_type TEXT CHECK (length(property_type) <= 50),
    insight_type TEXT NOT NULL CHECK (length(insight_type) <= 50),
    insight_data JSONB DEFAULT '{}'::jsonb,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    data_sources TEXT[] DEFAULT '{}',
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_properties_hash ON properties(property_hash);
CREATE INDEX idx_properties_location ON properties(suburb, state, postcode);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_coordinates ON properties(latitude, longitude);

CREATE INDEX idx_property_valuations_property_id ON property_valuations(property_id);
CREATE INDEX idx_property_valuations_date ON property_valuations(valuation_date);
CREATE INDEX idx_property_valuations_source ON property_valuations(valuation_source);

CREATE INDEX idx_property_market_data_property_id ON property_market_data(property_id);
CREATE INDEX idx_property_market_data_location ON property_market_data(suburb, state);
CREATE INDEX idx_property_market_data_date ON property_market_data(data_date);

CREATE INDEX idx_property_risk_assessments_property_id ON property_risk_assessments(property_id);
CREATE INDEX idx_property_risk_assessments_date ON property_risk_assessments(assessment_date);

CREATE INDEX idx_comparable_sales_property_id ON comparable_sales(property_id);
CREATE INDEX idx_comparable_sales_date ON comparable_sales(sale_date);

CREATE INDEX idx_property_sales_history_property_id ON property_sales_history(property_id);
CREATE INDEX idx_property_sales_history_date ON property_sales_history(sale_date);

CREATE INDEX idx_property_rental_history_property_id ON property_rental_history(property_id);
CREATE INDEX idx_property_rental_history_date ON property_rental_history(lease_date);

CREATE INDEX idx_user_saved_properties_user_id ON user_saved_properties(user_id);
CREATE INDEX idx_user_saved_properties_property_id ON user_saved_properties(property_id);

CREATE INDEX idx_property_searches_user_id ON property_searches(user_id);
CREATE INDEX idx_property_searches_date ON property_searches(executed_at);

CREATE INDEX idx_property_reports_property_id ON property_reports(property_id);
CREATE INDEX idx_property_reports_user_id ON property_reports(user_id);

CREATE INDEX idx_property_api_usage_user_id ON property_api_usage(user_id);
CREATE INDEX idx_property_api_usage_timestamp ON property_api_usage(timestamp);

CREATE INDEX idx_market_insights_location ON market_insights(suburb, state);
CREATE INDEX idx_market_insights_type ON market_insights(insight_type);
CREATE INDEX idx_market_insights_validity ON market_insights(valid_from, valid_until);

-- Create triggers for updated_at timestamps
CREATE TRIGGER update_properties_updated_at 
    BEFORE UPDATE ON properties 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_valuations_updated_at 
    BEFORE UPDATE ON property_valuations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_market_data_updated_at 
    BEFORE UPDATE ON property_market_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_risk_assessments_updated_at 
    BEFORE UPDATE ON property_risk_assessments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comparable_sales_updated_at 
    BEFORE UPDATE ON comparable_sales 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_sales_history_updated_at 
    BEFORE UPDATE ON property_sales_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_rental_history_updated_at 
    BEFORE UPDATE ON property_rental_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_saved_properties_updated_at 
    BEFORE UPDATE ON user_saved_properties 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_searches_updated_at 
    BEFORE UPDATE ON property_searches 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_reports_updated_at 
    BEFORE UPDATE ON property_reports 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_api_usage_updated_at 
    BEFORE UPDATE ON property_api_usage 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_market_insights_updated_at 
    BEFORE UPDATE ON market_insights 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security for user-specific tables
ALTER TABLE user_saved_properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_api_usage ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user-specific tables
CREATE POLICY "Users can view own saved properties" 
    ON user_saved_properties FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own saved properties" 
    ON user_saved_properties FOR ALL 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own property searches" 
    ON property_searches FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own property searches" 
    ON property_searches FOR ALL 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own property reports" 
    ON property_reports FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own property reports" 
    ON property_reports FOR ALL 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own API usage" 
    ON property_api_usage FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service can insert API usage" 
    ON property_api_usage FOR INSERT 
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role' OR auth.uid() = user_id);

-- Shared tables (properties, market data, etc.) have no RLS - they're accessible by all authenticated users
-- but actual access is controlled through the application layer

-- Comments for documentation
COMMENT ON TABLE properties IS 'Main properties table with detailed property information and features';
COMMENT ON TABLE property_valuations IS 'Property valuations from various sources with confidence scores';
COMMENT ON TABLE property_market_data IS 'Market analytics and trends data for properties by location';
COMMENT ON TABLE property_risk_assessments IS 'Risk assessment data including overall and category-specific risks';
COMMENT ON TABLE comparable_sales IS 'Comparable sales data for property valuation analysis';
COMMENT ON TABLE property_sales_history IS 'Historical sales records for properties';
COMMENT ON TABLE property_rental_history IS 'Rental history and yield data for properties';
COMMENT ON TABLE user_saved_properties IS 'User-specific saved and favorited properties with RLS';
COMMENT ON TABLE property_searches IS 'User property search history with RLS for privacy';
COMMENT ON TABLE property_reports IS 'Generated property analysis reports with RLS';
COMMENT ON TABLE property_api_usage IS 'API usage tracking for billing and rate limiting with RLS';
COMMENT ON TABLE market_insights IS 'Cached market insights and trends by location';