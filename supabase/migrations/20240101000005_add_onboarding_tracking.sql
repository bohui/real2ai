-- Migration to add onboarding tracking to existing profiles
-- This handles profiles that were created before onboarding tracking was implemented

-- Add onboarding columns if they don't exist (for safety)
DO $$ 
BEGIN
    -- Add onboarding_completed column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'onboarding_completed') THEN
        ALTER TABLE profiles ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add onboarding_completed_at column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'onboarding_completed_at') THEN
        ALTER TABLE profiles ADD COLUMN onboarding_completed_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Add onboarding_preferences column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'onboarding_preferences') THEN
        ALTER TABLE profiles ADD COLUMN onboarding_preferences JSONB DEFAULT '{}';
    END IF;
END $$;

-- Create index for onboarding_completed if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'idx_profiles_onboarding_completed') THEN
        CREATE INDEX idx_profiles_onboarding_completed ON profiles(onboarding_completed);
    END IF;
END $$;

-- Update existing profiles to have onboarding_completed = FALSE if NULL
-- This ensures backward compatibility
UPDATE profiles 
SET onboarding_completed = FALSE 
WHERE onboarding_completed IS NULL;

-- Update existing profiles with non-empty preferences to mark as onboarded
-- This handles users who may have already set up preferences in the old system
UPDATE profiles 
SET 
    onboarding_completed = TRUE,
    onboarding_completed_at = created_at,
    onboarding_preferences = preferences
WHERE 
    onboarding_completed = FALSE 
    AND preferences IS NOT NULL 
    AND preferences != '{}'::jsonb
    AND (
        preferences ? 'practice_area' OR 
        preferences ? 'jurisdiction' OR 
        preferences ? 'firm_size' OR
        preferences ? 'onboarding_completed'
    );

-- Add a comment to the table for documentation
COMMENT ON COLUMN profiles.onboarding_completed IS 'Tracks if user has completed initial onboarding process';
COMMENT ON COLUMN profiles.onboarding_completed_at IS 'Timestamp when user completed onboarding';
COMMENT ON COLUMN profiles.onboarding_preferences IS 'Preferences collected during onboarding process';