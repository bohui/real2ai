"""
WebSocket service for Real2.AI real-time updates
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for a specific session"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, metadata: Dict[str, Any] = None):
        """Connect a new WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "connected_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {str(e)}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        for connection in self.active_connections.copy():
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
            self.disconnect(connection)


class WebSocketManager:
    """Manage WebSocket connections across multiple sessions"""
    
    def __init__(self):
        self.managers: Dict[str, ConnectionManager] = {}
    
    def get_manager(self, session_id: str) -> ConnectionManager:
        """Get or create connection manager for session"""
        if session_id not in self.managers:
            self.managers[session_id] = ConnectionManager()
        return self.managers[session_id]
    
    async def connect(self, websocket: WebSocket, session_id: str, metadata: Dict[str, Any] = None):
        """Connect WebSocket to specific session"""
        manager = self.get_manager(session_id)
        await manager.connect(websocket, metadata)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect WebSocket from session"""
        if session_id in self.managers:
            manager = self.managers[session_id]
            manager.disconnect(websocket)
            
            # Clean up empty managers
            if not manager.active_connections:
                del self.managers[session_id]
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to all connections in a session"""
        if session_id in self.managers:
            manager = self.managers[session_id]
            await manager.broadcast(message)
    
    async def send_personal_message(
        self, 
        session_id: str, 
        websocket: WebSocket, 
        message: Dict[str, Any]
    ):
        """Send message to specific WebSocket in session"""
        if session_id in self.managers:
            manager = self.managers[session_id]
            await manager.send_personal_message(message, websocket)
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        for manager in self.managers.values():
            await manager.disconnect_all()
        self.managers.clear()
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.managers)
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(manager.active_connections) for manager in self.managers.values())
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session"""
        if session_id not in self.managers:
            return {"exists": False}
        
        manager = self.managers[session_id]
        return {
            "exists": True,
            "connection_count": len(manager.active_connections),
            "connections": [
                {
                    "connected_at": info["connected_at"].isoformat(),
                    "metadata": info["metadata"]
                }
                for info in manager.connection_info.values()
            ]
        }


# Event message templates
class WebSocketEvents:
    """Standard WebSocket event message templates"""
    
    @staticmethod
    def analysis_started(contract_id: str, estimated_time: Optional[int] = None) -> Dict[str, Any]:
        """Analysis started event"""
        return {
            "event_type": "analysis_started",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "processing",
                "estimated_completion_minutes": estimated_time
            }
        }
    
    @staticmethod
    def analysis_progress(
        contract_id: str, 
        step: str, 
        progress_percent: int,
        step_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analysis progress event"""
        return {
            "event_type": "analysis_progress",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "contract_id": contract_id,
                "current_step": step,
                "progress_percent": progress_percent,
                "step_description": step_description
            }
        }
    
    @staticmethod
    def analysis_completed(
        contract_id: str, 
        summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analysis completed event"""
        return {
            "event_type": "analysis_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "completed",
                "analysis_summary": summary
            }
        }
    
    @staticmethod
    def analysis_failed(
        contract_id: str, 
        error_message: str,
        retry_available: bool = False
    ) -> Dict[str, Any]:
        """Analysis failed event"""
        return {
            "event_type": "analysis_failed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "failed",
                "error_message": error_message,
                "retry_available": retry_available
            }
        }
    
    @staticmethod
    def document_uploaded(
        document_id: str, 
        filename: str,
        processing_status: str = "pending"
    ) -> Dict[str, Any]:
        """Document uploaded event"""
        return {
            "event_type": "document_uploaded",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "filename": filename,
                "processing_status": processing_status
            }
        }
    
    @staticmethod
    def document_processed(
        document_id: str,
        extraction_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Document processed event"""
        return {
            "event_type": "document_processed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "extraction_results": extraction_results
            }
        }
    
    @staticmethod
    def system_notification(
        message: str,
        notification_type: str = "info",
        action_required: bool = False
    ) -> Dict[str, Any]:
        """System notification event"""
        return {
            "event_type": "system_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": message,
                "type": notification_type,  # info, warning, error, success
                "action_required": action_required
            }
        }
    
    @staticmethod
    def heartbeat() -> Dict[str, Any]:
        """Heartbeat event to keep connection alive"""
        return {
            "event_type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"status": "alive"}
        }