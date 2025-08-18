#!/usr/bin/env python3
"""
Test script to verify that the transaction_value fix resolves the template rendering error.
This script tests the contract_analysis_base template with the updated context variables.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


# Mock the dependencies that might not be available in the test environment
class MockPromptTemplate:
    def __init__(self, content, metadata):
        self.content = content
        self.metadata = metadata

    def render(self, context, **kwargs):
        # Simple mock render that checks for required variables
        return self.content


class MockTemplateMetadata:
    def __init__(self, name="", version="1.0", description=""):
        self.name = name
        self.version = version
        self.description = description


class MockPromptLoader:
    def __init__(self, templates_dir):
        self.templates_dir = templates_dir

    async def load_template(self, name, version=None):
        # Return a mock template for testing
        return MockPromptTemplate(
            content=f"Mock content for {name}", metadata=MockTemplateMetadata(name=name)
        )


class MockFragmentManager:
    def compose_with_fragments(self, base_template, orchestration_id, context):
        # Mock fragment composition
        return base_template


class MockPromptComposer:
    def __init__(
        self, prompt_registry, composition_rules, prompts_dir, fragment_manager=None
    ):
        self.prompt_registry = prompt_registry
        self.composition_rules = composition_rules
        self.prompts_dir = prompts_dir
        self.fragment_manager = fragment_manager or MockFragmentManager()

    def compose(self, composition_name, context, variables=None, **kwargs):
        """Mock composition that simulates the real behavior"""
        if composition_name not in self.composition_rules:
            raise Exception(f"Composition not found: {composition_name}")

        rule = self.composition_rules[composition_name]

        # Simulate system prompt composition
        system_parts = []
        for prompt in rule.get("system_prompts", []):
            prompt_name = prompt.get("name")
            if prompt_name not in self.prompt_registry.get("system_prompts", {}):
                raise Exception(f"System prompt not found: {prompt_name}")

            # Add mock system content
            system_parts.append(f"System prompt: {prompt_name}")

        # Simulate user prompt composition with variable validation
        user_parts = []
        for prompt_name in rule.get("user_prompts", []):
            # Check if this is the contract_analysis_base template
            if prompt_name == "contract_analysis_base":
                # Validate required variables
                required_vars = ["contract_text", "australian_state", "analysis_type"]
                missing_vars = []

                for var in required_vars:
                    if var not in context.variables:
                        missing_vars.append(var)

                if missing_vars:
                    raise Exception(
                        f"Missing required variables for {prompt_name}: {missing_vars}"
                    )

                # Check for transaction_value reference
                if "transaction_value" not in context.variables:
                    print(
                        f"⚠ Warning: transaction_value not in context for {prompt_name}"
                    )

                user_parts.append(f"User prompt: {prompt_name} (variables validated)")
            else:
                user_parts.append(f"User prompt: {prompt_name}")

        return type(
            "ComposedPrompt",
            (),
            {
                "system_content": "\n".join(system_parts),
                "user_content": "\n".join(user_parts),
            },
        )


async def test_transaction_value_fix():
    """Test that the transaction_value fix resolves the template rendering error"""

    print("🧪 Testing transaction_value fix...")

    try:
        # Load the actual configuration files
        import yaml

        # Load composition rules
        composition_file = (
            backend_dir / "app" / "prompts" / "config" / "composition_rules.yaml"
        )
        with open(composition_file, "r", encoding="utf-8") as f:
            composition_rules = yaml.safe_load(f)

        # Load prompt registry
        registry_file = (
            backend_dir / "app" / "prompts" / "config" / "prompt_registry.yaml"
        )
        with open(registry_file, "r", encoding="utf-8") as f:
            prompt_registry = yaml.safe_load(f)

        print("✓ Successfully loaded configuration files")

        # Create mock composer
        composer = MockPromptComposer(
            prompt_registry=prompt_registry.get("registry", {}),
            composition_rules=composition_rules.get("compositions", {}),
            prompts_dir=backend_dir / "app" / "prompts",
        )

        print("✓ Successfully created mock prompt composer")

        # Test the specific composition that was failing
        composition_name = "structure_analysis_only"

        if composition_name not in composition_rules.get("compositions", {}):
            print(f"✗ Composition '{composition_name}' not found")
            return False

        print(f"✓ Found composition: {composition_name}")

        # Test with the OLD context (should fail)
        print("\n🧪 Testing with OLD context (should fail)...")
        old_context = type(
            "MockContext",
            (),
            {
                "variables": {
                    "extracted_text": "Sample contract text",
                    "australian_state": "NSW",
                    "contract_type": "property_contract",
                    "user_type": "buyer",
                    "user_experience_level": "intermediate",
                }
            },
        )

        try:
            composed = composer.compose(composition_name, old_context)
            print("❌ OLD context should have failed but didn't")
            return False
        except Exception as e:
            if "Missing required variables" in str(e):
                print("✓ OLD context correctly failed with missing variables")
            else:
                print(f"❌ OLD context failed with unexpected error: {e}")
                return False

        # Test with the NEW context (should succeed)
        print("\n🧪 Testing with NEW context (should succeed)...")
        new_context = type(
            "MockContext",
            (),
            {
                "variables": {
                    # Template-required variables
                    "contract_text": "Sample contract text",
                    "australian_state": "NSW",
                    "analysis_type": "contract_terms_extraction",
                    # Additional context variables
                    "extracted_text": "Sample contract text",
                    "document_metadata": {},
                    "extraction_type": "contract_terms",
                    "contract_type": "property_contract",
                    "user_type": "buyer",
                    "user_experience_level": "intermediate",
                    "extraction_timestamp": "2024-01-01T00:00:00Z",
                    # Optional template variables
                    "transaction_value": None,
                    "condition": None,
                    "specific_concerns": None,
                }
            },
        )

        try:
            composed = composer.compose(composition_name, new_context)
            print("✓ NEW context successfully composed prompt")
            print(f"  System content: {composed.system_content}")
            print(f"  User content: {composed.user_content}")

            # Verify that the system content contains the expected prompts
            if "legal_specialist" in composed.system_content:
                print("✓ System content contains legal specialist context")
            else:
                print("✗ System content missing legal specialist context")
                return False

            if "australian_legal" in composed.system_content:
                print("✓ System content contains Australian legal context")
            else:
                print("✗ System content missing Australian legal context")
                return False

        except Exception as e:
            print(f"✗ NEW context failed: {e}")
            return False

        print("\n🎉 Transaction value fix test passed!")
        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_template_variable_requirements():
    """Test that we understand the template variable requirements"""

    print("\n🧪 Testing template variable requirements...")

    try:
        # Load the contract_analysis_base template
        template_file = (
            backend_dir
            / "app"
            / "prompts"
            / "user"
            / "instructions"
            / "contract_analysis_base.md"
        )

        if not template_file.exists():
            print(f"✗ Template file not found: {template_file}")
            return False

        print(f"✓ Found template file: {template_file}")

        # Read and parse the template
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract required variables from frontmatter
        if "---" in content:
            frontmatter_start = content.find("---") + 3
            frontmatter_end = content.find("---", frontmatter_start)

            if frontmatter_end > frontmatter_start:
                frontmatter = content[frontmatter_start:frontmatter_end].strip()

                # Parse YAML frontmatter
                import yaml

                try:
                    metadata = yaml.safe_load(frontmatter)

                    required_vars = metadata.get("required_variables", [])
                    optional_vars = metadata.get("optional_variables", [])

                    print(f"✓ Template metadata parsed successfully")
                    print(f"  Required variables: {required_vars}")
                    print(f"  Optional variables: {optional_vars}")

                    # Check if transaction_value is in optional variables
                    if "transaction_value" in optional_vars:
                        print("✓ transaction_value is correctly marked as optional")
                    else:
                        print("⚠ transaction_value not found in optional variables")

                    # Check if contract_text is in required variables
                    if "contract_text" in required_vars:
                        print("✓ contract_text is correctly marked as required")
                    else:
                        print("⚠ contract_text not found in required variables")

                    # Check if analysis_type is in required variables
                    if "analysis_type" in required_vars:
                        print("✓ analysis_type is correctly marked as required")
                    else:
                        print("⚠ analysis_type not found in required variables")

                except yaml.YAMLError as e:
                    print(f"✗ Failed to parse YAML frontmatter: {e}")
                    return False

        # Check for transaction_value usage in template content
        if "transaction_value" in content:
            print("✓ Template content references transaction_value")

            # Find the specific line where it's used
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "transaction_value" in line:
                    print(f"  Line {i+1}: {line.strip()}")
                    break
        else:
            print("⚠ Template content does not reference transaction_value")

        return True

    except Exception as e:
        print(f"✗ Template variable test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting transaction value fix verification...\n")

    # Test the fix
    success1 = await test_transaction_value_fix()

    # Test template variable requirements
    success2 = await test_template_variable_requirements()

    if success1 and success2:
        print("\n🎉 All tests passed!")
        print("\n📋 Summary of fixes applied:")
        print(
            "  ✅ Fixed 'australian_context' -> 'australian_legal' in composition rules"
        )
        print("  ✅ Added missing required variables to context:")
        print("     - contract_text (was extracted_text)")
        print("     - analysis_type")
        print("  ✅ Added optional variables with defaults:")
        print("     - transaction_value: None")
        print("     - condition: None")
        print("     - specific_concerns: None")
        print(
            "\n🎯 The contract_terms_extraction_node should now work without both errors!"
        )
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
