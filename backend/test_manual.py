#!/usr/bin/env python3
"""
Manual test using requests to test the live server
"""

import requests
import sys
import subprocess
import time
import os

def test_health_endpoint():
    """Test the health endpoint manually"""
    print("🚀 Starting manual backend test...")
    
    # Start the server in background
    try:
        print("Starting server...")
        env = os.environ.copy()
        env['ENVIRONMENT'] = 'testing'
        
        server_process = subprocess.Popen([
            '.venv/bin/python', '-m', 'uvicorn', 'app.main:app', 
            '--host', '127.0.0.1', '--port', '8001'
        ], env=env)
        
        # Wait for server to start
        time.sleep(3)
        
        # Test health endpoint
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health endpoint working! Status: {response.status_code}")
            print(f"   Response: {data}")
            
            # Verify expected fields
            required_fields = ['status', 'timestamp', 'version', 'environment']
            for field in required_fields:
                if field in data:
                    print(f"   ✅ {field}: {data[field]}")
                else:
                    print(f"   ❌ Missing field: {field}")
                    
            return True
        else:
            print(f"❌ Health endpoint failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Clean up server process
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
            print("🛑 Server stopped")
        except:
            server_process.kill()
            print("🛑 Server force killed")

if __name__ == "__main__":
    success = test_health_endpoint()
    sys.exit(0 if success else 1)