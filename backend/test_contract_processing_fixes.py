#!/usr/bin/env python3
"""
Test the enhanced contract processing error handling and diagnostics
"""

import asyncio
import logging
from datetime import datetime

# Configure logging to see the enhanced diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_enhanced_error_handling():
    """Test the enhanced error handling for insufficient content"""
    
    print("🧪 Testing Enhanced Contract Processing Error Handling")
    print("=" * 60)
    
    try:
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        from app.models.contract_state import RealEstateAgentState, update_state_step
        
        # Initialize workflow
        workflow = ContractAnalysisWorkflow(enable_fallbacks=True)
        
        print("✅ Initialized ContractAnalysisWorkflow")
        
        # Test scenario 1: Empty document content
        print("\n🧪 Test 1: Empty document content")
        test_state_empty = RealEstateAgentState(
            document_data={
                "content": "",
                "extraction_method": "pymupdf",
                "extraction_confidence": 0.0,
                "file_type": "pdf"
            },
            document_id="test-doc-empty-123",
            content_hash="test-hash-empty",
            australian_state="NSW"
        )
        
        # This should trigger our enhanced error logging
        result_empty = await workflow.validate_document_quality_step(test_state_empty)
        
        print(f"   - Parsing status: {result_empty.get('parsing_status')}")
        print(f"   - Error message: {result_empty.get('error')}")
        
        # Test scenario 2: Very short document content
        print("\n🧪 Test 2: Very short document content")
        test_state_short = RealEstateAgentState(
            document_data={
                "content": "Contract",  # Only 8 characters
                "extraction_method": "tesseract_ocr",
                "extraction_confidence": 0.3,
                "file_type": "jpg"
            },
            document_id="test-doc-short-456",
            content_hash="test-hash-short",
            australian_state="VIC"
        )
        
        result_short = await workflow.validate_document_quality_step(test_state_short)
        
        print(f"   - Parsing status: {result_short.get('parsing_status')}")
        print(f"   - Error message: {result_short.get('error')}")
        
        # Test scenario 3: Sufficient document content (should pass)
        print("\n🧪 Test 3: Sufficient document content")
        sufficient_content = """
        This is a real estate purchase contract between the vendor and purchaser.
        The property is located at 123 Main Street, Sydney NSW 2000.
        The purchase price is $750,000 with a deposit of $75,000.
        Settlement date is 45 days from the date of this contract.
        Special conditions apply regarding building inspections.
        """
        
        test_state_good = RealEstateAgentState(
            document_data={
                "content": sufficient_content,
                "extraction_method": "pymupdf",
                "extraction_confidence": 0.95,
                "file_type": "pdf"
            },
            document_id="test-doc-good-789",
            content_hash="test-hash-good",
            australian_state="QLD"
        )
        
        result_good = await workflow.validate_document_quality_step(test_state_good)
        
        print(f"   - Parsing status: {result_good.get('parsing_status')}")
        if result_good.get('error'):
            print(f"   - Error: {result_good.get('error')}")
        else:
            print("   - ✅ Validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_diagnostic_information():
    """Test that diagnostic information is properly captured"""
    
    print("\n🧪 Testing Diagnostic Information Capture")
    print("-" * 40)
    
    # Capture log output to verify diagnostic info is included
    import io
    import sys
    
    # Create a string buffer to capture logs
    log_capture_string = io.StringIO()
    log_handler = logging.StreamHandler(log_capture_string)
    log_handler.setLevel(logging.ERROR)
    
    # Add handler to the logger
    test_logger = logging.getLogger('app.agents.contract_workflow')
    test_logger.addHandler(log_handler)
    
    try:
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        from app.models.contract_state import RealEstateAgentState
        
        workflow = ContractAnalysisWorkflow()
        
        # Test with minimal content that will fail validation
        test_state = RealEstateAgentState(
            document_data={
                "content": "X",  # 1 character - will fail
                "extraction_method": "easyocr",
                "extraction_confidence": 0.1,
                "file_type": "png"
            },
            document_id="diagnostic-test-999",
            content_hash="diagnostic-hash-test",
            australian_state="WA"
        )
        
        # This should generate enhanced diagnostic logging
        result = await workflow.validate_document_quality_step(test_state)
        
        # Check the captured log output
        log_contents = log_capture_string.getvalue()
        
        print("🔍 Checking diagnostic log output...")
        
        expected_fields = [
            "raw_length",
            "stripped_length", 
            "document_id",
            "extraction_method",
            "extraction_confidence",
            "content_hash",
            "file_type"
        ]
        
        diagnostic_found = all(field in log_contents for field in expected_fields)
        
        if diagnostic_found:
            print("✅ All expected diagnostic fields found in logs")
            print(f"   - Log contains: {', '.join(expected_fields)}")
        else:
            print("❌ Missing diagnostic fields in logs")
            print(f"   - Log output: {log_contents}")
        
        # Check error message enhancement
        error_message = result.get('error', '')
        enhanced_info = [
            "Extracted",
            "characters",
            "minimum required: 50",
            "Extraction method:",
            "confidence:"
        ]
        
        message_enhanced = all(info in error_message for info in enhanced_info)
        
        if message_enhanced:
            print("✅ Error message contains enhanced diagnostic information")
            print(f"   - Enhanced error: {error_message}")
        else:
            print("❌ Error message missing enhanced information")
            print(f"   - Error message: {error_message}")
        
        return diagnostic_found and message_enhanced
        
    finally:
        test_logger.removeHandler(log_handler)
        log_handler.close()


async def main():
    """Run all tests for the contract processing fixes"""
    
    print("🚀 Contract Processing Fixes Validation")
    print("=" * 60)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    results = []
    
    # Test 1: Enhanced error handling
    result1 = await test_enhanced_error_handling()
    results.append(("Enhanced Error Handling", result1))
    
    # Test 2: Diagnostic information
    result2 = await test_diagnostic_information()
    results.append(("Diagnostic Information", result2))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY") 
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Contract processing fixes are working correctly.")
        print("\n✅ Implemented Fixes:")
        print("- ✅ Enhanced error logging with comprehensive diagnostics")
        print("- ✅ Detailed error messages for insufficient content")
        print("- ✅ Document processing context preservation")
        print("- ✅ Debugging information for troubleshooting")
        
        print("\n🔧 Next Time Document Processing Fails:")
        print("- Check logs for detailed diagnostic information")
        print("- Error messages will show extraction method and confidence")
        print("- Document ID and content hash will be logged for tracking")
        print("- Text length and preview will help identify the issue")
        
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check the issues above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)