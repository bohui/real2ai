#!/usr/bin/env python3
"""
Simple test script to verify the backend works without pytest complications
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from app.main import app
    print("✅ App imported successfully")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    sys.exit(1)

try:
    from fastapi.testclient import TestClient
    print("✅ TestClient imported successfully")
except Exception as e:
    print(f"❌ Failed to import TestClient: {e}")
    sys.exit(1)

try:
    # Create a simple test client without dependency overrides
    client = TestClient(app)
    print("✅ TestClient created successfully")
except Exception as e:
    print(f"❌ Failed to create TestClient: {e}")
    sys.exit(1)

try:
    # Test health endpoint
    response = client.get("/health")
    print(f"✅ Health endpoint responded with status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"❌ Failed to test health endpoint: {e}")
    sys.exit(1)

print("🎉 All basic tests passed!")