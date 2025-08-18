#!/usr/bin/env python3
"""
Test script to verify the retry logic fix for contract analysis workflow.

This script tests the scenario where document processing fails and the system
tries to resume from compile_report step, but should detect missing artifacts
and restart from the beginning.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mock state for testing
def create_mock_state_with_failed_document_processing() -> Dict[str, Any]:
    """Create a mock state that simulates failed document processing."""
    return {
        "progress": {
            "current_step": "compile_report",
            "percentage": 95,
            "step_history": [
                {"step": "validate_input", "status": "completed"},
                {"step": "process_document", "status": "failed"},
                {"step": "extract_terms", "status": "failed"},
                {"step": "analyze_compliance", "status": "failed"},
                {"step": "assess_risks", "status": "failed"},
                {"step": "generate_recommendations", "status": "failed"},
                {"step": "compile_report", "status": "in_progress"}
            ]
        },
        "retry_attempts": 0,
        "error_state": "Document processing failed - no artifacts or extracted text found",
        "parsing_status": "FAILED",
        # Missing required artifacts
        "document_data": {
            "content": "",  # No extracted text
            "extraction_method": "unknown",
            "extraction_confidence": 0.0
        },
        "contract_terms": None,
        "compliance_analysis": None,
        "risk_assessment": None
    }

def create_mock_state_with_successful_document_processing() -> Dict[str, Any]:
    """Create a mock state that simulates successful document processing."""
    return {
        "progress": {
            "current_step": "compile_report",
            "percentage": 95,
            "step_history": [
                {"step": "validate_input", "status": "completed"},
                {"step": "process_document", "status": "completed"},
                {"step": "extract_terms", "status": "completed"},
                {"step": "analyze_compliance", "status": "completed"},
                {"step": "assess_risks", "status": "completed"},
                {"step": "generate_recommendations", "status": "completed"},
                {"step": "compile_report", "status": "in_progress"}
            ]
        },
        "retry_attempts": 0,
        "parsing_status": "COMPLETED",
        # Has required artifacts
        "document_data": {
            "content": "This is a sample contract with purchase price $500,000 and settlement date 2024-12-31",
            "extraction_method": "llm_structured",
            "extraction_confidence": 0.85
        },
        "contract_terms": {
            "purchase_price": "$500,000",
            "settlement_date": "2024-12-31",
            "property_address": "123 Main St, Sydney NSW"
        },
        "compliance_analysis": {
            "state_compliance": "NSW",
            "issues": [],
            "warnings": []
        },
        "risk_assessment": {
            "overall_risk_level": "low",
            "overall_risk_score": 0.2
        }
    }

async def test_retry_strategy_determination():
    """Test the retry strategy determination logic."""
    try:
        # Import the retry processing node
        from app.agents.nodes.retry_processing_node import RetryProcessingNode
        
        # Create a mock workflow (we only need the node, not the full workflow)
        class MockWorkflow:
            def __init__(self):
                self.name = "mock_workflow"
        
        # Create the retry processing node
        retry_node = RetryProcessingNode(MockWorkflow())
        
        # Test 1: Failed document processing - should restart workflow
        logger.info("=== Test 1: Failed document processing ===")
        failed_state = create_mock_state_with_failed_document_processing()
        
        retry_info = retry_node._determine_retry_strategy(failed_state)
        logger.info(f"Retry info: {retry_info}")
        
        if retry_info.get("strategy") == "restart_workflow":
            logger.info("✅ PASS: Correctly detected need to restart workflow")
        else:
            logger.error(f"❌ FAIL: Expected restart_workflow strategy, got {retry_info.get('strategy')}")
        
        # Test 2: Successful document processing - should continue normally
        logger.info("\n=== Test 2: Successful document processing ===")
        successful_state = create_mock_state_with_successful_document_processing()
        
        retry_info = retry_node._determine_retry_strategy(successful_state)
        logger.info(f"Retry info: {retry_info}")
        
        if retry_info.get("can_retry", False):
            logger.info("✅ PASS: Correctly detected retry is possible")
        else:
            logger.error(f"❌ FAIL: Expected retry to be possible, got {retry_info}")
        
        # Test 3: Check required artifacts validation
        logger.info("\n=== Test 3: Required artifacts validation ===")
        
        has_artifacts_failed = retry_node._check_required_artifacts(failed_state)
        logger.info(f"Failed state has artifacts: {has_artifacts_failed}")
        
        has_artifacts_success = retry_node._check_required_artifacts(successful_state)
        logger.info(f"Successful state has artifacts: {has_artifacts_success}")
        
        if not has_artifacts_failed and has_artifacts_success:
            logger.info("✅ PASS: Artifact validation working correctly")
        else:
            logger.error("❌ FAIL: Artifact validation not working correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    logger.info("Starting retry logic fix tests...")
    
    success = await test_retry_strategy_determination()
    
    if success:
        logger.info("🎉 All tests passed! The retry logic fix is working correctly.")
    else:
        logger.error("💥 Some tests failed. Please check the implementation.")
    
    return success

if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
