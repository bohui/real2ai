#!/usr/bin/env python3
"""
Quick test script to verify the retry mechanism fix.
Run this to validate that the retry_contract_analysis function properly clears all result fields.
"""

import asyncio
import asyncpg
from app.core.config import get_settings


async def test_retry_mechanism():
    """Test that retry_contract_analysis properly resets analysis results."""
    
    settings = get_settings()
    
    # Connect to the database
    conn = await asyncpg.connect(
        host="localhost",
        port=54322,
        database="postgres",
        user="postgres",
        password="postgres"
    )
    
    try:
        print("🧪 Testing retry mechanism fix...")
        
        # Create a test content hash
        test_hash = "test_hash_12345"
        test_user_id = "00000000-0000-0000-0000-000000000000"
        
        # Insert a completed analysis with all fields populated
        await conn.execute("""
            INSERT INTO analyses (
                id, content_hash, status, analysis_result, 
                executive_summary, risk_assessment, compliance_check,
                recommendations, risk_score, overall_risk_score,
                processing_time, processing_completed_at
            ) VALUES (
                gen_random_uuid(), $1, 'completed', 
                '{"test": "data"}', '{"summary": "test"}', '{"risk": "low"}',
                '{"compliance": "good"}', '["recommendation1"]', 0.2, 0.2,
                120, NOW()
            ) ON CONFLICT (content_hash) DO UPDATE SET
                status = EXCLUDED.status,
                analysis_result = EXCLUDED.analysis_result,
                executive_summary = EXCLUDED.executive_summary,
                risk_assessment = EXCLUDED.risk_assessment,
                compliance_check = EXCLUDED.compliance_check,
                recommendations = EXCLUDED.recommendations,
                risk_score = EXCLUDED.risk_score,
                overall_risk_score = EXCLUDED.overall_risk_score,
                processing_time = EXCLUDED.processing_time,
                processing_completed_at = EXCLUDED.processing_completed_at
        """, test_hash)
        
        print("✅ Created test analysis record with populated results")
        
        # Test 1: Try to retry a completed analysis (should not reset)
        print("\n🧪 Test 1: Attempting retry on completed analysis...")
        result = await conn.fetchval(
            "SELECT retry_contract_analysis($1, $2)", 
            test_hash, test_user_id
        )
        
        print(f"✅ retry_contract_analysis returned: {result}")
        
        # Verify the completed analysis was NOT reset
        completed_analysis = await conn.fetchrow("""
            SELECT status, analysis_result, executive_summary, risk_assessment,
                   compliance_check, recommendations, risk_score, overall_risk_score,
                   processing_time, processing_completed_at
            FROM analyses 
            WHERE content_hash = $1
        """, test_hash)
        
        print("🔍 Checking that completed analysis was NOT reset...")
        
        # Validate completed analysis remains unchanged
        completed_assertions = [
            (completed_analysis['status'] == 'completed', f"Status should remain 'completed', got: {completed_analysis['status']}"),
            (completed_analysis['analysis_result'] == {"test": "data"}, f"analysis_result should remain unchanged, got: {completed_analysis['analysis_result']}"),
            (completed_analysis['executive_summary'] == {"summary": "test"}, f"executive_summary should remain unchanged, got: {completed_analysis['executive_summary']}"),
            (completed_analysis['risk_score'] == 0.2, f"risk_score should remain unchanged, got: {completed_analysis['risk_score']}"),
        ]
        
        test1_passed = True
        for assertion, message in completed_assertions:
            if assertion:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
                test1_passed = False
        
        # Test 2: Create a failed analysis and verify retry works
        print("\n🧪 Test 2: Testing retry on failed analysis...")
        
        # Update to failed status
        await conn.execute("""
            UPDATE analyses 
            SET status = 'failed', error_message = 'Test failure'
            WHERE content_hash = $1
        """, test_hash)
        
        # Now retry the failed analysis
        result = await conn.fetchval(
            "SELECT retry_contract_analysis($1, $2)", 
            test_hash, test_user_id
        )
        
        print(f"✅ retry_contract_analysis on failed analysis returned: {result}")
        
        # Verify the failed analysis was properly reset
        reset_analysis = await conn.fetchrow("""
            SELECT status, analysis_result, executive_summary, risk_assessment,
                   compliance_check, recommendations, risk_score, overall_risk_score,
                   processing_time, processing_completed_at, error_message
            FROM analyses 
            WHERE content_hash = $1
        """, test_hash)
        
        print("🔍 Checking that failed analysis was properly reset...")
        
        # Validate all fields are properly reset for failed analysis
        assertions = [
            (reset_analysis['status'] == 'pending', f"Status should be 'pending', got: {reset_analysis['status']}"),
            (reset_analysis['analysis_result'] == {}, f"analysis_result should be empty, got: {reset_analysis['analysis_result']}"),
            (reset_analysis['executive_summary'] is None, f"executive_summary should be NULL, got: {reset_analysis['executive_summary']}"),
            (reset_analysis['risk_assessment'] is None, f"risk_assessment should be NULL, got: {reset_analysis['risk_assessment']}"),
            (reset_analysis['compliance_check'] is None, f"compliance_check should be NULL, got: {reset_analysis['compliance_check']}"),
            (reset_analysis['recommendations'] is None, f"recommendations should be NULL, got: {reset_analysis['recommendations']}"),
            (reset_analysis['risk_score'] == 0, f"risk_score should be 0, got: {reset_analysis['risk_score']}"),
            (reset_analysis['overall_risk_score'] == 0, f"overall_risk_score should be 0, got: {reset_analysis['overall_risk_score']}"),
            (reset_analysis['processing_time'] is None, f"processing_time should be NULL, got: {reset_analysis['processing_time']}"),
            (reset_analysis['processing_completed_at'] is None, f"processing_completed_at should be NULL, got: {reset_analysis['processing_completed_at']}"),
            (reset_analysis['error_message'] is None, f"error_message should be NULL, got: {reset_analysis['error_message']}")
        ]
        
        test2_passed = True
        for assertion, message in assertions:
            if assertion:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
                test2_passed = False
        
        # Cleanup test data
        await conn.execute("DELETE FROM analyses WHERE content_hash = $1", test_hash)
        print("🧹 Cleaned up test data")
        
        all_passed = test1_passed and test2_passed
        
        if all_passed:
            print("\n🎉 SUCCESS: Retry mechanism fix is working correctly!")
            print("   - ✅ Completed analyses are NOT retried (preserved)")
            print("   - ✅ Failed analyses are properly reset for retry")
            print("   - ✅ All analysis result fields are properly cleared on retry")
            print("   - ✅ Status transitions work correctly")
        else:
            print("\n❌ FAILURE: Some tests failed - review the fix")
            if not test1_passed:
                print("   - Test 1 FAILED: Completed analysis retry prevention")
            if not test2_passed:
                print("   - Test 2 FAILED: Failed analysis retry reset")
            
        return all_passed
        
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(test_retry_mechanism())
    exit(0 if success else 1)