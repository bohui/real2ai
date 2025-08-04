#!/usr/bin/env python3
"""
Test script for onboarding functionality
Validates that the onboarding system correctly saves and retrieves user preferences
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = f"test_onboarding_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
TEST_USER_PASSWORD = "TestPass123!"

class OnboardingTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def register_user(self):
        """Register a new test user"""
        self.log("Registering test user...")
        
        response = self.session.post(f"{API_BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "australian_state": "NSW",
            "user_type": "buyer"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.user_id = data.get("user_id")
            self.log(f"User registered successfully: {self.user_id}")
            return True
        else:
            self.log(f"Registration failed: {response.status_code} - {response.text}")
            return False
    
    def login_user(self):
        """Login the test user"""
        self.log("Logging in test user...")
        
        response = self.session.post(f"{API_BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            self.log("Login successful")
            return True
        else:
            self.log(f"Login failed: {response.status_code} - {response.text}")
            return False
    
    def check_initial_onboarding_status(self):
        """Check that onboarding is initially not completed"""
        self.log("Checking initial onboarding status...")
        
        response = self.session.get(f"{API_BASE_URL}/api/users/onboarding/status")
        
        if response.status_code == 200:
            data = response.json()
            onboarding_completed = data.get("onboarding_completed", True)  # Default to True to catch failures
            
            if not onboarding_completed:
                self.log("✓ Initial onboarding status is correctly 'not completed'")
                return True
            else:
                self.log("✗ Initial onboarding status should be 'not completed'")
                return False
        else:
            self.log(f"Failed to check onboarding status: {response.status_code} - {response.text}")
            return False
    
    def complete_onboarding(self):
        """Complete the onboarding process"""
        self.log("Completing onboarding...")
        
        preferences = {
            "practice_area": "property",
            "jurisdiction": "nsw",
            "firm_size": "small",
            "primary_contract_types": ["Purchase Agreements", "Lease Agreements"]
        }
        
        response = self.session.post(f"{API_BASE_URL}/api/users/onboarding/complete", json={
            "onboarding_preferences": preferences
        })
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", "")
            skip_onboarding = data.get("skip_onboarding", False)
            
            if not skip_onboarding and "completed successfully" in message:
                self.log("✓ Onboarding completed successfully")
                return True
            else:
                self.log(f"✗ Unexpected onboarding response: {data}")
                return False
        else:
            self.log(f"Failed to complete onboarding: {response.status_code} - {response.text}")
            return False
    
    def verify_onboarding_completed(self):
        """Verify that onboarding is now marked as completed"""
        self.log("Verifying onboarding completion...")
        
        response = self.session.get(f"{API_BASE_URL}/api/users/onboarding/status")
        
        if response.status_code == 200:
            data = response.json()
            onboarding_completed = data.get("onboarding_completed", False)
            onboarding_preferences = data.get("onboarding_preferences", {})
            
            if onboarding_completed:
                self.log("✓ Onboarding status is correctly 'completed'")
                self.log(f"  Preferences saved: {json.dumps(onboarding_preferences, indent=2)}")
                return True
            else:
                self.log("✗ Onboarding should be marked as completed")
                return False
        else:
            self.log(f"Failed to verify onboarding status: {response.status_code} - {response.text}")
            return False
    
    def test_skip_on_second_attempt(self):
        """Test that completing onboarding again returns skip message"""
        self.log("Testing skip behavior on second onboarding attempt...")
        
        response = self.session.post(f"{API_BASE_URL}/api/users/onboarding/complete", json={
            "onboarding_preferences": {
                "practice_area": "commercial",
                "jurisdiction": "vic"
            }
        })
        
        if response.status_code == 200:
            data = response.json()
            skip_onboarding = data.get("skip_onboarding", False)
            
            if skip_onboarding:
                self.log("✓ Second onboarding attempt correctly returns skip=True")
                return True
            else:
                self.log("✗ Second onboarding attempt should return skip=True")
                return False
        else:
            self.log(f"Failed second onboarding attempt: {response.status_code} - {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all onboarding tests"""
        self.log("Starting onboarding tests...")
        
        tests = [
            ("User Registration", self.register_user),
            ("User Login", self.login_user),
            ("Check Initial Status", self.check_initial_onboarding_status),
            ("Complete Onboarding", self.complete_onboarding),
            ("Verify Completion", self.verify_onboarding_completed),
            ("Test Skip Behavior", self.test_skip_on_second_attempt),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running Test: {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✓ {test_name} PASSED")
                else:
                    failed += 1
                    self.log(f"✗ {test_name} FAILED")
            except Exception as e:
                failed += 1
                self.log(f"✗ {test_name} FAILED with exception: {str(e)}")
        
        self.log(f"\n--- Test Results ---")
        self.log(f"Passed: {passed}/{len(tests)}")
        self.log(f"Failed: {failed}/{len(tests)}")
        
        if failed == 0:
            self.log("🎉 All onboarding tests passed!")
            return True
        else:
            self.log("❌ Some tests failed. Check the implementation.")
            return False

def main():
    """Main test execution"""
    tester = OnboardingTester()
    
    # Check if API server is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API server. Make sure it's running on localhost:8000")
        sys.exit(1)
    
    # Run tests
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()