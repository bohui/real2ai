"""
Test the improved client fallback after our fix.
"""

import asyncio
import logging
from app.agents.contract_workflow import ContractAnalysisWorkflow

async def test_fallback():
    # Create a basic workflow for testing
    workflow = ContractAnalysisWorkflow()
    await workflow.initialize()
    
    # Get the properly initialized node from workflow
    node = workflow.nodes['document_quality_validation']
    
    # Test with a simple prompt
    test_prompt = "Analyze the quality of this test document: 'This is a sample contract.'"
    
    print("Testing improved fallback mechanism...")
    try:
        result = await node._generate_content_with_fallback(test_prompt)
        if result:
            print("✅ Content generation successful!")
            print(f"Response: {result[:100]}...")
        else:
            print("⚠️  No content generated, but fallback handled gracefully")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_fallback())
