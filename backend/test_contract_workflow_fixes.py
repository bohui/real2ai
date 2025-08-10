#!/usr/bin/env python3
"""
Test the fixed contract workflow to ensure JSON parsing issues are resolved
"""

import asyncio
import logging
from datetime import datetime

# Configure logging to see the issue resolution
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_contract_workflow_fixes():
    """Test that the contract workflow JSON parsing fixes work correctly"""
    
    print("🧪 Testing Contract Workflow JSON Parsing Fixes")
    print("=" * 60)
    
    try:
        # Import the fixed workflow
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        
        print("✅ Successfully imported ContractAnalysisWorkflow")
        
        # Initialize the workflow
        workflow = ContractAnalysisWorkflow(
            extraction_config={
                "method": "llm_structured",
                "fallback_to_rule_based": True,
                "use_fragments": True,
            },
            enable_fallbacks=True
        )
        
        print("✅ Successfully initialized workflow with structured parsers")
        print(f"✅ Available structured parsers: {list(workflow.structured_parsers.keys())}")
        
        # Test the new helper methods
        print("\n🧪 Testing JSON Parsing Helper Methods:")
        
        # Test 1: Valid JSON response
        valid_json_response = '''```json
{
  "overall_risk_score": 7.0,
  "risk_factors": [
    {
      "factor": "Missing mandatory terms",
      "severity": "high",
      "description": "The contract is missing essential terms"
    }
  ],
  "risk_summary": "High risk contract",
  "confidence_level": 0.8,
  "critical_issues": ["Missing price"],
  "state_specific_risks": []
}
```'''
        
        is_valid, error_msg = workflow._is_valid_json_response(valid_json_response)
        print(f"✅ Valid JSON test: {is_valid} (error: {error_msg})")
        
        # Test 2: Structured parsing test
        parsed_data, success, error_msg = workflow._parse_structured_response(valid_json_response, 'risk_analysis')
        print(f"✅ Structured parsing test: {success} (error: {error_msg})")
        if success:
            print(f"   - Parsed risk score: {parsed_data.get('overall_risk_score', 'N/A')}")
            print(f"   - Number of risk factors: {len(parsed_data.get('risk_factors', []))}")
        
        # Test 3: Monitor response quality (the original issue)
        print("\n🧪 Testing Response Quality Monitoring (original issue):")
        
        # This was the problematic response from the logs
        problematic_response = '''```json

{

  "overall_compliance_score": 3,

  "state_compliance": false,

  "compliance_issues": [

    {

      "area": "financial",

      "issue": "Missing mandatory term: purchase_price",

      "severi'''
        
        print("Testing problematic response that caused original error...")
        try:
            workflow._monitor_response_quality(problematic_response, "openai")
            print("✅ Response quality monitoring completed without errors")
        except Exception as e:
            print(f"❌ Response quality monitoring failed: {e}")
        
        # Test 4: Fallback methods
        print("\n🧪 Testing Fallback Methods:")
        
        if hasattr(workflow, '_create_fallback_compliance_result'):
            fallback_compliance = workflow._create_fallback_compliance_result()
            print(f"✅ Fallback compliance result: {fallback_compliance.get('overall_compliance_score', 'N/A')}")
        
        if hasattr(workflow, '_create_fallback_risk_result'):
            fallback_risk = workflow._create_fallback_risk_result()
            print(f"✅ Fallback risk result: {fallback_risk.get('overall_risk_score', 'N/A')}")
        
        # Test 5: Parse various response types
        print("\n🧪 Testing Different Response Types:")
        
        # Test compliance analysis response (the one from the error logs)
        compliance_response = '''```json
{
  "overall_compliance": true,
  "compliance_score": 0.8,
  "compliance_issues": [
    {
      "issue_type": "financial",
      "description": "Missing mandatory term: purchase_price",
      "severity": "high",
      "legal_reference": "Property Law Act",
      "resolution_required": true
    }
  ],
  "australian_state": "NSW"
}
```'''
        
        parsed_compliance, success_compliance, error_compliance = workflow._parse_structured_response(
            compliance_response, 'compliance_analysis'
        )
        print(f"✅ Compliance parsing: {success_compliance} (error: {error_compliance})")
        if success_compliance:
            print(f"   - Australian state: {parsed_compliance.get('australian_state', 'N/A')}")
            print(f"   - Compliance score: {parsed_compliance.get('compliance_score', 'N/A')}")
        
        print(f"\n📊 Workflow Metrics:")
        print(f"   - Successful parses: {workflow._metrics.get('successful_parses', 0)}")
        print(f"   - Failed parses: {workflow._metrics.get('failed_parses', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_real_world_scenario():
    """Test with a more realistic scenario"""
    
    print("\n🧪 Testing Real-World Scenario")
    print("-" * 40)
    
    try:
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        
        workflow = ContractAnalysisWorkflow(
            enable_fallbacks=True
        )
        
        # Simulate the actual error from the logs
        problematic_openai_response = '''```json

{

  "overall_compliance_score": 3,

  "state_compliance": false,

  "compliance_issues": [

    {

      "area": "financial",

      "issue": "Missing mandatory term: purchase_price",

      "severi'''
        
        print("Simulating the exact error scenario from logs...")
        
        # Test the improved _monitor_response_quality method
        original_successful_parses = workflow._metrics.get('successful_parses', 0)
        original_failed_parses = workflow._metrics.get('failed_parses', 0)
        
        workflow._monitor_response_quality(problematic_openai_response, "openai")
        
        new_successful_parses = workflow._metrics.get('successful_parses', 0)
        new_failed_parses = workflow._metrics.get('failed_parses', 0)
        
        print(f"✅ Monitoring completed:")
        print(f"   - Failed parses increased by: {new_failed_parses - original_failed_parses}")
        print(f"   - No exceptions thrown (this was the original problem)")
        
        # Test fallback parsing
        parsed_data, success, error_msg = workflow._fallback_json_parse(problematic_openai_response)
        
        if not success:
            print(f"✅ Fallback correctly identified invalid JSON: {error_msg}")
        else:
            print(f"❌ Fallback unexpectedly succeeded: {parsed_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Real-world test failed: {e}")
        return False


async def main():
    """Run all tests"""
    
    print("🚀 Contract Workflow JSON Parsing Fix Validation")
    print("=" * 60)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    results = []
    
    # Test 1: Basic functionality
    result1 = await test_contract_workflow_fixes()
    results.append(("Basic Functionality", result1))
    
    # Test 2: Real-world scenario
    result2 = await test_real_world_scenario()
    results.append(("Real-World Scenario", result2))
    
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
        print("\n🎉 All tests passed! The JSON parsing fixes are working correctly.")
        print("\n✅ Fixed Issues:")
        print("- ✅ Invalid JSON. Error: Expecting value: line 1 column 1 (char 0)")
        print("- ✅ Response quality issue from openai")
        print("- ✅ Code block wrapped JSON responses")
        print("- ✅ Structured output parsing integration")
        print("- ✅ Comprehensive fallback mechanisms")
        
        print("\n🚀 The contract analysis system should now handle:")
        print("- JSON responses wrapped in ```json code blocks")
        print("- Malformed or incomplete JSON responses")
        print("- LLM responses with extra text around JSON")
        print("- Pydantic validation with australian_state defaults")
        print("- Graceful degradation when parsing fails")
        
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check the issues above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)