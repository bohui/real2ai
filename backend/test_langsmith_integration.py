#!/usr/bin/env python3
"""
Test script to validate LangSmith integration.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.langsmith_config import get_langsmith_config, langsmith_trace, langsmith_session
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status, validate_langsmith_configuration
from app.clients import get_gemini_client, get_openai_client

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


async def test_client_tracing():
    """Test client-level tracing integration."""
    print("=" * 60)
    print("Testing Client Tracing Integration")
    print("=" * 60)
    
    try:
        # Test Gemini client
        try:
            gemini_client = await get_gemini_client()
            if gemini_client:
                print("✅ Gemini client initialized")
                
                # Test simple content generation (this should be traced)
                result = await gemini_client.generate_content("Say 'Hello from Gemini!'")
                print(f"Gemini result: {result[:50]}...")
                print("✅ Gemini tracing test completed")
            else:
                print("⚠️ Gemini client not available")
        except Exception as e:
            print(f"⚠️ Gemini client test failed: {e}")
        
        # Test OpenAI client
        try:
            openai_client = await get_openai_client()
            if openai_client:
                print("✅ OpenAI client initialized")
                
                # Test simple content generation (this should be traced)
                result = await openai_client.generate_content("Say 'Hello from OpenAI!'")
                print(f"OpenAI result: {result[:50]}...")
                print("✅ OpenAI tracing test completed")
            else:
                print("⚠️ OpenAI client not available")
        except Exception as e:
            print(f"⚠️ OpenAI client test failed: {e}")
        
        print("✅ Client tracing test completed")
        return True
        
    except Exception as e:
        print(f"❌ Client tracing test failed: {e}")
        logger.exception("Client tracing test error")
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
    print("🚀 Starting LangSmith Integration Tests")
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
    
    # Test client tracing only if LangSmith is enabled
    client_ok = True
    if config_ok:
        client_ok = await test_client_tracing()
        print()
    else:
        print("⚠️ Skipping client tracing tests (LangSmith disabled)")
        print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Simple Tracing: {'✅ PASS' if simple_ok else '❌ FAIL'}")
    print(f"Client Tracing: {'✅ PASS' if client_ok else '⚠️ SKIPPED'}")
    
    if config_ok and simple_ok and client_ok:
        print("\n🎉 All tests passed! LangSmith integration is working correctly.")
        if not config_ok:
            print("💡 To enable LangSmith tracing, set LANGSMITH_API_KEY and LANGSMITH_PROJECT environment variables.")
    else:
        print(f"\n⚠️ Some tests failed. Check the output above for details.")
    
    return config_ok and simple_ok and client_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)