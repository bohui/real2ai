#!/usr/bin/env python3
"""
Test script for Redis Pub/Sub WebSocket communication.

This script simulates a Celery worker publishing progress updates 
and verifies they can be received by WebSocket clients.
"""

import asyncio
import json
import time
from typing import Dict, Any

# Simple test without full app dependencies
async def test_redis_pubsub():
    """Test Redis Pub/Sub functionality without full app context."""
    try:
        import redis.asyncio as redis
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Create Redis client
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8", 
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        print("✅ Redis connection successful")
        
        # Test publishing progress updates
        contract_id = "test-contract-123"
        channel = f"ws:progress:{contract_id}"
        
        test_messages = [
            {
                "event_type": "analysis_started",
                "timestamp": "2024-01-01T00:00:00Z",
                "data": {
                    "contract_id": contract_id,
                    "estimated_time_minutes": 5,
                    "message": "Analysis started"
                }
            },
            {
                "event_type": "analysis_progress", 
                "timestamp": "2024-01-01T00:01:00Z",
                "data": {
                    "contract_id": contract_id,
                    "current_step": "validating_input",
                    "progress_percent": 20,
                    "step_description": "Validating user credentials and document access",
                    "estimated_completion_minutes": 4
                }
            },
            {
                "event_type": "analysis_progress",
                "timestamp": "2024-01-01T00:02:00Z", 
                "data": {
                    "contract_id": contract_id,
                    "current_step": "analyzing_compliance",
                    "progress_percent": 60,
                    "step_description": "AI is analyzing contract terms and compliance requirements",
                    "estimated_completion_minutes": 2
                }
            },
            {
                "event_type": "analysis_completed",
                "timestamp": "2024-01-01T00:05:00Z",
                "data": {
                    "contract_id": contract_id,
                    "status": "completed",
                    "analysis_summary": {
                        "overall_risk_score": 7.5,
                        "total_recommendations": 3,
                        "compliance_status": "compliant",
                        "processing_time_seconds": 120
                    }
                }
            }
        ]
        
        print(f"📤 Publishing {len(test_messages)} test messages to channel: {channel}")
        
        for i, message in enumerate(test_messages):
            message_json = json.dumps(message)
            subscribers = await redis_client.publish(channel, message_json)
            print(f"  {i+1}. {message['event_type']}: {subscribers} subscribers")
            
            # Add small delay between messages
            await asyncio.sleep(0.5)
        
        await redis_client.close()
        print("✅ Redis Pub/Sub test completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis Pub/Sub test failed: {str(e)}")
        return False

async def test_sync_publish():
    """Test the synchronous publish function used by Celery tasks."""
    try:
        import redis
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Create sync Redis client 
        sync_redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test connection
        sync_redis.ping()
        print("✅ Sync Redis connection successful")
        
        contract_id = "test-sync-contract-456"
        channel = f"ws:progress:{contract_id}"
        
        message = {
            "event_type": "analysis_progress",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {
                "contract_id": contract_id,
                "current_step": "processing_document", 
                "progress_percent": 30,
                "step_description": "Processing document content with OCR"
            }
        }
        
        message_json = json.dumps(message)
        subscribers = sync_redis.publish(channel, message_json)
        
        print(f"📤 Sync publish successful: {subscribers} subscribers")
        
        sync_redis.close()
        print("✅ Sync Redis test completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync Redis test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Redis Pub/Sub for WebSocket communication")
    print("=" * 60)
    
    # Test async Redis pub/sub
    print("\n1. Testing async Redis Pub/Sub:")
    async_success = asyncio.run(test_redis_pubsub())
    
    # Test sync Redis publish (used by Celery)
    print("\n2. Testing sync Redis publish:")
    sync_success = asyncio.run(test_sync_publish())
    
    print("\n" + "=" * 60)
    if async_success and sync_success:
        print("🎉 All Redis Pub/Sub tests passed!")
        print("\n📋 Next steps:")
        print("  1. Start the FastAPI server")
        print("  2. Connect to WebSocket: ws://localhost:8000/ws/contracts/test-contract-123")
        print("  3. Run a Celery task to see real-time updates")
    else:
        print("⚠️  Some Redis tests failed - check Redis connection and configuration")