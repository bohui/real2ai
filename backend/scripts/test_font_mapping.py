#!/usr/bin/env python3
"""
Test Runner for Font Layout Mapping Functionality

This script runs all tests related to the font layout mapping system and provides
a comprehensive summary of the results.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def run_tests(test_pattern: str = None) -> dict:
    """
    Run tests and return results.

    Args:
        test_pattern: Optional pattern to filter tests

    Returns:
        Dictionary with test results
    """
    results = {
        "unit_tests": {"passed": 0, "failed": 0, "errors": 0},
        "integration_tests": {"passed": 0, "failed": 0, "errors": 0},
        "total_time": 0,
        "test_files": [],
    }

    # Define test directories
    test_dirs = ["tests/unit/utils", "tests/integration/agents/nodes"]

    start_time = time.time()

    for test_dir in test_dirs:
        test_path = backend_dir / test_dir
        if not test_path.exists():
            print(f"Warning: Test directory {test_dir} does not exist")
            continue

        # Find test files
        test_files = list(test_path.glob("test_*font*.py"))
        if not test_files:
            print(f"No font-related test files found in {test_dir}")
            continue

        print(f"\nRunning tests in {test_dir}...")

        for test_file in test_files:
            print(f"  Testing {test_file.name}...")
            results["test_files"].append(str(test_file))

            try:
                # Run pytest on the specific test file
                cmd = [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_file),
                    "-v",
                    "--tb=short",
                ]

                if test_pattern:
                    cmd.extend(["-k", test_pattern])

                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=backend_dir
                )

                # Parse results
                if result.returncode == 0:
                    if "unit" in test_dir:
                        results["unit_tests"]["passed"] += 1
                    else:
                        results["integration_tests"]["passed"] += 1
                    print(f"    ✓ PASSED")
                else:
                    if "unit" in test_dir:
                        results["unit_tests"]["failed"] += 1
                    else:
                        results["integration_tests"]["failed"] += 1
                    print(f"    ✗ FAILED")

                    # Show error details
                    if result.stderr:
                        print(f"    Error: {result.stderr.strip()}")

            except Exception as e:
                if "unit" in test_dir:
                    results["unit_tests"]["errors"] += 1
                else:
                    results["integration_tests"]["errors"] += 1
                print(f"    ✗ ERROR: {e}")

    results["total_time"] = time.time() - start_time
    return results


def print_summary(results: dict):
    """Print a summary of test results."""
    print("\n" + "=" * 60)
    print("FONT LAYOUT MAPPING TEST SUMMARY")
    print("=" * 60)

    # Unit test results
    unit_total = sum(results["unit_tests"].values())
    if unit_total > 0:
        print(f"\nUnit Tests:")
        print(f"  Passed:  {results['unit_tests']['passed']}")
        print(f"  Failed:   {results['unit_tests']['failed']}")
        print(f"  Errors:   {results['unit_tests']['errors']}")
        print(f"  Total:    {unit_total}")

    # Integration test results
    integration_total = sum(results["integration_tests"].values())
    if integration_total > 0:
        print(f"\nIntegration Tests:")
        print(f"  Passed:  {results['integration_tests']['passed']}")
        print(f"  Failed:   {results['integration_tests']['failed']}")
        print(f"  Errors:   {results['integration_tests']['errors']}")
        print(f"  Total:    {integration_total}")

    # Overall results
    total_passed = (
        results["unit_tests"]["passed"] + results["integration_tests"]["passed"]
    )
    total_failed = (
        results["unit_tests"]["failed"] + results["integration_tests"]["failed"]
    )
    total_errors = (
        results["unit_tests"]["errors"] + results["integration_tests"]["errors"]
    )
    total_tests = total_passed + total_failed + total_errors

    print(f"\nOverall Results:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed:      {total_passed}")
    print(f"  Failed:      {total_failed}")
    print(f"  Errors:      {total_errors}")
    print(
        f"  Success Rate: {(total_passed/total_tests*100):.1f}%"
        if total_tests > 0
        else "  Success Rate: N/A"
    )

    print(f"\nTotal Time: {results['total_time']:.2f} seconds")

    # Test files
    if results["test_files"]:
        print(f"\nTest Files Executed:")
        for test_file in results["test_files"]:
            print(f"  {test_file}")

    print("\n" + "=" * 60)

    # Return success/failure
    return total_failed == 0 and total_errors == 0


def main():
    """Main function to run the test suite."""
    print("Font Layout Mapping Test Suite")
    print("=" * 40)

    # Check if we're in the right directory
    if not (backend_dir / "app").exists():
        print(f"Error: Must run from backend directory. Current: {os.getcwd()}")
        sys.exit(1)

    # Check for test pattern argument
    test_pattern = None
    if len(sys.argv) > 1:
        test_pattern = sys.argv[1]
        print(f"Filtering tests with pattern: {test_pattern}")

    # Run tests
    try:
        results = run_tests(test_pattern)
        success = print_summary(results)

        if success:
            print("🎉 All tests passed!")
            sys.exit(0)
        else:
            print("❌ Some tests failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
