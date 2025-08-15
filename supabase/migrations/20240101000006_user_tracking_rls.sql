-- User tracking and RLS for user-scoped views

CREATE TABLE user_property_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_hash TEXT NOT NULL,
    property_address TEXT NOT NULL,
    source TEXT DEFAULT 'search',
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE user_property_views ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own property views" ON user_property_views FOR ALL USING (auth.uid() = user_id);

CREATE TABLE user_contract_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    property_address TEXT,
    analysis_id UUID,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT CHECK (source IN ('upload', 'cache_hit')) DEFAULT 'upload',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE user_contract_views ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own contract views" ON user_contract_views FOR ALL USING (auth.uid() = user_id);

-- Auto-update trigger for updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language plpgsql;

CREATE TRIGGER update_user_contract_views_updated_at
    BEFORE UPDATE ON user_contract_views
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_user_property_views_user_id ON user_property_views(user_id);
CREATE INDEX idx_user_property_views_property_hash ON user_property_views(property_hash);
CREATE INDEX idx_user_contract_views_user_id ON user_contract_views(user_id);
CREATE INDEX idx_user_contract_views_content_hash ON user_contract_views(content_hash);


COMMENT ON TABLE user_property_views IS 'User''s property search history with RLS for privacy';
COMMENT ON TABLE user_contract_views IS 'User''s contract analysis history with RLS for privacy';
COMMENT ON TABLE contracts IS 'Contract metadata - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE analyses IS 'Analysis results - flexible scoping, RLS enabled, accessed by content_hash and user_id';

