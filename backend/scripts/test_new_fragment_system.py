#!/usr/bin/env python3
"""
Test script for the new folder-structure-driven fragment system.

This script demonstrates the complete functionality of the new fragment system
with realistic scenarios and validates that it works as expected.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add the backend app to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.prompts.fragment_manager import FragmentManager
from app.core.prompts.composer import PromptComposer
from app.core.prompts.validators import FragmentSystemValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FragmentSystemTester:
    """Comprehensive tester for the new fragment system"""

    def __init__(self, fragments_dir: Path, templates_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.templates_dir = Path(templates_dir)

        # Initialize managers
        self.fragment_manager = FragmentManager(self.fragments_dir)
        self.validator = FragmentSystemValidator(self.fragments_dir)

        # Test scenarios
        self.test_scenarios = [
            {
                "name": "NSW Purchase - Novice - Comprehensive",
                "context": {
                    "state": "NSW",
                    "contract_type": "purchase",
                    "user_experience": "novice",
                    "analysis_depth": "comprehensive",
                },
                "expected_groups": [
                    "state_requirements",
                    "contract_types",
                    "user_experience",
                    "consumer_protection",
                ],
            },
            {
                "name": "VIC Lease - Expert - Quick",
                "context": {
                    "state": "VIC",
                    "contract_type": "lease",
                    "user_experience": "expert",
                    "analysis_depth": "quick",
                },
                "expected_groups": [
                    "state_requirements",
                    "contract_types",
                    "consumer_protection",
                ],
            },
            {
                "name": "Unknown State - Any Contract",
                "context": {
                    "state": "NT",  # No fragments for NT
                    "contract_type": "purchase",
                    "user_experience": "intermediate",
                    "analysis_depth": "focused",
                },
                "expected_empty_groups": ["state_requirements"],
            },
        ]

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        results = {
            "validation": {},
            "scenarios": [],
            "composition": {},
            "performance": {},
            "errors": [],
        }

        try:
            # Test 1: System validation
            logger.info("Running system validation tests...")
            results["validation"] = self.test_system_validation()

            # Test 2: Fragment loading and grouping
            logger.info("Testing fragment loading and grouping...")
            results["fragment_loading"] = self.test_fragment_loading()

            # Test 3: Context matching scenarios
            logger.info("Testing context matching scenarios...")
            for scenario in self.test_scenarios:
                scenario_result = self.test_scenario(scenario)
                results["scenarios"].append(scenario_result)

            # Test 4: Template composition
            logger.info("Testing template composition...")
            results["composition"] = self.test_template_composition()

            # Test 5: Performance metrics
            logger.info("Testing performance metrics...")
            results["performance"] = self.test_performance_metrics()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            results["errors"].append(str(e))

        return results

    def test_system_validation(self) -> Dict[str, Any]:
        """Test system validation functionality"""
        validation_result = self.validator.validate_complete_system()

        return {
            "valid": validation_result["valid"],
            "total_groups": validation_result["summary"]["total_groups"],
            "total_fragments": validation_result["summary"]["total_fragments"],
            "issues": validation_result["issues"],
            "warnings": validation_result["warnings"],
        }

    def test_fragment_loading(self) -> Dict[str, Any]:
        """Test fragment loading and caching"""
        groups = self.fragment_manager.get_available_groups()

        loading_results = {}
        for group in groups:
            fragments = self.fragment_manager.load_fragments_for_group(group)
            loading_results[group] = {
                "fragment_count": len(fragments),
                "has_fragments": len(fragments) > 0,
            }

        return {
            "available_groups": groups,
            "group_results": loading_results,
            "total_groups": len(groups),
        }

    def test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific context matching scenario"""
        logger.info(f"Testing scenario: {scenario['name']}")

        context = scenario["context"]
        result = self.fragment_manager.compose_fragments(context)

        scenario_result = {
            "name": scenario["name"],
            "context": context,
            "result": {},
            "validation": {"passed": True, "issues": []},
        }

        # Check that expected groups have content
        for group in scenario.get("expected_groups", []):
            if group in result:
                has_content = len(result[group].strip()) > 0
                scenario_result["result"][group] = {
                    "has_content": has_content,
                    "length": len(result[group]),
                }

                if not has_content:
                    scenario_result["validation"]["passed"] = False
                    scenario_result["validation"]["issues"].append(
                        f"Expected content in {group}"
                    )
            else:
                scenario_result["validation"]["passed"] = False
                scenario_result["validation"]["issues"].append(
                    f"Missing expected group: {group}"
                )

        # Check that expected empty groups are indeed empty
        for group in scenario.get("expected_empty_groups", []):
            if group in result:
                is_empty = len(result[group].strip()) == 0
                scenario_result["result"][group] = {
                    "is_empty": is_empty,
                    "length": len(result[group]),
                }

                if not is_empty:
                    scenario_result["validation"]["passed"] = False
                    scenario_result["validation"]["issues"].append(
                        f"Expected {group} to be empty"
                    )

        return scenario_result

    def test_template_composition(self) -> Dict[str, Any]:
        """Test complete template composition"""
        # Load a base template
        template_file = self.templates_dir / "contract_analysis_base.md"

        if not template_file.exists():
            return {"error": f"Template file not found: {template_file}"}

        template_content = template_file.read_text(encoding="utf-8")

        # Extract template content (skip frontmatter)
        if template_content.startswith("---"):
            end_pos = template_content.find("---", 3)
            if end_pos > 0:
                template_content = template_content[end_pos + 3 :].strip()

        # Test composition with realistic context
        test_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
            "analysis_depth": "comprehensive",
        }

        try:
            # Create a temporary composer for testing
            composer = PromptComposer(
                prompts_dir=self.fragments_dir.parent,
                config_dir=self.fragments_dir.parent / "config",
            )
            composer.folder_fragment_manager = self.fragment_manager

            composed_result = composer.compose_with_folder_fragments(
                base_template=template_content, runtime_context=test_context
            )

            return {
                "success": True,
                "template_length": len(template_content),
                "composed_length": len(composed_result),
                "context_used": test_context,
                "contains_nsw_content": "NSW" in composed_result,
                "contains_purchase_content": "purchase" in composed_result.lower()
                or "settlement" in composed_result.lower(),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "context_used": test_context}

    def test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance and get metrics"""
        import time

        # Test fragment loading performance
        start_time = time.time()
        groups = self.fragment_manager.get_available_groups()
        for group in groups:
            self.fragment_manager.load_fragments_for_group(group)
        loading_time = time.time() - start_time

        # Test composition performance
        test_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
            "analysis_depth": "comprehensive",
        }

        start_time = time.time()
        result = self.fragment_manager.compose_fragments(test_context)
        composition_time = time.time() - start_time

        # Get system metrics
        metrics = self.fragment_manager.get_metrics()

        return {
            "loading_time_seconds": round(loading_time, 3),
            "composition_time_seconds": round(composition_time, 3),
            "system_metrics": metrics,
            "total_composed_length": sum(len(content) for content in result.values()),
        }

    def print_test_results(self, results: Dict[str, Any]):
        """Print formatted test results"""
        print("\n" + "=" * 80)
        print("FRAGMENT SYSTEM TEST RESULTS")
        print("=" * 80)

        # Validation results
        validation = results.get("validation", {})
        print(f"\n📋 SYSTEM VALIDATION:")
        print(f"   Valid: {validation.get('valid', False)}")
        print(f"   Groups: {validation.get('total_groups', 0)}")
        print(f"   Fragments: {validation.get('total_fragments', 0)}")
        if validation.get("issues"):
            print(f"   Issues: {len(validation['issues'])}")

        # Fragment loading results
        loading = results.get("fragment_loading", {})
        print(f"\n📁 FRAGMENT LOADING:")
        print(f"   Available groups: {loading.get('total_groups', 0)}")
        for group, info in loading.get("group_results", {}).items():
            print(f"   {group}: {info['fragment_count']} fragments")

        # Scenario results
        print(f"\n🧪 SCENARIO TESTING:")
        for scenario in results.get("scenarios", []):
            status = "✅ PASS" if scenario["validation"]["passed"] else "❌ FAIL"
            print(f"   {status} {scenario['name']}")
            if scenario["validation"]["issues"]:
                for issue in scenario["validation"]["issues"]:
                    print(f"      - {issue}")

        # Composition results
        composition = results.get("composition", {})
        print(f"\n🔧 TEMPLATE COMPOSITION:")
        if composition.get("success"):
            print(f"   ✅ SUCCESS")
            print(f"   Template length: {composition.get('template_length', 0)} chars")
            print(f"   Composed length: {composition.get('composed_length', 0)} chars")
            print(
                f"   Contains NSW content: {composition.get('contains_nsw_content', False)}"
            )
            print(
                f"   Contains purchase content: {composition.get('contains_purchase_content', False)}"
            )
        else:
            print(f"   ❌ FAILED: {composition.get('error', 'Unknown error')}")

        # Performance results
        performance = results.get("performance", {})
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Loading time: {performance.get('loading_time_seconds', 0)}s")
        print(f"   Composition time: {performance.get('composition_time_seconds', 0)}s")
        print(
            f"   Cached fragments: {performance.get('system_metrics', {}).get('cached_fragments', 0)}"
        )
        print(
            f"   Total composed length: {performance.get('total_composed_length', 0)} chars"
        )

        # Errors
        if results.get("errors"):
            print(f"\n❌ ERRORS:")
            for error in results["errors"]:
                print(f"   - {error}")

        print("\n" + "=" * 80)


def main():
    """Main test script entry point"""
    # Get directories relative to script location
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent

    fragments_dir = backend_dir / "app" / "prompts" / "fragments_new"
    templates_dir = backend_dir / "app" / "prompts" / "templates_new"

    if not fragments_dir.exists():
        print(f"❌ Fragments directory not found: {fragments_dir}")
        print("   Run the migration script first or create test fragments.")
        return 1

    if not templates_dir.exists():
        print(f"⚠️  Templates directory not found: {templates_dir}")
        print("   Template composition test will be skipped.")

    # Run tests
    tester = FragmentSystemTester(fragments_dir, templates_dir)
    results = tester.run_all_tests()

    # Print results
    tester.print_test_results(results)

    # Return appropriate exit code
    validation_passed = results.get("validation", {}).get("valid", False)
    scenarios_passed = all(
        s["validation"]["passed"] for s in results.get("scenarios", [])
    )
    composition_passed = results.get("composition", {}).get("success", True)

    if (
        validation_passed
        and scenarios_passed
        and composition_passed
        and not results.get("errors")
    ):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
