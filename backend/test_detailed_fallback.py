"""
Test with detailed logging to see what's happening in the fallback.
"""

import asyncio
import logging
from app.agents.nodes.document_quality_validation_node import DocumentQualityValidationNode
from app.agents.contract_workflow import ContractAnalysisWorkflow

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

async def test_detailed_fallback():
    workflow = ContractAnalysisWorkflow()
    await workflow.initialize()
    
    # Get the properly initialized node from workflow
    node = workflow.nodes['document_quality_validation']
    
    # Test with a simple prompt
    test_prompt = "Analyze the quality of this test document: 'This is a sample contract.'"
    
    print("Testing with verbose logging...")
    print(f"OpenAI client available: {node.openai_client is not None}")
    print(f"Gemini client available: {node.gemini_client is not None}")
    
    try:
        # Test OpenAI client directly
        if node.openai_client:
            print("Testing OpenAI client directly...")
            try:
                openai_result = await node.openai_client.generate_content(test_prompt)
                print(f"OpenAI result: {openai_result[:100] if openai_result else 'None'}...")
            except Exception as e:
                print(f"OpenAI direct test failed: {e}")
        
        # Test Gemini client directly
        if node.gemini_client:
            print("Testing Gemini client directly...")
            try:
                gemini_result = await node.gemini_client.generate_content(test_prompt)
                print(f"Gemini result: {gemini_result[:100] if gemini_result else 'None'}...")
            except Exception as e:
                print(f"Gemini direct test failed: {e}")
        
        # Test fallback method
        print("Testing fallback method...")
        result = await node._generate_content_with_fallback(test_prompt)
        if result:
            print("✅ Fallback successful!")
            print(f"Response: {result[:100]}...")
        else:
            print("⚠️  Fallback returned None")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_detailed_fallback())
