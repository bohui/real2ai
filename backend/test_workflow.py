"""
Test runner for LangGraph Contract Analysis Workflow
"""

import asyncio
import os
import json
from typing import Dict, Any

from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.models.contract_state import create_initial_state
from app.model.enums import AustralianState


async def test_workflow_execution():
    """Test the complete workflow execution"""
    
    # Initialize workflow
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    workflow = ContractAnalysisWorkflow(
        openai_api_key=api_key,
        model_name="gpt-4"
    )
    
    # Create test initial state
    initial_state = create_initial_state(
        user_id="test_user_123",
        australian_state=AustralianState.VIC,
        user_type="buyer"
    )
    
    # Add test document data
    initial_state["document_data"] = {
        "content": """
        SALE OF LAND CONTRACT
        
        VENDOR: John Smith and Mary Smith
        PURCHASER: Jane Doe
        
        PROPERTY: 123 Collins Street, Melbourne VIC 3000
        
        PURCHASE PRICE: $850,000
        DEPOSIT: $85,000 (10%)
        SETTLEMENT DATE: 45 days from exchange
        
        COOLING OFF PERIOD: 3 business days
        
        SPECIAL CONDITIONS:
        1. Subject to finance approval within 21 days
        2. Subject to satisfactory building and pest inspection
        3. Subject to strata search and review of strata documents
        
        This contract is governed by Victorian law.
        """,
        "file_path": "test_contract.pdf",
        "mime_type": "application/pdf"
    }
    
    # Add user preferences
    initial_state["user_preferences"] = {
        "is_first_home_buyer": True,
        "is_foreign_buyer": False
    }
    
    print("Starting workflow execution test...")
    print(f"Initial state created for user: {initial_state['user_id']}")
    print(f"Session ID: {initial_state['session_id']}")
    print(f"Australian State: {initial_state['australian_state']}")
    
    try:
        # Execute workflow
        final_state = await workflow.analyze_contract(initial_state)
        
        # Print results
        print("\\n" + "="*50)
        print("WORKFLOW EXECUTION RESULTS")
        print("="*50)
        
        print(f"Final step: {final_state.get('current_step', 'unknown')}")
        print(f"Processing time: {final_state.get('processing_time', 0):.2f} seconds")
        print(f"Overall confidence: {final_state.get('analysis_results', {}).get('overall_confidence', 0):.2f}")
        
        # Progress information
        progress = final_state.get('progress', {})
        print(f"Progress: {progress.get('percentage', 0)}% ({progress.get('current_step', 0)}/{progress.get('total_steps', 0)} steps)")
        
        # Confidence breakdown
        confidence_scores = final_state.get('confidence_scores', {})
        print("\\nConfidence Scores:")
        for component, score in confidence_scores.items():
            print(f"  {component}: {score:.2f}")
        
        # Contract terms extracted
        contract_terms = final_state.get('contract_terms', {})
        print("\\nExtracted Contract Terms:")
        for term, value in contract_terms.items():
            print(f"  {term}: {value}")
        
        # Risk assessment
        risk_assessment = final_state.get('risk_assessment', {})
        if risk_assessment:
            print(f"\\nRisk Assessment:")
            print(f"  Overall Risk Score: {risk_assessment.get('overall_risk_score', 0)}/10")
            risk_factors = risk_assessment.get('risk_factors', [])
            print(f"  Risk Factors: {len(risk_factors)} identified")
            for i, factor in enumerate(risk_factors[:3]):  # Show top 3
                print(f"    {i+1}. {factor.get('factor', 'Unknown')} - {factor.get('severity', 'Unknown')}")
        
        # Compliance check
        compliance = final_state.get('compliance_check', {})
        if compliance:
            print(f"\\nCompliance Check:")
            print(f"  State Compliance: {'✓' if compliance.get('state_compliance', False) else '✗'}")
            print(f"  Compliance Issues: {len(compliance.get('compliance_issues', []))}")
            
            # Stamp duty
            stamp_duty = compliance.get('stamp_duty_calculation', {})
            if stamp_duty and not stamp_duty.get('error'):
                print(f"  Stamp Duty: ${stamp_duty.get('total_duty', 0):,.2f}")
        
        # Recommendations
        recommendations = final_state.get('final_recommendations', [])
        print(f"\\nRecommendations: {len(recommendations)} generated")
        for i, rec in enumerate(recommendations[:3]):  # Show top 3
            print(f"  {i+1}. [{rec.get('priority', 'medium').upper()}] {rec.get('recommendation', 'No recommendation')}")
        
        # Error state
        if final_state.get('error_state'):
            print(f"\\n⚠️  Error: {final_state['error_state']}")
        else:
            print("\\n✅ Workflow completed successfully!")
        
        return final_state
        
    except Exception as e:
        print(f"\\n❌ Workflow execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_workflow_components():
    """Test individual workflow components"""
    
    print("\\n" + "="*50)
    print("COMPONENT TESTING")
    print("="*50)
    
    # Test workflow creation
    try:
        workflow = ContractAnalysisWorkflow(
            openai_api_key="test-key",
            model_name="gpt-4"
        )
        print("✅ Workflow creation: SUCCESS")
    except Exception as e:
        print(f"❌ Workflow creation: FAILED - {str(e)}")
        return False
    
    # Test state creation
    try:
        initial_state = create_initial_state(
            user_id="test_user",
            australian_state=AustralianState.NSW,
            user_type="buyer"
        )
        print("✅ State creation: SUCCESS")
    except Exception as e:
        print(f"❌ State creation: FAILED - {str(e)}")
        return False
    
    # Test individual methods
    test_state = initial_state.copy()
    test_state["document_data"] = {"content": "test content"}
    
    try:
        validated_state = workflow.validate_input(test_state)
        if validated_state.get('current_step') == 'input_validated':
            print("✅ Input validation: SUCCESS")
        else:
            print(f"❌ Input validation: FAILED - {validated_state.get('error_state', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Input validation: FAILED - {str(e)}")
    
    return True


async def main():
    """Main test runner"""
    
    print("LangGraph Contract Analysis Workflow Test Suite")
    print("=" * 60)
    
    # Test components first
    if not test_workflow_components():
        print("\\n❌ Component tests failed. Skipping workflow execution test.")
        return
    
    # Test full workflow execution
    await test_workflow_execution()
    
    print("\\n" + "="*60)
    print("Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())