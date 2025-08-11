-- Artifact tables (shared, RLS disabled) and user-scoped processing tables (RLS enabled)

-- Shared artifacts
CREATE TABLE IF NOT EXISTS text_extraction_artifacts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    full_text_uri text NOT NULL,
    full_text_sha256 text NOT NULL,
    total_pages int NOT NULL,
    total_words int NOT NULL,
    methods jsonb NOT NULL,
    timings jsonb,
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_text_extraction_artifacts_lookup
    ON text_extraction_artifacts (content_hmac, algorithm_version, params_fingerprint);

CREATE TABLE IF NOT EXISTS artifact_pages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    page_number int NOT NULL,
    page_text_uri text NOT NULL,
    page_text_sha256 text NOT NULL,
    layout jsonb,
    metrics jsonb,
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number)
);

CREATE INDEX IF NOT EXISTS idx_artifact_pages_lookup
    ON artifact_pages (content_hmac, algorithm_version, params_fingerprint);

CREATE TABLE IF NOT EXISTS artifact_diagrams (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    page_number int NOT NULL,
    diagram_key text NOT NULL,
    diagram_meta jsonb NOT NULL,
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key)
);

CREATE INDEX IF NOT EXISTS idx_artifact_diagrams_lookup
    ON artifact_diagrams (content_hmac, algorithm_version, params_fingerprint);

CREATE TABLE IF NOT EXISTS artifact_paragraphs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hmac text NOT NULL,
    algorithm_version int NOT NULL,
    params_fingerprint text NOT NULL,
    page_number int NOT NULL,
    paragraph_index int NOT NULL,
    paragraph_text_uri text NOT NULL,
    paragraph_text_sha256 text NOT NULL,
    features jsonb,
    created_at timestamptz DEFAULT now(),
    UNIQUE (content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index)
);

-- Add data integrity constraints
DO $$
BEGIN
  -- Check constraints for text_extraction_artifacts
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_text_extraction_artifacts_content_hmac_length'
  ) THEN
    EXECUTE 'ALTER TABLE text_extraction_artifacts ADD CONSTRAINT chk_text_extraction_artifacts_content_hmac_length 
             CHECK (length(content_hmac) = 64 AND content_hmac ~ ''^[a-f0-9]+$'')';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_text_extraction_artifacts_params_fingerprint_length'
  ) THEN
    EXECUTE 'ALTER TABLE text_extraction_artifacts ADD CONSTRAINT chk_text_extraction_artifacts_params_fingerprint_length 
             CHECK (length(params_fingerprint) = 64 AND params_fingerprint ~ ''^[a-f0-9]+$'')';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_text_extraction_artifacts_sha256_length'
  ) THEN
    EXECUTE 'ALTER TABLE text_extraction_artifacts ADD CONSTRAINT chk_text_extraction_artifacts_sha256_length 
             CHECK (length(full_text_sha256) = 64 AND full_text_sha256 ~ ''^[a-f0-9]+$'')';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_text_extraction_artifacts_positive_counts'
  ) THEN
    EXECUTE 'ALTER TABLE text_extraction_artifacts ADD CONSTRAINT chk_text_extraction_artifacts_positive_counts 
             CHECK (total_pages >= 0 AND total_words >= 0 AND algorithm_version > 0)';
  END IF;

  -- Check constraints for artifact_pages
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_artifact_pages_page_number_positive'
  ) THEN
    EXECUTE 'ALTER TABLE artifact_pages ADD CONSTRAINT chk_artifact_pages_page_number_positive 
             CHECK (page_number > 0)';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_artifact_pages_sha256_length'
  ) THEN
    EXECUTE 'ALTER TABLE artifact_pages ADD CONSTRAINT chk_artifact_pages_sha256_length 
             CHECK (length(page_text_sha256) = 64 AND page_text_sha256 ~ ''^[a-f0-9]+$'')';
  END IF;

  -- Check constraints for artifact_paragraphs
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_artifact_paragraphs_indices_non_negative'
  ) THEN
    EXECUTE 'ALTER TABLE artifact_paragraphs ADD CONSTRAINT chk_artifact_paragraphs_indices_non_negative 
             CHECK (page_number > 0 AND paragraph_index >= 0)';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_artifact_paragraphs_sha256_length'
  ) THEN
    EXECUTE 'ALTER TABLE artifact_paragraphs ADD CONSTRAINT chk_artifact_paragraphs_sha256_length 
             CHECK (length(paragraph_text_sha256) = 64 AND paragraph_text_sha256 ~ ''^[a-f0-9]+$'')';
  END IF;

  -- Check constraints for artifact_diagrams
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_artifact_diagrams_page_number_positive'
  ) THEN
    EXECUTE 'ALTER TABLE artifact_diagrams ADD CONSTRAINT chk_artifact_diagrams_page_number_positive 
             CHECK (page_number > 0)';
  END IF;
END $$;

-- RLS configuration for artifact tables (service role only)
ALTER TABLE text_extraction_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_diagrams ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_paragraphs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role only access to text_extraction_artifacts" 
    ON text_extraction_artifacts FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role only access to artifact_pages" 
    ON artifact_pages FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role only access to artifact_paragraphs" 
    ON artifact_paragraphs FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role only access to artifact_diagrams" 
    ON artifact_diagrams FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Revoke direct access to artifact tables from regular users
REVOKE ALL ON TABLE text_extraction_artifacts FROM anon;
REVOKE ALL ON TABLE text_extraction_artifacts FROM authenticated;
REVOKE ALL ON TABLE artifact_pages FROM anon;
REVOKE ALL ON TABLE artifact_pages FROM authenticated;
REVOKE ALL ON TABLE artifact_paragraphs FROM anon;
REVOKE ALL ON TABLE artifact_paragraphs FROM authenticated;
REVOKE ALL ON TABLE artifact_diagrams FROM anon;
REVOKE ALL ON TABLE artifact_diagrams FROM authenticated;

-- Documents reference to artifacts with foreign key constraint
ALTER TABLE documents ADD COLUMN IF NOT EXISTS artifact_text_id uuid;

-- Add foreign key constraint for documents -> text_extraction_artifacts
-- Use ON DELETE SET NULL to handle graceful artifact cleanup
DO $$
BEGIN
  -- Only add constraint if it doesn't already exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'documents_artifact_text_fk'
    AND table_name = 'documents'
  ) THEN
    EXECUTE 'ALTER TABLE documents ADD CONSTRAINT documents_artifact_text_fk 
             FOREIGN KEY (artifact_text_id) REFERENCES text_extraction_artifacts(id) 
             ON DELETE SET NULL';
  END IF;
END $$;

-- Add additional integrity constraints to documents table
DO $$
BEGIN
  -- Ensure total_pages is non-negative when set
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_documents_total_pages_non_negative'
  ) THEN
    EXECUTE 'ALTER TABLE documents ADD CONSTRAINT chk_documents_total_pages_non_negative 
             CHECK (total_pages IS NULL OR total_pages >= 0)';
  END IF;
  
  -- Ensure total_word_count is non-negative when set  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'chk_documents_total_word_count_non_negative'
  ) THEN
    EXECUTE 'ALTER TABLE documents ADD CONSTRAINT chk_documents_total_word_count_non_negative 
             CHECK (total_word_count IS NULL OR total_word_count >= 0)';
  END IF;
END $$;

-- User-scoped tables referencing artifacts
CREATE TABLE IF NOT EXISTS user_document_pages (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number int NOT NULL,
    artifact_page_id uuid NOT NULL REFERENCES artifact_pages(id),
    annotations jsonb,
    flags jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (document_id, page_number)
);

CREATE TABLE IF NOT EXISTS user_document_diagrams (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number int NOT NULL,
    diagram_key text NOT NULL,
    artifact_diagram_id uuid NOT NULL REFERENCES artifact_diagrams(id),
    annotations jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (document_id, page_number, diagram_key)
);

CREATE TABLE IF NOT EXISTS user_document_paragraphs (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number int NOT NULL,
    paragraph_index int NOT NULL,
    artifact_paragraph_id uuid NOT NULL REFERENCES artifact_paragraphs(id),
    annotations jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (document_id, page_number, paragraph_index)
);

-- RLS and policies for user document tables
ALTER TABLE user_document_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_document_diagrams ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_document_paragraphs ENABLE ROW LEVEL SECURITY;

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

-- Indexes for user document tables
CREATE INDEX IF NOT EXISTS idx_user_document_pages_doc ON user_document_pages(document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_user_document_diagrams_doc ON user_document_diagrams(document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_user_document_paragraphs_doc ON user_document_paragraphs(document_id, page_number);

-- Processing runs and steps
CREATE TABLE IF NOT EXISTS document_processing_runs (
    run_id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES profiles(id),
    status text NOT NULL CHECK (status IN ('queued','in_progress','completed','failed')),
    last_step text,
    error jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_processing_runs_user
    ON document_processing_runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_processing_runs_document
    ON document_processing_runs (document_id, created_at DESC);

CREATE TABLE IF NOT EXISTS document_processing_steps (
    run_id uuid NOT NULL REFERENCES document_processing_runs(run_id) ON DELETE CASCADE,
    step_name text NOT NULL,
    status text NOT NULL CHECK (status IN ('started','success','failed','skipped')),
    state_snapshot jsonb,
    error jsonb,
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    PRIMARY KEY (run_id, step_name)
);

CREATE INDEX IF NOT EXISTS idx_document_processing_steps_run
    ON document_processing_steps (run_id, started_at);

-- RLS for processing tables
ALTER TABLE document_processing_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_processing_steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their own processing runs" ON document_processing_runs
    FOR ALL USING (user_id = auth.uid());
CREATE POLICY "Users can access their own processing steps" ON document_processing_steps
    FOR ALL USING (run_id IN (SELECT run_id FROM document_processing_runs WHERE user_id = auth.uid()));
CREATE POLICY "Service role can access all processing runs" ON document_processing_runs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
CREATE POLICY "Service role can access all processing steps" ON document_processing_steps
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Set updated_at to current timestamp
    NEW.updated_at = NOW();
    
    -- Ensure created_at is never modified after initial insert
    IF TG_OP = 'UPDATE' AND OLD.created_at IS NOT NULL THEN
        NEW.created_at = OLD.created_at;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION update_updated_at_column() IS 
'Automatically updates updated_at timestamp on row updates and preserves created_at';

-- Triggers for updated_at columns
CREATE TRIGGER update_document_processing_runs_updated_at 
    BEFORE UPDATE ON document_processing_runs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_document_pages_updated_at 
    BEFORE UPDATE ON user_document_pages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_document_diagrams_updated_at 
    BEFORE UPDATE ON user_document_diagrams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_document_paragraphs_updated_at 
    BEFORE UPDATE ON user_document_paragraphs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for artifact security policies
COMMENT ON POLICY "Service role only access to text_extraction_artifacts" ON text_extraction_artifacts IS 'Only service role can access text extraction artifacts - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_pages" ON artifact_pages IS 'Only service role can access artifact pages - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_paragraphs" ON artifact_paragraphs IS 'Only service role can access artifact paragraphs - shared cached data for content-addressed storage';
COMMENT ON POLICY "Service role only access to artifact_diagrams" ON artifact_diagrams IS 'Only service role can access artifact diagrams - shared cached data for content-addressed storage';
COMMENT ON POLICY "Users can manage own document pages" ON user_document_pages IS 'Users can manage document pages for their own documents via foreign key relationship';
COMMENT ON POLICY "Users can manage own document diagrams" ON user_document_diagrams IS 'Users can manage document diagrams for their own documents via foreign key relationship';
COMMENT ON POLICY "Users can manage own document paragraphs" ON user_document_paragraphs IS 'Users can manage document paragraphs for their own documents via foreign key relationship';

