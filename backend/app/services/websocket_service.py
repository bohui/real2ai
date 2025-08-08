"""
WebSocket service for Real2.AI real-time updates with PromptManager integration
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from fastapi import WebSocket, WebSocketDisconnect

from app.core.prompts.service_mixin import PromptEnabledService
from app.models.contract_state import AustralianState, ContractType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for a specific session

    Follows ASGI WebSocket lifecycle best practices:
    - WebSocket must be accepted before calling connect()
    - Proper error handling and state tracking
    - Graceful connection cleanup
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, metadata: Dict[str, Any] = None):
        """Connect a new WebSocket (assumes websocket is already accepted and authenticated)"""
        # Verify WebSocket is in correct state (should be OPEN after accept)
        if websocket.client_state.name != "CONNECTED":
            logger.warning(
                f"WebSocket connect called with state: {websocket.client_state.name}"
            )

        # Prevent duplicate connections
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "connected_at": datetime.now(UTC),
                "metadata": metadata or {},
                "authenticated": (
                    metadata.get("authenticated", False) if metadata else False
                ),
            }
            logger.info(
                f"WebSocket connected successfully. Total connections: {len(self.active_connections)}"
            )
        else:
            logger.warning("Attempted to connect already connected WebSocket")

    async def _rate_limit_outgoing(self, websocket: WebSocket) -> bool:
        """Simple per-connection message rate limiter: max 30 messages per 10 seconds."""
        info = self.connection_info.get(websocket, {})
        now = datetime.now(UTC).timestamp()
        history = info.setdefault("_out_msg_times", [])
        # keep only last 10 seconds
        history[:] = [t for t in history if now - t <= 10]
        if len(history) >= 30:
            return False
        history.append(now)
        return True

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            logger.info(
                f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_personal_message(
        self, message: Dict[str, Any], websocket: WebSocket
    ):
        """Send message to specific WebSocket with enhanced error handling and state validation"""
        try:
            if websocket in self.active_connections:
                # Verify WebSocket is still in CONNECTED state before sending
                if websocket.client_state.name == "CONNECTED":
                    # Rate-limit per-connection to mitigate spam
                    if not await self._rate_limit_outgoing(websocket):
                        logger.warning(
                            "WebSocket personal send throttled due to rate limit"
                        )
                        return
                    await websocket.send_text(json.dumps(message))
                else:
                    logger.warning(
                        f"WebSocket not in CONNECTED state: {websocket.client_state.name}"
                    )
                    self.disconnect(websocket)
            else:
                logger.warning("Attempted to send message to inactive WebSocket")
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            # Remove the problematic connection to prevent further issues
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSockets with state validation"""
        if not self.active_connections:
            logger.debug("No active connections for broadcast")
            return

        message_str = json.dumps(message)
        disconnected = []
        successful_sends = 0

        for (
            connection
        ) in (
            self.active_connections.copy()
        ):  # Use copy to avoid modification during iteration
            try:
                # Validate connection is still in our active list
                if connection in self.active_connections:
                    await connection.send_text(message_str)
                    successful_sends += 1
                else:
                    logger.warning("Skipped broadcast to connection not in active list")
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {str(e)}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(
            f"Broadcast completed: {successful_sends} successful, {len(disconnected)} failed"
        )

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

    async def connect(
        self, websocket: WebSocket, session_id: str, metadata: Dict[str, Any] = None
    ):
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
        self, session_id: str, websocket: WebSocket, message: Dict[str, Any]
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
        return sum(
            len(manager.active_connections) for manager in self.managers.values()
        )

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
                    "metadata": info["metadata"],
                }
                for info in manager.connection_info.values()
            ],
        }

    async def send_progress_update(self, session_id: str, message: Dict[str, Any]):
        """Send progress update to session - compatibility method for background tasks"""
        await self.send_message(session_id, message)


# Event message templates
class WebSocketEvents:
    """Standard WebSocket event message templates"""

    @staticmethod
    def analysis_started(
        contract_id: str, estimated_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """Analysis started event"""
        return {
            "event_type": "analysis_started",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "processing",
                "estimated_completion_minutes": estimated_time,
            },
        }

    @staticmethod
    def analysis_progress(
        contract_id: str,
        step: str,
        progress_percent: int,
        step_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analysis progress event"""
        return {
            "event_type": "analysis_progress",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "contract_id": contract_id,
                "current_step": step,
                "progress_percent": progress_percent,
                "step_description": step_description,
            },
        }

    @staticmethod
    def analysis_completed(contract_id: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analysis completed event"""
        return {
            "event_type": "analysis_completed",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "completed",
                "analysis_summary": summary,
            },
        }

    @staticmethod
    def analysis_failed(
        contract_id: str, error_message: str, retry_available: bool = False
    ) -> Dict[str, Any]:
        """Analysis failed event"""
        return {
            "event_type": "analysis_failed",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "contract_id": contract_id,
                "status": "failed",
                "error_message": error_message,
                "retry_available": retry_available,
            },
        }

    @staticmethod
    def document_uploaded(
        document_id: str, filename: str, processing_status: str = "pending"
    ) -> Dict[str, Any]:
        """Document uploaded event"""
        return {
            "event_type": "document_uploaded",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "document_id": document_id,
                "filename": filename,
                "processing_status": processing_status,
            },
        }

    @staticmethod
    def document_processed(
        document_id: str, extraction_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Document processed event"""
        return {
            "event_type": "document_processed",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "document_id": document_id,
                "extraction_results": extraction_results,
            },
        }

    @staticmethod
    def system_notification(
        message: str, notification_type: str = "info", action_required: bool = False
    ) -> Dict[str, Any]:
        """System notification event"""
        return {
            "event_type": "system_notification",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "message": message,
                "type": notification_type,  # info, warning, error, success
                "action_required": action_required,
            },
        }

    @staticmethod
    def heartbeat() -> Dict[str, Any]:
        """Heartbeat event to keep connection alive"""
        return {
            "event_type": "heartbeat",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"status": "alive"},
        }


class EnhancedWebSocketService(PromptEnabledService):
    """Enhanced WebSocket service with PromptManager integration for dynamic message generation"""

    def __init__(self, websocket_manager: WebSocketManager):
        super().__init__()
        self.websocket_manager = websocket_manager
        logger.info(
            "Enhanced WebSocket service initialized with PromptManager integration"
        )

    async def send_enhanced_notification(
        self,
        session_id: str,
        notification_type: str,
        context: Dict[str, Any],
        template_name: str = None,
        use_templates: bool = True,
    ) -> bool:
        """Send enhanced notification using PromptManager templates

        Args:
            session_id: WebSocket session ID
            notification_type: Type of notification (progress, status, error, etc.)
            context: Context data for message generation
            template_name: Specific template to use (optional)
            use_templates: Whether to use PromptManager templates

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Create base message structure
            base_message = {
                "event_type": notification_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": context,
            }

            # Enhanced message generation using templates if enabled
            if use_templates and template_name:
                try:
                    # Create context for notification template
                    prompt_context = self.create_context(
                        notification_type=notification_type,
                        session_id=session_id,
                        context_data=context,
                        australian_state=context.get(
                            "australian_state", AustralianState.NSW
                        ),
                        contract_type=context.get(
                            "contract_type", ContractType.PURCHASE_AGREEMENT
                        ),
                        service_name=self._service_name,
                    )

                    # Render notification template
                    enhanced_message = await self.render_prompt(
                        template_name=template_name,
                        context=prompt_context,
                        validate=True,
                        use_cache=True,
                    )

                    # Try to parse as JSON if template returns structured data
                    try:
                        structured_message = json.loads(enhanced_message)
                        if isinstance(structured_message, dict):
                            base_message.update(structured_message)
                        else:
                            base_message["enhanced_content"] = enhanced_message
                    except json.JSONDecodeError:
                        # Template returned text content
                        base_message["enhanced_content"] = enhanced_message

                    base_message["template_enhanced"] = True

                except Exception as e:
                    logger.warning(
                        f"Failed to enhance message with template '{template_name}': {e}"
                    )
                    base_message["template_enhanced"] = False
                    base_message["template_error"] = str(e)

            # Send message via WebSocket manager
            await self.websocket_manager.send_message(session_id, base_message)

            logger.debug(
                f"Enhanced notification '{notification_type}' sent to session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send enhanced notification: {e}")
            return False

    async def send_progress_update(
        self,
        session_id: str,
        contract_id: str,
        step: str,
        progress_percent: int,
        step_description: str = None,
        enhanced_context: Dict[str, Any] = None,
    ) -> bool:
        """Send progress update with optional template enhancement"""
        context = {
            "contract_id": contract_id,
            "current_step": step,
            "progress_percent": progress_percent,
            "step_description": step_description,
        }

        if enhanced_context:
            context.update(enhanced_context)

        return await self.send_enhanced_notification(
            session_id=session_id,
            notification_type="analysis_progress",
            context=context,
            template_name="progress_notification",
            use_templates=True,
        )

    async def send_analysis_complete(
        self,
        session_id: str,
        contract_id: str,
        analysis_summary: Dict[str, Any],
        enhanced_summary: bool = True,
    ) -> bool:
        """Send analysis completion notification with enhanced summary"""
        context = {
            "contract_id": contract_id,
            "status": "completed",
            "analysis_summary": analysis_summary,
        }

        template_name = "analysis_complete_notification" if enhanced_summary else None

        return await self.send_enhanced_notification(
            session_id=session_id,
            notification_type="analysis_completed",
            context=context,
            template_name=template_name,
            use_templates=enhanced_summary,
        )

    async def send_error_notification(
        self,
        session_id: str,
        error_type: str,
        error_message: str,
        contract_id: str = None,
        recovery_suggestions: List[str] = None,
    ) -> bool:
        """Send error notification with recovery suggestions"""
        context = {
            "error_type": error_type,
            "error_message": error_message,
            "contract_id": contract_id,
            "recovery_suggestions": recovery_suggestions or [],
            "retry_available": recovery_suggestions is not None,
        }

        return await self.send_enhanced_notification(
            session_id=session_id,
            notification_type="analysis_failed",
            context=context,
            template_name="error_notification",
            use_templates=True,
        )

    async def broadcast_system_message(
        self,
        message_type: str,
        content: str,
        priority: str = "info",
        target_sessions: List[str] = None,
    ) -> int:
        """Broadcast system message to all or specific sessions

        Returns:
            Number of sessions that received the message
        """
        context = {
            "message": content,
            "type": priority,
            "broadcast_time": datetime.now(UTC).isoformat(),
        }

        successful_sends = 0

        if target_sessions:
            # Send to specific sessions
            for session_id in target_sessions:
                success = await self.send_enhanced_notification(
                    session_id=session_id,
                    notification_type="system_notification",
                    context=context,
                    template_name="system_message",
                    use_templates=True,
                )
                if success:
                    successful_sends += 1
        else:
            # Broadcast to all sessions
            for session_id in self.websocket_manager.managers.keys():
                success = await self.send_enhanced_notification(
                    session_id=session_id,
                    notification_type="system_notification",
                    context=context,
                    template_name="system_message",
                    use_templates=True,
                )
                if success:
                    successful_sends += 1

        logger.info(f"System message broadcast to {successful_sends} sessions")
        return successful_sends

    def get_service_stats(self) -> Dict[str, Any]:
        """Get enhanced service statistics"""
        base_stats = {
            "active_sessions": self.websocket_manager.get_session_count(),
            "total_connections": self.websocket_manager.get_total_connections(),
            "service_version": "v2_prompt_enhanced",
            "prompt_manager_enabled": True,
        }

        # Add PromptManager render statistics
        render_stats = self.get_render_stats()
        base_stats.update(
            {
                "prompt_render_stats": render_stats,
                "template_usage": {
                    "total_renders": render_stats.get("total_renders", 0),
                    "cache_hit_rate": render_stats.get("cache_hit_rate", 0.0),
                    "error_rate": render_stats.get("error_rate", 0.0),
                },
            }
        )

        return base_stats
