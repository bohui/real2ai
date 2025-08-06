-- Property Intelligence Database Schema for Real2.AI
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

-- Create indexes for performance
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

-- Row Level Security Policies

-- Properties table - public read, authenticated write
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Properties are publicly readable" ON properties FOR SELECT USING (true);
CREATE POLICY "Authenticated users can insert properties" ON properties FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY "Service role can manage properties" ON properties FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Property valuations - users can read their requested valuations
ALTER TABLE property_valuations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view property valuations" ON property_valuations FOR SELECT USING (true);
CREATE POLICY "Service role can manage valuations" ON property_valuations FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Market data - publicly readable
ALTER TABLE property_market_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Market data is publicly readable" ON property_market_data FOR SELECT USING (true);
CREATE POLICY "Service role can manage market data" ON property_market_data FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Risk assessments - publicly readable
ALTER TABLE property_risk_assessments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Risk assessments are publicly readable" ON property_risk_assessments FOR SELECT USING (true);
CREATE POLICY "Service role can manage risk assessments" ON property_risk_assessments FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Comparable sales - publicly readable
ALTER TABLE comparable_sales ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Comparable sales are publicly readable" ON comparable_sales FOR SELECT USING (true);
CREATE POLICY "Service role can manage comparable sales" ON comparable_sales FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Sales history - publicly readable
ALTER TABLE property_sales_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Sales history is publicly readable" ON property_sales_history FOR SELECT USING (true);
CREATE POLICY "Service role can manage sales history" ON property_sales_history FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Rental history - publicly readable
ALTER TABLE property_rental_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Rental history is publicly readable" ON property_rental_history FOR SELECT USING (true);
CREATE POLICY "Service role can manage rental history" ON property_rental_history FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- User saved properties - users can only see their own
ALTER TABLE user_saved_properties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own saved properties" ON user_saved_properties FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own saved properties" ON user_saved_properties FOR ALL USING (auth.uid() = user_id);

-- Property searches - users can only see their own
ALTER TABLE property_searches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own search history" ON property_searches FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own searches" ON property_searches FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Property reports - users can view their own reports and public reports
ALTER TABLE property_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own reports" ON property_reports FOR SELECT USING (auth.uid() = user_id OR is_public = true);
CREATE POLICY "Users can create reports" ON property_reports FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role can manage reports" ON property_reports FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- API usage - users can only see their own usage
ALTER TABLE property_api_usage ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own API usage" ON property_api_usage FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage API usage" ON property_api_usage FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Market insights - publicly readable
ALTER TABLE market_insights ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Market insights are publicly readable" ON market_insights FOR SELECT USING (true);
CREATE POLICY "Service role can manage market insights" ON market_insights FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Functions for data management

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

-- Function to clean expired cache data
CREATE OR REPLACE FUNCTION cleanup_expired_property_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Clean expired valuations
    DELETE FROM property_valuations WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Clean expired market data
    DELETE FROM property_market_data WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Clean expired risk assessments
    DELETE FROM property_risk_assessments WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Clean expired reports
    DELETE FROM property_reports WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Clean expired market insights
    DELETE FROM market_insights WHERE valid_until < NOW();
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add updated_at triggers
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT EXECUTE ON FUNCTION find_or_create_property TO authenticated;
GRANT EXECUTE ON FUNCTION find_or_create_property TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_property_data TO service_role;