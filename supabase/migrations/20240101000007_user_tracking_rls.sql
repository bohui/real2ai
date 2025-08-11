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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE user_contract_views ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own contract views" ON user_contract_views FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_user_property_views_user_id ON user_property_views(user_id);
CREATE INDEX idx_user_property_views_property_hash ON user_property_views(property_hash);
CREATE INDEX idx_user_contract_views_user_id ON user_contract_views(user_id);
CREATE INDEX idx_user_contract_views_content_hash ON user_contract_views(content_hash);

GRANT ALL ON document_pages TO authenticated;
GRANT ALL ON document_entities TO authenticated;
GRANT ALL ON document_diagrams TO authenticated;
GRANT ALL ON document_analyses TO authenticated;

ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;
ALTER TABLE contract_analyses DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE property_data DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE user_property_views IS 'User''s property search history with RLS for privacy';
COMMENT ON TABLE user_contract_views IS 'User''s contract analysis history with RLS for privacy';
COMMENT ON TABLE contracts IS 'Contract metadata - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE contract_analyses IS 'Contract analysis results - shared resource, RLS disabled, accessed by content_hash';
COMMENT ON TABLE document_pages IS 'Individual page metadata and content from document processing (shared)';
COMMENT ON TABLE document_entities IS 'Basic entities extracted from documents (shared)';
COMMENT ON TABLE property_data IS 'Property analysis data - shared resource, RLS disabled, accessed by property_hash';

