"""Test script for the fragment-based prompt system"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from .manager import PromptManager, PromptManagerConfig
from .context import PromptContext, ContextType


async def test_fragment_system():
    """Test the fragment-based prompt composition"""

    # Configure the prompt manager
    prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
    config = PromptManagerConfig(
        templates_dir=prompts_dir,
        config_dir=prompts_dir / "config",
        enable_composition=True,
        validation_enabled=False,  # Disable for testing
    )

    try:
        manager = PromptManager(config)
        print("✅ PromptManager initialized successfully")

        # Test context
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "contract_text": "Sample NSW property purchase agreement...",
                "australian_state": "NSW",
                "analysis_type": "comprehensive",
                "user_experience_level": "novice",
                "transaction_value": 850000,
                "contract_type": "PURCHASE_AGREEMENT",
            },
        )

        # Test composition list
        compositions = manager.list_compositions()
        print(f"✅ Found {len(compositions)} compositions")
        for comp in compositions:
            print(f"  - {comp['name']}: {comp['description']}")

        # Test fragment manager directly
        if manager.composer and manager.composer.fragment_manager:
            fragments = manager.composer.fragment_manager.list_available_fragments()
            print(f"✅ Found {len(fragments)} fragments")
            for fragment in fragments[:3]:  # Show first 3
                print(f"  - {fragment['name']} ({fragment['category']})")

        # Test composition validation
        for comp in compositions:
            validation = manager.validate_composition(comp["name"])
            status = "✅ VALID" if validation["valid"] else "❌ INVALID"
            print(f"{comp['name']}: {status}")
            if not validation["valid"]:
                print(f"  Issues: {validation.get('issues', [])}")

        # Test orchestration validation
        if manager.composer and manager.composer.fragment_manager:
            orchestration_result = (
                manager.composer.fragment_manager.validate_orchestration(
                    "contract_analysis"
                )
            )
            status = "✅ VALID" if orchestration_result["valid"] else "❌ INVALID"
            print(f"Orchestration contract_analysis: {status}")
            if not orchestration_result["valid"]:
                print(f"  Issues: {orchestration_result.get('issues', [])}")

        print("\n" + "=" * 50)
        print("Fragment System Test Complete")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fragment_system())
