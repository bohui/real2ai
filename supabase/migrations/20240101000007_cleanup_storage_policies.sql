-- Cleanup and consolidate storage RLS policies
-- Remove the restrictive policies that were causing issues
-- Keep the working permissive policies for authenticated users

-- Drop the restrictive user-folder-specific policies from migration 20240101000005
DROP POLICY IF EXISTS "Users can view their own documents" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own documents" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own documents" ON storage.objects;

-- Create missing update/delete policies from the working permissive approach
-- Note: These policies should already exist, but we'll recreate them if needed

DO $$ 
BEGIN
    -- Update policy
    BEGIN
        CREATE POLICY "Authenticated users can update documents bucket"
        ON storage.objects FOR UPDATE
        USING (
            bucket_id = 'documents' 
            AND auth.role() = 'authenticated'
        );
    EXCEPTION 
        WHEN duplicate_object THEN
            NULL; -- Policy already exists, skip
    END;

    -- Delete policy  
    BEGIN
        CREATE POLICY "Authenticated users can delete documents bucket"
        ON storage.objects FOR DELETE
        USING (
            bucket_id = 'documents' 
            AND auth.role() = 'authenticated'
        );
    EXCEPTION 
        WHEN duplicate_object THEN
            NULL; -- Policy already exists, skip
    END;

    -- Upload policy
    BEGIN
        CREATE POLICY "Authenticated users can upload to documents bucket"
        ON storage.objects FOR INSERT
        WITH CHECK (
            bucket_id = 'documents' 
            AND auth.role() = 'authenticated'
        );
    EXCEPTION 
        WHEN duplicate_object THEN
            NULL; -- Policy already exists, skip
    END;

    -- Select policy
    BEGIN
        CREATE POLICY "Authenticated users can view documents bucket"
        ON storage.objects FOR SELECT
        USING (
            bucket_id = 'documents' 
            AND auth.role() = 'authenticated'
        );
    EXCEPTION 
        WHEN duplicate_object THEN
            NULL; -- Policy already exists, skip
    END;
END $$;

-- Keep service role policies (these work fine)
-- Note: These are already created by previous migrations

-- Clean up the debug function that's no longer needed
DROP FUNCTION IF EXISTS debug_auth_context();

-- Log the cleanup
DO $$
BEGIN
    RAISE NOTICE 'Storage policies cleanup completed - using permissive authenticated user policies';
END $$;