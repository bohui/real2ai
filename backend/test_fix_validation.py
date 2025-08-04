#!/usr/bin/env python3
"""
Test fix validation script for Real2.AI backend
Validates that architectural fixes resolve the failing test categories
"""

import subprocess
import sys
import json
from pathlib import Path

def run_tests():
    """Run the test suite and capture results"""
    try:
        # Run tests with JSON output for parsing
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--json-report", "--json-report-file=test_results.json"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print("✅ Tests completed")
        print(f"Exit code: {result.returncode}")
        
        # Try to parse JSON results if available
        json_file = Path("test_results.json")
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                print(f"📊 Test Summary:")
                print(f"   Total: {data['summary']['total']}")
                print(f"   Passed: {data['summary'].get('passed', 0)}")
                print(f"   Failed: {data['summary'].get('failed', 0)}")
                print(f"   Errors: {data['summary'].get('error', 0)}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def validate_architectural_fixes():
    """Validate that our architectural fixes are in place"""
    
    fixes_validated = []
    
    # 1. Check auth error handling
    main_py = Path("app/main.py")
    if main_py.exists():
        content = main_py.read_text()
        if "Registration failed" in content and "Invalid credentials" in content:
            fixes_validated.append("✅ Auth error messages fixed")
        else:
            fixes_validated.append("❌ Auth error messages not fixed")
    
    # 2. Check conftest fixtures
    conftest_py = Path("tests/conftest.py")
    if conftest_py.exists():
        content = conftest_py.read_text()
        if "app.main.db_client" in content and "contract_terms" in content:
            fixes_validated.append("✅ Test fixtures updated")
        else:
            fixes_validated.append("❌ Test fixtures not updated")
    
    # 3. Check HTTP exception handling
    if "HTTPException:" in main_py.read_text():
        fixes_validated.append("✅ HTTP exception handling improved")
    else:
        fixes_validated.append("❌ HTTP exception handling not improved")
    
    return fixes_validated

def main():
    """Main validation script"""
    print("🔍 Real2.AI Backend Test Fix Validation")
    print("=" * 50)
    
    # Validate architectural fixes
    print("\n📋 Architectural Fix Validation:")
    fixes = validate_architectural_fixes()
    for fix in fixes:
        print(f"   {fix}")
    
    # Run tests
    print("\n🧪 Running Test Suite:")
    success = run_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Architectural fixes successful.")
        return 0
    else:
        print("\n⚠️  Some tests still failing. Check output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())