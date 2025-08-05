"""
Singleton WebSocket Manager for sharing connections across the application.

This ensures WebSocket connections made in the router can receive messages
from background tasks (Celery workers).
"""

from app.services.websocket_service import WebSocketManager

# Global singleton instance
_websocket_manager_instance = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create the singleton WebSocket manager instance."""
    global _websocket_manager_instance
    
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager()
    
    return _websocket_manager_instance


# For backward compatibility and easier imports
websocket_manager = get_websocket_manager()