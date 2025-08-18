#!/usr/bin/env python3
"""
Test script to verify that the prompt composition fix works correctly.
This script tests the structure_analysis_only composition that was failing.
"""

import asyncio
import sys
import os
import yaml
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


async def test_composition_configuration():
    """Test if the composition configuration files are valid after the fix"""

    print("🧪 Testing composition configuration files...")

    try:
        # Check the composition rules file
        composition_file = (
            backend_dir / "app" / "prompts" / "config" / "composition_rules.yaml"
        )
        if not composition_file.exists():
            print(f"✗ Composition rules file not found: {composition_file}")
            return False

        print(f"✓ Found composition rules file: {composition_file}")

        # Load and parse the composition rules
        with open(composition_file, "r", encoding="utf-8") as f:
            composition_data = yaml.safe_load(f)

        print("✓ Successfully parsed composition rules YAML")

        # Check the specific composition that was failing
        compositions = composition_data.get("compositions", {})
        structure_analysis = compositions.get("structure_analysis_only")

        if not structure_analysis:
            print("✗ structure_analysis_only composition not found")
            return False

        print("✓ Found structure_analysis_only composition")
        print(f"  Description: {structure_analysis.get('description', 'N/A')}")

        # Check system prompts
        system_prompts = structure_analysis.get("system_prompts", [])
        if not system_prompts:
            print("✗ No system prompts defined")
            return False

        print(f"✓ Found {len(system_prompts)} system prompts")

        # Check each system prompt
        for i, prompt in enumerate(system_prompts):
            prompt_name = prompt.get("name")
            prompt_path = prompt.get("path")

            if not prompt_name:
                print(f"✗ System prompt {i} missing name")
                return False

            if not prompt_path:
                print(f"✗ System prompt {i} missing path")
                return False

            print(f"  ✓ System prompt {i}: {prompt_name} -> {prompt_path}")

            # Check if the prompt file exists
            prompt_file = backend_dir / "app" / "prompts" / prompt_path
            if not prompt_file.exists():
                print(f"    ⚠ Prompt file not found: {prompt_file}")
            else:
                print(f"    ✓ Prompt file exists: {prompt_file}")

        # Check user prompts
        user_prompts = structure_analysis.get("user_prompts", [])
        if not user_prompts:
            print("✗ No user prompts defined")
            return False

        print(f"✓ Found {len(user_prompts)} user prompts: {user_prompts}")

        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_prompt_registry():
    """Test if the prompt registry is valid"""

    print("\n🧪 Testing prompt registry...")

    try:
        # Check the prompt registry file
        registry_file = (
            backend_dir / "app" / "prompts" / "config" / "prompt_registry.yaml"
        )
        if not registry_file.exists():
            print(f"✗ Prompt registry file not found: {registry_file}")
            return False

        print(f"✓ Found prompt registry file: {registry_file}")

        # Load and parse the prompt registry
        with open(registry_file, "r", encoding="utf-8") as f:
            registry_data = yaml.safe_load(f)

        print("✓ Successfully parsed prompt registry YAML")

        # Check system prompts
        registry = registry_data.get("registry", {})
        system_prompts = registry.get("system_prompts", {})

        if not system_prompts:
            print("✗ No system prompts in registry")
            return False

        print(f"✓ Found {len(system_prompts)} system prompts in registry")

        # Check for the australian_legal prompt
        if "australian_legal" not in system_prompts:
            print("✗ australian_legal prompt not found in registry")
            return False

        australian_legal = system_prompts["australian_legal"]
        print("✓ Found australian_legal prompt in registry")
        print(f"  Path: {australian_legal.get('path', 'N/A')}")
        print(f"  Category: {australian_legal.get('category', 'N/A')}")
        print(f"  Priority: {australian_legal.get('priority', 'N/A')}")

        # Check if the prompt file exists
        prompt_path = australian_legal.get("path")
        if prompt_path:
            prompt_file = backend_dir / "app" / "prompts" / prompt_path
            if not prompt_file.exists():
                print(f"    ⚠ Prompt file not found: {prompt_file}")
            else:
                print(f"    ✓ Prompt file exists: {prompt_file}")

        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_composition_consistency():
    """Test if all compositions reference valid prompt names"""

    print("\n🧪 Testing composition consistency...")

    try:
        # Load composition rules
        composition_file = (
            backend_dir / "app" / "prompts" / "config" / "composition_rules.yaml"
        )
        with open(composition_file, "r", encoding="utf-8") as f:
            composition_data = yaml.safe_load(f)

        # Load prompt registry
        registry_file = (
            backend_dir / "app" / "prompts" / "config" / "prompt_registry.yaml"
        )
        with open(registry_file, "r", encoding="utf-8") as f:
            registry_data = yaml.safe_load(f)

        compositions = composition_data.get("compositions", {})
        registry = registry_data.get("registry", {})
        system_prompts = registry.get("system_prompts", {})

        print(
            f"✓ Loaded {len(compositions)} compositions and {len(system_prompts)} system prompts"
        )

        # Check each composition
        errors = []
        for comp_name, comp_data in compositions.items():
            system_prompts_list = comp_data.get("system_prompts", [])

            for prompt in system_prompts_list:
                prompt_name = prompt.get("name")
                if prompt_name and prompt_name not in system_prompts:
                    error_msg = f"Composition '{comp_name}' references unknown system prompt: {prompt_name}"
                    errors.append(error_msg)
                    print(f"✗ {error_msg}")
                elif prompt_name:
                    print(
                        f"✓ Composition '{comp_name}' -> system prompt '{prompt_name}' (valid)"
                    )

        if errors:
            print(f"\n❌ Found {len(errors)} composition errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("\n🎉 All compositions reference valid system prompts!")
            return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting prompt composition fix verification...\n")

    # Test configuration files
    success1 = await test_composition_configuration()

    # Test prompt registry
    success2 = await test_prompt_registry()

    # Test composition consistency
    success3 = await test_composition_consistency()

    if success1 and success2 and success3:
        print("\n🎉 All tests passed! The prompt composition fix is working correctly.")
        print("\n📋 Summary of fixes applied:")
        print(
            "  ✓ Changed 'australian_context' to 'australian_legal' in composition rules"
        )
        print("  ✓ Updated state-specific overrides to use 'australian_legal'")
        print("  ✓ All compositions now reference valid system prompt names")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
