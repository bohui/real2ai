"""
Test WebSocket service functionality
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.services.websocket_service import ConnectionManager, WebSocketService


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with proper state tracking"""
    ws = Mock(spec=WebSocket)
    ws.client_state = MagicMock()
    ws.client_state.name = "CONNECTED"
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture 
def connection_manager():
    """Create a fresh ConnectionManager instance"""
    return ConnectionManager()


@pytest.fixture
def websocket_service():
    """Create a WebSocketService instance"""
    return WebSocketService()


class TestConnectionManager:
    """Test ConnectionManager functionality"""
    
    @pytest.mark.asyncio
    async def test_connect_new_websocket(self, connection_manager, mock_websocket):
        """Test connecting a new WebSocket"""
        metadata = {"user_id": "test-user", "authenticated": True}
        
        await connection_manager.connect(mock_websocket, metadata)
        
        assert mock_websocket in connection_manager.active_connections
        assert len(connection_manager.active_connections) == 1
        
        conn_info = connection_manager.connection_info[mock_websocket]
        assert conn_info["authenticated"] == True
        assert conn_info["metadata"]["user_id"] == "test-user"
        assert isinstance(conn_info["connected_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_connect_duplicate_websocket(self, connection_manager, mock_websocket, caplog):
        """Test connecting the same WebSocket twice"""
        metadata = {"user_id": "test-user"}
        
        # Connect first time
        await connection_manager.connect(mock_websocket, metadata)
        initial_count = len(connection_manager.active_connections)
        
        # Connect second time (should not duplicate)
        await connection_manager.connect(mock_websocket, metadata)
        
        assert len(connection_manager.active_connections) == initial_count
        assert "Attempted to connect already connected WebSocket" in caplog.text
    
    @pytest.mark.asyncio
    async def test_connect_without_metadata(self, connection_manager, mock_websocket):
        """Test connecting WebSocket without metadata"""
        await connection_manager.connect(mock_websocket)
        
        assert mock_websocket in connection_manager.active_connections
        conn_info = connection_manager.connection_info[mock_websocket]
        assert conn_info["authenticated"] == False
        assert conn_info["metadata"] == {}
    
    @pytest.mark.asyncio
    async def test_disconnect_existing_websocket(self, connection_manager, mock_websocket):
        """Test disconnecting an existing WebSocket"""
        # Connect first
        await connection_manager.connect(mock_websocket)
        assert mock_websocket in connection_manager.active_connections
        
        # Disconnect
        await connection_manager.disconnect(mock_websocket)
        
        assert mock_websocket not in connection_manager.active_connections
        assert mock_websocket not in connection_manager.connection_info
        assert len(connection_manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_websocket(self, connection_manager, mock_websocket, caplog):
        """Test disconnecting a WebSocket that was never connected"""
        await connection_manager.disconnect(mock_websocket)
        
        assert "WebSocket not found in active connections" in caplog.text
    
    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, connection_manager, mock_websocket):
        """Test sending personal message to connected WebSocket"""
        await connection_manager.connect(mock_websocket)
        
        message = {"type": "notification", "data": "Test message"}
        result = await connection_manager.send_personal_message(message, mock_websocket)
        
        assert result == True
        mock_websocket.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_send_personal_message_connection_error(self, connection_manager, mock_websocket):
        """Test handling connection error when sending personal message"""
        await connection_manager.connect(mock_websocket)
        mock_websocket.send_json.side_effect = Exception("Connection error")
        
        message = {"type": "notification", "data": "Test message"}
        result = await connection_manager.send_personal_message(message, mock_websocket)
        
        assert result == False
        # Should remove failed connection
        assert mock_websocket not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_message_all_connections(self, connection_manager):
        """Test broadcasting message to all connected WebSockets"""
        # Create multiple mock WebSockets
        ws1 = Mock(spec=WebSocket)
        ws1.client_state.name = "CONNECTED"
        ws1.send_json = AsyncMock()
        
        ws2 = Mock(spec=WebSocket)
        ws2.client_state.name = "CONNECTED" 
        ws2.send_json = AsyncMock()
        
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        message = {"type": "broadcast", "data": "Global message"}
        await connection_manager.broadcast_message(message)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_message_with_failures(self, connection_manager):
        """Test broadcasting when some connections fail"""
        # Working WebSocket
        ws1 = Mock(spec=WebSocket)
        ws1.client_state.name = "CONNECTED"
        ws1.send_json = AsyncMock()
        
        # Failing WebSocket
        ws2 = Mock(spec=WebSocket)
        ws2.client_state.name = "CONNECTED"
        ws2.send_json = AsyncMock(side_effect=Exception("Connection failed"))
        
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        message = {"type": "broadcast", "data": "Global message"}
        await connection_manager.broadcast_message(message)
        
        # Working connection should succeed
        ws1.send_json.assert_called_once_with(message)
        
        # Failed connection should be removed
        assert ws2 not in connection_manager.active_connections
        assert len(connection_manager.active_connections) == 1
    
    @pytest.mark.asyncio
    async def test_get_connection_info(self, connection_manager, mock_websocket):
        """Test getting connection information"""
        metadata = {"user_id": "test-user", "role": "admin"}
        await connection_manager.connect(mock_websocket, metadata)
        
        info = connection_manager.get_connection_info(mock_websocket)
        
        assert info is not None
        assert info["metadata"]["user_id"] == "test-user" 
        assert info["metadata"]["role"] == "admin"
        assert "connected_at" in info
        assert info["authenticated"] == False  # No authenticated flag in metadata
    
    @pytest.mark.asyncio
    async def test_get_connection_info_nonexistent(self, connection_manager, mock_websocket):
        """Test getting info for non-connected WebSocket"""
        info = connection_manager.get_connection_info(mock_websocket)
        assert info is None


class TestWebSocketService:
    """Test WebSocketService functionality"""
    
    @pytest.mark.asyncio
    async def test_handle_message_analysis_status(self, websocket_service, mock_websocket):
        """Test handling analysis status message"""
        with patch.object(websocket_service, '_handle_analysis_status') as mock_handler:
            message_data = {
                "type": "analysis_status", 
                "contract_id": "test-contract",
                "status": "processing"
            }
            
            await websocket_service.handle_message(mock_websocket, message_data)
            
            mock_handler.assert_called_once_with(mock_websocket, message_data)
    
    @pytest.mark.asyncio 
    async def test_handle_message_contract_update(self, websocket_service, mock_websocket):
        """Test handling contract update message"""
        with patch.object(websocket_service, '_handle_contract_update') as mock_handler:
            message_data = {
                "type": "contract_update",
                "contract_id": "test-contract", 
                "update_data": {"status": "reviewed"}
            }
            
            await websocket_service.handle_message(mock_websocket, message_data)
            
            mock_handler.assert_called_once_with(mock_websocket, message_data)
    
    @pytest.mark.asyncio
    async def test_handle_message_unknown_type(self, websocket_service, mock_websocket):
        """Test handling unknown message type"""
        message_data = {"type": "unknown_type", "data": "test"}
        
        # Should not raise exception
        await websocket_service.handle_message(mock_websocket, message_data)
        
        # Should send error response
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"
        assert "Unknown message type" in sent_message["message"]
    
    @pytest.mark.asyncio
    async def test_notify_analysis_progress(self, websocket_service):
        """Test notifying analysis progress to all connections"""
        with patch.object(websocket_service.manager, 'broadcast_message') as mock_broadcast:
            await websocket_service.notify_analysis_progress(
                "contract-123", "processing", 0.5
            )
            
            mock_broadcast.assert_called_once()
            message = mock_broadcast.call_args[0][0]
            assert message["type"] == "analysis_progress"
            assert message["contract_id"] == "contract-123"
            assert message["status"] == "processing" 
            assert message["progress"] == 0.5
    
    @pytest.mark.asyncio
    async def test_notify_analysis_complete(self, websocket_service):
        """Test notifying analysis completion"""
        result_data = {"risk_score": 3.2, "recommendations": []}
        
        with patch.object(websocket_service.manager, 'broadcast_message') as mock_broadcast:
            await websocket_service.notify_analysis_complete(
                "contract-123", result_data
            )
            
            mock_broadcast.assert_called_once()
            message = mock_broadcast.call_args[0][0]
            assert message["type"] == "analysis_complete"
            assert message["contract_id"] == "contract-123"
            assert message["result"] == result_data
    
    @pytest.mark.asyncio
    async def test_notify_error(self, websocket_service):
        """Test notifying errors to all connections"""
        error_message = "Analysis failed due to invalid document"
        
        with patch.object(websocket_service.manager, 'broadcast_message') as mock_broadcast:
            await websocket_service.notify_error("contract-123", error_message)
            
            mock_broadcast.assert_called_once()
            message = mock_broadcast.call_args[0][0]
            assert message["type"] == "error"
            assert message["contract_id"] == "contract-123" 
            assert message["message"] == error_message
    
    @pytest.mark.asyncio
    async def test_get_connection_count(self, websocket_service):
        """Test getting active connection count"""
        # Mock the manager's active_connections
        websocket_service.manager.active_connections = [Mock(), Mock(), Mock()]
        
        count = websocket_service.get_connection_count()
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_handle_analysis_status_message(self, websocket_service, mock_websocket):
        """Test internal analysis status handler"""
        message_data = {
            "contract_id": "test-contract",
            "status": "completed",
            "progress": 1.0
        }
        
        with patch.object(websocket_service, 'notify_analysis_progress') as mock_notify:
            await websocket_service._handle_analysis_status(mock_websocket, message_data)
            
            mock_notify.assert_called_once_with("test-contract", "completed", 1.0)
    
    @pytest.mark.asyncio
    async def test_handle_contract_update_message(self, websocket_service, mock_websocket):
        """Test internal contract update handler"""
        message_data = {
            "contract_id": "test-contract", 
            "update_data": {"field": "value"}
        }
        
        with patch.object(websocket_service.manager, 'broadcast_message') as mock_broadcast:
            await websocket_service._handle_contract_update(mock_websocket, message_data)
            
            mock_broadcast.assert_called_once()
            broadcasted_message = mock_broadcast.call_args[0][0]
            assert broadcasted_message["type"] == "contract_update"
            assert broadcasted_message["contract_id"] == "test-contract"
            assert broadcasted_message["update_data"] == {"field": "value"}


class TestWebSocketIntegration:
    """Test WebSocket service integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, websocket_service):
        """Test complete connection lifecycle"""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state.name = "CONNECTED"
        mock_ws.send_json = AsyncMock()
        
        # Connect
        await websocket_service.manager.connect(mock_ws, {"user_id": "test-user"})
        assert websocket_service.get_connection_count() == 1
        
        # Send message
        message = {"type": "analysis_status", "contract_id": "test", "status": "processing"}
        await websocket_service.handle_message(mock_ws, message)
        
        # Broadcast notification
        await websocket_service.notify_analysis_progress("contract-123", "processing", 0.5)
        mock_ws.send_json.assert_called()
        
        # Disconnect
        await websocket_service.manager.disconnect(mock_ws)
        assert websocket_service.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_multiple_clients_broadcast(self, websocket_service):
        """Test broadcasting to multiple clients"""
        # Create multiple mock WebSockets
        clients = []
        for i in range(3):
            ws = Mock(spec=WebSocket)
            ws.client_state.name = "CONNECTED"
            ws.send_json = AsyncMock()
            clients.append(ws)
            await websocket_service.manager.connect(ws, {"user_id": f"user-{i}"})
        
        assert websocket_service.get_connection_count() == 3
        
        # Broadcast message
        await websocket_service.notify_analysis_complete("contract-123", {"status": "done"})
        
        # All clients should receive the message
        for client in clients:
            client.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_failure_cleanup(self, websocket_service):
        """Test cleanup when connections fail"""
        # Create one working and one failing WebSocket
        good_ws = Mock(spec=WebSocket)
        good_ws.client_state.name = "CONNECTED"
        good_ws.send_json = AsyncMock()
        
        bad_ws = Mock(spec=WebSocket)
        bad_ws.client_state.name = "CONNECTED"
        bad_ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        
        await websocket_service.manager.connect(good_ws)
        await websocket_service.manager.connect(bad_ws)
        assert websocket_service.get_connection_count() == 2
        
        # Broadcast should clean up failed connections
        await websocket_service.notify_analysis_progress("contract-123", "processing", 0.5)
        
        # Only good connection should remain
        assert websocket_service.get_connection_count() == 1
        assert good_ws in websocket_service.manager.active_connections
        assert bad_ws not in websocket_service.manager.active_connections