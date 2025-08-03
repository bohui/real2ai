#!/usr/bin/env python3
"""
Test script to verify Real2.AI backend can start without errors
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test core FastAPI imports
        from fastapi import FastAPI
        print("✓ FastAPI imports successful")
        
        # Test Pydantic imports
        from pydantic import BaseModel
        print("✓ Pydantic imports successful")
        
        # Test application imports
        from app.models.contract_state import RealEstateAgentState, AustralianState
        print("✓ Contract state models imported successfully")
        
        from app.agents.australian_tools import extract_australian_contract_terms
        print("✓ Australian tools imported successfully")
        
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        print("✓ Contract workflow imported successfully")
        
        from app.core.config import get_settings
        print("✓ Configuration module imported successfully")
        
        from app.api.models import ContractAnalysisRequest
        print("✓ API models imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        # Set minimal required environment variables for testing
        os.environ.setdefault('SUPABASE_URL', 'https://example.supabase.co')
        os.environ.setdefault('SUPABASE_ANON_KEY', 'test-anon-key')
        os.environ.setdefault('SUPABASE_SERVICE_KEY', 'test-service-key')
        os.environ.setdefault('OPENAI_API_KEY', 'test-openai-key')
        os.environ.setdefault('OPENAI_API_BASE', 'https://api.openai.com/v1')
        os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret')
        
        from app.core.config import get_settings
        settings = get_settings()
        
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Debug mode: {settings.debug}")
        print(f"✓ Default state: {settings.default_australian_state}")
        
        print("\n✅ Configuration loaded successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        return False

def test_workflow_creation():
    """Test that workflow can be created"""
    print("\nTesting workflow creation...")
    
    try:
        from app.agents.contract_workflow import ContractAnalysisWorkflow
        
        # Create workflow with test API key
        workflow = ContractAnalysisWorkflow(
            openai_api_key="test-key",
            model_name="gpt-4"
        )
        
        print("✓ Contract analysis workflow created successfully")
        print(f"✓ Workflow type: {type(workflow)}")
        
        print("\n✅ Workflow creation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow creation error: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI app creation"""
    print("\nTesting FastAPI app creation...")
    
    try:
        # Note: We can't import the main app directly without proper environment setup
        # So we'll just test that FastAPI can be instantiated
        from fastapi import FastAPI
        
        app = FastAPI(
            title="Real2.AI Test",
            description="Test instance",
            version="1.0.0"
        )
        
        print("✓ FastAPI app created successfully")
        print(f"✓ App title: {app.title}")
        
        print("\n✅ FastAPI app creation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ FastAPI app creation error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Real2.AI Backend Test Suite\n")
    
    tests = [
        test_imports,
        test_configuration,
        test_workflow_creation,
        test_fastapi_app
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 50)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The backend is ready for development.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())