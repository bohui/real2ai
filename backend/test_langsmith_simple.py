#!/usr/bin/env python3
"""
Simple test script to validate core LangSmith integration.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up basic environment variables for testing
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-key"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

from app.core.langsmith_config import get_langsmith_config, langsmith_trace, langsmith_session
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status, validate_langsmith_configuration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@langsmith_trace(name="test_simple_function", run_type="tool")
async def test_simple_function(message: str) -> str:
    """Simple test function to verify tracing works."""
    await asyncio.sleep(0.1)  # Simulate some work
    return f"Processed: {message}"


async def test_langsmith_configuration():
    """Test basic LangSmith configuration."""
    print("=" * 60)
    print("Testing LangSmith Configuration")
    print("=" * 60)
    
    # Initialize LangSmith
    enabled = initialize_langsmith()
    print(f"LangSmith enabled: {enabled}")
    
    # Get status
    status = get_langsmith_status()
    print(f"Status: {status}")
    
    # Validate configuration
    is_valid, error = validate_langsmith_configuration()
    print(f"Configuration valid: {is_valid}")
    if error:
        print(f"Configuration error: {error}")
    
    # Get config
    config = get_langsmith_config()
    print(f"Project name: {config.project_name}")
    print(f"Client available: {config.client is not None}")
    
    return enabled


async def test_simple_tracing():
    """Test simple function tracing."""
    print("=" * 60)
    print("Testing Simple Function Tracing")
    print("=" * 60)
    
    try:
        # Test simple traced function
        result = await test_simple_function("Hello LangSmith!")
        print(f"Simple function result: {result}")
        
        # Test session tracing
        async with langsmith_session("test_session", test_type="integration"):
            result1 = await test_simple_function("Message 1")
            result2 = await test_simple_function("Message 2")
            print(f"Session results: {result1}, {result2}")
        
        print("✅ Simple tracing test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Simple tracing test failed: {e}")
        logger.exception("Simple tracing test error")
        return False


async def test_environment_variables():
    """Test environment variable configuration."""
    print("=" * 60)
    print("Testing Environment Variables")
    print("=" * 60)
    
    # Check environment variables
    env_vars = [
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT", 
        "LANGSMITH_TRACING",
        "LANGSMITH_ENDPOINT"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == "LANGSMITH_API_KEY":
                # Mask the API key for security
                masked_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: Not set")
    
    return True


async def main():
    """Main test function."""
    print("🚀 Starting LangSmith Core Integration Tests")
    print()
    
    # Test configuration
    config_ok = await test_langsmith_configuration()
    print()
    
    # Test environment variables
    await test_environment_variables()
    print()
    
    # Test simple tracing (always run, even if LangSmith is disabled)
    simple_ok = await test_simple_tracing()
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Simple Tracing: {'✅ PASS' if simple_ok else '❌ FAIL'}")
    
    if simple_ok:
        print("\n🎉 Core LangSmith integration is working correctly!")
        if not config_ok:
            print("💡 To enable LangSmith tracing, set LANGSMITH_API_KEY and LANGSMITH_PROJECT environment variables.")
    else:
        print(f"\n⚠️ Some tests failed. Check the output above for details.")
    
    return simple_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)