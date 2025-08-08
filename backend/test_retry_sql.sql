-- Test script to verify retry_contract_analysis function behavior
-- Run this with: psql -h localhost -p 54322 -U postgres -d postgres -f test_retry_sql.sql

\echo '🧪 Testing retry mechanism SQL function...'

-- Setup test data
INSERT INTO contract_analyses (
    id, content_hash, status, analysis_result, 
    executive_summary, risk_assessment, compliance_check,
    recommendations, risk_score, overall_risk_score,
    processing_time, processing_completed_at
) VALUES (
    gen_random_uuid(), 'test_hash_12345', 'completed', 
    '{"test": "data"}'::jsonb, '{"summary": "test"}'::jsonb, '{"risk": "low"}'::jsonb,
    '{"compliance": "good"}'::jsonb, '["recommendation1"]'::jsonb, 0.2, 0.2,
    120, NOW()
) ON CONFLICT (content_hash) DO UPDATE SET
    status = EXCLUDED.status,
    analysis_result = EXCLUDED.analysis_result,
    executive_summary = EXCLUDED.executive_summary;

\echo '✅ Created test analysis record with completed status'

-- Test 1: Try to retry completed analysis (should NOT reset)
\echo ''
\echo '🧪 Test 1: Attempting retry on completed analysis...'
SELECT retry_contract_analysis('test_hash_12345', '00000000-0000-0000-0000-000000000000') as retry_result;

-- Check that completed analysis was NOT modified
\echo '🔍 Checking that completed analysis was NOT reset:'
SELECT 
    status,
    (analysis_result->>'test') as test_data,
    (executive_summary->>'summary') as summary_data,
    risk_score
FROM contract_analyses 
WHERE content_hash = 'test_hash_12345';

-- Test 2: Update to failed and test retry
\echo ''
\echo '🧪 Test 2: Testing retry on failed analysis...'
UPDATE contract_analyses 
SET status = 'failed', error_message = 'Test failure'
WHERE content_hash = 'test_hash_12345';

-- Now retry the failed analysis
SELECT retry_contract_analysis('test_hash_12345', '00000000-0000-0000-0000-000000000000') as retry_result;

-- Check that failed analysis WAS reset
\echo '🔍 Checking that failed analysis was properly reset:'
SELECT 
    status,
    analysis_result,
    executive_summary,
    risk_score,
    error_message
FROM contract_analyses 
WHERE content_hash = 'test_hash_12345';

-- Cleanup
DELETE FROM contract_analyses WHERE content_hash = 'test_hash_12345';
\echo ''
\echo '🧹 Cleaned up test data'
\echo '✅ Test completed!'