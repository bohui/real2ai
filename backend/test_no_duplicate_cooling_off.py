#!/usr/bin/env python3
"""
Test script to verify that removing duplicate cooling_off_framework doesn't break composition
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


async def test_no_duplicate_cooling_off():
    """Test that removing duplicate cooling_off_framework doesn't break composition"""

    print("🧪 TESTING FRAGMENT COMPOSITION WITHOUT DUPLICATE COOLING-OFF")
    print("=" * 60)

    # Initialize fragment manager
    fragments_dir = backend_dir / "app" / "prompts" / "fragments"
    print(f"📁 Fragments directory: {fragments_dir}")

    if not fragments_dir.exists():
        print("❌ Fragments directory does not exist!")
        return

    fragment_manager = FragmentManager(fragments_dir)

    # Create test context
    test_context = PromptContext(
        context_type=ContextType.EXTRACTION,
        variables={
            "contract_text": "test contract",
            "state": "NSW",
            "analysis_type": "contract_terms_extraction",
            "extracted_text": "test contract",
            "document_metadata": {},
            "extraction_type": "contract_terms",
            "contract_type": "purchase_agreement",
            "user_type": "buyer",
            "user_experience": "intermediate",
            "extraction_timestamp": "2025-08-22T00:49:21.336383+00:00",
            "transaction_value": None,
            "condition": None,
            "specific_concerns": None,
        },
    )

    # Test fragment composition
    print("\n🧩 TESTING FRAGMENT COMPOSITION")
    print("-" * 30)

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

    # Check for duplicate cooling-off content
    cooling_off_count = composed_result.count("cooling-off")
    print(f"\n🔍 Cooling-off mentions count: {cooling_off_count}")

    if cooling_off_count > 0:
        print("✅ Cooling-off content still present (from state-specific fragments)")
    else:
        print("❌ No cooling-off content found")

    # Check if NSW-specific cooling-off content is still there
    if "NSW Standard Period: 5 business days" in composed_result:
        print("✅ NSW-specific cooling-off content found")
    else:
        print("❌ NSW-specific cooling-off content missing")

    # Check if consumer protection still has other content
    if "Unfair Contract Terms Protection" in composed_result:
        print("✅ Unfair terms protection content found")
    else:
        print("❌ Unfair terms protection content missing")

    if "Statutory Warranties" in composed_result:
        print("✅ Statutory warranties content found")
    else:
        print("❌ Statutory warranties content missing")


if __name__ == "__main__":
    asyncio.run(test_no_duplicate_cooling_off())
