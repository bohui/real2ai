#!/usr/bin/env python3
"""
Test script to verify that the updated context with 'state' and 'user_experience' keys works correctly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.prompts import PromptContext, ContextType
from app.core.prompts.fragment_manager import FragmentManager


async def test_updated_context():
    """Test that the updated context works correctly with fragments"""

    print("🧪 TESTING UPDATED CONTEXT WITH FRAGMENTS")
    print("=" * 50)

    # Initialize fragment manager
    fragments_dir = backend_dir / "app" / "prompts" / "fragments"
    print(f"📁 Fragments directory: {fragments_dir}")

    if not fragments_dir.exists():
        print("❌ Fragments directory does not exist!")
        return

    fragment_manager = FragmentManager(fragments_dir)

    # Create test context with the UPDATED keys (state, user_experience)
    test_context = PromptContext(
        context_type=ContextType.EXTRACTION,
        variables={
            "contract_text": "test contract",
            "state": "NSW",  # ✅ Now using 'state' instead of 'australian_state'
            "analysis_type": "contract_terms_extraction",
            "extracted_text": "test contract",
            "document_metadata": {},
            "extraction_type": "contract_terms",
            "contract_type": "purchase_agreement",
            "user_type": "buyer",
            "user_experience": "intermediate",  # ✅ Now using 'user_experience' instead of 'user_experience_level'
            "extraction_timestamp": "2025-08-22T00:49:21.336383+00:00",
            "transaction_value": None,
            "condition": None,
            "specific_concerns": None,
        },
    )

    print(f"\n🔧 Test context with UPDATED keys:")
    print(f"  state: {test_context.variables.get('state')}")
    print(f"  user_experience: {test_context.variables.get('user_experience')}")

    # Test fragment composition
    print("\n🧩 TESTING FRAGMENT COMPOSITION WITH UPDATED CONTEXT")
    print("-" * 50)

    # Test compose_fragments method
    runtime_context = test_context.to_dict()
    fragment_vars = fragment_manager.compose_fragments(runtime_context)

    print(f"\n📊 Fragment variables result:")
    for group, content in fragment_vars.items():
        content_length = len(content) if content else 0
        print(f"  {group}: {content_length} chars")
        if content:
            print(f"    Preview: {content[:100]}...")

    # Test compose_with_folder_fragments method
    print("\n🔧 TESTING COMPOSE_WITH_FOLDER_FRAGMENTS")
    print("-" * 40)

    # Load the base template
    base_template = """## State-Specific Legal Requirements

{{ state_requirements }}

## Consumer Protection Framework

{{ consumer_protection }}

## Contract Type Specific Analysis

{{ contract_types }}"""

    composed_result = fragment_manager.compose_with_folder_fragments(
        base_template=base_template, context=test_context
    )

    print(f"\n📝 Composed result:")
    print(composed_result)

    # Check if the key sections are populated
    if "NSW" in composed_result:
        print("✅ NSW state-specific content found")
    else:
        print("❌ NSW state-specific content missing")

    if "Consumer Protection" in composed_result:
        print("✅ Consumer protection content found")
    else:
        print("❌ Consumer protection content missing")

    if "Purchase Agreement" in composed_result:
        print("✅ Contract type content found")
    else:
        print("❌ Contract type content missing")


if __name__ == "__main__":
    asyncio.run(test_updated_context())
