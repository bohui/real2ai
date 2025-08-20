#!/usr/bin/env python3
"""
Focused tests for fragment system changes without external dependencies.
"""

import tempfile
import shutil
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Import our new components directly
import sys

sys.path.insert(0, str(Path(__file__).parent))


def test_context_matcher():
    """Test the context matching functionality"""
    print("🧪 TESTING CONTEXT MATCHER")
    print("-" * 40)

    # Import our context matcher
    from app.core.prompts.context_matcher import ContextMatcher

    matcher = ContextMatcher()

    test_cases = [
        {
            "name": "Exact string match",
            "fragment_context": {"state": "NSW"},
            "runtime_context": {"state": "NSW"},
            "expected": True,
        },
        {
            "name": "Case insensitive match",
            "fragment_context": {"state": "NSW"},
            "runtime_context": {"state": "nsw"},
            "expected": True,
        },
        {
            "name": "Wildcard match",
            "fragment_context": {"state": "*", "contract_type": "*"},
            "runtime_context": {"state": "NSW", "contract_type": "purchase"},
            "expected": True,
        },
        {
            "name": "List match - included",
            "fragment_context": {"contract_type": ["purchase", "option"]},
            "runtime_context": {"contract_type": "purchase"},
            "expected": True,
        },
        {
            "name": "List match - case insensitive",
            "fragment_context": {"contract_type": ["purchase", "option"]},
            "runtime_context": {"contract_type": "PURCHASE"},
            "expected": True,
        },
        {
            "name": "List match - not included",
            "fragment_context": {"contract_type": ["purchase", "option"]},
            "runtime_context": {"contract_type": "lease"},
            "expected": False,
        },
        {
            "name": "Missing runtime key",
            "fragment_context": {"state": "NSW", "missing_key": "value"},
            "runtime_context": {"state": "NSW"},
            "expected": False,
        },
        {
            "name": "Empty fragment context matches all",
            "fragment_context": {},
            "runtime_context": {"state": "NSW", "contract_type": "purchase"},
            "expected": True,
        },
        {
            "name": "Complex multi-key match",
            "fragment_context": {
                "state": "NSW",
                "contract_type": ["purchase", "option"],
                "user_experience": "*",
            },
            "runtime_context": {
                "state": "NSW",
                "contract_type": "purchase",
                "user_experience": "novice",
            },
            "expected": True,
        },
        {
            "name": "Complex multi-key no match",
            "fragment_context": {
                "state": "NSW",
                "contract_type": ["purchase", "option"],
                "user_experience": "expert",
            },
            "runtime_context": {
                "state": "NSW",
                "contract_type": "purchase",
                "user_experience": "novice",  # Doesn't match expert
            },
            "expected": False,
        },
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        result = matcher.matches_context(
            test_case["fragment_context"], test_case["runtime_context"]
        )

        if result == test_case["expected"]:
            print(f"✅ PASS: {test_case['name']}")
            passed += 1
        else:
            print(
                f"❌ FAIL: {test_case['name']} - Expected {test_case['expected']}, got {result}"
            )
            failed += 1

    print(f"\n📊 Context Matcher Results: {passed} passed, {failed} failed")
    return failed == 0


def test_folder_fragment_manager():
    """Test the folder fragment manager functionality"""
    print("\n🗂️  TESTING FOLDER FRAGMENT MANAGER")
    print("-" * 40)

    from app.core.prompts.fragment_manager import FragmentManager

    # Create temporary test structure
    with tempfile.TemporaryDirectory() as temp_dir:
        fragments_dir = Path(temp_dir) / "fragments"

        # Create test structure
        test_structure = {
            "state_requirements/NSW/planning.md": {
                "metadata": {
                    "category": "legal_requirement",
                    "context": {"state": "NSW", "contract_type": "*"},
                    "priority": 80,
                },
                "content": "NSW planning requirements content",
            },
            "state_requirements/VIC/vendor.md": {
                "metadata": {
                    "category": "legal_requirement",
                    "context": {"state": "VIC", "contract_type": "*"},
                    "priority": 85,
                },
                "content": "VIC vendor statement content",
            },
            "contract_types/purchase/settlement.md": {
                "metadata": {
                    "category": "contract_specific",
                    "context": {"state": "*", "contract_type": "purchase"},
                    "priority": 70,
                },
                "content": "Purchase settlement content",
            },
            "user_experience/novice/guidance.md": {
                "metadata": {
                    "category": "guidance",
                    "context": {"user_experience": "novice"},
                    "priority": 60,
                },
                "content": "Novice user guidance content",
            },
            "consumer_protection/cooling_off.md": {
                "metadata": {
                    "category": "consumer_protection",
                    "context": {},  # Empty context = matches all
                    "priority": 90,
                },
                "content": "Consumer protection content",
            },
        }

        # Create files
        for file_path, data in test_structure.items():
            full_path = fragments_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            frontmatter = yaml.dump(data["metadata"], default_flow_style=False)
            content = f"---\n{frontmatter}---\n\n{data['content']}"
            full_path.write_text(content, encoding="utf-8")

        # Test the manager
        manager = FragmentManager(fragments_dir)

        # Test 1: Get available groups
        groups = manager.get_available_groups()
        expected_groups = [
            "consumer_protection",
            "contract_types",
            "state_requirements",
            "user_experience",
        ]

        if sorted(groups) == sorted(expected_groups):
            print("✅ PASS: Get available groups")
        else:
            print(
                f"❌ FAIL: Get available groups - Expected {expected_groups}, got {groups}"
            )
            return False

        # Test 2: Load fragments for specific group
        state_fragments = manager.load_fragments_for_group("state_requirements")
        if len(state_fragments) == 2:
            print("✅ PASS: Load fragments for group")
        else:
            print(
                f"❌ FAIL: Load fragments for group - Expected 2, got {len(state_fragments)}"
            )
            return False

        # Test 3: Fragment priority ordering (VIC=85 should come before NSW=80)
        if state_fragments[0].priority == 85 and state_fragments[1].priority == 80:
            print("✅ PASS: Fragment priority ordering")
        else:
            priorities = [f.priority for f in state_fragments]
            print(
                f"❌ FAIL: Fragment priority ordering - Expected [85, 80], got {priorities}"
            )
            return False

        # Test 4: Context-based composition
        runtime_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
        }

        result = manager.compose_fragments(runtime_context)

        # Check that all groups are present
        expected_groups = [
            "state_requirements",
            "contract_types",
            "user_experience",
            "consumer_protection",
        ]
        if all(group in result for group in expected_groups):
            print("✅ PASS: All groups present in composition")
        else:
            missing = [g for g in expected_groups if g not in result]
            print(f"❌ FAIL: Missing groups in composition: {missing}")
            return False

        # Check specific content inclusion
        if "NSW planning requirements" in result["state_requirements"]:
            print("✅ PASS: NSW content included")
        else:
            print("❌ FAIL: NSW content not included")
            return False

        if "VIC vendor statement" not in result["state_requirements"]:
            print("✅ PASS: VIC content excluded")
        else:
            print("❌ FAIL: VIC content incorrectly included")
            return False

        if "Purchase settlement content" in result["contract_types"]:
            print("✅ PASS: Purchase content included")
        else:
            print("❌ FAIL: Purchase content not included")
            return False

        if "Consumer protection content" in result["consumer_protection"]:
            print("✅ PASS: Universal content included")
        else:
            print("❌ FAIL: Universal content not included")
            return False

        # Test 5: Empty group handling
        empty_context = {"state": "QLD", "contract_type": "lease"}  # No QLD fragments
        empty_result = manager.compose_fragments(empty_context)

        if empty_result["state_requirements"] == "":
            print("✅ PASS: Empty group returns empty string")
        else:
            print("❌ FAIL: Empty group should return empty string")
            return False

        print("\n📊 Folder Fragment Manager: All tests passed!")
        return True


def test_enhanced_logging():
    """Test the enhanced logging functionality"""
    print("\n📝 TESTING ENHANCED LOGGING")
    print("-" * 40)

    from app.core.prompts.context_matcher import ContextMatcher

    # Capture log output
    import io
    import logging

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger("app.core.prompts.context_matcher")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    matcher = ContextMatcher()

    # Test fragments with different match outcomes
    fragments = [
        {
            "name": "nsw_fragment",
            "metadata": {"context": {"state": "NSW", "contract_type": "purchase"}},
        },
        {
            "name": "vic_fragment",
            "metadata": {"context": {"state": "VIC", "contract_type": "*"}},
        },
        {"name": "universal_fragment", "metadata": {"context": {}}},
    ]

    runtime_context = {"state": "NSW", "contract_type": "purchase"}

    # This should trigger detailed logging
    matching = matcher.filter_fragments(fragments, runtime_context)

    # Check log output
    log_output = log_capture.getvalue()

    # Should have match and no-match entries with reasons
    if "✅" in log_output and "❌" in log_output:
        print("✅ PASS: Enhanced logging includes match status indicators")
    else:
        print("❌ FAIL: Enhanced logging missing status indicators")
        return False

    if "NO MATCH:" in log_output:
        print("✅ PASS: Enhanced logging includes mismatch reasons")
    else:
        print("❌ FAIL: Enhanced logging missing mismatch reasons")
        return False

    if "fragment_context=" in log_output and "runtime_context=" in log_output:
        print("✅ PASS: Enhanced logging includes context details")
    else:
        print("❌ FAIL: Enhanced logging missing context details")
        return False

    print("\n📊 Enhanced Logging: All tests passed!")
    return True


def test_validators():
    """Test the validation framework"""
    print("\n✅ TESTING VALIDATION FRAMEWORK")
    print("-" * 40)

    from app.core.prompts.validators import FragmentSystemValidator

    # Create test structure with validation issues
    with tempfile.TemporaryDirectory() as temp_dir:
        fragments_dir = Path(temp_dir) / "fragments"

        # Create valid group
        valid_group = fragments_dir / "state_requirements" / "NSW"
        valid_group.mkdir(parents=True)

        valid_fragment = valid_group / "valid.md"
        valid_content = """---
category: "legal_requirement"
context:
  state: "NSW"
  contract_type: "*"
priority: 80
version: "1.0.0"
---

Valid fragment content"""
        valid_fragment.write_text(valid_content)

        # Create invalid group name
        invalid_group = fragments_dir / "123invalid"
        invalid_group.mkdir(parents=True)

        invalid_fragment = invalid_group / "invalid.md"
        invalid_content = """---
group: "old_group"  # Deprecated field
domain: "old_domain"  # Deprecated field
context:
  state: 123  # Invalid context value type
priority: "invalid"  # Invalid priority type
---

Invalid fragment content"""
        invalid_fragment.write_text(invalid_content)

        # Test validator
        validator = FragmentSystemValidator(fragments_dir)
        result = validator.validate_complete_system()

        # Should find validation issues
        if not result["valid"]:
            print("✅ PASS: Validator detects issues")
        else:
            print("❌ FAIL: Validator should detect issues")
            return False

        # Should detect invalid group name
        invalid_group_found = any("123invalid" in issue for issue in result["issues"])
        if invalid_group_found:
            print("✅ PASS: Validator detects invalid group name")
        else:
            print("❌ FAIL: Validator should detect invalid group name")
            return False

        # Should detect deprecated fields
        deprecated_found = len(result["metadata"]["deprecated_fields"]) > 0
        if deprecated_found:
            print("✅ PASS: Validator detects deprecated fields")
        else:
            print("❌ FAIL: Validator should detect deprecated fields")
            return False

        print("\n📊 Validation Framework: All tests passed!")
        return True


def main():
    """Run all tests"""
    print("🚀 RUNNING FRAGMENT SYSTEM TESTS")
    print("=" * 60)

    tests = [
        ("Context Matcher", test_context_matcher),
        ("Folder Fragment Manager", test_folder_fragment_manager),
        ("Enhanced Logging", test_enhanced_logging),
        ("Validation Framework", test_validators),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    failed = len(results) - passed

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! Fragment system changes are working correctly.")
        return 0
    else:
        print(f"💥 {failed} tests failed. Please review implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
