#!/usr/bin/env python3
"""
Test script for Gemini client service role authentication.
"""

import asyncio
import logging
import sys
import os

# Add the app directory to Python path
sys.path.append('/Users/bohuihan/ai/real2ai/backend')

from app.clients.gemini.client import GeminiClient
from app.clients.gemini.config import GeminiClientConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_service_role_auth():
    """Test Gemini client with service role authentication."""
    
    logger.info("Starting Gemini service role authentication test...")
    
    # Configuration for service role authentication
    config = GeminiClientConfig(
        # Service account authentication
        use_service_account=True,
        api_key=None,  # No API key for service account auth
        
        # Model settings
        model_name="gemini-2.5-pro",
        
        # Connection settings
        timeout=30,
        max_retries=2,
        
        # OCR settings
        max_file_size=50 * 1024 * 1024,  # 50MB
        processing_timeout=60,
    )
    
    client = None
    try:
        # Create client
        logger.info("Creating Gemini client...")
        client = GeminiClient(config)
        
        # Check pre-initialization status
        logger.info(f"Client initialized: {client.is_initialized}")
        
        # Check environment setup
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
        if credentials_path and os.path.exists(credentials_path):
            logger.info("✓ Service account credentials file found")
        elif credentials_path:
            logger.error("✗ Service account credentials file not found")
            return False
        else:
            logger.info("Using Application Default Credentials (gcloud auth or metadata server)")
        
        # Initialize client
        logger.info("Initializing client...")
        await client.initialize()
        logger.info("✓ Client initialization successful")
        
        # Perform health check
        logger.info("Performing health check...")
        health_status = await client.health_check()
        logger.info(f"Health check result: {health_status}")
        
        if health_status["status"] == "healthy":
            logger.info("✓ Health check passed")
        else:
            logger.error(f"✗ Health check failed: {health_status}")
            return False
        
        # Test content generation
        logger.info("Testing content generation...")
        test_prompt = "Say 'Hello from Gemini with service account authentication!' in a single sentence."
        
        result = await client.generate_content(test_prompt)
        logger.info(f"✓ Content generation successful: {result[:100]}...")
        
        # Test document analysis capability (if available)
        logger.info("Testing OCR client availability...")
        try:
            ocr_health = await client.ocr.health_check()
            logger.info(f"✓ OCR client health: {ocr_health['status']}")
        except Exception as e:
            logger.warning(f"OCR client test failed: {e}")
        
        logger.info("🎉 All tests passed! Service role authentication is working correctly.")
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        logger.exception("Full error details:")
        return False
        
    finally:
        if client and client.is_initialized:
            logger.info("Cleaning up...")
            await client.close()
            logger.info("✓ Client closed successfully")


async def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Gemini Service Role Authentication Test")
    logger.info("=" * 60)
    
    success = await test_service_role_auth()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("❌ TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())