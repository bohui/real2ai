-- Artifact Security Policies - Run after artifact tables are created
-- This migration runs after 20240101000009_artifacts_and_user_scoped_processing.sql
-- to ensure artifact tables exist before enabling RLS and creating policies

-- Enable RLS on artifact tables (they were created with RLS disabled)
ALTER TABLE text_extraction_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_diagrams ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_paragraphs ENABLE ROW LEVEL SECURITY;

-- Service-role-only policies for artifact tables
CREATE POLICY IF NOT EXISTS "Service role only access to text_extraction_artifacts" 
    ON text_extraction_artifacts FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role only access to artifact_pages" 
    ON artifact_pages FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role only access to artifact_paragraphs" 
    ON artifact_paragraphs FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role only access to artifact_diagrams" 
    ON artifact_diagrams FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Enhanced policies for user-scoped document processing tables
-- These tables were created with basic policies in 20240101000009, 
-- now we enhance them to match the security model from other migrations

-- Drop existing basic policies and create enhanced ones
DROP POLICY IF EXISTS "Users can access their own user_document_pages" ON user_document_pages;
DROP POLICY IF EXISTS "Service role can access all user_document_pages" ON user_document_pages;
DROP POLICY IF EXISTS "Users can access their own user_document_diagrams" ON user_document_diagrams;
DROP POLICY IF EXISTS "Service role can access all user_document_diagrams" ON user_document_diagrams;
DROP POLICY IF EXISTS "Users can access their own user_document_paragraphs" ON user_document_paragraphs;
DROP POLICY IF EXISTS "Service role can access all user_document_paragraphs" ON user_document_paragraphs;

-- Create enhanced policies for user document tables
CREATE POLICY "Users can manage own document pages" 
    ON user_document_pages FOR ALL 
    USING (
        auth.jwt() ->> 'role' = 'service_role'
        OR 
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = user_document_pages.document_id 
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage own document diagrams" 
    ON user_document_diagrams FOR ALL 
    USING (
        auth.jwt() ->> 'role' = 'service_role'
        OR 
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = user_document_diagrams.document_id 
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage own document paragraphs" 
    ON user_document_paragraphs FOR ALL 
    USING (
        auth.jwt() ->> 'role' = 'service_role'
        OR 
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = user_document_paragraphs.document_id 
            AND d.user_id = auth.uid()
        )
    );

-- Revoke direct access to artifact tables from regular users
REVOKE ALL ON TABLE text_extraction_artifacts FROM anon;
REVOKE ALL ON TABLE text_extraction_artifacts FROM authenticated;
REVOKE ALL ON TABLE artifact_pages FROM anon;
REVOKE ALL ON TABLE artifact_pages FROM authenticated;
REVOKE ALL ON TABLE artifact_paragraphs FROM anon;
REVOKE ALL ON TABLE artifact_paragraphs FROM authenticated;
REVOKE ALL ON TABLE artifact_diagrams FROM anon;
REVOKE ALL ON TABLE artifact_diagrams FROM authenticated;

-- Comments for artifact security policies
COMMENT ON POLICY "Service role only access to text_extraction_artifacts" ON text_extraction_artifacts IS 'Only service role can access text extraction artifacts - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_pages" ON artifact_pages IS 'Only service role can access artifact pages - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_paragraphs" ON artifact_paragraphs IS 'Only service role can access artifact paragraphs - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_diagrams" ON artifact_diagrams IS 'Only service role can access artifact diagrams - shared cached data for content-addressed storage';
COMMENT ON POLICY "Users can manage own document pages" ON user_document_pages IS 'Users can manage document pages for their own documents via foreign key relationship';
COMMENT ON POLICY "Users can manage own document diagrams" ON user_document_diagrams IS 'Users can manage document diagrams for their own documents via foreign key relationship';
COMMENT ON POLICY "Users can manage own document paragraphs" ON user_document_paragraphs IS 'Users can manage document paragraphs for their own documents via foreign key relationship';