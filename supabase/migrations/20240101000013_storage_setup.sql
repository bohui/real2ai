-- Storage setup for Real2.AI documents  
-- Creates storage buckets and policies for secure file management
--
-- SECURITY NOTE: Uses user-specific RLS policies to ensure users can only access their own files.
-- Files are stored in user_id/filename paths and policies verify auth.uid() matches the folder.

-- Create storagmig
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,  -- Private bucket
    52428800,  -- 50MB limit
    ARRAY[
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
) ON CONFLICT (id) DO UPDATE SET
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Create storage bucket for generated reports
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'reports',
    'reports',
    false,  -- Private bucket
    10485760,  -- 10MB limit
    ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/html'
    ]
) ON CONFLICT (id) DO UPDATE SET
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Enable RLS on storage.objects table
-- ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Storage policies for documents bucket
-- SECURE: Users can only access files in their own folder (user_id/filename)
CREATE POLICY "Users can upload documents to their own folder"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
    AND auth.role() = 'authenticated'
);

CREATE POLICY "Users can view their own documents"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can update their own documents"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can delete their own documents"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'documents' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Service role can manage all documents
CREATE POLICY "Service role can manage all documents"
ON storage.objects FOR ALL
USING (
    bucket_id = 'documents' 
    AND auth.jwt() ->> 'role' = 'service_role'
);

-- Storage policies for reports bucket
CREATE POLICY "Users can access their own reports"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'reports' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Service role can manage all reports"
ON storage.objects FOR ALL
USING (
    bucket_id = 'reports' 
    AND auth.jwt() ->> 'role' = 'service_role'
);

-- Function to generate secure file path
CREATE OR REPLACE FUNCTION generate_secure_file_path(
    user_id UUID,
    original_filename TEXT,
    file_extension TEXT DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    file_uuid UUID;
    clean_filename TEXT;
    timestamp_str TEXT;
    extension TEXT;
BEGIN
    -- Generate UUID for file
    file_uuid := uuid_generate_v4();
    
    -- Clean filename (remove special characters, limit length)
    clean_filename := regexp_replace(
        substring(original_filename FROM 1 FOR 50), 
        '[^a-zA-Z0-9._-]', 
        '_', 
        'g'
    );
    
    -- Get timestamp
    timestamp_str := to_char(NOW(), 'YYYY/MM/DD');
    
    -- Determine extension
    IF file_extension IS NOT NULL THEN
        extension := file_extension;
    ELSE
        extension := split_part(original_filename, '.', -1);
    END IF;
    
    -- Return secure path: user_id/YYYY/MM/DD/uuid_filename.ext
    RETURN format('%s/%s/%s_%s.%s', 
        user_id, 
        timestamp_str, 
        file_uuid, 
        clean_filename,
        extension
    );
END;
$$ LANGUAGE plpgsql;

-- Function to validate file upload
CREATE OR REPLACE FUNCTION validate_file_upload(
    user_id UUID,
    filename TEXT,
    file_size BIGINT,
    mime_type TEXT
)
RETURNS JSONB AS $$
DECLARE
    user_plan TEXT;
    max_file_size BIGINT;
    allowed_types TEXT[];
    result JSONB;
BEGIN
    -- Get user's subscription plan limits
    SELECT 
        sp.max_file_size_mb * 1024 * 1024,
        ARRAY['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    INTO max_file_size, allowed_types
    FROM profiles p
    JOIN subscription_plans sp ON sp.slug = p.subscription_status::text
    WHERE p.id = user_id;
    
    -- Default limits if plan not found
    IF max_file_size IS NULL THEN
        max_file_size := 10 * 1024 * 1024; -- 10MB default
        allowed_types := ARRAY['application/pdf'];
    END IF;
    
    -- Validate file size
    IF file_size > max_file_size THEN
        RETURN jsonb_build_object(
            'valid', false,
            'error', 'file_too_large',
            'message', format('File size %s MB exceeds limit of %s MB', 
                round(file_size::decimal / 1024 / 1024, 2),
                round(max_file_size::decimal / 1024 / 1024, 2)
            ),
            'max_size_mb', round(max_file_size::decimal / 1024 / 1024, 2)
        );
    END IF;
    
    -- Validate MIME type
    IF NOT (mime_type = ANY(allowed_types)) THEN
        RETURN jsonb_build_object(
            'valid', false,
            'error', 'invalid_file_type',
            'message', format('File type %s is not supported', mime_type),
            'allowed_types', to_jsonb(allowed_types)
        );
    END IF;
    
    -- Validate filename
    IF length(filename) > 255 OR filename ~ '[<>:"/\\|?*]' THEN
        RETURN jsonb_build_object(
            'valid', false,
            'error', 'invalid_filename',
            'message', 'Filename contains invalid characters or is too long'
        );
    END IF;
    
    -- All validations passed
    RETURN jsonb_build_object(
        'valid', true,
        'max_size_mb', round(max_file_size::decimal / 1024 / 1024, 2),
        'allowed_types', to_jsonb(allowed_types)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to track storage usage
CREATE OR REPLACE FUNCTION update_storage_usage(
    user_id UUID,
    file_size BIGINT,
    operation TEXT -- 'add' or 'remove'
)
RETURNS BOOLEAN AS $$
DECLARE
    current_usage BIGINT;
BEGIN
    -- Get current storage usage from user metadata
    SELECT COALESCE((preferences->>'storage_used_bytes')::BIGINT, 0)
    INTO current_usage
    FROM profiles
    WHERE id = user_id;
    
    -- Update storage usage
    IF operation = 'add' THEN
        current_usage := current_usage + file_size;
    ELSIF operation = 'remove' THEN
        current_usage := GREATEST(0, current_usage - file_size);
    END IF;
    
    -- Update user profile
    UPDATE profiles
    SET preferences = preferences || jsonb_build_object('storage_used_bytes', current_usage)
    WHERE id = user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update storage usage when documents are added/removed
CREATE OR REPLACE FUNCTION handle_document_storage_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM update_storage_usage(NEW.user_id, NEW.file_size, 'add');
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM update_storage_usage(OLD.user_id, OLD.file_size, 'remove');
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Handle file size changes
        IF OLD.file_size != NEW.file_size THEN
            PERFORM update_storage_usage(NEW.user_id, OLD.file_size, 'remove');
            PERFORM update_storage_usage(NEW.user_id, NEW.file_size, 'add');
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_storage_trigger
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION handle_document_storage_change();

-- Function to clean up orphaned files (files in storage but not in database)
CREATE OR REPLACE FUNCTION cleanup_orphaned_files()
RETURNS INTEGER AS $$
DECLARE
    orphaned_count INTEGER := 0;
    file_record RECORD;
BEGIN
    -- This function would need to be run with service_role privileges
    -- and would compare storage.objects with documents table
    
    -- For now, return count of files that might be orphaned
    SELECT COUNT(*) INTO orphaned_count
    FROM storage.objects so
    WHERE so.bucket_id = 'documents'
    AND NOT EXISTS (
        SELECT 1 FROM documents d 
        WHERE d.storage_path = so.name
    );
    
    RETURN orphaned_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create view for user storage statistics
CREATE OR REPLACE VIEW user_storage_stats 
WITH (security_barrier = true) AS
SELECT 
    p.id as user_id,
    p.email,
    p.subscription_status,
    sp.max_file_size_mb,
    COALESCE((p.preferences->>'storage_used_bytes')::BIGINT, 0) as storage_used_bytes,
    round(COALESCE((p.preferences->>'storage_used_bytes')::BIGINT, 0)::decimal / 1024 / 1024, 2) as storage_used_mb,
    COUNT(d.id) as total_files,
    MAX(d.created_at) as last_upload,
    sp.max_file_size_mb * 1024 * 1024 as storage_limit_bytes,
    round(
        (COALESCE((p.preferences->>'storage_used_bytes')::BIGINT, 0)::decimal / 
         (sp.max_file_size_mb * 1024 * 1024)::decimal) * 100, 
        2
    ) as storage_usage_percentage
FROM profiles p
LEFT JOIN subscription_plans sp ON sp.slug = p.subscription_status::text
LEFT JOIN documents d ON d.user_id = p.id
GROUP BY p.id, p.email, p.subscription_status, sp.max_file_size_mb, p.preferences;

-- Grant appropriate permissions on the view
GRANT SELECT ON user_storage_stats TO authenticated;

-- RLS policy for the view
-- ALTER VIEW user_storage_stats ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own storage stats" ON user_storage_stats
--     FOR SELECT USING (auth.uid() = user_id);

-- Note: ensure_bucket_exists function is now defined in the initial migration (20240101000000_initial_schema.sql)
-- to avoid return type conflicts and maintain consistent schema setup

-- Note: All property intelligence tables and functions have been moved to the initial schema
-- This migration now focuses only on storage-specific functionality