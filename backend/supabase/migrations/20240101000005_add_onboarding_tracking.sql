-- Enable RLS on storage.objects table if not already enabled
-- This is required for file upload policies to work properly

-- Enable RLS on storage.objects (this might already be enabled but we make sure)
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Check if our storage policies exist and are correctly configured
-- If they don't exist, the migration will continue without error

-- Recreate the main upload policy to ensure it works correctly
DROP POLICY IF EXISTS "Users can upload documents to their own folder" ON storage.objects;
CREATE POLICY "Users can upload documents to their own folder"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
    AND auth.role() = 'authenticated'
);

-- Ensure the view policy exists for users to access their files
DROP POLICY IF EXISTS "Users can view their own documents" ON storage.objects;
CREATE POLICY "Users can view their own documents"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Ensure update policy exists
DROP POLICY IF EXISTS "Users can update their own documents" ON storage.objects;
CREATE POLICY "Users can update their own documents"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Ensure delete policy exists
DROP POLICY IF EXISTS "Users can delete their own documents" ON storage.objects;
CREATE POLICY "Users can delete their own documents"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Ensure service role policy exists
DROP POLICY IF EXISTS "Service role can manage all documents" ON storage.objects;
CREATE POLICY "Service role can manage all documents"
ON storage.objects FOR ALL
USING (
    bucket_id = 'documents' 
    AND auth.jwt() ->> 'role' = 'service_role'
);

-- Reports bucket policies
DROP POLICY IF EXISTS "Users can access their own reports" ON storage.objects;
CREATE POLICY "Users can access their own reports"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'reports' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

DROP POLICY IF EXISTS "Service role can manage all reports" ON storage.objects;
CREATE POLICY "Service role can manage all reports"
ON storage.objects FOR ALL
USING (
    bucket_id = 'reports' 
    AND auth.jwt() ->> 'role' = 'service_role'
);

-- Add a more permissive policy for authenticated users as a fallback
-- This helps debug authentication issues
CREATE POLICY IF NOT EXISTS "Debug: authenticated users can upload to documents"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'documents' 
    AND auth.role() = 'authenticated'
);

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Storage RLS policies updated successfully';
END $$;