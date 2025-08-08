"""
Redis Pub/Sub service for WebSocket communication.

This service allows Celery workers to publish progress updates that are
received by WebSocket connections in the FastAPI process.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
import redis.asyncio as redis
from redis.asyncio.client import PubSub

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisPubSubService:
    """
    Redis Pub/Sub service for real-time communication between Celery workers and WebSocket connections.
    
    Uses Redis channels with namespace prefix to avoid conflicts with Celery.
    Channel format: ws:progress:{contract_id}
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.subscriptions: Dict[str, asyncio.Task] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
            
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            self.pubsub = self.redis_client.pubsub()
            self._initialized = True
            
            logger.info("Redis Pub/Sub service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis Pub/Sub: {str(e)}")
            raise
    
    async def publish_progress(self, contract_id: str, message: Dict[str, Any]):
        """
        Publish progress update to Redis channel.
        Used by Celery workers to send updates.
        """
        if not self._initialized:
            await self.initialize()
            
        channel = f"ws:progress:{contract_id}"
        
        try:
            # Serialize message to JSON
            message_json = json.dumps(message)
            
            # Publish to Redis channel
            subscribers = await self.redis_client.publish(channel, message_json)
            
            logger.info(f"Published progress to {channel}, {subscribers} subscribers")
            return subscribers
        except Exception as e:
            logger.error(f"Failed to publish progress update: {str(e)}")
            raise
    
    async def subscribe_to_progress(
        self, 
        contract_id: str, 
        callback: Callable[[Dict[str, Any]], Any]
    ) -> asyncio.Task:
        """
        Subscribe to progress updates for a specific contract.
        Used by WebSocket connections to receive updates.
        
        Args:
            contract_id: Contract ID to subscribe to
            callback: Async function to call when message received
            
        Returns:
            Subscription task that can be cancelled
        """
        if not self._initialized:
            await self.initialize()
            
        channel = f"ws:progress:{contract_id}"
        
        async def message_listener():
            """Listen for messages and call callback."""
            try:
                # Create a new pubsub instance for this subscription
                sub_pubsub = self.redis_client.pubsub()
                await sub_pubsub.subscribe(channel)
                
                logger.info(f"Subscribed to channel: {channel}")
                
                async for message in sub_pubsub.listen():
                    # Skip subscription confirmation message
                    if message["type"] == "subscribe":
                        continue
                        
                    if message["type"] == "message":
                        try:
                            # Parse JSON message
                            data = json.loads(message["data"])
                            logger.info(f"📦 Redis message received on {channel}: {data}")
                            
                            # Call callback with parsed data
                            await callback(data)
                            logger.info(f"✅ Callback executed successfully for channel {channel}")
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in message: {message['data']}")
                        except Exception as e:
                            logger.error(f"Error in message callback: {str(e)}")
                            
            except asyncio.CancelledError:
                logger.info(f"Subscription cancelled for channel: {channel}")
                await sub_pubsub.unsubscribe(channel)
                await sub_pubsub.close()
                raise
            except Exception as e:
                logger.error(f"Error in message listener: {str(e)}")
                raise
        
        # Create and store subscription task
        task = asyncio.create_task(message_listener())
        self.subscriptions[contract_id] = task
        
        return task
    
    async def unsubscribe_from_progress(self, contract_id: str):
        """Unsubscribe from progress updates for a contract."""
        if contract_id in self.subscriptions:
            task = self.subscriptions[contract_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            del self.subscriptions[contract_id]
            logger.info(f"Unsubscribed from progress updates for contract: {contract_id}")
    
    async def close(self):
        """Close Redis connections and cancel all subscriptions."""
        # Cancel all subscriptions
        for contract_id in list(self.subscriptions.keys()):
            await self.unsubscribe_from_progress(contract_id)
            
        # Close Redis connections
        if self.pubsub:
            await self.pubsub.close()
            
        if self.redis_client:
            await self.redis_client.close()
            
        self._initialized = False
        logger.info("Redis Pub/Sub service closed")


# Global instance
redis_pubsub_service = RedisPubSubService()


# Synchronous wrapper for Celery tasks
def publish_progress_sync(contract_id: str, message: Dict[str, Any]):
    """
    Synchronous wrapper for publishing progress updates from Celery tasks.
    
    This creates a new event loop if needed, suitable for use in Celery workers.
    """
    import asyncio
    import redis
    
    try:
        settings = get_settings()
        sync_redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        
        channel = f"ws:progress:{contract_id}"
        message_json = json.dumps(message)
        
        subscribers = sync_redis.publish(channel, message_json)
        logger.info(f"[Sync] Published progress to {channel}, {subscribers} subscribers")
        logger.debug(f"[Sync] Message content: {message_json}")
        
        sync_redis.close()
        return subscribers
    except Exception as e:
        logger.error(f"[Sync] Failed to publish progress update: {str(e)}")
        return 0