#!/usr/bin/env python3
"""
Test script for prompt: ocr/whole_document_extraction
Model: gemini-2.5-flash
Test type: template
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.prompts.manager import get_prompt_manager
from app.core.prompts.context import PromptContext, ContextType

async def test_prompt():
    """Test the specific prompt with the given model"""
    try:
        # Initialize prompt manager
        prompt_manager = get_prompt_manager()
        await prompt_manager.initialize()
        
        # Load test context
        with open("/Users/bohuihan/ai/real2ai/backend/test_results/test_context_ocr.json", "r") as f:
            context_data = json.load(f)
        
        # Create context
        context = PromptContext(
            context_type=ContextType.USER,
            variables=context_data
        )
        
        # Test prompt rendering
        if "template" == "composition":
            result = await prompt_manager.render_composed(
                composition_name="ocr/whole_document_extraction",
                context=context
            )
            print(f"✓ Composition rendered successfully")
            print(f"  System prompt length: {len(result.get('system_prompt', ''))}")
            print(f"  User prompt length: {len(result.get('user_prompt', ''))}")
        else:
            rendered = await prompt_manager.render(
                template_name="ocr/whole_document_extraction",
                context=context,
                model="gemini-2.5-flash"
            )
            print(f"✓ Prompt rendered successfully")
            print(f"  Length: {len(rendered)} characters")
            print(f"  Preview: {rendered[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing prompt: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_prompt())
    sys.exit(0 if success else 1)
