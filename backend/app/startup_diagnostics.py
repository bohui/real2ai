"""
Application startup diagnostics
Checks system health including time synchronization
"""

import logging
from datetime import datetime, timezone
from app.utils.jwt_diagnostics import check_system_time_sync

logger = logging.getLogger(__name__)


async def run_startup_diagnostics():
    """Run diagnostic checks at application startup"""
    logger.info("=" * 50)
    logger.info("STARTUP DIAGNOSTICS")
    logger.info("=" * 50)
    
    # Check system time sync
    logger.info("Checking system time synchronization...")
    time_info = check_system_time_sync()
    
    # Log startup time precisely
    startup_time = datetime.now(timezone.utc)
    logger.info(f"Application startup time: {startup_time.isoformat()}")
    logger.info(f"Startup timestamp: {int(startup_time.timestamp())}")
    
    # Log environment info
    import os
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
    logger.info(f"Database URL: {os.getenv('SUPABASE_URL', 'not_set')[:50]}...")
    
    logger.info("=" * 50)
    logger.info("STARTUP DIAGNOSTICS COMPLETE")
    logger.info("=" * 50)
    
    return {
        "startup_time": startup_time.isoformat(),
        "time_info": time_info,
        "status": "completed"
    }