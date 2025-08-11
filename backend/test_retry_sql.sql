-- Test script to verify retry_contract_analysis function behavior
-- Run this with: psql -h localhost -p 54322 -U postgres -d postgres -f test_retry_sql.sql

\echo '🧪 Testing retry mechanism SQL function...'

-- Setup test data
INSERT INTO analyses (
    id, content_hash, status, result, 
    error_details, started_at, completed_at,
    user_id, agent_version
) VALUES (
    gen_random_uuid(), 'test_hash_12345', 'completed', 
    '{"test": "data", "executive_summary": {"summary": "test"}, "risk_assessment": {"risk": "low"}}'::jsonb, 
    NULL, NOW(), NOW(),
    '00000000-0000-0000-0000-000000000000'::uuid, '1.0'
) ON CONFLICT (content_hash, agent_version) DO UPDATE SET
    status = EXCLUDED.status,
    result = EXCLUDED.result,
    completed_at = EXCLUDED.completed_at;

\echo '✅ Created test analysis record with completed status'

-- Test 1: Try to retry completed analysis (should NOT reset)
\echo ''
\echo '🧪 Test 1: Attempting retry on completed analysis...'
SELECT retry_contract_analysis('test_hash_12345', '00000000-0000-0000-0000-000000000000') as retry_result;

-- Check that completed analysis was NOT modified
\echo '🔍 Checking that completed analysis was NOT reset:'
SELECT 
    status,
    (result->>'test') as test_data,
    (result->'executive_summary'->>'summary') as summary_data,
    result
FROM analyses 
WHERE content_hash = 'test_hash_12345';

-- Test 2: Update to failed and test retry
\echo ''
\echo '🧪 Test 2: Testing retry on failed analysis...'
UPDATE analyses 
SET status = 'failed', error_details = '{"error": "Test failure"}'::jsonb
WHERE content_hash = 'test_hash_12345';

-- Now retry the failed analysis
SELECT retry_contract_analysis('test_hash_12345', '00000000-0000-0000-0000-000000000000') as retry_result;

-- Check that failed analysis WAS reset
\echo '🔍 Checking that failed analysis was properly reset:'
SELECT 
    status,
    result,
    error_details
FROM analyses 
WHERE content_hash = 'test_hash_12345';

-- Cleanup
DELETE FROM analyses WHERE content_hash = 'test_hash_12345';
\echo ''
\echo '🧹 Cleaned up test data'
\echo '✅ Test completed!'