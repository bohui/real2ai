-- Storage upload policies for authenticated users
-- Permissive policies that allow authenticated users to access documents bucket

-- First, let's check if we have the right policies and make them more permissive temporarily

-- Drop existing restrictive policies if they exist
DROP POLICY IF EXISTS "Users can upload documents to their own folder" ON storage.objects;
DROP POLICY IF EXISTS "Debug: authenticated users can upload to documents" ON storage.objects;

-- Create a more permissive policy for testing
CREATE POLICY "Authenticated users can upload to documents bucket"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'documents' 
    AND auth.role() = 'authenticated'
);

-- Create a simple select policy
CREATE POLICY "Authenticated users can view documents bucket"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'documents' 
    AND auth.role() = 'authenticated'
);

-- Create update/delete policies
CREATE POLICY "Authenticated users can update documents bucket"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'documents' 
    AND auth.role() = 'authenticated'
);

CREATE POLICY "Authenticated users can delete documents bucket"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'documents' 
    AND auth.role() = 'authenticated'
);

-- Keep the service role policy
CREATE POLICY IF NOT EXISTS "Service role can manage all documents"
ON storage.objects FOR ALL
USING (
    bucket_id = 'documents' 
    AND auth.jwt() ->> 'role' = 'service_role'
);

-- Also ensure RLS is enabled
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Log the change
DO $$
BEGIN
    RAISE NOTICE 'Applied permissive storage policies for authenticated users';
END $$;