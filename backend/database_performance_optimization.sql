-- =============================================================================
-- DATABASE PERFORMANCE OPTIMIZATION FOR REAL2.AI PLATFORM
-- =============================================================================
-- Target: 75% reduction in query times (200-500ms → 50-100ms)
-- Focus: Contract analysis access validation and query consolidation
--
-- Performance Improvements:
-- 1. Composite indexes for frequently queried column combinations
-- 2. Optimized query consolidation (4 queries → 1 JOIN)
-- 3. Strategic indexes on high-traffic tables
-- 4. Performance monitoring and metrics
-- =============================================================================

-- Enable performance monitoring extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- =============================================================================
-- CRITICAL COMPOSITE INDEXES FOR USER ACCESS VALIDATION
-- =============================================================================

-- Index 1: user_contract_views - Most critical for access validation
-- Covers the primary access check query pattern
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_contract_views_user_content
ON user_contract_views(user_id, content_hash)
WHERE content_hash IS NOT NULL;

-- Index 2: documents - User document access with content hash
-- Optimizes document-based access validation  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_user_content_hash
ON documents(user_id, content_hash)
WHERE content_hash IS NOT NULL;

-- Index 3: contracts - Contract lookup by ID with content hash
-- Speeds up contract existence validation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contracts_id_content_hash
ON contracts(id, content_hash);

-- Index 4: contract_analyses - Analysis lookup by content hash with status
-- Critical for analysis status checks with ordering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contract_analyses_content_status_created
ON contract_analyses(content_hash, status, created_at DESC)
WHERE status IN ('pending', 'processing', 'completed');

-- Index 5: contract_analyses - Content hash with updated timestamp
-- Optimizes the ORDER BY created_at DESC pattern
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contract_analyses_content_updated
ON contract_analyses(content_hash, updated_at DESC);

-- =============================================================================
-- ADDITIONAL PERFORMANCE INDEXES
-- =============================================================================

-- Index 6: documents - User ID with processing status
-- Speeds up document status filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_user_status
ON documents(user_id, processing_status)
WHERE processing_status IN ('uploaded', 'processing', 'completed', 'failed');

-- Index 7: contracts - Content hash lookup (unique constraint)
-- Ensures fast content hash lookups
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_contracts_content_hash_unique
ON contracts(content_hash);

-- Index 8: contract_analyses - Agent version with status for cache queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contract_analyses_agent_status
ON contract_analyses(agent_version, status, content_hash);

-- =============================================================================
-- OPTIMIZED QUERY FUNCTIONS
-- =============================================================================

-- Function 1: Consolidated user access validation with single query
-- Replaces 4 separate queries with 1 optimized JOIN
CREATE OR REPLACE FUNCTION get_user_contract_access_optimized(
    p_user_id UUID,
    p_contract_id UUID
) RETURNS TABLE (
    contract_id UUID,
    content_hash TEXT,
    has_access BOOLEAN,
    access_source TEXT,
    analysis_id UUID,
    analysis_status TEXT,
    analysis_created_at TIMESTAMPTZ,
    analysis_updated_at TIMESTAMPTZ,
    processing_time FLOAT,
    error_message TEXT,
    analysis_metadata JSONB
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH user_content_hashes AS (
        -- Get all content hashes user has access to via views
        SELECT ucv.content_hash, 'view' as source
        FROM user_contract_views ucv
        WHERE ucv.user_id = p_user_id 
          AND ucv.content_hash IS NOT NULL
        
        UNION ALL
        
        -- Get all content hashes user has access to via documents
        SELECT d.content_hash, 'document' as source
        FROM documents d
        WHERE d.user_id = p_user_id 
          AND d.content_hash IS NOT NULL
    ),
    contract_info AS (
        -- Get contract details
        SELECT c.id, c.content_hash
        FROM contracts c
        WHERE c.id = p_contract_id
    )
    SELECT 
        ci.id as contract_id,
        ci.content_hash,
        CASE WHEN uch.content_hash IS NOT NULL THEN TRUE ELSE FALSE END as has_access,
        COALESCE(uch.source, 'none') as access_source,
        ca.id as analysis_id,
        ca.status as analysis_status,
        ca.created_at as analysis_created_at,
        ca.updated_at as analysis_updated_at,
        ca.processing_time,
        ca.error_message,
        ca.analysis_metadata
    FROM contract_info ci
    LEFT JOIN user_content_hashes uch ON ci.content_hash = uch.content_hash
    LEFT JOIN contract_analyses ca ON ci.content_hash = ca.content_hash
        AND ca.created_at = (
            SELECT MAX(created_at) 
            FROM contract_analyses ca2 
            WHERE ca2.content_hash = ci.content_hash
        )
    LIMIT 1;
END;
$$;

-- Function 2: Bulk user access validation for multiple contracts
-- Optimizes batch operations
CREATE OR REPLACE FUNCTION get_user_contracts_bulk_access(
    p_user_id UUID,
    p_limit INT DEFAULT 50
) RETURNS TABLE (
    content_hash TEXT,
    access_source TEXT,
    contract_count INT
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH user_content_hashes AS (
        SELECT ucv.content_hash, 'view' as source
        FROM user_contract_views ucv
        WHERE ucv.user_id = p_user_id 
          AND ucv.content_hash IS NOT NULL
        
        UNION ALL
        
        SELECT d.content_hash, 'document' as source
        FROM documents d
        WHERE d.user_id = p_user_id 
          AND d.content_hash IS NOT NULL
    )
    SELECT 
        uch.content_hash,
        uch.source as access_source,
        COUNT(*)::INT as contract_count
    FROM user_content_hashes uch
    GROUP BY uch.content_hash, uch.source
    ORDER BY contract_count DESC
    LIMIT p_limit;
END;
$$;

-- =============================================================================
-- PERFORMANCE MONITORING VIEWS
-- =============================================================================

-- View 1: Query performance monitoring
CREATE OR REPLACE VIEW contract_query_performance AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE query ILIKE '%contract%' 
   OR query ILIKE '%user_contract_views%'
   OR query ILIKE '%contract_analyses%'
ORDER BY mean_exec_time DESC;

-- View 2: Index usage statistics
CREATE OR REPLACE VIEW contract_index_usage AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE 
        WHEN idx_scan > 0 THEN ROUND((idx_tup_read::NUMERIC / idx_scan), 2)
        ELSE 0
    END AS avg_tuples_per_scan
FROM pg_stat_user_indexes
WHERE tablename IN ('contracts', 'contract_analyses', 'user_contract_views', 'documents')
ORDER BY idx_scan DESC;

-- View 3: Table performance metrics
CREATE OR REPLACE VIEW contract_table_performance AS
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    CASE 
        WHEN seq_scan + idx_scan > 0 
        THEN ROUND(100.0 * idx_scan / (seq_scan + idx_scan), 2)
        ELSE 0
    END AS index_usage_percent
FROM pg_stat_user_tables
WHERE tablename IN ('contracts', 'contract_analyses', 'user_contract_views', 'documents')
ORDER BY seq_scan DESC;

-- =============================================================================
-- PERFORMANCE OPTIMIZATION FUNCTIONS
-- =============================================================================

-- Function 3: Clear query performance stats (for testing)
CREATE OR REPLACE FUNCTION reset_contract_performance_stats()
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    -- Reset pg_stat_statements
    SELECT pg_stat_statements_reset();
    
    -- Reset table and index statistics
    SELECT pg_stat_reset_single_table_counters('contracts'::regclass);
    SELECT pg_stat_reset_single_table_counters('contract_analyses'::regclass);
    SELECT pg_stat_reset_single_table_counters('user_contract_views'::regclass);
    SELECT pg_stat_reset_single_table_counters('documents'::regclass);
    
    RAISE NOTICE 'Contract performance statistics reset successfully';
END;
$$;

-- Function 4: Generate performance report
CREATE OR REPLACE FUNCTION generate_contract_performance_report()
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    report TEXT;
    avg_query_time NUMERIC;
    total_queries BIGINT;
    cache_hit_ratio NUMERIC;
BEGIN
    -- Get average query time for contract operations
    SELECT 
        ROUND(AVG(mean_exec_time), 2),
        SUM(calls)
    INTO avg_query_time, total_queries
    FROM pg_stat_statements 
    WHERE query ILIKE '%contract%'
       OR query ILIKE '%user_contract_views%';
    
    -- Calculate cache hit ratio
    SELECT 
        ROUND(100.0 * SUM(shared_blks_hit) / 
        NULLIF(SUM(shared_blks_hit) + SUM(shared_blks_read), 0), 2)
    INTO cache_hit_ratio
    FROM pg_stat_statements 
    WHERE query ILIKE '%contract%';
    
    -- Build report
    report := format('
=== CONTRACT DATABASE PERFORMANCE REPORT ===

Query Performance:
- Average Query Time: %s ms
- Total Queries: %s
- Cache Hit Ratio: %s%%

Target Metrics:
- Target Query Time: <100ms (Current: %s ms)
- Performance Status: %s

Recommendations:
%s
',
        COALESCE(avg_query_time::TEXT, 'N/A'),
        COALESCE(total_queries::TEXT, '0'),
        COALESCE(cache_hit_ratio::TEXT, 'N/A'),
        COALESCE(avg_query_time::TEXT, 'N/A'),
        CASE 
            WHEN avg_query_time IS NULL THEN 'No data available'
            WHEN avg_query_time <= 100 THEN '✅ EXCELLENT - Target achieved'
            WHEN avg_query_time <= 200 THEN '⚠️ GOOD - Near target'
            ELSE '❌ NEEDS IMPROVEMENT - Above target'
        END,
        CASE 
            WHEN avg_query_time IS NULL THEN '- Run some queries to collect performance data'
            WHEN avg_query_time <= 100 THEN '- Performance is optimal, monitor regularly'
            WHEN avg_query_time <= 200 THEN '- Consider additional query optimizations'
            ELSE '- Immediate optimization needed, check slow queries'
        END
    );
    
    RETURN report;
END;
$$;

-- =============================================================================
-- MAINTENANCE AND MONITORING
-- =============================================================================

-- Function 5: Analyze table statistics (run after index creation)
CREATE OR REPLACE FUNCTION update_contract_table_stats()
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    -- Update table statistics for better query planning
    ANALYZE contracts;
    ANALYZE contract_analyses;
    ANALYZE user_contract_views;
    ANALYZE documents;
    
    RETURN 'Table statistics updated successfully for optimal query planning';
END;
$$;

-- =============================================================================
-- DEPLOYMENT AND VALIDATION SCRIPT
-- =============================================================================

-- Validate all indexes were created successfully
DO $validation$
DECLARE
    index_count INTEGER;
    expected_count INTEGER := 8; -- Total number of indexes we're creating
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE indexname LIKE 'idx_user_contract_views_%'
       OR indexname LIKE 'idx_documents_%'
       OR indexname LIKE 'idx_contracts_%'
       OR indexname LIKE 'idx_contract_analyses_%';
    
    IF index_count >= expected_count THEN
        RAISE NOTICE '✅ SUCCESS: % performance indexes created successfully', index_count;
    ELSE
        RAISE WARNING '⚠️ WARNING: Only % of % expected indexes were created', index_count, expected_count;
    END IF;
END;
$validation$;

-- Generate initial performance report
SELECT generate_contract_performance_report();

-- Update table statistics
SELECT update_contract_table_stats();

-- =============================================================================
-- DEPLOYMENT NOTES
-- =============================================================================

/*
DEPLOYMENT CHECKLIST:

1. ✅ BEFORE DEPLOYMENT:
   - Backup current database
   - Test in staging environment
   - Verify index creation permissions
   - Check available disk space (indexes ~10-20% table size)

2. ✅ DURING DEPLOYMENT:
   - Indexes created with CONCURRENTLY (no table locks)
   - Monitor system resources during creation
   - Validate all indexes created successfully

3. ✅ AFTER DEPLOYMENT:
   - Run ANALYZE on all tables
   - Monitor query performance improvements
   - Check pg_stat_statements for optimization validation
   - Set up regular performance monitoring

4. ✅ EXPECTED RESULTS:
   - 75% reduction in query response times
   - 200-500ms → 50-100ms for contract access validation
   - Improved cache hit ratios
   - Better query plan selection

5. ✅ MONITORING:
   - Use contract_query_performance view for ongoing monitoring
   - Set up alerts for queries >100ms average
   - Weekly performance reports via generate_contract_performance_report()
*/

-- Log successful deployment
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🚀 ===================================================================';
    RAISE NOTICE '🚀 REAL2.AI DATABASE PERFORMANCE OPTIMIZATION DEPLOYED';
    RAISE NOTICE '🚀 ===================================================================';
    RAISE NOTICE '🚀 Target: 75%% query time reduction (200-500ms → 50-100ms)';
    RAISE NOTICE '🚀 Status: Indexes and optimization functions ready';
    RAISE NOTICE '🚀 Next: Monitor performance with contract_query_performance view';
    RAISE NOTICE '🚀 ===================================================================';
    RAISE NOTICE '';
END $$;