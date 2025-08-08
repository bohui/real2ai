-- Migration to fix missing columns causing schema errors
-- Adds document_id column to document_pages and error_message to contract_analyses

-- Add document_id column to document_pages table
ALTER TABLE document_pages 
ADD COLUMN document_id UUID REFERENCES documents(id) ON DELETE CASCADE;

-- Add error_message column to contract_analyses table  
ALTER TABLE contract_analyses
ADD COLUMN error_message TEXT;

-- Add processing_completed_at column to contract_analyses table
ALTER TABLE contract_analyses
ADD COLUMN processing_completed_at TIMESTAMP WITH TIME ZONE;

-- Create index for the new document_id column
CREATE INDEX idx_document_pages_document_id ON document_pages(document_id);

-- Update existing document_pages records to populate document_id from content_hash
-- This matches pages to documents based on their content_hash
UPDATE document_pages 
SET document_id = d.id
FROM documents d
WHERE document_pages.content_hash = d.content_hash
AND document_pages.document_id IS NULL;

-- Add comment for new columns
COMMENT ON COLUMN document_pages.document_id IS 'Reference to the document this page belongs to (for user-specific operations)';
COMMENT ON COLUMN contract_analyses.error_message IS 'Error message when analysis fails';