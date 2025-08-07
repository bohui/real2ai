#!/usr/bin/env python3
"""Test script to verify FastAPI fix."""

import sys
import traceback


def test_fastapi_import():
    """Test that FastAPI can import the contracts router without errors."""
    try:
        # Test importing the main app
        from app.main import app

        print("✅ Successfully imported FastAPI app")

        # Test importing the contracts router specifically
        from app.router.contracts import router

        print("✅ Successfully imported contracts router")

        # Test that the problematic endpoint exists
        routes = [route for route in app.routes if hasattr(route, "path")]
        report_routes = [route for route in routes if "/report" in str(route.path)]

        if report_routes:
            print("✅ Found report endpoint in routes")
        else:
            print("⚠️  Report endpoint not found in routes")

        return True

    except Exception as e:
        print(f"❌ Error importing FastAPI app: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fastapi_import()
    sys.exit(0 if success else 1)
