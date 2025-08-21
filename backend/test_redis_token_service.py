#!/usr/bin/env python3
"""
Test script for Redis-based BackendTokenService.
Run this to verify the token service is working with Redis.
"""

import asyncio
import logging
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.services.backend_token_service import BackendTokenService
from app.core.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_redis_token_service():
    """Test the Redis-based token service."""

    try:
        logger.info("Testing Redis-based BackendTokenService...")

        # Test Redis connection
        logger.info("Testing Redis connection...")
        redis_client = await BackendTokenService._get_redis_client()
        await redis_client.ping()
        logger.info("✅ Redis connection successful")

        # Test token issuance
        logger.info("Testing token issuance...")
        test_user_id = "test-user-123"
        test_email = "test@example.com"
        test_supabase_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjk5OTk5OTk5OX0.test"

        backend_token = await BackendTokenService.issue_backend_token(
            user_id=test_user_id,
            email=test_email,
            supabase_access_token=test_supabase_token,
            supabase_refresh_token="test-refresh-token",
            ttl_seconds=3600,  # 1 hour
        )

        logger.info(f"✅ Backend token issued: {backend_token[:20]}...")

        # Test token retrieval
        logger.info("Testing token retrieval...")
        token_data = await BackendTokenService._get_token_data(backend_token)
        if token_data:
            logger.info(f"✅ Token data retrieved: user_id={token_data.get('user_id')}")
        else:
            logger.error("❌ Failed to retrieve token data")
            return False

        # Test token mapping
        logger.info("Testing token mapping...")
        mapping = await BackendTokenService.get_mapping(backend_token)
        if mapping:
            logger.info(f"✅ Token mapping retrieved: user_id={mapping.get('user_id')}")
        else:
            logger.error("❌ Failed to retrieve token mapping")
            return False

        # Test store stats
        logger.info("Testing store stats...")
        stats = await BackendTokenService.get_store_stats()
        logger.info(f"✅ Store stats: {stats}")

        # Test token deletion
        logger.info("Testing token deletion...")
        deleted = await BackendTokenService._delete_token_data(backend_token)
        if deleted:
            logger.info("✅ Token data deleted successfully")
        else:
            logger.error("❌ Failed to delete token data")
            return False

        # Verify deletion
        token_data_after = await BackendTokenService._get_token_data(backend_token)
        if token_data_after is None:
            logger.info("✅ Token data confirmed deleted")
        else:
            logger.error("❌ Token data still exists after deletion")
            return False

        logger.info(
            "🎉 All tests passed! Redis-based token service is working correctly."
        )
        return True

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("Starting Redis token service tests...")

    success = await test_redis_token_service()

    if success:
        logger.info("All tests completed successfully!")
        sys.exit(0)
    else:
        logger.error("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
