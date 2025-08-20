"""Simple test to validate fragment system components"""

from pathlib import Path
import yaml


def test_fragment_files():
    """Test that fragment files exist and are valid"""
    print("🧪 Testing Fragment System Components")
    print("=" * 50)

    # Test fragment files exist
    fragments_dir = Path(__file__).parent.parent.parent.parent / "prompts" / "fragments"

    expected_fragments = [
        "nsw/planning_certificates.md",
        "nsw/cooling_off_period.md",
        "vic/vendor_statements.md",
        "vic/cooling_off_period.md",
        "common/cooling_off_framework.md",
    ]

    print("📁 Checking Fragment Files:")
    for fragment_path in expected_fragments:
        full_path = fragments_dir / fragment_path
        if full_path.exists():
            print(f"  ✅ {fragment_path}")

            # Test frontmatter parsing
            content = full_path.read_text()
            if content.startswith("---"):
                end_pos = content.find("---", 3)
                if end_pos > 0:
                    frontmatter = content[3:end_pos].strip()
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        required_fields = ["category", "description", "tags"]
                        missing = [
                            field for field in required_fields if field not in metadata
                        ]
                        if missing:
                            print(f"    ⚠️  Missing metadata: {missing}")
                        else:
                            print(f"    ✅ Valid metadata")
                    except yaml.YAMLError as e:
                        print(f"    ❌ Invalid YAML: {e}")
        else:
            print(f"  ❌ {fragment_path} - NOT FOUND")

    # Test configuration files
    config_dir = Path(__file__).parent.parent.parent.parent / "prompts" / "config"

    expected_configs = [
        "contract_analysis_orchestrator.yaml",
        "composition_rules.yaml",
        "prompt_registry.yaml",
    ]

    print("\n⚙️  Checking Configuration Files:")
    for config_file in expected_configs:
        full_path = config_dir / config_file
        if full_path.exists():
            print(f"  ✅ {config_file}")

            # Test YAML validity
            try:
                with open(full_path, "r") as f:
                    yaml.safe_load(f)
                print(f"    ✅ Valid YAML")
            except yaml.YAMLError as e:
                print(f"    ❌ Invalid YAML: {e}")
        else:
            print(f"  ❌ {config_file} - NOT FOUND")

    # Test base templates
    templates_dir = (
        Path(__file__).parent.parent.parent.parent / "prompts" / "user" / "instructions"
    )

    expected_templates = ["contract_analysis_base.md"]

    print("\n📝 Checking Base Templates:")
    for template_file in expected_templates:
        full_path = templates_dir / template_file
        if full_path.exists():
            print(f"  ✅ {template_file}")

            # Check for fragment orchestration reference
            content = full_path.read_text()
            if "fragment_orchestration" in content:
                print(f"    ✅ Contains fragment orchestration reference")
            if "{{ " in content and "_fragments" in content:
                print(f"    ✅ Contains fragment placeholders")
        else:
            print(f"  ❌ {template_file} - NOT FOUND")

    print("\n" + "=" * 50)
    print("✅ Fragment System Structure Test Complete")


if __name__ == "__main__":
    test_fragment_files()
