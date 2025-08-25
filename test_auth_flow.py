#!/usr/bin/env python3
"""
Test script to verify the complete authentication flow is working correctly.
This tests the fix where 403 responses are now converted to 401 for proper frontend handling.
"""

import requests
from datetime import datetime


def test_authentication_flow():
    """Test the complete authentication flow to verify the fix."""

    base_url = "http://localhost:8000"

    print(f"🔍 Testing Authentication Flow at {base_url}")
    print(f"⏰ Time: {datetime.now()}")
    print("=" * 70)

    # Test 1: Health check
    try:
        health_response = requests.get(f"{base_url}/health")
        print(f"✅ Backend health check: {health_response.status_code}")
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return

    # Test 2: No Authorization header (simulates browser refresh with no token)
    print("\n🔒 Test: No Authorization Header (Browser Refresh)")
    try:
        response = requests.get(f"{base_url}/api/users/onboarding/status")
        print(f"   Status: {response.status_code}")
        print(f"   Expected: 401 (Not authenticated)")
        print(f"   Actual: {response.status_code}")

        if response.status_code == 401:
            print("   ✅ SUCCESS: Returns 401 as expected")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ FAILED: Expected 401, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Empty Authorization header
    print("\n🔒 Test: Empty Authorization Header")
    try:
        headers = {"Authorization": ""}
        response = requests.get(
            f"{base_url}/api/users/onboarding/status", headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Expected: 401 (Not authenticated)")

        if response.status_code == 401:
            print("   ✅ SUCCESS: Returns 401 as expected")
        else:
            print(f"   ❌ FAILED: Expected 401, got {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Invalid Bearer token
    print("\n🔒 Test: Invalid Bearer Token")
    try:
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = requests.get(
            f"{base_url}/api/users/onboarding/status", headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Expected: 401 (Could not validate credentials)")

        if response.status_code == 401:
            print("   ✅ SUCCESS: Returns 401 as expected")
        else:
            print(f"   ❌ FAILED: Expected 401, got {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Malformed Authorization header
    print("\n🔒 Test: Malformed Authorization Header")
    try:
        headers = {"Authorization": "InvalidFormat"}
        response = requests.get(
            f"{base_url}/api/users/onboarding/status", headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Expected: 401 (Not authenticated)")

        if response.status_code == 401:
            print("   ✅ SUCCESS: Returns 401 as expected")
        else:
            print(f"   ❌ FAILED: Expected 401, got {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 70)
    print("📋 Summary:")
    print("   All tests should return 401 (Not authenticated) instead of 403")
    print("   This ensures the frontend properly catches authentication failures")
    print("   and redirects users to the login page.")
    print("\n💡 Next Steps:")
    print("   1. Test in browser: Refresh page with expired token")
    print("   2. Verify frontend redirects to login on 401 responses")
    print("   3. Check browser console for proper error handling")


if __name__ == "__main__":
    test_authentication_flow()
