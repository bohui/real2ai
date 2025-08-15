-- Seed data for Real2.AI
-- Creates initial subscription plans and reference data

-- Insert subscription plans
INSERT INTO subscription_plans (
    name, 
    slug, 
    description, 
    price_monthly, 
    price_annually, 
    credits_per_month, 
    max_file_size_mb,
    features, 
    limits,
    sort_order
) VALUES
(
    'Free',
    'free',
    'Perfect for trying out Real2.AI with basic contract analysis',
    0.00,
    0.00,
    1,
    10,
    '["1 contract analysis per month", "Basic risk assessment", "Email support", "PDF export"]'::jsonb,
    '{"max_analyses_per_month": 1, "max_file_size_mb": 10, "support_level": "email"}'::jsonb,
    1
),
(
    'Basic',
    'basic',
    'Ideal for individuals and small property investors',
    29.99,
    299.99,
    10,
    25,
    '["10 contract analyses per month", "Advanced risk assessment", "Compliance checking", "Priority email support", "PDF & Word reports", "Analysis history"]'::jsonb,
    '{"max_analyses_per_month": 10, "max_file_size_mb": 25, "support_level": "priority_email", "history_retention_days": 365}'::jsonb,
    2
),
(
    'Premium',
    'premium',
    'Perfect for real estate professionals and active investors',
    79.99,
    799.99,
    50,
    50,
    '["50 contract analyses per month", "Premium risk assessment", "Advanced compliance checking", "Property market insights", "Phone & email support", "Custom reporting", "API access", "Team collaboration"]'::jsonb,
    '{"max_analyses_per_month": 50, "max_file_size_mb": 50, "support_level": "phone_email", "history_retention_days": 1095, "api_calls_per_month": 1000, "team_members": 3}'::jsonb,
    3
),
(
    'Enterprise',
    'enterprise',
    'For large agencies and institutional investors',
    199.99,
    1999.99,
    200,
    100,
    '["200 contract analyses per month", "Enterprise risk assessment", "Custom compliance rules", "Advanced property analytics", "Dedicated account manager", "Custom integrations", "White-label reporting", "Unlimited team members", "SLA guarantee"]'::jsonb,
    '{"max_analyses_per_month": 200, "max_file_size_mb": 100, "support_level": "dedicated", "history_retention_days": -1, "api_calls_per_month": 10000, "team_members": -1, "sla_uptime": 99.9}'::jsonb,
    4
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    price_monthly = EXCLUDED.price_monthly,
    price_annually = EXCLUDED.price_annually,
    credits_per_month = EXCLUDED.credits_per_month,
    max_file_size_mb = EXCLUDED.max_file_size_mb,
    features = EXCLUDED.features,
    limits = EXCLUDED.limits;

-- Demo user creation removed - profiles are automatically created via trigger
-- when users sign up through the auth system

-- Insert Australian state reference data for validation
CREATE TABLE IF NOT EXISTS australian_states_ref (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capital TEXT NOT NULL,
    population INTEGER,
    area_sq_km INTEGER,
    time_zones TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO australian_states_ref (code, name, capital, population, area_sq_km, time_zones) VALUES
('NSW', 'New South Wales', 'Sydney', 8166369, 800642, ARRAY['AEST', 'AEDT']),
('VIC', 'Victoria', 'Melbourne', 6681200, 227444, ARRAY['AEST', 'AEDT']),
('QLD', 'Queensland', 'Brisbane', 5206400, 1851736, ARRAY['AEST', 'AEDT']),
('WA', 'Western Australia', 'Perth', 2667912, 2529875, ARRAY['AWST']),
('SA', 'South Australia', 'Adelaide', 1771703, 1044353, ARRAY['ACST', 'ACDT']),
('TAS', 'Tasmania', 'Hobart', 541965, 90758, ARRAY['AEST', 'AEDT']),
('ACT', 'Australian Capital Territory', 'Canberra', 454499, 2358, ARRAY['AEST', 'AEDT']),
('NT', 'Northern Territory', 'Darwin', 249129, 1419630, ARRAY['ACST'])
ON CONFLICT (code) DO UPDATE SET
    population = EXCLUDED.population;

-- Insert contract type reference data
CREATE TABLE IF NOT EXISTS contract_types_ref (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    typical_complexity TEXT CHECK (typical_complexity IN ('low', 'medium', 'high')),
    average_pages INTEGER,
    common_clauses JSONB DEFAULT '[]',
    risk_factors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO contract_types_ref (code, name, description, typical_complexity, average_pages, common_clauses, risk_factors) VALUES
(
    'purchase_agreement',
    'Purchase Agreement',
    'Standard contract for buying property in Australia',
    'medium',
    15,
    '["purchase_price", "settlement_date", "special_conditions", "cooling_off_period", "building_inspection", "pest_inspection"]'::jsonb,
    '["finance_clause", "building_defects", "title_issues", "zoning_restrictions"]'::jsonb
),
(
    'lease_agreement',
    'Lease Agreement',
    'Rental agreement between landlord and tenant',
    'low',
    8,
    '["rent_amount", "lease_term", "bond", "maintenance_responsibilities", "pet_policy"]'::jsonb,
    '["rent_increases", "maintenance_disputes", "early_termination", "bond_recovery"]'::jsonb
),
(
    'off_plan',
    'Off-the-Plan Purchase',
    'Purchase of property before construction is complete',
    'high',
    25,
    '["sunset_clause", "progress_payments", "completion_date", "variation_clause", "defects_liability"]'::jsonb,
    '["construction_delays", "developer_insolvency", "market_fluctuations", "specification_changes"]'::jsonb
),
(
    'auction',
    'Auction Contract',
    'Contract used for property sales at auction',
    'medium',
    12,
    '["reserve_price", "deposit", "settlement_period", "chattels_included", "special_conditions"]'::jsonb,
    '["unconditional_purchase", "rapid_settlement", "limited_due_diligence", "gazumping_risk"]'::jsonb
)
ON CONFLICT (code) DO UPDATE SET
    description = EXCLUDED.description,
    typical_complexity = EXCLUDED.typical_complexity,
    average_pages = EXCLUDED.average_pages,
    common_clauses = EXCLUDED.common_clauses,
    risk_factors = EXCLUDED.risk_factors;

-- Insert sample property types for reference
CREATE TABLE IF NOT EXISTS property_types_ref (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('residential', 'commercial', 'industrial', 'rural')),
    description TEXT,
    typical_features JSONB DEFAULT '[]',
    investment_considerations JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO property_types_ref (code, name, category, description, typical_features, investment_considerations) VALUES
('house', 'House', 'residential', 'Detached single dwelling', '["bedrooms", "bathrooms", "garage", "garden"]'::jsonb, '["capital_growth", "rental_yield", "maintenance_costs"]'::jsonb),
('unit', 'Unit/Apartment', 'residential', 'Apartment or unit in multi-dwelling building', '["bedrooms", "bathrooms", "balcony", "parking"]'::jsonb, '["strata_fees", "capital_growth", "rental_demand"]'::jsonb),
('townhouse', 'Townhouse', 'residential', 'Multi-story attached dwelling', '["bedrooms", "bathrooms", "garage", "courtyard"]'::jsonb, '["lower_maintenance", "community_amenities", "strata_considerations"]'::jsonb),
('duplex', 'Duplex', 'residential', 'Semi-detached dwelling', '["bedrooms", "bathrooms", "garage", "garden"]'::jsonb, '["dual_income_potential", "shared_wall", "zoning_flexibility"]'::jsonb),
('land', 'Vacant Land', 'residential', 'Undeveloped residential land', '["size", "zoning", "services", "topography"]'::jsonb, '["development_potential", "holding_costs", "approval_risks"]'::jsonb),
('commercial', 'Commercial Property', 'commercial', 'Business or retail property', '["floor_area", "parking", "signage", "accessibility"]'::jsonb, '["lease_terms", "tenant_quality", "location_value"]'::jsonb)
ON CONFLICT (code) DO UPDATE SET
    description = EXCLUDED.description,
    typical_features = EXCLUDED.typical_features,
    investment_considerations = EXCLUDED.investment_considerations;

-- Create system configuration table
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'general',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert system configuration
INSERT INTO system_config (key, value, description, category) VALUES
(
    'analysis_settings',
    '{
        "default_timeout_seconds": 300,
        "max_file_size_mb": 50,
        "supported_file_types": ["pdf", "doc", "docx"],
        "default_analysis_options": {
            "include_financial_analysis": true,
            "include_risk_assessment": true,
            "include_compliance_check": true,
            "include_recommendations": true
        }
    }'::jsonb,
    'Default settings for contract analysis',
    'analysis'
),
(
    'notification_settings',
    '{
        "email_notifications": true,
        "push_notifications": false,
        "analysis_complete_notification": true,
        "weekly_summary": true,
        "credit_low_warning": true,
        "credit_low_threshold": 5
    }'::jsonb,
    'Default notification preferences for new users',
    'notifications'
),
(
    'feature_flags',
    '{
        "beta_features_enabled": false,
        "ai_chat_support": false,
        "property_valuation": false,
        "market_analysis": true,
        "multi_language_support": false
    }'::jsonb,
    'Feature flags for experimental functionality',
    'features'
)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- Create maintenance log for tracking database maintenance
CREATE TABLE IF NOT EXISTS maintenance_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    details JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10,3)
);

-- Insert initial maintenance log entry
INSERT INTO maintenance_log (operation, status, details) VALUES
('initial_seed_data', 'completed', '{"tables_seeded": ["subscription_plans", "australian_states_ref", "contract_types_ref", "property_types_ref", "system_config"], "version": "1.0.0"}'::jsonb);