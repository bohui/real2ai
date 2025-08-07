-- Migration: Remove cache tables and simplify architecture
-- This migration removes the dedicated cache tables (hot_properties_cache and hot_contracts_cache)
-- in favor of direct source table access with RLS disabled for cross-user cache sharing

-- Drop cache tables if they exist
DROP TABLE IF EXISTS hot_properties_cache CASCADE;
DROP TABLE IF EXISTS hot_contracts_cache CASCADE;

-- Drop cache-related functions if they exist
DROP FUNCTION IF EXISTS cleanup_expired_cache() CASCADE;

-- Ensure RLS is disabled on analysis tables for cross-user cache sharing
ALTER TABLE contract_analyses DISABLE ROW LEVEL SECURITY;

-- Create property_data table if it doesn't exist
CREATE TABLE IF NOT EXISTS property_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_hash TEXT NOT NULL UNIQUE,
    property_address TEXT NOT NULL,
    analysis_result JSONB NOT NULL,
    processing_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Disable RLS on property_data for cross-user cache sharing
ALTER TABLE property_data DISABLE ROW LEVEL SECURITY;

-- Create performance indexes for direct cache access
CREATE INDEX IF NOT EXISTS idx_contract_analyses_content_hash 
    ON contract_analyses(content_hash) 
    WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS idx_contract_analyses_created_at 
    ON contract_analyses(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_property_data_property_hash 
    ON property_data(property_hash);

CREATE INDEX IF NOT EXISTS idx_property_data_created_at 
    ON property_data(created_at DESC);

-- Add comment explaining the new architecture
COMMENT ON TABLE contract_analyses IS 'Contract analysis results - RLS disabled for cross-user cache sharing via content hash';
COMMENT ON TABLE property_data IS 'Property analysis data - RLS disabled for cross-user cache sharing via property hash';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Cache tables removed successfully. Using direct source table access for caching.';
END $$;