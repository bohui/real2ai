-- Enhanced Timestamp Management Migration
-- Ensures all tables have proper created_at/updated_at timestamp handling
-- This supplements existing triggers and adds comprehensive timestamp management

-- Enhanced trigger function with better error handling
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

-- Add comment for documentation
COMMENT ON FUNCTION update_updated_at_column() IS 
'Automatically updates updated_at timestamp on row updates and preserves created_at';

-- Ensure all tables have proper triggers (idempotent operations)
-- These will only create triggers if they don't already exist

-- Core tables
DO $$ 
BEGIN
    -- Profiles
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_profiles_updated_at'
    ) THEN
        CREATE TRIGGER update_profiles_updated_at 
            BEFORE UPDATE ON profiles 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Documents (already exists, ensure it's using the enhanced function)
    DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
    CREATE TRIGGER update_documents_updated_at 
        BEFORE UPDATE ON documents 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Contracts
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_contracts_updated_at'
    ) THEN
        CREATE TRIGGER update_contracts_updated_at 
            BEFORE UPDATE ON contracts 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Contract analyses
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_contract_analyses_updated_at'
    ) THEN
        CREATE TRIGGER update_contract_analyses_updated_at 
            BEFORE UPDATE ON contract_analyses 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Document pages
    DROP TRIGGER IF EXISTS update_document_pages_updated_at ON document_pages;
    CREATE TRIGGER update_document_pages_updated_at 
        BEFORE UPDATE ON document_pages 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Document entities
    DROP TRIGGER IF EXISTS update_document_entities_updated_at ON document_entities;
    CREATE TRIGGER update_document_entities_updated_at 
        BEFORE UPDATE ON document_entities 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Document diagrams
    DROP TRIGGER IF EXISTS update_document_diagrams_updated_at ON document_diagrams;
    CREATE TRIGGER update_document_diagrams_updated_at 
        BEFORE UPDATE ON document_diagrams 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Document analyses
    DROP TRIGGER IF EXISTS update_document_analyses_updated_at ON document_analyses;
    CREATE TRIGGER update_document_analyses_updated_at 
        BEFORE UPDATE ON document_analyses 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Property data
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_property_data_updated_at'
    ) THEN
        CREATE TRIGGER update_property_data_updated_at 
            BEFORE UPDATE ON property_data 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- User subscriptions
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_subscriptions_updated_at'
    ) THEN
        CREATE TRIGGER update_user_subscriptions_updated_at 
            BEFORE UPDATE ON user_subscriptions 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Analysis progress
    DROP TRIGGER IF EXISTS update_analysis_progress_updated_at ON analysis_progress;
    CREATE TRIGGER update_analysis_progress_updated_at 
        BEFORE UPDATE ON analysis_progress 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
END $$;

-- Function to verify all timestamp columns have proper defaults
CREATE OR REPLACE FUNCTION verify_timestamp_defaults()
RETURNS TABLE(
    table_name TEXT,
    created_at_default TEXT,
    updated_at_default TEXT,
    has_trigger BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        COALESCE(c_created.column_default, 'NO DEFAULT')::TEXT as created_at_default,
        COALESCE(c_updated.column_default, 'NO DEFAULT')::TEXT as updated_at_default,
        EXISTS(
            SELECT 1 FROM pg_trigger tr 
            WHERE tr.tgname = 'update_' || t.table_name || '_updated_at'
        ) as has_trigger
    FROM information_schema.tables t
    LEFT JOIN information_schema.columns c_created ON (
        c_created.table_name = t.table_name 
        AND c_created.column_name = 'created_at'
        AND c_created.table_schema = 'public'
    )
    LEFT JOIN information_schema.columns c_updated ON (
        c_updated.table_name = t.table_name 
        AND c_updated.column_name = 'updated_at'
        AND c_updated.table_schema = 'public'
    )
    WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
    AND (c_created.column_name IS NOT NULL OR c_updated.column_name IS NOT NULL)
    ORDER BY t.table_name;
END;
$$ LANGUAGE plpgsql;

-- Function to create timestamps on existing records (if needed)
CREATE OR REPLACE FUNCTION backfill_timestamps(target_table TEXT)
RETURNS INTEGER AS $$
DECLARE
    rows_updated INTEGER := 0;
    sql_query TEXT;
BEGIN
    -- Update records where created_at is NULL
    sql_query := format('UPDATE %I SET created_at = NOW() WHERE created_at IS NULL', target_table);
    EXECUTE sql_query;
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    
    -- Update records where updated_at is NULL  
    sql_query := format('UPDATE %I SET updated_at = created_at WHERE updated_at IS NULL', target_table);
    EXECUTE sql_query;
    
    RETURN rows_updated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add helpful comments to all timestamp columns
DO $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    LOOP
        -- Add comments for created_at columns
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = table_record.table_name 
            AND column_name = 'created_at' 
            AND table_schema = 'public'
        ) THEN
            EXECUTE format('COMMENT ON COLUMN %I.created_at IS %L', 
                table_record.table_name, 
                'Automatically set on record creation (DEFAULT NOW())');
        END IF;

        -- Add comments for updated_at columns
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = table_record.table_name 
            AND column_name = 'updated_at' 
            AND table_schema = 'public'
        ) THEN
            EXECUTE format('COMMENT ON COLUMN %I.updated_at IS %L', 
                table_record.table_name, 
                'Automatically updated on record modification (trigger managed)');
        END IF;
    END LOOP;
END $$;

-- Create a view for monitoring timestamp management
CREATE OR REPLACE VIEW timestamp_management_status AS
SELECT 
    table_name,
    created_at_default,
    updated_at_default,
    has_trigger,
    CASE 
        WHEN created_at_default LIKE '%now()%' 
        AND updated_at_default LIKE '%now()%' 
        AND has_trigger THEN 'OPTIMAL'
        WHEN has_trigger THEN 'GOOD'
        ELSE 'NEEDS_ATTENTION'
    END as status
FROM verify_timestamp_defaults();

-- Grant permissions
GRANT SELECT ON timestamp_management_status TO authenticated;
GRANT EXECUTE ON FUNCTION verify_timestamp_defaults() TO authenticated;
GRANT EXECUTE ON FUNCTION backfill_timestamps(TEXT) TO service_role;

-- Add indexes for timestamp queries (if they don't exist)
DO $$
BEGIN
    -- Index for created_at queries on main tables
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contracts_created_at ON contracts(created_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contract_analyses_created_at ON contract_analyses(created_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
    
    -- Index for updated_at queries (useful for sync operations)
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_updated_at ON documents(updated_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contracts_updated_at ON contracts(updated_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contract_analyses_updated_at ON contract_analyses(updated_at DESC);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_updated_at ON profiles(updated_at DESC);

EXCEPTION WHEN duplicate_table THEN
    -- Indexes already exist, continue
    NULL;
END $$;

-- Example usage functions for application code
CREATE OR REPLACE FUNCTION get_recent_records(
    table_name TEXT, 
    hours_back INTEGER DEFAULT 24,
    limit_count INTEGER DEFAULT 100
)
RETURNS SETOF RECORD AS $$
DECLARE
    sql_query TEXT;
BEGIN
    sql_query := format(
        'SELECT * FROM %I WHERE created_at > NOW() - INTERVAL ''%s hours'' ORDER BY created_at DESC LIMIT %s',
        table_name, hours_back, limit_count
    );
    RETURN QUERY EXECUTE sql_query;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_recently_updated_records(
    table_name TEXT, 
    minutes_back INTEGER DEFAULT 60,
    limit_count INTEGER DEFAULT 100
)
RETURNS SETOF RECORD AS $$
DECLARE
    sql_query TEXT;
BEGIN
    sql_query := format(
        'SELECT * FROM %I WHERE updated_at > NOW() - INTERVAL ''%s minutes'' ORDER BY updated_at DESC LIMIT %s',
        table_name, minutes_back, limit_count
    );
    RETURN QUERY EXECUTE sql_query;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Final verification and status report
DO $$
DECLARE
    status_record RECORD;
    total_tables INTEGER := 0;
    optimal_tables INTEGER := 0;
BEGIN
    RAISE NOTICE 'Timestamp Management Migration Complete';
    RAISE NOTICE '=====================================';
    
    FOR status_record IN 
        SELECT table_name, status FROM timestamp_management_status ORDER BY table_name
    LOOP
        total_tables := total_tables + 1;
        IF status_record.status = 'OPTIMAL' THEN
            optimal_tables := optimal_tables + 1;
        END IF;
        
        RAISE NOTICE 'Table: % - Status: %', status_record.table_name, status_record.status;
    END LOOP;
    
    RAISE NOTICE '=====================================';
    RAISE NOTICE 'Summary: %/% tables have optimal timestamp management', optimal_tables, total_tables;
    RAISE NOTICE 'Run "SELECT * FROM timestamp_management_status;" to verify configuration';
END $$;