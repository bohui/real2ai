#!/usr/bin/env python3
"""
Debug script to help identify authentication issues causing 403 responses.
Run this script to test the authentication flow and see where it's failing.
"""

import requests
from datetime import datetime


def test_auth_flow():
    """Test the complete authentication flow to identify issues."""

    base_url = "http://localhost:8000"

    print(f"🔍 Testing authentication flow at {base_url}")
    print(f"⏰ Time: {datetime.now()}")
    print("=" * 60)

    # Test 1: Check if backend is running
    try:
        health_response = requests.get(f"{base_url}/health")
        print(f"✅ Backend health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print(f"   Response: {health_response.json()}")
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return

    # Test 2: Check if we have a valid token in localStorage (frontend)
    print("\n🔑 Checking frontend token...")
    print("   Please check your browser console for:")
    print("   - localStorage.getItem('auth_token')")
    print("   - Any 401/403 responses in Network tab")

    # Test 3: Test onboarding endpoint with no auth
    try:
        onboarding_response = requests.get(f"{base_url}/api/users/onboarding/status")
        print(f"🔒 Onboarding endpoint (no auth): {onboarding_response.status_code}")
        if onboarding_response.status_code != 401:
            print(f"   ⚠️  Expected 401, got {onboarding_response.status_code}")
            print(f"   Response: {onboarding_response.text}")
    except Exception as e:
        print(f"❌ Onboarding endpoint test failed: {e}")

    # Test 4: Check backend logs
    print("\n📋 Backend logging check:")
    print("   1. Check if backend is running with proper log level")
    print("   2. Look for these log messages:")
    print("      - 'Processing token for user: ...'")
    print("      - 'Token type check - is_backend_token: ...'")
    print("      - 'Auth context set for user: ...'")
    print("      - 'No token available for request to ...'")

    # Test 5: Common issues and solutions
    print("\n🔧 Common issues and solutions:")
    print("   1. Token expired: Clear localStorage and re-login")
    print("   2. Backend token mapping lost: Restart backend")
    print("   3. RLS policy issues: Check Supabase policies")
    print("   4. CORS issues: Check backend CORS configuration")

    print("\n" + "=" * 60)
    print("💡 Next steps:")
    print("   1. Check browser console for 403 responses")
    print("   2. Check backend logs for authentication messages")
    print("   3. Try logging out and back in")
    print("   4. Check if token is valid in Supabase dashboard")


if __name__ == "__main__":
    test_auth_flow()
